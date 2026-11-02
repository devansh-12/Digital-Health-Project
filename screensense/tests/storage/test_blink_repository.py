import json

from screensense.storage.db import open_database
from screensense.storage.export import clear_all_data, export_data_as_json
from screensense.storage.repositories import (
    BlinkMetricsRepository,
    BlinkMinuteRecord,
)


def test_blink_repository_stores_aggregates_and_filters_unmonitored_minutes(tmp_path) -> None:
    connection = open_database(tmp_path / "blink.sqlite3")
    try:
        repository = BlinkMetricsRepository(connection)
        repository.record_minute(BlinkMinuteRecord(120, 14, 0.9, 0.28))
        repository.record_minute(BlinkMinuteRecord(180, 8, 0.4, 0.24))
        repository.record_minute(BlinkMinuteRecord(240, 8, 0.8, 0.25))

        assert repository.counts_for_range(120, 240) == (1, 1)
        assert repository.list_for_range(120, 300) == [
            BlinkMinuteRecord(120, 14, 0.9, 0.28),
            BlinkMinuteRecord(180, 8, 0.4, 0.24),
            BlinkMinuteRecord(240, 8, 0.8, 0.25),
        ]
    finally:
        connection.close()


def test_blink_metrics_are_in_export_and_removed_by_delete_all(tmp_path) -> None:
    connection = open_database(tmp_path / "blink-export.sqlite3")
    try:
        BlinkMetricsRepository(connection).record_minute(
            BlinkMinuteRecord(120, 14, 0.9, 0.28)
        )

        exported = json.loads(export_data_as_json(connection))
        assert exported["blink_minutely"][0]["blinks"] == 14

        clear_all_data(connection)
        assert BlinkMetricsRepository(connection).list_for_range(0, 1000) == []
    finally:
        connection.close()
