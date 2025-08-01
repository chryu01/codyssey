# mars_mission_computer.py

import random

#관련된 데이터(변수)와 함수(기능)를 하나의 단위로 묶은 것이 class
class DummySensor:
    #__init__: 객체가 처음 만들어질 때 자동으로 실행되는 함수(생성자 함수, constructor)
    def __init__(self): #self: 클래스로 만든 객체가 자기 자신의 데이터에 접근할 수 있게 해주는 키워드 (메소드의 첫번째 인자)
        #env_values라는 사전객체 만들기
        #self.변수명=값 : 객체 자체 안에 저장되는 변수 (인스턴스 변수)
        self.env_values = { 
            'mars_base_internal_temperature': 0.0,
            'mars_base_external_temperature': 0.0,
            'mars_base_internal_humidity': 0.0,
            'mars_base_external_illuminance': 0.0,
            'mars_base_internal_co2': 0.0,
            'mars_base_internal_oxygen': 0.0
        }

    #random하게 값을 받더라도 범위를 지정해줘야 해서
    #객체의 env_values라는 dict. 그 dict의 ['키']에 특정 범위의 값을 넣겠다!!
    def set_env(self):
        self.env_values['mars_base_internal_temperature'] = random.uniform(18.0, 30.0)
        self.env_values['mars_base_external_temperature'] = random.uniform(0.0, 21.0)
        self.env_values['mars_base_internal_humidity'] = random.uniform(50.0, 60.0)
        self.env_values['mars_base_external_illuminance'] = random.uniform(500.0, 715.0)
        self.env_values['mars_base_internal_co2'] = random.uniform(0.02, 0.1)
        self.env_values['mars_base_internal_oxygen'] = random.uniform(4.0, 7.0)

    #랜덤으로 배정된 그 값이 담긴 env_values를 불러오는 함수
    def get_env(self):
        return self.env_values


# 인스턴스 생성 및 테스트
if __name__ == '__main__': #이 코드 파일에서만 실행되도록. 다른 코드 파일에서 DummySensor를 돌리면 이 아래부터는 안 돌아가도록!
    ds = DummySensor() #인스턴스: 클래스를 실제로 사용해서 만든 ‘실체’
    ds.set_env()
    env_data = ds.get_env()

    print('📡 Dummy Sensor Environmental Data')
    for key in env_data:
        print(f'{key}: {env_data[key]:.3f}') #{env_data[key]:.3f}는 env_data에서 key에 해당하는 값 (소숫점 3자리까지)
