# javis.py
# ------------------------------------------
# 기능 요약
# - PyAudio로 시스템 마이크 입력 녹음 (WAV, 16kHz/모노/16bit)
# - 현재 폴더 하위 records/ 에 YYYYMMDD-HHMMSS.wav 로 저장
# - 녹음 종료 즉시 SpeechRecognition(google, ko-KR)로 STT → 같은 이름의 CSV 저장
# - CSV 형식: start,end,text (초 단위, chunk 기반 타임스탬프)
# - 옵션:
#     --list-devices           : 입력 장치 목록 보기
#     --device IDX/NAME        : 사용할 장치 선택(인덱스 또는 이름 일부)
#     --samplerate SR          : 샘플레이트(기본 16000; STT 권장)
#     --channels N             : 채널 수(기본 1=모노; STT 권장)
#     --duration SEC           : 지정 시간(초) 녹음; 미지정 시 ENTER로 종료
#     --stt PATH               : 지정 WAV 파일 STT → CSV
#     --stt-all                : records/의 모든 WAV STT → CSV
#     --chunk-sec SEC          : STT 청크 길이(기본 5초, 3~15 권장)
#     --api-key KEY            : Google Speech API Key(선택. 미지정시 기본 웹 API 사용)
#     --debug                  : 오류 시 traceback 출력
# ------------------------------------------

from __future__ import annotations

import argparse
import csv
import sys
import threading
import time
import traceback
import wave
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

# 외부 라이브러리 (녹음/인식 전용으로만 사용)
try:
    import pyaudio  # 녹음 (허용)
except Exception:  # pragma: no cover
    pyaudio = None

try:
    import speech_recognition as sr  # STT (허용)
except Exception:  # pragma: no cover
    sr = None


# ========= 로깅 =========

def log_info(msg: str) -> None:
    print(msg)


def log_warn(msg: str) -> None:
    print(f'[경고] {msg}')


def log_error(msg: str) -> None:
    print(f'[오류] {msg}', file=sys.stderr)


def log_auto(msg: str) -> None:
    print(f'[AUTO-STT] {msg}')


def log_auto_err(msg: str) -> None:
    print(f'[AUTO-STT 오류] {msg}', file=sys.stderr)


# ========= 공통 유틸 =========

def timestamp_filename() -> str:
    return datetime.now().strftime('%Y%m%d-%H%M%S')


def ensure_records_dir() -> Path:
    records = Path(__file__).resolve().parent / 'records'
    records.mkdir(parents=True, exist_ok=True)
    return records


def list_record_files() -> List[Path]:
    base = ensure_records_dir()
    files = sorted(base.glob('*.wav'), key=lambda p: p.stat().st_mtime, reverse=True)
    return files


def get_wav_duration_sec(path: Path) -> float:
    try:
        with wave.open(str(path), 'rb') as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            return frames / float(rate) if rate else 0.0
    except Exception:
        return 0.0


# ========= 장치 관련 (PyAudio) =========

def require_pyaudio() -> None:
    if pyaudio is None:
        log_error('PyAudio가 설치되어 있지 않습니다. `pip install pyaudio`')
        sys.exit(1)


def list_input_devices() -> None:
    require_pyaudio()
    pa = pyaudio.PyAudio()
    print('=== Audio Input Devices ===')
    try:
        default_idx = pa.get_default_input_device_info().get('index', None)
    except Exception:
        default_idx = None

    for idx in range(pa.get_device_count()):
        info = pa.get_device_info_by_index(idx)
        if int(info.get('maxInputChannels', 0)) > 0:
            mark = ' (default)' if default_idx == idx else ''
            name = info.get('name', '')
            rate = int(info.get('defaultSampleRate', 0))
            ch = int(info.get('maxInputChannels', 0))
            print(f'[{idx:>2}] {name} | inputs={ch} | default_sr={rate}{mark}')
    pa.terminate()


def pick_device_index(device_arg: Optional[str]) -> Optional[int]:
    if not device_arg:
        return None
    require_pyaudio()
    pa = pyaudio.PyAudio()
    try:
        # 숫자 인덱스
        if device_arg.isdigit():
            idx = int(device_arg)
            info = pa.get_device_info_by_index(idx)
            if int(info.get('maxInputChannels', 0)) <= 0:
                raise ValueError(f'입력 장치가 아닙니다: {idx}')
            return idx
        # 이름 부분일치
        key = device_arg.lower()
        for idx in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(idx)
            if int(info.get('maxInputChannels', 0)) > 0 and key in info.get('name', '').lower():
                return idx
        raise ValueError(f'이름에 "{device_arg}" 가 포함된 입력 장치를 찾을 수 없습니다.')
    finally:
        pa.terminate()


