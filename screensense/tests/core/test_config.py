"""Tests for application settings and validation."""

from typing import Any

import pytest

from screensense.core.config import Settings, SettingsKey


def test_settings_use_memory_defaults() -> None:
    """Use the documented defaults for break and wellness settings."""
    settings = Settings()

    assert settings.work_interval_minutes == 20
    assert settings.quick_break_seconds == 20
    assert settings.long_break_minutes == 5
    assert settings.long_break_every == 3
    assert settings.idle_threshold_seconds == 120
    assert settings.snooze_minutes == 5
    assert settings.screen_goal_hours == 8
    assert settings.yoga_target_per_day == 3


def test_settings_mapping_uses_enum_keys() -> None:
    """Expose persisted setting names through the key enum."""
    mapping = Settings().to_mapping()

    assert mapping[SettingsKey.WORK_INTERVAL_MINUTES] == 20
    assert mapping[SettingsKey.SCREEN_GOAL_HOURS] == 8
    assert all(isinstance(key, SettingsKey) for key in mapping)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("work_interval_minutes", 9),
        ("work_interval_minutes", 61),
        ("quick_break_seconds", 9),
        ("quick_break_seconds", 61),
        ("long_break_minutes", 0),
        ("long_break_every", 0),
        ("idle_threshold_seconds", 0),
        ("snooze_minutes", 0),
        ("screen_goal_hours", 0),
        ("yoga_target_per_day", 0),
    ],
)
def test_settings_reject_values_outside_supported_ranges(
    field: str, value: float
) -> None:
    """Reject zero, negative, and out-of-range setting values."""
    with pytest.raises(ValueError):
        Settings(**{field: value})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("work_interval_minutes", True),
        ("quick_break_seconds", 20.0),
        ("screen_goal_hours", float("inf")),
        ("screen_goal_hours", float("nan")),
    ],
)
def test_settings_reject_invalid_value_types(field: str, value: Any) -> None:
    """Reject values with incompatible types or non-finite numeric values."""
    exception = ValueError if field == "screen_goal_hours" else TypeError
    with pytest.raises(exception):
        Settings(**{field: value})
