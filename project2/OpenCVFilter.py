import sys
import cv2
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout,
    QWidget, QHBoxLayout, QSpacerItem, QSizePolicy, QMessageBox
)
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QImage, QPixmap
import numpy as np
from datetime import datetime
from pathlib import Path

import os

class WebcamFilterApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("실시간 웹캠 필터")
        self.filter_name = "none"   # 기본 필터 없음
        self.last_frame = None      # 현재 표시 중 프레임(저장용)

        self.initUI()
        self.cap = cv2.VideoCapture(0)  # 웹캠 열기

        self.timer = QTimer()
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

        # -------------------- 버튼 스타일 정의 --------------------
        button_styles = {
            "none": """
                QPushButton {
                    background-color: #A0A0A0;
                    color: white;
                    border-radius: 10px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #888888; }
                QPushButton:pressed { background-color: #666666; }
            """,
            "gray": """
                QPushButton {
                    background-color: #555555;
                    color: white;
                    border-radius: 10px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #444444; }
                QPushButton:pressed { background-color: #333333; }
            """,
            "sepia": """
                QPushButton {
                    background-color: #C49E6C;
                    color: white;
                    border-radius: 10px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #B68655; }
                QPushButton:pressed { background-color: #9F6D3D; }
            """,
            "cartoon": """
                QPushButton {
                    background-color: #FFAA33;
                    color: white;
                    border-radius: 10px;
                    padding: 8px 16px;
                    font-size: 14px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #FF9900; }
                QPushButton:pressed { background-color: #E68A00; }
            """
        }

        btn_none.setStyleSheet(button_styles["none"])
        btn_gray.setStyleSheet(button_styles["gray"])
        btn_sepia.setStyleSheet(button_styles["sepia"])
        btn_cartoon.setStyleSheet(button_styles["cartoon"])

        # 필터 버튼 행
        hbox_filters = QHBoxLayout()
        hbox_filters.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        for btn in [btn_none, btn_gray, btn_sepia, btn_cartoon]:
            hbox_filters.addWidget(btn)
            hbox_filters.addSpacing(10)
        hbox_filters.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # -------------------- (추가) 촬영 버튼: 필터 줄 아래, 가운데 --------------------
        self.btn_capture = QPushButton("사진 촬영")
        self.btn_capture.setMinimumHeight(40)
        self.btn_capture.setStyleSheet("""
            QPushButton {
                background-color: #2E7D32;
                color: white;
                border-radius: 12px;
                padding: 10px 18px;
                font-size: 15px;
                font-weight: bold;
                border-bottom: 3px solid #1B5E20; /* 밑줄 느낌 */
            }
            QPushButton:hover { background-color: #27682B; }
            QPushButton:pressed { background-color: #1F5222; }
        """)
        self.btn_capture.clicked.connect(self.capture_photo)

        hbox_capture = QHBoxLayout()
        hbox_capture.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))
        hbox_capture.addWidget(self.btn_capture)
        hbox_capture.addSpacerItem(QSpacerItem(20, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        # 전체 레이아웃
        vbox = QVBoxLayout()
        vbox.addWidget(self.image_label)
        vbox.addLayout(hbox_filters)
        vbox.addSpacing(8)
        vbox.addLayout(hbox_capture)  # 필터 아래, 가운데 배치

        container = QWidget()
        container.setLayout(vbox)
        self.setCentralWidget(container)

    def set_filter(self, name):
        self.filter_name = name

    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)
        frame = self.apply_filter(frame)

        # 저장용 프레임 보관 (필터 적용 결과 그대로)
        self.last_frame = frame.copy()

        # 표시용 변환 (흑백이면 3채널로 맞춰주기)
        if len(frame.shape) == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.image_label.setPixmap(QPixmap.fromImage(qt_image))

    def apply_filter(self, frame):
        # (필터 설정값/로직 그대로 유지)
        if self.filter_name == "gray":
            return cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        elif self.filter_name == "sepia":
            kernel = np.array([[0.272, 0.534, 0.131],
                               [0.349, 0.686, 0.168],
                               [0.393, 0.769, 0.189]])
            return cv2.transform(frame, kernel)
        elif self.filter_name == "cartoon":
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.medianBlur(gray, 5)
            edges = cv2.adaptiveThreshold(gray, 255,
                                          cv2.ADAPTIVE_THRESH_MEAN_C,
                                          cv2.THRESH_BINARY, 9, 9)
            color = cv2.bilateralFilter(frame, 9, 300, 300)
            return cv2.bitwise_and(color, color, mask=edges)
        else:
            return frame

    # -------------------- (추가) 촬영 & 저장 --------------------
    def capture_photo(self):
        if self.last_frame is None:
            QMessageBox.warning(self, "안내", "저장할 화면이 없습니다.")
            return

        out_dir = Path(__file__).resolve().parent / "Filtered"
        out_dir.mkdir(parents=True, exist_ok=True)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"{ts}_{self.filter_name}.png"

        frame_to_save = self.last_frame
        if np.issubdtype(frame_to_save.dtype, np.floating):
            frame_to_save = np.clip(frame_to_save, 0, 255).astype(np.uint8)
        if frame_to_save.ndim == 2:
            frame_to_save = cv2.cvtColor(frame_to_save, cv2.COLOR_GRAY2BGR)
        frame_to_save = np.ascontiguousarray(frame_to_save)

        # 경로 정규화 (OpenCV가 처리 가능한 Windows 경로로 변환)
        save_path = os.path.normpath(str(out_path))

        ok = cv2.imwrite(save_path, frame_to_save)
        if ok:
            QMessageBox.information(self, "저장 완료", f"저장됨:\n{save_path}")
        else:
            QMessageBox.critical(
                self, "오류",
                f"이미지 저장 실패\n경로: {save_path}\n"
                f"dtype: {frame_to_save.dtype}, shape: {frame_to_save.shape}"
            )

    def closeEvent(self, event):
        self.cap.release()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WebcamFilterApp()
    window.show()
    sys.exit(app.exec())