# ========= 녹음 (PyAudio) =========

def record_audio(
    device_index: Optional[int],
    samplerate: Optional[int],
    channels: int,
    duration: Optional[float],
) -> Path:
    require_pyaudio()

    rate = int(samplerate or 16000)  # ko-KR STT 최적: 16kHz
    ch = int(channels or 1)
    if ch <= 0:
        raise ValueError('채널 수는 1 이상이어야 합니다.')

    pa = pyaudio.PyAudio()
    fmt = pyaudio.paInt16
    frames_per_buffer = 1024

    out_dir = ensure_records_dir()
    out_path = out_dir / f'{timestamp_filename()}.wav'

    stop_flag = threading.Event()

    def wait_enter():
        try:
            input()
        except EOFError:
            # 입력이 없는 환경이면 Ctrl+C로 종료 유도
            while not stop_flag.is_set():
                time.sleep(0.2)
        finally:
            stop_flag.set()

    print('===================================')
    print(f'Recording... device={device_index if device_index is not None else "default"} | sr={rate} | ch={ch}')
    print(f'→ Saving to: {out_path}')
    if duration is None:
        print('Stop: Press ENTER (또는 Ctrl+C)')
    else:
        print(f'Stop: {duration}초 후 자동 종료')
    print('===================================')

    # 스트림 열기
    stream = pa.open(
        format=fmt,
        channels=ch,
        rate=rate,
        input=True,
        input_device_index=device_index,
        frames_per_buffer=frames_per_buffer,
    )

    # WAV 파일 헤더 준비
    wf = wave.open(str(out_path), 'wb')
    wf.setnchannels(ch)
    wf.setsampwidth(pa.get_sample_size(fmt))
    wf.setframerate(rate)

    # ENTER 대기 스레드
    enter_thread: Optional[threading.Thread] = None
    if duration is None:
        enter_thread = threading.Thread(target=wait_enter, daemon=True)
        enter_thread.start()

    try:
        start_time = time.time()
        while True:
            data = stream.read(frames_per_buffer, exception_on_overflow=False)
            wf.writeframes(data)

            if duration is not None:
                if time.time() - start_time >= float(duration):
                    break
            else:
                if stop_flag.is_set():
                    break
    except KeyboardInterrupt:
        print('\n[KeyboardInterrupt] Stopping...')
    finally:
        stream.stop_stream()
        stream.close()
        pa.terminate()
        wf.close()

    print(f'Saved: {out_path}')
    return out_path


# ========= STT (SpeechRecognition + Google) =========

def require_speech_recognition() -> None:
    if sr is None:
        log_error('SpeechRecognition이 설치되어 있지 않습니다. `pip install SpeechRecognition`')
        sys.exit(1)


def chunk_ranges(total_sec: float, chunk_sec: float) -> Iterable[Tuple[float, float]]:
    start = 0.0
    while start < total_sec:
        end = min(start + chunk_sec, total_sec)
        yield start, end
        start = end


def stt_google_chunked_to_csv(
    wav_path: Path,
    csv_path: Optional[Path] = None,
    chunk_sec: float = 5.0,
    api_key: Optional[str] = None,
    language: str = 'ko-KR',
) -> Path:
    require_speech_recognition()
    if chunk_sec <= 0:
        raise ValueError('chunk_sec 는 0보다 커야 합니다.')
    if csv_path is None:
        csv_path = wav_path.with_suffix('.csv')

    total_sec = get_wav_duration_sec(wav_path)
    recognizer = sr.Recognizer()

    # 약간의 노이즈 보정(짧게 샘플)
    with sr.AudioFile(str(wav_path)) as source:
        try:
            recognizer.adjust_for_ambient_noise(source, duration=0.3)
        except Exception:
            pass

    rows: List[Tuple[float, float, str]] = []
    with sr.AudioFile(str(wav_path)) as source:
        for s, e in chunk_ranges(total_sec, chunk_sec):
            try:
                audio = recognizer.record(source, duration=(e - s), offset=s)
                # 구글 웹 STT (네트워크 필요). api_key=None이면 기본 공개 엔드포인트를 사용(제한적).
                text = recognizer.recognize_google(audio, key=api_key, language=language)
                text = (text or '').strip()
                if text:
                    rows.append((s, e, text))
                    log_auto(f'{s:.2f}~{e:.2f}s → "{text}"')
                else:
                    log_auto(f'{s:.2f}~{e:.2f}s → (빈 결과)')
            except sr.UnknownValueError:
                log_auto(f'{s:.2f}~{e:.2f}s → (인식 실패)')
            except sr.RequestError as ex:
                # API 호출 실패(쿼터/네트워크 등)
                log_auto_err(f'{s:.2f}~{e:.2f}s → 요청 오류: {ex}')
                # 치명적이므로 중단
                raise

    # CSV 저장
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['start', 'end', 'text'])
        for s, e, t in rows:
            writer.writerow([f'{s:.2f}', f'{e:.2f}', t])

    return csv_path


