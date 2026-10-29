"""Start ScreenSense and connect scheduler events to the UI."""

from PyQt6.QtWidgets import QApplication

from screensense.core.clock import Clock
from screensense.core.config import Settings
from screensense.core.events import EventBus
from screensense.core.scheduler import Scheduler
from screensense.platform_adapters.clock import SystemClock
from screensense.ui.event_bridge import SchedulerUiBridge
from screensense.ui.overlay import BreakOverlay
from screensense.ui.theme import load_stylesheet
from screensense.ui.tray import ScreenSenseTray


def main() -> int:
    """Create the scheduler, overlay, tray, and Qt event loop."""
    app = QApplication([])
    app.setApplicationName("ScreenSense")
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(load_stylesheet())

    event_bus = EventBus()
    clock: Clock = SystemClock()
    scheduler = Scheduler(Settings(), clock, event_bus)
    overlay = BreakOverlay(clock)
    tray = ScreenSenseTray(app.quit, parent=app)
    ui_bridge = SchedulerUiBridge(event_bus, scheduler, overlay, tray, parent=app)

    app.aboutToQuit.connect(tray.close)
    app.aboutToQuit.connect(ui_bridge.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
