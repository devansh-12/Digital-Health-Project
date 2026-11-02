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


def test_tray_menu_actions(app: QApplication) -> None:
    """Verify tray menu actions trigger the configured callbacks."""
    yoga_called = []
    settings_called = []
    quit_called = []
    tray = ScreenSenseTray(
        on_quit=lambda: quit_called.append(True),
        on_settings=lambda: settings_called.append(True),
        on_eye_yoga=lambda: yoga_called.append(True),
        parent=app,
    )
    actions = tray._menu.actions()
    assert len(actions) == 3
    assert actions[0].text() == "Start Eye Yoga (60s)"
    assert actions[1].text() == "Settings"
    assert actions[2].text() == "Quit"
    actions[0].trigger()
    assert yoga_called == [True]
    tray.close()


def test_tray_exposes_camera_indicator_and_stop_switch(app: QApplication) -> None:
    stopped = []
    tray = ScreenSenseTray(
        on_quit=lambda: None,
        on_stop_blink_monitor=lambda: stopped.append(True),
        parent=app,
    )
    action = next(
        action
        for action in tray._menu.actions()
        if action.text() == "Stop Blink Monitoring"
    )
    assert not action.isEnabled()

    tray.set_camera_active(True, "Calibrating")
    assert action.isEnabled()
    assert "Camera active: Calibrating" in tray._icon.toolTip()
    action.trigger()
    assert stopped == [True]
    tray.set_camera_active(False)
    assert not action.isEnabled()
    tray.close()
