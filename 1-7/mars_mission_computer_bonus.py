import random
import time

class DummySensor:
    def __init__(self):
        self.env_values = {
            'mars_base_internal_temperature': 0.0,
            'mars_base_external_temperature': 0.0,
            'mars_base_internal_humidity': 0.0,
            'mars_base_external_illuminance': 0.0,
            'mars_base_internal_co2': 0.0,
            'mars_base_internal_oxygen': 0.0
        }

    def set_env(self):
        self.env_values['mars_base_internal_temperature'] = random.uniform(18.0, 30.0)
        self.env_values['mars_base_external_temperature'] = random.uniform(0.0, 21.0)
        self.env_values['mars_base_internal_humidity'] = random.uniform(50.0, 60.0)
        self.env_values['mars_base_external_illuminance'] = random.uniform(500.0, 715.0)
        self.env_values['mars_base_internal_co2'] = random.uniform(0.02, 0.1)
        self.env_values['mars_base_internal_oxygen'] = random.uniform(4.0, 7.0)

    def get_env(self):
        return self.env_values

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

            # 출력
            print('📡 현재 환경 정보:')
            print('{')
            for key in self.env_values:
                value = self.env_values[key]
                print(f'  "{key}": {value:.3f}')
                self.history[key].append(value)  # 누적 저장/해당 key의 list를 꺼내고 그 list에 value 값 저장
            print('}')

            count += 1 #반복문 도는 횟수 카운트
            time.sleep(5)

            # 5분(=300초 = 60회)마다 평균값 출력
            #1분(=60초=12회)
            if count % 12 == 0: #빠른 시연 위해 1분으로 설정, 후에 count % 60 == 0 으로 변경
                print('\n🧮 최근 1분간 평균값:') #빠른 시연 위해 1분으로 설정. 후에 5분으로 변경
                print('{')
                for key in self.history:
                    values = self.history[key][-12:]  # 최근 12개만 사용/ 뒤에서부터 셀 때 - 사용/5분으로 변경시 [-60:]
                    avg = sum(values) / len(values)
                    print(f'  "{key}": {avg:.3f}') #각 key값들의 평균 json형식으로 출력
                print('}')

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

