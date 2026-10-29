"""Tests for SQLite initialization and migrations."""

import sqlite3

import pytest

from screensense.storage.db import open_database, run_migrations


def test_open_database_enables_wal_and_creates_schema(tmp_path) -> None:
    """Initialize a temporary database with WAL and all architecture tables."""
    database_path = tmp_path / "screensense.sqlite3"

    connection = open_database(database_path)
    try:
        journal_mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        table_names = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    finally:
        connection.close()

    assert journal_mode == "wal"
    assert {
        "schema_migrations",
        "settings",
        "usage_hourly",
        "breaks",
        "yoga_sessions",
        "blink_minutely",
        "daily_scores",
        "streaks",
        "badges",
        "context_rules",
    } <= table_names


def test_migrations_are_idempotent(tmp_path) -> None:
    """Applying migrations again leaves the existing schema unchanged."""
    connection = open_database(tmp_path / "screensense.sqlite3")
    try:
        run_migrations(connection)
        applied_count = connection.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0]
    finally:
        connection.close()

    assert applied_count == 1


def test_schema_constraints_reject_invalid_values(tmp_path) -> None:
    """Enforce the architecture's enumerated break and context values."""
    connection = open_database(tmp_path / "screensense.sqlite3")
    try:
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO breaks (due_at, kind) VALUES (?, ?)",
                (1, "unknown"),
            )
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO context_rules (process, rule) VALUES (?, ?)",
                ("sample.exe", "unknown"),
            )
    finally:
        connection.close()
