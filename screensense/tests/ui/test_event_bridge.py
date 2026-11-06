"""Tests for scheduler-to-UI event and action wiring."""

import os

import pytest
from PyQt6.QtWidgets import QApplication

from screensense.core.clock import FakeClock
from screensense.core.config import Settings
from screensense.core.context import ContextState
from screensense.core.events import EventBus, ShowPrompt
from screensense.core.scheduler import Scheduler, State
from screensense.ui.event_bridge import SchedulerUiBridge
from screensense.ui.overlay import BreakOverlay
from screensense.ui.quick_break import QuickBreakDialog
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


def test_eye_yoga_button_triggers_on_start_yoga(app: QApplication) -> None:
    """Clicking Eye Yoga button starts yoga break and invokes on_start_yoga."""
    event_bus = EventBus()
    clock = FakeClock()
    scheduler = Scheduler(Settings(work_interval_minutes=10), clock, event_bus)
    overlay = BreakOverlay(clock)
    tray = ScreenSenseTray(lambda: None, parent=app)
    yoga_called = []
    bridge = SchedulerUiBridge(
        event_bus,
        scheduler,
        overlay,
        tray,
        on_start_yoga=lambda: yoga_called.append(True),
        parent=app,
    )

    clock.advance(10 * 60)
    scheduler.tick(ContextState.FREE)
    overlay.eye_yoga_button.click()

    assert scheduler.state is State.ON_BREAK
    assert yoga_called == [True]

    bridge.close()
    tray.close()
    overlay.close()


def test_quick_break_button_runs_timed_break_to_completion(app: QApplication) -> None:
    clock = FakeClock()
    event_bus = EventBus()
    scheduler = Scheduler(Settings(work_interval_minutes=10), clock, event_bus)
    overlay = BreakOverlay(clock)
    tray = ScreenSenseTray(lambda: None, parent=app)
    dialog = QuickBreakDialog(clock)
    dialog.session_completed.connect(scheduler.complete_break)
    bridge = SchedulerUiBridge(
        event_bus,
        scheduler,
        overlay,
        tray,
        on_start_break=lambda kind, duration: dialog.start(duration, kind=kind),
        parent=app,
    )

    clock.advance(10 * 60)
    scheduler.tick(ContextState.FREE)
    overlay.quick_break_button.click()

    assert scheduler.state is State.ON_BREAK
    assert dialog.isVisible()
    clock.advance(20)
    dialog._on_tick()

    assert scheduler.state is State.WORKING
    assert not dialog.isVisible()

    bridge.close()
    tray.close()
    overlay.close()
    dialog.close()


def test_long_prompt_starts_the_configured_long_break(app: QApplication) -> None:
    clock = FakeClock()
    event_bus = EventBus()
    settings = Settings(
        work_interval_minutes=10,
        long_break_minutes=3,
        long_break_every=3,
    )
    scheduler = Scheduler(settings, clock, event_bus)
    scheduler.start_break(kind="quick")
    scheduler.complete_break(20)
    scheduler.start_break(kind="quick")
    scheduler.complete_break(20)
    overlay = BreakOverlay(clock)
    tray = ScreenSenseTray(lambda: None, parent=app)
    dialog = QuickBreakDialog(clock)
    bridge = SchedulerUiBridge(
        event_bus,
        scheduler,
        overlay,
        tray,
        on_start_break=lambda kind, duration: dialog.start(duration, kind=kind),
        parent=app,
    )
    prompts: list[ShowPrompt] = []
    event_bus.subscribe(ShowPrompt, prompts.append)

    clock.advance(10 * 60)
    scheduler.tick(ContextState.FREE)
    app.processEvents()

    assert prompts[-1].kind == "long"
    assert prompts[-1].duration_s == 180
    assert overlay.quick_break_button.text() == "Long break (3 min)"
    overlay.quick_break_button.click()
    assert scheduler.state is State.ON_BREAK
    assert dialog._duration_s == 180
    assert dialog._title_label.text() == "Take a longer break"

    dialog.close()
    bridge.close()
    tray.close()
    overlay.close()


def test_dismissing_prompt_clears_prompting_scheduler_state(app: QApplication) -> None:
    event_bus = EventBus()
    clock = FakeClock()
    scheduler = Scheduler(Settings(work_interval_minutes=10), clock, event_bus)
    overlay = BreakOverlay(clock)
    tray = ScreenSenseTray(lambda: None, parent=app)
    bridge = SchedulerUiBridge(event_bus, scheduler, overlay, tray, parent=app)

    clock.advance(10 * 60)
    scheduler.tick(ContextState.FREE)
    overlay._dismiss()
    app.processEvents()

    assert scheduler.state is State.WORKING
    assert not overlay.isVisible()
    assert tray.status is TrayStatus.ACTIVE

    bridge.close()
    tray.close()
    overlay.close()


def test_snooze_button_label_tracks_saved_duration(app: QApplication) -> None:
    overlay = BreakOverlay(FakeClock())
    overlay.set_snooze_minutes(9)
    overlay.show_prompt()
    assert overlay.snooze_button.text() == "Snooze 9 min"
    overlay.close()
