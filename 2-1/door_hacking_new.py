import zipfile
import itertools
import string
import time
import multiprocessing
from datetime import datetime
import io
import os

# === CONFIGURATION ===
ZIP_FILE = 'emergency_storage_key.zip'  # 열고자 하는 zip 파일 이름 (확장자 포함 정확히!)
PASSWORD_OUTPUT = 'password.txt'        # 비밀번호 저장 파일
PASSWORD_LENGTH = 6
CHARS = list(string.ascii_lowercase + string.digits)
CPU_COUNT = multiprocessing.cpu_count()

# === Load ZIP into memory (to avoid file I/O in every process) ===
def load_zip_bytes(zip_path):
    with open(zip_path, 'rb') as f:
        return f.read()

# === Try a password on in-memory zip bytes ===
def try_password(zip_bytes, password):
    try:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.setpassword(password.encode('utf-8'))
            return zf.testzip() is None  # testzip()이 None이면 성공적으로 압축 해제 가능
    except:
        return False

# === Worker Process ===
def worker(prefixes, zip_bytes, found_flag, result, counter):
    local_count = 0
    for prefix in prefixes:
        if found_flag.value:
            break
        suffix_len = PASSWORD_LENGTH - len(prefix)
        for combo in itertools.product(CHARS, repeat=suffix_len):
            if found_flag.value:
                break
            password = prefix + ''.join(combo)
            if try_password(zip_bytes, password):
                found_flag.value = True
                result.put(password)
                return
            local_count += 1
            if local_count % 10000 == 0:
                with counter.get_lock():
                    counter.value += 10000
    with counter.get_lock():
        counter.value += local_count % 10000

# === Brute-force Controller ===
def unlock_zip():
    # 현재 실행 중인 스크립트 위치로 작업 디렉토리 이동 (Windows에서 중요!)
    os.chdir(os.path.dirname(__file__))

    # ZIP 파일 메모리에 적재
    zip_bytes = load_zip_bytes(ZIP_FILE)

    # 접두사 조합 (예: ab, ac, ad, ..., zz, z9)
    prefix_len = 2
    all_prefixes = [''.join(p) for p in itertools.product(CHARS, repeat=prefix_len)]
    chunk_size = (len(all_prefixes) + CPU_COUNT - 1) // CPU_COUNT

    found_flag = multiprocessing.Value('b', False)
    counter = multiprocessing.Value('i', 0)
    result = multiprocessing.Queue()
    processes = []

    print(f"🔐 Brute-force 시작! 프로세스 수: {CPU_COUNT}개 — {datetime.now().strftime('%H:%M:%S')}")

    for i in range(CPU_COUNT):
        chunk = all_prefixes[i * chunk_size:(i + 1) * chunk_size]
        p = multiprocessing.Process(target=worker, args=(chunk, zip_bytes, found_flag, result, counter))
        processes.append(p)
        p.start()

    start = time.time()

    try:
        while not found_flag.value:
            time.sleep(5)
            print(f"[⏱ {int(time.time() - start)}s] 시도 횟수: {counter.value}")
    except KeyboardInterrupt:
        print("\n⛔ 사용자 중단. 모든 프로세스를 종료합니다...")
        for p in processes:
            p.terminate()
        return

    for p in processes:
        p.join()

    if not result.empty():
        password = result.get()
        with open(PASSWORD_OUTPUT, 'w') as f:
            f.write(password)
        print(f"\n✅ 비밀번호 찾음: {password}")
    else:
        print("❌ 비밀번호를 찾지 못했습니다.")

    print(f"🏁 종료 시간: {datetime.now().strftime('%H:%M:%S')} — 총 시도 횟수: {counter.value}")

# === Entry Point (Windows-safe) ===
if __name__ == '__main__':
    multiprocessing.freeze_support()  # Windows 실행 시 필수!
    unlock_zip()
