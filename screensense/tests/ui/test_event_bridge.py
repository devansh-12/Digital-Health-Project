"""Tests for scheduler-to-UI event and action wiring."""

import os

import pytest
from PyQt6.QtWidgets import QApplication

from screensense.core.clock import FakeClock
from screensense.core.config import Settings
from screensense.core.context import ContextState
from screensense.core.events import EventBus
from screensense.core.scheduler import Scheduler, State
from screensense.ui.event_bridge import SchedulerUiBridge
from screensense.ui.overlay import BreakOverlay
from screensense.ui.tray import ScreenSenseTray, TrayStatus


@pytest.fixture(scope="module")
def app() -> QApplication:
    """Create an offscreen Qt application for bridge tests."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_prompt_and_skip_events_update_overlay_and_tray(app: QApplication) -> None:
    """Show a prompt from the scheduler, then dismiss it after a skip."""
    event_bus = EventBus()
    clock = FakeClock()
    scheduler = Scheduler(Settings(work_interval_minutes=10), clock, event_bus)
    overlay = BreakOverlay(clock)
    tray = ScreenSenseTray(lambda: None, parent=app)
    bridge = SchedulerUiBridge(event_bus, scheduler, overlay, tray, parent=app)

    clock.advance(10 * 60)
    scheduler.tick(ContextState.FREE)
    app.processEvents()

    assert overlay.isVisible()
    assert overlay.countdown_ring.seconds_remaining == 20
    assert tray.status is TrayStatus.DUE

    overlay.skip_button.click()
    app.processEvents()

    assert not overlay.isVisible()
    assert scheduler.state is State.WORKING
    assert tray.status is TrayStatus.ACTIVE

    bridge.close()
    tray.close()
    overlay.close()


def test_snooze_action_updates_scheduler_and_tray(app: QApplication) -> None:
    """Snooze a visible prompt and mark the tray as suppressed."""
    event_bus = EventBus()
    clock = FakeClock()
    scheduler = Scheduler(Settings(work_interval_minutes=10), clock, event_bus)
    overlay = BreakOverlay(clock)
    tray = ScreenSenseTray(lambda: None, parent=app)
    bridge = SchedulerUiBridge(event_bus, scheduler, overlay, tray, parent=app)

    clock.advance(10 * 60)
    scheduler.tick(ContextState.FREE)
    overlay.snooze_button.click()

    assert scheduler.state is State.SNOOZED
    assert tray.status is TrayStatus.SUPPRESSED
    assert not overlay.isVisible()

    bridge.close()
    tray.close()
    overlay.close()
