"""Test the transparent stats HUD overlay."""

import os
import pytest
from PyQt6.QtWidgets import QApplication

from screensense.ui.stats_overlay import StatsOverlayWidget


@pytest.fixture(scope="module")
def app() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_stats_overlay_updates_blink_rate(app: QApplication) -> None:
    hud = StatsOverlayWidget()
    assert "-- bpm" in hud._blink_label.text()

    hud.update_blink_rate(16)
    assert "16 bpm" in hud._blink_label.text()

    hud.update_blink_rate(8)
    assert "8 bpm" in hud._blink_label.text()
    hud.close()


def test_stats_overlay_updates_active_time(app: QApplication) -> None:
    hud = StatsOverlayWidget()
    assert "0:00:00" in hud._time_label.text()

    hud.update_active_time(3665)  # 1 hour, 1 minute, 5 seconds
    assert "1:01:05" in hud._time_label.text()
    hud.close()

