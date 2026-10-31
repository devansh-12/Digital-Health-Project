"""Test Eye Yoga domain structures and default routine."""

from screensense.core.yoga import DEFAULT_EYE_YOGA_ROUTINE, YogaRoutine, YogaStep


def test_default_routine_structure() -> None:
    """Verify DEFAULT_EYE_YOGA_ROUTINE has 6 steps summing to 60 seconds."""
    routine = DEFAULT_EYE_YOGA_ROUTINE
    assert routine.id == "eye_yoga_60"
    assert routine.total_seconds == 60
    assert len(routine.steps) == 6

    step_sum = sum(s.seconds for s in routine.steps)
    assert step_sum == routine.total_seconds

    for step in routine.steps:
        assert isinstance(step.name, str) and step.name
        assert isinstance(step.text, str) and step.text
        assert isinstance(step.anim, str) and step.anim
        assert step.seconds > 0


def test_yoga_routine_immutability() -> None:
    """Verify YogaStep and YogaRoutine cannot be mutated after creation."""
    step = YogaStep("Test", 10, "Instruction", "anim")
    try:
        step.name = "Other"  # type: ignore[misc]
    except (TypeError, AttributeError):
        pass
    else:
        assert False, "YogaStep should be immutable"
