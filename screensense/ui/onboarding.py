"""Present the first-run privacy and preference onboarding flow."""

from dataclasses import replace

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from screensense.storage.repositories import SettingsRepository


class OnboardingDialog(QDialog):
    """Three-step first-run welcome, local storage explanation, and consent flow."""

    def __init__(
        self,
        settings_repository: SettingsRepository,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._settings_repository = settings_repository
        self.setWindowTitle("Welcome to ScreenSense")
        self.setAccessibleName("ScreenSense onboarding")
        self.setMinimumSize(480, 360)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 20)
        layout.setSpacing(16)

        self._step_label = QLabel("Step 1 of 3", self)
        self._step_label.setObjectName("settingsSectionHeading")
        layout.addWidget(self._step_label)

        self._pages = QStackedWidget(self)
        self._pages.addWidget(
            self._page(
                "A calmer way to rest your eyes",
                "ScreenSense offers gentle reminders and guided Eye Yoga. "
                "You stay in control: reminders can be dismissed, and monitoring is optional.",
            )
        )
        self._pages.addWidget(
            self._page(
                "Your information stays on this device",
                "ScreenSense stores break and Eye Yoga activity, screen-time aggregates, "
                "your preferences, and optional per-minute blink estimates in a local "
                "SQLite database. Window titles and camera images are not stored. "
                "Local diagnostic logs are kept beside the database. You can export "
                "or clear history from the dashboard.",
            )
        )
        consent_page = self._page(
            "Choose whether to use blink monitoring",
            "Blink monitoring is off unless you choose it. If enabled, your webcam is "
            "processed on this device only. Frames are handled in memory and discarded; "
            "only per-minute estimates are saved. The tray shows when the camera is active "
            "and provides a stop control.",
        )
        self._blink_consent = QCheckBox(
            "I agree to enable optional webcam blink monitoring", consent_page
        )
        self._blink_consent.setAccessibleName("Consent to blink monitoring")
        consent_page.layout().addWidget(self._blink_consent)
        disclaimer = QLabel(
            "ScreenSense supports healthy screen habits. It is not a medical device "
            "and does not diagnose or treat any condition.",
            consent_page,
        )
        disclaimer.setWordWrap(True)
        disclaimer.setObjectName("settingsFieldLabel")
        consent_page.layout().addWidget(disclaimer)
        self._pages.addWidget(consent_page)
        layout.addWidget(self._pages, 1)

        controls = QHBoxLayout()
        self._back_button = QPushButton("Back", self)
        self._back_button.clicked.connect(self._previous_page)
        self._continue_button = QPushButton("Continue", self)
        self._continue_button.setObjectName("primaryActionButton")
        self._continue_button.clicked.connect(self._next_page)
        controls.addWidget(self._back_button)
        controls.addStretch()
        controls.addWidget(self._continue_button)
        layout.addLayout(controls)
        self._update_navigation()

    @staticmethod
    def _page(title: str, body: str) -> QWidget:
        page = QWidget()
        page_layout = QVBoxLayout(page)
        page_layout.setContentsMargins(0, 0, 0, 0)
        heading = QLabel(title, page)
        heading.setWordWrap(True)
        heading.setStyleSheet("font-size: 20px; font-weight: 600;")
        text = QLabel(body, page)
        text.setWordWrap(True)
        text.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        page_layout.addWidget(heading)
        page_layout.addWidget(text)
        page_layout.addStretch()
        return page

    def _next_page(self) -> None:
        if self._pages.currentIndex() < self._pages.count() - 1:
            self._pages.setCurrentIndex(self._pages.currentIndex() + 1)
            self._update_navigation()
            return
        settings = replace(
            self._settings_repository.load(),
            onboarding_completed=True,
            blink_monitor_enabled=self._blink_consent.isChecked(),
        )
        self._settings_repository.save(settings)
        self.accept()

    def _previous_page(self) -> None:
        if self._pages.currentIndex() > 0:
            self._pages.setCurrentIndex(self._pages.currentIndex() - 1)
            self._update_navigation()

    def _update_navigation(self) -> None:
        index = self._pages.currentIndex()
        self._step_label.setText(f"Step {index + 1} of {self._pages.count()}")
        self._back_button.setEnabled(index > 0)
        self._continue_button.setText(
            "Get started" if index == self._pages.count() - 1 else "Continue"
        )
