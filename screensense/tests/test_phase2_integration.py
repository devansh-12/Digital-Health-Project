"""Exercise context, scheduler, tracker, and SQLite through a simulated workday."""

from datetime import datetime

from screensense.core.clock import FakeClock
from screensense.core.config import Settings
from screensense.core.context import ContextEvaluator, ContextInputs, ContextState
from screensense.core.events import EventBus, ShowPrompt
from screensense.core.scheduler import Scheduler
from screensense.core.tracker import Tracker
from screensense.platform_adapters.base import PowerEvent, WindowInfo
from screensense.platform_adapters.stub import (
    StubIdleProvider,
    StubPowerProvider,
    StubWindowProvider,
)
from screensense.storage.db import open_database
from screensense.storage.repositories import (
    BreakOutcome,
    BreaksRepository,
    ContextRulesRepository,
    UsageHourlyRepository,
)


def test_simulated_eight_hour_day_integrates_phase_two_modules(tmp_path) -> None:
    """Simulate work, calls, idle lunch, fullscreen, sleep, and midnight rollover."""
    connection = open_database(tmp_path / "phase2.sqlite3")
    try:
        clock = FakeClock(wall_seconds=86_400 - 5 * 60)
        event_bus = EventBus()
        breaks = BreaksRepository(connection)
        rules = ContextRulesRepository(connection)
        settings = Settings(work_interval_minutes=60)
        scheduler = Scheduler(settings, clock, event_bus, breaks_repository=breaks)
        tracker = Tracker(clock)
        idle_provider = StubIdleProvider()
        window_provider = StubWindowProvider(
            WindowInfo("Editor", "editor.exe", (0, 0, 1280, 720), False)
        )
        power_provider = StubPowerProvider()
        power_state = {"locked": False, "asleep": False}

        def handle_power_event(event: PowerEvent) -> None:
            """Apply fake power transitions to tracker sampling state."""
            if event is PowerEvent.LOCK:
                power_state["locked"] = True
                tracker.pause()
            elif event is PowerEvent.UNLOCK:
                power_state["locked"] = False
                if not power_state["asleep"]:
                    tracker.resume()
            elif event is PowerEvent.SLEEP:
                power_state["asleep"] = True
                tracker.pause()
            elif event is PowerEvent.RESUME:
                power_state["asleep"] = False
                if not power_state["locked"]:
                    tracker.resume()

        power_provider.subscribe(handle_power_event)
        evaluator = ContextEvaluator(clock, rules, event_bus)
        current_context = [ContextState.FREE]
        prompt_contexts: list[ContextState] = []
        event_bus.subscribe(
            ShowPrompt,
            lambda _event: prompt_contexts.append(current_context[0]),
        )
        tracker.sample(ContextState.FREE)
        scheduler.tick(ContextState.FREE)
        sampled_seconds = 0
        awake_seconds = 0

        def configure_context(context: ContextState) -> None:
            """Set controllable platform values for the requested scenario."""
            idle_provider.idle_seconds = (
                120.0 if context is ContextState.IDLE else 0.0
            )
            if context is ContextState.CALL:
                window_provider.window = WindowInfo(
                    "Zoom Meeting", "zoom.exe", (0, 0, 1280, 720), False
                )
            elif context is ContextState.FULLSCREEN:
                window_provider.window = WindowInfo(
                    "Video", "browser.exe", (0, 0, 1920, 1080), True
                )
            else:
                window_provider.window = WindowInfo(
                    "Editor", "editor.exe", (0, 0, 1280, 720), False
                )

        def run_segment(
            seconds: int,
            requested_context: ContextState,
            *,
            complete_prompts: bool = True,
        ) -> None:
            """Tick the evaluator/scheduler each second and tracker every five."""
            nonlocal awake_seconds, sampled_seconds
            configure_context(requested_context)
            for _ in range(seconds):
                clock.advance(1)
                awake_seconds += 1
                inputs = ContextInputs(
                    locked=power_state["locked"],
                    asleep=power_state["asleep"],
                    now=datetime.fromtimestamp(clock.wall_time()),
                    work_hours=None,
                    idle_seconds=idle_provider.seconds_since_input(),
                    idle_threshold=float(settings.idle_threshold_seconds),
                    window=window_provider.foreground(),
                )
                observed = evaluator.evaluate(inputs)
                current_context[0] = observed
                scheduler.tick(observed)
                sampled_seconds += 1
                if sampled_seconds == 5:
                    tracker.sample(observed)
                    sampled_seconds = 0
                if scheduler.state.value == "prompting" and complete_prompts:
                    assert observed is ContextState.FREE
                    scheduler.start_break()
                    scheduler.complete_break(duration_s=settings.quick_break_seconds)

        run_segment(60 * 60, ContextState.FREE)
        before_call = len(prompt_contexts)
        run_segment(60 * 60, ContextState.CALL)
        assert len(prompt_contexts) == before_call
        run_segment(3, ContextState.FREE, complete_prompts=False)
        assert scheduler.state.value == "prompting"
        scheduler.start_break()
        scheduler.complete_break(duration_s=settings.quick_break_seconds)

        run_segment(5 * 60, ContextState.IDLE)
        run_segment(59 * 60, ContextState.FREE)
        before_fullscreen = len(prompt_contexts)
        run_segment(63, ContextState.FULLSCREEN, complete_prompts=False)
        assert len(prompt_contexts) == before_fullscreen
        run_segment(3, ContextState.FREE, complete_prompts=False)
        assert scheduler.state.value == "prompting"
        scheduler.skip()

        power_provider.emit(PowerEvent.LOCK)
        run_segment(2, ContextState.LOCKED, complete_prompts=False)
        power_provider.emit(PowerEvent.SLEEP)
        clock.advance(3 * 60 * 60)
        power_provider.emit(PowerEvent.RESUME)
        power_provider.emit(PowerEvent.UNLOCK)
        run_segment(2, ContextState.FREE, complete_prompts=False)

        run_segment(8 * 60 * 60 - awake_seconds, ContextState.FREE)

        assert prompt_contexts
        assert all(context is ContextState.FREE for context in prompt_contexts)
        assert tracker.flush(UsageHourlyRepository(connection))

        outcomes = connection.execute(
            "SELECT kind, outcome, COUNT(*) FROM breaks GROUP BY kind, outcome"
        ).fetchall()
        outcome_pairs = {(row[0], row[1]) for row in outcomes}
        assert ("quick", BreakOutcome.COMPLETED.value) in outcome_pairs
        assert ("quick", BreakOutcome.SUPPRESSED.value) in outcome_pairs
        assert ("natural", BreakOutcome.COMPLETED.value) in outcome_pairs

        usage = connection.execute(
            """
            SELECT COALESCE(SUM(active_s), 0), COALESCE(SUM(idle_s), 0),
                   COALESCE(SUM(fullscreen_s), 0), COALESCE(SUM(call_s), 0)
            FROM usage_hourly
            """
        ).fetchone()
        active_s, idle_s, fullscreen_s, call_s = (int(value) for value in usage)
        assert active_s > 0
        assert idle_s > 0
        assert fullscreen_s > 0
        assert call_s > 0
        assert 28_770 <= active_s + idle_s + fullscreen_s + call_s <= 28_800

        hours = connection.execute(
            "SELECT hour_start FROM usage_hourly ORDER BY hour_start"
        ).fetchall()
        hour_starts = [int(row[0]) for row in hours]
        assert min(hour_starts) < 86_400
        assert max(hour_starts) >= 86_400
    finally:
        connection.close()
