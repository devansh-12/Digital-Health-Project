"""Smoke tests for the ScreenSense application entry point."""

from screensense.app import main


def test_main_is_available() -> None:
    """Expose the application entry point."""
    assert callable(main)
