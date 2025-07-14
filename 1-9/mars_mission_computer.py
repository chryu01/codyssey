import platform #운영체제(OS), CPU 등에 대한 정보를 얻을 수 있는 표준 라이브러리
import os #운영체제 관련 함수들 (예: CPU 개수 등)
import json # 딕셔너리를 JSON 형식으로 보기 좋게 출력하기 위한 표준 라이브러리
import random
import time
import threading
import multiprocessing

try:
    import psutil  # 시스템 정보 수집용으로 예외적으로 허용된 라이브러리(설치 여부 확인하는 과정)
except ImportError:
    print("⚠️ psutil 모듈이 설치되어 있지 않습니다. 시스템 부하 정보를 가져올 수 없습니다.")
    psutil = None

class DummySensor:  #따로 써야 한다는 조건은 없었지만..문제7의 MissionComputer class를 사용하기 위해서는 ds가 사용될 수밖에 없어서
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

ds = DummySensor() #DummySensor ds로 인스턴스화

class MissionComputer: #class 생성
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

            # 소수점 3자리로 반올림한 새 딕셔너리 생성(round함수 사용)
            #isinstance(값, 자료형)로 특정 자료형인지 확인/int, float인 경우 소수3자리로 반올림. 그렇지 않을 경우 그대로 사용
            #dict.items()는 딕셔너리 순회 도구
            rounded_env_values = {
                key: round(value, 3) if isinstance(value, (int, float)) else value
                 for key, value in self.env_values.items()
                }

            print(json.dumps(rounded_env_values, indent=4))

            time.sleep(5)  #5초마다 반복

    #여기부터 추가하는 메소드!!
    def get_mission_computer_info(self): #메소드 이름 get_mission_computer_info
        try:
            info = {
                "Operating System": platform.system(), #운영체계
                "OS Version": platform.version(), #운영체계 버전
                "CPU Type": platform.processor(), #CPU의 타입
                "CPU Cores": os.cpu_count(), #CPU의 코어 수
                "Total Memory (GB)": round(psutil.virtual_memory().total / (1024 ** 3), 2) if psutil else "Unavailable"  #메모리의 크기
            }

            print("🖥️ Mission Computer Info:")
            print(json.dumps(info, indent=4))
            return info

        except Exception as e:
            print("❌ 시스템 정보를 가져오는 도중 오류가 발생했습니다:", str(e))
            return {}

    #컴퓨터에 부하를 일으키는 코드
    def get_mission_computer_load(self):
        try:
            if psutil is None:
                raise ImportError("psutil 모듈이 없어서 부하 정보를 가져올 수 없습니다.")

            load = {
                "CPU Usage (%)": psutil.cpu_percent(interval=1),    #CPU의 실시간 용량
                "Memory Usage (%)": psutil.virtual_memory().percent #메모리의 실시간 용량
            }

            print("📊 Mission Computer Load:")
            print(json.dumps(load, indent=4))
            return load

        except Exception as e:
            print("❌ 시스템 부하 정보를 가져오는 도중 오류가 발생했습니다:", str(e))
            return {}

# 인스턴스 생성 및 실행
if __name__ == "__main__":
    runComputer = MissionComputer() #인스턴스화
    runComputer.get_mission_computer_info()
    runComputer.get_mission_computer_load()