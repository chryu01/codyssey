# engineering_calculator.py
# PyQt6 기반 '아이폰 가로(공학용)' 스타일 UI + 실제 공학용 기능 동작
# - 출력 우측 정렬, 버튼 배치 유사
# - 색상/모양 동일 불필요
# - 기본 사칙연산, 괄호, %/±, 공학용 함수들 동작
# - DEG/RAD 토글, 2nd(역함수/대체기능) 토글, Ans(직전 결과), Rand(0~1)
# - x^y는 Python '**'로 처리, y√x는 x ** (1/y)

import sys
import math
import random
import re
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QGridLayout,
    QPushButton, QLineEdit, QSizePolicy
)


# ---- 안전 평가용 래퍼: DEG/RAD 지원 ----
class MathCtx:
    def __init__(self, use_deg: bool, ans: float):
        self.use_deg = use_deg
        self.ans = ans

    # 삼각함수 (DEG면 라디안 변환)
    def sin(self, x): return math.sin(math.radians(x) if self.use_deg else x)
    def cos(self, x): return math.cos(math.radians(x) if self.use_deg else x)
    def tan(self, x): return math.tan(math.radians(x) if self.use_deg else x)

    # 역삼각함수 (DEG면 결과를 도로 DEG로)
    def asin(self, x):
        v = math.asin(x)
        return math.degrees(v) if self.use_deg else v

    def acos(self, x):
        v = math.acos(x)
        return math.degrees(v) if self.use_deg else v

    def atan(self, x):
        v = math.atan(x)
        return math.degrees(v) if self.use_deg else v

    # 하이퍼볼릭
    def sinh(self, x): return math.sinh(x)
    def cosh(self, x): return math.cosh(x)
    def tanh(self, x): return math.tanh(x)

    # 로그/지수
    def ln(self, x): return math.log(x)
    def log(self, x): return math.log10(x)
    def exp(self, x): return math.exp(x)
    def pow10(self, x): return 10 ** x

    # 루트/멱/기타
    def sqrt(self, x): return math.sqrt(x)
    def cbrt(self, x):  # (2nd 토글 시 √ ↔ ∛x로 쓰고 싶으면 사용 가능)
        return x ** (1/3) if x >= 0 else -((-x) ** (1/3))
    def inv(self, x): return 1/x
    def fact(self, n):
        if n < 0 or int(n) != n:
            raise ValueError("factorial() only defined for non-negative integers")
        return math.factorial(int(n))

    # 상수 & 기타
    @property
    def pi(self): return math.pi
    @property
    def e(self): return math.e
    def yroot(self, x, y): return x ** (1.0 / y)
    def Rand(self): return random.random()
    def Ans(self): return self.ans


