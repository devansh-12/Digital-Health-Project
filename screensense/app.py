"""Application entry point and subsystem coordinator."""

import logging
import sys
from dataclasses import replace
from datetime import datetime
from types import TracebackType
from typing import Any

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from screensense.core.blink_alert import BlinkAlertEvaluator
from screensense.core.clock import Clock
from screensense.core.config import Settings
from screensense.core.context import ContextEvaluator, ContextInputs, ContextRule
from screensense.core.events import BreakKind, EventBus
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
from screensense.ui.blink_calibration import BlinkCalibrationCard
from screensense.ui.dashboard.window import DashboardWindow
from screensense.ui.event_bridge import SchedulerUiBridge
from screensense.ui.eye_yoga.player import EyeYogaPlayer
from screensense.ui.onboarding import OnboardingDialog
from screensense.ui.overlay import BreakOverlay
from screensense.ui.platform_event_bridge import PowerEventBridge
from screensense.ui.quick_break import QuickBreakDialog
from screensense.ui.settings import SettingsDialog
from screensense.ui.stats_overlay import StatsOverlayWidget
from screensense.ui.theme import load_stylesheet
from screensense.ui.tray import ScreenSenseTray
from screensense.ui.usage_flush import UsageFlushController
from screensense.vision.worker import VisionMonitorProcess

_LOGGER = logging.getLogger(__name__)


def handle_uncaught_exception(
    exception_type: type[BaseException],
    exception: BaseException,
    traceback: TracebackType | None,
) -> None:
    """Log unhandled errors and notify user before terminating."""
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
    app = QApplication.instance()
    if app is not None:
        app.quit()


def get_foreground_process(providers: Any) -> str | None:
    """Retrieve the name of the current foreground process without inline assignment."""
    window = providers.window.foreground()
    if window is not None:
        return window.process
    return None


class PowerStateTracker:
    """Track lock and sleep transitions."""

    def __init__(self, usage_flush: UsageFlushController) -> None:
        self.locked = False
        self.asleep = False
        self._usage_flush = usage_flush

    def handle_transition(self, event: PowerEvent) -> None:
        """Update local power flags and inform the usage flush controller."""
        if event is PowerEvent.LOCK:
            self.locked = True
        elif event is PowerEvent.UNLOCK:
            self.locked = False
        elif event is PowerEvent.SLEEP:
            self.asleep = True
        elif event is PowerEvent.RESUME:
            self.asleep = False
        self._usage_flush.handle_power_event(event)


class BreakSessionCoordinator:
    """Coordinate Eye Yoga and timed quick break dialogs with the scheduler."""

    def __init__(
        self,
        scheduler: Scheduler,
        yoga_player: EyeYogaPlayer,
        quick_break_dialog: QuickBreakDialog,
        yoga_repository: YogaSessionsRepository,
        clock: Clock,
    ) -> None:
        self._scheduler = scheduler
        self._yoga_player = yoga_player
        self._quick_break = quick_break_dialog
        self._yoga_repo = yoga_repository
        self._clock = clock
        self._yoga_session_start = 0

        self._yoga_player.session_completed.connect(self._on_yoga_completed)
        self._yoga_player.session_exited.connect(self._on_yoga_exited)
        self._quick_break.session_completed.connect(self._on_break_completed)
        self._quick_break.session_exited.connect(self._on_break_exited)

    def show_eye_yoga(self) -> None:
        """Record session timestamp and display the Eye Yoga routine."""
        self._yoga_session_start = int(self._clock.wall_time())
        self._yoga_player.start()

    def launch_eye_yoga(self) -> None:
        """Begin an on-demand Eye Yoga break in the scheduler and show the player."""
        self._scheduler.start_break(kind="yoga")
        self.show_eye_yoga()

    def show_scheduled_break(self, kind: BreakKind, duration_s: int) -> None:
        """Display the timed break window for the prompt's chosen duration."""
        self._quick_break.start(duration_s, kind=kind)

    def _on_yoga_completed(self, done: int, total: int, duration_s: int) -> None:
        self._yoga_repo.record_session(
            started_at=self._yoga_session_start,
            steps_completed=done,
            total_steps=total,
            duration_s=duration_s,
        )
        if self._scheduler.state is State.ON_BREAK:
            self._scheduler.complete_break(duration_s=duration_s)

    def _on_yoga_exited(self, done: int, total: int, duration_s: int) -> None:
        self._yoga_repo.record_session(
            started_at=self._yoga_session_start,
            steps_completed=done,
            total_steps=total,
            duration_s=duration_s,
        )
        if self._scheduler.state is State.ON_BREAK:
            self._scheduler.cancel_break()

    def _on_break_completed(self, duration_s: int) -> None:
        if self._scheduler.state is State.ON_BREAK:
            self._scheduler.complete_break(duration_s=duration_s)

    def _on_break_exited(self) -> None:
        if self._scheduler.state is State.ON_BREAK:
            self._scheduler.cancel_break()


