import itertools
import string
import time
import zipfile
import multiprocessing
import os
from datetime import datetime

# 설정
ZIP_FILE = 'emergency_storage_key.zip'
PASSWORD_OUTPUT = 'password.txt'
PASSWORD_LENGTH = 6
CHARSET = string.ascii_lowercase + string.digits  # 소문자 + 숫자

# 공유 변수 (멀티프로세싱-safe)
found_password = multiprocessing.Value('b', False)
attempts = multiprocessing.Value('i', 0)

def try_password(zip_path, password, found_flag):
    if found_flag.value:
        return
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(pwd=password.encode('utf-8'))
        # 성공
        with open(PASSWORD_OUTPUT, 'w') as f:
            f.write(password)
        print(f"\n✅ Password found: {password}")
        found_flag.value = True
    except:
        pass  # 실패한 경우

def worker(start_chars, zip_path, found_flag, counter):
    for prefix in start_chars:
        if found_flag.value:
            break
        for comb in itertools.product(CHARSET, repeat=PASSWORD_LENGTH - len(prefix)):
            if found_flag.value:
                break
            password = prefix + ''.join(comb)
            try_password(zip_path, password, found_flag)
            with counter.get_lock():
                counter.value += 1

def unlock_zip():
    zip_path = ZIP_FILE
    print(f"🔐 Starting password cracking for: {zip_path}")
    start_time = time.time()

    cpu_count = multiprocessing.cpu_count()
    print(f"🧠 Using {cpu_count} processes...")

    # 시작 글자 기준으로 나누기 (예: a, b, c...z, 0~9)
    start_chars = list(CHARSET)
    split_prefixes = [[] for _ in range(cpu_count)]
    for idx, ch in enumerate(start_chars):
        split_prefixes[idx % cpu_count].append(ch)

    # 프로세스 시작
    processes = []
    for i in range(cpu_count):
        p = multiprocessing.Process(target=worker,
                                    args=(split_prefixes[i], zip_path, found_password, attempts))
        p.start()
        processes.append(p)

    # 진행 상황 출력
    try:
        while True:
            if found_password.value:
                break
            elapsed = time.time() - start_time
            print(f"⏱️ {int(attempts.value)} attempts | Elapsed: {int(elapsed)} sec", end='\r')
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user.")
        found_password.value = True

    for p in processes:
        p.terminate()
    for p in processes:
        p.join()

    if not found_password.value:
        print("\n❌ Password not found.")
    else:
        print(f"\n📁 Password saved to {PASSWORD_OUTPUT}")
        print(f"⏳ Total time: {int(time.time() - start_time)} seconds")

if __name__ == '__main__':
    unlock_zip()
