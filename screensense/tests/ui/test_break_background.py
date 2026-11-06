"""Test the animated gradient break background."""

import os
import pytest
from PyQt6.QtWidgets import QApplication

from screensense.ui.break_background import GradientBreakBackground


@pytest.fixture(scope="module")
def app() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_gradient_break_background_animation_cycle(app: QApplication) -> None:
    bg = GradientBreakBackground()
    assert bg._phase == 0.0

    bg.start()
    assert bg._timer.isActive()

    bg._tick()
    assert bg._phase > 0.0

    bg.stop()
    assert not bg._timer.isActive()
    bg.close()

