"""Implement platform interfaces for Windows."""
"""Implement Windows platform providers with import-safe API boundaries."""

import ctypes
import logging
import os
import sys
import threading
from collections.abc import Callable
from ctypes import wintypes
from pathlib import Path

import psutil

from screensense.platform_adapters.base import PowerEvent, Rect, WindowInfo

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
_LOGGER = logging.getLogger(__name__)

_WM_CLOSE = 0x0010
_WM_DESTROY = 0x0002
_WM_POWERBROADCAST = 0x0218
_WM_WTSSESSION_CHANGE = 0x02B1
_WM_QUIT = 0x0012
_PBT_APMSUSPEND = 0x0004
_PBT_APMRESUMEAUTOMATIC = 0x0012
_PBT_APMRESUMESUSPEND = 0x0007
_WTS_SESSION_LOCK = 0x0007
_WTS_SESSION_UNLOCK = 0x0008
_NOTIFY_FOR_THIS_SESSION = 0
_RUN_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
_AUTOSTART_VALUE_NAME = "ScreenSense"


def power_event_for_message(message: int, wparam: int) -> PowerEvent | None:
    """Map supported Windows power/session messages to domain events."""
    if message == _WM_POWERBROADCAST:
        if wparam == _PBT_APMSUSPEND:
            return PowerEvent.SLEEP
        if wparam in (_PBT_APMRESUMEAUTOMATIC, _PBT_APMRESUMESUSPEND):
            return PowerEvent.RESUME
    elif message == _WM_WTSSESSION_CHANGE:
        if wparam == _WTS_SESSION_LOCK:
            return PowerEvent.LOCK
        if wparam == _WTS_SESSION_UNLOCK:
            return PowerEvent.UNLOCK
    return None


class WindowsPowerProvider:
    """Receive Windows sleep, resume, lock, and unlock messages."""

    def __init__(self) -> None:
        """Initialize native-listener state and an empty subscriber list."""
        self._handlers: list[Callable[[PowerEvent], None]] = []
        self._handlers_lock = threading.Lock()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None
        self._window_handle: int | None = None
        self._listener_error: OSError | RuntimeError | None = None

    def subscribe(self, handler: Callable[[PowerEvent], None]) -> Callable[[], None]:
        """Subscribe to events and return an unsubscribe callback."""
        with self._handlers_lock:
            self._handlers.append(handler)

        def unsubscribe() -> None:
            with self._handlers_lock:
                if handler in self._handlers:
                    self._handlers.remove(handler)

        return unsubscribe

    def handle_message(self, message: int, wparam: int) -> bool:
        """Translate one native message and notify current subscribers."""
        event = power_event_for_message(message, wparam)
        if event is None:
            return False
        with self._handlers_lock:
            handlers = tuple(self._handlers)
        for handler in handlers:
            try:
                handler(event)
            except Exception:  # noqa: BLE001 - never unwind through the native WndProc.
                _LOGGER.error("Power event subscriber failed")
        return True

    def start(self) -> None:
        """Start a hidden Win32 message window on a dedicated thread."""
        if sys.platform != "win32":
            raise OSError("Windows power notifications are available only on Windows")
        if self._thread is not None and self._thread.is_alive():
            return
        self._ready.clear()
        self._listener_error = None
        self._thread = threading.Thread(
            target=self._run_listener, name="ScreenSensePowerEvents", daemon=True
        )
        self._thread.start()
        self._ready.wait()
        if self._listener_error is not None:
            raise RuntimeError("Could not start the Windows power listener") from (
                self._listener_error
            )

    def stop(self) -> None:
        """Close the message window and wait for its listener thread to exit."""
        thread = self._thread
        if thread is None:
            return
        if self._window_handle is not None:
            ctypes.WinDLL("user32", use_last_error=True).PostMessageW(
                self._window_handle, _WM_CLOSE, 0, 0
            )
        thread.join()
        self._thread = None
        self._window_handle = None

    def _run_listener(self) -> None:
        """Create and run the native message window until it receives WM_QUIT."""
        if sys.platform != "win32":
            self._listener_error = OSError("Windows APIs are unavailable")
            self._ready.set()
            return

        class WindowClassEx(ctypes.Structure):
            """Represent the Win32 WNDCLASSEXW structure."""

            _fields_ = [
                ("cbSize", wintypes.UINT),
                ("style", wintypes.UINT),
                ("lpfnWndProc", ctypes.c_void_p),
                ("cbClsExtra", ctypes.c_int),
                ("cbWndExtra", ctypes.c_int),
                ("hInstance", wintypes.HINSTANCE),
                ("hIcon", wintypes.HICON),
                ("hCursor", wintypes.HCURSOR),
                ("hbrBackground", wintypes.HBRUSH),
                ("lpszMenuName", wintypes.LPCWSTR),
                ("lpszClassName", wintypes.LPCWSTR),
                ("hIconSm", wintypes.HICON),
            ]

        user32 = ctypes.WinDLL("user32", use_last_error=True)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        wtsapi32 = ctypes.WinDLL("wtsapi32", use_last_error=True)
        instance = kernel32.GetModuleHandleW(None)
        class_name = f"ScreenSensePowerWindow-{id(self):x}"
        window_proc_type = ctypes.WINFUNCTYPE(
            ctypes.c_ssize_t,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        )

        def window_proc(
            hwnd: int, message: int, wparam: int, lparam: int
        ) -> int:
            if message in (_WM_POWERBROADCAST, _WM_WTSSESSION_CHANGE):
                self.handle_message(message, wparam)
                return 1
            if message == _WM_CLOSE:
                user32.DestroyWindow(hwnd)
                return 0
            if message == _WM_DESTROY:
                wtsapi32.WTSUnRegisterSessionNotification(hwnd)
                user32.PostQuitMessage(0)
                return 0
            return int(user32.DefWindowProcW(hwnd, message, wparam, lparam))

        callback = window_proc_type(window_proc)
        window_class = WindowClassEx()
        window_class.cbSize = ctypes.sizeof(WindowClassEx)
        window_class.lpfnWndProc = ctypes.cast(callback, ctypes.c_void_p).value
        window_class.hInstance = instance
        window_class.lpszClassName = class_name
        if not user32.RegisterClassExW(ctypes.byref(window_class)):
            self._listener_error = ctypes.WinError(ctypes.get_last_error())
            self._ready.set()
            return

        hwnd = user32.CreateWindowExW(
            0, class_name, "", 0, 0, 0, 0, 0, None, None, instance, None
        )
        if not hwnd:
            self._listener_error = ctypes.WinError(ctypes.get_last_error())
            self._ready.set()
            user32.UnregisterClassW(class_name, instance)
            return
        self._window_handle = int(hwnd)
        if not wtsapi32.WTSRegisterSessionNotification(
            hwnd, _NOTIFY_FOR_THIS_SESSION
        ):
            self._listener_error = ctypes.WinError(ctypes.get_last_error())
            self._ready.set()
            user32.DestroyWindow(hwnd)
            user32.UnregisterClassW(class_name, instance)
            return

        self._ready.set()
        message = wintypes.MSG()
        while user32.GetMessageW(ctypes.byref(message), hwnd, 0, 0) > 0:
            user32.TranslateMessage(ctypes.byref(message))
            user32.DispatchMessageW(ctypes.byref(message))
        user32.UnregisterClassW(class_name, instance)


