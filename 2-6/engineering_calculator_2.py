# engineering_calculator.py
# - Calculator 상속
# - 아이폰 가로(공학용) UI
# - 함수 버튼을 누르면 "sin(" 같은 토큰이 화면에 바로 찍힘 → 숫자 입력 후 ')'로 닫아 식 작성
# - '=' 후 결과에서 바로 연산/함수 이어가기 가능
# - 요구된 공학 메서드: sin, cos, tan, sinh, cosh, tanh, pi_const, square, cube 구현
# - 안전 평가 컨텍스트(eval)로 식 계산, DEG/RAD 지원

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

# --------------------- 기본 Calculator (문제 4에서 사용한 형태 요약) ---------------------
class Calculator(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Calculator")
        self.setMinimumSize(320, 480)

        # 상태(기본기)
        self.entry_str = "0"
        self.accumulator = 0.0
        self.pending_op = None
        self.last_operand = None
        self.new_entry = True
        self.error = False

        # 세로 UI (상속 후 교체될 예정)
        central = QWidget(self); self.setCentralWidget(central)
        main = QVBoxLayout(central); main.setContentsMargins(12,12,12,12); main.setSpacing(12)

        self.display = QLineEdit("0", self)
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.display.setObjectName("display")
        self.display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        dfont = QFont("Arial", 36); dfont.setBold(True); self.display.setFont(dfont)
        self.display.setMinimumHeight(100)
        main.addWidget(self.display)

        grid = QGridLayout(); grid.setSpacing(8); main.addLayout(grid)

        rows = [["AC","±","%","÷"],["7","8","9","×"],["4","5","6","−"],["1","2","3","+"]]
        def make_button(text, role):
            b = QPushButton(text); b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            f = QFont("Arial", 20);  f.setPointSize(24) if text in ["÷","×","−","+","="] else None; b.setFont(f)
            if role=="function":
                b.setStyleSheet("QPushButton{background:#d9d9d9;border:none;border-radius:12px;padding:12px;}")
            elif role=="operator":
                b.setStyleSheet("QPushButton{background:#ff9500;color:white;border:none;border-radius:12px;padding:12px;}")
            else:
                b.setStyleSheet("QPushButton{background:#505050;color:white;border:none;border-radius:12px;padding:12px;}")
            return b
        for r,row in enumerate(rows):
            for c,label in enumerate(row):
                role = "function" if (r==0 and c<=2) else ("operator" if c==3 else "digit")
                b = make_button(label, role); b.clicked.connect(lambda _,t=label:self.on_button(t))
                grid.addWidget(b, r, c)
        z = make_button("0","digit"); z.clicked.connect(lambda _,t="0":self.on_button(t)); grid.addWidget(z,4,0,1,2)
        d = make_button(".","digit"); d.clicked.connect(lambda _,t=".":self.on_button(t)); grid.addWidget(d,4,2,1,1)
        e = make_button("=","operator"); e.clicked.connect(lambda _,t="=":self.on_button(t)); grid.addWidget(e,4,3,1,1)

        self.setStyleSheet("QMainWindow{background:#000;} #display{background:#000;color:#fff;border:none;padding:8px 12px;}")

        self.refresh_display()

    # --- helpers / minimal logic (상속 클래스에서 쓰진 않음) ---
    def format_number(self, value: float) -> str:
        try:
            s = f"{value:.12g}"
            if "." in s: s = s.rstrip("0").rstrip(".")
            return s
        except Exception:
            return "0"
    def current_entry_value(self) -> float:
        try: return float(self.entry_str)
        except: return 0.0
    def set_entry_from_value(self, value: float): self.entry_str = self.format_number(value)
    def refresh_display(self): self.display.setText("Error" if self.error else self.entry_str)

    # --- vanilla handlers (상속 클래스에서 대체함) ---
    def on_button(self, label: str): pass  # 여기선 사용 안 함


# --------------------- EngineeringCalculator ---------------------
class EngineeringCalculator(Calculator):
    def __init__(self):
        super().__init__()  # 상태/표시 위젯 생성만 활용

        # 부모 세로 UI 제거 → 가로 공학용 UI로 교체
        old = self.takeCentralWidget()
        if old: old.deleteLater()

        self.setWindowTitle("Engineering Calculator")
        self.setMinimumSize(980, 460)

        # 표현식 모델 상태
        self.expr = ""            # 화면에 그대로 보이는 수식 문자열
        self.result_mode = False  # 직전에 = 으로 결과 표시 중이면 True
        self.last_result = 0.0

        # 공학 상태
        self.use_deg = True
        self.second_on = False
        self.memory = 0.0

        # 새 UI
        central = QWidget(self); self.setCentralWidget(central)
        main = QVBoxLayout(central); main.setContentsMargins(12,12,12,12); main.setSpacing(12)

        self.display = QLineEdit("0", self)
        self.display.setReadOnly(True)
        self.display.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.display.setObjectName("display")
        self.display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        dfont = QFont("Arial", 40); dfont.setBold(True); self.display.setFont(dfont)
        self.display.setMinimumHeight(96)
        main.addWidget(self.display)

        grid = QGridLayout(); grid.setSpacing(8); main.addLayout(grid)

        # iPhone 가로 느낌(좌 6열: 공학 / 우 4열: 표준)
        sci_rows = [
            ["2nd","(",")","Deg","mc","mr"],
            ["x²","x³","xʸ","10^x","√","1/x"],
            ["x!","y√x","ln","log","e","π"],
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

        def make_btn(text, role):
            b = QPushButton(text)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            f = QFont("Arial", 18); 
            if text in ["÷","×","−","+","="]: f.setPointSize(22)
            b.setFont(f)
            if role=="op":   b.setStyleSheet("QPushButton{background:#ff9500;color:white;border:none;border-radius:18px;padding:12px;} QPushButton:pressed{opacity:.9;}")
            elif role=="fn": b.setStyleSheet("QPushButton{background:#d9d9d9;border:none;border-radius:18px;padding:12px;} QPushButton:pressed{opacity:.88;}")
            else:            b.setStyleSheet("QPushButton{background:#505050;color:white;border:none;border-radius:18px;padding:12px;} QPushButton:pressed{opacity:.9;}")
            return b

        self._btn = {}
        for r in range(5):
            # 왼쪽 6개
            for c in range(6):
                label = sci_rows[r][c]
                b = make_btn(label, "fn")
                b.clicked.connect(lambda _, t=label: self.on_sci(t))
                grid.addWidget(b, r, c)
                self._btn[(r,c)] = b
            # 오른쪽 4개
            for c in range(4):
                label = std_rows[r][c]
                role = "fn" if (r==0 and c<=2) else ("op" if c==3 or label=="=" else "num")
                b = make_btn(label, role)
                b.clicked.connect(lambda _, t=label: self.on_std(t))
                grid.addWidget(b, r, 6+c)

        self.setStyleSheet("QMainWindow{background:#000;} #display{background:#000;color:#fff;border:none;padding:8px 12px;}")

        self._refresh()

    # --------------------- 공학 메서드(요구된 것) ---------------------
    # 아래 메서드들은 평가 컨텍스트에서 식의 함수로 사용됨 (sin(…), square(…))
    def _to_rad(self, x): return math.radians(x) if self.use_deg else x
    def _to_deg(self, x): return math.degrees(x) if self.use_deg else x

    def sin(self, x):  return math.sin(self._to_rad(x))
    def cos(self, x):  return math.cos(self._to_rad(x))
    def tan(self, x):  return math.tan(self._to_rad(x))

    def sinh(self, x): return math.sinh(x)
    def cosh(self, x): return math.cosh(x)
    def tanh(self, x): return math.tanh(x)

    def square(self, x): return x**2
    def cube(self, x):   return x**3
    def pi_const(self):  return math.pi

    # 추가 함수(평가 컨텍스트 용도)
    def asin_func(self, x):  return self._to_deg(math.asin(x))
    def acos_func(self, x):  return self._to_deg(math.acos(x))
    def atan_func(self, x):  return self._to_deg(math.atan(x))
    def asinh_func(self, x): return math.asinh(x)
    def acosh_func(self, x): return math.acosh(x)
    def atanh_func(self, x): return math.atanh(x)
    def inv(self, x):        return 1.0/x
    def sqrt(self, x):       return math.sqrt(x)
    def fact(self, n):
        if n < 0 or int(n)!=n: raise ValueError("factorial domain")
        return math.factorial(int(n))
    def ln(self, x):         return math.log(x)
    def log10(self, x):      return math.log10(x)
    def pow10(self, x):      return 10**x
    def yroot(self, x, y):   return x**(1.0/y)

    # --------------------- 표시/입력 유틸 ---------------------
    def _refresh(self):
        self.display.setText(self.expr if self.expr else "0")

    def _fmt(self, v: float) -> str:
        s = f"{v:.12g}"
        if "." in s: s = s.rstrip("0").rstrip(".")
        return s

    def _append(self, s: str):
        # '=' 직후에 숫자/괄호/함수가 오면 새 수식 시작, 연산자가 오면 결과 뒤에 이어붙임
        if self.result_mode:
            if s in {"+","−","×","÷"}:
                self.expr = self._fmt(self.last_result) + s
            elif s.endswith("("):  # 함수 시작
                self.expr = f"{s}{self._fmt(self.last_result)}"
            elif s in (")",):
                # 닫을 건 없으니 무시
                pass
            else:
                # 숫자/점/EE/상수 등은 새 식
                self.expr = s
            self.result_mode = False
        else:
            # 연산자 중복 방지(마지막이 연산자일 때 교체)
            if s in {"+","−","×","÷"} and (not self.expr or self.expr[-1] in "+−×÷"):
                if self.expr: self.expr = self.expr[:-1] + s
                else: return
            else:
                self.expr += s
        self._refresh()

    def _insert_func(self, name: str):
        # sin → "sin(" 식으로 토큰 추가
        self._append(f"{name}(")

    def _replace_last_number(self, transform):
        # 마지막 숫자(과학표기 포함) 찾아 변환
        m = re.search(r"([-+]?\d*\.?\d+(?:e[+\-]?\d+)?)\s*$", self.expr, re.IGNORECASE)
        if m:
            s, e = m.span(1)
            try:
                v = float(m.group(1))
                nv = transform(v)
                self.expr = self.expr[:s] + self._fmt(nv) + self.expr[e:]
                self._refresh()
            except Exception:
                self._error()
        else:
            # 없으면 결과값에 적용
            try:
                nv = transform(self.last_result)
                self.expr = self._fmt(nv)
                self._refresh()
            except Exception:
                self._error()

    def _error(self):
        self.expr = "Error"
        self.display.setText("Error")
        self.result_mode = True  # 다음 입력 시 새 시작

    # --------------------- 버튼 핸들러(우측 표준) ---------------------
    def on_std(self, label: str):
        if label.isdigit():
            self._append(label); return
        if label == ".":
            # 직전 숫자에 점이 없을 때만
            m = re.search(r"(\d*\.?\d*(?:e[+\-]?\d+)?)$", self.expr, re.IGNORECASE)
            if m and "." in m.group(1):
                return
            self._append("."); return
        if label in ("+","−","×","÷"):
            self._append(label); return
        if label == "(" or label == ")":
            self._append(label); return
        if label == "AC":
            self.expr = ""; self.result_mode = False; self._refresh(); return
        if label == "±":
            self._replace_last_number(lambda v: -v); return
        if label == "%":
            self._replace_last_number(lambda v: v/100.0); return
        if label == "EE":
            # 과학표기: 숫자 뒤에 'e' 붙이기(없으면 1e 시작)
            if not self.expr or not re.search(r"\d$", self.expr):
                self._append("1e")
            else:
                if not re.search(r"e[+\-]?\d*$", self.expr, re.IGNORECASE):
                    self._append("e")
            return
        if label == "=":
            self._evaluate(); return

    # --------------------- 버튼 핸들러(좌측 공학) ---------------------
    def on_sci(self, label: str):
        # 토글
        if label == "2nd":
            self.second_on = not self.second_on
            self._swap_2nd_labels()
            return
        if label in ("Deg","Rad"):
            self.use_deg = not self.use_deg
            btn = self._btn.get((0,3))
            if btn: btn.setText("Deg" if self.use_deg else "Rad")
            return

        # 메모리
        if label == "mc": self.memory = 0.0; return
        if label == "mr":
            s = self._fmt(self.memory); self._append(s); return

        # 상수/난수
        if label == "π":   self._append("pi"); return
        if label == "e":   self._append("eul") if False else self._append("e")  # python literal과 충돌 없음
        if label == "Rand": self._append(self._fmt(random.random())); return

        # 함수/연산 토큰
        if label in {"sin","cos","tan","sinh","cosh","tanh","asin","acos","atan","asinh","acosh","atanh","ln","log","10^x","√","1/x","x!","y√x"}:
            if label == "10^x": self._insert_func("pow10"); return
            if label == "√":    self._insert_func("sqrt");  return
            if label == "1/x":  self._insert_func("inv");   return
            if label == "x!":   self._insert_func("fact");  return
            if label == "y√x":
                # yroot(x, y) 형태 → 결과에 이어 쓰려면 yroot(result, …)로 프리필
                if self.result_mode:
                    self.expr = f"yroot({self._fmt(self.last_result)},"
                    self.result_mode = False
                    self._refresh()
                else:
                    self._append("yroot(")
                return
            # 나머지 함수들은 그대로 이름(
            self._insert_func(label); return

        # 멱
        if label == "xʸ":
            # '**' 토큰(화면엔 그대로 '**' 보이게)
            self._append("**"); return
        if label == "x²":
            # 바로 '**2' 붙이기 또는 (결과) 적용
            if self.result_mode:
                self.expr = f"({self._fmt(self.last_result)})**2"; self.result_mode=False; self._refresh()
            else:
                self._append("**2")
            return
        if label == "x³":
            if self.result_mode:
                self.expr = f"({self._fmt(self.last_result)})**3"; self.result_mode=False; self._refresh()
            else:
                self._append("**3")
            return

        # 괄호
        if label in ("(",")"):
            self._append(label); return

    def _swap_2nd_labels(self):
        tri = [("sin",(3,0)),("cos",(3,1)),("tan",(3,2))]
        inv = [("asin",(4,0)),("acos",(4,1)),("atan",(4,2))]
        hyp = [("sinh",(3,3)),("cosh",(3,4)),("tanh",(3,5))]
        invh= [("asinh",(4,3)),("acosh",(4,4)),("atanh",(4,5))]
        if self.second_on:
            for (name,pos), (iname,_) in zip(tri, inv):  self._btn[pos].setText(iname)
            for (name,pos), (iname,_) in zip(hyp, invh): self._btn[pos].setText(iname)
        else:
            for name,pos in tri:  self._btn[pos].setText(name)
            for name,pos in hyp:  self._btn[pos].setText(name)

    # --------------------- 평가 ---------------------
    def _evaluate(self):
        if not self.expr:
            self._refresh(); return
        expr = self.expr

        # 자동 괄호 닫기
        opens = expr.count("("); closes = expr.count(")")
        if opens > closes: expr += ")"*(opens-closes)

        # 화면 토큰 → 파이썬 표현으로 변환
        trans = (expr
                 .replace("×","*")
                 .replace("÷","/")
                 .replace("−","-"))
        # 안전 컨텍스트 구성
        safe_globals = {"__builtins__": None,
                        # 요구된 메서드(바운드)와 추가 함수들
                        "sin": self.sin, "cos": self.cos, "tan": self.tan,
                        "sinh": self.sinh, "cosh": self.cosh, "tanh": self.tanh,
                        "asin": self.asin_func, "acos": self.acos_func, "atan": self.atan_func,
                        "asinh": self.asinh_func, "acosh": self.acosh_func, "atanh": self.atanh_func,
                        "square": self.square, "cube": self.cube,
                        "ln": self.ln, "log": self.log10, "pow10": self.pow10,
                        "sqrt": self.sqrt, "inv": self.inv, "fact": self.fact, "yroot": self.yroot,
                        "pi": math.pi, "e": math.e}
        try:
            result = eval(trans, safe_globals, {})
            if not isinstance(result, (int,float)) or not math.isfinite(result):
                raise ValueError("Invalid result")
            self.last_result = float(result)
            self.expr = self._fmt(self.last_result)
            self.result_mode = True
            self._refresh()
        except Exception:
            self._error()


# --------------------- 실행 ---------------------
def main():
    app = QApplication(sys.argv)
    win = EngineeringCalculator()
    win.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
