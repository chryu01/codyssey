import zipfile                 # ZIP 파일을 열고 읽는 기능을 제공하는 파이썬 기본 라이브러리
import itertools               # 모든 가능한 조합/순열 등을 만들어주는 라이브러리
import string                  # 알파벳, 숫자 등 문자 집합을 쉽게 불러올 수 있게 해주는 라이브러리
import time                    # 시간 측정 및 대기 기능 제공
import multiprocessing         # CPU 여러 개를 동시에 사용하는 병렬 처리 기능
from datetime import datetime  # 날짜와 시간 형식을 편하게 다루기 위한 라이브러리
import io                      # 메모리에서 파일처럼 다룰 수 있게 해주는 라이브러리
import os                      # 운영체제 기능(폴더 이동, 경로 처리 등)을 사용하기 위한 라이브러리

# === CONFIGURATION ===
ZIP_FILE = 'emergency_storage_key.zip'  # 열고 싶은 ZIP 파일 이름 (확장자까지 정확히 입력)
PASSWORD_OUTPUT = 'password.txt'        # 비밀번호를 찾으면 저장할 텍스트 파일 이름
PASSWORD_LENGTH = 6                     # 비밀번호 길이 (6자리)
CHARS = list(string.ascii_lowercase + string.digits)  # 사용할 문자: 소문자 + 숫자 → 총 36개
CPU_COUNT = multiprocessing.cpu_count() # 내 컴퓨터 CPU 코어 개수 확인

# === ZIP 파일을 메모리에 올리는 함수 ===
def load_zip_bytes(zip_path):
    # zip_path: 열고 싶은 ZIP 파일 경로
    with open(zip_path, 'rb') as f:  # ZIP 파일을 '읽기 전용' + '바이너리 모드'로  열기
        return f.read()              # 파일 내용을 그대로 읽어서 메모리에 저장 (바이트 형태)

# === 비밀번호를 시험하는 함수 ===
def try_password(zip_bytes, password):
    try:
        # 메모리에 올려둔 ZIP 데이터를 파일처럼 열기
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.setpassword(password.encode('utf-8'))  # 비밀번호를 바이트 형태로 설정
            # testzip() → 압축 해제가 가능한지 테스트
            # None이면 모든 파일이 정상 해제 가능 → 비밀번호 맞음
            return zf.testzip() is None
    except:
        # 잘못된 비밀번호이거나 에러 발생 시 False 반환
        return False

# === 실제로 비밀번호 조합을 시도하는 작업자 함수 ===
def worker(prefixes, zip_bytes, found_flag, result, counter):
    local_count = 0  # 이 작업자가 시도한 횟수를 저장
    for prefix in prefixes:  # 이 작업자가 맡은 접두사 목록에서 하나씩 꺼내기
        if found_flag.value:  # 이미 다른 작업자가 비밀번호를 찾았다면 중단
            break
        suffix_len = PASSWORD_LENGTH - len(prefix)  # 나머지 자리 수 계산
        # 나머지 자리 수만큼 가능한 모든 조합 만들기
        for combo in itertools.product(CHARS, repeat=suffix_len):
            if found_flag.value:  # 다른 작업자가 찾았다면 즉시 중단j
                break
            password = prefix + ''.join(combo)  # 접두사 + 나머지 글자 조합으로 비밀번호 생성
            if try_password(zip_bytes, password):  # 이 비밀번호로 열어보기
                found_flag.value = True           # 성공 시, 모든 작업자에게 중지 신호
                result.put(password)              # 찾은 비밀번호를 중앙 저장소(큐)에 넣기
                return                            # 함수 종료
            local_count += 1
            if local_count % 10000 == 0:          # 1만 번 시도할 때마다
                with counter.get_lock():          # 공유 변수(counter)를 안전하게 잠금
                    counter.value += 10000        # 누적 시도 횟수 업데이트
    # 마지막 남은 시도 횟수 더해주기 (1만 단위에 못 미친 나머지)
    with counter.get_lock():
        counter.value += local_count % 10000

# === 전체 브루트포스 과정을 관리하는 함수 ===
def unlock_zip():
    # 현재 스크립트가 있는 폴더로 이동 (Windows에서 경로 문제 방지)
    os.chdir(os.path.dirname(__file__))

    # ZIP 파일을 메모리로 읽기
    zip_bytes = load_zip_bytes(ZIP_FILE)

    # 접두사(앞 2자리) 모든 조합 생성 (36^2 = 1296개)
    prefix_len = 2
    all_prefixes = [''.join(p) for p in itertools.product(CHARS, repeat=prefix_len)]

    # 코어 수에 맞게 접두사 목록을 균등하게 나누기
    chunk_size = (len(all_prefixes) + CPU_COUNT - 1) // CPU_COUNT

    # 멀티프로세싱에서 공유할 변수들 준비
    found_flag = multiprocessing.Value('b', False)  # 비밀번호 찾았는지 여부
    counter = multiprocessing.Value('i', 0)         # 전체 시도 횟수
    result = multiprocessing.Queue()                # 찾은 비밀번호 저장 큐
    processes = []                                   # 작업자 목록

    print(f"🔐 Brute-force 시작! 프로세스 수: {CPU_COUNT}개 — {datetime.now().strftime('%H:%M:%S')}")

    # CPU 코어 수만큼 프로세스를 만들어서 실행
    for i in range(CPU_COUNT):
        chunk = all_prefixes[i * chunk_size:(i + 1) * chunk_size]  # 이 프로세스가 맡을 접두사 목록
        p = multiprocessing.Process(target=worker, args=(chunk, zip_bytes, found_flag, result, counter))
        processes.append(p)  # 작업자 목록에 추가
        p.start()            # 작업자 시작

    start = time.time()  # 시작 시각 기록

    try:
        # 비밀번호를 찾을 때까지 진행 상황 출력
        while not found_flag.value:
            time.sleep(5)  # 5초마다
            print(f"[⏱ {int(time.time() - start)}s] 시도 횟수: {counter.value}")
    except KeyboardInterrupt:
        # 사용자가 Ctrl+C로 중단한 경우
        print("\n⛔ 사용자 중단. 모든 프로세스를 종료합니다...")
        for p in processes:
            p.terminate()  # 모든 작업자 종료
        return

    # 모든 프로세스가 끝날 때까지 대기
    for p in processes:
        p.join()

    # 결과가 있다면 파일에 저장
    if not result.empty():
        password = result.get()
        with open(PASSWORD_OUTPUT, 'w') as f:
            f.write(password)
        print(f"\n✅ 비밀번호 찾음: {password}")
    else:
        print("❌ 비밀번호를 찾지 못했습니다.")

    # 종료 시각과 총 시도 횟수 출력
    print(f"🏁 종료 시간: {datetime.now().strftime('%H:%M:%S')} — 총 시도 횟수: {counter.value}")

# === 프로그램 시작 지점 (Windows 멀티프로세스 안전) ===
if __name__ == '__main__':
    multiprocessing.freeze_support()  # Windows에서 멀티프로세스 실행 시 필수
    unlock_zip()  # 프로그램 실행
