import atexit, sys
if sys.platform.startswith("win"):
    import ctypes
    _winmm = ctypes.WinDLL("winmm")
    # Request 1 ms system timer resolution for steadier sleep/timers
    _winmm.timeBeginPeriod(1)
    atexit.register(lambda: _winmm.timeEndPeriod(1))

    # Be polite: bump process priority (not realtime)
    import ctypes.wintypes as wt
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    HIGH_PRIORITY_CLASS = 0x00000080
    handle = kernel32.GetCurrentProcess()
    kernel32.SetPriorityClass(handle, HIGH_PRIORITY_CLASS)
