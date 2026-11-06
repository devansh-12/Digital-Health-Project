"""Test keyboard-accessible work-hours and process-rule settings."""

import os
from dataclasses import replace

import pytest
from PyQt6.QtCore import QTime
from PyQt6.QtWidgets import QApplication, QMessageBox

from screensense.core.context import ContextRule
from screensense.platform_adapters.stub import StubAutostartProvider
from screensense.storage.db import open_database
from screensense.storage.repositories import ContextRulesRepository, SettingsRepository
from screensense.ui.onboarding import OnboardingDialog
from screensense.ui.settings import SettingsDialog
from screensense.ui.theme import load_stylesheet


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
        dialog.work_interval.setValue(30)
        dialog.break_duration.setValue(45)
        dialog.long_break_duration.setValue(8)
        dialog.long_break_every.setValue(4)
        dialog.snooze_duration.setValue(8)
        dialog.snooze_limit.setValue(3)
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
        assert settings_repo.load().work_interval_minutes == 30
        assert settings_repo.load().quick_break_seconds == 45
        assert settings_repo.load().long_break_minutes == 8
        assert settings_repo.load().long_break_every == 4
        assert settings_repo.load().snooze_minutes == 8
        assert settings_repo.load().snooze_limit_per_session == 3
        assert rules_repo.load_all() == {"videoplayer.exe": ContextRule.FULLSCREEN_OK}
        dialog.close()
    finally:
        connection.close()


def test_settings_requires_consent_before_enabling_blink_monitoring(
    app, tmp_path, monkeypatch
) -> None:
    connection = open_database(tmp_path / "blink-consent.sqlite3")
    try:
        settings_repo = SettingsRepository(connection)
        dialog = SettingsDialog(settings_repo, ContextRulesRepository(connection))
        dialog.blink_monitor_checkbox.setChecked(True)
        monkeypatch.setattr(
            QMessageBox,
            "question",
            lambda *args, **kwargs: QMessageBox.StandardButton.Yes,
        )

        dialog.save_button.click()

        assert settings_repo.load().blink_monitor_enabled is True
        dialog.close()
    finally:
        connection.close()


def test_onboarding_completes_three_steps_and_persists_camera_consent(
    app, tmp_path
) -> None:
    connection = open_database(tmp_path / "onboarding.sqlite3")
    try:
        settings_repo = SettingsRepository(connection)
        dialog = OnboardingDialog(settings_repo)
        assert dialog._pages.count() == 3
        dialog._continue_button.click()
        dialog._continue_button.click()
        dialog._blink_consent.setChecked(True)
        dialog._continue_button.click()

        settings = settings_repo.load()
        assert settings.onboarding_completed
        assert settings.blink_monitor_enabled
    finally:
        connection.close()


def test_settings_persist_theme_accessibility_and_autostart_preferences(
    app, tmp_path
) -> None:
    connection = open_database(tmp_path / "preferences.sqlite3")
    try:
        provider = StubAutostartProvider()
        settings_repo = SettingsRepository(connection)
        dialog = SettingsDialog(
            settings_repo,
            ContextRulesRepository(connection),
            autostart_provider=provider,
        )
        dialog.theme_choice.setCurrentIndex(dialog.theme_choice.findData("light"))
        dialog.reduced_motion_checkbox.setChecked(True)
        dialog.autostart_checkbox.setChecked(True)
        dialog.save_button.click()

        settings = settings_repo.load()
        assert settings.ui_theme == "light"
        assert settings.reduced_motion
        assert provider.is_enabled()
        dialog.close()
    finally:
        connection.close()


def test_timing_controls_load_saved_values(app, tmp_path) -> None:
    connection = open_database(tmp_path / "timing-controls.sqlite3")
    try:
        settings_repo = SettingsRepository(connection)
        settings_repo.save(
            replace(
                settings_repo.load(),
                work_interval_minutes=35,
                quick_break_seconds=40,
                long_break_minutes=12,
                long_break_every=5,
                snooze_minutes=7,
            )
        )
        dialog = SettingsDialog(settings_repo, ContextRulesRepository(connection))

        assert dialog.work_interval.value() == 35
        assert dialog.break_duration.value() == 40
        assert dialog.long_break_duration.value() == 12
        assert dialog.long_break_every.value() == 5
        assert dialog.snooze_duration.value() == 7
        dialog.close()
    finally:
        connection.close()


def test_light_and_dark_stylesheets_are_available() -> None:
    assert "background-color: #1e1e1e" in load_stylesheet("dark")
    assert "background-color: #F7FAF9" in load_stylesheet("light")


def test_theme_loader_rejects_unknown_theme() -> None:
    with pytest.raises(ValueError, match="Unsupported theme"):
        load_stylesheet("sepia")
