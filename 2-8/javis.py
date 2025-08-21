# javis.py
# ------------------------------------------
# 기능 요약
# - (문제 7) 시스템 마이크 입력으로 음성 녹음 → records/ 에 YYYYMMDD-HHMMSS.wav 저장
# - (문제 8) 녹음 파일 목록 조회 / STT(Speech-to-Text)로 텍스트 추출
#   · CSV 형식: '시간, 인식된 텍스트' (세그먼트별 start~end)
#   · CSV 파일명: 음성파일명과 동일 + 확장자만 .csv
# ------------------------------------------

from __future__ import annotations

import argparse
import csv
import queue
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Iterable

import sounddevice as sd  # 외부 라이브러리 (녹음 용도: 허용)
import soundfile as sf    # 외부 라이브러리 (파일 저장 용도: 허용)


# ========================= 공통 유틸 =========================
def ensure_records_dir() -> Path:
    '''현재 실행 폴더 하위 records/를 생성하고 Path를 반환.'''
    records = Path(__file__).resolve().parent / 'records'
    records.mkdir(parents=True, exist_ok=True)
    return records


def timestamp_filename() -> str:
    '''YYYYMMDD-HHMMSS 형태의 파일명(확장자 제외).'''
    return datetime.now().strftime('%Y%m%d-%H%M%S')


# ========================= 문제 7: 녹음 =========================
def list_input_devices() -> None:
    '''입력 가능한 오디오 장치 목록을 출력.'''
    print('=== Audio Input Devices ===')
    devices = sd.query_devices()
    default_in = sd.default.device[0] if sd.default.device else None
    for idx, dev in enumerate(devices):
        if dev['max_input_channels'] > 0:
            mark = ' (default)' if default_in == idx else ''
            print(
                f'[{idx:>2}] {dev["name"]} | inputs={dev["max_input_channels"]} | '
                f'default_sr={dev.get("default_samplerate")} {mark}'
            )


def pick_device(device_arg: str | int | None) -> int | None:
    '''
    --device 인자로 장치 선택.
    - 숫자면 인덱스로 사용
    - 문자열이면 이름 부분일치 검색(첫 번째 매치)
    - None이면 기본 장치 반환(None = PortAudio 기본)
    '''
    if device_arg is None:
        return None

    devices = sd.query_devices()

    if isinstance(device_arg, int) or (
        isinstance(device_arg, str) and device_arg.isdigit()
    ):
        idx = int(device_arg)
        if idx < 0 or idx >= len(devices) or devices[idx]['max_input_channels'] <= 0:
            raise ValueError(f'입력 장치 인덱스가 유효하지 않습니다: {idx}')
        return idx

    namekey = str(device_arg).lower()
    for idx, dev in enumerate(devices):
        if dev['max_input_channels'] > 0 and namekey in dev['name'].lower():
            return idx

    raise ValueError(f'이름에 "{device_arg}" 가 포함된 입력 장치를 찾을 수 없습니다.')


def record_audio(
    device: int | None,
    samplerate: int | None,
    channels: int,
    duration: float | None,
) -> Path:
    '''
    마이크 입력을 녹음하여 records/에 WAV로 저장하고 경로를 반환.
    '''
    # 샘플레이트 결정
    if samplerate is None:
        info = sd.query_devices(device, 'input')
        samplerate = int(info.get('default_samplerate') or 48000)

    # 파일 경로 준비
    out_dir = ensure_records_dir()
    out_path = out_dir / f'{timestamp_filename()}.wav'

    # 오디오 콜백: 들어오는 프레임을 큐에 넣는다.
    q: queue.Queue = queue.Queue()

    def callback(indata, frames, time_info, status):
        if status:
            print(f'[sounddevice] {status}', file=sys.stderr)
        # sounddevice가 넘겨주는 배열(ndarray 유사 객체)을 복사해 큐에 적재
        q.put(indata.copy())

    # 출력 파일 열기 (PCM 16비트)
    sf_file = sf.SoundFile(
        str(out_path),
        mode='w',
        samplerate=samplerate,
        channels=channels,
        subtype='PCM_16',
    )

    # 큐 소비 쓰레드: 큐에서 꺼내 파일에 write
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

    # 안내
    print('===================================')
    print(
        f'Recording... device={device if device is not None else "default"} | '
        f'sr={samplerate} | ch={channels}'
    )
    print(f'→ Saving to: {out_path}')
    if duration is None:
        print('Stop: Press ENTER (또는 Ctrl+C)')
    else:
        print(f'Stop: {duration}초 후 자동 종료')
    print('===================================')

    # 입력 스트림
    try:
        with sd.InputStream(
            device=device,
            channels=channels,
            samplerate=samplerate,
            dtype='float32',
            callback=callback,
        ):
            if duration is None:
                try:
                    input()  # 엔터 대기
                except EOFError:
                    print('표준입력이 없어 Ctrl+C로 종료하세요.')
                    while True:
                        pass
            else:
                sd.sleep(int(duration * 1000))
    except KeyboardInterrupt:
        print('\n[KeyboardInterrupt] Stopping...')
    finally:
        # 정리
        stop_flag.set()
        writer_thread.join(timeout=3.0)
        sf_file.close()

    print(f'Saved: {out_path}')
    return out_path


