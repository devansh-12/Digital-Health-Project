"""Test completion and cancellation of timed quick breaks."""

import os

import pytest
from PyQt6.QtWidgets import QApplication

from screensense.core.clock import FakeClock
from screensense.ui.quick_break import QuickBreakDialog


@pytest.fixture(scope="module")
def app() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_quick_break_completes_after_duration(app: QApplication) -> None:
    clock = FakeClock()
    dialog = QuickBreakDialog(clock)
    completed: list[int] = []
    exited: list[bool] = []
    dialog.session_completed.connect(completed.append)
    dialog.session_exited.connect(lambda: exited.append(True))

    dialog.start(20)
    clock.advance(19)
    dialog._on_tick()
    assert dialog.countdown_ring.seconds_remaining == 1
    assert completed == []

    clock.advance(1)
    dialog._on_tick()
    assert completed == [20]
    assert exited == []
    assert not dialog.isVisible()
    dialog.close()


def test_quick_break_can_be_ended_without_completing(app: QApplication) -> None:
    dialog = QuickBreakDialog(FakeClock())
    completed: list[int] = []
    exited: list[bool] = []
    dialog.session_completed.connect(completed.append)
    dialog.session_exited.connect(lambda: exited.append(True))

    dialog.start(20)
    dialog.end_button.click()

    assert completed == []
    assert exited == [True]
    assert not dialog.isVisible()
    dialog.close()


def test_closing_quick_break_cancels_active_session(app: QApplication) -> None:
    dialog = QuickBreakDialog(FakeClock())
    exited: list[bool] = []
    dialog.session_exited.connect(lambda: exited.append(True))

    dialog.start(20)
    dialog.close()

    assert exited == [True]


@pytest.mark.parametrize("duration", [0, -1])
def test_quick_break_rejects_non_positive_duration(app: QApplication, duration: int) -> None:
    dialog = QuickBreakDialog(FakeClock())
    with pytest.raises(ValueError, match="duration_s must be positive"):
        dialog.start(duration)
    dialog.close()
