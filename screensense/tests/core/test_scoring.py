import pytest
from screensense.core.scoring import ScoreBand, compute_daily_score


def test_perfect_compliance_gives_high_score() -> None:
    breakdown = compute_daily_score(
        completed_breaks=12,
        due_breaks=12,
        yoga_sessions=3,
        yoga_target=3,
        active_seconds=6 * 3600,
        screen_goal_hours=8.0,
    )
    assert breakdown.score == 100
    assert breakdown.band is ScoreBand.GREAT
    assert "Outstanding" in breakdown.explanation


def test_zero_breaks_and_no_yoga_drastically_reduces_score() -> None:
    breakdown = compute_daily_score(
        completed_breaks=0,
        due_breaks=10,
        yoga_sessions=0,
        yoga_target=3,
        active_seconds=4 * 3600,
        screen_goal_hours=8.0,
    )
    assert breakdown.score == 25
    assert breakdown.band is ScoreBand.REST_YOUR_EYES
    assert "held back by breaks" in breakdown.explanation


def test_excessive_screen_time_decays_score() -> None:
    breakdown = compute_daily_score(
        completed_breaks=10,
        due_breaks=10,
        yoga_sessions=3,
        yoga_target=3,
        active_seconds=12 * 3600,
        screen_goal_hours=8.0,
    )
    assert breakdown.screen_score == 0.0
    assert breakdown.score == 75
    assert breakdown.band is ScoreBand.GOOD
    assert "screen time" in breakdown.explanation


def test_weight_redistribution_when_blink_monitor_enabled() -> None:
    breakdown = compute_daily_score(
        completed_breaks=10,
        due_breaks=10,
        yoga_sessions=3,
        yoga_target=3,
        active_seconds=6 * 3600,
        screen_goal_hours=8.0,
        good_blink_minutes=50,
        monitored_minutes=100,
        blink_enabled=True,
    )
    assert breakdown.blink_score == 0.5
    assert breakdown.score == int(round(100 * (0.40 * 1.0 + 0.20 * 1.0 + 0.25 * 1.0 + 0.15 * 0.5)))
    assert breakdown.score == 93


def test_invalid_negative_arguments_raise() -> None:
    with pytest.raises(ValueError):
        compute_daily_score(-1, 5, 1, 3, 3600, 8.0)

    with pytest.raises(ValueError):
        compute_daily_score(1, 5, -1, 3, 3600, 8.0)

    with pytest.raises(ValueError):
        compute_daily_score(1, 5, 1, 0, 3600, 8.0)

    with pytest.raises(ValueError):
        compute_daily_score(1, 5, 1, 3, -100, 8.0)
