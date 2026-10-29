"""Decision-table tests for context evaluation (red until evaluate is added)."""

from dataclasses import replace
from datetime import datetime, time

import pytest

from screensense.core import context
from screensense.core.clock import FakeClock
from screensense.core.context import (
    ContextEvaluator,
    ContextInputs,
    ContextRule,
    ContextState,
    WorkHours,
)
from screensense.core.events import ContextChanged, EventBus
from screensense.platform_adapters.base import WindowInfo

WEEKDAYS = WorkHours(start=time(9), end=time(18))
MONDAY_WORKDAY = datetime(2026, 10, 26, 12, 0)


def make_inputs(**changes: object) -> ContextInputs:
    """Build a typical active-work context with optional field overrides."""
    inputs = ContextInputs(
        locked=False,
        asleep=False,
        now=MONDAY_WORKDAY,
        work_hours=WEEKDAYS,
        idle_seconds=0.0,
        idle_threshold=120.0,
        window=WindowInfo("Editor", "editor.exe", (0, 0, 800, 600), False),
    )
    return replace(inputs, **changes)


def evaluate_for_red(inputs: ContextInputs) -> ContextState:
    """Fail explicitly until the evaluator is implemented in the green chunk."""
    evaluator = getattr(context, "evaluate", None)
    assert callable(evaluator), "core.context.evaluate is not implemented yet"
    return evaluator(inputs)


