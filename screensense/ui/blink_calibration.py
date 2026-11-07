"""Frameless floating card showing webcam baseline calibration progress."""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)


class BlinkCalibrationCard(QWidget):
    """Non-blocking floating card displayed while the vision worker calibrates."""

    CALIBRATION_SECONDS = 10.0

    def __init__(self, parent: QWidget | None = None) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        super().__init__(parent, flags)
        self.setObjectName("blinkCalibrationCard")
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(320)

        self._elapsed = 0.0
        self._build_ui()

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(shadow)

        self._timer = QTimer(self)
        self._timer.setInterval(100)
        self._timer.timeout.connect(self._on_tick)

        self.move(24, 64)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(8)

        container = QWidget(self)
        container.setObjectName("calibrationContainer")
        container.setStyleSheet(
            "#calibrationContainer {"
            "  background-color: rgba(26, 26, 26, 235);"
            "  border: 1px solid #333333;"
            "  border-radius: 8px;"
            "  padding: 10px;"
            "}"
        )
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(12, 10, 12, 10)
        c_layout.setSpacing(6)

        self._title_label = QLabel("🎥  Calibrating blink monitor", container)
        self._title_label.setStyleSheet(
            "font-size: 13px; font-weight: 600; color: #2A9D8F;"
        )
        c_layout.addWidget(self._title_label)

        self._desc_label = QLabel(
            "Look at the screen normally for 10 seconds to set your baseline.",
            container,
        )
        self._desc_label.setWordWrap(True)
        self._desc_label.setStyleSheet("font-size: 11px; color: #aaaaaa;")
        c_layout.addWidget(self._desc_label)

        self._progress_bar = QProgressBar(container)
        self._progress_bar.setRange(0, int(self.CALIBRATION_SECONDS * 10))
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._progress_bar.setFixedHeight(5)
        self._progress_bar.setStyleSheet(
            "QProgressBar {"
            "  background: #333333;"
            "  border: none;"
            "  border-radius: 2px;"
            "}"
            "QProgressBar::chunk {"
            "  background: #2A9D8F;"
            "  border-radius: 2px;"
            "}"
        )
        c_layout.addWidget(self._progress_bar)

        layout.addWidget(container)

    def start(self) -> None:
        """Reset countdown and show the floating calibration card."""
        self._elapsed = 0.0
        self._progress_bar.setValue(0)
        self.show()
        self._timer.start()

    def finish(self) -> None:
        """Stop the timer and hide the card."""
        self._timer.stop()
        self.hide()

    def _on_tick(self) -> None:
        self._elapsed += 0.1
        steps = int(self._elapsed * 10)
        self._progress_bar.setValue(min(steps, self._progress_bar.maximum()))
        if self._elapsed >= self.CALIBRATION_SECONDS:
            self.finish()

