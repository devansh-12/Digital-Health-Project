"""Implement platform interfaces for Windows."""
"""Implement Windows platform providers with import-safe API boundaries."""

import ctypes
import sys
from ctypes import wintypes

import psutil

from screensense.platform_adapters.base import Rect, WindowInfo

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


_WS_CAPTION = 0x00C0_0000
_GWL_STYLE = -16
_MONITOR_DEFAULTTONEAREST = 2
_SHELL_WINDOW_CLASSES = {"Progman", "WorkerW", "Shell_TrayWnd"}


def is_fullscreen_rect(
    window_rect: Rect, monitor_rect: Rect, *, has_caption: bool
) -> bool:
    """Return whether an uncaptioned window covers its monitor rectangle."""
    if has_caption:
        return False
    left, top, right, bottom = window_rect
    monitor_left, monitor_top, monitor_right, monitor_bottom = monitor_rect
    return (
        left <= monitor_left
        and top <= monitor_top
        and right >= monitor_right
        and bottom >= monitor_bottom
    )


def _read_foreground_window() -> WindowInfo | None:
    """Read foreground metadata using Win32 and psutil; title remains memory-only."""
    if sys.platform != "win32":
        raise OSError("Windows window APIs are available only on Windows")

    class WinRect(ctypes.Structure):
        """Represent a Win32 RECT."""

        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]

    class MonitorInfo(ctypes.Structure):
        """Represent the portion of MONITORINFO used for monitor bounds."""

        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("rcMonitor", WinRect),
            ("rcWork", WinRect),
            ("dwFlags", wintypes.DWORD),
        ]

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    hwnd = user32.GetForegroundWindow()
    if not hwnd or hwnd in (user32.GetDesktopWindow(), user32.GetShellWindow()):
        return None

    class_name_buffer = ctypes.create_unicode_buffer(256)
    if (
        user32.GetClassNameW(hwnd, class_name_buffer, len(class_name_buffer))
        and class_name_buffer.value in _SHELL_WINDOW_CLASSES
    ):
        return None

    process_id = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(process_id))
    if not process_id.value:
        return None

    window_rect = WinRect()
    if not user32.GetWindowRect(hwnd, ctypes.byref(window_rect)):
        return None

    monitor = user32.MonitorFromWindow(hwnd, _MONITOR_DEFAULTTONEAREST)
    if not monitor:
        return None
    monitor_info = MonitorInfo()
    monitor_info.cbSize = ctypes.sizeof(MonitorInfo)
    if not user32.GetMonitorInfoW(monitor, ctypes.byref(monitor_info)):
        return None

    style = user32.GetWindowLongW(hwnd, _GWL_STYLE)
    has_caption = bool(style & _WS_CAPTION)
    title_length = user32.GetWindowTextLengthW(hwnd)
    title_buffer = ctypes.create_unicode_buffer(title_length + 1)
    user32.GetWindowTextW(hwnd, title_buffer, len(title_buffer))
    try:
        process_name = psutil.Process(int(process_id.value)).name()
    except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
        return None

    rect = (
        int(window_rect.left),
        int(window_rect.top),
        int(window_rect.right),
        int(window_rect.bottom),
    )
    monitor_rect = (
        int(monitor_info.rcMonitor.left),
        int(monitor_info.rcMonitor.top),
        int(monitor_info.rcMonitor.right),
        int(monitor_info.rcMonitor.bottom),
    )
    return WindowInfo(
        title=title_buffer.value,
        process=process_name,
        rect=rect,
        is_fullscreen=is_fullscreen_rect(
            rect, monitor_rect, has_caption=has_caption
        ),
    )


class WindowsWindowProvider:
    """Read foreground process and fullscreen state on Windows."""

    def foreground(self) -> WindowInfo | None:
        """Return foreground metadata, or None for unavailable/shell windows."""
        try:
            return _read_foreground_window()
        except (OSError, psutil.Error, ValueError):
            return None
