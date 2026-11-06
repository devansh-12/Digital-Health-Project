"""Test automatic platform provider resolution."""

import pytest

from screensense.platform_adapters.factory import get_platform_providers


def test_get_platform_providers_returns_valid_instances() -> None:
    """Verify that get_platform_providers returns an object with all required providers."""
    providers = get_platform_providers()
    assert hasattr(providers, "app_data")
    assert hasattr(providers, "idle")
    assert hasattr(providers, "window")
    assert hasattr(providers, "power")
    assert hasattr(providers, "autostart")

    # Verify basic protocol methods are callable without error
    try:
        app_dir = providers.app_data.application_data_dir()
        assert app_dir.exists()
    except OSError as error:
        if "Read-only file system" in str(error):
            pytest.skip(f"Read-only environment: {error}")
        raise

    idle_seconds = providers.idle.seconds_since_input()
    assert isinstance(idle_seconds, float)
    assert idle_seconds >= 0.0

    assert providers.window.foreground() is None or hasattr(
        providers.window.foreground(), "process"
    )
