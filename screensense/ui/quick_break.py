"""Present a short, timed eye-rest break."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QKeyEvent
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from screensense.core.clock import Clock
from screensense.core.events import BreakKind
from screensense.ui.overlay import CountdownRing


class QuickBreakDialog(QDialog):
    """Run a dismissible countdown and report whether the break was completed."""

    session_completed = pyqtSignal(int)
    session_exited = pyqtSignal()

    def __init__(self, clock: Clock, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._clock = clock
        self._duration_s = 0
        self._started_at = 0.0
        self._active = False
        self._title_label: QLabel

        self.setWindowTitle("ScreenSense — Quick break")
        self.setAccessibleName("ScreenSense quick break")
        self.setMinimumSize(360, 300)
        self.setWindowModality(Qt.WindowModality.NonModal)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        self._title_label = QLabel("Rest your eyes", self)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet("font-size: 22px; font-weight: 600;")
        layout.addWidget(self._title_label)

        instruction = QLabel(
            "Look at something in the distance and let your eyes relax.",
            self,
        )
        instruction.setWordWrap(True)
        instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(instruction)

        ring_row = QHBoxLayout()
        ring_row.addStretch()
        self.countdown_ring = CountdownRing(20.0, self)
        ring_row.addWidget(self.countdown_ring)
        ring_row.addStretch()
        layout.addLayout(ring_row)

        self.end_button = QPushButton("End break", self)
        self.end_button.setAccessibleName("End quick break")
        self.end_button.clicked.connect(self._cancel)
        layout.addWidget(self.end_button)

        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._on_tick)

    def start(self, duration_s: int, kind: BreakKind = "quick") -> None:
        """Start the countdown for a validated break duration."""
        if isinstance(duration_s, bool) or not isinstance(duration_s, int):
            raise TypeError("duration_s must be an integer")
        if duration_s < 1:
            raise ValueError("duration_s must be positive")
        if kind not in {"quick", "long"}:
            raise ValueError("A timed rest break must be quick or long")
        self._duration_s = duration_s
        self._started_at = self._clock.monotonic()
        self._active = True
        self._title_label.setText("Take a longer break" if kind == "long" else "Rest your eyes")
        self.countdown_ring.reset(float(duration_s))
        self.show()
        self.raise_()
        self._timer.start()

    def _on_tick(self) -> None:
        if not self._active:
            return
        elapsed = max(0.0, self._clock.monotonic() - self._started_at)
        remaining = max(0.0, self._duration_s - elapsed)
        self.countdown_ring.set_remaining_seconds(remaining)
        if remaining == 0:
            self._active = False
            self._timer.stop()
            self.session_completed.emit(self._duration_s)
            self.accept()

    def _cancel(self) -> None:
        self._timer.stop()
        if self._active:
            self._active = False
            self.session_exited.emit()
        self.reject()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self._cancel()
            event.accept()
            return
        super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        self._timer.stop()
        if self._active:
            self._active = False
            self.session_exited.emit()
        super().closeEvent(event)
