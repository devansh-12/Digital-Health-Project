"""Test fullscreen geometry and mocked Win32 foreground queries."""

from typing import Any

import psutil
import pytest

from screensense.platform_adapters import windows
from screensense.platform_adapters.base import WindowInfo
from screensense.platform_adapters.windows import (
    WindowsWindowProvider,
    is_fullscreen_rect,
)

MONITOR = (0, 0, 1920, 1080)


@pytest.mark.parametrize(
    ("window", "has_caption", "expected"),
    [
        (MONITOR, False, True),
        ((-1920, 0, 1920, 1080), False, True),
        ((-1, -1, 1921, 1081), False, True),
        (MONITOR, True, False),
        ((1, 0, 1920, 1080), False, False),
        ((0, 1, 1920, 1080), False, False),
        ((0, 0, 1919, 1080), False, False),
        ((0, 0, 1920, 1079), False, False),
        ((1, 1, 1919, 1079), False, False),
        ((-1920, 0, -1, 1080), False, False),
        ((1920, 0, 3840, 1080), False, False),
        ((0, -1080, 1920, -1), False, False),
        ((0, 1080, 1920, 2160), False, False),
        ((-10, -10, 100, 100), False, False),
    ],
)
def test_is_fullscreen_rect_uses_coverage_and_caption(
    window: tuple[int, int, int, int], has_caption: bool, expected: bool
) -> None:
    """Require full monitor coverage and no caption style."""
    assert is_fullscreen_rect(window, MONITOR, has_caption=has_caption) is expected


def test_read_foreground_window_uses_mocked_win32_and_psutil(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Translate mocked native calls into in-memory foreground metadata."""

    class FakeUser32:
        """Provide controlled Win32 results for the query helper."""

        @staticmethod
        def GetForegroundWindow() -> int:
            return 42

        @staticmethod
        def GetDesktopWindow() -> int:
            return 1

        @staticmethod
        def GetShellWindow() -> int:
            return 2

        @staticmethod
        def GetClassNameW(_hwnd: int, buffer: Any, _size: int) -> int:
            buffer.value = "GameWindow"
            return len(buffer.value)

        @staticmethod
        def GetWindowThreadProcessId(_hwnd: int, process_id: Any) -> int:
            process_id._obj.value = 987
            return 1

        @staticmethod
        def GetWindowRect(_hwnd: int, rect_pointer: Any) -> int:
            rect = rect_pointer._obj
            rect.left, rect.top, rect.right, rect.bottom = MONITOR
            return 1

        @staticmethod
        def MonitorFromWindow(_hwnd: int, _flags: int) -> int:
            return 3

        @staticmethod
        def GetMonitorInfoW(_monitor: int, info_pointer: Any) -> int:
            rect = info_pointer._obj.rcMonitor
            rect.left, rect.top, rect.right, rect.bottom = MONITOR
            return 1

        @staticmethod
        def GetWindowLongW(_hwnd: int, _index: int) -> int:
            return 0

        @staticmethod
        def GetWindowTextLengthW(_hwnd: int) -> int:
            return 4

        @staticmethod
        def GetWindowTextW(_hwnd: int, buffer: Any, _size: int) -> int:
            buffer.value = "Game"
            return len(buffer.value)

    fake_user32 = FakeUser32()
    monkeypatch.setattr(windows.sys, "platform", "win32")
    monkeypatch.setattr(
        windows.ctypes, "WinDLL", lambda *_args, **_kwargs: fake_user32, raising=False
    )

    class FakeProcess:
        """Return a fake process name for the mocked process ID."""

        def __init__(self, process_id: int) -> None:
            assert process_id == 987

        @staticmethod
        def name() -> str:
            return "game.exe"

    monkeypatch.setattr(windows.psutil, "Process", FakeProcess)

    assert windows._read_foreground_window() == WindowInfo(
        title="Game",
        process="game.exe",
        rect=MONITOR,
        is_fullscreen=True,
    )


def test_window_provider_returns_none_for_shell_and_query_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Return None when native query detects shell or access errors."""
    monkeypatch.setattr(windows, "_read_foreground_window", lambda: None)
    assert WindowsWindowProvider().foreground() is None

    def denied() -> WindowInfo | None:
        raise psutil.AccessDenied()

    monkeypatch.setattr(windows, "_read_foreground_window", denied)
    assert WindowsWindowProvider().foreground() is None


def test_window_provider_swallows_missing_process_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Avoid crashing if a foreground process exits during inspection."""

    def missing() -> WindowInfo | None:
        raise psutil.NoSuchProcess(987)

    monkeypatch.setattr(windows, "_read_foreground_window", missing)
    assert WindowsWindowProvider().foreground() is None
