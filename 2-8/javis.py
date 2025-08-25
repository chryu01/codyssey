# javis.py
# ------------------------------------------
# 기능 요약
# - 시스템 마이크 입력으로 음성 녹음
# - 현재 폴더 하위 records/ 에 저장
# - 파일명: YYYYMMDD-HHMMSS.wav
# - 녹음이 끝나면 자동으로 STT → 같은 이름의 CSV 파일 생성
# ------------------------------------------

from __future__ import annotations

import argparse
import csv
import json
import queue
import sys
import threading
import traceback
import wave
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# ====== 기본 Vosk 모델 경로(압축 해제한 "안쪽 폴더") ======
DEFAULT_VOSK_MODEL = r"C:\models\vosk-model-small-ko-0.22\vosk-model-small-ko-0.22"

# 외부 라이브러리 (녹음/인식 전용)
try:
    import sounddevice as sd  # 녹음
except Exception:
    sd = None

try:
    import vosk  # STT
except Exception:
    vosk = None


# ========= 로깅 유틸 =========
def log_info(msg: str) -> None:
    print(msg)


def log_warn(msg: str) -> None:
    print(f"[경고] {msg}")


def log_error(msg: str) -> None:
    print(f"[오류] {msg}", file=sys.stderr)


def log_auto(msg: str) -> None:
    print(f"[AUTO-STT] {msg}")


def log_auto_err(msg: str) -> None:
    print(f"[AUTO-STT 오류] {msg}", file=sys.stderr)


# ========= 공통 유틸 =========
def timestamp_filename() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


def ensure_records_dir() -> Path:
    records = Path(__file__).resolve().parent / "records"
    records.mkdir(parents=True, exist_ok=True)
    return records


def list_record_files() -> List[Path]:
    base = ensure_records_dir()
    files = sorted(base.glob("*.wav"), key=lambda p: p.stat().st_mtime, reverse=True)
    return files


# ========= 녹음 =========
def record_audio(
    device: Optional[int],
    samplerate: Optional[int],
    channels: int,
    duration: Optional[float],
) -> Path:
    if sd is None:
        log_error("sounddevice 설치 필요: pip install sounddevice")
        sys.exit(1)

    if samplerate is None:
        info = sd.query_devices(device, "input")
        samplerate = int(info.get("default_samplerate") or 48000)

    out_dir = ensure_records_dir()
    out_path = out_dir / f"{timestamp_filename()}.wav"

    wf = wave.open(str(out_path), "wb")
    wf.setnchannels(channels)
    wf.setsampwidth(2)  # 16bit
    wf.setframerate(samplerate)

    q_frames: "queue.Queue[bytes]" = queue.Queue()
    stop_flag = threading.Event()

    def callback(indata, frames, time, status):
        if status:
            print(f"[sounddevice] {status}", file=sys.stderr)
        q_frames.put(indata.tobytes())

    def writer():
        while not stop_flag.is_set() or not q_frames.empty():
            try:
                data = q_frames.get(timeout=0.2)
            except queue.Empty:
                continue
            wf.writeframes(data)

    writer_thread = threading.Thread(target=writer, daemon=True)
    writer_thread.start()

    print("===================================")
    print(f"Recording... device={device if device else 'default'} | sr={samplerate} | ch={channels}")
    print(f"→ Saving to: {out_path}")
    print("CSV 예상 경로:", out_path.with_suffix(".csv"))
    if duration:
        print(f"Stop: {duration}초 후 자동 종료")
    else:
        print("Stop: Press ENTER (또는 Ctrl+C)")
    print("===================================")

    try:
        with sd.InputStream(
            device=device,
            channels=channels,
            samplerate=samplerate,
            dtype="int16",
            callback=callback,
        ):
            if duration:
                sd.sleep(int(duration * 1000))
            else:
                input()
    except KeyboardInterrupt:
        print("\n[KeyboardInterrupt] Stopping...")
    finally:
        stop_flag.set()
        writer_thread.join(timeout=3.0)
        wf.close()

    print(f"Saved: {out_path}")
    return out_path


# ========= STT (Vosk) =========
def _open_vosk_model(model_dir: str):
    if vosk is None:
        raise RuntimeError("vosk 설치 필요: pip install vosk")
    model_path = Path(model_dir)
    if not model_path.exists():
        raise FileNotFoundError(f"Vosk 모델 폴더 없음: {model_path}")
    return vosk.Model(str(model_path))


def _recognize_segments(
    wav_path: Path, model, force_sr: Optional[int] = None
) -> Iterable[Tuple[float, float, str]]:
    with wave.open(str(wav_path), "rb") as wf:
        nch = wf.getnchannels()
        sr = wf.getframerate()
        width = wf.getsampwidth()
        if nch != 1 or width != 2:
            raise ValueError("STT는 모노(1ch), 16bit PCM WAV 필요")

        rec = vosk.KaldiRecognizer(model, int(force_sr or sr))
        rec.SetWords(True)

        block_bytes = int(sr * 2 * 0.5)
        while True:
            buf = wf.readframes(block_bytes // 2)
            if not buf:
                break
            if rec.AcceptWaveform(buf):
                data = json.loads(rec.Result())
                text = (data.get("text") or "").strip()
                words = data.get("result") or []
                if text and words:
                    yield float(words[0]["start"]), float(words[-1]["end"]), text

        data = json.loads(rec.FinalResult())
        text = (data.get("text") or "").strip()
        words = data.get("result") or []
        if text and words:
            yield float(words[0]["start"]), float(words[-1]["end"]), text


def stt_to_csv(
    wav_path: Path,
    model_dir: str,
    csv_path: Optional[Path] = None,
) -> Path:
    model = _open_vosk_model(model_dir)
    if csv_path is None:
        csv_path = wav_path.with_suffix(".csv")

    rows = list(_recognize_segments(wav_path, model))

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["start", "end", "text"])
        for s, e, t in rows:
            writer.writerow([f"{s:.2f}", f"{e:.2f}", t])

    return csv_path


# ========= CLI =========
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="JAVIS: recorder + auto STT")
    p.add_argument("--duration", type=float, help="녹음 시간(초). 없으면 ENTER로 종료")
    p.add_argument("--device", type=str, help="입력 장치 인덱스 또는 이름 일부")
    p.add_argument("--samplerate", type=int, help="샘플레이트")
    p.add_argument("--channels", type=int, default=1, help="채널 수 (STT 호환을 위해 1 권장)")
    p.add_argument("--debug", action="store_true", help="traceback 출력")
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # 장치
    try:
        device = None
        if args.device:
            device = int(args.device) if args.device.isdigit() else None
    except Exception as e:
        log_error(f"장치 선택 오류: {e}")
        sys.exit(1)

    # 녹음
    try:
        wav_path = record_audio(
            device=device,
            samplerate=args.samplerate,
            channels=1,  # STT 안정성을 위해 1ch 강제
            duration=args.duration,
        )
    except Exception as e:
        log_error(f"녹음 실패: {e}")
        if args.debug:
            traceback.print_exc()
        sys.exit(2)

    # 자동 STT
    try:
        log_auto("녹음 종료 → STT 수행 중...")
        out_csv = stt_to_csv(wav_path, DEFAULT_VOSK_MODEL)
        log_auto(f"CSV 저장 완료 → {out_csv}")
    except Exception as e:
        log_auto_err(str(e))
        if args.debug:
            traceback.print_exc()
        
        sys.exit(3)


if __name__ == "__main__":
    main()
