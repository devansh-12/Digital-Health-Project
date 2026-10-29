"""Aggregate sampled context durations into hourly usage buckets."""

from collections.abc import Iterable
from dataclasses import dataclass, replace
from math import floor, isfinite

from screensense.core.clock import Clock
from screensense.core.context import ContextState

_SECONDS_PER_HOUR = 3_600
_CONTEXT_COUNTERS = {
    ContextState.FREE: "active_s",
    ContextState.IDLE: "idle_s",
    ContextState.FULLSCREEN: "fullscreen_s",
    ContextState.CALL: "call_s",
}


@dataclass(slots=True)
class UsageBucket:
    """Accumulate context seconds for one Unix-hour bucket."""

    hour_start: int
    active_s: int = 0
    idle_s: int = 0
    fullscreen_s: int = 0
    call_s: int = 0


@dataclass(frozen=True, slots=True)
class ActivitySegment:
    """Describe a context interval and whether a completed break resets it."""

    context: ContextState
    duration_s: float
    break_completed: bool = False


class Tracker:
    """Accumulate sampled context durations into local hourly buckets."""

    def __init__(self, clock: Clock) -> None:
        """Initialize an empty tracker with an injected clock."""
        self._clock = clock
        self._buckets: dict[int, UsageBucket] = {}
        self._last_monotonic: float | None = None
        self._paused = False

    @property
    def buckets(self) -> dict[int, UsageBucket]:
        """Return a copy of hourly buckets keyed by Unix-hour start."""
        return {hour: replace(bucket) for hour, bucket in self._buckets.items()}

    def sample(self, context: ContextState) -> None:
        """Record the elapsed interval since the previous context sample."""
        now_monotonic = self._clock.monotonic()
        now_wall = self._clock.wall_time()
        if self._paused:
            self._last_monotonic = now_monotonic
            return
        if self._last_monotonic is None:
            self._last_monotonic = now_monotonic
            return

        elapsed = max(0.0, now_monotonic - self._last_monotonic)
        self._last_monotonic = now_monotonic
        counter = _CONTEXT_COUNTERS.get(context)
        if elapsed <= 0 or counter is None:
            return
        self._add_interval(now_wall - elapsed, elapsed, counter)

    def pause(self) -> None:
        """Stop counting while the system is asleep or otherwise paused."""
        self._paused = True
        self._last_monotonic = None

    def resume(self) -> None:
        """Restart sampling from a fresh monotonic baseline."""
        self._paused = False
        self._last_monotonic = self._clock.monotonic()

    def _add_interval(self, start_wall: float, duration_s: float, counter: str) -> None:
        """Split one elapsed interval at hour boundaries and update counters."""
        remaining = round(duration_s)
        cursor = start_wall
        while remaining > 0:
            hour_start = floor(cursor / _SECONDS_PER_HOUR) * _SECONDS_PER_HOUR
            seconds_to_boundary = _SECONDS_PER_HOUR - (cursor - hour_start)
            portion = min(remaining, round(seconds_to_boundary))
            if portion <= 0:
                portion = min(remaining, 1)
            bucket = self._buckets.setdefault(hour_start, UsageBucket(hour_start))
            setattr(bucket, counter, getattr(bucket, counter) + portion)
            cursor += portion
            remaining -= portion


def longest_unbroken_active_stretch(
    segments: Iterable[ActivitySegment],
) -> float:
    """Return the longest active run, resetting on idle gaps and completed breaks."""
    longest = 0.0
    current = 0.0
    active_contexts = {ContextState.FREE, ContextState.CALL, ContextState.FULLSCREEN}
    for segment in segments:
        if not isfinite(segment.duration_s) or segment.duration_s < 0:
            raise ValueError("segment duration must be finite and non-negative")
        if segment.break_completed:
            current = 0.0
            continue
        if segment.context not in active_contexts:
            current = 0.0
            continue
        current += segment.duration_s
        longest = max(longest, current)
    return longest
