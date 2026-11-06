"""Animated gradient background for breaks and Eye Yoga.

Inspired by the soothing Aurora theme concept in blink-eye.
"""

import math

from PyQt6.QtCore import QPointF, QTimer
from PyQt6.QtGui import QColor, QLinearGradient, QPainter, QPaintEvent, QRadialGradient
from PyQt6.QtWidgets import QWidget


class GradientBreakBackground(QWidget):
    """Slow-shifting gradient background — visual concept inspired by blink-eye's Aurora."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._phase = 0.0
        self._timer = QTimer(self)
        self._timer.setInterval(50)  # ~20 FPS for gentle motion
        self._timer.timeout.connect(self._tick)

    def start(self) -> None:
        """Start the gradient animation."""
        self._timer.start()

    def stop(self) -> None:
        """Stop the gradient animation."""
        self._timer.stop()

    def _tick(self) -> None:
        self._phase = (self._phase + 0.015) % (2 * math.pi)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        w, h = float(self.width()), float(self.height())
        t = self._phase

        r1 = int(10 + 20 * math.sin(t))
        g1 = int(80 + 50 * math.cos(t * 0.7))
        b1 = int(100 + 60 * math.sin(t * 0.5))

        grad = QLinearGradient(QPointF(0, 0), QPointF(w, h))
        grad.setColorAt(0.0, QColor(max(0, min(255, r1)), max(0, min(255, g1)), max(0, min(255, b1))))
        grad.setColorAt(0.5, QColor(10, 20, 40))
        grad.setColorAt(1.0, QColor(max(0, min(255, r1 // 2)), max(0, min(255, g1 // 3)), max(0, min(255, b1))))
        painter.fillRect(self.rect(), grad)

        cx, cy = w / 2, h / 2
        glow_r = 180.0 + 40.0 * math.sin(t * 1.3)
        radial = QRadialGradient(QPointF(cx, cy), glow_r)
        radial.setColorAt(0.0, QColor(42, 157, 143, 60))
        radial.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.fillRect(self.rect(), radial)
        painter.end()

