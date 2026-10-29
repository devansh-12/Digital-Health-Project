"""Define activity segments and hourly tracking bucket types."""

from dataclasses import dataclass

from screensense.core.context import ContextState


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
