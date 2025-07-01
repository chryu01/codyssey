import json

def read_and_parse_log(file_path):
    """
    로그 파일을 읽어 각 줄을 리스트로 파싱하고 반환
    """
    parsed_list = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:       
            for line in f:
                parts = line.strip().split(",", maxsplit=2)  #line.strip를 하는 이유는,를 기준으로 파트를 나누기 위해서 + maxsplit는 앞부분부터 2개의 ,만 분리의 기준으로 삼고 나머지는 문자 취급한다는 것(.split 함수의 리턴값은 무조건 list임)
                if len(parts) == 3:       #list로 변환된 part가 [a,b,c]처럼 3개로 나누어지면(설정하고자 했던 기준과 동일)
                    parsed_list.append(parts)       #제대로 나뉜 것이라 판단하여 list로 추가함. list안에 각 줄이 list 형태의 요소로 저장되는 것
                else:
                    print("⚠️ 형식 오류:", line)
        return parsed_list
    except Exception as e:
        print("❌ 파일 처리 중 오류:", e)
        return []

def convert_list_to_dict(parsed_list):
    """
    리스트 객체를 dict 형식으로 변환
    키: timestamp, 값: {event, message}
    """
    result_dict = {}
    for entry in parsed_list:          #list를 한 요소별로 불러와서 분석
        timestamp, event, message = entry
        result_dict[timestamp] = {       #timestamp를 key값으로/event, message를 value로 지정해서 dict 만드는것
            "event": event,
            "message": message
        }                                       #dict는 재선언할 때마다 자동으로 추가됨. 굳이 append를 할 필요 없음(만약 동일한 key값이 주어지면 가장 최신 값으로 덮어쓰기 됨)
    return result_dict

def save_dict_to_json(data_dict, output_path): #output_path는 저장하고자 하는 json파일의 이름을 포함한 경로
    """
    dict 객체를 JSON 파일로 저장
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f: #"w"는 write_새로덮어쓰기/"r"는 read/"a"는 all_불러와서 이어쓰기 + as f에서 f는 변수명
            json.dump(data_dict, f, ensure_ascii=False, indent=4) #.dump는 import해온 json안에 있는 변환하는 함수 + ensure_ascii=False: 한글은 그대로 한글로 저장 + indent는 들여쓰기(dict 가독성을 위해)
        print(f"✅ JSON 파일 저장 완료: {output_path}")  #저장 경로 출력 print(f)는 문자열 프린트 방식 중 하나
    except Exception as e:
        print(f"❌ JSON 저장 중 오류: {e}")

if __name__ == "__main__":      #코드를 다른 곳에서 import했을 때 바로 이 코드들이 실행되지 않도록 막아주는 역할.
    log_path = "mission_computer_main.log"
    json_output_path = "mission_computer_main.json" #python 스크립트 실행 폴더를 기준으로 같은 폴더 안에 있을 경우 경로 생략 가능

    # 1. 파일 읽고 리스트로 파싱
    parsed = read_and_parse_log(log_path)

    # 2. 파싱된 리스트 출력
    print("📋 파싱된 리스트 출력:")
    for row in parsed:  
        print(row)

    # 3. 시간 기준 역순 정렬
    parsed_sorted = sorted(parsed, key=lambda x: x[0], reverse=True) #sorted는 파이썬 자체 함수. 따로 선언 필요X (sorted는 원본 변경X/sort는 원본도 변경됨)

    '''
    key=lambda x: x[0]는 정렬 기준은 리스트 안의 각 요소 첫번째 값이라는 뜻
    lambda는 익명함수/한 줄 함수.
     -> 간단하게 사용 가능한 일회용 함수
    '''

    # 4. 리스트 → dict 전환
    log_dict = convert_list_to_dict(parsed_sorted)

    # 5. dict → JSON 파일로 저장
    save_dict_to_json(log_dict, json_output_path)   #위에서 json_output_path 변수 지정해놓음