"""Test YogaSessionsRepository persistence with SQLite."""

from screensense.storage.db import open_database
from screensense.storage.repositories import YogaSessionsRepository


def test_yoga_sessions_repository(tmp_path) -> None:
    """Verify recording and querying yoga sessions."""
    db_path = tmp_path / "test_yoga.sqlite3"
    conn = open_database(db_path)
    try:
        repo = YogaSessionsRepository(conn)

        # Initially 0
        assert repo.count_today(1000) == 0

        # Record a full session
        session_id_1 = repo.record_session(
            started_at=1050,
            steps_completed=6,
            total_steps=6,
            duration_s=60,
        )
        assert session_id_1 == 1

        # Record a partial session (exited at step 3)
        session_id_2 = repo.record_session(
            started_at=2000,
            steps_completed=3,
            total_steps=6,
            duration_s=30,
        )
        assert session_id_2 == 2

        # count_today only counts completed sessions
        assert repo.count_today(1000) == 1
        assert repo.count_today(1100) == 0

        # list_recent
        recent = repo.list_recent()
        assert len(recent) == 2
        assert recent[0].id == 2  # most recent first
        assert recent[1].id == 1
        assert recent[0].steps_completed == 3
        assert recent[1].steps_completed == 6
    finally:
        conn.close()
