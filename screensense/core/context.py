"""Define typed context inputs and states for reminder suppression."""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from screensense.core.clock import Clock
from screensense.core.config import WorkHours
from screensense.core.events import ContextChanged, EventBus
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


class ContextRulesSource(Protocol):
    """Load process context rules from a repository."""

    def load_all(self) -> Mapping[str, ContextRule]:
        """Return the latest process-to-rule mapping."""


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


class ContextEvaluator:
    """Debounce context changes and publish confirmed transitions."""

    def __init__(
        self,
        clock: Clock,
        rules_source: ContextRulesSource,
        event_bus: EventBus,
        debounce_seconds: float = 2.0,
    ) -> None:
        """Initialize context evaluation with injectable time and rule storage."""
        if debounce_seconds < 0:
            raise ValueError("debounce_seconds must be non-negative")
        self._clock = clock
        self._rules_source = rules_source
        self._event_bus = event_bus
        self._debounce_seconds = debounce_seconds
        self._current: ContextState | None = None
        self._pending: ContextState | None = None
        self._pending_since: float | None = None
        self._last_rules: dict[str, ContextRule] | None = None

    @property
    def current(self) -> ContextState | None:
        """Return the last confirmed state, if evaluation has started."""
        return self._current

    def evaluate(self, inputs: ContextInputs) -> ContextState:
        """Evaluate current inputs and return the last debounced state."""
        latest_rules = dict(self._rules_source.load_all())
        candidate = evaluate(replace(inputs, rules=latest_rules))
        now = self._clock.monotonic()
        rules_changed = self._last_rules is not None and latest_rules != self._last_rules
        self._last_rules = latest_rules

        if self._current is None:
            self._set_current(candidate)
            return candidate

        if rules_changed:
            self._pending = None
            self._pending_since = None
            if candidate != self._current:
                self._set_current(candidate)
            return self._current

        if candidate == self._current:
            self._pending = None
            self._pending_since = None
            return self._current

        if candidate != self._pending:
            self._pending = candidate
            self._pending_since = now
            return self._current

        if (
            self._pending_since is not None
            and now - self._pending_since >= self._debounce_seconds
        ):
            self._set_current(candidate)
        return self._current

    def _set_current(self, state: ContextState) -> None:
        """Store a changed state and publish one transition event."""
        previous = self._current
        if previous is not None and previous == state:
            return
        self._current = state
        self._pending = None
        self._pending_since = None
        self._event_bus.publish(ContextChanged(previous=previous, current=state))
