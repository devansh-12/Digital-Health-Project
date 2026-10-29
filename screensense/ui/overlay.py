"""Display a dismissible, non-activating break reminder card."""

from math import ceil

from PyQt6.QtCore import QRectF, Qt, QTimer, pyqtSignal
from PyQt6.QtGui import (
    QCloseEvent,
    QColor,
    QKeyEvent,
    QKeySequence,
    QPainter,
    QPaintEvent,
    QPen,
    QShortcut,
    QShowEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from screensense.core.clock import Clock
from screensense.core.events import ShowPrompt
from screensense.ui.theme import MUTED, PRIMARY, TEXT


class CountdownRing(QWidget):
    """Paint a numeric countdown with a shrinking progress ring."""

    def __init__(self, total_seconds: float, parent: QWidget | None = None) -> None:
        """Create a countdown ring for a positive duration."""
        super().__init__(parent)
        if total_seconds <= 0:
            raise ValueError("total_seconds must be positive")
        self._total_seconds = total_seconds
        self._remaining_seconds = total_seconds
        self._last_announced_second = ceil(total_seconds)
        self.setObjectName("countdownRing")
        self.setAccessibleName("Break reminder countdown")
        self.setFixedSize(72, 72)
        self._update_accessible_description()

    @property
    def seconds_remaining(self) -> int:
        """Return the rounded-up number of seconds remaining."""
        return ceil(self._remaining_seconds)

    def set_remaining_seconds(self, seconds: float) -> None:
        """Update the countdown value and repaint the ring."""
        self._remaining_seconds = min(self._total_seconds, max(0.0, seconds))
        announced_second = self.seconds_remaining
        if announced_second != self._last_announced_second:
            self._last_announced_second = announced_second
            self._update_accessible_description()
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        """Paint the remaining arc and its centered number."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect = QRectF(7.0, 7.0, self.width() - 14.0, self.height() - 14.0)

        painter.setPen(QPen(QColor(MUTED), 5.0))
        painter.drawEllipse(rect)

        fraction = self._remaining_seconds / self._total_seconds
        progress_pen = QPen(QColor(PRIMARY), 5.0)
        progress_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(progress_pen)
        painter.drawArc(rect, 90 * 16, -round(360 * 16 * fraction))

        painter.setPen(QColor(TEXT))
        painter.drawText(
            self.rect(),
            Qt.AlignmentFlag.AlignCenter,
            str(self.seconds_remaining),
        )
        painter.end()

    def _update_accessible_description(self) -> None:
        """Announce the remaining time as text for assistive technology."""
        self.setAccessibleDescription(f"{self.seconds_remaining} seconds remaining")


class BreakOverlay(QWidget):
    """Show the four break actions without activating or focusing on show."""

    COUNTDOWN_SECONDS = 20.0

    eye_yoga_requested = pyqtSignal()
    quick_break_requested = pyqtSignal()
    snooze_requested = pyqtSignal()
    skip_requested = pyqtSignal()
    dismissed = pyqtSignal()
    always_allow_here_requested = pyqtSignal(str)

    def __init__(self, clock: Clock, parent: QWidget | None = None) -> None:
        """Create a frameless, always-on-top reminder card using an injected clock."""
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        super().__init__(parent, flags)
        self._clock = clock
        self._countdown_started_at: float | None = None
        self._current_process = ""
        self.setObjectName("breakOverlay")
        self.setAccessibleName("ScreenSense break reminder")
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedWidth(392)

        self._build_layout()
        self._connect_actions()
        self._escape_shortcut = QShortcut(QKeySequence("Esc"), self)
        self._escape_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._escape_shortcut.activated.connect(self._dismiss)
        self._countdown_timer = QTimer(self)
        self._countdown_timer.setInterval(100)
        self._countdown_timer.timeout.connect(self.refresh_countdown)

    def _build_layout(self) -> None:
        """Create the prompt heading, countdown, and four actions."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        heading = QHBoxLayout()
        heading.setSpacing(16)
        self.prompt_label = QLabel("Time to rest your eyes 👀", self)
        self.prompt_label.setObjectName("promptTitle")
        self.prompt_label.setWordWrap(True)
        heading.addWidget(self.prompt_label, 1)

        self.countdown_ring = CountdownRing(self.COUNTDOWN_SECONDS, self)
        heading.addWidget(self.countdown_ring)
        layout.addLayout(heading)

        buttons = QGridLayout()
        buttons.setHorizontalSpacing(12)
        buttons.setVerticalSpacing(12)

        self.eye_yoga_button = QPushButton("Eye Yoga (60s)", self)
        self.eye_yoga_button.setObjectName("eyeYogaButton")
        self.quick_break_button = QPushButton("Quick break (20s)", self)
        self.snooze_button = QPushButton("Snooze 5 min", self)
        self.skip_button = QPushButton("Skip", self)

        buttons.addWidget(self.eye_yoga_button, 0, 0)
        buttons.addWidget(self.quick_break_button, 0, 1)
        buttons.addWidget(self.snooze_button, 1, 0)
        buttons.addWidget(self.skip_button, 1, 1)
        layout.addLayout(buttons)

        context_actions = QHBoxLayout()
        self.not_now_button = QPushButton("Not now", self)
        self.always_allow_button = QPushButton("Always allow here", self)
        self.always_allow_button.setEnabled(False)
        self.always_allow_button.setAccessibleDescription(
            "Allow reminders for this process name"
        )
        context_actions.addWidget(self.not_now_button)
        context_actions.addWidget(self.always_allow_button)
        layout.addLayout(context_actions)

    def _connect_actions(self) -> None:
        """Connect each button to its action signal and close the card."""
        self.eye_yoga_button.clicked.connect(self._request_eye_yoga)
        self.quick_break_button.clicked.connect(self._request_quick_break)
        self.snooze_button.clicked.connect(self._request_snooze)
        self.skip_button.clicked.connect(self._request_skip)
        self.not_now_button.clicked.connect(self._dismiss)
        self.always_allow_button.clicked.connect(self._allow_current_process)

    def set_current_process(self, process: str | None) -> None:
        """Set the in-memory executable name used by the allow action."""
        normalized = (process or "").strip().casefold()
        if any(separator in normalized for separator in ("/", "\\")):
            normalized = ""
        self._current_process = normalized
        self.always_allow_button.setEnabled(bool(normalized))

    def show_prompt(self, event: ShowPrompt | None = None) -> None:
        """Reset the 20-second countdown and show the prompt without activation."""
        self.prompt_label.setText(
            event.message
            if event is not None and event.message is not None
            else "Time to rest your eyes 👀"
        )
        self._start_countdown()
        self.show()

    def refresh_countdown(self) -> None:
        """Refresh the ring from monotonic time without dismissing at zero."""
        if self._countdown_started_at is None:
            return
        elapsed = max(0.0, self._clock.monotonic() - self._countdown_started_at)
        remaining = max(0.0, self.COUNTDOWN_SECONDS - elapsed)
        self.countdown_ring.set_remaining_seconds(remaining)
        if remaining == 0.0:
            self._countdown_timer.stop()

    def showEvent(self, event: QShowEvent) -> None:
        """Position the card at the lower-right of the current screen."""
        self.adjustSize()
        screen = self.screen() or QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            margin = 24
            self.move(
                area.right() - self.width() - margin + 1,
                area.bottom() - self.height() - margin + 1,
            )
        if self._countdown_started_at is None:
            self._start_countdown()
        super().showEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Dismiss the card when Escape is pressed while it is active."""
        if event.key() == Qt.Key.Key_Escape:
            self._dismiss()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Stop countdown updates when the card closes."""
        self._countdown_timer.stop()
        self._countdown_started_at = None
        super().closeEvent(event)

    def _start_countdown(self) -> None:
        """Start a fresh countdown from the injected monotonic clock."""
        self._countdown_started_at = self._clock.monotonic()
        self.countdown_ring.set_remaining_seconds(self.COUNTDOWN_SECONDS)
        self._countdown_timer.start()

    def _dismiss(self) -> None:
        """Emit dismissal and close the card."""
        self.dismissed.emit()
        self.close()

    def _request_eye_yoga(self) -> None:
        """Emit the Eye Yoga action and close the card."""
        self.eye_yoga_requested.emit()
        self.close()

    def _request_quick_break(self) -> None:
        """Emit the quick-break action and close the card."""
        self.quick_break_requested.emit()
        self.close()

    def _request_snooze(self) -> None:
        """Emit the snooze action and close the card."""
        self.snooze_requested.emit()
        self.close()

    def _request_skip(self) -> None:
        """Emit the skip action and close the card."""
        self.skip_requested.emit()
        self.close()

    def _allow_current_process(self) -> None:
        """Request a process-name allow rule without retaining window metadata."""
        if self._current_process:
            self.always_allow_here_requested.emit(self._current_process)
        self.close()
