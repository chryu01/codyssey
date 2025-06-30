print('Hello Mars')

'''
# 파일 열고 한 줄씩 출력
with open("mission_computer_main.log", "r", encoding="utf-8") as f:
    for line in f:
        print(line.strip())
'''


# main.py

def read_log_file(file_path):        # file_path는 "매개변수(parameter)"
    """
    로그 파일을 읽어서 한 줄씩 화면에 출력하는 함수.
    파일이 없거나 문제가 생기면 오류 메시지를 보여줌.
    """
    try:
        with open("mission_computer_main.log", "r", encoding="utf-8") as f:
            for line in f:
                print(line.strip())  # 줄바꿈 제거 후 출력
    except FileNotFoundError:
        print("❌ 파일을 찾을 수 없습니다. 경로를 다시 확인해주세요.")
    except UnicodeDecodeError:
        print("❌ 파일을 읽는 도중 인코딩 문제가 발생했습니다. 'cp949' 인코딩으로 다시 시도해보세요.")
    except Exception as e:
        print(f"❌ 알 수 없는 오류가 발생했습니다: {e}")

read_log_file("mission_computer_main.log")