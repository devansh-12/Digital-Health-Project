"""Test the floating webcam calibration progress card."""

import pytest
from PyQt6.QtWidgets import QApplication

from screensense.ui.blink_calibration import BlinkCalibrationCard


@pytest.fixture(scope="module")
def app() -> QApplication:
    return QApplication.instance() or QApplication([])


def test_calibration_card_lifecycle(app: QApplication) -> None:
    card = BlinkCalibrationCard()
    assert not card.isVisible()
    assert card._elapsed == 0.0

    card.start()
    assert card.isVisible()
    assert card._timer.isActive()

    # Simulate tick
    card._on_tick()
    assert card._elapsed > 0.0

    card.finish()
    assert not card.isVisible()
    assert not card._timer.isActive()
    card.close()

