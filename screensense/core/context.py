"""Define context states for reminder suppression."""

from enum import StrEnum


class ContextState(StrEnum):
    """Current user context used to decide whether a prompt may appear."""

    FREE = "free"
    IDLE = "idle"
    FULLSCREEN = "fullscreen"
    CALL = "call"
    OUTSIDE_HOURS = "outside_hours"
    LOCKED = "locked"
