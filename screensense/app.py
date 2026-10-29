"""Start ScreenSense and connect scheduler events to the UI."""

from PyQt6.QtWidgets import QApplication

from screensense.core.clock import Clock
from screensense.core.config import Settings
from screensense.core.events import EventBus
from screensense.core.scheduler import Scheduler
from screensense.core.tracker import Tracker
from screensense.platform_adapters.clock import SystemClock
from screensense.platform_adapters.windows import (
    WindowsAppDataProvider,
    WindowsPowerProvider,
)
from screensense.storage.db import open_database
from screensense.storage.repositories import (
    BreaksRepository,
    UsageHourlyRepository,
)
from screensense.ui.event_bridge import SchedulerUiBridge
from screensense.ui.overlay import BreakOverlay
from screensense.ui.platform_event_bridge import PowerEventBridge
from screensense.ui.theme import load_stylesheet
from screensense.ui.tray import ScreenSenseTray
from screensense.ui.usage_flush import UsageFlushController


def main() -> int:
    """Create the scheduler, overlay, tray, and Qt event loop."""
    app = QApplication([])
    app.setApplicationName("ScreenSense")
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(load_stylesheet())

    event_bus = EventBus()
    clock: Clock = SystemClock()
    database_path = WindowsAppDataProvider().application_data_dir() / "screensense.sqlite3"
    database = open_database(database_path)
    breaks_repository = BreaksRepository(database)
    usage_repository = UsageHourlyRepository(
        connection_factory=lambda: open_database(database_path)
    )
    scheduler = Scheduler(
        Settings(), clock, event_bus, breaks_repository=breaks_repository
    )
    tracker = Tracker(clock)
    overlay = BreakOverlay(clock)
    tray = ScreenSenseTray(app.quit, parent=app)
    ui_bridge = SchedulerUiBridge(event_bus, scheduler, overlay, tray, parent=app)
    usage_flush = UsageFlushController(tracker, usage_repository, parent=app)
    power_provider = WindowsPowerProvider()
    power_bridge = PowerEventBridge(usage_flush.handle_power_event, parent=app)
    power_provider.subscribe(power_bridge.enqueue)
    power_provider.start()

    app.aboutToQuit.connect(tray.close)
    app.aboutToQuit.connect(ui_bridge.close)
    app.aboutToQuit.connect(usage_flush.flush_and_wait)
    app.aboutToQuit.connect(power_provider.stop)
    app.aboutToQuit.connect(database.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
