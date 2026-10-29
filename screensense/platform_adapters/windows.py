"""Implement platform interfaces for Windows."""
"""Implement Windows platform providers with import-safe API boundaries."""

import ctypes
import sys
from ctypes import wintypes

_TICK_MASK = 0xFFFF_FFFF
_MILLISECONDS_PER_SECOND = 1_000.0


def _get_idle_ticks() -> tuple[int, int]:
    """Return (current tick, last input tick) from the Windows APIs."""
    if sys.platform != "win32":
        raise OSError("Windows idle APIs are available only on Windows")

    class LastInputInfo(ctypes.Structure):
        """Represent the Win32 LASTINPUTINFO structure."""

        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    info = LastInputInfo()
    info.cbSize = ctypes.sizeof(LastInputInfo)
    user32 = ctypes.WinDLL("user32", use_last_error=True)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    if not user32.GetLastInputInfo(ctypes.byref(info)):
        raise ctypes.WinError(ctypes.get_last_error())
    current_tick = int(kernel32.GetTickCount()) & _TICK_MASK
    return current_tick, int(info.dwTime) & _TICK_MASK


class WindowsIdleProvider:
    """Read elapsed idle time using GetLastInputInfo on Windows."""

    def seconds_since_input(self) -> float:
        """Return idle seconds, including across the 49.7-day DWORD wrap."""
        current_tick, last_input_tick = _get_idle_ticks()
        elapsed_ms = (current_tick - last_input_tick) & _TICK_MASK
        return elapsed_ms / _MILLISECONDS_PER_SECOND
