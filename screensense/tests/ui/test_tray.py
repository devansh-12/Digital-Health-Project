"""Tests for scheduler-driven tray status updates."""

import os

import pytest
from PyQt6.QtWidgets import QApplication

from screensense.ui.tray import ScreenSenseTray, TrayStatus


@pytest.fixture(scope="module")
def app() -> QApplication:
    """Create an offscreen Qt application for tray widget tests."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_tray_status_can_show_active_due_and_suppressed_states(
    app: QApplication,
) -> None:
    """Expose active, due, and suppressed icon states for the event bridge."""
    tray = ScreenSenseTray(lambda: None, parent=app)
    assert tray.status is TrayStatus.ACTIVE

    tray.set_status(TrayStatus.DUE)
    assert tray.status is TrayStatus.DUE

    tray.set_status(TrayStatus.SUPPRESSED)
    assert tray.status is TrayStatus.SUPPRESSED
    tray.close()