class BlinkMonitorController:
    """Manage lifecycle and background messages for the webcam vision worker."""

    def __init__(
        self,
        tray: ScreenSenseTray | None,
        settings_dialog: SettingsDialog,
        settings_repository: SettingsRepository,
        blink_repository: BlinkMetricsRepository,
        stats_overlay: StatsOverlayWidget,
        scheduler: Scheduler | None = None,
        calibration_card: BlinkCalibrationCard | None = None,
        clock: Clock | None = None,
    ) -> None:
        self._monitor: VisionMonitorProcess | None = None
        self._tray = tray
        self._settings_dialog = settings_dialog
        self._settings_repository = settings_repository
        self._blink_repository = blink_repository
        self._stats_overlay = stats_overlay
        self._scheduler = scheduler
        self._calibration_card = calibration_card
        self._clock = clock
        self._blink_alert = (
            BlinkAlertEvaluator(clock) if clock is not None else None
        )

    def start(self) -> None:
        """Launch the worker process if not already running."""
        if self._monitor is not None:
            return
        monitor = VisionMonitorProcess()
        try:
            monitor.start()
        except (AssertionError, OSError, RuntimeError) as error:
            if self._tray is not None:
                self._tray.show_message(
                    "Blink monitoring could not start",
                    str(error),
                    QSystemTrayIcon.MessageIcon.Warning,
                )
            self._settings_dialog.set_blink_monitor_enabled(False)
            self._settings_repository.save(
                replace(self._settings_repository.load(), blink_monitor_enabled=False)
            )
            return
        self._monitor = monitor
        if self._tray is not None:
            self._tray.set_camera_active(True, "Starting")

    def stop(self, *, persist_disabled: bool) -> None:
        """Halt the vision process and update tray/dialog states."""
        if self._monitor is not None:
            self._monitor.stop()
            self._monitor = None
        if self._calibration_card is not None:
            self._calibration_card.finish()
        if self._tray is not None:
            self._tray.set_camera_active(False)
        self._settings_dialog.set_blink_monitor_enabled(False)
        if persist_disabled:
            current = self._settings_repository.load()
            if current.blink_monitor_enabled:
                self._settings_repository.save(
                    replace(current, blink_monitor_enabled=False)
                )

    def poll(self) -> None:
        """Process pending message batches from the vision monitor."""
        if self._monitor is None:
            return
        for message in self._monitor.read_messages():
            if self._handle_message(message):
                return
        if not self._monitor.is_running:
            self.stop(persist_disabled=True)
            if self._tray is not None:
                self._tray.show_message(
                    "Blink monitoring stopped",
                    "The vision worker exited unexpectedly. You can try enabling it again in Settings.",
                    QSystemTrayIcon.MessageIcon.Warning,
                )

    def _handle_message(self, message: dict[str, Any]) -> bool:
        msg_type = message.get("type")
        if msg_type == "status":
            status_str = str(message["status"])
            if self._tray is not None:
                self._tray.set_camera_active(True, status_str.title())
            if status_str == "calibrating" and self._calibration_card is not None:
                self._calibration_card.start()
            elif status_str == "monitoring" and self._calibration_card is not None:
                self._calibration_card.finish()
        elif msg_type == "metrics":
            self._record_metrics(message["metrics"])
        elif msg_type == "error":
            self.stop(persist_disabled=True)
            if self._tray is not None:
                self._tray.show_message(
                    "Blink monitoring stopped",
                    str(message["message"]),
                    QSystemTrayIcon.MessageIcon.Warning,
                )
            return True
        return False

    def _record_metrics(self, values: dict[str, Any]) -> None:
        blinks_count = int(values["blinks"])
        face_present_ratio = float(values["face_present_ratio"])
        self._stats_overlay.update_blink_rate(blinks_count)
        self._blink_repository.record_minute(
            BlinkMinuteRecord(
                minute_start=int(values["minute_start"]),
                blinks=blinks_count,
                face_present_ratio=face_present_ratio,
                ear_mean=(
                    float(values["ear_mean"])
                    if values.get("ear_mean") is not None
                    else None
                ),
            )
        )
        if (
            self._blink_alert is not None
            and self._scheduler is not None
            and self._tray is not None
            and self._blink_alert.record_minute(blinks_count, face_present_ratio)
            and self._scheduler.nudge_break_forward()
        ):
            self._tray.show_message(
                "Rest your eyes soon",
                "Your blink rate has been low recently. Next break has been moved forward.",
                QSystemTrayIcon.MessageIcon.Information,
            )


