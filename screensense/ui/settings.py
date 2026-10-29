"""Display and edit work-hour and per-process context settings."""

from dataclasses import replace

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from screensense.core.config import WorkHours
from screensense.core.context import ContextRule
from screensense.storage.repositories import ContextRulesRepository, SettingsRepository


class SettingsDialog(QDialog):
    """Edit the local work schedule and process context rules."""

    settings_saved = pyqtSignal(object)

    def __init__(
        self,
        settings_repository: SettingsRepository,
        rules_repository: ContextRulesRepository,
        parent: QWidget | None = None,
    ) -> None:
        """Build a keyboard-operable editor backed by local repositories."""
        super().__init__(parent)
        self._settings_repository = settings_repository
        self._rules_repository = rules_repository
        self.setWindowTitle("ScreenSense settings")
        self._build_ui()
        self._load_values()

    def _build_ui(self) -> None:
        """Create schedule controls, rule list, and inline validation."""
        layout = QVBoxLayout(self)
        self.setAccessibleName("ScreenSense settings")
        self.day_checks: list[QPushButton] = []
        days = QHBoxLayout()
        for day, label in enumerate(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")):
            button = QPushButton(label, self)
            button.setCheckable(True)
            button.setAccessibleName(f"Work day {label}")
            self.day_checks.append(button)
            days.addWidget(button)
        layout.addWidget(QLabel("Work days", self))
        layout.addLayout(days)

        times = QHBoxLayout()
        self.start_time = QTimeEdit(self)
        self.start_time.setDisplayFormat("HH:mm")
        self.start_time.setAccessibleName("Work starts")
        self.end_time = QTimeEdit(self)
        self.end_time.setDisplayFormat("HH:mm")
        self.end_time.setAccessibleName("Work ends")
        times.addWidget(QLabel("Start", self))
        times.addWidget(self.start_time)
        times.addWidget(QLabel("End", self))
        times.addWidget(self.end_time)
        layout.addLayout(times)

        self.process_input = QLineEdit(self)
        self.process_input.setPlaceholderText("Process name, such as editor.exe")
        self.process_input.setAccessibleName("Process name")
        self.rule_choice = QComboBox(self)
        for rule in ContextRule:
            self.rule_choice.addItem(rule.value.replace("_", " ").title(), rule)
        self.add_rule_button = QPushButton("Add rule", self)
        self.remove_rule_button = QPushButton("Remove selected", self)
        self.rule_list = QListWidget(self)
        self.rule_list.setAccessibleName("Process context rules")
        self.validation_label = QLabel("", self)
        self.validation_label.setAccessibleName("Settings validation message")
        self.validation_label.setWordWrap(True)
        self.save_button = QPushButton("Save", self)
        self.cancel_button = QPushButton("Close", self)
        layout.addWidget(QLabel("App rules", self))
        layout.addWidget(self.process_input)
        row = QHBoxLayout()
        row.addWidget(self.rule_choice)
        row.addWidget(self.add_rule_button)
        row.addWidget(self.remove_rule_button)
        layout.addLayout(row)
        layout.addWidget(self.rule_list)
        layout.addWidget(self.validation_label)
        footer = QHBoxLayout()
        footer.addStretch(1)
        footer.addWidget(self.cancel_button)
        footer.addWidget(self.save_button)
        layout.addLayout(footer)
        self.add_rule_button.clicked.connect(self._add_rule)
        self.remove_rule_button.clicked.connect(self._remove_rule)
        self.save_button.clicked.connect(self._save)
        self.cancel_button.clicked.connect(self.close)

    def _load_values(self) -> None:
        """Populate controls from the current local settings and process rules."""
        settings = self._settings_repository.load()
        schedule = settings.work_hours
        for index, button in enumerate(self.day_checks):
            button.setChecked(schedule is not None and index in schedule.weekdays)
        if schedule is not None:
            self.start_time.setTime(self.start_time.time().fromString(schedule.start.strftime("%H:%M"), "HH:mm"))
            self.end_time.setTime(self.end_time.time().fromString(schedule.end.strftime("%H:%M"), "HH:mm"))
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
            self.validation_label.setText("Enter a process name only, such as editor.exe.")
            return
        if any(self.rule_list.item(i).data(Qt.ItemDataRole.UserRole)[0] == process for i in range(self.rule_list.count())):
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
        days = frozenset(index for index, button in enumerate(self.day_checks) if button.isChecked())
        start = self.start_time.time().toPyTime()
        end = self.end_time.time().toPyTime()
        if bool(days) != (start < end):
            self.validation_label.setText("Choose at least one day and an end time after the start.")
            return
        current = self._settings_repository.load()
        schedule = WorkHours(start, end, days) if days else None
        updated_settings = replace(current, work_hours=schedule)
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

