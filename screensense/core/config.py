"""Define and validate application settings."""

from dataclasses import dataclass
from datetime import time
from enum import StrEnum
from math import isfinite


class SettingsKey(StrEnum):
    """Stable keys for settings serialization and lookup."""

    WORK_INTERVAL_MINUTES = "work_interval_minutes"
    QUICK_BREAK_SECONDS = "quick_break_seconds"
    LONG_BREAK_MINUTES = "long_break_minutes"
    LONG_BREAK_EVERY = "long_break_every"
    IDLE_THRESHOLD_SECONDS = "idle_threshold_seconds"
    SNOOZE_MINUTES = "snooze_minutes"
    SCREEN_GOAL_HOURS = "screen_goal_hours"
    YOGA_TARGET_PER_DAY = "yoga_target_per_day"
    WORK_HOURS = "work_hours"


@dataclass(frozen=True, slots=True)
class WorkHours:
    """Local weekday schedule; the end time is exclusive."""

    start: time
    end: time
    weekdays: frozenset[int] = frozenset(range(5))

    def __post_init__(self) -> None:
        """Validate weekday indices and a non-empty same-day time range."""
        if any(day < 0 or day > 6 for day in self.weekdays):
            raise ValueError("weekdays must use datetime weekday values from 0 to 6")
        if self.start >= self.end:
            raise ValueError("work hours must start before they end on the same day")


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated user-configurable defaults for ScreenSense."""

    work_interval_minutes: int = 20
    quick_break_seconds: int = 20
    long_break_minutes: int = 5
    long_break_every: int = 3
    idle_threshold_seconds: int = 120
    snooze_minutes: int = 5
    screen_goal_hours: float = 8.0
    yoga_target_per_day: int = 3
    work_hours: WorkHours | None = WorkHours(time(9), time(18))

    def __post_init__(self) -> None:
        """Reject values outside the supported settings ranges."""
        self._validate_integer(
            SettingsKey.WORK_INTERVAL_MINUTES,
            self.work_interval_minutes,
            minimum=10,
            maximum=60,
        )
        self._validate_integer(
            SettingsKey.QUICK_BREAK_SECONDS,
            self.quick_break_seconds,
            minimum=10,
            maximum=60,
        )
        self._validate_integer(SettingsKey.LONG_BREAK_MINUTES, self.long_break_minutes)
        self._validate_integer(SettingsKey.LONG_BREAK_EVERY, self.long_break_every)
        self._validate_integer(
            SettingsKey.IDLE_THRESHOLD_SECONDS, self.idle_threshold_seconds
        )
        self._validate_integer(SettingsKey.SNOOZE_MINUTES, self.snooze_minutes)
        self._validate_positive_number(
            SettingsKey.SCREEN_GOAL_HOURS, self.screen_goal_hours
        )
        self._validate_integer(SettingsKey.YOGA_TARGET_PER_DAY, self.yoga_target_per_day)

    def to_mapping(self) -> dict[SettingsKey, int | float | str]:
        """Return settings keyed by the stable enum values."""
        return {
            SettingsKey.WORK_INTERVAL_MINUTES: self.work_interval_minutes,
            SettingsKey.QUICK_BREAK_SECONDS: self.quick_break_seconds,
            SettingsKey.LONG_BREAK_MINUTES: self.long_break_minutes,
            SettingsKey.LONG_BREAK_EVERY: self.long_break_every,
            SettingsKey.IDLE_THRESHOLD_SECONDS: self.idle_threshold_seconds,
            SettingsKey.SNOOZE_MINUTES: self.snooze_minutes,
            SettingsKey.SCREEN_GOAL_HOURS: self.screen_goal_hours,
            SettingsKey.YOGA_TARGET_PER_DAY: self.yoga_target_per_day,
            SettingsKey.WORK_HOURS: (
                "null"
                if self.work_hours is None
                else (
                    f"{self.work_hours.start.isoformat()}|"
                    f"{self.work_hours.end.isoformat()}|"
                    f"{','.join(str(day) for day in sorted(self.work_hours.weekdays))}"
                )
            ),
        }

    @staticmethod
    def _validate_integer(
        key: SettingsKey,
        value: int,
        *,
        minimum: int = 1,
        maximum: int | None = None,
    ) -> None:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{key.value} must be an integer")
        if value < minimum or (maximum is not None and value > maximum):
            if maximum is None:
                raise ValueError(f"{key.value} must be at least {minimum}")
            raise ValueError(f"{key.value} must be between {minimum} and {maximum}")

    @staticmethod
    def _validate_positive_number(key: SettingsKey, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"{key.value} must be a number")
        if not isfinite(value) or value <= 0:
            raise ValueError(f"{key.value} must be a finite positive number")
