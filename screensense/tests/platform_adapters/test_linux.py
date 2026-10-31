"""Test Linux platform adapters."""

from pathlib import Path
from screensense.platform_adapters.base import PowerEvent
from screensense.platform_adapters.linux import (
    LinuxAppDataProvider,
    LinuxAutostartProvider,
    LinuxIdleProvider,
    LinuxPowerProvider,
    LinuxWindowProvider,
)


def test_linux_app_data_provider_resolves_path(monkeypatch, tmp_path) -> None:
    """Verify application_data_dir respects XDG_DATA_HOME."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    provider = LinuxAppDataProvider()
    data_dir = provider.application_data_dir()
    assert data_dir == tmp_path / "ScreenSense"
    assert data_dir.is_dir()


def test_linux_idle_provider_returns_float() -> None:
    """Verify idle provider returns non-negative seconds."""
    provider = LinuxIdleProvider()
    idle = provider.seconds_since_input()
    assert isinstance(idle, float)
    assert idle >= 0.0


def test_linux_window_provider_returns_safe_value() -> None:
    """Verify window provider returns None or WindowInfo without error."""
    provider = LinuxWindowProvider()
    window = provider.foreground()
    assert window is None or hasattr(window, "is_fullscreen")


def test_linux_power_provider_subscribe_and_emit() -> None:
    """Verify Linux power provider publishes events to subscribers."""
    provider = LinuxPowerProvider()
    received: list[PowerEvent] = []
    unsubscribe = provider.subscribe(received.append)

    provider.start()
    provider.emit(PowerEvent.LOCK)
    assert received == [PowerEvent.LOCK]

    unsubscribe()
    provider.emit(PowerEvent.UNLOCK)
    assert received == [PowerEvent.LOCK]
    provider.stop()


def test_linux_autostart_provider(monkeypatch, tmp_path) -> None:
    """Verify enabling and disabling autostart on Linux creates and unlinks desktop file."""
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    provider = LinuxAutostartProvider(command="screensense")
    assert not provider.is_enabled()

    provider.enable()
    assert provider.is_enabled()
    desktop_file = tmp_path / "autostart" / "screensense.desktop"
    assert desktop_file.is_file()
    assert "screensense" in desktop_file.read_text(encoding="utf-8")

    provider.disable()
    assert not provider.is_enabled()
    assert not desktop_file.exists()
