"""Decision-table tests for context evaluation (red until evaluate is added)."""

from dataclasses import replace
from datetime import datetime, time

import pytest

from screensense.core import context
from screensense.core.context import ContextInputs, ContextRule, ContextState, WorkHours
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
