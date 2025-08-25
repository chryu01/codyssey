#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
cctv.py
- CCTV.zip(또는 절대경로)의 압축을 풀어 "CCTV" 폴더를 만든다.
- CCTV 폴더의 이미지를 하나 띄우고, ←/→ 로 이전/다음 사진을 본다.
- ESC 로 종료한다.
- 이미지 읽기/표시는 Pillow(PIL) 라이브러리를 사용한다 → JPG 포함 대부분 포맷 지원.
"""

import sys                      # sys.exit(1) 등: 프로그램 즉시 종료, 실행기 정보에 접근
import zipfile                  # zipfile.ZipFile: ZIP 압축파일 열기/목록/해제 기능 제공 (표준 라이브러리)
from pathlib import Path        # Path 객체: 파일/폴더 경로를 객체처럼 다룸 (조합/검사/순회 등)
import tkinter as tk            # tk.Tk/Label/Canvas 등: GUI(창, 위젯) 만드는 표준 GUI 라이브러리
from tkinter import messagebox  # messagebox.showerror 등: 오류/알림 팝업창 띄우기

# >>> 이미지 표시용 외부 라이브러리 (허용) <<<
# pip install pillow 로 설치 가능
from PIL import Image, ImageTk
# PIL.Image: 이미지 파일 열기/변환/리사이즈 등 이미지 처리 기능 제공
# PIL.ImageTk.PhotoImage: Pillow 이미지를 Tkinter가 화면에 그릴 수 있는 객체로 변환

# ===================== 사용자 설정 =====================
# 절대 경로를 직접 쓰고 싶다면 아래 ZIP_PATH를 수정하세요.
# 예) Windows: r"C:\Users\me\Desktop\cctv.zip"
#     macOS  : "/Users/me/Desktop/cctv.zip"
ZIP_PATH: Path | None = None  # None이면 스크립트 폴더의 "CCTV.zip"을 자동으로 찾음
# =======================================================

# Path(__file__).resolve().parent: 현재 파이썬 파일이 있는 폴더(절대경로)
SCRIPT_DIR = Path(__file__).resolve().parent
# 압축을 풀 대상 폴더: 현재 스크립트가 있는 폴더 아래 "CCTV"
DEST_DIR = (SCRIPT_DIR / "CCTV").resolve()

# Pillow가 잘 지원하는 이미지 확장자 목록 (여기에 포함된 파일만 모아 표시)
SUPPORTED_EXTS = (
    ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tif", ".tiff", ".webp"
)


def resolve_zip_path() -> Path:
    """
    ZIP 파일의 실제 경로를 결정한다.
    - 사용자가 ZIP_PATH를 지정했으면 그 절대경로를 사용
    - 아니면 스크립트 폴더의 "CCTV.zip"을 기본으로 사용
    Path.resolve(): 경로를 절대경로로 변환
    """
    if ZIP_PATH:
        return Path(ZIP_PATH).resolve()
    return (SCRIPT_DIR / "CCTV.zip").resolve()


def unzip_to_dest(zip_path: Path, dest: Path) -> None:
    """
    zip을 dest 폴더에 해제한다. (표준 라이브러리만 사용)
    - zip_path.exists(): 파일 존재 여부 확인 (True/False)
    - dest.mkdir(parents=True, exist_ok=True): 폴더 생성 (이미 있으면 에러 없이 통과)
    - zipfile.ZipFile(zip_path, "r"): ZIP 파일을 '읽기' 모드로 연다
    - ZipFile.extractall(dest): ZIP 내용 전체를 지정 폴더에 해제
    """
    if not zip_path.exists():
        messagebox.showerror("오류", f"압축 파일을 찾을 수 없습니다:\n{zip_path}")
        sys.exit(1)  # 오류시 프로그램 종료
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:  # 컨텍스트 매니저: 사용 후 자동 닫힘
        zf.extractall(dest)


def collect_images(dest: Path) -> list[Path]:
    """
    DEST_DIR 하위(모든 하위폴더 포함)에서 지원 확장자 이미지를 수집해 정렬하여 반환.
    - dest.rglob("*"): 하위 모든 경로를 재귀적으로 순회
    - p.is_file(): 파일인지 확인 (폴더 제외)
    - p.suffix.lower(): 파일 확장자를 소문자로 가져옴
    - list.sort(key=...): 경로 문자열 기준 정렬 → 사람이 보기 편한 순서
    """
    files: list[Path] = []
    if dest.exists():
        for p in dest.rglob("*"):
            if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS:
                files.append(p)
    files.sort(key=lambda x: x.as_posix().lower())
    return files


class CCTVViewer(tk.Tk):
    """
    Tkinter 기반 이미지 뷰어.
    - tk.Tk: 최상위 윈도우(앱 창) 객체
    - tk.Label: 텍스트 표시 위젯
    - tk.Canvas: 그림/이미지 등을 그릴 수 있는 도화지 위젯
    - 이벤트 바인딩(bind): 키보드 입력(←/→/ESC)과 함수 연결
    - Pillow(Image, ImageTk)로 이미지를 읽고 Tk에서 그릴 수 있게 변환
    """

    def __init__(self, images: list[Path]):
        super().__init__()
        self.title("CCTV Viewer (←/→, ESC)")  # 창 제목
        self.geometry("960x720")               # 초기 창 크기
        self.minsize(640, 480)                 # 최소 창 크기

        self.images = images   # 표시할 이미지 파일 경로 리스트
        self.index = 0         # 현재 표시 중인 이미지의 인덱스(0부터 시작)

        # 현재 표시 중인 PhotoImage를 보관해 가비지 컬렉션으로 사라지지 않게 유지
        self._current_tk_img: ImageTk.PhotoImage | None = None

        # ---- 상단 정보 라벨: 파일명/순번 표시 ----
        # tk.Label(..., anchor="w"): 왼쪽 정렬
        self.label_info = tk.Label(self, text="", anchor="w")
        # pack(fill="x"): 가로로 끝까지 채우며 배치 / padx/pady: 여백
        self.label_info.pack(fill="x", padx=8, pady=(8, 0))

        # ---- 가운데 캔버스: 이미지를 실제로 그리는 영역 ----
        # bg="black": 배경 검은색, highlightthickness=0: 외곽선 제거
        self.canvas = tk.Canvas(self, bg="black", highlightthickness=0)
        # pack(fill="both", expand=True): 창 크기 변화에 맞춰 가로/세로 모두 늘어남
        self.canvas.pack(fill="both", expand=True, padx=8, pady=8)

        # ---- 하단 도움말 라벨 ----
        self.label_hint = tk.Label(self, text="← 이전 | → 다음 | ESC 종료", anchor="e")
        self.label_hint.pack(fill="x", padx=8, pady=(0, 8))

        # ---- 키보드 이벤트 바인딩 ----
        # self.bind("<Left>", 함수): 왼쪽 화살표 키를 누르면 해당 함수를 호출
        self.bind("<Left>", self.prev_image)
        self.bind("<Right>", self.next_image)
        self.bind("<Escape>", lambda e: self.destroy())  # ESC로 창 닫기
        self.bind("<Configure>", self.on_resize)         # 창 크기 바뀔 때 호출

        # ---- 처음 화면 표시 ----
        if self.images:
            self.show_image(self.index)
        else:
            self.show_empty_message()

    # ---------- 이벤트 핸들러 ----------
    def prev_image(self, event=None):
        """
        ← 키를 눌렀을 때 호출.
        - (self.index - 1) % len(self.images): 맨 앞에서 다시 누르면 맨 끝으로 순환
        """
        if not self.images:
            return
        self.index = (self.index - 1) % len(self.images)
        self.show_image(self.index)

    def next_image(self, event=None):
        """
        → 키를 눌렀을 때 호출.
        - (self.index + 1) % len(self.images): 맨 끝에서 다시 누르면 맨 앞으로 순환
        """
        if not self.images:
            return
        self.index = (self.index + 1) % len(self.images)
        self.show_image(self.index)

    def on_resize(self, event=None):
        """
        창 크기가 바뀔 때 호출(자동).
        - 현재 이미지를 캔버스 크기에 맞춰 다시 그려서 품질/배치를 유지
        """
        if self.images:
            self.show_image(self.index)

    # ---------- 표시 관련 ----------
    def show_empty_message(self, extra: str = ""):
        """
        이미지가 없을 때 중앙에 안내 문구를 표시.
        - Canvas.delete("all"): 캔버스에 그려진 모든 내용을 지움
        - Canvas.create_text(x, y, text=...): 좌표(x, y)에 텍스트 표시
        """
        self.label_info.config(text="표시할 이미지가 없습니다.")
        self.canvas.delete("all")
        msg = "CCTV 폴더에 이미지(JPG/PNG/GIF 등)를 넣어주세요."
        if extra:
            msg += f"\n\n{extra}"
        self.canvas.create_text(
            self.canvas.winfo_width() // 2,
            self.canvas.winfo_height() // 2,
            text=msg,
            fill="white",
            justify="center"
        )

    def show_image(self, idx: int):
        """
        idx 번째 이미지를 캔버스 크기에 맞춰 '비율 유지'로 리사이즈해 중앙에 표시.
        - Image.open(path): 이미지 파일을 엶
        - im.convert("RGBA"): 색/투명정보를 통일해 표시 안정성 향상
        - im.resize(new_size, Image.LANCZOS): 고품질 리사이즈 필터
        - ImageTk.PhotoImage(im): Pillow 이미지를 Tk가 쓸 수 있도록 변환
        - Canvas.create_image(x, y, image=...): 캔버스에 이미지 그림
        """
        path = self.images[idx]
        self.label_info.config(text=f"[{idx + 1}/{len(self.images)}] {path.name}")

        try:
            # with 블록: 파일을 열고 사용이 끝나면 자동으로 닫아줌
            with Image.open(path) as im:
                im = im.convert("RGBA")

                # 현재 캔버스 크기 가져오기 (너비/높이)
                cw = max(1, self.canvas.winfo_width())
                ch = max(1, self.canvas.winfo_height())

                # 테두리 여유를 조금 두고 최대 크기 계산
                max_w = max(1, cw - 16)
                max_h = max(1, ch - 16)

                # 원본 크기와 비율 계산
                w, h = im.size
                # scale: 너비/높이에 맞춘 배율 중 더 작은 값 사용 → 가로세로 모두 안 넘치게
                # 마지막 1.0은 원본보다 '키우지' 않도록 제한(원본 초과 확대 방지)
                scale = min(max_w / w, max_h / h, 1.0)
                new_size = (max(1, int(w * scale)), max(1, int(h * scale)))

                # 필요한 경우에만 리사이즈 수행
                if new_size != (w, h):
                    im = im.resize(new_size, Image.LANCZOS)

                # Tkinter가 이해할 수 있는 이미지 객체로 변환
                tk_img = ImageTk.PhotoImage(im)
        except Exception as e:
            # 이미지 파일이 손상/미지원 포맷 등 예외 발생 시 안내
            self.show_empty_message(f"이미지 로드 오류:\n{path}\n\n{e}")
            return

        # 이전 그린 내용 삭제 후, 계산된 좌표에 중앙 정렬로 배치
        self.canvas.delete("all")
        x = (self.canvas.winfo_width() - tk_img.width()) // 2
        y = (self.canvas.winfo_height() - tk_img.height()) // 2
        self.canvas.create_image(max(0, x), max(0, y), anchor="nw", image=tk_img)

        # 지역변수로만 두면 그려진 직후 가비지 컬렉션으로 사라질 수 있으니 참조 유지
        self._current_tk_img = tk_img


def main():
    """
    실행 흐름:
    1) ZIP 경로 결정(resolve_zip_path)
    2) ZIP 압축을 DEST_DIR로 해제(unzip_to_dest)
    3) DEST_DIR에서 이미지 목록 수집(collect_images)
    4) 뷰어 실행(CCTVViewer)
    """
    zip_path = resolve_zip_path()
    unzip_to_dest(zip_path, DEST_DIR)
    images = collect_images(DEST_DIR)

    # 콘솔에 간단히 상태 출력 (디버깅/확인용)
    print(f"[INFO] ZIP: {zip_path}")
    print(f"[INFO] Extracted to: {DEST_DIR}")
    print(f"[INFO] Found {len(images)} images")
    for p in images[:10]:
        print(f"  - {p.relative_to(DEST_DIR)}")
    if len(images) > 10:
        print(f"  ... (+{len(images) - 10} more)")

    # Tkinter 메인 윈도우 생성 및 이벤트 루프 시작
    app = CCTVViewer(images)
    app.mainloop()  # 이벤트(키 입력/창 크기변경 등)를 기다리면서 GUI 실행 유지


if __name__ == "__main__":
    # 이 파일을 직접 실행한 경우에만 main() 실행
    # (다른 파일에서 import할 때는 실행되지 않음)
    main()
