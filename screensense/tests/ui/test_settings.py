"""Test keyboard-accessible work-hours and process-rule settings."""

import os

import pytest
from PyQt6.QtCore import QTime
from PyQt6.QtWidgets import QApplication

from screensense.core.context import ContextRule
from screensense.storage.db import open_database
from screensense.storage.repositories import ContextRulesRepository, SettingsRepository
from screensense.ui.settings import SettingsDialog


@pytest.fixture(scope="module")
def app() -> QApplication:
    """Create the Qt application needed by offscreen widget tests."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_settings_dialog_saves_schedule_and_process_rules(app, tmp_path) -> None:
    """Save selected weekdays, local hours, and one process-only rule."""
    connection = open_database(tmp_path / "settings-ui.sqlite3")
    try:
        settings_repo = SettingsRepository(connection)
        rules_repo = ContextRulesRepository(connection)
        dialog = SettingsDialog(settings_repo, rules_repo)
        for button in dialog.day_checks:
            button.setChecked(False)
        dialog.day_checks[0].setChecked(True)
        dialog.day_checks[4].setChecked(True)
        dialog.start_time.setTime(QTime(8, 30))
        dialog.end_time.setTime(QTime(17, 0))
        dialog.process_input.setText("VideoPlayer.exe")
        dialog.rule_choice.setCurrentIndex(
            dialog.rule_choice.findData(ContextRule.FULLSCREEN_OK)
        )
        dialog.add_rule_button.click()
        dialog.save_button.click()

        assert settings_repo.load().work_hours is not None
        assert settings_repo.load().work_hours.weekdays == frozenset({0, 4})
        assert rules_repo.load_all() == {
            "videoplayer.exe": ContextRule.FULLSCREEN_OK
        }
        dialog.close()
    finally:
        connection.close()
