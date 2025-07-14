import platform
import os
import json

try:
    import psutil  # 시스템 정보 수집용으로 예외적으로 허용
except ImportError:
    print("⚠️ psutil 모듈이 설치되어 있지 않습니다. 시스템 부하 정보를 가져올 수 없습니다.")
    psutil = None

class MissionComputer:
    def get_mission_computer_info(self):
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
            return info

        except Exception as e:
            print("❌ 시스템 정보를 가져오는 도중 오류가 발생했습니다:", str(e))
            return {}

    def get_mission_computer_load(self):
        try:
            if psutil is None:
                raise ImportError("psutil 모듈이 없어서 부하 정보를 가져올 수 없습니다.")

            load = {
                "CPU Usage (%)": psutil.cpu_percent(interval=1),
                "Memory Usage (%)": psutil.virtual_memory().percent
            }

            print("📊 Mission Computer Load:")
            print(json.dumps(load, indent=4))
            return load

        except Exception as e:
            print("❌ 시스템 부하 정보를 가져오는 도중 오류가 발생했습니다:", str(e))
            return {}

# 인스턴스 생성 및 실행
if __name__ == "__main__":
    runComputer = MissionComputer()
    runComputer.get_mission_computer_info()
    runComputer.get_mission_computer_load()
