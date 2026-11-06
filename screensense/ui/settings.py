"""Display and edit work-hour and per-process context settings."""

from dataclasses import replace

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from screensense.core.config import WorkHours
from screensense.core.context import ContextRule
from screensense.platform_adapters.base import AutostartProvider
from screensense.storage.repositories import ContextRulesRepository, SettingsRepository


class SettingsDialog(QDialog):
    """Edit the local work schedule and process context rules."""

    settings_saved = pyqtSignal(object)

    def __init__(
        self,
        settings_repository: SettingsRepository,
        rules_repository: ContextRulesRepository,
        parent: QWidget | None = None,
        autostart_provider: AutostartProvider | None = None,
    ) -> None:
        """Build a keyboard-operable editor backed by local repositories."""
        super().__init__(parent)
        self._settings_repository = settings_repository
        self._rules_repository = rules_repository
        self._autostart_provider = autostart_provider
        self.setWindowTitle("ScreenSense settings")
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        """Create schedule controls, rule list, and inline validation."""
        self.setObjectName("settingsDialog")
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        scroll_area = QScrollArea(self)
        scroll_area.setObjectName("settingsScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.viewport().setObjectName("settingsViewport")
        content = QWidget(scroll_area)
        content.setObjectName("settingsContent")
        content.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout = QVBoxLayout(content)
        layout.setContentsMargins(22, 22, 22, 22)
        layout.setSpacing(12)
        self.setAccessibleName("ScreenSense settings")
        self.setMinimumSize(440, 520)
        timing_label = QLabel("Break timing", self)
        timing_label.setObjectName("settingsSectionHeading")
        layout.addWidget(timing_label)
        timing_fields = QHBoxLayout()
        timing_fields.setSpacing(10)

        self.work_interval = QSpinBox(self)
        self.work_interval.setRange(10, 60)
        self.work_interval.setSuffix(" min")
        self.work_interval.setAccessibleName("Work interval in minutes")
        self.break_duration = QSpinBox(self)
        self.break_duration.setRange(10, 60)
        self.break_duration.setSuffix(" sec")
        self.break_duration.setAccessibleName("Quick break duration in seconds")
        self.snooze_duration = QSpinBox(self)
        self.snooze_duration.setRange(1, 60)
        self.snooze_duration.setSuffix(" min")
        self.snooze_duration.setAccessibleName("Snooze duration in minutes")
        self.long_break_duration = QSpinBox(self)
        self.long_break_duration.setRange(1, 120)
        self.long_break_duration.setSuffix(" min")
        self.long_break_duration.setAccessibleName("Long break duration in minutes")
        self.long_break_every = QSpinBox(self)
        self.long_break_every.setRange(1, 20)
        self.long_break_every.setSuffix(" breaks")
        self.long_break_every.setAccessibleName("Long break frequency")
        self.snooze_limit = QSpinBox(self)
        self.snooze_limit.setRange(0, 20)
        self.snooze_limit.setSpecialValueText("Unlimited")
        self.snooze_limit.setAccessibleName("Max snoozes per break interval (0 = unlimited)")
        timing_groups = (
            (
                ("Work interval", self.work_interval),
                ("Quick break", self.break_duration),
                ("Snooze", self.snooze_duration),
            ),
            (
                ("Long break", self.long_break_duration),
                ("Long break every", self.long_break_every),
                ("Max snoozes", self.snooze_limit),
            ),
        )
        for group in timing_groups:
            row = QHBoxLayout()
            row.setSpacing(10)
            for label, control in group:
                field = QVBoxLayout()
                lbl = QLabel(label, self)
                lbl.setObjectName("settingsFieldLabel")
                field.addWidget(lbl)
                field.addWidget(control)
                row.addLayout(field)
            layout.addLayout(row)

        self.day_checks: list[QPushButton] = []
        days = QHBoxLayout()
        days.setSpacing(6)
        for day, label in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
            button = QPushButton(label, self)
            button.setCheckable(True)
            button.setObjectName("dayCheckButton")
            button.setAccessibleName(f"Work day {label}")
            self.day_checks.append(button)
            days.addWidget(button)
        work_days_label = QLabel("Work days", self)
        work_days_label.setObjectName("settingsSectionHeading")
        layout.addWidget(work_days_label)
        layout.addLayout(days)

        times = QHBoxLayout()
        times.setSpacing(10)
        self.start_time = QTimeEdit(self)
        self.start_time.setDisplayFormat("HH:mm")
        self.start_time.setAccelerated(True)
        self.start_time.setAccessibleName("Work starts")
        self.end_time = QTimeEdit(self)
        self.end_time.setDisplayFormat("HH:mm")
        self.end_time.setAccelerated(True)
        self.end_time.setAccessibleName("Work ends")
        start_label = QLabel("Start", self)
        start_label.setObjectName("settingsFieldLabel")
        times.addWidget(start_label)
        times.addWidget(self.start_time)
        end_label = QLabel("End", self)
        end_label.setObjectName("settingsFieldLabel")
        times.addWidget(end_label)
        times.addWidget(self.end_time)
        layout.addLayout(times)

        self.process_input = QLineEdit(self)
        self.process_input.setPlaceholderText("Process name, such as editor.exe")
        self.process_input.setAccessibleName("Process name")
        self.rule_choice = QComboBox(self)
        for rule in ContextRule:
            self.rule_choice.addItem(rule.value.replace("_", " ").title(), rule)
        self.add_rule_button = QPushButton("Add rule", self)
        self.add_rule_button.setObjectName("secondaryActionButton")
        self.remove_rule_button = QPushButton("Remove selected", self)
        self.remove_rule_button.setObjectName("secondaryActionButton")
        self.rule_list = QListWidget(self)
        self.rule_list.setAccessibleName("Process context rules")
        self.blink_monitor_checkbox = QCheckBox(
            "Enable optional blink monitoring (webcam)", self
        )
        self.blink_monitor_checkbox.setAccessibleName("Enable blink monitoring")
        self.blink_privacy_label = QLabel(
            "Uses your camera on this device only. Frames are processed in memory; "
            "only per-minute blink estimates are saved. You can stop it from the tray.",
            self,
        )
        self.blink_privacy_label.setWordWrap(True)
        self.blink_privacy_label.setObjectName("settingsFieldLabel")
        self.theme_choice = QComboBox(self)
        self.theme_choice.addItem("Dark theme", "dark")
        self.theme_choice.addItem("Light theme", "light")
        self.theme_choice.setAccessibleName("Application theme")
        self.reduced_motion_checkbox = QCheckBox("Reduce motion", self)
        self.reduced_motion_checkbox.setAccessibleName("Reduce motion")
        self.autostart_checkbox = QCheckBox("Start ScreenSense when I sign in", self)
        self.autostart_checkbox.setAccessibleName("Start ScreenSense automatically")
        self.autostart_checkbox.setEnabled(self._autostart_provider is not None)
        self.autostart_help = QLabel(
            "Autostart is available on supported Windows and Linux desktops.", self
        )
        self.autostart_help.setWordWrap(True)
        self.autostart_help.setObjectName("settingsFieldLabel")
        self.validation_label = QLabel("", self)
        self.validation_label.setObjectName("validationMessage")
        self.validation_label.setAccessibleName("Settings validation message")
        self.validation_label.setWordWrap(True)
        self.save_button = QPushButton("Save", self)
        self.save_button.setObjectName("primaryActionButton")
        self.cancel_button = QPushButton("Close", self)
        self.cancel_button.setObjectName("secondaryActionButton")
        app_rules_label = QLabel("App rules", self)
        app_rules_label.setObjectName("settingsSectionHeading")
        layout.addWidget(app_rules_label)
        layout.addWidget(self.process_input)
        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(self.rule_choice, 1)
        row.addWidget(self.add_rule_button)
        row.addWidget(self.remove_rule_button)
        layout.addLayout(row)
        layout.addWidget(self.rule_list)
        layout.addWidget(self.blink_monitor_checkbox)
        layout.addWidget(self.blink_privacy_label)
        appearance_label = QLabel("Appearance", self)
        appearance_label.setObjectName("settingsSectionHeading")
        layout.addWidget(appearance_label)
        layout.addWidget(self.theme_choice)
        layout.addWidget(self.reduced_motion_checkbox)
        layout.addWidget(self.autostart_checkbox)
        layout.addWidget(self.autostart_help)
        layout.addWidget(self.validation_label)
        scroll_area.setWidget(content)
        root_layout.addWidget(scroll_area, 1)
        footer = QHBoxLayout()
        footer.setSpacing(10)
        footer.setContentsMargins(22, 10, 22, 16)
        footer.addStretch(1)
        footer.addWidget(self.cancel_button)
        footer.addWidget(self.save_button)
        root_layout.addLayout(footer)
        self.add_rule_button.clicked.connect(self._add_rule)
        self.remove_rule_button.clicked.connect(self._remove_rule)
        self.save_button.clicked.connect(self._save)
        self.cancel_button.clicked.connect(self.close)

    def _load_values(self) -> None:
        """Populate controls from the current local settings and process rules."""
        settings = self._settings_repository.load()
        self.work_interval.setValue(settings.work_interval_minutes)
        self.break_duration.setValue(settings.quick_break_seconds)
        self.long_break_duration.setValue(settings.long_break_minutes)
        self.long_break_every.setValue(settings.long_break_every)
        self.snooze_duration.setValue(settings.snooze_minutes)
        self.snooze_limit.setValue(settings.snooze_limit_per_session)
        self.blink_monitor_checkbox.setChecked(settings.blink_monitor_enabled)
        self.theme_choice.setCurrentIndex(
            max(0, self.theme_choice.findData(settings.ui_theme))
        )
        self.reduced_motion_checkbox.setChecked(settings.reduced_motion)
        if self._autostart_provider is not None:
            self.autostart_checkbox.setChecked(self._autostart_provider.is_enabled())
        schedule = settings.work_hours
        for index, button in enumerate(self.day_checks):
            button.setChecked(schedule is not None and index in schedule.weekdays)
        if schedule is not None:
            self.start_time.setTime(
                self.start_time.time().fromString(
                    schedule.start.strftime("%H:%M"), "HH:mm"
                )
            )
            self.end_time.setTime(
                self.end_time.time().fromString(schedule.end.strftime("%H:%M"), "HH:mm")
            )
        for process, rule in self._rules_repository.load_all().items():
            self._append_rule(process, rule)

    def _append_rule(self, process: str, rule: ContextRule) -> None:
        """Add a normalized process name and rule to the visible list."""
        item = QListWidgetItem(f"{process} — {rule.value.replace('_', ' ')}")
        item.setData(Qt.ItemDataRole.UserRole, (process, rule.value))
        self.rule_list.addItem(item)

    def _add_rule(self) -> None:
        """Validate and display one process-only rule."""
        process = self.process_input.text().strip().casefold()
        if not process or any(separator in process for separator in ("/", "\\")):
            self.validation_label.setText(
                "Enter a process name only, such as editor.exe."
            )
            return
        if any(
            self.rule_list.item(i).data(Qt.ItemDataRole.UserRole)[0] == process
            for i in range(self.rule_list.count())
        ):
            self.validation_label.setText("That process already has a rule.")
            return
        self._append_rule(process, self.rule_choice.currentData())
        self.process_input.clear()
        self.validation_label.clear()

    def _remove_rule(self) -> None:
        """Remove the selected process rule from the pending settings list."""
        row = self.rule_list.currentRow()
        if row >= 0:
            self.rule_list.takeItem(row)

    def _save(self) -> None:
        """Validate and save work hours and all listed process rules."""
        days = frozenset(
            index for index, button in enumerate(self.day_checks) if button.isChecked()
        )
        start = self.start_time.time().toPyTime()
        end = self.end_time.time().toPyTime()
        if bool(days) != (start < end):
            self.validation_label.setText(
                "Choose at least one day and an end time after the start."
            )
            return
        current = self._settings_repository.load()
        blink_enabled = self.blink_monitor_checkbox.isChecked()
        if blink_enabled and not current.blink_monitor_enabled:
            answer = QMessageBox.question(
                self,
                "Enable blink monitoring?",
                "Blink monitoring uses your webcam on this device only. "
                "No video or images are saved or sent anywhere. "
                "Only per-minute blink estimates are stored. Enable it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer is not QMessageBox.StandardButton.Yes:
                self.blink_monitor_checkbox.setChecked(False)
                return
        schedule = WorkHours(start, end, days) if days else None
        updated_settings = replace(
            current,
            work_interval_minutes=self.work_interval.value(),
            quick_break_seconds=self.break_duration.value(),
            long_break_minutes=self.long_break_duration.value(),
            long_break_every=self.long_break_every.value(),
            snooze_minutes=self.snooze_duration.value(),
            snooze_limit_per_session=self.snooze_limit.value(),
            work_hours=schedule,
            blink_monitor_enabled=blink_enabled,
            ui_theme=str(self.theme_choice.currentData()),
            reduced_motion=self.reduced_motion_checkbox.isChecked(),
        )
        if self._autostart_provider is not None:
            try:
                if self.autostart_checkbox.isChecked():
                    self._autostart_provider.enable()
                else:
                    self._autostart_provider.disable()
            except OSError as error:
                self.validation_label.setText(f"Could not update autostart: {error}")
                return
        self._settings_repository.save(updated_settings)
        desired = {
            str(self.rule_list.item(i).data(Qt.ItemDataRole.UserRole)[0]): ContextRule(
                str(self.rule_list.item(i).data(Qt.ItemDataRole.UserRole)[1])
            )
            for i in range(self.rule_list.count())
        }
        for process in self._rules_repository.load_all():
            if process not in desired:
                self._rules_repository.delete_rule(process)
        for process, rule in desired.items():
            self._rules_repository.set_rule(process, rule)
        self.settings_saved.emit(updated_settings)
        self.accept()

    def set_blink_monitor_enabled(self, enabled: bool) -> None:
        """Synchronize the visible consent toggle after a tray stop command."""
        self.blink_monitor_checkbox.setChecked(enabled)

    def set_theme(self, theme: str) -> None:
        """Synchronize the selected theme after a settings change elsewhere."""
        index = self.theme_choice.findData(theme)
        if index < 0:
            raise ValueError(f"Unsupported theme: {theme}")
        self.theme_choice.setCurrentIndex(index)
