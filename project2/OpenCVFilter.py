import sys
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget,
    QHBoxLayout, QSpacerItem, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QImage, QPixmap


class WebcamFilterApp(QMainWindow):
    """
    실시간으로 웹캠 화면을 띄우고, 버튼으로 필터를 바꾼 뒤
    현재 화면을 이미지로 저장할 수 있는 간단한 프로그램의 메인 창입니다.
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("실시간 웹캠 필터")

        # 지금 어떤 필터가 선택되어 있는지 기억하는 변수 (기본값: none = 원본)
        self.filter_name = "none"

        # 마지막으로 화면에 보여준 영상 프레임을 저장해두는 변수 (사진 저장에 사용)
        self.last_frame = None

        # 화면(버튼, 영상 영역 등) 만드는 함수 호출
        self.initUI()

        # 컴퓨터에 연결된 웹캠을 연다. 0은 기본 웹캠을 의미.
        self.cap = cv2.VideoCapture(0)

        # 일정 시간마다(여기선 30ms) 웹캠 새 화면을 읽어와서 창에 그려주도록 타이머 설정
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)  # 타이머가 울릴 때마다 update_frame 실행
        self.timer.start(30)  # 1초에 약 33번(= 1000/30) 화면 갱신

    def initUI(self):
        """
        프로그램의 겉모습(UI)을 구성합니다.
        - 위쪽: 웹캠 영상이 보이는 영역
        - 중간: 필터 선택 버튼 4개
        - 아래: '사진 촬영' 버튼 (가운데 정렬)
        """

        # 웹캠 영상을 보여줄 상자(라벨). 가로 640, 세로 480 픽셀로 고정.
        self.image_label = QLabel()
        self.image_label.setFixedSize(640, 480)

        # ====== 필터 선택 버튼들 ======
        btn_none = QPushButton("원본")   # 필터 없이 원본 화면
        btn_gray = QPushButton("흑백")   # 흑백 필터
        btn_sepia = QPushButton("세피아") # 세피아(갈색 톤) 필터
        btn_cartoon = QPushButton("만화") # 만화 느낌 필터

        # 버튼을 클릭하면 현재 필터 이름을 바꾸도록 연결
        btn_none.clicked.connect(lambda: self.set_filter("none"))
        btn_gray.clicked.connect(lambda: self.set_filter("gray"))
        btn_sepia.clicked.connect(lambda: self.set_filter("sepia"))
        btn_cartoon.clicked.connect(lambda: self.set_filter("cartoon"))

        # 버튼의 색/모양을 보기 좋게 꾸미는 설정 (디자인만 바뀌고 기능엔 영향 없음)
        button_styles = {
            "none": """
                QPushButton {
                    background-color: #A0A0A0; color: white; border-radius: 10px;
                    padding: 8px 16px; font-size: 14px; font-weight: bold;
                }
                QPushButton:hover { background-color: #888888; }
                QPushButton:pressed { background-color: #666666; }
            """,
            "gray": """
                QPushButton {
                    background-color: #555555; color: white; border-radius: 10px;
                    padding: 8px 16px; font-size: 14px; font-weight: bold;
                }
                QPushButton:hover { background-color: #444444; }
                QPushButton:pressed { background-color: #333333; }
            """,
            "sepia": """
                QPushButton {
                    background-color: #C49E6C; color: white; border-radius: 10px;
                    padding: 8px 16px; font-size: 14px; font-weight: bold;
                }
                QPushButton:hover { background-color: #B68655; }
                QPushButton:pressed { background-color: #9F6D3D; }
            """,
            "cartoon": """
                QPushButton {
                    background-color: #FFAA33; color: white; border-radius: 10px;
                    padding: 8px 16px; font-size: 14px; font-weight: bold;
                }
                QPushButton:hover { background-color: #FF9900; }
                QPushButton:pressed { background-color: #E68A00; }
            """
        }
        btn_none.setStyleSheet(button_styles["none"])
        btn_gray.setStyleSheet(button_styles["gray"])
        btn_sepia.setStyleSheet(button_styles["sepia"])
        btn_cartoon.setStyleSheet(button_styles["cartoon"])

        # 필터 버튼들을 가로로 나열하고, 양쪽에 빈 공간을 넣어 가운데 정렬 효과
        hbox_filters = QHBoxLayout()
        hbox_filters.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        for btn in [btn_none, btn_gray, btn_sepia, btn_cartoon]:
            hbox_filters.addWidget(btn)
            hbox_filters.addSpacing(10)  # 버튼 사이 간격
        hbox_filters.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # ====== 사진 촬영 버튼 ======
        # 현재 화면(선택된 필터가 적용된 상태)을 이미지 파일로 저장
        self.btn_capture = QPushButton("사진 촬영")
        self.btn_capture.setMinimumHeight(40)
        self.btn_capture.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32; color: white; border-radius: 12px;
                padding: 10px 18px; font-size: 15px; font-weight: bold;
                border-bottom: 3px solid #1B5E20; /* 아래쪽 테두리(살짝 밑줄 느낌) */
            }
            QPushButton:hover { background-color: #27682B; }
            QPushButton:pressed { background-color: #1F5222; }
        """)
        self.btn_capture.clicked.connect(self.capture_photo)

        # 촬영 버튼도 가로로 배치하지만, 양쪽 빈 공간으로 가운데 정렬되도록 함
        hbox_capture = QHBoxLayout()
        hbox_capture.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        hbox_capture.addWidget(self.btn_capture)
        hbox_capture.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # ====== 전체 화면 배치 ======
        vbox = QVBoxLayout()
        vbox.addWidget(self.image_label)  # 위: 카메라 영상
        vbox.addLayout(hbox_filters)      # 중간: 필터 버튼 줄
        vbox.addSpacing(8)                # 여백 조금
        vbox.addLayout(hbox_capture)      # 아래: 촬영 버튼

        # 완성한 레이아웃을 창의 중앙 위젯으로 설정
        container = QWidget()
        container.setLayout(vbox)
        self.setCentralWidget(container)

    def set_filter(self, name: str):
        """버튼을 눌렀을 때 현재 적용할 필터 이름을 바꾼다."""
        self.filter_name = name

    def update_frame(self):
        """
        타이머가 울릴 때마다 실행.
        1) 웹캠에서 새 화면을 읽고
        2) 좌우 반전(거울처럼 보이게)
        3) 선택된 필터 적용
        4) 화면에 그리기
        5) 사진 저장을 위해 마지막 프레임 보관
        """
        ret, frame = self.cap.read()  # ret=True면 성공적으로 읽었음을 의미
        if not ret:
            return  # 읽기 실패 시 그냥 건너뜀

        frame = cv2.flip(frame, 1)     # 화면 좌우 반전
        frame = self.apply_filter(frame)  # 필터 적용

        # 사진 저장을 위해 현재 프레임을 복사해 둔다.
        self.last_frame = frame.copy()

        # 화면에 보여주기 위해 색상 형태를 PyQt가 이해할 수 있게 변환
        # (흑백(회색)만 반환되는 경우가 있으므로 3색(BGR)으로 맞춘 뒤 RGB로 바꿈)
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)

        # 변환한 이미지를 라벨에 표시
        self.image_label.setPixmap(QPixmap.fromImage(qt_image))

    def apply_filter(self, frame: np.ndarray):
        """
        실제로 필터를 적용하는 부분.
        - gray  : 흑백 변환
        - sepia : 갈색 톤으로 변환
        - cartoon: 윤곽을 강조하여 만화같은 느낌
        """
        if self.filter_name == "gray":
            # 컬러(BGR)를 흑백(1채널)로 바꿈
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        elif self.filter_name == "sepia":
            # 세피아 변환을 위한 3x3 변환 행렬(각 색을 섞어 톤을 바꿈)
            kernel = np.array([
                [0.272, 0.534, 0.131],
                [0.349, 0.686, 0.168],
                [0.393, 0.769, 0.189]
            ])
            return cv2.transform(frame, kernel)

        elif self.filter_name == "cartoon":
            # 1) 흑백으로 바꾼 뒤
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # 2) 잡티를 줄이기 위해 흐림 처리
            gray = cv2.medianBlur(gray, 5)
            # 3) 밝고 어두운 경계(윤곽선)만 남기기
            edges = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY, 9, 9
            )
            # 4) 색상은 부드럽게 만들고
            color = cv2.bilateralFilter(frame, 9, 300, 300)
            # 5) 윤곽선과 색을 합쳐 만화 느낌 만들기
            return cv2.bitwise_and(color, color, mask=edges)

        else:
            # 'none'인 경우: 아무 것도 안 하고 원본 그대로
            return frame

    def capture_photo(self):
        """
        '사진 촬영' 버튼을 눌렀을 때 실행.
        현재 화면(필터 적용된 상태)을 'Filtered' 폴더 안에 PNG 파일로 저장합니다.
        - 파일 이름 예: 20250101_123045_gray.png
        - 한글/특수문자 경로에서도 잘 저장되도록 안전한 방법 사용
        """
        if self.last_frame is None:
            QMessageBox.warning(self, "안내", "저장할 화면이 없습니다.")
            return

        # 현재 파이썬 파일이 있는 폴더 기준으로 'Filtered' 폴더를 만든다.
        out_dir = Path(__file__).resolve().parent / "Filtered"
        out_dir.mkdir(parents=True, exist_ok=True)

        # 파일 이름에 현재 시각과 필터 이름을 넣어 구분하기 쉽게 함
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"{ts}_{self.filter_name}.png"

        # 저장하기 전에, 파일 형식에 맞게 데이터 형태를 정리
        img = self.last_frame
        # (만약 실수형으로 되어 있으면 0~255 범위로 잘라서 8비트 정수로 변경)
        if np.issubdtype(img.dtype, np.floating):
            img = np.clip(img, 0, 255).astype(np.uint8)
        # (흑백(2차원) 이미지면 컬러(3차원)로 바꿔서 일관성 있게 저장)
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        # (메모리 배치가 연속적이도록 만들어 저장 실패를 예방)
        img = np.ascontiguousarray(img)

        # OpenCV의 imwrite가 한글 경로에서 실패하는 문제를 피하기 위해
        # 메모리에 PNG로 먼저 인코딩한 뒤, 파일로 저장(tofile)하는 방식을 사용
        ok, buf = cv2.imencode(".png", img)
        if not ok:
            QMessageBox.critical(self, "오류", "PNG 인코딩에 실패했습니다.")
            return

        try:
            buf.tofile(str(out_path))  # 실제 파일로 저장
        except Exception as e:
            QMessageBox.critical(
                self, "오류",
                f"이미지 저장 실패\n경로: {out_path}\n사유: {e}\n"
                f"dtype: {img.dtype}, shape: {img.shape}"
            )
            return

        QMessageBox.information(self, "저장 완료", f"저장됨:\n{out_path}")

    def closeEvent(self, event):
        """
        창을 닫을 때 실행.
        - 웹캠을 꼭 닫아주지 않으면 다음 실행에서 카메라가 안 잡힐 수 있음.
        """
        self.cap.release()
        event.accept()


if __name__ == "__main__":
    # 모든 PyQt 앱은 QApplication부터 시작해야 함 (운영체제와 소통하는 창 관리자)
    app = QApplication(sys.argv)

    # 위에서 만든 창 클래스를 생성해서 띄운다.
    window = WebcamFilterApp()
    window.show()

    # 앱을 실행하고, 사용자가 창을 닫을 때까지 대기
    sys.exit(app.exec())