# ========= CLI =========

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='JAVIS: PyAudio recorder + Google STT (ko-KR)')
    # 녹음
    p.add_argument('--list-devices', action='store_true', help='입력 오디오 장치 목록 표시 후 종료')
    p.add_argument('--device', type=str, help='사용할 입력 장치(인덱스 또는 이름 일부/인덱스)')
    p.add_argument('--samplerate', type=int, help='샘플레이트(기본 16000)')
    p.add_argument('--channels', type=int, default=1, help='채널 수(기본 1=모노)')
    p.add_argument('--duration', type=float, help='녹음 시간(초). 미지정 시 ENTER로 종료')

    # STT
    p.add_argument('--stt', type=str, help='지정 WAV 파일 STT → CSV 저장(파일 경로)')
    p.add_argument('--stt-all', action='store_true', help='records/ 모든 WAV에 대해 STT→CSV 일괄 처리')
    p.add_argument('--chunk-sec', type=float, default=5.0, help='STT 청크 길이(초). 기본 5.0')
    p.add_argument('--api-key', type=str, help='Google Speech Recognition API Key (선택)')
    p.add_argument('--debug', action='store_true', help='오류 발생 시 traceback 출력')
    return p.parse_args()


def main() -> None:
    args = parse_args()

    # 1) 장치 목록
    if args.list_devices:
        list_input_devices()
        return

    # 2) 수동 STT: 단일 파일
    if args.stt:
        try:
            csv_path = stt_google_chunked_to_csv(
                wav_path=Path(args.stt),
                chunk_sec=float(args.chunk_sec or 5.0),
                api_key=args.api_key,
            )
            log_info(f'STT 완료 → {csv_path}')
        except Exception as e:
            log_error(f'STT 실패: {e}')
            if args.debug:
                traceback.print_exc()
            sys.exit(3)
        return

    # 3) 수동 STT: 일괄
    if args.stt_all:
        ok, fail = 0, 0
        for wavp in list_record_files():
            try:
                csv_path = stt_google_chunked_to_csv(
                    wav_path=wavp,
                    chunk_sec=float(args.chunk_sec or 5.0),
                    api_key=args.api_key,
                )
                print(f'[OK] {wavp.name} → {csv_path.name}')
                ok += 1
            except Exception as e:
                print(f'[FAIL] {wavp.name} → {e}', file=sys.stderr)
                if args.debug:
                    traceback.print_exc()
                fail += 1
        print(f'\n완료: 성공 {ok} / 실패 {fail}')
        return

    # 4) 기본: 녹음 → 자동 STT
    # 장치 선택
    try:
        device_index = pick_device_index(args.device) if args.device else None
    except Exception as e:
        log_error(f'장치 선택 오류: {e}')
        if args.debug:
            traceback.print_exc()
        sys.exit(1)

    # 녹음
    try:
        wav_path = record_audio(
            device_index=device_index,
            samplerate=args.samplerate or 16000,
            channels=args.channels or 1,
            duration=args.duration,
        )
    except Exception as e:
        log_error(f'녹음 실패: {e}')
        if args.debug:
            traceback.print_exc()
        sys.exit(2)

    # 자동 STT
    try:
        log_auto('녹음 종료 → STT 수행 중...')
        csv_path = stt_google_chunked_to_csv(
            wav_path=wav_path,
            chunk_sec=float(args.chunk_sec or 5.0),
            api_key=args.api_key,
        )
        log_auto(f'CSV 저장 완료 → {csv_path}')
    except Exception as e:
        log_auto_err(str(e))
        if args.debug:
            traceback.print_exc()
        sys.exit(3)


if __name__ == '__main__':
    main()
