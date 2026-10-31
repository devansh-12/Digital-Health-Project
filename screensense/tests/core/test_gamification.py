from screensense.core.gamification import (
    StreakState,
    evaluate_new_badges,
    update_streak,
)


def test_initial_streak_increments_when_qualified() -> None:
    initial = StreakState(current=0, best=0, last_counted_day=None, freeze_week=None)
    next_state = update_streak(initial, "2026-10-01", score=75, completed_breaks=3)
    assert next_state.current == 1
    assert next_state.best == 1
    assert next_state.last_counted_day == "2026-10-01"


def test_consecutive_days_increment_streak() -> None:
    s1 = update_streak(
        StreakState(0, 0, None, None), "2026-10-01", score=80, completed_breaks=2
    )
    s2 = update_streak(s1, "2026-10-02", score=65, completed_breaks=1)
    assert s2.current == 2
    assert s2.best == 2
    assert s2.last_counted_day == "2026-10-02"


def test_weekly_freeze_protects_single_missed_day() -> None:
    s1 = update_streak(
        StreakState(0, 0, None, None), "2026-10-01", score=80, completed_breaks=2
    )
    s2 = update_streak(s1, "2026-10-03", score=85, completed_breaks=3)
    assert s2.current == 2
    assert s2.freeze_week is not None
    assert s2.last_counted_day == "2026-10-03"


def test_second_gap_in_same_week_resets_streak() -> None:
    s1 = StreakState(current=4, best=4, last_counted_day="2026-10-01", freeze_week="2026-40")
    s2 = update_streak(s1, "2026-10-03", score=80, completed_breaks=2)
    assert s2.current == 1


def test_badge_evaluation_triggers_on_milestones() -> None:
    earned: set[str] = set()
    badges = evaluate_new_badges(
        earned_codes=earned,
        total_breaks_completed=1,
        total_yoga_sessions=1,
        streak_count=3,
        today_score=96,
    )
    assert "first_break" in badges
    assert "first_yoga" in badges
    assert "streak_3" in badges
    assert "zen_master" in badges
