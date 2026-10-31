from datetime import datetime

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication

from screensense.core.clock import Clock
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
    providers = get_platform_providers()
    database_path = providers.app_data.application_data_dir() / "screensense.sqlite3"
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
    yoga_repository = YogaSessionsRepository(database)
    yoga_player = EyeYogaPlayer(clock=clock)
    yoga_session_start = [0]

    def launch_eye_yoga() -> None:
        yoga_session_start[0] = int(clock.wall_time())
        scheduler.start_break(kind="yoga")
        yoga_player.start()

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

    def handle_yoga_exited(
        steps_done: int, total_steps: int, duration_s: int
    ) -> None:
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
        parent=app,
    )
    ui_bridge = SchedulerUiBridge(
        event_bus,
        scheduler,
        overlay,
        tray,
        current_process=lambda: (
            window.process if (window := providers.window.foreground()) is not None else None
        ),
        allow_process=lambda process: rules_repository.set_rule(
            process, ContextRule.ALLOW
        ),
        on_start_yoga=launch_eye_yoga,
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
    app.aboutToQuit.connect(yoga_player.close)
    app.aboutToQuit.connect(tray.close)
    app.aboutToQuit.connect(settings_dialog.close)
    app.aboutToQuit.connect(ui_bridge.close)
    app.aboutToQuit.connect(usage_flush.flush_and_wait)
    app.aboutToQuit.connect(providers.power.stop)
    app.aboutToQuit.connect(database.close)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
