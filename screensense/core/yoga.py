"""Define data structures and routines for guided Eye Yoga sessions."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class YogaStep:
    """Describe a single guided exercise step in an Eye Yoga routine."""

    name: str
    seconds: int
    text: str
    anim: str


@dataclass(frozen=True, slots=True)
class YogaRoutine:
    """Represent an immutable sequence of Eye Yoga exercises."""

    id: str
    total_seconds: int
    steps: tuple[YogaStep, ...]


DEFAULT_EYE_YOGA_ROUTINE = YogaRoutine(
    id="eye_yoga_60",
    total_seconds=60,
    steps=(
        YogaStep(
            name="Palming",
            seconds=10,
            text="Rub palms, cup them over closed eyes. Breathe slowly.",
            anim="palming",
        ),
        YogaStep(
            name="Fast blinking",
            seconds=10,
            text="Blink gently and quickly, then close eyes for 2 s.",
            anim="blink",
        ),
        YogaStep(
            name="Figure eight",
            seconds=10,
            text="Trace a big sideways 8 with your eyes.",
            anim="fig8",
        ),
        YogaStep(
            name="Near-far focus",
            seconds=10,
            text="Focus on your thumb, then something far away. Switch.",
            anim="nearfar",
        ),
        YogaStep(
            name="Up-down-left-right",
            seconds=10,
            text="Look in each direction, holding 1-2 s without moving your head.",
            anim="compass",
        ),
        YogaStep(
            name="Slow eye rolls",
            seconds=10,
            text="Roll eyes in a slow circle, then reverse.",
            anim="roll",
        ),
    ),
)
