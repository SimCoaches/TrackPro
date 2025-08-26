from __future__ import annotations

import time
from collections import deque
from typing import Optional

import numpy as np
from PyQt6.QtCore import QObject, QThread, pyqtSignal, pyqtSlot, QTimer, Qt


class PedalsWorker(QObject):
    samplesReady = pyqtSignal(object)  # numpy ndarray shape (N,3) float32 in [0,1]

    def __init__(self, hardware, ui_hz: int = 120, parent=None):
        super().__init__(parent)
        self._hardware = hardware
        self._ui_interval_ms = max(4, int(1000 / max(1, ui_hz)))
        self._poll_timer: Optional[QTimer] = None
        self._emit_timer: Optional[QTimer] = None
        self._running = False
        self._ring = deque(maxlen=4096)

    @pyqtSlot()
    def start(self):
        if self._running:
            return
        self._running = True
        # Fast polling timer (coarse enough to avoid exhaustion), use small interval
        self._poll_timer = QTimer(self)
        self._poll_timer.setTimerType(QTimer.TimerType.PreciseTimer)
        self._poll_timer.timeout.connect(self._poll_once)
        self._poll_timer.start(1)  # ~1 kHz best-effort

        # UI emission timer at steady rate
        self._emit_timer = QTimer(self)
        self._emit_timer.setTimerType(QTimer.TimerType.CoarseTimer)
        self._emit_timer.timeout.connect(self._emit_slice)
        self._emit_timer.start(self._ui_interval_ms)

    @pyqtSlot()
    def stop(self):
        self._running = False
        if self._poll_timer:
            self._poll_timer.stop()
            self._poll_timer.deleteLater()
            self._poll_timer = None
        if self._emit_timer:
            self._emit_timer.stop()
            self._emit_timer.deleteLater()
            self._emit_timer = None

    @pyqtSlot(int)
    def setRate(self, hz: int):
        self._ui_interval_ms = max(4, int(1000 / max(1, hz)))
        if self._emit_timer and self._emit_timer.isActive():
            self._emit_timer.setInterval(self._ui_interval_ms)

    @pyqtSlot()
    def recalibrate(self):
        if hasattr(self._hardware, 'save_calibration') and hasattr(self._hardware, 'calibration'):
            self._hardware.save_calibration(self._hardware.calibration)

    def _poll_once(self):
        if not self._running or not self._hardware:
            return
        try:
            raw = self._hardware.read_pedals() or {}
            thr = float(raw.get('throttle', 0)) / 65535.0
            brk = float(raw.get('brake', 0)) / 65535.0
            clt = float(raw.get('clutch', 0)) / 65535.0
            self._ring.append((time.perf_counter(), thr, brk, clt))
        except Exception:
            pass

    def _emit_slice(self):
        if not self._ring:
            return
        # Emit last ~16ms slice or up to 128 samples
        now = time.perf_counter()
        window = 0.016
        result = []
        for ts, thr, brk, clt in reversed(self._ring):
            if now - ts > window:
                break
            result.append((thr, brk, clt))
            if len(result) >= 128:
                break
        if not result:
            # Fallback to last sample
            ts, thr, brk, clt = self._ring[-1]
            result = [(thr, brk, clt)]
        arr = np.asarray(list(reversed(result)), dtype=np.float32)
        self.samplesReady.emit(arr)


def create_pedals_thread(hardware, ui_hz: int = 120):
    worker = PedalsWorker(hardware, ui_hz)
    thread = QThread()
    worker.moveToThread(thread)
    thread.started.connect(worker.start)
    thread.finished.connect(worker.deleteLater)
    return worker, thread