class EngineeringCalculator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Engineering Calculator")
        self.setMinimumSize(680, 360)

        # 상태
        self.entry = ""           # 사용자가 만드는 수식 문자열
        self.last_result = 0.0    # Ans
        self.use_deg = True       # DEG/RAD
        self.second_on = False    # 2nd 토글

        # UI 구성
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

        # 기본(2nd OFF) 라벨
        self.rows_default = [
            ["2nd", "(", ")", "Deg",  "AC", "±", "%", "÷"],
            ["sin", "cos", "tan", "π", "7",  "8", "9", "×"],
            ["ln",  "log", "e",  "x^y","4",  "5", "6", "−"],
            ["x²",  "x³",  "√",  "1/x","1",  "2", "3", "+"],
            ["x!",  "Rand","Exp","Ans","0",  ".", "=", "▯"],
        ]
        # 2nd ON 라벨 (필요한 것만 치환)
        self.rows_second = [
            ["2nd", "(", ")", "Deg",  "AC", "±", "%", "÷"],
            ["asin","acos","atan","π", "7",  "8", "9", "×"],
            ["exp", "10^x","e", "y√x","4",  "5", "6", "−"],
            ["x²",  "x³",  "√",  "1/x","1",  "2", "3", "+"],
            ["x!",  "Rand","Exp","Ans","0",  ".", "=", "▯"],
        ]

        # 버튼 위젯 보관해서 2nd 토글 시 텍스트 교체
        self.btns = []

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
                btn.setStyleSheet(
                    "QPushButton{background:#d9d9d9;border:none;border-radius:12px;padding:10px;}"
                    "QPushButton:pressed{opacity:.88;}")
            elif role == "operator":
                btn.setStyleSheet(
                    "QPushButton{background:#ff9500;color:white;border:none;border-radius:12px;padding:10px;}"
                    "QPushButton:pressed{opacity:.9;}")
            else:
                btn.setStyleSheet(
                    "QPushButton{background:#505050;color:white;border:none;border-radius:12px;padding:10px;}"
                    "QPushButton:pressed{opacity:.9;}")
            return btn

        # 초기 배치(기본 라벨)
        for r, row in enumerate(self.rows_default):
            row_btns = []
            for c, label in enumerate(row):
                if label == "▯":
                    dummy = QWidget()
                    grid.addWidget(dummy, r, c)
                    row_btns.append(None)
                    continue

                # 역할 분류
                if r == 0 and 4 <= c <= 6:
                    role = "function"  # AC, ±, %
                elif c == 7 or label in ("=",):
                    role = "operator"  # 우측 연산자 열
                elif c >= 4 and label.isdigit():
                    role = "digit"     # 숫자
                else:
                    role = "sci"       # 과학/기타

                btn = make_button(label, role)
                btn.clicked.connect(lambda _, t=label: self.on_button(t))
                grid.addWidget(btn, r, c)
                row_btns.append(btn)
            self.btns.append(row_btns)

        self.setStyleSheet("""
        QMainWindow { background: #000; }
        #display { background: #000; color: #fff; border: none; padding: 8px 12px; }
        """)

        self.refresh_display("0")

    # ---------------- 유틸 ----------------
    def refresh_display(self, text: str | None = None):
        if text is not None:
            self.display.setText(text)
        else:
            self.display.setText(self.entry if self.entry else "0")

    def append_token(self, tok: str):
        self.entry += tok
        self.refresh_display()

    def replace_last_number(self, transform_fn):
        """
        식(entry)에서 마지막 '숫자(소수점 포함) 혹은 함수호출 결과 숫자' 토큰을 찾아 변환.
        """
        m = re.search(r"([0-9]*\.?[0-9]+)$", self.entry)
        if m:
            s, e = m.span(1)
            num = m.group(1)
            try:
                v = float(num)
                nv = transform_fn(v)
                if nv == int(nv):
                    repl = str(int(nv))
                else:
                    repl = str(nv)
                self.entry = self.entry[:s] + repl + self.entry[e:]
            except Exception:
                self.show_error()
        else:
            # 마지막이 숫자가 아니면 Ans에 대해 적용
            try:
                nv = transform_fn(self.last_result)
                self.entry = (str(int(nv)) if nv == int(nv) else str(nv))
            except Exception:
                self.show_error()
        self.refresh_display()

    def show_error(self, msg: str = "Error"):
        self.refresh_display(msg)
        # 에러 후 입력 초기화
        self.entry = ""

    def set_deg_label(self):
        # (0,3)의 버튼 텍스트 갱신
        btn = self.btns[0][3]
        if btn:
            btn.setText("Deg" if self.use_deg else "Rad")

    def toggle_second_labels(self):
        src = self.rows_second if self.second_on else self.rows_default
        for r in range(len(src)):
            for c in range(len(src[r])):
                btn = self.btns[r][c]
                if btn and src[r][c] != "▯":
                    btn.setText(src[r][c])

    # ---------------- 버튼 핸들러 ----------------
    def on_button(self, label: str):
        # 2nd 토글
        if label == "2nd":
            self.second_on = not self.second_on
            self.toggle_second_labels()
            return

        # DEG/RAD
        if label in ("Deg", "Rad"):
            self.use_deg = not self.use_deg
            self.set_deg_label()
            return

        # AC
        if label == "AC":
            self.entry = ""
            self.refresh_display("0")
            return

        # ± (마지막 숫자 부호 토글)
        if label == "±":
            def neg(v): return -v
            self.replace_last_number(neg)
            return

        # % (마지막 숫자를 /100)
        if label == "%":
            def pct(v): return v / 100.0
            self.replace_last_number(pct)
            return

        # 숫자/점
        if label.isdigit():
            self.append_token(label)
            return
        if label == ".":
            # 숫자 뒤가 아니면 0. 시작
            if not self.entry or not re.search(r"[0-9]$", self.entry):
                self.append_token("0.")
            else:
                # 직전 숫자에 .이 없으면 추가
                m = re.search(r"([0-9]*\.?[0-9]+)$", self.entry)
                if m and "." in m.group(1):
                    return
                self.append_token(".")
            return

        # 괄호
        if label in ("(", ")"):
            self.append_token(label)
            return

        # 사칙연산
        if label in ("+", "−", "×", "÷"):
            op_map = {"−": "-", "×": "*", "÷": "/"}
            self.append_token(op_map.get(label, label))
            return

        # 상수
        if label == "π":
            self.append_token("pi")
            return
        if label == "e":
            self.append_token("e")
            return
        if label == "Ans":
            # Ans는 즉시 값으로 확정해서 넣음(표현 안전)
            val = self.last_result
            self.append_token(str(int(val)) if val == int(val) else str(val))
            return
        if label == "Rand":
            # 즉시 난수 값을 기입
            r = random.random()
            self.append_token(str(r))
            return

        # 멱/루트/역수/팩토리얼/로그/삼각함수 등
        # 2nd 토글 상태에 따라 라벨이 바뀌므로 버튼 텍스트를 그대로 쓰되 실행 토큰으로 매핑
        token_map = {
            "x²": "(**2)",
            "x³": "(**3)",
            "√": "sqrt(",
            "1/x": "inv(",
            "x!": "fact(",
            "ln": "ln(",
            "log": "log(",
            "Exp": "exp(",
            "exp": "exp(",
            "10^x": "pow10(",
            "x^y": "**",
            "y√x": "yroot(",
            # 삼각/역삼각
            "sin": "sin(", "cos": "cos(", "tan": "tan(",
            "asin": "asin(", "acos": "acos(", "atan": "atan(",
        }

        if label in token_map:
            tok = token_map[label]
            if tok == "**":
                # 이항연산자: x ** y 형태 만들기
                # 끝이 연산자인 경우에는 무시
                if not self.entry or re.search(r"[*+\-/(]$", self.entry):
                    return
                self.append_token("**")
            elif label == "y√x":
                # y√x는 yroot(x,y) 형태 필요 -> 현재 x를 먼저 넣고 후에 , 대기
                # UX 단순화를 위해 "yroot(" 만 넣고 사용자가 x,y 순으로 입력하도록 함: yroot(x,y)
                self.append_token("yroot(")
            elif tok in ("(**2)", "(**3)"):
                # 마지막 항에 제곱/세제곱 적용: 마지막 숫자/괄호식에 붙이기
                # 단순 구현: 바로 토큰 추가 (사용자가 x² 누르면 ...x**2)
                self.append_token(tok)
            else:
                self.append_token(tok)
            return

        # '=' 평가
        if label == "=":
            self.evaluate()
            return

        # 그 외는 무시
        return

    # ---------------- 평가 ----------------
    def evaluate(self):
        if not self.entry:
            self.refresh_display("0")
            return

        expr = self.entry

        # 사용자가 'sin(' 등 입력 후 닫지 않았으면 자동 닫기 시도 (간단 보완)
        open_paren = expr.count("(")
        close_paren = expr.count(")")
        if open_paren > close_paren:
            expr += ")" * (open_paren - close_paren)

        # 안전 eval 환경 구성
        ctx = MathCtx(self.use_deg, self.last_result)
        safe_globals = {
            "__builtins__": None,
            # 함수/상수 노출
            "sin": ctx.sin, "cos": ctx.cos, "tan": ctx.tan,
            "asin": ctx.asin, "acos": ctx.acos, "atan": ctx.atan,
            "sinh": ctx.sinh, "cosh": ctx.cosh, "tanh": ctx.tanh,
            "ln": ctx.ln, "log": ctx.log, "exp": ctx.exp, "pow10": ctx.pow10,
            "sqrt": ctx.sqrt, "cbrt": ctx.cbrt, "inv": ctx.inv, "fact": ctx.fact,
            "yroot": ctx.yroot,
            "pi": ctx.pi, "e": ctx.e,
        }
        safe_locals = {}

        try:
            # 표현 보정: x(**2) 같은 패턴은 허용하지만, 숫자 바로 뒤 괄호는 OK
            # 불필요 변환 없음. (x^y 버튼은 '**'로 이미 변환)
            result = eval(expr, safe_globals, safe_locals)

            # 표시 포맷: 정수면 소수점 제거
            if isinstance(result, (int, float)) and math.isfinite(result):
                disp = str(int(result)) if result == int(result) else str(result)
            else:
                # NaN/Inf 혹은 비수치
                disp = str(result)

            self.last_result = float(result) if isinstance(result, (int, float)) and math.isfinite(result) else self.last_result
            self.refresh_display(disp)
            # 결과를 새로운 식의 시작으로 삼음
            self.entry = disp
        except Exception:
            self.show_error("Error")


def main():
    app = QApplication(sys.argv)
    win = EngineeringCalculator()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