def _read_autostart_command(value_name: str) -> str | None:
    """Read a per-user Run registry value, returning None if absent."""
    if sys.platform != "win32":
        raise OSError("Windows autostart is available only on Windows")
    import winreg

    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_QUERY_VALUE
        ) as key:
            value, _value_type = winreg.QueryValueEx(key, value_name)
    except FileNotFoundError:
        return None
    return str(value)


def _write_autostart_command(value_name: str, command: str | None) -> None:
    """Create or remove a per-user Run registry value."""
    if sys.platform != "win32":
        raise OSError("Windows autostart is available only on Windows")
    import winreg

    if command is None:
        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE
            ) as key:
                winreg.DeleteValue(key, value_name)
        except FileNotFoundError:
            return
        return
    with winreg.CreateKeyEx(
        winreg.HKEY_CURRENT_USER, _RUN_KEY_PATH, 0, winreg.KEY_SET_VALUE
    ) as key:
        winreg.SetValueEx(key, value_name, 0, winreg.REG_SZ, command)


class WindowsAutostartProvider:
    """Manage the current user's ScreenSense Run registry value."""

    def __init__(self, command: str | None = None) -> None:
        """Initialize with an explicit command or the current application path."""
        if command is None:
            if getattr(sys, "frozen", False):
                command = f'"{sys.executable}"'
            else:
                app_path = Path(sys.argv[0]).resolve()
                command = f'"{sys.executable}" "{app_path}"'
        self._command = command

    def enable(self) -> None:
        """Write the application command to the current user's Run key."""
        _write_autostart_command(_AUTOSTART_VALUE_NAME, self._command)

    def disable(self) -> None:
        """Remove the application value from the current user's Run key."""
        _write_autostart_command(_AUTOSTART_VALUE_NAME, None)

    def is_enabled(self) -> bool:
        """Return whether the current user's Run value matches this command."""
        return (
            _read_autostart_command(_AUTOSTART_VALUE_NAME) == self._command
        )


class WindowsAppDataProvider:
    """Resolve ScreenSense's per-user directory under Windows APPDATA."""

    def application_data_dir(self) -> Path:
        """Create and return `%APPDATA%/ScreenSense`."""
        if sys.platform != "win32":
            raise OSError("Windows app data paths are available only on Windows")
        app_data = os.environ.get("APPDATA")
        if not app_data:
            raise OSError("APPDATA is not set")
        directory = Path(app_data) / "ScreenSense"
        directory.mkdir(parents=True, exist_ok=True)
        return directory


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
