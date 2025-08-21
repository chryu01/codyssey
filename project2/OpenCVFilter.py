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
    def __init__(self):
        super().__init__()
        self.setWindowTitle("실시간 웹캠 필터")
        self.filter_name = "none"   # 기본 필터 없음
        self.last_frame = None      # 저장용 마지막 프레임

        self.initUI()
        self.cap = cv2.VideoCapture(0)  # 웹캠 열기

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        self.timer.start(30)  # 약 30ms마다 프레임 업데이트

    def initUI(self):
        self.image_label = QLabel()
        self.image_label.setFixedSize(640, 480)

        # 필터 버튼 생성
        btn_none = QPushButton("원본")
        btn_gray = QPushButton("흑백")
        btn_sepia = QPushButton("세피아")
        btn_cartoon = QPushButton("만화")

        btn_none.clicked.connect(lambda: self.set_filter("none"))
        btn_gray.clicked.connect(lambda: self.set_filter("gray"))
        btn_sepia.clicked.connect(lambda: self.set_filter("sepia"))
        btn_cartoon.clicked.connect(lambda: self.set_filter("cartoon"))

        # 버튼 스타일
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

        # 필터 버튼 줄
        hbox_filters = QHBoxLayout()
        hbox_filters.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        for btn in [btn_none, btn_gray, btn_sepia, btn_cartoon]:
            hbox_filters.addWidget(btn)
            hbox_filters.addSpacing(10)
        hbox_filters.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # 촬영 버튼 (필터 줄 아래, 가운데)
        self.btn_capture = QPushButton("사진 촬영")
        self.btn_capture.setMinimumHeight(40)
        self.btn_capture.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32; color: white; border-radius: 12px;
                padding: 10px 18px; font-size: 15px; font-weight: bold;
                border-bottom: 3px solid #1B5E20;
            }
            QPushButton:hover { background-color: #27682B; }
            QPushButton:pressed { background-color: #1F5222; }
        """)
        self.btn_capture.clicked.connect(self.capture_photo)

        hbox_capture = QHBoxLayout()
        hbox_capture.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        hbox_capture.addWidget(self.btn_capture)
        hbox_capture.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # 레이아웃 조합
        vbox = QVBoxLayout()
        vbox.addWidget(self.image_label)
        vbox.addLayout(hbox_filters)
        vbox.addSpacing(8)
        vbox.addLayout(hbox_capture)

        container = QWidget()
        container.setLayout(vbox)
        self.setCentralWidget(container)

    def set_filter(self, name: str):
        self.filter_name = name

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        frame = self.apply_filter(frame)

        # 저장용 프레임 보관
        self.last_frame = frame.copy()

        # 표시용 변환 (흑백이면 3채널로 보정)
        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(qt_image))

    def apply_filter(self, frame: np.ndarray):
        # (필터 설정값 그대로 유지)
        if self.filter_name == "gray":
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        elif self.filter_name == "sepia":
            kernel = np.array([
                [0.272, 0.534, 0.131],
                [0.349, 0.686, 0.168],
                [0.393, 0.769, 0.189]
            ])
            return cv2.transform(frame, kernel)
        elif self.filter_name == "cartoon":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.medianBlur(gray, 5)
            edges = cv2.adaptiveThreshold(
                gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                cv2.THRESH_BINARY, 9, 9
            )
            color = cv2.bilateralFilter(frame, 9, 300, 300)
            return cv2.bitwise_and(color, color, mask=edges)
        else:
            return frame

    def capture_photo(self):
        """현재 프레임을 프로젝트 폴더의 Filtered/에 저장 (한글/특수문자 경로 대응)."""
        if self.last_frame is None:
            QMessageBox.warning(self, "안내", "저장할 화면이 없습니다.")
            return

        # 저장 폴더 준비: 현재 파일 기준 Filtered/
        out_dir = Path(__file__).resolve().parent / "Filtered"
        out_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"{ts}_{self.filter_name}.png"

        # 저장 안정성: dtype/채널 보정
        img = self.last_frame
        if np.issubdtype(img.dtype, np.floating):
            img = np.clip(img, 0, 255).astype(np.uint8)
        if img.ndim == 2:
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        img = np.ascontiguousarray(img)

        # imencode + tofile로 유니코드/특수문자 경로에서도 저장
        ok, buf = cv2.imencode(".png", img)
        if not ok:
            QMessageBox.critical(self, "오류", "PNG 인코딩에 실패했습니다.")
            return

        try:
            buf.tofile(str(out_path))
        except Exception as e:
            QMessageBox.critical(
                self, "오류",
                f"이미지 저장 실패\n경로: {out_path}\n사유: {e}\n"
                f"dtype: {img.dtype}, shape: {img.shape}"
            )
            return

        QMessageBox.information(self, "저장 완료", f"저장됨:\n{out_path}")

    def closeEvent(self, event):
        self.cap.release()
        event.accept()


if __name__ == "__main__":
        app = QApplication(sys.argv)
        window = WebcamFilterApp()
        window.show()
        sys.exit(app.exec())
