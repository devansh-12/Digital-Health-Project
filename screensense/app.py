import logging
import sys
from dataclasses import replace
from datetime import datetime
from types import TracebackType

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from screensense.core.clock import Clock
from screensense.core.config import Settings
from screensense.core.context import ContextEvaluator, ContextInputs, ContextRule
from screensense.core.events import EventBus
from screensense.core.scheduler import Scheduler, State
from screensense.core.tracker import Tracker
from screensense.platform_adapters.base import PowerEvent
from screensense.platform_adapters.clock import SystemClock
from screensense.platform_adapters.factory import get_platform_providers
from screensense.storage.db import open_database
from screensense.storage.repositories import (
    BadgesRepository,
    BlinkMetricsRepository,
    BlinkMinuteRecord,
    BreaksRepository,
    ContextRulesRepository,
    DailyScoresRepository,
    SettingsRepository,
    StreaksRepository,
    UsageHourlyRepository,
    YogaSessionsRepository,
)
from screensense.ui.dashboard.window import DashboardWindow
from screensense.ui.event_bridge import SchedulerUiBridge
from screensense.ui.eye_yoga.player import EyeYogaPlayer
from screensense.ui.onboarding import OnboardingDialog
from screensense.ui.overlay import BreakOverlay
from screensense.ui.platform_event_bridge import PowerEventBridge
from screensense.ui.quick_break import QuickBreakDialog
from screensense.ui.settings import SettingsDialog
from screensense.ui.theme import load_stylesheet
from screensense.ui.tray import ScreenSenseTray
from screensense.ui.usage_flush import UsageFlushController
from screensense.vision.worker import VisionMonitorProcess

_LOGGER = logging.getLogger(__name__)


