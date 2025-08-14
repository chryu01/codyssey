import os

def caesar_cipher_decode(target_text):  # parameter를 target_text로 설정
    decoded_results = []
    for shift in range(26):  # 알파벳 수만큼
        decoded = ""
        for char in target_text:
            if 'A' <= char <= 'Z':  # 대문자 처리 (현재는 사용 X)
                decoded += chr((ord(char) - ord('A') - shift) % 26 + ord('A'))
            elif 'a' <= char <= 'z':
                decoded += chr((ord(char) - ord('a') - shift) % 26 + ord('a'))
            else:
                decoded += char  # 공백, 특수문자는 그대로
        decoded_results.append((shift, decoded))
        print(f"[{shift}] {decoded}\n")
    return decoded_results

def main():
    # py 파일이 있는 폴더 기준으로 password.txt 경로 만들기
    base_dir = os.path.dirname(os.path.abspath(__file__))
    password_path = os.path.join(base_dir, "password.txt")

    try:
        with open(password_path, "r", encoding="utf-8") as f:
            encrypted_text = f.read().strip()
    except FileNotFoundError:
        print(f"Error: '{password_path}' 파일을 찾을 수 없습니다.")
        return
    except Exception as e:
        print(f"파일을 읽는 도중 오류가 발생했습니다: {e}")
        return

    decoded_results = caesar_cipher_decode(encrypted_text)

    try:
        shift_choice = int(input("어느 자리수(shift)가 제대로 해독된 것으로 보입니까? 숫자를 입력하세요 (0~25): "))
        if 0 <= shift_choice < 26:
            result_text = decoded_results[shift_choice][1]
            result_path = os.path.join(base_dir, "result.txt")
            try:
                with open(result_path, "w", encoding="utf-8") as f:
                    f.write(result_text)
                print(f"'{result_path}'에 저장되었습니다. (shift: {shift_choice})")
            except Exception as e:
                print(f"파일을 저장하는 도중 오류가 발생했습니다: {e}")
        else:
            print("유효하지 않은 숫자입니다. 프로그램을 종료합니다.")
    except ValueError:
        print("숫자가 입력되지 않았습니다. 프로그램을 종료합니다.")

if __name__ == "__main__":
    main()
