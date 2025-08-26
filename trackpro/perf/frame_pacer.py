# trackpro/perf/frame_pacer.py
# Ensures stable timers/sleeps on Windows; restores on exit.
import atexit, sys

def enable_1ms_timer_resolution():
    """
    Set 1ms timer resolution process-wide on Windows.
    timeBeginPeriod(1) improves wait/timer accuracy but costs power — fine for sim apps.
    References:
    - Microsoft Learn: Timer resolution APIs
    - Stack Overflow: Windows timer precision
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        winmm = ctypes.WinDLL("winmm")
        if winmm.timeBeginPeriod(1) == 0:  # TIMERR_NOERROR
            atexit.register(lambda: winmm.timeEndPeriod(1))
            return True
    except Exception:
        pass
    return False

def disable_timer_throttle():
    """
    Optional: ask Windows not to ignore timer resolution for this process.
    Safe to call; ignored if unavailable.
    See: SetProcessInformation(PROCESS_POWER_THROTTLING)
    References:
    - Microsoft Learn: Process power throttling
    """
    if sys.platform != "win32":
        return False
    try:
        import ctypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        GetCurrentProcess = kernel32.GetCurrentProcess
        SetProcessInformation = kernel32.SetProcessInformation
        class PROCESS_POWER_THROTTLING_STATE(ctypes.Structure):
            _fields_ = [("Version", ctypes.c_ulong),
                        ("ControlMask", ctypes.c_ulong),
                        ("StateMask", ctypes.c_ulong)]
        # Turn OFF IGNORE_TIMER_RESOLUTION (bit 0x2) for this process.
        PPT = PROCESS_POWER_THROTTLING_STATE(Version=1, ControlMask=0x2, StateMask=0x0)
        SetProcessInformation(GetCurrentProcess(), 7, ctypes.byref(PPT), ctypes.sizeof(PPT))  # 7 = ProcessPowerThrottling
        return True
    except Exception:
        return False