def main() -> int:
    """Create the scheduler, overlay, tray, and Qt event loop."""
    app = QApplication([])
    app.setApplicationName("ScreenSense")
    app.setQuitOnLastWindowClosed(False)

    event_bus = EventBus()
    clock: Clock = SystemClock()
    providers = get_platform_providers()
    database_path = providers.app_data.application_data_dir() / "screensense.sqlite3"
    database = open_database(database_path)
    logging.basicConfig(
        filename=database_path.with_name("screensense.log"),
        level=logging.ERROR,
        format="%(asctime)s %(levelname)s %(message)s",
    )

    def handle_uncaught_exception(
        exception_type: type[BaseException],
        exception: BaseException,
        traceback: TracebackType | None,
    ) -> None:
        _LOGGER.error(
            "Unhandled application exception",
            exc_info=(exception_type, exception, traceback),
        )
        QMessageBox.critical(
            None,
            "ScreenSense encountered a problem",
            "ScreenSense encountered an unexpected problem. "
            "A local diagnostic log was saved; restart the app to continue.",
        )
        app.quit()

    sys.excepthook = handle_uncaught_exception
    breaks_repository = BreaksRepository(database)
    settings_repository = SettingsRepository(database)
    rules_repository = ContextRulesRepository(database)
    usage_repository = UsageHourlyRepository(
        connection_factory=lambda: open_database(database_path)
    )
    startup_settings = settings_repository.load()
    if not startup_settings.onboarding_completed:
        OnboardingDialog(settings_repository).exec()
        startup_settings = settings_repository.load()
    app.setStyleSheet(load_stylesheet(startup_settings.ui_theme))
    settings_dialog = SettingsDialog(
        settings_repository,
        rules_repository,
        autostart_provider=providers.autostart,
    )
    scheduler = Scheduler(
        settings_repository.load(),
        clock,
        event_bus,
        breaks_repository=breaks_repository,
    )
    vision_monitor: list[VisionMonitorProcess | None] = [None]
    tracker = Tracker(clock)
    overlay = BreakOverlay(clock)
    yoga_repository = YogaSessionsRepository(database)
    yoga_player = EyeYogaPlayer(
        clock=clock,
        reduced_motion=startup_settings.reduced_motion,
        theme=startup_settings.ui_theme,
    )
    quick_break_dialog = QuickBreakDialog(clock)
    yoga_session_start = [0]

    def show_eye_yoga() -> None:
        yoga_session_start[0] = int(clock.wall_time())
        yoga_player.start()

    def launch_eye_yoga() -> None:
        scheduler.start_break(kind="yoga")
        show_eye_yoga()

    def show_quick_break() -> None:
        quick_break_dialog.start(settings_repository.load().quick_break_seconds)

    def handle_yoga_completed(
        steps_done: int, total_steps: int, duration_s: int
    ) -> None:
        yoga_repository.record_session(
            started_at=yoga_session_start[0],
            steps_completed=steps_done,
            total_steps=total_steps,
            duration_s=duration_s,
        )
        if scheduler.state is State.ON_BREAK:
            scheduler.complete_break(duration_s=duration_s)

    def handle_yoga_exited(steps_done: int, total_steps: int, duration_s: int) -> None:
        yoga_repository.record_session(
            started_at=yoga_session_start[0],
            steps_completed=steps_done,
            total_steps=total_steps,
            duration_s=duration_s,
        )
        if scheduler.state is State.ON_BREAK:
            scheduler.cancel_break()

    yoga_player.session_completed.connect(handle_yoga_completed)
    yoga_player.session_exited.connect(handle_yoga_exited)

    def handle_quick_break_completed(duration_s: int) -> None:
        if scheduler.state is State.ON_BREAK:
            scheduler.complete_break(duration_s=duration_s)

    def handle_quick_break_exited() -> None:
        if scheduler.state is State.ON_BREAK:
            scheduler.cancel_break()

    quick_break_dialog.session_completed.connect(handle_quick_break_completed)
    quick_break_dialog.session_exited.connect(handle_quick_break_exited)

    scores_repository = DailyScoresRepository(database)
    streaks_repository = StreaksRepository(database)
    badges_repository = BadgesRepository(database)
    dashboard_window = DashboardWindow(
        database=database,
        settings_repo=settings_repository,
        breaks_repo=breaks_repository,
        yoga_repo=yoga_repository,
        usage_repo=usage_repository,
        scores_repo=scores_repository,
        streaks_repo=streaks_repository,
        badges_repo=badges_repository,
        blink_repo=BlinkMetricsRepository(database),
        settings_dialog=settings_dialog,
        clock=clock,
    )

    def show_dashboard() -> None:
        dashboard_window.refresh_data()
        dashboard_window.show()
        dashboard_window.raise_()
        dashboard_window.activateWindow()

    tray = ScreenSenseTray(
        on_quit=app.quit,
        on_settings=settings_dialog.show,
        on_eye_yoga=launch_eye_yoga,
        on_dashboard=show_dashboard,
        on_stop_blink_monitor=lambda: stop_blink_monitor(persist_disabled=True),
        parent=app,
    )
    blink_repository = BlinkMetricsRepository(database)

    def stop_blink_monitor(*, persist_disabled: bool) -> None:
        monitor = vision_monitor[0]
        if monitor is not None:
            monitor.stop()
            vision_monitor[0] = None
        tray.set_camera_active(False)
        settings_dialog.set_blink_monitor_enabled(False)
        if persist_disabled:
            current = settings_repository.load()
            if current.blink_monitor_enabled:
                settings_repository.save(replace(current, blink_monitor_enabled=False))

    def start_blink_monitor() -> None:
        if vision_monitor[0] is not None:
            return
        monitor = VisionMonitorProcess()
        try:
            monitor.start()
        except (AssertionError, OSError, RuntimeError) as error:
            tray.show_message(
                "Blink monitoring could not start",
                str(error),
                QSystemTrayIcon.MessageIcon.Warning,
            )
            settings_dialog.set_blink_monitor_enabled(False)
            settings_repository.save(
                replace(settings_repository.load(), blink_monitor_enabled=False)
            )
            return
        vision_monitor[0] = monitor
        tray.set_camera_active(True, "Starting")

    def on_settings_saved(updated_settings: Settings) -> None:
        scheduler.update_settings(updated_settings)
        app.setStyleSheet(load_stylesheet(updated_settings.ui_theme))
        settings_dialog.set_theme(updated_settings.ui_theme)
        dashboard_window.set_theme(updated_settings.ui_theme)
        yoga_player.set_theme(updated_settings.ui_theme)
        yoga_player.set_reduced_motion(updated_settings.reduced_motion)
        if updated_settings.blink_monitor_enabled:
            start_blink_monitor()
        else:
            stop_blink_monitor(persist_disabled=False)

    settings_dialog.settings_saved.connect(on_settings_saved)

    def poll_blink_monitor() -> None:
        monitor = vision_monitor[0]
        if monitor is None:
            return
        messages = monitor.read_messages()
        for message in messages:
            if message["type"] == "status":
                tray.set_camera_active(True, str(message["status"]).title())
            elif message["type"] == "metrics":
                values = message["metrics"]
                blink_repository.record_minute(
                    BlinkMinuteRecord(
                        minute_start=int(values["minute_start"]),
                        blinks=int(values["blinks"]),
                        face_present_ratio=float(values["face_present_ratio"]),
                        ear_mean=(
                            float(values["ear_mean"])
                            if values["ear_mean"] is not None
                            else None
                        ),
                    )
                )
            elif message["type"] == "error":
                error = str(message["message"])
                stop_blink_monitor(persist_disabled=True)
                tray.show_message(
                    "Blink monitoring stopped",
                    error,
                    QSystemTrayIcon.MessageIcon.Warning,
                )
                return
        if not monitor.is_running:
            stop_blink_monitor(persist_disabled=True)
            tray.show_message(
                "Blink monitoring stopped",
                "The vision worker exited unexpectedly. You can try enabling it again in Settings.",
                QSystemTrayIcon.MessageIcon.Warning,
            )

    blink_poll_timer = QTimer(app)
    blink_poll_timer.setInterval(250)
    blink_poll_timer.timeout.connect(poll_blink_monitor)
    blink_poll_timer.start()
    if settings_repository.load().blink_monitor_enabled:
        start_blink_monitor()
    ui_bridge = SchedulerUiBridge(
        event_bus,
        scheduler,
        overlay,
        tray,
        current_process=lambda: (
            window.process
            if (window := providers.window.foreground()) is not None
            else None
        ),
        allow_process=lambda process: rules_repository.set_rule(
            process, ContextRule.ALLOW
        ),
        on_start_yoga=show_eye_yoga,
        on_start_quick_break=show_quick_break,
        parent=app,
    )
    usage_flush = UsageFlushController(tracker, usage_repository, parent=app)

    power_state = {"locked": False, "asleep": False}

    def handle_power_transition(event: PowerEvent) -> None:
        if event is PowerEvent.LOCK:
            power_state["locked"] = True
        elif event is PowerEvent.UNLOCK:
            power_state["locked"] = False
        elif event is PowerEvent.SLEEP:
            power_state["asleep"] = True
        elif event is PowerEvent.RESUME:
            power_state["asleep"] = False
        usage_flush.handle_power_event(event)

    power_bridge = PowerEventBridge(handle_power_transition, parent=app)
    providers.power.subscribe(power_bridge.enqueue)
    providers.power.start()

    evaluator = ContextEvaluator(clock, rules_repository, event_bus)

    def on_tick() -> None:
        current_settings = settings_repository.load()
        idle_s = providers.idle.seconds_since_input()
        window = providers.window.foreground()
        inputs = ContextInputs(
            locked=power_state["locked"],
            asleep=power_state["asleep"],
            now=datetime.fromtimestamp(clock.wall_time()),
            work_hours=current_settings.work_hours,
            idle_seconds=idle_s,
            idle_threshold=float(current_settings.idle_threshold_seconds),
            window=window,
        )
        context = evaluator.evaluate(inputs)
        tracker.sample(context)
        scheduler.tick(context)

    tick_timer = QTimer(app)
    tick_timer.setInterval(1000)
    tick_timer.timeout.connect(on_tick)
    tick_timer.start()

    app.aboutToQuit.connect(tick_timer.stop)
    app.aboutToQuit.connect(blink_poll_timer.stop)
    app.aboutToQuit.connect(lambda: stop_blink_monitor(persist_disabled=False))
    app.aboutToQuit.connect(yoga_player.close)
    app.aboutToQuit.connect(quick_break_dialog.close)
    app.aboutToQuit.connect(tray.close)
    app.aboutToQuit.connect(settings_dialog.close)
    app.aboutToQuit.connect(ui_bridge.close)
    app.aboutToQuit.connect(usage_flush.flush_and_wait)
    app.aboutToQuit.connect(providers.power.stop)
    app.aboutToQuit.connect(database.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
