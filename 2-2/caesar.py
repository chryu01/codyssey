def caesar_cipher_decode(target_text): #parameter를 target_txt로 설정
    decoded_results = []
    for shift in range(26):  # 알파벳 수만큼
        decoded = ""
        for char in target_text:
            if 'A' <= char <= 'Z': #지금 당장은 사용 X. 훗날 다른 암호문 다룰 수 있는 경우 때문에 작성한 부분
                decoded += chr((ord(char) - ord('A') - shift) % 26 + ord('A'))
            elif 'a' <= char <= 'z':
                decoded += chr((ord(char) - ord('a') - shift) % 26 + ord('a'))
                #ord(char)는 문자를 유니코드/아스키코드로 변환.
                #변환한 문자와 기준이 되는 'a' 사이의 거리를 측정하기 위해 뺄셈 사용
                # 알파벳을 왼쪽으로 shift만큼 이동시켜야 하니까 - shift 사용 후 %26(모두 연산)
                #+ord('a')는 다시 문자로 바꿔줄 때, a부터 시작하는 알파벳 코드 값으로 변환하기 위함
            else:
                decoded += char  # 공백이나 특수기호는 그대로
        decoded_results.append((shift, decoded))
        print(f"[{shift}] {decoded}\n")
    return decoded_results

def main():
    try:
        with open("password.txt", "r", encoding="utf-8") as f:
            encrypted_text = f.read().strip() #실제 인자는 encrypted_text로 설정
    except FileNotFoundError:
        print("Error: 'password.txt' 파일을 찾을 수 없습니다.")
        return
    except Exception as e:
        print(f"파일을 읽는 도중 오류가 발생했습니다: {e}")
        return

    decoded_results = caesar_cipher_decode(encrypted_text)

    try:
        shift_choice = int(input("어느 자리수(shift)가 제대로 해독된 것으로 보입니까? 숫자를 입력하세요 (0~25): "))
        if 0 <= shift_choice < 26:
            result_text = decoded_results[shift_choice][1]
            try:
                with open("result.txt", "w", encoding="utf-8") as f:
                    f.write(result_text)
                print(f"'result.txt'에 저장되었습니다. (shift: {shift_choice})")
            except Exception as e:
                print(f"파일을 저장하는 도중 오류가 발생했습니다: {e}")
        else:
            print("유효하지 않은 숫자입니다. 프로그램을 종료합니다.")
    except ValueError:
        print("숫자가 입력되지 않았습니다. 프로그램을 종료합니다.")

if __name__ == "__main__":
    main()
