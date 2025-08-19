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


class Calculator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calculator")
        self.setMinimumSize(320, 480)

        # 간단한 상태 (계산은 하지 않지만 입력 UX를 위해 보관)
        self.new_entry = True        # 새로운 숫자 입력 시작 여부
        self.pending_operator = None # 마지막으로 누른 연산자(계산 기능은 없음)

        # 메인 위젯/레이아웃
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # 디스플레이 (우측정렬, ReadOnly)
        self.display = QLineEdit("0", self)
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.display.setObjectName("display")
        self.display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        dfont = QFont("Arial", 36)
        dfont.setBold(True)
        self.display.setFont(dfont)
        self.display.setMinimumHeight(100)
        main_layout.addWidget(self.display)

        # 버튼 그리드
        grid = QGridLayout()
        grid.setSpacing(8)
        main_layout.addLayout(grid)

        # 버튼 텍스트 구성 (아이폰 계산기 배치와 동일)
        rows = [
            ["AC", "±", "%", "÷"],
            ["7", "8", "9", "×"],
            ["4", "5", "6", "−"],
            ["1", "2", "3", "+"],
        ]

        # 버튼 생성 도우미
        def make_button(text: str, role: str) -> QPushButton:
            btn = QPushButton(text)
            btn.setCheckable(False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

            # 글꼴
            bfont = QFont("Arial", 20)
            if text in ["÷", "×", "−", "+", "="]:
                bfont.setPointSize(24)
            btn.setFont(bfont)

            # 간단 스타일 (색상은 동일할 필요 없음)
            if role == "function":
                btn.setStyleSheet("QPushButton{background:#d9d9d9;border:none;border-radius:12px;padding:12px;} QPushButton:pressed{opacity:.85;}")
            elif role == "operator":
                btn.setStyleSheet("QPushButton{background:#ff9500;color:white;border:none;border-radius:12px;padding:12px;} QPushButton:pressed{opacity:.9;}")
            else:  # digit
                btn.setStyleSheet("QPushButton{background:#505050;color:white;border:none;border-radius:12px;padding:12px;} QPushButton:pressed{opacity:.9;}")
            return btn

        # 1~4번째 줄 배치
        for r, row in enumerate(rows):
            for c, label in enumerate(row):
                if r == 0 and c <= 2:
                    role = "function"
                elif c == 3:
                    role = "operator"
                else:
                    role = "digit"
                btn = make_button(label, role)
                btn.clicked.connect(lambda _, t=label: self.handle_button(t))
                grid.addWidget(btn, r, c)

        # 마지막 줄: 0(두 칸), ".", "="
        zero_btn = make_button("0", "digit")
        zero_btn.clicked.connect(lambda _, t="0": self.handle_button(t))
        grid.addWidget(zero_btn, 4, 0, 1, 2)  # column span 2

        dot_btn = make_button(".", "digit")
        dot_btn.clicked.connect(lambda _, t=".": self.handle_button(t))
        grid.addWidget(dot_btn, 4, 2, 1, 1)

        eq_btn = make_button("=", "operator")
        eq_btn.clicked.connect(lambda _, t="=": self.handle_button(t))
        grid.addWidget(eq_btn, 4, 3, 1, 1)

        # 키보드 입력도 약간 지원 (선택 사항)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        # 전체 폰트/여백 느낌 살짝 조정
        self.setStyleSheet("""
        QMainWindow { background: #000; }
        #display {
            background: #000;
            color: #fff;
            border: none;
            padding: 8px 12px;
        }
        """)

    # 버튼 핸들러 (계산 없이 입력만 처리)
    def handle_button(self, label: str):
        if label.isdigit():
            self.input_digit(label)
        elif label == ".":
            self.input_dot()
        elif label in ("+", "−", "×", "÷"):
            # 연산자는 아직 계산하지 않고, 단순히 상태만 기록
            self.pending_operator = label
            self.new_entry = True
        elif label == "AC":
            self.clear_all()
        elif label == "±":
            self.toggle_sign()
        elif label == "%":
            # 실제 계산은 하지 않지만, 아이폰처럼 즉각 퍼센트 변환 느낌을 위해 단순 표시 변경
            # 계산 미구현 과제이므로, 여기서는 입력된 숫자 끝에 '%'만 붙였다가 또 누르면 제거하는 수준으로 처리
            text = self.display.text()
            if text.endswith("%"):
                self.display.setText(text[:-1] if text[:-1] else "0")
            else:
                if text != "0":
                    self.display.setText(text + "%")
        elif label == "=":
            # 계산은 하지 않음. 눌러도 변화 없음(또는 입력 확정 정도로만 취급)
            self.new_entry = True

    def input_digit(self, d: str):
        current = self.display.text()

        # 퍼센트 표시가 있으면 제거하고 새로 입력 시작
        if current.endswith("%"):
            current = current[:-1]
            self.new_entry = True

        if self.new_entry or current == "0":
            self.display.setText(d)
            self.new_entry = False
        else:
            self.display.setText(current + d)

    def input_dot(self):
        current = self.display.text()

        # 퍼센트 표시가 있으면 제거하고 새로 시작
        if current.endswith("%"):
            current = current[:-1]

        if self.new_entry:
            # 새 입력 시작 시 "0."부터
            self.display.setText("0.")
            self.new_entry = False
        else:
            if "." not in current:
                self.display.setText(current + ".")

    def clear_all(self):
        self.display.setText("0")
        self.new_entry = True
        self.pending_operator = None

    def toggle_sign(self):
        text = self.display.text()
        if text.endswith("%"):
            text = text[:-1]  # % 제거 후 동작
        if text.startswith("-"):
            text = text[1:]
        else:
            if text != "0":
                text = "-" + text
        self.display.setText(text)

    # 간단한 키보드 입력(옵션)
    def keyPressEvent(self, event):
        key = event.key()
        if Qt.Key.Key_0 <= key <= Qt.Key.Key_9:
            self.input_digit(chr(key))
        elif key == Qt.Key.Key_Period:
            self.input_dot()
        elif key in (Qt.Key.Key_Plus, Qt.Key.Key_Minus, Qt.Key.Key_Asterisk, Qt.Key.Key_Slash):
            mapping = {
                Qt.Key.Key_Plus: "+",
                Qt.Key.Key_Minus: "−",
                Qt.Key.Key_Asterisk: "×",
                Qt.Key.Key_Slash: "÷",
            }
            self.handle_button(mapping[key])
        elif key == Qt.Key.Key_Enter or key == Qt.Key.Key_Return:
            self.handle_button("=")
        elif key == Qt.Key.Key_Escape:
            self.clear_all()
        else:
            super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    win = Calculator()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
'''
with open('/mnt/data/calculator.py', 'w', encoding='utf-8') as f:
    f.write(code)
'''
