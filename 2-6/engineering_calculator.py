# engineering_calculator.py
# - 기존 Calculator를 상속해 공학용(가로) UI와 기능을 추가
# - iPhone 가로 공학용 배치 유사 (10열 구성: 좌 6열 공학용, 우 4열 일반)
# - 필수 구현: sin, cos, tan, sinh, cosh, tanh, pi(π), square(x²), cube(x³)
# - math 표준 라이브러리만 사용
#
# [공학 기능(30+):]
# 1) 2nd, 2) Deg/Rad, 3) MC, 4) MR, 5) M+, 6) M-, 7) x², 8) x³, 9) xʸ,
# 10) 10^x, 11) √x, 12) 1/x, 13) x!, 14) y√x, 15) ln, 16) log10,
# 17) e(상수), 18) π(상수), 19) sin, 20) cos, 21) tan,
# 22) asin, 23) acos, 24) atan, 25) sinh, 26) cosh, 27) tanh,
# 28) asinh, 29) acosh, 30) atanh, 31) Rand(0~1), 32) EE(지수표기), 
# + 기본 계산기 기능들(AC, ±, %, +, −, ×, ÷, =, 숫자, .)

import sys
import math
import random
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QSizePolicy
)

# -------------------------- 너의 기본 Calculator (원문 유지) --------------------------
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

        # ----- UI 구성(세로) -----
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
            if "." not in self.entry_str and "e" not in self.entry_str.lower():
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

