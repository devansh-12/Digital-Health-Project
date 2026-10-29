"""Manage break scheduling using injected time, context, and event dependencies."""

from enum import StrEnum
from typing import Protocol

from screensense.core.clock import Clock
from screensense.core.config import Settings
from screensense.core.context import ContextState
from screensense.core.events import (
    BreakCompleted,
    BreakKind,
    BreakSkipped,
    EventBus,
    ShowPrompt,
)


class State(StrEnum):
    """Named states in the scheduler state machine."""

    WORKING = "working"
    PROMPTING = "prompting"
    SNOOZED = "snoozed"
    ON_BREAK = "on_break"
    SUPPRESS = "suppress"


class BreakRecorder(Protocol):
    """Persist suppressed prompts and naturally completed breaks."""

    def record_suppressed(self, due_at: int, kind: BreakKind) -> None:
        """Record one queued prompt as suppressed."""

    def record_natural(self, due_at: int, duration_s: int) -> None:
        """Record an idle period counted as a natural break."""


_WORK_CONTEXTS = frozenset(
    {ContextState.FREE, ContextState.FULLSCREEN, ContextState.CALL}
)


class Scheduler:
    """Track work time and publish break prompt and outcome events."""

    def __init__(
        self,
        settings: Settings,
        clock: Clock,
        event_bus: EventBus,
        breaks_repository: BreakRecorder | None = None,
    ) -> None:
        """Initialize the scheduler in the working state."""
        self._settings = settings
        self._clock = clock
        self._event_bus = event_bus
        self._breaks_repository = breaks_repository
        self._state = State.WORKING
        self._last_tick = clock.monotonic()
        self._last_context = ContextState.FREE
        self._work_elapsed = 0.0
        self._completed_breaks = 0
        self._prompt_queued = False
        self._queued_for_suppression = False
        self._suppressed_recorded = False
        self._snooze_until: float | None = None
        self._prompt_kind: BreakKind | None = None
        self._active_break_kind: BreakKind | None = None
        self._idle_since: float | None = None
        self._idle_break_counted = False

    @property
    def state(self) -> State:
        """Return the current scheduler state."""
        return self._state

    def tick(self, context: ContextState) -> None:
        """Advance timers and evaluate context; call every 1-2 seconds and on changes."""
        now = self._clock.monotonic()
        elapsed = max(0.0, now - self._last_tick)
        if (
            self._state in (State.WORKING, State.SUPPRESS)
            and not self._prompt_queued
            and self._last_context in _WORK_CONTEXTS
        ):
            self._work_elapsed += elapsed
        self._last_tick = now

        self._update_idle_break(context, now)
        if self._idle_break_counted and context is ContextState.IDLE:
            self._last_context = context
            return

        if self._state is State.ON_BREAK:
            self._last_context = context
            return

        if self._state is State.PROMPTING:
            if context is not ContextState.FREE:
                self._queue_suppressed_prompt()
                self._state = State.SUPPRESS
            self._last_context = context
            return

        if self._state is State.SNOOZED:
            if self._snooze_until is not None and now >= self._snooze_until:
                self._prompt_queued = True
                self._snooze_until = None
            else:
                self._last_context = context
                return

        if self._prompt_queued:
            if context is ContextState.FREE:
                self._show_prompt()
            else:
                self._queue_suppressed_prompt()
                self._state = State.SUPPRESS
            self._last_context = context
            return

        if self._work_elapsed >= self._interval_seconds():
            if context is ContextState.FREE:
                self._show_prompt()
            else:
                self._queue_suppressed_prompt()
                self._state = State.SUPPRESS
        elif context is not ContextState.FREE:
            self._state = State.SUPPRESS
        else:
            self._state = State.WORKING

        self._last_context = context

    def snooze(self) -> None:
        """Snooze the visible prompt for the configured duration."""
        self._require_state(State.PROMPTING)
        now = self._clock.monotonic()
        self._snooze_until = now + self._settings.snooze_minutes * 60
        self._last_tick = now
        self._prompt_queued = False
        self._queued_for_suppression = False
        self._suppressed_recorded = False
        self._state = State.SNOOZED

    def skip(self) -> None:
        """Skip the visible prompt and begin a fresh work interval."""
        self._require_state(State.PROMPTING)
        kind = self._current_prompt_kind()
        self._event_bus.publish(BreakSkipped(kind=kind))
        self._begin_work_interval()

    def start_break(self, kind: BreakKind | None = None) -> None:
        """Start the break selected by the current prompt."""
        self._require_state(State.PROMPTING)
        selected_kind = kind or self._current_prompt_kind()
        if selected_kind not in ("quick", "long", "yoga"):
            raise ValueError("A user-started break must be quick, long, or yoga")
        self._active_break_kind = selected_kind
        self._state = State.ON_BREAK
        self._last_tick = self._clock.monotonic()

    def complete_break(self, duration_s: int) -> None:
        """Record completion and begin a fresh work interval."""
        self._require_state(State.ON_BREAK)
        if (
            isinstance(duration_s, bool)
            or not isinstance(duration_s, int)
            or duration_s < 0
        ):
            raise ValueError("duration_s must be a non-negative integer")
        if self._active_break_kind is None:
            raise RuntimeError("No break is active")
        kind = self._active_break_kind
        self._event_bus.publish(BreakCompleted(kind=kind, duration_s=duration_s))
        self._completed_breaks += 1
        self._begin_work_interval()

    def update_settings(self, settings: Settings) -> None:
        """Replace settings while preserving elapsed work time."""
        self._settings = settings

    def _update_idle_break(self, context: ContextState, now: float) -> None:
        if self._state is State.ON_BREAK:
            self._idle_since = None
            self._idle_break_counted = context is ContextState.IDLE
            return
        if context is not ContextState.IDLE:
            self._idle_since = None
            self._idle_break_counted = False
            return
        if self._idle_since is None:
            self._idle_since = now
        remaining_idle_seconds = max(
            0,
            self._settings.quick_break_seconds
            - self._settings.idle_threshold_seconds,
        )
        if not self._idle_break_counted and now - self._idle_since >= remaining_idle_seconds:
            self._idle_break_counted = True
            self._completed_breaks += 1
            if self._breaks_repository is not None:
                self._breaks_repository.record_natural(
                    due_at=int(self._clock.wall_time()),
                    duration_s=self._settings.quick_break_seconds,
                )
            self._event_bus.publish(
                BreakCompleted(
                    kind="natural",
                    duration_s=self._settings.quick_break_seconds,
                )
            )
            self._begin_work_interval()
            self._state = State.SUPPRESS

    def _show_prompt(self) -> None:
        kind = self._next_break_kind()
        message = (
            "Meeting's over. Want a quick eye break?"
            if self._queued_for_suppression
            else None
        )
        self._prompt_kind = kind
        self._prompt_queued = False
        self._queued_for_suppression = False
        self._suppressed_recorded = False
        self._snooze_until = None
        self._state = State.PROMPTING
        self._event_bus.publish(ShowPrompt(kind=kind, message=message))

    def _queue_suppressed_prompt(self) -> None:
        """Queue one due reminder and persist its suppression once."""
        self._prompt_queued = True
        self._queued_for_suppression = True
        if self._suppressed_recorded:
            return
        if self._breaks_repository is not None:
            self._breaks_repository.record_suppressed(
                due_at=int(self._clock.wall_time()), kind=self._next_break_kind()
            )
        self._suppressed_recorded = True

    def _next_break_kind(self) -> BreakKind:
        next_break_number = self._completed_breaks + 1
        if next_break_number % self._settings.long_break_every == 0:
            return "long"
        return "quick"

    def _current_prompt_kind(self) -> BreakKind:
        if self._prompt_kind is None:
            raise RuntimeError("No prompt is active")
        return self._prompt_kind

    def _interval_seconds(self) -> int:
        return self._settings.work_interval_minutes * 60

    def _begin_work_interval(self) -> None:
        self._state = State.WORKING
        self._work_elapsed = 0.0
        self._prompt_queued = False
        self._queued_for_suppression = False
        self._suppressed_recorded = False
        self._snooze_until = None
        self._prompt_kind = None
        self._active_break_kind = None
        self._last_tick = self._clock.monotonic()

    def _require_state(self, expected: State) -> None:
        if self._state is not expected:
            raise RuntimeError(f"Expected scheduler state {expected.value}")
