import random
import time
import json

from P06_mars_mission_computer import DummySensor

ds = DummySensor()

class MissionComputer:
    def __init__(self):
        self.sensor = ds
        self.env_values = {key: 0.0 for key in ds.env_values}
        self.history = {key: [] for key in self.env_values}  # key : []로 누적값 저장할 dict생성

    def get_sensor_data(self):
        count = 0 #반복 횟수 카운트 위해 count변수 설정
        while True:

            # 센서 값 수집 및 저장
            self.sensor.set_env()
            self.env_values = self.sensor.get_env()

            for key in self.env_values:
                self.history[key].append(self.env_values[key])


            # 출력
            print('📡 현재 환경 정보:')
            rounded_env_values = {
                key: round(value, 3) if isinstance(value, (int, float)) else value
                 for key, value in self.env_values.items()
                }

            print(json.dumps(rounded_env_values, indent=4))

            count += 1 #반복문 도는 횟수 카운트
            time.sleep(5)

            # 5분(=300초 = 60회)마다 평균값 출력
            #1분(=60초=12회)
            if count % 12 == 0: #빠른 시연 위해 1분으로 설정, 후에 count % 60 == 0 으로 변경
                print('\n🧮 최근 1분간 평균값:') #빠른 시연 위해 1분으로 설정. 후에 5분으로 변경
                averaged_values = {}

                for key in self.history:
                    values = self.history[key][-12:]  # 최근 12개만 사용(5분일 경우 60)
                    if values:  # 리스트가 비어있지 않다면
                      avg = sum(values) / len(values)
                      averaged_values[key] = round(avg, 3)  # 소수점 3자리까지
                    else:  # 아직 값이 하나도 누적되지 않은 경우
                      averaged_values[key] = None  # 또는 'N/A', 0.0 등으로 대체 가능

                # JSON 형식으로 평균값 출력
                print(json.dumps(averaged_values, indent=4))

                print('\n▶ 계속하려면 Enter, 중지하려면 "stop" 입력:') #1분/5분에 한번 계속 이어갈지 멈출지 결정 가능
                try:
                    user_input = input() #input()에 try를 걸지 않으면 다른 행동 발생 시 오류 발생
                except:
                    user_input = ''

                if user_input.strip().lower() == 'stop': #대문자/소문자 상관없이 stop이면 break
                    print('System stopped...')
                    break

            


if __name__ == '__main__':
    RunComputer = MissionComputer()
    RunComputer.get_sensor_data()

