"""Catalog of rotating ergonomic and eye-health tips."""

import random

ERGONOMIC_TIPS: tuple[str, ...] = (
    "20-20-20 Rule: Look at something 20 feet away for 20 seconds.",
    "Blink slowly 10 times to naturally re-moisturize your eyes.",
    "Palming: Warm your palms by rubbing them together, then gently cup them over closed eyes.",
    "Roll your shoulders backward to release tension in your neck and upper back.",
    "Sip some water — staying hydrated directly promotes healthy tear production.",
    "Check your screen angle: the top of your monitor should be at or slightly below eye level.",
    "Take three slow, deep belly breaths to help relax facial muscles.",
    "Gentle eye roll: look up, slowly circle to the right, down, left, and back up.",
    "Adjust room lighting so it matches your monitor's brightness.",
    "Stand up and stretch your legs and hip flexors for a few moments.",
)


def get_random_tip() -> str:
    """Return a randomly chosen eye care or ergonomic tip."""
    return random.choice(ERGONOMIC_TIPS)

