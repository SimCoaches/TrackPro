# trackpro/pedals/rt_pipeline.py
# Three-loop architecture:
#   - HW reader thread (you already have it) -> call set_latest(thr, brk)
#   - vJoy publisher thread at fixed Hz -> reads the latest only; pushes to vJoy
#   - UI remains at 60 Hz via your existing timer/signals (no change)

import threading, time
from dataclasses import dataclass
from typing import Callable, Optional

@dataclass
class PedalState:
    throttle: float = 0.0  # 0..1
    brake: float = 0.0     # 0..1

class LatestMailbox:
    """ lock-free-ish mailbox: always keep only the newest sample """
    __slots__ = ("_state", "_lock")
    def __init__(self):
        self._state = PedalState()
        self._lock = threading.Lock()
    def set(self, thr: float, brk: float):
        t = 0.0 if thr < 0 else 1.0 if thr > 1 else float(thr)
        b = 0.0 if brk < 0 else 1.0 if brk > 1 else float(brk)
        with self._lock:
            self._state.throttle = t
            self._state.brake = b
    def get(self) -> PedalState:
        with self._lock:
            return PedalState(self._state.throttle, self._state.brake)

class VJoyPublisher:
    """
    Fixed-rate vJoy publisher that eliminates stutter.
    The publisher always sends the latest normalized values at a fixed cadence;
    it never builds a queue or blocks on logs/DB/UI.
    References:
    - KDAB: Qt threading best practices
    - Qt Documentation: Worker thread patterns
    """
    def __init__(self, device, hz: int = 250, on_rate: Optional[Callable[[float], None]] = None):
        self.dev = device          # existing pyvjoy.VJoyDevice instance
        self.hz = max(30, int(hz)) # don't go silly-low
        self._mb = LatestMailbox()
        self._thr = threading.Thread(target=self._loop, name="vjoy-pub", daemon=True)
        self._run = threading.Event(); self._run.set()
        self._last_i_th = -1; self._last_i_br = -1
        self._on_rate = on_rate

        # axis constants commonly used by pyvjoy
        try:
            import pyvjoy
            self.AX_TH = getattr(pyvjoy, "HID_USAGE_Z", 0x32)
            self.AX_BR = getattr(pyvjoy, "HID_USAGE_RZ", 0x35)
        except Exception:
            self.AX_TH, self.AX_BR = 0x32, 0x35

    @staticmethod
    def _to_vjoy_i16(x: float) -> int:
        """Convert 0..1 to vJoy range 1..32768 per pyvjoy examples."""
        return int(round(0x0001 + x * (0x8000 - 0x0001)))  # 1..32768 per pyvjoy examples

    def set_latest(self, thr: float, brk: float):
        """Feed latest pedal values from hardware thread."""
        self._mb.set(thr, brk)

    def start(self):
        """Start the fixed-rate vJoy publishing thread."""
        if not self._thr.is_alive():
            self._thr.start()

    def stop(self):
        """Stop the vJoy publishing thread."""
        self._run.clear()
        self._thr.join(timeout=1.0)

    def _loop(self):
        """
        Deadline-based loop for solid 250Hz with drift correction.
        Uses perf_counter() and sleep-until approach to prevent timing drift.
        """
        from time import perf_counter, sleep
        
        HZ = float(self.hz)
        PERIOD = 1.0 / HZ
        next_t = perf_counter()
        sent = 0
        last_log = perf_counter()
        
        while self._run.is_set():
            now = perf_counter()
            
            # Wake jitter guard - don't process if we're too early
            if now < next_t - 0.002:
                sleep(next_t - now)
                continue

            st = self._mb.get()
            ith = self._to_vjoy_i16(st.throttle)
            ibr = self._to_vjoy_i16(st.brake)

            # avoid redundant writes (saves driver calls)
            if ith != self._last_i_th:
                try: self.dev.set_axis(self.AX_TH, ith)
                except Exception: pass
                self._last_i_th = ith
            if ibr != self._last_i_br:
                try: self.dev.set_axis(self.AX_BR, ibr)
                except Exception: pass
                self._last_i_br = ibr

            sent += 1
            next_t += PERIOD
            
            # Drift correction - if we're running behind, reset timing
            if now - next_t > PERIOD:
                next_t = now + PERIOD

            # lightweight rolling rate log (every ~2s)
            if now - last_log > 2.0:
                if self._on_rate:
                    self._on_rate(sent / (now - last_log))
                sent = 0; last_log = now
