import json
import sqlite3
from typing import Any


def export_data_as_json(connection: sqlite3.Connection) -> str:
    tables = [
        "settings",
        "usage_hourly",
        "breaks",
        "yoga_sessions",
        "blink_minutely",
        "daily_scores",
        "streaks",
        "badges",
        "context_rules",
    ]
    payload: dict[str, list[dict[str, Any]]] = {}

    for table in tables:
        cursor = connection.execute(f"SELECT * FROM {table}")
        columns = [description[0] for description in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
        payload[table] = rows

    return json.dumps(payload, indent=2, default=str)


def clear_all_data(connection: sqlite3.Connection) -> None:
    history_tables = [
        "usage_hourly",
        "breaks",
        "yoga_sessions",
        "daily_scores",
        "streaks",
        "badges",
        "blink_minutely",
    ]
    with connection:
        for table in history_tables:
            connection.execute(f"DELETE FROM {table}")
