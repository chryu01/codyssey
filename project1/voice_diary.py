import sys              # 프로그램 실행 및 종료, 명령줄 인자 처리에 필요
import wave             # WAV 오디오 파일을 읽고 쓰기 위한 모듈
import pyaudio          # 마이크 입력/스피커 출력 등 오디오 처리를 위한 라이브러리
import datetime         # 파일 저장 시 현재 날짜·시간을 파일명으로 사용하기 위해 필요
import speech_recognition as sr  # 구글 음성 인식 API 등 다양한 음성 인식 기능 제공

# PyQt6에서 UI 구성 요소 불러오기
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton,
    QLabel, QTextEdit, QMessageBox
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt  # 스레드, 시그널, 정렬 옵션 등

# --- 녹음 관련 상수 설정 ---
CHUNK = 1024                # 오디오 버퍼 크기(한 번에 읽어들일 데이터 프레임 수)
FORMAT = pyaudio.paInt16    # 16비트 PCM 오디오 포맷
CHANNELS = 1                # 1 채널(모노) 녹음
RATE = 44100                # 샘플링 속도(Hz) → 44.1kHz CD 음질
TEMP_WAV_FILE = "temp_recording.wav" # 임시로 녹음을 저장할 파일명


# === 별도 스레드에서 녹음을 처리하는 클래스 ===
class RecorderThread(QThread):
    # PyQt 시그널: 메인 UI에 녹음 완료/오류 이벤트를 알려주기 위함
    finished = pyqtSignal()     # 정상 종료 시
    error = pyqtSignal(str)     # 오류 시(문자열로 에러 메시지 전달)

    def run(self):
        """스레드가 start()로 시작되면 실행되는 메서드"""
        self.is_recording = True    # 녹음 중 상태 플래그
        self.frames = []            # 오디오 데이터 조각(바이너리)을 저장할 리스트
        
        p = pyaudio.PyAudio()       # PyAudio 초기화
        try:
            # 마이크 입력 스트림 열기
            stream = p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,               # 입력 모드(녹음)
                frames_per_buffer=CHUNK   # 버퍼 크기 지정
            )
        except OSError:
            # 마이크 장치가 없거나 접근 불가할 때
            self.error.emit("사용 가능한 마이크를 찾을 수 없습니다.\n마이크 연결을 확인해주세요.")
            p.terminate()
            return

        # 녹음 루프
        while self.is_recording:
            data = stream.read(CHUNK)     # 마이크에서 오디오 데이터 읽기
            self.frames.append(data)      # 읽은 데이터를 프레임 리스트에 저장
        
        # 녹음이 끝나면 스트림과 PyAudio 자원 해제
        stream.stop_stream()
        stream.close()
        p.terminate()

        # 녹음한 데이터를 WAV 파일로 저장
        with wave.open(TEMP_WAV_FILE, 'wb') as wf:     # 'wb' = write binary
            wf.setnchannels(CHANNELS)                  # 채널 수 설정
            wf.setsampwidth(p.get_sample_size(FORMAT)) # 샘플 너비(바이트 단위) 설정
            wf.setframerate(RATE)                      # 샘플링 속도 설정
            wf.writeframes(b''.join(self.frames))      # 프레임 리스트를 합쳐서 저장
            
        # 메인 쓰레드(UI)에 '녹음 완료' 신호 전송
        self.finished.emit()

    def stop(self):
        """녹음 중지 요청"""
        self.is_recording = False