# ========================= 문제 8: STT =========================
def list_record_files(
    patterns: tuple[str, ...] = ('*.wav', '*.mp3', '*.m4a', '*.flac', '*.ogg'),
) -> list[Path]:
    '''
    records/ 폴더의 음성 파일 목록을 반환(이름순).
    '''
    base = ensure_records_dir()
    files: list[Path] = []
    for pat in patterns:
        files.extend(base.glob(pat))
    return sorted(files)


def sec_to_timestamp(sec: float) -> str:
    '''
    초(float)를 HH:MM:SS.mmm 문자열로 변환.
    '''
    if sec < 0:
        sec = 0.0
    ms = int(round(sec * 1000))
    h = ms // 3_600_000
    ms -= h * 3_600_000
    m = ms // 60_000
    ms -= m * 60_000
    s = ms // 1_000
    ms -= s * 1_000
    return f'{h:02d}:{m:02d}:{s:02d}.{ms:03d}'


def transcribe_with_whisper(
    audio_files: Iterable[Path],
    model_name: str = 'small',
    language: str | None = None,
) -> list[Path]:
    '''
    Whisper로 여러 음성 파일을 STT 수행하고, 각 파일과 같은 이름의 CSV를 생성.
    반환: 생성된 CSV 경로 목록
    '''
    try:
        import whisper  # 외부 라이브러리 (STT 용도: 허용)
    except Exception as exc:
        raise RuntimeError(
            'Whisper 패키지가 필요합니다. 다음을 먼저 실행하세요:\n'
            '  python -m pip install openai-whisper\n'
            '또는 ffmpeg 설치 후 다시 시도하세요.'
        ) from exc

    model = whisper.load_model(model_name)
    created_csvs: list[Path] = []

    for audio_path in audio_files:
        audio_path = Path(audio_path)
        if not audio_path.exists():
            print(f'[건너뜀] 파일이 존재하지 않음: {audio_path}')
            continue

        print(
            f'[STT] Transcribing: {audio_path.name} '
            f'(model={model_name}, lang={language or "auto"})'
        )
        result = model.transcribe(str(audio_path), language=language)

        # CSV 경로: 같은 이름 + .csv
        csv_path = audio_path.with_suffix('.csv')

        # CSV 작성 (UTF-8 with BOM: Excel 호환)
        with csv_path.open('w', encoding='utf-8-sig', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['시간', '인식된 텍스트'])

            segments = result.get('segments', []) or []
            for seg in segments:
                start = float(seg.get('start', 0.0))
                end = float(seg.get('end', start))
                text = (seg.get('text') or '').strip()
                time_str = f'{sec_to_timestamp(start)}~{sec_to_timestamp(end)}'
                writer.writerow([time_str, text])

        print(f'[완료] CSV 저장: {csv_path}')
        if result.get('segments'):
            preview = ' / '.join(
                (s.get('text') or '').strip() for s in result['segments'][:3]
            )
            print(f'  미리보기: {preview[:120]}')
        created_csvs.append(csv_path)

    return created_csvs


