'''
PyQt6로 만든 아이폰 '가로(공학용)' 계산기와 유사한 레이아웃의 UI.
요구:
- 출력 형태(우측 정렬) 및 버튼 배치 유사
- 색상/모양 동일 불필요
- 버튼 클릭 시 숫자 입력 누적(계산 기능은 이번 과제에서 불필요)
'''

import sys
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QGridLayout,
    QPushButton,
    QLineEdit,
    QSizePolicy,
)


class EngineeringCalculator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Engineering Calculator")
        self.setMinimumSize(680, 360)

        # 입력 상태
        self.new_entry = True
        self.entry_str = "0"

        central = QWidget(self)
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(12)

        # 디스플레이
        self.display = QLineEdit("0", self)
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.display.setObjectName("display")
        self.display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        dfont = QFont("Arial", 36)
        dfont.setBold(True)
        self.display.setFont(dfont)
        self.display.setMinimumHeight(96)
        main.addWidget(self.display)

        grid = QGridLayout()
        grid.setSpacing(8)
        main.addLayout(grid)

        # 아이폰 공학용(가로)과 유사한 8열 구성 (좌측 4열: 공학용, 우측 4열: 일반)
        # 배치 예시 (계산 기능은 연결하지 않지만, 버튼과 이벤트는 모두 연결)
        rows = [
            ["2nd", "(", ")", "Deg",  "AC", "±", "%", "÷"],
            ["sin", "cos", "tan", "π", "7",  "8", "9", "×"],
            ["ln",  "log", "e",  "x^y","4",  "5", "6", "−"],
            ["x²",  "x³",  "√",  "1/x","1",  "2", "3", "+"],
            ["x!",  "Rand","Exp","Ans","0",  ".", "=", "▯"],
        ]

        def make_button(text: str, role: str) -> QPushButton:
            btn = QPushButton(text)
            btn.setCheckable(False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            bfont = QFont("Arial", 18)
            if text in ["÷", "×", "−", "+", "="]:
                bfont.setPointSize(22)
            btn.setFont(bfont)

            if role == "function":
                btn.setStyleSheet("QPushButton{background:#d9d9d9;border:none;border-radius:12px;padding:10px;} QPushButton:pressed{opacity:.88;}")
            elif role == "operator":
                btn.setStyleSheet("QPushButton{background:#ff9500;color:white;border:none;border-radius:12px;padding:10px;} QPushButton:pressed{opacity:.9;}")
            else:
                btn.setStyleSheet("QPushButton{background:#505050;color:white;border:none;border-radius:12px;padding:10px;} QPushButton:pressed{opacity:.9;}")
            return btn

        # 배치 및 시그널 연결
        for r, row in enumerate(rows):
            for c, label in enumerate(row):
                if label == "▯":
                    dummy = QWidget()
                    grid.addWidget(dummy, r, c)
                    continue

                if r == 0 and 4 <= c <= 6:
                    role = "function"
                elif c == 7:
                    role = "operator"
                elif c >= 4 and label.isdigit():
                    role = "digit"
                elif label in ("=",):
                    role = "operator"
                else:
                    role = "sci"

                btn = make_button(label, role)
                btn.clicked.connect(lambda _, t=label: self.on_button(t))
                grid.addWidget(btn, r, c)

        self.setStyleSheet("""
        QMainWindow { background: #000; }
        #display { background: #000; color: #fff; border: none; padding: 8px 12px; }
        """)

    # ---------- 입력 처리(계산 기능 없음) ----------
    def on_button(self, label: str):
        if label.isdigit():
            self.input_digit(label)
            return
        if label == ".":
            self.input_dot()
            return
        if label == "AC":
            self.entry_str = "0"
            self.new_entry = True
            self.refresh_display()

    def input_digit(self, d: str):
        if self.new_entry:
            self.entry_str = d
            self.new_entry = False
        else:
            if self.entry_str == "0":
                self.entry_str = d
            else:
                self.entry_str += d
        self.refresh_display()

    def input_dot(self):
        if self.new_entry:
            self.entry_str = "0."
            self.new_entry = False
        else:
            if "." not in self.entry_str:
                self.entry_str += "."
        self.refresh_display()

    def refresh_display(self):
        self.display.setText(self.entry_str)


def main():
    app = QApplication(sys.argv)
    win = EngineeringCalculator()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
