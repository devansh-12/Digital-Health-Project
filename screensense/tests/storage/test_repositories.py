"""Tests for settings and break repositories using temporary databases."""

import pytest

from screensense.core.config import Settings
from screensense.storage.db import open_database
from screensense.storage.repositories import (
    BreakKind,
    BreakOutcome,
    BreaksRepository,
    SettingsRepository,
)


@pytest.fixture
def connection(tmp_path):
    """Provide an initialized temporary database connection."""
    database = open_database(tmp_path / "screensense.sqlite3")
    yield database
    database.close()


def test_settings_repository_returns_defaults_when_empty(connection) -> None:
    """Return validated defaults when no user settings have been saved."""
    assert SettingsRepository(connection).load() == Settings()


def test_settings_repository_round_trips_values(connection) -> None:
    """Persist and reload a complete validated settings object."""
    repository = SettingsRepository(connection)
    settings = Settings(
        work_interval_minutes=30,
        quick_break_seconds=25,
        long_break_minutes=10,
        long_break_every=4,
        idle_threshold_seconds=150,
        snooze_minutes=7,
        screen_goal_hours=7.5,
        yoga_target_per_day=2,
    )

    repository.save(settings)

    assert repository.load() == settings


def test_break_repository_creates_reads_and_updates_break(connection) -> None:
    """Store a pending break, then retrieve it with its completed outcome."""
    repository = BreaksRepository(connection)
    break_id = repository.create(due_at=100, shown_at=105, kind=BreakKind.QUICK)

    pending = repository.get(break_id)
    assert pending is not None
    assert pending.due_at == 100
    assert pending.shown_at == 105
    assert pending.kind is BreakKind.QUICK
    assert pending.outcome is None

    repository.update_outcome(break_id, BreakOutcome.COMPLETED, duration_s=20)

    completed = repository.get(break_id)
    assert completed is not None
    assert completed.outcome is BreakOutcome.COMPLETED
    assert completed.duration_s == 20


def test_break_repository_lists_newest_due_first(connection) -> None:
    """Limit results and return breaks ordered by due time descending."""
    repository = BreaksRepository(connection)
    repository.create(due_at=100, kind=BreakKind.QUICK)
    newest_id = repository.create(due_at=200, kind=BreakKind.LONG)

    records = repository.list_recent(limit=1)

    assert len(records) == 1
    assert records[0].id == newest_id
    assert records[0].due_at == 200


def test_break_repository_returns_none_for_unknown_id(connection) -> None:
    """Return None when a requested break does not exist."""
    assert BreaksRepository(connection).get(999) is None


def test_break_repository_rejects_invalid_limit_and_duration(connection) -> None:
    """Reject invalid pagination limits and negative durations."""
    repository = BreaksRepository(connection)

    with pytest.raises(ValueError):
        repository.list_recent(limit=0)
    with pytest.raises(ValueError):
        repository.update_outcome(1, BreakOutcome.SKIPPED, duration_s=-1)


def test_break_repository_rejects_outcome_for_unknown_id(connection) -> None:
    """Raise when updating a break that is not present in storage."""
    with pytest.raises(KeyError):
        BreaksRepository(connection).update_outcome(999, BreakOutcome.SKIPPED)
