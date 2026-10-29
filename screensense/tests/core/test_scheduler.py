"""Behavior specifications for the not-yet-implemented scheduler."""

from typing import Any

import pytest

from screensense.core import scheduler as scheduler_module
from screensense.core.clock import FakeClock
from screensense.core.config import Settings
from screensense.core.context import ContextState
from screensense.core.events import (
    BreakCompleted,
    BreakSkipped,
    EventBus,
    ShowPrompt,
)
from screensense.core.scheduler import State


def make_scheduler(
    settings: Settings,
) -> tuple[
    Any,
    FakeClock,
    EventBus,
    list[ShowPrompt],
    list[BreakCompleted],
    list[BreakSkipped],
]:
    """Build the expected scheduler interface with a fake clock and event bus."""
    scheduler_type = getattr(scheduler_module, "Scheduler", None)
    assert scheduler_type is not None, "Scheduler behavior has not been implemented"

    clock = FakeClock()
    event_bus = EventBus()
    prompts: list[ShowPrompt] = []
    completed: list[BreakCompleted] = []
    skipped: list[BreakSkipped] = []
    event_bus.subscribe(ShowPrompt, prompts.append)
    event_bus.subscribe(BreakCompleted, completed.append)
    event_bus.subscribe(BreakSkipped, skipped.append)
    scheduler = scheduler_type(settings=settings, clock=clock, event_bus=event_bus)
    return scheduler, clock, event_bus, prompts, completed, skipped


@pytest.mark.parametrize("interval_minutes", [10, 20, 60])
def test_normal_cycle_prompts_then_returns_to_working(interval_minutes: int) -> None:
    """Prompt at the interval, then return to working after completion."""
    settings = Settings(work_interval_minutes=interval_minutes)
    scheduler, clock, _, prompts, completed, _ = make_scheduler(settings)

    clock.advance(interval_minutes * 60 - 1)
    scheduler.tick(ContextState.FREE)
    assert scheduler.state is State.WORKING
    assert prompts == []

    clock.advance(1)
    scheduler.tick(ContextState.FREE)
    assert scheduler.state is State.PROMPTING
    assert prompts == [ShowPrompt(kind="quick")]

    scheduler.start_break()
    assert scheduler.state is State.ON_BREAK
    scheduler.complete_break(duration_s=settings.quick_break_seconds)
    assert scheduler.state is State.WORKING
    assert completed == [
        BreakCompleted(kind="quick", duration_s=settings.quick_break_seconds)
    ]


@pytest.mark.parametrize(
    ("snoozed_seconds", "expected_state"),
    [(299, State.SNOOZED), (300, State.PROMPTING)],
)
def test_snooze_reprompts_after_five_minutes(
    snoozed_seconds: int, expected_state: State
) -> None:
    """Keep a prompt snoozed until the configured five-minute delay elapses."""
    scheduler, clock, _, prompts, _, _ = make_scheduler(Settings())
    clock.advance(20 * 60)
    scheduler.tick(ContextState.FREE)
    scheduler.snooze()

    clock.advance(snoozed_seconds)
    scheduler.tick(ContextState.FREE)

    assert scheduler.state is expected_state
    assert len(prompts) == (2 if snoozed_seconds == 300 else 1)


def test_skip_returns_to_working_and_publishes_skip_event() -> None:
    """Skip a prompt without starting a break and publish the skip event."""
    scheduler, clock, _, prompts, _, skipped = make_scheduler(Settings())
    clock.advance(20 * 60)
    scheduler.tick(ContextState.FREE)

    scheduler.skip()

    assert scheduler.state is State.WORKING
    assert prompts == [ShowPrompt(kind="quick")]
    assert skipped == [BreakSkipped(kind="quick")]


@pytest.mark.parametrize(
    ("completed_breaks", "expected_kind"),
    [(1, "quick"), (2, "quick"), (3, "long"), (4, "quick"), (6, "long")],
)
def test_every_third_break_is_long(
    completed_breaks: int, expected_kind: str
) -> None:
    """Select a long prompt on every third completed break."""
    scheduler, clock, _, prompts, _, _ = make_scheduler(Settings())

    for _ in range(completed_breaks):
        clock.advance(20 * 60)
        scheduler.tick(ContextState.FREE)
        scheduler.start_break()
        scheduler.complete_break(duration_s=20)

    assert prompts[-1].kind == expected_kind


