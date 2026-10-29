"""Provide settings and break data access repositories."""

import sqlite3
from dataclasses import dataclass
from enum import StrEnum

from screensense.core.config import Settings, SettingsKey
from screensense.core.context import ContextRule


class BreakKind(StrEnum):
    """Supported break categories stored in the database."""

    QUICK = "quick"
    LONG = "long"
    YOGA = "yoga"
    NATURAL = "natural"


class BreakOutcome(StrEnum):
    """Supported outcomes for a scheduled break."""

    COMPLETED = "completed"
    SNOOZED = "snoozed"
    SKIPPED = "skipped"
    SUPPRESSED = "suppressed"
    EXPIRED = "expired"


@dataclass(frozen=True, slots=True)
class BreakRecord:
    """A stored break and its current outcome, if one is recorded."""

    id: int
    due_at: int
    shown_at: int | None
    kind: BreakKind
    outcome: BreakOutcome | None
    duration_s: int | None


class SettingsRepository:
    """Load and save validated settings using the SQLite settings table."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Create a repository backed by an open database connection."""
        self._connection = connection

    def load(self) -> Settings:
        """Load saved values over defaults and validate the resulting settings."""
        defaults = Settings()
        default_values = defaults.to_mapping()
        values: dict[SettingsKey, int | float] = dict(default_values)

        rows = self._connection.execute("SELECT key, value FROM settings")
        for row in rows:
            try:
                key = SettingsKey(row[0])
            except ValueError:
                continue
            default_value = default_values[key]
            try:
                values[key] = (
                    float(row[1]) if isinstance(default_value, float) else int(row[1])
                )
            except (TypeError, ValueError) as error:
                raise ValueError(f"Invalid stored value for {key.value}") from error

        return Settings(
            work_interval_minutes=int(values[SettingsKey.WORK_INTERVAL_MINUTES]),
            quick_break_seconds=int(values[SettingsKey.QUICK_BREAK_SECONDS]),
            long_break_minutes=int(values[SettingsKey.LONG_BREAK_MINUTES]),
            long_break_every=int(values[SettingsKey.LONG_BREAK_EVERY]),
            idle_threshold_seconds=int(values[SettingsKey.IDLE_THRESHOLD_SECONDS]),
            snooze_minutes=int(values[SettingsKey.SNOOZE_MINUTES]),
            screen_goal_hours=float(values[SettingsKey.SCREEN_GOAL_HOURS]),
            yoga_target_per_day=int(values[SettingsKey.YOGA_TARGET_PER_DAY]),
        )

    def save(self, settings: Settings) -> None:
        """Persist every validated setting in one transaction."""
        entries = [
            (key.value, str(value)) for key, value in settings.to_mapping().items()
        ]
        with self._connection:
            self._connection.executemany(
                """
                INSERT INTO settings (key, value) VALUES (?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value
                """,
                entries,
            )


class ContextRulesRepository:
    """Load and update per-process context rules in SQLite."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Create a repository backed by an open database connection."""
        self._connection = connection

    def load_all(self) -> dict[str, ContextRule]:
        """Return all process rules, keyed by normalized process name."""
        rows = self._connection.execute(
            "SELECT process, rule FROM context_rules ORDER BY process"
        )
        return {
            str(row[0]): ContextRule(str(row[1]))
            for row in rows
        }

    def set_rule(self, process: str, rule: ContextRule) -> None:
        """Insert or update a rule for a normalized process name."""
        process_name = process.strip().casefold()
        if not process_name:
            raise ValueError("process must not be empty")
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO context_rules (process, rule) VALUES (?, ?)
                ON CONFLICT(process) DO UPDATE SET rule = excluded.rule
                """,
                (process_name, rule.value),
            )

    def delete_rule(self, process: str) -> None:
        """Remove a process rule if it exists."""
        process_name = process.strip().casefold()
        if not process_name:
            raise ValueError("process must not be empty")
        with self._connection:
            self._connection.execute(
                "DELETE FROM context_rules WHERE process = ?", (process_name,)
            )


class BreaksRepository:
    """Create, retrieve, list, and update stored break records."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Create a repository backed by an open database connection."""
        self._connection = connection

    def create(
        self, due_at: int, kind: BreakKind, shown_at: int | None = None
    ) -> int:
        """Insert a pending break and return its database identifier."""
        cursor = self._connection.execute(
            "INSERT INTO breaks (due_at, shown_at, kind) VALUES (?, ?, ?)",
            (due_at, shown_at, kind.value),
        )
        self._connection.commit()
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return an identifier for the break")
        return cursor.lastrowid

    def get(self, break_id: int) -> BreakRecord | None:
        """Return a break by identifier, or None when it does not exist."""
        row = self._connection.execute(
            """
            SELECT id, due_at, shown_at, kind, outcome, duration_s
            FROM breaks
            WHERE id = ?
            """,
            (break_id,),
        ).fetchone()
        return self._to_record(row) if row is not None else None

    def list_recent(self, limit: int = 100) -> list[BreakRecord]:
        """Return the most recently due breaks, newest first."""
        if isinstance(limit, bool) or not isinstance(limit, int) or limit < 1:
            raise ValueError("limit must be a positive integer")
        rows = self._connection.execute(
            """
            SELECT id, due_at, shown_at, kind, outcome, duration_s
            FROM breaks
            ORDER BY due_at DESC, id DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [self._to_record(row) for row in rows]

    def update_outcome(
        self,
        break_id: int,
        outcome: BreakOutcome,
        duration_s: int | None = None,
    ) -> None:
        """Set a break outcome and optional duration, raising for an unknown ID."""
        if duration_s is not None and (
            isinstance(duration_s, bool)
            or not isinstance(duration_s, int)
            or duration_s < 0
        ):
            raise ValueError("duration_s must be a non-negative integer")
        with self._connection:
            cursor = self._connection.execute(
                "UPDATE breaks SET outcome = ?, duration_s = ? WHERE id = ?",
                (outcome.value, duration_s, break_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(f"Break not found: {break_id}")

    @staticmethod
    def _to_record(row: sqlite3.Row | tuple[object, ...]) -> BreakRecord:
        outcome_value = row[4]
        return BreakRecord(
            id=int(row[0]),
            due_at=int(row[1]),
            shown_at=int(row[2]) if row[2] is not None else None,
            kind=BreakKind(str(row[3])),
            outcome=(BreakOutcome(str(outcome_value)) if outcome_value is not None else None),
            duration_s=int(row[5]) if row[5] is not None else None,
        )
