"""Verify the controllable platform adapters."""

from screensense.platform_adapters.base import PowerEvent, WindowInfo
from screensense.platform_adapters.stub import (
    StubAppDataProvider,
    StubAutostartProvider,
    StubIdleProvider,
    StubPowerProvider,
    StubWindowProvider,
)


def test_stub_idle_provider_returns_configured_value() -> None:
    """Expose the configured idle duration."""
    provider = StubIdleProvider(12.5)

    assert provider.seconds_since_input() == 12.5


def test_stub_window_provider_returns_configured_window() -> None:
    """Expose the configured foreground window without persistence."""
    window = WindowInfo("Untitled", "editor.exe", (0, 0, 800, 600), False)
    provider = StubWindowProvider(window)

    assert provider.foreground() == window


def test_stub_power_provider_delivers_and_unsubscribes() -> None:
    """Deliver configured power events and stop after unsubscribe."""
    provider = StubPowerProvider()
    received: list[PowerEvent] = []
    unsubscribe = provider.subscribe(received.append)

    provider.emit(PowerEvent.SLEEP)
    unsubscribe()
    provider.emit(PowerEvent.RESUME)

    assert received == [PowerEvent.SLEEP]


def test_stub_autostart_provider_tracks_changes() -> None:
    """Track enabled and disabled autostart state."""
    provider = StubAutostartProvider()

    assert not provider.is_enabled()
    provider.enable()
    assert provider.is_enabled()
    provider.disable()
    assert not provider.is_enabled()


def test_stub_app_data_provider_returns_path_without_creating_it(tmp_path) -> None:
    """Return a caller-selected directory without making filesystem changes."""
    directory = tmp_path / "screensense"

    assert StubAppDataProvider(directory).application_data_dir() == directory
    assert not directory.exists()
