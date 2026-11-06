"""Frameless transparent HUD overlay for live blink rate and active time stats.

Inspired by BlinkWell's HUD concept, adapted for ScreenSense and PyQt6.
"""

from PyQt6.QtCore import QPoint, Qt
from PyQt6.QtGui import QColor, QMouseEvent
from PyQt6.QtWidgets import (
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QWidget,
)


class StatsOverlayWidget(QWidget):
    """Frameless transparent HUD for live stats, draggable by the user."""

    def __init__(self, parent: QWidget | None = None) -> None:
        flags = (
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        super().__init__(parent, flags)
        self.setObjectName("statsOverlay")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._drag_position: QPoint | None = None

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(14)

        self._blink_label = QLabel("● -- bpm", self)
        self._blink_label.setStyleSheet(
            "color: #2A9D8F; font-size: 12px; font-weight: 600; "
            "background: rgba(30, 30, 30, 180); border-radius: 4px; padding: 2px 6px;"
        )
        layout.addWidget(self._blink_label)

        self._time_label = QLabel("⏱ 0:00:00", self)
        self._time_label.setStyleSheet(
            "color: #cccccc; font-size: 12px; "
            "background: rgba(30, 30, 30, 180); border-radius: 4px; padding: 2px 6px;"
        )
        layout.addWidget(self._time_label)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(12)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 180))
        self.setGraphicsEffect(shadow)

        self.move(16, 16)
        self.adjustSize()

    def update_blink_rate(self, blinks_per_min: int) -> None:
        """Update the displayed blink rate and color indicator."""
        self._blink_label.setText(f"● {blinks_per_min} bpm")
        color = "#2A9D8F" if blinks_per_min >= 12 else "#e06c75"
        self._blink_label.setStyleSheet(
            f"color: {color}; font-size: 12px; font-weight: 600; "
            "background: rgba(30, 30, 30, 180); border-radius: 4px; padding: 2px 6px;"
        )
        self.adjustSize()

    def update_active_time(self, active_seconds: int) -> None:
        """Update the active screen time counter."""
        hours, rem = divmod(active_seconds, 3600)
        minutes, seconds = divmod(rem, 60)
        self._time_label.setText(f"⏱ {hours}:{minutes:02d}:{seconds:02d}")
        self.adjustSize()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Capture position offset when left button is pressed."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Reposition the HUD as the user drags with the left mouse button."""
        if (
            event.buttons() == Qt.MouseButton.LeftButton
            and self._drag_position is not None
        ):
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()
        else:
            super().mouseMoveEvent(event)

