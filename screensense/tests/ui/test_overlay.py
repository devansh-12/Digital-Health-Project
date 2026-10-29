"""Tests for the break overlay's controls and window behavior."""

import os
from collections.abc import Iterator

import pytest
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import QApplication

from screensense.core.clock import FakeClock
from screensense.core.events import ShowPrompt
from screensense.ui.overlay import BreakOverlay
from screensense.ui.theme import load_stylesheet


@pytest.fixture(scope="module")
def app() -> QApplication:
    """Create the Qt application required by widget tests."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


@pytest.fixture
def overlay(app: QApplication) -> Iterator[BreakOverlay]:
    """Create and clean up one overlay widget."""
    widget = BreakOverlay(FakeClock())
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()


def test_overlay_has_expected_copy_and_four_actions(overlay: BreakOverlay) -> None:
    """Show the guide copy and exactly the four prescribed buttons."""
    assert overlay.prompt_label.text() == "Time to rest your eyes 👀"
    assert [
        overlay.eye_yoga_button.text(),
        overlay.quick_break_button.text(),
        overlay.snooze_button.text(),
        overlay.skip_button.text(),
    ] == ["Eye Yoga (60s)", "Quick break (20s)", "Snooze 5 min", "Skip"]


def test_overlay_displays_queued_recovery_copy(overlay: BreakOverlay) -> None:
    """Show the meeting recovery copy supplied by the scheduler event."""
    overlay.show_prompt(
        ShowPrompt(kind="quick", message="Meeting's over. Want a quick eye break?")
    )

    assert overlay.prompt_label.text() == "Meeting's over. Want a quick eye break?"

    overlay.show_prompt(ShowPrompt(kind="quick"))
    assert overlay.prompt_label.text() == "Time to rest your eyes 👀"


def test_always_allow_action_emits_only_current_process_name(
    overlay: BreakOverlay,
) -> None:
    """Emit the in-memory executable name and keep paths unavailable."""
    emitted: list[str] = []
    overlay.always_allow_here_requested.connect(emitted.append)
    overlay.set_current_process("editor.exe")
    overlay.always_allow_button.click()

    assert emitted == ["editor.exe"]
    overlay.set_current_process(r"C:\Users\A\editor.exe")
    assert not overlay.always_allow_button.isEnabled()


def test_overlay_is_frameless_topmost_and_does_not_activate_on_show(
    overlay: BreakOverlay,
) -> None:
    """Use the requested window flags without taking focus on show."""
    flags = overlay.windowFlags()

    assert flags & Qt.WindowType.FramelessWindowHint
    assert flags & Qt.WindowType.WindowStaysOnTopHint
    assert overlay.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
    assert overlay.focusPolicy() is Qt.FocusPolicy.NoFocus


@pytest.mark.parametrize(
    ("button_name", "signal_name"),
    [
        ("eye_yoga_button", "eye_yoga_requested"),
        ("quick_break_button", "quick_break_requested"),
        ("snooze_button", "snooze_requested"),
        ("skip_button", "skip_requested"),
    ],
)
def test_button_emits_its_action_and_closes_overlay(
    overlay: BreakOverlay,
    button_name: str,
    signal_name: str,
) -> None:
    """Emit the matching action signal and dismiss the overlay on selection."""
    actions: list[str] = []
    getattr(overlay, signal_name).connect(lambda: actions.append(signal_name))
    overlay.show()
    getattr(overlay, button_name).click()

    assert actions == [signal_name]
    assert not overlay.isVisible()


def test_escape_dismisses_overlay(overlay: BreakOverlay, app: QApplication) -> None:
    """Dismiss the card and emit its dismissal signal on Escape."""
    dismissed: list[bool] = []
    overlay.dismissed.connect(lambda: dismissed.append(True))
    overlay.show()
    event = QKeyEvent(
        QEvent.Type.KeyPress,
        Qt.Key.Key_Escape,
        Qt.KeyboardModifier.NoModifier,
    )

    QApplication.sendEvent(overlay, event)
    app.processEvents()

    assert dismissed == [True]
    assert not overlay.isVisible()


def test_countdown_uses_injected_clock_and_does_not_auto_dismiss(
    app: QApplication,
) -> None:
    """Show 20 seconds, update from the clock, and remain dismissible at zero."""
    clock = FakeClock()
    overlay = BreakOverlay(clock)
    overlay.show_prompt()
    assert overlay.countdown_ring.seconds_remaining == 20

    clock.advance(5)
    overlay.refresh_countdown()
    assert overlay.countdown_ring.seconds_remaining == 15

    clock.advance(15)
    overlay.refresh_countdown()
    assert overlay.countdown_ring.seconds_remaining == 0
    assert overlay.isVisible()
    overlay.close()
    app.processEvents()


def test_stylesheet_uses_style_guide_tokens() -> None:
    """Load the QSS file and verify key light-theme tokens are present."""
    stylesheet = load_stylesheet()

    assert "#F7FAF9" in stylesheet
    assert "#14201E" in stylesheet
    assert "#2A9D8F" in stylesheet
    assert "#E9C46A" in stylesheet
