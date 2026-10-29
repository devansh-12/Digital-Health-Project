"""Test threaded usage flush coordination and power-event behavior."""

import os

import pytest
from PyQt6.QtWidgets import QApplication

from screensense.core.clock import FakeClock
from screensense.core.context import ContextState
from screensense.core.tracker import Tracker
from screensense.platform_adapters.base import PowerEvent
from screensense.storage.db import open_database
from screensense.storage.repositories import UsageHourlyRepository
from screensense.ui.usage_flush import UsageFlushController


@pytest.fixture(scope="module")
def app() -> QApplication:
    """Create an offscreen QApplication for worker-pool tests."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_controller_flushes_on_sleep_and_shutdown(app: QApplication, tmp_path) -> None:
    """Persist queued activity before sleep and again at application shutdown."""
    database_path = tmp_path / "usage.sqlite3"
    open_database(database_path).close()
    writer = UsageHourlyRepository(
        connection_factory=lambda: open_database(database_path)
    )
    clock = FakeClock(wall_seconds=3_600)
    tracker = Tracker(clock)
    tracker.sample(ContextState.FREE)
    clock.advance(5)
    tracker.sample(ContextState.FREE)
    controller = UsageFlushController(tracker, writer, parent=app)
    assert controller._timer.interval() == 60_000

    controller.handle_power_event(PowerEvent.SLEEP)
    reader = open_database(database_path)
    try:
        row = reader.execute(
            "SELECT active_s FROM usage_hourly WHERE hour_start = ?", (3_600,)
        ).fetchone()
        assert row is not None
        assert row[0] == 5
    finally:
        reader.close()

    clock.advance(3 * 60 * 60)
    controller.handle_power_event(PowerEvent.RESUME)
    clock.advance(5)
    tracker.sample(ContextState.FREE)
    controller.handle_power_event(PowerEvent.LOCK)

    reader = open_database(database_path)
    try:
        row = reader.execute(
            "SELECT SUM(active_s) FROM usage_hourly"
        ).fetchone()
        assert row is not None
        assert row[0] == 10
    finally:
        reader.close()

    controller.handle_power_event(PowerEvent.UNLOCK)
    clock.advance(5)
    tracker.sample(ContextState.FREE)
    controller.flush_and_wait()

    reader = open_database(database_path)
    try:
        row = reader.execute("SELECT SUM(active_s) FROM usage_hourly").fetchone()
        assert row is not None
        assert row[0] == 15
    finally:
        reader.close()
    controller.deleteLater()
    app.processEvents()
