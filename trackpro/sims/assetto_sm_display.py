# Windows-only; reads acpmf_physics -> (gas, brake) floats 0..1 for display parity.
# Shared memory names documented by AC: physics = "acpmf_physics".
# Fields start with: int packetId; float gas; float brake; ...
import ctypes
from typing import Optional, Tuple

FILE_MAP_READ = 0x0004
AC_PHYSICS_MMAP_NAME = "acpmf_physics"

class _SPageFilePhysicsMinimal(ctypes.Structure):
    _pack_ = 4
    _fields_ = [
        ("packetId", ctypes.c_int32),
        ("gas", ctypes.c_float),
        ("brake", ctypes.c_float),
    ]

class ACSharedMemoryDisplay:
    def __init__(self):
        # Map/unmap on each read to avoid stale pointers across AC load/unload
        self._name = AC_PHYSICS_MMAP_NAME

    def open(self) -> bool:
        # Probe once to verify the mapping exists; do not hold persistent handles
        k = ctypes.windll.kernel32
        h = k.OpenFileMappingW(FILE_MAP_READ, False, self._name)
        if not h:
            return False
        try:
            v = k.MapViewOfFile(h, FILE_MAP_READ, 0, 0, ctypes.sizeof(_SPageFilePhysicsMinimal))
            if not v:
                return False
            # Immediately unmap to avoid keeping stale views during AC transitions
            k.UnmapViewOfFile(v)
            return True
        finally:
            k.CloseHandle(h)

    def close(self):
        # No persistent resources are held between reads
        return

    def read(self) -> Optional[Tuple[float, float]]:
        k = ctypes.windll.kernel32
        h = k.OpenFileMappingW(FILE_MAP_READ, False, self._name)
        if not h:
            return None
        v = None
        try:
            v = k.MapViewOfFile(h, FILE_MAP_READ, 0, 0, ctypes.sizeof(_SPageFilePhysicsMinimal))
            if not v:
                return None

            # Copy into a local structure to minimize time holding the view
            local = _SPageFilePhysicsMinimal()
            ctypes.memmove(ctypes.byref(local), v, ctypes.sizeof(local))

            gas = max(0.0, min(1.0, float(local.gas)))
            brake = max(0.0, min(1.0, float(local.brake)))
            return (gas, brake)
        except Exception:
            # Fail safely; caller will handle None
            return None
        finally:
            if v:
                try:
                    k.UnmapViewOfFile(v)
                except Exception:
                    pass
            try:
                k.CloseHandle(h)
            except Exception:
                pass
