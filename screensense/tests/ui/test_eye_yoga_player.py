"""Test EyeYogaPlayer UI transitions and events."""

import pytest
from PyQt6.QtWidgets import QApplication

from screensense.core.clock import FakeClock
from screensense.core.yoga import YogaRoutine, YogaStep
from screensense.ui.eye_yoga.player import EyeYogaPlayer


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    """Ensure a QApplication instance is available for Qt widgets."""
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_eye_yoga_player_initial_state(qapp) -> None:
    """Verify EyeYogaPlayer starts with initial step displayed."""
    clock = FakeClock()
    player = EyeYogaPlayer(clock=clock)
    assert player._current_step_index == 0
    assert player._step_title.text() == "Palming"
    assert "Rub palms" in player._step_instruction.text()
    assert player._control_button.text() == "Pause"
    assert not player._is_paused
    player.close()


def test_eye_yoga_player_updates_theme_for_new_and_active_sessions(qapp) -> None:
    player = EyeYogaPlayer(clock=FakeClock(), theme="light")
    assert "#F7FAF9" in player.styleSheet()

    player.start()
    player.set_theme("dark")

    assert "#000000" in player.styleSheet()
    assert "#ffffff" in player._step_title.styleSheet()
    player.close()


def test_eye_yoga_player_pause_resume(qapp) -> None:
    """Verify toggling pause stops time advance and flips button text."""
    clock = FakeClock()
    player = EyeYogaPlayer(clock=clock)
    player.start()

    # Toggle pause
    player._toggle_pause()
    assert player._is_paused
    assert player._control_button.text() == "Resume"

    # Toggle resume
    player._toggle_pause()
    assert not player._is_paused
    assert player._control_button.text() == "Pause"
    player.close()


def test_eye_yoga_player_advance_steps(qapp) -> None:
    """Verify advancing through steps transitions to finish."""
    # Custom 2-step routine for fast deterministic testing
    routine = YogaRoutine(
        id="test_routine",
        total_seconds=4,
        steps=(
            YogaStep("Step A", 2, "Do A", "palming"),
            YogaStep("Step B", 2, "Do B", "blink"),
        ),
    )
    clock = FakeClock()
    player = EyeYogaPlayer(clock=clock, routine=routine)
    player.start()

    # Advance step 1
    player._advance_step()
    assert player._current_step_index == 1
    assert player._step_title.text() == "Step B"

    # Advance past step 2 -> finish
    player._advance_step()
    assert player._is_finished
    assert "Rest complete" in player._step_title.text()
    assert player._control_button.text() == "Done"
    player.close()


def test_eye_yoga_player_exit_signal(qapp) -> None:
    """Verify early exit emits session_exited with completed step count."""
    clock = FakeClock()
    player = EyeYogaPlayer(clock=clock)
    player.start()

    exited_payload: list[tuple[int, int, int]] = []
    player.session_exited.connect(
        lambda done, total, dur: exited_payload.append((done, total, dur))
    )

    player._handle_exit()
    assert len(exited_payload) == 1
    done, total, _duration = exited_payload[0]
    assert done == 0
    assert total == 6
    player.close()


def test_eye_yoga_player_audio_chimes_respect_reduced_motion(qapp) -> None:
    """Verify audio cues are disabled when reduced motion is enabled."""
    clock = FakeClock()
    player_normal = EyeYogaPlayer(clock=clock, reduced_motion=False)
    assert player_normal._step_chime is not None
    assert player_normal._complete_chime is not None
    player_normal.close()

    player_reduced = EyeYogaPlayer(clock=clock, reduced_motion=True)
    assert player_reduced._step_chime is None
    assert player_reduced._complete_chime is None

    # Toggling reduced motion to False sets them up
    player_reduced.set_reduced_motion(False)
    assert player_reduced._step_chime is not None
    player_reduced.close()
