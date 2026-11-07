"""Provide settings and break data access repositories."""

import sqlite3
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import time
from enum import StrEnum

from screensense.core.config import Settings, SettingsKey, WorkHours
from screensense.core.context import ContextRule
from screensense.core.gamification import StreakState
from screensense.core.tracker import UsageBucket


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
        values: dict[SettingsKey, int | float | str | bool] = dict(default_values)

        rows = self._connection.execute("SELECT key, value FROM settings")
        for row in rows:
            try:
                key = SettingsKey(row[0])
            except ValueError:
                continue
            default_value = default_values[key]
            try:
                if key is SettingsKey.WORK_HOURS:
                    values[key] = str(row[1])
                elif key is SettingsKey.BLINK_MONITOR_ENABLED or key in {
                    SettingsKey.ONBOARDING_COMPLETED,
                    SettingsKey.REDUCED_MOTION,
                }:
                    if str(row[1]) not in {"0", "1"}:
                        raise ValueError(f"Invalid stored value for {key.value}")
                    values[key] = str(row[1]) == "1"
                elif key is SettingsKey.UI_THEME:
                    values[key] = str(row[1])
                else:
                    values[key] = (
                        float(row[1])
                        if isinstance(default_value, float)
                        else int(row[1])
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
            work_hours=self._parse_work_hours(str(values[SettingsKey.WORK_HOURS])),
            blink_monitor_enabled=bool(values[SettingsKey.BLINK_MONITOR_ENABLED]),
            onboarding_completed=bool(values[SettingsKey.ONBOARDING_COMPLETED]),
            ui_theme=str(values[SettingsKey.UI_THEME]),
            reduced_motion=bool(values[SettingsKey.REDUCED_MOTION]),
            snooze_limit_per_session=int(values[SettingsKey.SNOOZE_LIMIT_PER_SESSION]),
        )

    @staticmethod
    def _parse_work_hours(value: str) -> WorkHours | None:
        """Parse the compact persisted local work schedule."""
        if value == "null":
            return None
        try:
            start, end, weekdays = value.split("|")
            return WorkHours(
                start=time.fromisoformat(start),
                end=time.fromisoformat(end),
                weekdays=frozenset(int(day) for day in weekdays.split(",") if day),
            )
        except (TypeError, ValueError) as error:
            raise ValueError("Invalid stored value for work_hours") from error

    def save(self, settings: Settings) -> None:
        """Persist every validated setting in one transaction."""
        entries = [
            (
                key.value,
                ("1" if value else "0") if isinstance(value, bool) else str(value),
            )
            for key, value in settings.to_mapping().items()
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
        return {str(row[0]): ContextRule(str(row[1])) for row in rows}

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

    def create(self, due_at: int, kind: BreakKind, shown_at: int | None = None) -> int:
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

    def record_suppressed(self, due_at: int, kind: str) -> int:
        """Insert one suppressed reminder and return its database identifier."""
        if kind not in (BreakKind.QUICK.value, BreakKind.LONG.value):
            raise ValueError("suppressed prompts must use quick or long kind")
        with self._connection:
            cursor = self._connection.execute(
                "INSERT INTO breaks (due_at, kind, outcome) VALUES (?, ?, ?)",
                (due_at, kind, BreakOutcome.SUPPRESSED.value),
            )
        if cursor.lastrowid is None:
            raise RuntimeError("SQLite did not return an identifier for the break")
        return cursor.lastrowid

    def record_completed(
        self,
        due_at: int,
        shown_at: int,
        kind: str,
        duration_s: int,
        suppressed_break_id: int | None = None,
    ) -> None:
        """Insert a completed break or finalize its queued suppressed record."""
        if kind not in (
            BreakKind.QUICK.value,
            BreakKind.LONG.value,
            BreakKind.YOGA.value,
        ):
            raise ValueError("completed breaks must use quick, long, or yoga kind")
        if (
            isinstance(duration_s, bool)
            or not isinstance(duration_s, int)
            or duration_s < 0
        ):
            raise ValueError("duration_s must be a non-negative integer")
        with self._connection:
            if suppressed_break_id is not None:
                cursor = self._connection.execute(
                    """
                    UPDATE breaks
                    SET shown_at = ?, kind = ?, outcome = ?, duration_s = ?
                    WHERE id = ?
                    """,
                    (
                        shown_at,
                        kind,
                        BreakOutcome.COMPLETED.value,
                        duration_s,
                        suppressed_break_id,
                    ),
                )
                if cursor.rowcount == 0:
                    raise KeyError(f"Break not found: {suppressed_break_id}")
                return
            self._connection.execute(
                """
                INSERT INTO breaks (due_at, shown_at, kind, outcome, duration_s)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    due_at,
                    shown_at,
                    kind,
                    BreakOutcome.COMPLETED.value,
                    duration_s,
                ),
            )

    def record_natural(self, due_at: int, duration_s: int) -> None:
        """Insert a completed natural break using parameterized SQL."""
        if (
            isinstance(duration_s, bool)
            or not isinstance(duration_s, int)
            or duration_s < 0
        ):
            raise ValueError("duration_s must be a non-negative integer")
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO breaks (due_at, kind, outcome, duration_s)
                VALUES (?, ?, ?, ?)
                """,
                (
                    due_at,
                    BreakKind.NATURAL.value,
                    BreakOutcome.COMPLETED.value,
                    duration_s,
                ),
            )

    def count_for_range(self, start_ts: int, end_ts: int) -> tuple[int, int]:
        cursor = self._connection.execute(
            """
            SELECT
                SUM(CASE WHEN outcome = 'completed' THEN 1 ELSE 0 END),
                COUNT(*)
            FROM breaks
            WHERE due_at >= ? AND due_at < ?
            """,
            (start_ts, end_ts),
        )
        row = cursor.fetchone()
        if not row or row[1] is None:
            return 0, 0
        completed = int(row[0]) if row[0] is not None else 0
        due = int(row[1]) if row[1] is not None else 0
        return completed, due

    def list_for_range(self, start_ts: int, end_ts: int) -> list[BreakRecord]:
        rows = self._connection.execute(
            """
            SELECT id, due_at, shown_at, kind, outcome, duration_s
            FROM breaks
            WHERE due_at >= ? AND due_at < ?
            ORDER BY due_at ASC
            """,
            (start_ts, end_ts),
        )
        return [self._to_record(row) for row in rows]

    @staticmethod
    def _to_record(row: sqlite3.Row | tuple[object, ...]) -> BreakRecord:
        outcome_value = row[4]
        return BreakRecord(
            id=int(str(row[0])),
            due_at=int(str(row[1])),
            shown_at=int(str(row[2])) if row[2] is not None else None,
            kind=BreakKind(str(row[3])),
            outcome=(
                BreakOutcome(str(outcome_value)) if outcome_value is not None else None
            ),
            duration_s=int(str(row[5])) if row[5] is not None else None,
        )


class UsageHourlyRepository:
    """Atomically upsert additive usage deltas by hour."""

    def __init__(
        self,
        connection: sqlite3.Connection | None = None,
        *,
        connection_factory: Callable[[], sqlite3.Connection] | None = None,
    ) -> None:
        """Use a same-thread connection or a factory for worker-thread writes."""
        if (connection is None) == (connection_factory is None):
            raise ValueError("provide exactly one connection or connection_factory")
        self._connection = connection
        self._connection_factory = connection_factory

    def write_usage(self, buckets: Sequence[UsageBucket]) -> None:
        """Upsert a batch, opening the connection inside the calling thread if needed."""
        if not buckets:
            return
        if self._connection is not None:
            self._upsert(self._connection, buckets)
            return
        if self._connection_factory is None:
            raise RuntimeError("No database connection is configured")
        connection = self._connection_factory()
        try:
            self._upsert(connection, buckets)
        finally:
            connection.close()

    def upsert(self, buckets: Sequence[UsageBucket]) -> None:
        """Public alias for writing one atomic batch of usage deltas."""
        self.write_usage(buckets)

    def get_active_seconds_for_range(self, start_ts: int, end_ts: int) -> int:
        conn = self._connection
        should_close = False
        if conn is None:
            if self._connection_factory is None:
                return 0
            conn = self._connection_factory()
            should_close = True
        try:
            cursor = conn.execute(
                """
                SELECT SUM(active_s) FROM usage_hourly
                WHERE hour_start >= ? AND hour_start < ?
                """,
                (start_ts, end_ts),
            )
            row = cursor.fetchone()
            return int(row[0]) if row and row[0] is not None else 0
        finally:
            if should_close:
                conn.close()

    def get_hourly_breakdown_for_range(
        self, start_ts: int, end_ts: int
    ) -> list[tuple[int, int, int]]:
        conn = self._connection
        should_close = False
        if conn is None:
            if self._connection_factory is None:
                return []
            conn = self._connection_factory()
            should_close = True
        try:
            cursor = conn.execute(
                """
                SELECT hour_start, active_s, idle_s
                FROM usage_hourly
                WHERE hour_start >= ? AND hour_start < ?
                ORDER BY hour_start ASC
                """,
                (start_ts, end_ts),
            )
            return [(int(r[0]), int(r[1]), int(r[2])) for r in cursor.fetchall()]
        finally:
            if should_close:
                conn.close()

    @staticmethod
    def _upsert(connection: sqlite3.Connection, buckets: Sequence[UsageBucket]) -> None:
        entries: list[tuple[int, int, int, int, int]] = []
        for bucket in buckets:
            if (
                isinstance(bucket.hour_start, bool)
                or not isinstance(bucket.hour_start, int)
                or bucket.hour_start % 3_600 != 0
            ):
                raise ValueError("hour_start must be an integer Unix-hour boundary")
            values = (
                bucket.active_s,
                bucket.idle_s,
                bucket.fullscreen_s,
                bucket.call_s,
            )
            if any(
                isinstance(value, bool) or not isinstance(value, int) or value < 0
                for value in values
            ):
                raise ValueError("usage counters must be non-negative integers")
            entries.append((bucket.hour_start, *values))

        with connection:
            connection.executemany(
                """
                INSERT INTO usage_hourly (
                    hour_start, active_s, idle_s, fullscreen_s, call_s
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(hour_start) DO UPDATE SET
                    active_s = usage_hourly.active_s + excluded.active_s,
                    idle_s = usage_hourly.idle_s + excluded.idle_s,
                    fullscreen_s = usage_hourly.fullscreen_s + excluded.fullscreen_s,
                    call_s = usage_hourly.call_s + excluded.call_s
                """,
                entries,
            )


@dataclass(frozen=True, slots=True)
class YogaSessionRecord:
    """A stored record of an Eye Yoga session."""

    id: int
    started_at: int
    steps_completed: int
    total_steps: int
    duration_s: int


class YogaSessionsRepository:
    """Store and query Eye Yoga sessions using the SQLite database."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        """Create a repository backed by an open database connection."""
        self._connection = connection

    def record_session(
        self,
        started_at: int,
        steps_completed: int,
        total_steps: int,
        duration_s: int,
    ) -> int:
        """Insert an Eye Yoga session and return its database identifier."""
        with self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO yoga_sessions (
                    started_at, steps_completed, total_steps, duration_s
                ) VALUES (?, ?, ?, ?)
                """,
                (started_at, steps_completed, total_steps, duration_s),
            )
            return int(cursor.lastrowid or 0)

    def count_today(self, day_start_timestamp: int) -> int:
        """Return the count of completed sessions started on or after day_start_timestamp."""
        cursor = self._connection.execute(
            """
            SELECT COUNT(*) FROM yoga_sessions
            WHERE started_at >= ? AND steps_completed = total_steps
            """,
            (day_start_timestamp,),
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0

    def count_for_range(self, start_ts: int, end_ts: int) -> int:
        cursor = self._connection.execute(
            """
            SELECT COUNT(*) FROM yoga_sessions
            WHERE started_at >= ? AND started_at < ? AND steps_completed = total_steps
            """,
            (start_ts, end_ts),
        )
        row = cursor.fetchone()
        return int(row[0]) if row and row[0] is not None else 0

    def list_recent(self, limit: int = 10) -> list[YogaSessionRecord]:
        """Return recently recorded sessions ordered by start time descending."""
        cursor = self._connection.execute(
            """
            SELECT id, started_at, steps_completed, total_steps, duration_s
            FROM yoga_sessions
            ORDER BY started_at DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            YogaSessionRecord(
                id=row[0],
                started_at=row[1],
                steps_completed=row[2],
                total_steps=row[3],
                duration_s=row[4],
            )
            for row in cursor.fetchall()
        ]


@dataclass(frozen=True, slots=True)
class BlinkMinuteRecord:
    """Aggregated blink measurements stored for one minute."""

    minute_start: int
    blinks: int
    face_present_ratio: float
    ear_mean: float | None


class BlinkMetricsRepository:
    """Persist and query aggregated blink metrics without retaining camera data."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def record_minute(self, record: BlinkMinuteRecord) -> None:
        if record.minute_start < 0 or record.blinks < 0:
            raise ValueError("minute_start and blinks must be non-negative")
        if not 0.0 <= record.face_present_ratio <= 1.0:
            raise ValueError("face_present_ratio must be between zero and one")
        if record.ear_mean is not None and record.ear_mean < 0:
            raise ValueError("ear_mean must be non-negative")
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO blink_minutely (
                    minute_start, blinks, face_present_ratio, ear_mean
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(minute_start) DO UPDATE SET
                    blinks = excluded.blinks,
                    face_present_ratio = excluded.face_present_ratio,
                    ear_mean = excluded.ear_mean
                """,
                (
                    record.minute_start,
                    record.blinks,
                    record.face_present_ratio,
                    record.ear_mean,
                ),
            )

    def counts_for_range(self, start_ts: int, end_ts: int) -> tuple[int, int]:
        """Return (good-blink minutes, adequately monitored minutes) in [start, end)."""
        row = self._connection.execute(
            """
            SELECT
                SUM(CASE WHEN blinks >= 12 THEN 1 ELSE 0 END),
                COUNT(*)
            FROM blink_minutely
            WHERE minute_start >= ? AND minute_start < ?
              AND face_present_ratio >= 0.5
            """,
            (start_ts, end_ts),
        ).fetchone()
        return (int(row[0] or 0), int(row[1] or 0))

    def list_for_range(self, start_ts: int, end_ts: int) -> list[BlinkMinuteRecord]:
        rows = self._connection.execute(
            """
            SELECT minute_start, blinks, face_present_ratio, ear_mean
            FROM blink_minutely
            WHERE minute_start >= ? AND minute_start < ?
            ORDER BY minute_start
            """,
            (start_ts, end_ts),
        )
        return [
            BlinkMinuteRecord(
                minute_start=int(row[0]),
                blinks=int(row[1] or 0),
                face_present_ratio=float(row[2] or 0.0),
                ear_mean=float(row[3]) if row[3] is not None else None,
            )
            for row in rows
        ]


@dataclass(frozen=True, slots=True)
class DailyScoreRecord:
    day: str
    score: int
    break_c: float
    yoga_c: float
    screen_c: float
    blink_c: float
    counted_for_streak: int


class DailyScoresRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def save_score(self, record: DailyScoreRecord) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO daily_scores (
                    day, score, break_c, yoga_c, screen_c, blink_c, counted_for_streak
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(day) DO UPDATE SET
                    score = excluded.score,
                    break_c = excluded.break_c,
                    yoga_c = excluded.yoga_c,
                    screen_c = excluded.screen_c,
                    blink_c = excluded.blink_c,
                    counted_for_streak = excluded.counted_for_streak
                """,
                (
                    record.day,
                    record.score,
                    record.break_c,
                    record.yoga_c,
                    record.screen_c,
                    record.blink_c,
                    record.counted_for_streak,
                ),
            )

    def get_score(self, day: str) -> DailyScoreRecord | None:
        cursor = self._connection.execute(
            """
            SELECT day, score, break_c, yoga_c, screen_c, blink_c, counted_for_streak
            FROM daily_scores
            WHERE day = ?
            """,
            (day,),
        )
        row = cursor.fetchone()
        if not row:
            return None
        return DailyScoreRecord(
            day=str(row[0]),
            score=int(row[1]),
            break_c=float(row[2]),
            yoga_c=float(row[3]),
            screen_c=float(row[4]),
            blink_c=float(row[5]),
            counted_for_streak=int(row[6]),
        )

    def list_recent(self, limit: int = 30) -> list[DailyScoreRecord]:
        cursor = self._connection.execute(
            """
            SELECT day, score, break_c, yoga_c, screen_c, blink_c, counted_for_streak
            FROM daily_scores
            ORDER BY day DESC
            LIMIT ?
            """,
            (limit,),
        )
        return [
            DailyScoreRecord(
                day=str(row[0]),
                score=int(row[1]),
                break_c=float(row[2]),
                yoga_c=float(row[3]),
                screen_c=float(row[4]),
                blink_c=float(row[5]),
                counted_for_streak=int(row[6]),
            )
            for row in cursor.fetchall()
        ]


class StreaksRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def load(self) -> StreakState:
        cursor = self._connection.execute(
            "SELECT current, best, last_counted_day, freeze_week FROM streaks WHERE id = 1"
        )
        row = cursor.fetchone()
        if not row:
            return StreakState(
                current=0,
                best=0,
                last_counted_day=None,
                freeze_week=None,
            )
        return StreakState(
            current=int(row[0]),
            best=int(row[1]),
            last_counted_day=str(row[2]) if row[2] is not None else None,
            freeze_week=str(row[3]) if row[3] is not None else None,
        )

    def save(self, state: StreakState) -> None:
        with self._connection:
            self._connection.execute(
                """
                INSERT INTO streaks (id, current, best, last_counted_day, freeze_week)
                VALUES (1, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    current = excluded.current,
                    best = excluded.best,
                    last_counted_day = excluded.last_counted_day,
                    freeze_week = excluded.freeze_week
                """,
                (
                    state.current,
                    state.best,
                    state.last_counted_day,
                    state.freeze_week,
                ),
            )


class BadgesRepository:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def award_badge(self, code: str, earned_at: int) -> bool:
        with self._connection:
            cursor = self._connection.execute(
                "INSERT INTO badges (code, earned_at) VALUES (?, ?) ON CONFLICT(code) DO NOTHING",
                (code, earned_at),
            )
            return cursor.rowcount > 0

    def list_earned(self) -> list[tuple[str, int]]:
        cursor = self._connection.execute(
            "SELECT code, earned_at FROM badges ORDER BY earned_at ASC"
        )
        return [(str(row[0]), int(row[1])) for row in cursor.fetchall()]

    def earned_codes(self) -> set[str]:
        cursor = self._connection.execute("SELECT code FROM badges")
        return {str(row[0]) for row in cursor.fetchall()}
