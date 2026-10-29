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


_CALL_PROCESSES = frozenset({"zoom.exe", "teams.exe", "webex.exe", "slack.exe"})
_CALL_TITLE_PATTERNS = ("meet -", "zoom meeting", "slack huddle")


def evaluate(inputs: ContextInputs) -> ContextState:
    """Return the highest-priority context state for one input snapshot."""
    if inputs.locked or inputs.asleep:
        return ContextState.LOCKED

    work_hours = inputs.work_hours
    if work_hours is not None and (
        inputs.now.weekday() not in work_hours.weekdays
        or not work_hours.start <= inputs.now.time() < work_hours.end
    ):
        return ContextState.OUTSIDE_HOURS

    if inputs.idle_seconds >= inputs.idle_threshold:
        return ContextState.IDLE

    window = inputs.window
    if window is None:
        return ContextState.FREE

    process = _normalize_process(window.process)
    rule = next(
        (
            configured_rule
            for process_name, configured_rule in inputs.rules.items()
            if _normalize_process(process_name) == process
        ),
        None,
    )

    # ContextState has no DENIED value; OUTSIDE_HOURS is the existing blocked state.
    if rule is ContextRule.DENY:
        return ContextState.OUTSIDE_HOURS
    if rule is ContextRule.ALLOW:
        return ContextState.FREE
    if rule is ContextRule.CALL:
        return ContextState.CALL

    title = window.title.casefold()
    if process in _CALL_PROCESSES or any(
        pattern in title for pattern in _CALL_TITLE_PATTERNS
    ):
        return ContextState.CALL
    if window.is_fullscreen and rule is not ContextRule.FULLSCREEN_OK:
        return ContextState.FULLSCREEN
    return ContextState.FREE


def _normalize_process(process: str) -> str:
    """Normalize a process name for case-insensitive user-rule matching."""
    return process.strip().casefold()