@pytest.mark.parametrize(
    ("inputs", "expected"),
    [
        pytest.param(make_inputs(locked=True), ContextState.LOCKED, id="locked"),
        pytest.param(make_inputs(asleep=True), ContextState.LOCKED, id="asleep"),
        pytest.param(
            make_inputs(locked=True, asleep=True, idle_seconds=300),
            ContextState.LOCKED,
            id="locked-priority-over-idle",
        ),
        pytest.param(
            make_inputs(now=datetime(2026, 10, 26, 8, 59)),
            ContextState.OUTSIDE_HOURS,
            id="before-work-hours",
        ),
        pytest.param(
            make_inputs(now=datetime(2026, 10, 26, 9, 0)),
            ContextState.FREE,
            id="work-hours-start-inclusive",
        ),
        pytest.param(
            make_inputs(now=datetime(2026, 10, 26, 17, 59)),
            ContextState.FREE,
            id="work-hours-before-end",
        ),
        pytest.param(
            make_inputs(now=datetime(2026, 10, 26, 18, 0)),
            ContextState.OUTSIDE_HOURS,
            id="work-hours-end-exclusive",
        ),
        pytest.param(
            make_inputs(now=datetime(2026, 10, 25, 12, 0)),
            ContextState.OUTSIDE_HOURS,
            id="weekend-outside-hours",
        ),
        pytest.param(
            make_inputs(work_hours=None, now=datetime(2026, 10, 25, 12, 0)),
            ContextState.FREE,
            id="no-work-hours-configured",
        ),
        pytest.param(
            make_inputs(idle_seconds=120.0),
            ContextState.IDLE,
            id="idle-threshold-inclusive",
        ),
        pytest.param(
            make_inputs(idle_seconds=119.999),
            ContextState.FREE,
            id="below-idle-threshold",
        ),
        pytest.param(
            make_inputs(idle_seconds=120, window=WindowInfo("Zoom", "zoom.exe", (0, 0, 1920, 1080), True)),
            ContextState.IDLE,
            id="idle-priority-over-call-and-fullscreen",
        ),
        pytest.param(
            make_inputs(window=WindowInfo("Zoom", "zoom.exe", (0, 0, 800, 600), False)),
            ContextState.CALL,
            id="zoom-process-is-call",
        ),
        pytest.param(
            make_inputs(window=WindowInfo("Teams", "teams.exe", (0, 0, 800, 600), False)),
            ContextState.CALL,
            id="teams-process-is-call",
        ),
        pytest.param(
            make_inputs(window=WindowInfo("Webex", "webex.exe", (0, 0, 800, 600), False)),
            ContextState.CALL,
            id="webex-process-is-call",
        ),
        pytest.param(
            make_inputs(window=WindowInfo("Meet - Standup", "browser.exe", (0, 0, 800, 600), False)),
            ContextState.CALL,
            id="meet-title-pattern-is-call",
        ),
        pytest.param(
            make_inputs(window=WindowInfo("Zoom Meeting", "browser.exe", (0, 0, 800, 600), False)),
            ContextState.CALL,
            id="zoom-meeting-title-pattern-is-call",
        ),
        pytest.param(
            make_inputs(window=WindowInfo("meet - standup", "browser.exe", (0, 0, 800, 600), False)),
            ContextState.CALL,
            id="call-title-pattern-is-case-insensitive",
        ),
        pytest.param(
            make_inputs(window=WindowInfo("Game", "game.exe", (0, 0, 1920, 1080), True)),
            ContextState.FULLSCREEN,
            id="fullscreen-is-suppressed",
        ),
        pytest.param(
            make_inputs(window=WindowInfo("Meet - Game", "game.exe", (0, 0, 1920, 1080), True)),
            ContextState.CALL,
            id="call-priority-over-fullscreen",
        ),
        pytest.param(
            make_inputs(
                window=WindowInfo("Game", "game.exe", (0, 0, 1920, 1080), True),
                rules={"game.exe": ContextRule.ALLOW},
            ),
            ContextState.FREE,
            id="allow-rule-bypasses-fullscreen",
        ),
        pytest.param(
            make_inputs(
                window=WindowInfo("Game", "game.exe", (0, 0, 1920, 1080), True),
                rules={"game.exe": ContextRule.FULLSCREEN_OK},
            ),
            ContextState.FREE,
            id="fullscreen-ok-rule-bypasses-fullscreen",
        ),
        pytest.param(
            make_inputs(
                window=WindowInfo("Editor", "editor.exe", (0, 0, 800, 600), False),
                rules={"editor.exe": ContextRule.CALL},
            ),
            ContextState.CALL,
            id="call-rule-forces-call-context",
        ),
        pytest.param(
            make_inputs(
                window=WindowInfo("Editor", "editor.exe", (0, 0, 800, 600), False),
                rules={"editor.exe": ContextRule.DENY},
            ),
            ContextState.OUTSIDE_HOURS,
            id="deny-rule-suppresses-prompts",
        ),
        pytest.param(
            make_inputs(
                now=datetime(2026, 10, 26, 8, 0),
                idle_seconds=300,
                window=WindowInfo("Zoom", "zoom.exe", (0, 0, 1920, 1080), True),
            ),
            ContextState.OUTSIDE_HOURS,
            id="outside-hours-priority-over-idle-and-call",
        ),
        pytest.param(
            make_inputs(
                now=datetime(2026, 10, 26, 8, 0),
                rules={"zoom.exe": ContextRule.ALLOW},
                window=WindowInfo("Zoom", "zoom.exe", (0, 0, 1920, 1080), True),
            ),
            ContextState.OUTSIDE_HOURS,
            id="outside-hours-cannot-be-overridden",
        ),
        pytest.param(
            make_inputs(
                locked=True,
                rules={"zoom.exe": ContextRule.ALLOW},
                window=WindowInfo("Zoom", "zoom.exe", (0, 0, 1920, 1080), True),
            ),
            ContextState.LOCKED,
            id="lock-cannot-be-overridden",
        ),
        pytest.param(make_inputs(window=None), ContextState.FREE, id="no-window"),
    ],
)
def test_context_decision_table(
    inputs: ContextInputs, expected: ContextState
) -> None:
    """Resolve state according to priority, boundaries, and process rules."""
    assert evaluate_for_red(inputs) is expected


def test_work_hours_reject_invalid_days_and_empty_ranges() -> None:
    """Reject invalid weekday indices and overnight/empty ranges explicitly."""
    with pytest.raises(ValueError, match="weekday"):
        WorkHours(start=time(9), end=time(18), weekdays=frozenset({7}))
    with pytest.raises(ValueError, match="start before"):
        WorkHours(start=time(18), end=time(9))


