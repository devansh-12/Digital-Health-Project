"""Start ScreenSense and connect scheduler events to the UI."""

from PyQt6.QtWidgets import QApplication

from screensense.core.clock import Clock
from screensense.core.context import ContextRule
from screensense.core.events import EventBus
from screensense.core.scheduler import Scheduler
from screensense.core.tracker import Tracker
from screensense.platform_adapters.clock import SystemClock
from screensense.platform_adapters.windows import (
    WindowsAppDataProvider,
    WindowsPowerProvider,
    WindowsWindowProvider,
)
from screensense.storage.db import open_database
from screensense.storage.repositories import (
    BreaksRepository,
    ContextRulesRepository,
    SettingsRepository,
    UsageHourlyRepository,
)
from screensense.ui.event_bridge import SchedulerUiBridge
from screensense.ui.overlay import BreakOverlay
from screensense.ui.platform_event_bridge import PowerEventBridge
from screensense.ui.settings import SettingsDialog
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
    settings_repository = SettingsRepository(database)
    rules_repository = ContextRulesRepository(database)
    usage_repository = UsageHourlyRepository(
        connection_factory=lambda: open_database(database_path)
    )
    settings_dialog = SettingsDialog(settings_repository, rules_repository)
    scheduler = Scheduler(
        settings_repository.load(), clock, event_bus, breaks_repository=breaks_repository
    )
    settings_dialog.settings_saved.connect(scheduler.update_settings)
    tracker = Tracker(clock)
    overlay = BreakOverlay(clock)
    tray = ScreenSenseTray(app.quit, settings_dialog.show, parent=app)
    window_provider = WindowsWindowProvider()
    ui_bridge = SchedulerUiBridge(
        event_bus,
        scheduler,
        overlay,
        tray,
        current_process=lambda: (
            window.process if (window := window_provider.foreground()) is not None else None
        ),
        allow_process=lambda process: rules_repository.set_rule(
            process, ContextRule.ALLOW
        ),
        parent=app,
    )
    usage_flush = UsageFlushController(tracker, usage_repository, parent=app)
    power_provider = WindowsPowerProvider()
    power_bridge = PowerEventBridge(usage_flush.handle_power_event, parent=app)
    power_provider.subscribe(power_bridge.enqueue)
    power_provider.start()

    app.aboutToQuit.connect(tray.close)
    app.aboutToQuit.connect(settings_dialog.close)
    app.aboutToQuit.connect(ui_bridge.close)
    app.aboutToQuit.connect(usage_flush.flush_and_wait)
    app.aboutToQuit.connect(power_provider.stop)
    app.aboutToQuit.connect(database.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