# ========================= CLI 인터페이스 =========================
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='JAVIS: microphone recorder & STT')

    # 문제 7 (녹음)
    p.add_argument(
        '--list-devices',
        action='store_true',
        help='입력 오디오 장치 목록 표시 후 종료',
    )
    p.add_argument(
        '--device',
        type=str,
        help='사용할 입력 장치(인덱스 번호 또는 이름 일부)',
    )
    p.add_argument('--samplerate', type=int, help='샘플레이트(예: 48000)')
    p.add_argument(
        '--channels',
        type=int,
        default=1,
        help='채널 수(기본 1=모노, 2=스테레오)',
    )
    p.add_argument(
        '--duration',
        type=float,
        help='녹음 시간(초). 미지정 시 Enter로 종료',
    )

    # 문제 8 (목록/변환)
    p.add_argument(
        '--list-records',
        action='store_true',
        help='records/ 폴더의 음성 파일 목록을 출력하고 종료',
    )
    p.add_argument(
        '--stt',
        type=str,
        help='지정 파일을 STT 수행 (절대경로 또는 records/ 하위 파일명)',
    )
    p.add_argument(
        '--stt-all',
        action='store_true',
        help='records/ 폴더의 모든 음성 파일에 대해 STT 수행',
    )
    p.add_argument(
        '--model',
        type=str,
        default='small',
        help='Whisper 모델명 (tiny/base/small/medium/large 등)',
    )
    p.add_argument(
        '--language',
        type=str,
        help='음성 언어 코드(예: ko, en). 미지정 시 자동감지',
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # 장치 목록
    if args.list_devices:
        list_input_devices()
        return

    # 녹음 모드(문제 7):
    # 녹음 관련 인자 중 하나라도 주어졌거나, 채널이 기본값과 다르면 녹음을 수행
    if any(v is not None for v in [args.device, args.samplerate, args.duration]) or (
        args.channels != 1
    ):
        try:
            device = pick_device(args.device) if args.device is not None else None
        except ValueError as exc:
            print(f'[장치 선택 오류] {exc}', file=sys.stderr)
            sys.exit(1)

        try:
            record_audio(
                device=device,
                samplerate=args.samplerate,
                channels=args.channels,
                duration=args.duration,
            )
        except Exception as exc:
            print(f'[오류] {exc}', file=sys.stderr)
            sys.exit(2)
        return

    # 녹음 파일 목록(문제 8)
    if args.list_records:
        files = list_record_files()
        if not files:
            print('records/ 폴더에 음성 파일이 없습니다.')
        else:
            print('=== Recorded files ===')
            for p in files:
                print(f'- {p.name}')
        return

    # STT: 단일 파일
    if args.stt:
        base = ensure_records_dir()
        p = Path(args.stt)
        audio_path = p if p.is_absolute() else (base / p)
        try:
            created = transcribe_with_whisper(
                [audio_path], model_name=args.model, language=args.language
            )
            if created:
                print(f'[완료] 생성된 CSV: {created[0]}')
        except Exception as exc:
            print(f'[STT 오류] {exc}', file=sys.stderr)
            sys.exit(3)
        return

    # STT: 전체 파일
    if args.stt_all:
        files = list_record_files()
        if not files:
            print('records/ 폴더에 음성 파일이 없습니다.')
            return
        try:
            created = transcribe_with_whisper(
                files, model_name=args.model, language=args.language
            )
            print(f'[완료] 총 {len(created)}개 CSV 생성')
        except Exception as exc:
            print(f'[STT 오류] {exc}', file=sys.stderr)
            sys.exit(3)
        return

    # 아무 인자 없이 실행되면 간단 안내
    print(
        '사용법 예시:\n'
        '  (장치 목록)                   python javis.py --list-devices\n'
        '  (10초 녹음)                   python javis.py --duration 10\n'
        '  (목록 보기)                   python javis.py --list-records\n'
        '  (단일 파일 STT)               python javis.py --stt 20250821-142312.wav '
        '--model small --language ko\n'
        '  (전체 STT)                    python javis.py --stt-all --model small '
        '--language ko\n'
    )


if __name__ == '__main__':
    main()
