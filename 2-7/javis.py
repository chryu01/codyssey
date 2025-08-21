# javis.py
# ------------------------------------------
# 기능 요약
# - 시스템 마이크 입력으로 음성 녹음
# - 현재 폴더 하위 records/ 에 저장
# - 파일명: YYYYMMDD-HHMMSS.wav
# - 옵션:
#     --list-devices    : 입력 장치 목록 보기
#     --device IDX/NAME : 사용할 장치 선택(인덱스 또는 이름 일부)
#     --samplerate SR   : 샘플레이트(기본: 장치 기본값 또는 48000)
#     --channels N      : 채널 수(기본: 1 = 모노)
#     --duration SEC    : 지정 시간(초)만큼 녹음; 미지정 시 Enter로 종료
# ------------------------------------------

from __future__ import annotations

import argparse
import queue
import sys
import threading
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf


def list_input_devices() -> None:
    """입력 가능한 오디오 장치 목록을 출력."""
    print("=== Audio Input Devices ===")
    devices = sd.query_devices()
    default_in = sd.default.device[0] if sd.default.device else None
    for idx, d in enumerate(devices):
        if d["max_input_channels"] > 0:
            mark = " (default)" if default_in == idx else ""
            print(
                f"[{idx:>2}] {d['name']} | inputs={d['max_input_channels']} | "
                f"default_sr={d.get('default_samplerate')} {mark}"
            )


def pick_device(device_arg: str | int | None) -> int | None:
    """
    --device 인자로 장치 선택.
    - 숫자면 인덱스로 사용
    - 문자열이면 이름 부분일치 검색(첫 번째 매치)
    - None이면 기본 장치 반환(None = PortAudio 기본)
    """
    if device_arg is None:
        return None

    devices = sd.query_devices()

    # 숫자(문자열 숫자 포함)로 주어진 경우: 인덱스로 처리
    if isinstance(device_arg, int) or (
        isinstance(device_arg, str) and device_arg.isdigit()
    ):
        idx = int(device_arg)
        if idx < 0 or idx >= len(devices) or devices[idx]["max_input_channels"] <= 0:
            raise ValueError(f"입력 장치 인덱스가 유효하지 않습니다: {idx}")
        return idx

    # 이름 부분일치 검색
    namekey = str(device_arg).lower()
    for idx, d in enumerate(devices):
        if d["max_input_channels"] > 0 and namekey in d["name"].lower():
            return idx

    raise ValueError(f"이름에 '{device_arg}' 가 포함된 입력 장치를 찾을 수 없습니다.")


def timestamp_filename() -> str:
    """YYYYMMDD-HHMMSS 형식 파일명 생성."""
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def ensure_records_dir() -> Path:
    """현재 실행 폴더 하위 records/를 생성하고 경로 반환."""
    records = Path(__file__).resolve().parent / "records"
    records.mkdir(parents=True, exist_ok=True)
    return records


def record_audio(
    device: int | None,
    samplerate: int | None,
    channels: int,
    duration: float | None,
) -> Path:
    """
    실제 녹음 수행.
    - device: 입력 장치 인덱스(None이면 기본)
    - samplerate: 샘플레이트(None이면 장치 기본 또는 48000 시도)
    - channels: 입력 채널 수
    - duration: 녹음 시간(초). None이면 Enter로 종료.
    반환값: 저장된 파일 경로
    """
    # 샘플레이트 결정
    if samplerate is None:
        info = sd.query_devices(device, "input")
        samplerate = int(info.get("default_samplerate") or 48000)

    # 파일 경로 준비
    out_dir = ensure_records_dir()
    out_path = out_dir / f"{timestamp_filename()}.wav"

    # 오디오 콜백 -> 큐에 프레임을 쌓고, 별도 쓰레드가 파일에 기록
    q: queue.Queue[np.ndarray] = queue.Queue()

    def callback(indata, frames, time, status):
        if status:
            # XRuns 등 상태 메시지는 stderr로 출력하고 계속 진행
            print(f"[sounddevice] {status}", file=sys.stderr)
        # float32 프레임을 복사해서 큐에 넣음
        q.put(indata.copy())

    # 파일 열기 (PCM 16비트로 저장; float32 입력은 자동 변환)
    sf_file = sf.SoundFile(
        str(out_path),
        mode="w",
        samplerate=samplerate,
        channels=channels,
        subtype="PCM_16",
    )

    # 큐 소비 쓰레드: 스트림이 도는 동안 큐에서 꺼내 파일에 write
    stop_flag = threading.Event()

    def writer():
        while not stop_flag.is_set() or not q.empty():
            try:
                data = q.get(timeout=0.2)
            except queue.Empty:
                continue
            sf_file.write(data)

    writer_thread = threading.Thread(target=writer, daemon=True)
    writer_thread.start()

    # 스트림 시작
    print("===================================")
    print(
        f"Recording... device={device if device is not None else 'default'} | "
        f"sr={samplerate} | ch={channels}"
    )
    print(f"→ Saving to: {out_path}")
    if duration is None:
        print("Stop: Press ENTER (또는 Ctrl+C)")
    else:
        print(f"Stop: {duration}초 후 자동 종료")
    print("===================================")

    try:
        with sd.InputStream(
            device=device,
            channels=channels,
            samplerate=samplerate,
            dtype="float32",
            callback=callback,
        ):
            if duration is None:
                try:
                    input()  # 엔터 기다리기
                except EOFError:
                    # 입력 스트림이 없는 환경이면 Ctrl+C로 멈추면 됨
                    print("표준입력이 없어 Ctrl+C로 종료하세요.")
                    while True:
                        pass
            else:
                sd.sleep(int(duration * 1000))
    except KeyboardInterrupt:
        print("\n[KeyboardInterrupt] Stopping...")
    finally:
        # 스트림 종료 후 writer가 남은 프레임을 비우도록 신호
        stop_flag.set()
        writer_thread.join(timeout=3.0)
        sf_file.close()

    print(f"Saved: {out_path}")
    return out_path


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="JAVIS: microphone recorder")
    p.add_argument(
        "--list-devices",
        action="store_true",
        help="입력 오디오 장치 목록 표시 후 종료",
    )
    p.add_argument(
        "--device",
        type=str,
        help="사용할 입력 장치(인덱스 번호 또는 이름 일부)",
    )
    p.add_argument("--samplerate", type=int, help="샘플레이트(예: 48000)")
    p.add_argument(
        "--channels",
        type=int,
        default=1,
        help="채널 수(기본 1=모노, 2=스테레오)",
    )
    p.add_argument(
        "--duration",
        type=float,
        help="녹음 시간(초). 미지정 시 Enter로 종료",
    )
    return p.parse_args()


def main():
    args = parse_args()

    if args.list_devices:
        list_input_devices()
        return

    # 장치 선택 처리
    try:
        device = pick_device(args.device) if args.device is not None else None
    except ValueError as e:
        print(f"[장치 선택 오류] {e}", file=sys.stderr)
        sys.exit(1)

    try:
        record_audio(
            device=device,
            samplerate=args.samplerate,
            channels=args.channels,
            duration=args.duration,
        )
    except Exception as e:
        print(f"[오류] {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
