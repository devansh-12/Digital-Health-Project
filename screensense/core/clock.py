"""Define injectable wall and monotonic clocks for core logic."""

from math import isfinite
from typing import Protocol


class Clock(Protocol):
    """Provide wall-clock and monotonic time readings."""

    def monotonic(self) -> float:
        """Return monotonic seconds for measuring elapsed time."""
        ...

    def wall_time(self) -> float:
        """Return wall-clock seconds since the Unix epoch."""
        ...


class FakeClock:
    """A deterministic clock that advances without sleeping."""

    def __init__(
        self, monotonic_seconds: float = 0.0, wall_seconds: float = 0.0
    ) -> None:
        """Initialize monotonic and wall time values in seconds."""
        if not isfinite(monotonic_seconds) or monotonic_seconds < 0:
            raise ValueError("monotonic_seconds must be finite and non-negative")
        if not isfinite(wall_seconds):
            raise ValueError("wall_seconds must be finite")
        self._monotonic_seconds = monotonic_seconds
        self._wall_seconds = wall_seconds

    def monotonic(self) -> float:
        """Return the current fake monotonic time in seconds."""
        return self._monotonic_seconds

    def wall_time(self) -> float:
        """Return the current fake wall time in seconds since the epoch."""
        return self._wall_seconds

    def advance(self, seconds: float) -> None:
        """Advance both clock readings by a finite, non-negative duration."""
        if not isfinite(seconds) or seconds < 0:
            raise ValueError("seconds must be finite and non-negative")
        self._monotonic_seconds += seconds
        self._wall_seconds += seconds
