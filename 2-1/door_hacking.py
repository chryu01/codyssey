import itertools
import string
import time
import zipfile
import multiprocessing
from datetime import datetime

# 설정
ZIP_FILE = 'emergency_storage_key.zip' #열고자 하는 zip 파일
PASSWORD_OUTPUT = 'password.txt' #이후에 저장되는 결과 이름
PASSWORD_LENGTH = 6 #비밀번호 자리수
CHARSET = string.ascii_lowercase + string.digits  # 대문자도 소문자로 변환! 소문자+숫자

# 공유 변수 (멀티프로세싱-safe)
found_password = multiprocessing.Value('b', False)
attempts = multiprocessing.Value('i', 0)

def try_password(zip_path, password, found_flag):
    if found_flag.value:
        return
    try:
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(pwd=password.encode('utf-8'))
        with open(PASSWORD_OUTPUT, 'w') as f:
            f.write(password)
        print(f"\n✅ Password found: {password}")
        found_flag.value = True
    except:
        pass

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

    # 대소문자 및 숫자를 기준으로 그룹 분할
    group1 = [ch for ch in CHARSET if 'A' <= ch <= 'L' or 'a' <= ch <= 'l']
    group2 = [ch for ch in CHARSET if 'M' <= ch <= 'Z' or 'm' <= ch <= 'z']
    group3 = [ch for ch in CHARSET if ch.isdigit()]  # '0' ~ '9'

    start_groups = [group1, group2, group3]

    processes = []
    for i in range(3):
        p = multiprocessing.Process(
            target=worker,
            args=(start_groups[i], zip_path, found_password, attempts)
        )
        p.start()
        processes.append(p)

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