def test_interval_change_mid_cycle_keeps_elapsed_work_time() -> None:
    """Apply a longer interval mid-cycle without discarding elapsed work."""
    scheduler, clock, _, prompts, _, _ = make_scheduler(
        Settings(work_interval_minutes=20)
    )
    clock.advance(10 * 60)
    scheduler.tick(ContextState.FREE)
    scheduler.update_settings(Settings(work_interval_minutes=30))

    clock.advance(19 * 60)
    scheduler.tick(ContextState.FREE)
    assert scheduler.state is State.WORKING

    clock.advance(60)
    scheduler.tick(ContextState.FREE)
    assert scheduler.state is State.PROMPTING
    assert prompts == [ShowPrompt(kind="quick")]


def test_resume_after_three_hours_asleep_does_not_count_sleep_as_work() -> None:
    """Pause the work interval while locked/asleep and resume from prior progress."""
    scheduler, clock, _, prompts, _, _ = make_scheduler(
        Settings(work_interval_minutes=20)
    )
    clock.advance(19 * 60)
    scheduler.tick(ContextState.FREE)
    scheduler.tick(ContextState.LOCKED)

    clock.advance(3 * 60 * 60)
    scheduler.tick(ContextState.FREE)
    assert scheduler.state is State.WORKING
    assert prompts == []

    clock.advance(59)
    scheduler.tick(ContextState.FREE)
    assert scheduler.state is State.WORKING

    clock.advance(1)
    scheduler.tick(ContextState.FREE)
    assert scheduler.state is State.PROMPTING
    assert prompts == [ShowPrompt(kind="quick")]


@pytest.mark.parametrize("context", [ContextState.CALL, ContextState.FULLSCREEN])
def test_due_prompt_waits_for_free_context_and_is_queued_once(
    context: ContextState,
) -> None:
    """Count work in calls/fullscreen but show one queued prompt only in FREE."""
    scheduler, clock, _, prompts, _, _ = make_scheduler(
        Settings(work_interval_minutes=10)
    )
    clock.advance(5 * 60)
    scheduler.tick(context)
    assert scheduler.state is State.SUPPRESS
    assert prompts == []

    clock.advance(5 * 60)
    scheduler.tick(context)

    assert scheduler.state is State.SUPPRESS
    assert prompts == []

    clock.advance(60)
    scheduler.tick(context)
    scheduler.tick(ContextState.FREE)
    scheduler.tick(ContextState.FREE)

    assert scheduler.state is State.PROMPTING
    assert prompts == [ShowPrompt(kind="quick")]


@pytest.mark.parametrize(
    ("idle_threshold_seconds", "additional_idle_seconds"),
    [(120, 0), (10, 10)],
)
def test_idle_longer_than_break_length_counts_as_natural_break(
    idle_threshold_seconds: int, additional_idle_seconds: int
) -> None:
    """Count idle threshold time plus any remaining break time as a natural break."""
    scheduler, clock, _, prompts, completed, _ = make_scheduler(
        Settings(
            work_interval_minutes=10,
            idle_threshold_seconds=idle_threshold_seconds,
        )
    )
    clock.advance(9 * 60)
    scheduler.tick(ContextState.FREE)
    scheduler.tick(ContextState.IDLE)

    if additional_idle_seconds:
        assert completed == []
        clock.advance(additional_idle_seconds)
        scheduler.tick(ContextState.IDLE)

    assert scheduler.state is State.SUPPRESS
    assert completed == [BreakCompleted(kind="natural", duration_s=20)]

    scheduler.tick(ContextState.FREE)
    clock.advance(9 * 60)
    scheduler.tick(ContextState.FREE)

    assert prompts == []


