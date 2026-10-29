"""Test Windows power message translation and autostart registry boundaries."""

import pytest

from screensense.platform_adapters import windows
from screensense.platform_adapters.base import PowerEvent
from screensense.platform_adapters.windows import (
    WindowsAutostartProvider,
    WindowsPowerProvider,
    power_event_for_message,
)


@pytest.mark.parametrize(
    ("message", "wparam", "expected"),
    [
        (0x0218, 0x0004, PowerEvent.SLEEP),
        (0x0218, 0x0012, PowerEvent.RESUME),
        (0x0218, 0x0007, PowerEvent.RESUME),
        (0x02B1, 0x0007, PowerEvent.LOCK),
        (0x02B1, 0x0008, PowerEvent.UNLOCK),
        (0x0218, 0xFFFF, None),
        (0x0001, 0x0007, None),
    ],
)
def test_power_event_for_message_maps_supported_messages(
    message: int, wparam: int, expected: PowerEvent | None
) -> None:
    """Map only documented power-broadcast and session-change values."""
    assert power_event_for_message(message, wparam) is expected


def test_windows_power_provider_emits_and_unsubscribes() -> None:
    """Deliver translated fake messages to current subscribers only."""
    provider = WindowsPowerProvider()
    received: list[PowerEvent] = []
    unsubscribe = provider.subscribe(received.append)

    assert provider.handle_message(0x0218, 0x0004)
    unsubscribe()
    assert provider.handle_message(0x02B1, 0x0008)
    assert not provider.handle_message(0x02B1, 0xFFFF)
    assert received == [PowerEvent.SLEEP]


def test_windows_power_provider_requires_windows_to_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail explicitly instead of loading Win32 APIs on other platforms."""
    monkeypatch.setattr(windows.sys, "platform", "darwin")

    with pytest.raises(OSError, match="only on Windows"):
        WindowsPowerProvider().start()


def test_windows_autostart_provider_uses_mockable_registry_helpers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enable, query, and disable autostart through isolated registry calls."""
    values: dict[str, str] = {}
    writes: list[tuple[str, str | None]] = []

    def read(value_name: str) -> str | None:
        return values.get(value_name)

    def write(value_name: str, command: str | None) -> None:
        writes.append((value_name, command))
        if command is None:
            values.pop(value_name, None)
        else:
            values[value_name] = command

    monkeypatch.setattr(windows, "_read_autostart_command", read)
    monkeypatch.setattr(windows, "_write_autostart_command", write)
    provider = WindowsAutostartProvider('"C:\\ScreenSense.exe"')

    assert not provider.is_enabled()
    provider.enable()
    assert provider.is_enabled()
    provider.disable()
    assert not provider.is_enabled()
    assert writes == [("ScreenSense", '"C:\\ScreenSense.exe"'), ("ScreenSense", None)]
