# javis.py
# ------------------------------------------
# PyQt6 UI로 녹음 시작/종료가 가능한 레코더 (버튼 동작 명확 분리)
# - records/ 폴더에 YYYYMMDD-HHMMSS.wav 저장
# - Start는 '시작만', Stop은 '종료만'
# - 상태머신(Idle/Starting/Recording/Stopping)으로 더블클릭/연타에도 안전
# ------------------------------------------

from __future__ import annotations
import sys
import queue
import threading
import time
from datetime import datetime
from enum import Enum, auto
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QMessageBox, QSizePolicy
)


def ensure_records_dir() -> Path:
    p = Path(__file__).resolve().parent / "records"
    p.mkdir(parents=True, exist_ok=True)
    return p


def timestamp_filename() -> str:
    return datetime.now().strftime("%Y%m%d-%H%M%S")


class RecState(Enum):
    IDLE = auto()
    STARTING = auto()
    RECORDING = auto()
    STOPPING = auto()


class JavisRecorder(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Javis Recorder")
        self.setMinimumSize(640, 360)

        # ----- 상태머신/내부 리소스 -----
        self.state = RecState.IDLE
        self.stream: sd.InputStream | None = None
        self.sf_file: sf.SoundFile | None = None
        self.writer_thread: threading.Thread | None = None
        self.stop_event = threading.Event()
        self.q: "queue.Queue[np.ndarray]" = queue.Queue()
        self.start_time = 0.0

        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(200)
        self.elapsed_timer.timeout.connect(self._tick_elapsed)

        # ----- UI -----
        central = QWidget(self)
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel("🎙️  Javis Recorder")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        root.addWidget(title)

        grid = QGridLayout()
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(8)
        row = 0

        grid.addWidget(QLabel("Input Device"), row, 0, alignment=Qt.AlignmentFlag.AlignRight)
        self.device_combo = QComboBox()
        self._populate_devices()
        self.device_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.device_combo.currentIndexChanged.connect(self._on_device_changed)
        grid.addWidget(self.device_combo, row, 1, 1, 3)
        row += 1

        grid.addWidget(QLabel("Sample Rate"), row, 0, alignment=Qt.AlignmentFlag.AlignRight)
        self.sr_combo = QComboBox()
        self.sr_combo.setEditable(True)
        for sr in (8000, 16000, 22050, 32000, 44100, 48000):
            self.sr_combo.addItem(str(sr))
        default_sr = self._current_device_default_sr()
        if default_sr and str(int(default_sr)) not in [self.sr_combo.itemText(i) for i in range(self.sr_combo.count())]:
            self.sr_combo.insertItem(0, str(int(default_sr)))
        self.sr_combo.setCurrentIndex(0)
        grid.addWidget(self.sr_combo, row, 1)

        grid.addWidget(QLabel("Channels"), row, 2, alignment=Qt.AlignmentFlag.AlignRight)
        self.ch_spin = QSpinBox()
        self.ch_spin.setRange(1, 8)
        self.ch_spin.setValue(1)
        grid.addWidget(self.ch_spin, row, 3)
        row += 1

        root.addLayout(grid)

        # 상태/경로/시간
        self.status_label = QLabel("대기 중")
        self.path_label = QLabel("파일 경로: -")
        self.elapsed_label = QLabel("경과 시간: 00:00")
        for lbl in (self.status_label, self.path_label, self.elapsed_label):
            lbl.setStyleSheet("color: #bbb;") #font color
            root.addWidget(lbl)

        # 버튼
        btns = QHBoxLayout()
        self.start_btn = QPushButton("●  녹음 시작")
        self.start_btn.setToolTip("녹음을 시작합니다")
        self.start_btn.setStyleSheet("QPushButton{background:#e74c3c;color:white;padding:12px;border-radius:10px;}")
        self.start_btn.clicked.connect(self.start_recording)

        self.stop_btn = QPushButton("■  녹음 종료")
        self.stop_btn.setToolTip("녹음을 종료하고 파일로 저장합니다")
        self.stop_btn.setStyleSheet("QPushButton{background:#555;color:white;padding:12px;border-radius:10px;}")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_recording)

        btns.addWidget(self.start_btn)
        btns.addWidget(self.stop_btn)
        root.addLayout(btns)
        root.addStretch(1)

        self._update_buttons()

    # ---------- 장치 관련 ----------
    def _populate_devices(self):
        self.device_combo.clear()
        devices = sd.query_devices()
        default_in = sd.default.device[0] if sd.default.device else None
        for idx, d in enumerate(devices):
            if d["max_input_channels"] > 0:
                label = f"[{idx}] {d['name']}  •  {d['max_input_channels']}ch  •  {int(d.get('default_samplerate') or 0)}Hz"
                self.device_combo.addItem(label, userData=idx)
                if default_in == idx:
                    self.device_combo.setCurrentIndex(self.device_combo.count() - 1)
        if self.device_combo.count() == 0:
            QMessageBox.critical(self, "에러", "입력 가능한 오디오 장치를 찾을 수 없습니다.")

    def _current_device_index(self) -> int | None:
        if self.device_combo.currentIndex() < 0:
            return None
        return self.device_combo.currentData()

    def _current_device_default_sr(self) -> int | None:
        idx = self._current_device_index()
        try:
            info = sd.query_devices(idx, "input")
            return int(info.get("default_samplerate") or 0) or None
        except Exception:
            return None

    def _on_device_changed(self, *_):
        idx = self._current_device_index()
        try:
            info = sd.query_devices(idx, "input")
            max_in = int(info.get("max_input_channels") or 1)
            self.ch_spin.setMaximum(max(1, max_in))
            default_sr = int(info.get("default_samplerate") or 0)
            if default_sr:
                self.sr_combo.setItemText(0, str(default_sr))
                self.sr_combo.setCurrentIndex(0)
        except Exception:
            pass

    # ---------- 상태/버튼 제어 ----------
    def _update_buttons(self):
        # Start는 오직 IDLE에서만 활성, Stop은 오직 RECORDING에서만 활성
        self.start_btn.setEnabled(self.state == RecState.IDLE)
        self.stop_btn.setEnabled(self.state == RecState.RECORDING)

    # ---------- 녹음 제어 ----------
    def start_recording(self):
        # Start는 '시작만' 수행: 녹음 중이면 무시
        if self.state != RecState.IDLE:
            return

        # 즉시 상태 전이(더블클릭/연타 방지)
        self.state = RecState.STARTING
        self._update_buttons()
        self.status_label.setText("시작 준비…")

        device = self._current_device_index()
        # 샘플레이트
        try:
            samplerate = int(self.sr_combo.currentText())
        except ValueError:
            self.state = RecState.IDLE
            self._update_buttons()
            QMessageBox.warning(self, "입력 오류", "샘플레이트는 숫자여야 합니다.")
            return

        # 채널
        channels = int(self.ch_spin.value())
        try:
            info = sd.query_devices(device, "input")
            max_in = int(info.get("max_input_channels") or 1)
            channels = min(channels, max_in)
            self.ch_spin.setValue(channels)
        except Exception:
            pass

        # 파일 경로
        out_dir = ensure_records_dir()
        out_path = out_dir / f"{timestamp_filename()}.wav"

        # 큐/이벤트 초기화
        self.q = queue.Queue()
        self.stop_event.clear()

        def callback(indata, frames, time_info, status):
            if status:
                self.status_label.setText(f"녹음 중… (경고: {status})")
            self.q.put(indata.copy())

        # 파일 열기
        try:
            self.sf_file = sf.SoundFile(str(out_path), mode="w",
                                        samplerate=samplerate, channels=channels, subtype="PCM_16")
        except Exception as e:
            self.state = RecState.IDLE
            self._update_buttons()
            QMessageBox.critical(self, "파일 오류", f"출력 파일을 열 수 없습니다:\n{e}")
            return

        # writer thread
        def writer():
            while not self.stop_event.is_set() or not self.q.empty():
                try:
                    data = self.q.get(timeout=0.2)
                except queue.Empty:
                    continue
                if self.sf_file:
                    self.sf_file.write(data)

        self.writer_thread = threading.Thread(target=writer, daemon=True)
        self.writer_thread.start()

        # 입력 스트림 시작
        try:
            self.stream = sd.InputStream(device=device, channels=channels,
                                         samplerate=samplerate, dtype="float32",
                                         callback=callback)
            self.stream.start()
        except Exception as e:
            # 실패 시 정리하고 IDLE로 회복
            self.stop_event.set()
            if self.writer_thread:
                self.writer_thread.join(timeout=2.0)
            self.writer_thread = None
            if self.sf_file:
                try: self.sf_file.close()
                except: pass
            self.sf_file = None
            self.state = RecState.IDLE
            self._update_buttons()
            QMessageBox.critical(self, "장치 오류", f"오디오 스트림을 시작할 수 없습니다:\n{e}")
            return

        # 성공적으로 시작됨 → RECORDING
        self.state = RecState.RECORDING
        self._update_buttons()
        self.start_time = time.time()
        self.elapsed_timer.start()
        self.status_label.setText(f"녹음 중…  sr={samplerate}  ch={channels}  dev={device if device is not None else 'default'}")
        self.path_label.setText(f"파일 경로: {out_path}")

    def stop_recording(self):
        # Stop은 '종료만' 수행: 녹음 중이 아닐 때는 무시
        if self.state != RecState.RECORDING:
            return

        # 즉시 상태 전이(연타 방지)
        self.state = RecState.STOPPING
        self._update_buttons()
        self.status_label.setText("정리 중…")

        # 스트림 중지/해제
        try:
            if self.stream:
                self.stream.stop()
                self.stream.close()
        except Exception:
            pass
        self.stream = None

        # writer 종료
        self.stop_event.set()
        if self.writer_thread:
            self.writer_thread.join(timeout=3.0)
        self.writer_thread = None

        # 파일 닫기
        if self.sf_file:
            try:
                self.sf_file.close()
            except Exception:
                pass
        self.sf_file = None

        # 상태 복귀
        self.elapsed_timer.stop()
        self.state = RecState.IDLE
        self._update_buttons()
        self.status_label.setText("대기 중")
        # path_label은 마지막 저장 경로 확인용으로 유지

    def closeEvent(self, event):
        # 창 닫힐 때 안전 정리
        if self.state == RecState.RECORDING:
            self.stop_recording()
        super().closeEvent(event)

    # ---------- 경과 시간 ----------
    def _tick_elapsed(self):
        if self.state != RecState.RECORDING:
            return
        elapsed = int(time.time() - self.start_time)
        mm = elapsed // 60
        ss = elapsed % 60
        self.elapsed_label.setText(f"경과 시간: {mm:02d}:{ss:02d}")


def main():
    app = QApplication(sys.argv)
    w = JavisRecorder()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