def test_process_rules_match_case_insensitively() -> None:
    """Match persisted process names without depending on Windows casing."""
    inputs = make_inputs(
        window=WindowInfo("Game", "GAME.EXE", (0, 0, 1920, 1080), True),
        rules={"game.exe": ContextRule.FULLSCREEN_OK},
    )

    assert context.evaluate(inputs) is ContextState.FREE


def test_allow_rule_can_override_call_detection() -> None:
    """Honor the explicit always-allow rule after higher-priority lock/time/idle checks."""
    inputs = make_inputs(
        window=WindowInfo("Zoom Meeting", "zoom.exe", (0, 0, 800, 600), False),
        rules={"ZOOM.EXE": ContextRule.ALLOW},
    )

    assert context.evaluate(inputs) is ContextState.FREE


def test_fullscreen_ok_rule_does_not_override_call_detection() -> None:
    """Keep calls suppressed even when fullscreen reminders are allowed."""
    inputs = make_inputs(
        window=WindowInfo("Zoom Meeting", "zoom.exe", (0, 0, 1920, 1080), True),
        rules={"zoom.exe": ContextRule.FULLSCREEN_OK},
    )

    assert context.evaluate(inputs) is ContextState.CALL


class MutableRulesSource:
    """Provide a mutable rule mapping for evaluator behavior tests."""

    def __init__(self) -> None:
        """Initialize an empty rule mapping."""
        self.rules: dict[str, ContextRule] = {}

    def load_all(self) -> dict[str, ContextRule]:
        """Return a copy of the current process rules."""
        return dict(self.rules)


def test_context_evaluator_debounces_rapid_flapping() -> None:
    """Ignore a brief state change that returns to the confirmed state."""
    clock = FakeClock()
    bus = EventBus()
    source = MutableRulesSource()
    evaluator = ContextEvaluator(clock, source, bus)
    events: list[ContextChanged] = []
    bus.subscribe(ContextChanged, events.append)

    assert evaluator.evaluate(make_inputs()) is ContextState.FREE
    clock.advance(0.5)
    assert evaluator.evaluate(make_inputs(idle_seconds=120)) is ContextState.FREE
    clock.advance(1.0)
    assert evaluator.evaluate(make_inputs()) is ContextState.FREE
    clock.advance(2.0)

    assert evaluator.evaluate(make_inputs()) is ContextState.FREE
    assert [event.current for event in events] == [ContextState.FREE]


def test_context_evaluator_accepts_change_after_two_seconds() -> None:
    """Publish a state that remains the candidate through the debounce window."""
    clock = FakeClock()
    bus = EventBus()
    evaluator = ContextEvaluator(clock, MutableRulesSource(), bus)
    events: list[ContextChanged] = []
    bus.subscribe(ContextChanged, events.append)
    evaluator.evaluate(make_inputs())

    clock.advance(0.25)
    assert evaluator.evaluate(make_inputs(idle_seconds=120)) is ContextState.FREE
    clock.advance(1.99)
    assert evaluator.evaluate(make_inputs(idle_seconds=120)) is ContextState.FREE
    clock.advance(0.01)

    assert evaluator.evaluate(make_inputs(idle_seconds=120)) is ContextState.IDLE
    assert [event.current for event in events] == [
        ContextState.FREE,
        ContextState.IDLE,
    ]


def test_context_evaluator_applies_rule_updates_immediately() -> None:
    """Reload repository rules on every check and bypass state debounce on update."""
    clock = FakeClock()
    bus = EventBus()
    source = MutableRulesSource()
    evaluator = ContextEvaluator(clock, source, bus)
    events: list[ContextChanged] = []
    bus.subscribe(ContextChanged, events.append)
    fullscreen = make_inputs(
        window=WindowInfo("Game", "game.exe", (0, 0, 1920, 1080), True)
    )

    assert evaluator.evaluate(fullscreen) is ContextState.FULLSCREEN
    clock.advance(0.1)
    source.rules["game.exe"] = ContextRule.FULLSCREEN_OK

    assert evaluator.evaluate(fullscreen) is ContextState.FREE
    assert [event.current for event in events] == [
        ContextState.FULLSCREEN,
        ContextState.FREE,
    ]
