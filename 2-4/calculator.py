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

        # ----- 내부 상태 -----
        self.entry_str = "0"           # 현재 입력중인 숫자(문자열)
        self.accumulator = 0.0         # 누적 값
        self.pending_op = None         # 대기 중인 연산자: '+', '−', '×', '÷'
        self.last_operand = None       # '=' 반복 시 사용할 마지막 피연산자
        self.new_entry = True          # True면 다음 숫자 입력 시 entry_str 새로 시작
        self.error = False             # 0으로 나눔 등 오류 상태

        # ----- UI 구성 -----
        central = QWidget(self)
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

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

        grid = QGridLayout()
        grid.setSpacing(8)
        main_layout.addLayout(grid)

        rows = [
            ["AC", "±", "%", "÷"],
            ["7", "8", "9", "×"],
            ["4", "5", "6", "−"],
            ["1", "2", "3", "+"],
        ]

        def make_button(text: str, role: str) -> QPushButton:
            btn = QPushButton(text)
            btn.setCheckable(False)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            bfont = QFont("Arial", 20)
            if text in ["÷", "×", "−", "+", "="]:
                bfont.setPointSize(24)
            btn.setFont(bfont)
            if role == "function":
                btn.setStyleSheet("QPushButton{background:#d9d9d9;border:none;border-radius:12px;padding:12px;} QPushButton:pressed{opacity:.85;}")
            elif role == "operator":
                btn.setStyleSheet("QPushButton{background:#ff9500;color:white;border:none;border-radius:12px;padding:12px;} QPushButton:pressed{opacity:.9;}")
            else:
                btn.setStyleSheet("QPushButton{background:#505050;color:white;border:none;border-radius:12px;padding:12px;} QPushButton:pressed{opacity:.9;}")
            return btn

        # 1~4행
        for r, row in enumerate(rows):
            for c, label in enumerate(row):
                if r == 0 and c <= 2:
                    role = "function"
                elif c == 3:
                    role = "operator"
                else:
                    role = "digit"
                btn = make_button(label, role)
                btn.clicked.connect(lambda _, t=label: self.on_button(t))
                grid.addWidget(btn, r, c)

        # 마지막 행
        zero = make_button("0", "digit")
        zero.clicked.connect(lambda _, t="0": self.on_button(t))
        grid.addWidget(zero, 4, 0, 1, 2)

        dot = make_button(".", "digit")
        dot.clicked.connect(lambda _, t=".": self.on_button(t))
        grid.addWidget(dot, 4, 2, 1, 1)

        eq = make_button("=", "operator")
        eq.clicked.connect(lambda _, t="=": self.on_button(t))
        grid.addWidget(eq, 4, 3, 1, 1)

        self.setStyleSheet("""
        QMainWindow { background: #000; }
        #display { background: #000; color: #fff; border: none; padding: 8px 12px; }
        """)

        self.refresh_display()

    # ------------------ 유틸 ------------------
    def format_number(self, value: float) -> str:
        """표시용 숫자 포맷 (불필요한 0 제거, 너무 긴 소수 줄이기)"""
        try:
            s = f"{value:.12g}"
            if "." in s:
                s = s.rstrip("0").rstrip(".")
            return s
        except Exception:
            return "0"

    def current_entry_value(self) -> float:
        try:
            return float(self.entry_str)
        except Exception:
            return 0.0

    def set_entry_from_value(self, value: float):
        self.entry_str = self.format_number(value)

    def refresh_display(self):
        if self.error:
            self.display.setText("Error")
        else:
            self.display.setText(self.entry_str)

    # ------------------ 입력 처리 ------------------
    def on_button(self, label: str):
        if self.error and label not in ("AC", "±"):
            return

        if label.isdigit():
            self.input_digit(label)
        elif label == ".":
            self.input_dot()
        elif label in ("+", "−", "×", "÷"):
            self.set_operator(label)
        elif label == "AC":
            self.reset()
        elif label == "±":
            self.negative_positive()
        elif label == "%":
            self.percent()
        elif label == "=":
            self.equal()

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

    # ------------------ 연산 메소드 ------------------
    def add(self, a: float, b: float) -> float:
        return a + b

    def subtract(self, a: float, b: float) -> float:
        return a - b

    def multiply(self, a: float, b: float) -> float:
        return a * b

    def divide(self, a: float, b: float) -> float:
        if b == 0:
            self.error = True
            return 0.0
        return a / b

    # ------------------ 상태/기능 메소드 ------------------
    def reset(self):
        self.entry_str = "0"
        self.accumulator = 0.0
        self.pending_op = None
        self.last_operand = None
        self.new_entry = True
        self.error = False
        self.refresh_display()

    def negative_positive(self):
        if self.entry_str.startswith("-"):
            self.entry_str = self.entry_str[1:]
        else:
            if self.entry_str != "0":
                self.entry_str = "-" + self.entry_str
        self.refresh_display()

    def percent(self):
        val = self.current_entry_value() / 100.0
        self.set_entry_from_value(val)
        self.refresh_display()

    def set_operator(self, op: str):
        current = self.current_entry_value()
        if self.pending_op is None:
            self.accumulator = current
        else:
            self.accumulator = self.apply_op(self.pending_op, self.accumulator, current)
            if self.error:
                self.refresh_display()
                return
            self.set_entry_from_value(self.accumulator)
        self.pending_op = op
        self.last_operand = None
        self.new_entry = True
        self.refresh_display()

    def apply_op(self, op: str, a: float, b: float) -> float:
        if op == "+":
            return self.add(a, b)
        elif op == "−":
            return self.subtract(a, b)
        elif op == "×":
            return self.multiply(a, b)
        elif op == "÷":
            return self.divide(a, b)
        return b

    def equal(self):
        if self.pending_op is None and self.last_operand is None:
            return

        if self.pending_op is not None:
            if self.new_entry and self.last_operand is not None:
                operand = self.last_operand
            else:
                operand = self.current_entry_value()
                self.last_operand = operand
            result = self.apply_op(self.pending_op, self.accumulator, operand)
            if self.error:
                self.refresh_display()
                return
            self.accumulator = result
            self.set_entry_from_value(result)
            self.new_entry = True
        else:
            result = self.apply_op("+", self.current_entry_value(), 0)
            self.set_entry_from_value(result)
        self.refresh_display()

    # ------------------ 키보드 (옵션) ------------------
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
            self.set_operator(mapping[key])
        elif key in (Qt.Key.Key_Enter, Qt.Key.Key_Return):
            self.equal()
        elif key == Qt.Key.Key_Escape:
            self.reset()
        else:
            super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    win = Calculator()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()