def main() -> int:
    """Create the scheduler, overlay, tray, and Qt event loop."""
    app = QApplication([])
    app.setApplicationName("ScreenSense")
    app.setQuitOnLastWindowClosed(False)
    sys.excepthook = handle_uncaught_exception

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

    breaks_repo = BreaksRepository(database)
    settings_repo = SettingsRepository(database)
    rules_repo = ContextRulesRepository(database)
    usage_repo = UsageHourlyRepository(
        connection_factory=lambda: open_database(database_path)
    )

    startup_settings = settings_repo.load()
    if not startup_settings.onboarding_completed:
        OnboardingDialog(settings_repo).exec()
        startup_settings = settings_repo.load()

    cutoff_epoch = int(clock.wall_time()) - startup_settings.data_retention_days * 86_400
    usage_repo.prune_before(cutoff_epoch)
    BlinkMetricsRepository(database).prune_before(cutoff_epoch)

    app.setStyleSheet(load_stylesheet(startup_settings.ui_theme))
    settings_dialog = SettingsDialog(
        settings_repo,
        rules_repo,
        autostart_provider=providers.autostart,
    )
    scheduler = Scheduler(
        startup_settings,
        clock,
        event_bus,
        breaks_repository=breaks_repo,
    )
    tracker = Tracker(clock)
    overlay = BreakOverlay(clock)
    yoga_player = EyeYogaPlayer(
        clock=clock,
        reduced_motion=startup_settings.reduced_motion,
        theme=startup_settings.ui_theme,
    )
    quick_break_dialog = QuickBreakDialog(clock)

    break_coordinator = BreakSessionCoordinator(
        scheduler=scheduler,
        yoga_player=yoga_player,
        quick_break_dialog=quick_break_dialog,
        yoga_repository=YogaSessionsRepository(database),
        clock=clock,
    )

    dashboard_window = DashboardWindow(
        database=database,
        settings_repo=settings_repo,
        breaks_repo=breaks_repo,
        yoga_repo=YogaSessionsRepository(database),
        usage_repo=usage_repo,
        scores_repo=DailyScoresRepository(database),
        streaks_repo=StreaksRepository(database),
        badges_repo=BadgesRepository(database),
        blink_repo=BlinkMetricsRepository(database),
        settings_dialog=settings_dialog,
        clock=clock,
    )

    def show_dashboard() -> None:
        dashboard_window.refresh_data()
        dashboard_window.show()
        dashboard_window.raise_()
        dashboard_window.activateWindow()

    stats_overlay = StatsOverlayWidget()
    calibration_card = BlinkCalibrationCard()

    def toggle_stats_overlay() -> None:
        if stats_overlay.isVisible():
            stats_overlay.hide()
        else:
            stats_overlay.show()

    blink_controller = BlinkMonitorController(
        tray=None,  # will set below
        settings_dialog=settings_dialog,
        settings_repository=settings_repo,
        blink_repository=BlinkMetricsRepository(database),
        stats_overlay=stats_overlay,
        scheduler=scheduler,
        calibration_card=calibration_card,
        clock=clock,
    )

    tray = ScreenSenseTray(
        on_quit=app.quit,
        on_settings=settings_dialog.show,
        on_eye_yoga=break_coordinator.launch_eye_yoga,
        on_dashboard=show_dashboard,
        on_stop_blink_monitor=lambda: blink_controller.stop(persist_disabled=True),
        on_toggle_stats=toggle_stats_overlay,
        parent=app,
    )
    blink_controller._tray = tray

    def on_settings_saved(updated_settings: Settings) -> None:
        scheduler.update_settings(updated_settings)
        app.setStyleSheet(load_stylesheet(updated_settings.ui_theme))
        settings_dialog.set_theme(updated_settings.ui_theme)
        dashboard_window.set_theme(updated_settings.ui_theme)
        yoga_player.set_theme(updated_settings.ui_theme)
        yoga_player.set_reduced_motion(updated_settings.reduced_motion)
        overlay.set_snooze_minutes(updated_settings.snooze_minutes)
        if updated_settings.blink_monitor_enabled:
            blink_controller.start()
        else:
            blink_controller.stop(persist_disabled=False)

    settings_dialog.settings_saved.connect(on_settings_saved)

    blink_poll_timer = QTimer(app)
    blink_poll_timer.setInterval(250)
    blink_poll_timer.timeout.connect(blink_controller.poll)
    blink_poll_timer.start()

    if startup_settings.blink_monitor_enabled:
        blink_controller.start()

    ui_bridge = SchedulerUiBridge(
        event_bus,
        scheduler,
        overlay,
        tray,
        current_process=lambda: get_foreground_process(providers),
        allow_process=lambda process: rules_repo.set_rule(process, ContextRule.ALLOW),
        on_start_yoga=break_coordinator.show_eye_yoga,
        on_start_break=break_coordinator.show_scheduled_break,
        parent=app,
    )
    overlay.set_snooze_minutes(startup_settings.snooze_minutes)
    usage_flush = UsageFlushController(tracker, usage_repo, parent=app)

    power_tracker = PowerStateTracker(usage_flush)
    power_bridge = PowerEventBridge(power_tracker.handle_transition, parent=app)
    providers.power.subscribe(power_bridge.enqueue)
    providers.power.start()

    evaluator = ContextEvaluator(clock, rules_repo, event_bus)

    def on_tick() -> None:
        current_settings = settings_repo.load()
        inputs = ContextInputs(
            locked=power_tracker.locked,
            asleep=power_tracker.asleep,
            now=datetime.fromtimestamp(clock.wall_time()),
            work_hours=current_settings.work_hours,
            idle_seconds=providers.idle.seconds_since_input(),
            idle_threshold=float(current_settings.idle_threshold_seconds),
            window=providers.window.foreground(),
        )
        context = evaluator.evaluate(inputs)
        tracker.sample(context)
        scheduler.tick(context)
        stats_overlay.update_active_time(round(scheduler.work_elapsed))

    tick_timer = QTimer(app)
    tick_timer.setInterval(1000)
    tick_timer.timeout.connect(on_tick)
    tick_timer.start()

    app.aboutToQuit.connect(tick_timer.stop)
    app.aboutToQuit.connect(blink_poll_timer.stop)
    app.aboutToQuit.connect(lambda: blink_controller.stop(persist_disabled=False))
    app.aboutToQuit.connect(calibration_card.close)
    app.aboutToQuit.connect(stats_overlay.close)
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