# -------------------------- EngineeringCalculator (상속 + 가로 UI) --------------------------
class EngineeringCalculator(Calculator):
    def __init__(self):
        super().__init__()  # 상태/로직 재사용

        # 부모가 만든 세로 UI 제거 후 가로 UI 재구성
        old = self.takeCentralWidget()
        if old:
            old.deleteLater()

        self.setWindowTitle("Engineering Calculator")
        self.setMinimumSize(900, 460)

        # 공학용 상태
        self.use_deg = True          # DEG/RAD
        self.second_on = False       # 2nd
        self.memory = 0.0            # MC/MR/M+/M-
        # 이항 공학연산 대기 (x^y, y√x)
        self._pending_sci = None     # "pow" | "yroot"
        self._sci_left = None        # 좌항 저장

        central = QWidget(self)
        self.setCentralWidget(central)
        main = QVBoxLayout(central)
        main.setContentsMargins(12, 12, 12, 12)
        main.setSpacing(12)

        # 디스플레이 (부모 display 새로 구성)
        self.display = QLineEdit(self.entry_str, self)
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.display.setObjectName("display")
        self.display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        dfont = QFont("Arial", 40); dfont.setBold(True)
        self.display.setFont(dfont)
        self.display.setMinimumHeight(96)
        main.addWidget(self.display)

        grid = QGridLayout()
        grid.setSpacing(8)
        main.addLayout(grid)

        # 10열 배치: 좌 6열(공학), 우 4열(일반)
        sci_rows = [
            ["2nd", "(", ")", "Deg", "mc", "mr"],
            ["x²",  "x³", "xʸ", "10^x", "√x",  "1/x"],
            ["x!",  "y√x", "ln", "log",  "e",   "π"],
            ["sin","cos","tan","sinh","cosh","tanh"],
            ["asin","acos","atan","asinh","acosh","atanh"],
        ]
        std_rows = [
            ["AC","±","%","÷"],
            ["7","8","9","×"],
            ["4","5","6","−"],
            ["1","2","3","+"],
            ["0",".","EE","="],
        ]

        def make_button(text: str, role: str) -> QPushButton:
            btn = QPushButton(text)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            bfont = QFont("Arial", 18)
            if text in ["÷", "×", "−", "+", "="]:
                bfont.setPointSize(22)
            btn.setFont(bfont)
            if role == "op":
                btn.setStyleSheet("QPushButton{background:#ff9500;color:white;border:none;border-radius:18px;padding:12px;} QPushButton:pressed{opacity:.9;}")
            elif role == "fn":
                btn.setStyleSheet("QPushButton{background:#d9d9d9;border:none;border-radius:18px;padding:12px;} QPushButton:pressed{opacity:.88;}")
            else:
                btn.setStyleSheet("QPushButton{background:#505050;color:white;border:none;border-radius:18px;padding:12px;} QPushButton:pressed{opacity:.9;}")
            return btn

        # 버튼 생성/배치
        self._btn_refs = {}  # 라벨 변경(2nd/DEG 표시)용
        for r in range(5):
            # 왼쪽 6개
            for c in range(6):
                label = sci_rows[r][c]
                role = "fn" if r==0 else ("fn" if r<=2 else "fn")  # 공학은 전부 function 스타일
                b = make_button(label, role)
                b.clicked.connect(lambda _, t=label: self.on_eng_button(t))
                grid.addWidget(b, r, c)
                self._btn_refs[(r, c)] = b
            # 오른쪽 4개
            for c in range(4):
                label = std_rows[r][c]
                if r == 0 and c <= 2:
                    role = "fn"
                elif c == 3 or label == "=":
                    role = "op"
                elif label.isdigit() or label in (".","0"):
                    role = "num"
                else:
                    role = "num"
                b = make_button(label, role)
                b.clicked.connect(lambda _, t=label: self.on_std_button(t))
                grid.addWidget(b, r, 6 + c)

        self.setStyleSheet("""
        QMainWindow { background: #000; }
        #display { background: #000; color: #fff; border: none; padding: 8px 12px; }
        """)

        # 초기 표시 갱신
        self.refresh_display()

    # ---------------- 표시/유틸 ----------------
    def _set_value(self, v: float):
        if math.isfinite(v):
            self.set_entry_from_value(v)
        else:
            self.error = True
        self.new_entry = True
        self.refresh_display()

    def _current(self) -> float:
        return self.current_entry_value()

    def _deg2rad(self, x: float) -> float:
        return math.radians(x) if self.use_deg else x

    def _rad2deg(self, x: float) -> float:
        return math.degrees(x) if self.use_deg else x

    # ---------------- 표준(우측) 버튼 ----------------
    def on_std_button(self, label: str):
        if label in {"AC","±","%","+","−","×","÷","=",".", "0","1","2","3","4","5","6","7","8","9"}:
            # x^y / y√x의 중간 상태에서 사칙/=/숫자 입력이 올 수 있음
            if label in {"+","−","×","÷","="} and self._pending_sci:
                # 이항 공학 연산을 먼저 완결
                left = self._sci_left if self._sci_left is not None else self._current()
                right = self._current()
                try:
                    if self._pending_sci == "pow":
                        self._set_value(left ** right)
                    elif self._pending_sci == "yroot":
                        self._set_value(left ** (1.0 / right))
                except Exception:
                    self.error = True
                    self.refresh_display()
                # 클리어
                self._pending_sci = None
                self._sci_left = None
            # EE는 std쪽에 있어서 분기 제외
            if label == "EE":
                return
            super().on_button(label)
            return
        if label == "EE":
            # 과학 표기: 현재 숫자 뒤에 'e' 추가 (다음에 지수 입력)
            if self.new_entry:
                self.entry_str = "1e"
                self.new_entry = False
            else:
                if "e" not in self.entry_str.lower():
                    self.entry_str += "e"
            self.refresh_display()

    # ---------------- 공학(좌측) 버튼 ----------------
    def on_eng_button(self, label: str):
        # 토글/표시
        if label == "2nd":
            self.second_on = not self.second_on
            self._toggle_second_labels()
            return
        if label in ("Deg","Rad"):
            self.use_deg = not self.use_deg
            btn = self._btn_refs.get((0,3))
            if btn:
                btn.setText("Deg" if self.use_deg else "Rad")
            return

        # 메모리
        if label == "mc":
            self.memory = 0.0; return
        if label == "mr":
            self._set_value(self.memory); return
        if label == "m+":
            self.memory += self._current(); return
        if label == "m-":
            self.memory -= self._current(); return

        # 상수
        if label == "π":
            self.pi_const(); return
        if label == "e":
            self.e_const(); return
        if label == "Rand":
            self._set_value(random.random()); return

        # 단항 공학연산
        unary_map = {
            "x²": self.square,
            "x³": self.cube,
            "√x": self.sqrt,
            "1/x": self.reciprocal,
            "x!": self.factorial,
            "ln": self.ln,
            "log": self.log10,
            "sin": self.sin, "cos": self.cos, "tan": self.tan,
            "asin": self.asin, "acos": self.acos, "atan": self.atan,
            "sinh": self.sinh, "cosh": self.cosh, "tanh": self.tanh,
            "asinh": self.asinh, "acosh": self.acosh, "atanh": self.atanh,
            "10^x": self.pow10,
        }
        if label in unary_map:
            unary_map[label]()
            return

        # 이항 공학연산: xʸ, y√x
        if label == "xʸ":
            self._sci_left = self._current()
            self._pending_sci = "pow"
            self.new_entry = True
            return
        if label == "y√x":
            self._sci_left = self._current()
            self._pending_sci = "yroot"
            self.new_entry = True
            return

        # 괄호는 (현재 구조상) 표현식 평가가 없으므로 무시
        if label in ("(", ")"):
            return

    def _toggle_second_labels(self):
        # 2nd 토글에 따라 첫 번째 삼각행/역삼각행을 스왑처럼 보이게 구성
        tri_pos = [(3,0,"sin"),(3,1,"cos"),(3,2,"tan")]
        inv_pos = [(4,0,"asin"),(4,1,"acos"),(4,2,"atan")]
        hyp_pos = [(3,3,"sinh"),(3,4,"cosh"),(3,5,"tanh")]
        invh_pos= [(4,3,"asinh"),(4,4,"acosh"),(4,5,"atanh")]
        if self.second_on:
            # tri <-> inv
            for (r,c,_),(_,_,name) in zip(tri_pos, inv_pos):
                self._btn_refs[(r,c)].setText(name)
            for (r,c,_),(_,_,name) in zip(hyp_pos, invh_pos):
                self._btn_refs[(r,c)].setText(name)
        else:
            for r,c,name in tri_pos:
                self._btn_refs[(r,c)].setText(name)
            for r,c,name in hyp_pos:
                self._btn_refs[(r,c)].setText(name)

    # ---------------- 필수/공학 메서드 구현 ----------------
    # π
    def pi_const(self):
        self._set_value(math.pi)

    # e
    def e_const(self):
        self._set_value(math.e)

    # x²
    def square(self):
        self._set_value(self._current() ** 2)

    # x³
    def cube(self):
        self._set_value(self._current() ** 3)

    # √x
    def sqrt(self):
        x = self._current()
        if x < 0:
            self.error = True; self.refresh_display(); return
        self._set_value(math.sqrt(x))

    # 1/x
    def reciprocal(self):
        x = self._current()
        if x == 0:
            self.error = True; self.refresh_display(); return
        self._set_value(1.0 / x)

    # x! (정수, 0 이상)
    def factorial(self):
        x = self._current()
        if x < 0 or int(x) != x:
            self.error = True; self.refresh_display(); return
        self._set_value(math.factorial(int(x)))

    # ln
    def ln(self):
        x = self._current()
        if x <= 0:
            self.error = True; self.refresh_display(); return
        self._set_value(math.log(x))

    # log10
    def log10(self):
        x = self._current()
        if x <= 0:
            self.error = True; self.refresh_display(); return
        self._set_value(math.log10(x))

    # 10^x
    def pow10(self):
        self._set_value(10 ** self._current())

    # 삼각함수 (DEG/RAD 지원)
    def sin(self):
        self._set_value(math.sin(self._deg2rad(self._current())))

    def cos(self):
        self._set_value(math.cos(self._deg2rad(self._current())))

    def tan(self):
        self._set_value(math.tan(self._deg2rad(self._current())))

    # 역삼각 (결과 각도는 현재 모드에 맞춤)
    def asin(self):
        x = self._current()
        if x < -1 or x > 1:
            self.error = True; self.refresh_display(); return
        v = math.asin(x)
        self._set_value(self._rad2deg(v))

    def acos(self):
        x = self._current()
        if x < -1 or x > 1:
            self.error = True; self.refresh_display(); return
        v = math.acos(x)
        self._set_value(self._rad2deg(v))

    def atan(self):
        v = math.atan(self._current())
        self._set_value(self._rad2deg(v))

    # 쌍곡선
    def sinh(self):
        self._set_value(math.sinh(self._current()))

    def cosh(self):
        self._set_value(math.cosh(self._current()))

    def tanh(self):
        self._set_value(math.tanh(self._current()))

    # 역쌍곡선
    def asinh(self):
        self._set_value(math.asinh(self._current()))

    def acosh(self):
        x = self._current()
        if x < 1:
            self.error = True; self.refresh_display(); return
        self._set_value(math.acosh(x))

    def atanh(self):
        x = self._current()
        if x <= -1 or x >= 1:
            self.error = True; self.refresh_display(); return
        self._set_value(math.atanh(x))

# -------------------------- 실행 --------------------------
def main():
    app = QApplication(sys.argv)
    win = EngineeringCalculator()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
