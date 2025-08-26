# trackpro/race_coach/pedals_perf.py
"""
Performance-optimized pedal data aggregator for smooth UI updates.

Coalesces high-rate pedal samples into a fixed-rate UI signal to prevent
repaint spam and cross-thread churn. Threads → UI via signals/slots/QMetaObject 
is the recommended pattern to avoid stutter & crashes.

References:
- Real Python: Qt threading best practices
- Qt Forum: Signal/slot communication
"""
from PyQt6 import QtCore

class PedalSample(QtCore.QObject):
    """Signal container for normalized pedal values."""
    updated = QtCore.pyqtSignal(float, float, float)  # throttle, brake, clutch (0..1)

class PedalAggregator(QtCore.QObject):
    """
    Coalesces high-rate pedal samples into a fixed-rate UI signal.
    Call feed(thr, brk) from your telemetry path (any thread via invokeMethod).
    Connect .sample.updated to a UI slot to paint at a steady cadence.
    
    QTimer precision notes for Windows: expect ~16 ms granularity.
    References:
    - qtcentre.org: Windows timer granularity
    - Stack Overflow: QTimer precision limitations
    """
    def __init__(self, ui_hz: int = 60, parent=None):
        super().__init__(parent)
        self.sample = PedalSample()
        self._thr = 0.0
        self._brk = 0.0
        self._clt = 0.0
        self._lock = QtCore.QReadWriteLock()

        self._timer = QtCore.QTimer(self)
        self._timer.setTimerType(QtCore.Qt.TimerType.PreciseTimer)  # best available accuracy
        self._timer.setInterval(max(1, int(1000 / max(1, ui_hz))))  # ~16 ms @ 60 Hz
        self._timer.timeout.connect(self._emit_latest)
        self._timer.start()

        # Register with global resource manager to prevent handle exhaustion
        try:
            from new_ui import global_qt_resource_manager
            global_qt_resource_manager.track_timer(self._timer)
        except:
            pass

    @QtCore.pyqtSlot(float, float, float)
    def feed(self, thr_0_1: float, brk_0_1: float, clt_0_1: float = 0.0):
        """Thread-safe store; clamp to [0,1]."""
        t = 0.0 if thr_0_1 < 0 else 1.0 if thr_0_1 > 1.0 else float(thr_0_1)
        b = 0.0 if brk_0_1 < 0 else 1.0 if brk_0_1 > 1.0 else float(brk_0_1)
        c = 0.0 if clt_0_1 < 0 else 1.0 if clt_0_1 > 1.0 else float(clt_0_1)
        with QtCore.QWriteLocker(self._lock):
            self._thr, self._brk, self._clt = t, b, c

    def _emit_latest(self):
        """Single UI signal per frame - prevents UI spam."""
        with QtCore.QReadLocker(self._lock):
            t, b, c = self._thr, self._brk, self._clt
        self.sample.updated.emit(t, b, c)
