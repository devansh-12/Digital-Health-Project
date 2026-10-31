from dataclasses import dataclass
from enum import StrEnum


class ScoreBand(StrEnum):
    GREAT = "Great"
    GOOD = "Good"
    NEEDS_ATTENTION = "Needs attention"
    REST_YOUR_EYES = "Rest your eyes"


@dataclass(frozen=True, slots=True)
class DailyScoreBreakdown:
    score: int
    break_score: float
    yoga_score: float
    screen_score: float
    blink_score: float
    band: ScoreBand
    explanation: str


def compute_daily_score(
    completed_breaks: int,
    due_breaks: int,
    yoga_sessions: int,
    yoga_target: int,
    active_seconds: int,
    screen_goal_hours: float,
    good_blink_minutes: int = 0,
    monitored_minutes: int = 0,
    blink_enabled: bool = False,
) -> DailyScoreBreakdown:
    if completed_breaks < 0 or due_breaks < 0:
        raise ValueError("breaks must be non-negative")
    if yoga_sessions < 0 or yoga_target <= 0:
        raise ValueError("yoga sessions must be non-negative and target positive")
    if active_seconds < 0 or screen_goal_hours <= 0:
        raise ValueError("active seconds non-negative and goal positive")

    break_component = min(1.0, completed_breaks / max(1, due_breaks))
    yoga_component = min(1.0, yoga_sessions / yoga_target)

    active_hours = active_seconds / 3600.0
    if active_hours <= screen_goal_hours:
        screen_component = 1.0
    else:
        overshoot = active_hours - screen_goal_hours
        decay_range = 0.5 * screen_goal_hours
        screen_component = max(0.0, 1.0 - (overshoot / max(0.1, decay_range)))

    if blink_enabled and monitored_minutes > 0:
        blink_component = min(1.0, max(0.0, good_blink_minutes / monitored_minutes))
        w_break, w_yoga, w_screen, w_blink = 0.40, 0.20, 0.25, 0.15
    else:
        blink_component = 0.0
        w_break, w_yoga, w_screen, w_blink = 0.50, 0.25, 0.25, 0.00

    weighted_sum = (
        w_break * break_component
        + w_yoga * yoga_component
        + w_screen * screen_component
        + w_blink * blink_component
    )
    score = int(round(100.0 * weighted_sum))
    score = max(0, min(100, score))

    if score >= 80:
        band = ScoreBand.GREAT
    elif score >= 60:
        band = ScoreBand.GOOD
    elif score >= 40:
        band = ScoreBand.NEEDS_ATTENTION
    else:
        band = ScoreBand.REST_YOUR_EYES

    explanation = _generate_explanation(
        break_component,
        yoga_component,
        screen_component,
        blink_component,
        completed_breaks,
        due_breaks,
        yoga_sessions,
        yoga_target,
        active_hours,
        screen_goal_hours,
        blink_enabled and monitored_minutes > 0,
    )

    return DailyScoreBreakdown(
        score=score,
        break_score=round(break_component, 3),
        yoga_score=round(yoga_component, 3),
        screen_score=round(screen_component, 3),
        blink_score=round(blink_component, 3),
        band=band,
        explanation=explanation,
    )


def _generate_explanation(
    break_c: float,
    yoga_c: float,
    screen_c: float,
    blink_c: float,
    completed_b: int,
    due_b: int,
    yoga_s: int,
    yoga_target: int,
    active_h: float,
    goal_h: float,
    blink_active: bool,
) -> str:
    components = [
        ("breaks", break_c),
        ("yoga", yoga_c),
        ("screen", screen_c),
    ]
    if blink_active:
        components.append(("blink", blink_c))

    components.sort(key=lambda item: item[1])
    lowest_name, lowest_val = components[0]

    if lowest_val >= 0.99:
        return "Outstanding eye care! All daily goals were achieved."

    if lowest_name == "breaks":
        return f"Your score was held back by breaks: {completed_b} completed out of {due_b} due."
    elif lowest_name == "yoga":
        return f"Your score was held back by Eye Yoga: {yoga_s} completed vs your {yoga_target} goal."
    elif lowest_name == "screen":
        return f"Your score was held back by screen time: {active_h:.1f}h active vs your {goal_h:.1f}h goal."
    else:
        return "Your score was held back by reduced blink rate during screen sessions."