# === 메인 애플리케이션 UI 클래스 ===
class VoiceDiaryApp(QWidget):
    def __init__(self):
        super().__init__()
        self.recorder_thread = None   # 녹음 스레드 객체
        self.init_ui()                # UI 초기화

    def init_ui(self):
        """UI 구성 요소 초기화"""
        self.setWindowTitle("음성 인식 일기장 v2.0")  # 창 제목
        self.setGeometry(300, 300, 500, 400)           # (x, y, width, height)

        layout = QVBoxLayout()  # 위에서 아래로 쌓는 레이아웃

        # 상태 표시 라벨
        self.status_label = QLabel("버튼을 눌러 녹음을 시작하세요.", self)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)  # 가운데 정렬

        # 녹음 버튼
        self.record_button = QPushButton("🎙️ 녹음 시작", self)
        self.record_button.setFixedHeight(40)

        # 텍스트 표시/편집 박스
        self.text_edit = QTextEdit(self)
        self.text_edit.setPlaceholderText("이곳에 음성 인식 결과가 표시됩니다.")

        # 저장 버튼
        self.save_button = QPushButton("💾 일기 저장", self)
        self.save_button.setFixedHeight(40)

        # 레이아웃에 요소 추가
        layout.addWidget(self.status_label)
        layout.addWidget(self.record_button)
        layout.addWidget(self.text_edit)
        layout.addWidget(self.save_button)
        self.setLayout(layout)

        # 버튼 클릭 시 실행될 메서드 연결
        self.record_button.clicked.connect(self.toggle_recording)
        self.save_button.clicked.connect(self.save_diary)

    def toggle_recording(self):
        """녹음 시작/중지 토글"""
        # 이미 녹음 중이면 → 중지
        if self.recorder_thread and self.recorder_thread.isRunning():
            self.recorder_thread.stop()    # 녹음 중지 요청
            self.status_label.setText("음성 처리 중... 잠시만 기다려주세요.")
            self.record_button.setEnabled(False)  # 처리 중 버튼 비활성화
        else:
            # 녹음 시작
            self.recorder_thread = RecorderThread()
            self.recorder_thread.finished.connect(self.transcribe_audio) # 녹음 완료 후 변환
            self.recorder_thread.error.connect(self.show_error_message)  # 오류 발생 시 메시지
            self.recorder_thread.start()  # 스레드 시작(run 실행)
            
            self.status_label.setText("녹음 중... 🎙️ (다시 누르면 중지)")
            self.record_button.setText("🛑 녹음 중지")
            self.text_edit.clear()

    def transcribe_audio(self):
        """WAV 파일 → 텍스트 변환"""
        r = sr.Recognizer()  # 인식기 객체
        try:
            with sr.AudioFile(TEMP_WAV_FILE) as source:
                audio_data = r.record(source)  # 파일 전체 읽기
                # 구글 음성 인식 API 호출
                text = r.recognize_google(audio_data, language='ko-KR')
                self.text_edit.setText(text)
                self.status_label.setText("음성 인식이 완료되었습니다. 내용을 확인하고 저장하세요.")
        except sr.UnknownValueError:
            # 인식 실패(잡음, 너무 짧은 음성 등)
            self.status_label.setText("음성을 인식할 수 없습니다. 다시 시도해주세요.")
            QMessageBox.warning(self, "인식 실패", "음성을 인식할 수 없습니다.\n너무 짧거나 주변 소음을 확인해주세요.")
        except sr.RequestError as e:
            # 네트워크/API 오류
            self.status_label.setText("API 요청 오류가 발생했습니다.")
            QMessageBox.critical(self, "네트워크 오류", f"구글 음성 인식 서비스에 연결할 수 없습니다.\n오류: {e}")
        finally:
            # UI 상태 초기화
            self.record_button.setText("🎙️ 녹음 시작")
            self.record_button.setEnabled(True)

    def save_diary(self):
        """텍스트 내용을 파일로 저장"""
        diary_text = self.text_edit.toPlainText().strip()
        if not diary_text:
            QMessageBox.warning(self, "알림", "저장할 내용이 없습니다.")
            return

        # 저장 여부 확인
        reply = QMessageBox.question(
            self, "일기 저장", "현재 내용을 파일로 저장하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            now = datetime.datetime.now()
            filename = now.strftime("%Y-%m-%d_%H-%M-%S") + ".txt"
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(diary_text)
                self.status_label.setText(f"'{filename}' 파일로 일기가 저장되었습니다.")
                QMessageBox.information(self, "저장 완료", f"'{filename}' 파일로 저장되었습니다.")
            except Exception as e:
                QMessageBox.critical(self, "저장 실패", f"파일 저장 중 오류 발생: {e}")

    def show_error_message(self, message):
        """스레드에서 보낸 오류 메시지를 팝업으로 표시"""
        QMessageBox.critical(self, "오류 발생", message)
        self.status_label.setText("오류가 발생했습니다. 다시 시도해주세요.")
        self.record_button.setText("🎙️ 녹음 시작")
        self.record_button.setEnabled(True)


# === 프로그램 실행부 ===
if __name__ == '__main__':
    app = QApplication(sys.argv)  # Qt 애플리케이션 객체 생성
    ex = VoiceDiaryApp()          # 메인 UI 클래스 인스턴스
    ex.show()                     # UI 표시
    sys.exit(app.exec())           # 이벤트 루프 실행
