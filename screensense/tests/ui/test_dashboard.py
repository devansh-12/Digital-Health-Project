"""Test dashboard trend controls and date ranges."""

import os
from datetime import datetime

import pytest
from PyQt6.QtWidgets import QApplication

from screensense.core.clock import FakeClock
from screensense.storage.db import open_database
from screensense.storage.repositories import (
    BadgesRepository,
    BreaksRepository,
    DailyScoresRepository,
    SettingsRepository,
    StreaksRepository,
    UsageHourlyRepository,
    YogaSessionsRepository,
)
from screensense.ui.dashboard.window import DashboardWindow


@pytest.fixture(scope="module")
def app() -> QApplication:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_dashboard_switches_between_seven_and_thirty_day_trends(
    app: QApplication, tmp_path
) -> None:
    database = open_database(tmp_path / "dashboard.sqlite3")
    try:
        window = DashboardWindow(
            database=database,
            settings_repo=SettingsRepository(database),
            breaks_repo=BreaksRepository(database),
            yoga_repo=YogaSessionsRepository(database),
            usage_repo=UsageHourlyRepository(database),
            scores_repo=DailyScoresRepository(database),
            streaks_repo=StreaksRepository(database),
            badges_repo=BadgesRepository(database),
            clock=FakeClock(wall_seconds=datetime(2026, 11, 6, 12).timestamp()),
        )

        assert len(window._trend_chart._data) == 7
        assert window._trend_summary.text().startswith("7-day average")

        window._trend_30_button.click()
        assert len(window._trend_chart._data) == 30
        assert window._trend_heading.text() == "30-day trend"
        assert window._trend_summary.text().startswith("30-day average")

        window._trend_7_button.click()
        assert len(window._trend_chart._data) == 7
        assert window._trend_heading.text() == "7-day trend"

        window.close()
    finally:
        database.close()


def test_dashboard_theme_switch_updates_widgets(
    app: QApplication, tmp_path
) -> None:
    database = open_database(tmp_path / "dashboard_theme.sqlite3")
    try:
        window = DashboardWindow(
            database=database,
            settings_repo=SettingsRepository(database),
            breaks_repo=BreaksRepository(database),
            yoga_repo=YogaSessionsRepository(database),
            usage_repo=UsageHourlyRepository(database),
            scores_repo=DailyScoresRepository(database),
            streaks_repo=StreaksRepository(database),
            badges_repo=BadgesRepository(database),
            clock=FakeClock(wall_seconds=datetime(2026, 11, 6, 12).timestamp()),
        )
        assert window._gauge._theme == "dark"
        assert window._timeline_widget._theme == "dark"
        assert window._trend_chart._theme == "dark"

        window.set_theme("light")
        assert window._gauge._theme == "light"
        assert window._timeline_widget._theme == "light"
        assert window._trend_chart._theme == "light"

        window.close()
    finally:
        database.close()