def test_active_break_does_not_count_time_as_work() -> None:
    """Keep the scheduler in ON_BREAK until completion without accruing work."""
    scheduler, clock, _, prompts, _, _ = make_scheduler(
        Settings(work_interval_minutes=10)
    )
    clock.advance(10 * 60)
    scheduler.tick(ContextState.FREE)
    scheduler.start_break(kind="yoga")

    clock.advance(60)
    scheduler.tick(ContextState.FREE)
    assert scheduler.state is State.ON_BREAK

    scheduler.complete_break(duration_s=60)
    clock.advance(10 * 60 - 1)
    scheduler.tick(ContextState.FREE)
    assert scheduler.state is State.WORKING
    clock.advance(1)
    scheduler.tick(ContextState.FREE)
    assert scheduler.state is State.PROMPTING
    assert prompts[-1].kind == "quick"


@pytest.mark.parametrize("context", [ContextState.CALL, ContextState.FULLSCREEN])
def test_queued_prompt_is_delivered_with_recovery_copy_within_ten_seconds(
    context: ContextState,
) -> None:
    """Queue in a call/fullscreen context and deliver promptly after it clears."""
    scheduler, clock, _, prompts, _, _ = make_scheduler(
        Settings(work_interval_minutes=10)
    )
    clock.advance(10 * 60)
    scheduler.tick(context)
    assert scheduler.state is State.SUPPRESS
    assert prompts == []

    clock.advance(9)
    scheduler.tick(ContextState.FREE)

    assert scheduler.state is State.PROMPTING
    assert len(prompts) == 1
    assert getattr(prompts[0], "message", None) == (
        "Meeting's over. Want a quick eye break?"
    )


def test_multiple_due_intervals_while_suppressed_keep_one_queued_prompt() -> None:
    """Collapse many suppressed due intervals into one queued reminder."""
    scheduler, clock, _, prompts, _, _ = make_scheduler(
        Settings(work_interval_minutes=10)
    )
    scheduler.tick(ContextState.CALL)
    clock.advance(40 * 60)
    scheduler.tick(ContextState.CALL)
    assert prompts == []

    scheduler.tick(ContextState.FREE)

    assert scheduler.state is State.PROMPTING
    assert len(prompts) == 1


@pytest.mark.parametrize("context", [ContextState.CALL, ContextState.FULLSCREEN])
def test_work_timer_advances_but_prompt_waits_in_working_contexts(
    context: ContextState,
) -> None:
    """Count call/fullscreen time as work while withholding the due prompt."""
    scheduler, clock, _, prompts, _, _ = make_scheduler(
        Settings(work_interval_minutes=10)
    )
    scheduler.tick(context)
    clock.advance(10 * 60)
    scheduler.tick(context)

    assert scheduler.state is State.SUPPRESS
    assert prompts == []


@pytest.mark.parametrize("context", [ContextState.IDLE, ContextState.LOCKED])
def test_idle_and_locked_time_do_not_advance_work_timer(
    context: ContextState,
) -> None:
    """Pause accrued work while idle or locked, then resume remaining time."""
    settings = Settings(work_interval_minutes=10)
    if context is ContextState.IDLE:
        settings = Settings(
            work_interval_minutes=10,
            quick_break_seconds=60,
            idle_threshold_seconds=30,
        )
    scheduler, clock, _, prompts, _, _ = make_scheduler(settings)
    clock.advance(5 * 60)
    scheduler.tick(ContextState.FREE)
    scheduler.tick(context)
    clock.advance(2)
    scheduler.tick(context)
    scheduler.tick(ContextState.FREE)

    clock.advance(5 * 60 - 1)
    scheduler.tick(ContextState.FREE)
    assert prompts == []
    clock.advance(1)
    scheduler.tick(ContextState.FREE)

    assert len(prompts) == 1


def test_idle_at_least_break_length_counts_natural_break_and_resets_timer() -> None:
    """Count a sufficiently long idle period as a break and reset work progress."""
    scheduler, clock, _, prompts, completed, _ = make_scheduler(
        Settings(work_interval_minutes=10, idle_threshold_seconds=1)
    )
    clock.advance(9 * 60)
    scheduler.tick(ContextState.FREE)
    scheduler.tick(ContextState.IDLE)
    clock.advance(19)
    scheduler.tick(ContextState.IDLE)

    assert completed == [BreakCompleted(kind="natural", duration_s=20)]
    scheduler.tick(ContextState.FREE)
    clock.advance(9 * 60)
    scheduler.tick(ContextState.FREE)
    assert prompts == []
    clock.advance(60)
    scheduler.tick(ContextState.FREE)

    assert len(prompts) == 1
