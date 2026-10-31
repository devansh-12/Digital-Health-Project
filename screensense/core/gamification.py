from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True, slots=True)
class StreakState:
    current: int
    best: int
    last_counted_day: str | None
    freeze_week: str | None


@dataclass(frozen=True, slots=True)
class BadgeDefinition:
    code: str
    title: str
    description: str
    category: str


BADGES_CATALOGUE: list[BadgeDefinition] = [
    BadgeDefinition(
        code="first_break",
        title="First Look Away",
        description="Completed your first screen break.",
        category="Break",
    ),
    BadgeDefinition(
        code="first_yoga",
        title="First Stretch",
        description="Completed your first 60s Eye Yoga session.",
        category="Yoga",
    ),
    BadgeDefinition(
        code="yogi",
        title="Yogi",
        description="Completed 10 Eye Yoga sessions.",
        category="Yoga",
    ),
    BadgeDefinition(
        code="streak_3",
        title="Three's Company",
        description="Maintained a 3-day wellness streak.",
        category="Streak",
    ),
    BadgeDefinition(
        code="streak_7",
        title="Week Warrior",
        description="Maintained a 7-day wellness streak.",
        category="Streak",
    ),
    BadgeDefinition(
        code="iron_eyes",
        title="Iron Eyes",
        description="Reached an unbroken 30-day streak.",
        category="Streak",
    ),
    BadgeDefinition(
        code="zen_master",
        title="Zen Master",
        description="Achieved a Daily Wellness Score of 95 or higher.",
        category="Mastery",
    ),
]


def update_streak(
    state: StreakState,
    day_str: str,
    score: int,
    completed_breaks: int,
) -> StreakState:
    qualifies = score >= 60 and completed_breaks >= 1
    current_day = date.fromisoformat(day_str)

    if state.last_counted_day is None:
        if qualifies:
            return StreakState(
                current=1,
                best=max(state.best, 1),
                last_counted_day=day_str,
                freeze_week=state.freeze_week,
            )
        return state

    last_day = date.fromisoformat(state.last_counted_day)
    if current_day == last_day:
        return state

    if current_day < last_day:
        return state

    delta_days = (current_day - last_day).days

    if delta_days == 1:
        if qualifies:
            new_current = state.current + 1
            return StreakState(
                current=new_current,
                best=max(state.best, new_current),
                last_counted_day=day_str,
                freeze_week=state.freeze_week,
            )
        return state

    if delta_days == 2:
        missed_day = last_day + timedelta(days=1)
        iso = missed_day.isocalendar()
        missed_week_str = f"{iso.year}-{iso.week:02d}"
        if state.freeze_week != missed_week_str:
            if qualifies:
                new_current = state.current + 1
                return StreakState(
                    current=new_current,
                    best=max(state.best, new_current),
                    last_counted_day=day_str,
                    freeze_week=missed_week_str,
                )
            return state

    if qualifies:
        return StreakState(
            current=1,
            best=max(state.best, 1),
            last_counted_day=day_str,
            freeze_week=state.freeze_week,
        )

    return StreakState(
        current=0,
        best=state.best,
        last_counted_day=None,
        freeze_week=state.freeze_week,
    )


def evaluate_new_badges(
    earned_codes: set[str],
    total_breaks_completed: int,
    total_yoga_sessions: int,
    streak_count: int,
    today_score: int,
) -> list[str]:
    new_badges: list[str] = []

    if "first_break" not in earned_codes and total_breaks_completed >= 1:
        new_badges.append("first_break")

    if "first_yoga" not in earned_codes and total_yoga_sessions >= 1:
        new_badges.append("first_yoga")

    if "yogi" not in earned_codes and total_yoga_sessions >= 10:
        new_badges.append("yogi")

    if "streak_3" not in earned_codes and streak_count >= 3:
        new_badges.append("streak_3")

    if "streak_7" not in earned_codes and streak_count >= 7:
        new_badges.append("streak_7")

    if "iron_eyes" not in earned_codes and streak_count >= 30:
        new_badges.append("iron_eyes")

    if "zen_master" not in earned_codes and today_score >= 95:
        new_badges.append("zen_master")

    return new_badges
