import platform #운영체제(OS), CPU 등에 대한 정보를 얻을 수 있는 표준 라이브러리
import os #운영체제 관련 함수들 (예: CPU 개수 등)
import json # 딕셔너리를 JSON 형식으로 보기 좋게 출력하기 위한 표준 라이브러리

from P06_mars_mission_computer import DummySensor

try:
    import psutil  # 시스템 정보 수집용으로 예외적으로 허용된 라이브러리(설치 여부 확인하는 과정)
except ImportError:
    print("⚠️ psutil 모듈이 설치되어 있지 않습니다. 시스템 부하 정보를 가져올 수 없습니다.")
    psutil = None

ds = DummySensor() #DummySensor ds로 인스턴스화

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

    #여기부터 추가하는 메소드!!
    def get_mission_computer_info(self): #메소드 이름 get_mission_computer_info
        try:
            info = {
                "Operating System": platform.system(), #운영체계 이름을 문자열로
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
