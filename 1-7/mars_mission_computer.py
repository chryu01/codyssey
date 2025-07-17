#mars_mission_computer

import random
import time  # 시간 라이브러리
import json

from P06_mars_mission_computer import DummySensor

ds = DummySensor() #DummySensor ds로 인스턴스화

class MissionComputer:
    def __init__(self):
        self.env_values = {
            'mars_base_internal_temperature': 0.0,
            'mars_base_external_temperature': 0.0,
            'mars_base_internal_humidity': 0.0,
            'mars_base_external_illuminance': 0.0,
            'mars_base_internal_co2': 0.0,
            'mars_base_internal_oxygen': 0.0
        }
        self.sensor = ds #MissionComputer 클래스 안에서 DummySensor를 사용할 수 있게 연결해주는 역할

    def get_sensor_data(self):
        while True:
            self.sensor.set_env()
            self.env_values = self.sensor.get_env()

            print('📡 환경 정보:')

            
        
            rounded_env_values = {
                key: round(value, 3) if isinstance(value, (int, float)) else value
                 for key, value in self.env_values.items()
                }

            print(json.dumps(rounded_env_values, indent=4))

            '''
            print('{')
            for key in self.env_values:
                value = self.env_values[key]
                print(f'  "{key}": {value:.3f}') #json 형식에 맞추기 위해 {} 출력 및 ""출력
            print('}\n')
            '''

            time.sleep(5)  #5초마다 반복


if __name__ == '__main__':
    RunComputer = MissionComputer() #RunComputer로 인스턴스화
    RunComputer.get_sensor_data() 
