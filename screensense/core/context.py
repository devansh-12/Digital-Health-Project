"""Define typed context inputs and states for reminder suppression."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime, time
from enum import StrEnum

from screensense.platform_adapters.base import WindowInfo


class ContextState(StrEnum):
    """Current user context used to decide whether a prompt may appear."""

    FREE = "free"
    IDLE = "idle"
    FULLSCREEN = "fullscreen"
    CALL = "call"
    OUTSIDE_HOURS = "outside_hours"
    LOCKED = "locked"


class ContextRule(StrEnum):
    """Per-process reminder and context overrides."""

    ALLOW = "allow"
    DENY = "deny"
    CALL = "call"
    FULLSCREEN_OK = "fullscreen_ok"


@dataclass(frozen=True, slots=True)
class WorkHours:
    """Local weekday schedule; end time is exclusive."""

    start: time
    end: time
    weekdays: frozenset[int] = frozenset(range(5))

    def __post_init__(self) -> None:
        """Validate weekday indices and a same-day non-empty time range."""
        if any(day < 0 or day > 6 for day in self.weekdays):
            raise ValueError("weekdays must use datetime weekday values from 0 to 6")
        if self.start >= self.end:
            raise ValueError("work hours must start before they end on the same day")


@dataclass(frozen=True, slots=True)
class ContextInputs:
    """Capture one context evaluation's inputs without persisting window titles."""

    locked: bool
    asleep: bool
    now: datetime
    work_hours: WorkHours | None
    idle_seconds: float
    idle_threshold: float
    window: WindowInfo | None
    rules: Mapping[str, ContextRule] = field(default_factory=dict)
