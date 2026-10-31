"""Provide eye-yoga routines and animation widgets."""

from screensense.core.yoga import DEFAULT_EYE_YOGA_ROUTINE, YogaRoutine, YogaStep
from screensense.ui.eye_yoga.animations import EyeYogaAnimationWidget
from screensense.ui.eye_yoga.player import EyeYogaPlayer

__all__ = [
    "DEFAULT_EYE_YOGA_ROUTINE",
    "EyeYogaAnimationWidget",
    "EyeYogaPlayer",
    "YogaRoutine",
    "YogaStep",
]
