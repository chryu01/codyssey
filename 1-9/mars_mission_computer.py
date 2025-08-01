import platform
import os
import json
import random
import time
import threading
import multiprocessing

try:
    import psutil
except ImportError:
    print("⚠️ psutil 모듈이 설치되어 있지 않습니다.")
    psutil = None

from P06_mars_mission_computer import DummySensor

ds = DummySensor()

class MissionComputer:
    def __init__(self):
        self.env_values = ds.get_env()
        self.sensor = ds

    def get_sensor_data(self):
        while True:
            self.sensor.set_env()
            self.env_values = self.sensor.get_env()
            rounded_env_values = {
                key: round(value, 3) if isinstance(value, (int, float)) else value
                for key, value in self.env_values.items()
            }
            print("📡 Sensor Data:")
            print(json.dumps(rounded_env_values, indent=4))
            time.sleep(5)

    def get_mission_computer_info(self):
        while True:
            try:
                info = {
                    "Operating System": platform.system(),
                    "OS Version": platform.version(),
                    "CPU Type": platform.processor(),
                    "CPU Cores": os.cpu_count(),
                    "Total Memory (GB)": round(psutil.virtual_memory().total / (1024 ** 3), 2) if psutil else "Unavailable"
                }
                print("🖥️ Mission Computer Info:")
                print(json.dumps(info, indent=4))
            except Exception as e:
                print("❌ 시스템 정보 오류:", str(e))
            time.sleep(20) #20초에 한번씩 출력

    def get_mission_computer_load(self):
        while True:
            try:
                if psutil is None:
                    raise ImportError("psutil 모듈 없음.")
                load = {
                    "CPU Usage (%)": psutil.cpu_percent(interval=1),
                    "Memory Usage (%)": psutil.virtual_memory().percent
                }
                print("📊 Mission Computer Load:")
                print(json.dumps(load, indent=4))
            except Exception as e:
                print("❌ 시스템 부하 오류:", str(e))
            time.sleep(20)  #20초에 한번씩 출력

# ---------- 멀티스레드 실행 ----------
def run_threads():
    runComputer = MissionComputer()
    t1 = threading.Thread(target=runComputer.get_mission_computer_info)
    t2 = threading.Thread(target=runComputer.get_mission_computer_load)
    t3 = threading.Thread(target=runComputer.get_sensor_data)
    t1.start()
    t2.start()
    t3.start()
    t1.join()
    t2.join()
    t3.join()

# ---------- 멀티프로세스 실행 ----------
def run_info():
    MissionComputer().get_mission_computer_info()

def run_load():
    MissionComputer().get_mission_computer_load()

def run_sensor():
    MissionComputer().get_sensor_data()

def run_processes():
    p1 = multiprocessing.Process(target=run_info)
    p2 = multiprocessing.Process(target=run_load)
    p3 = multiprocessing.Process(target=run_sensor)
    p1.start()
    p2.start()
    p3.start()
    p1.join()
    p2.join()
    p3.join()

# ---------- 메인 ----------
if __name__ == "__main__":
    print("=== [1] 멀티스레드 실행 (1개 인스턴스) ===")
    threading.Thread(target=run_threads).start()

    time.sleep(3)  # 구분을 위한 대기

    print("\n=== [2] 멀티프로세스 실행 (3개 인스턴스) ===")
    multiprocessing.set_start_method("spawn")  # Windows 안전용
    run_processes()
