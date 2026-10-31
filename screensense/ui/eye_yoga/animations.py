"""Paint gentle vector animations for guided Eye Yoga exercises."""

import math
from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QWidget

from screensense.ui.theme import ACCENT, CALM, MUTED, PRIMARY, TEXT


class EyeYogaAnimationWidget(QWidget):
    """Render smooth vector animations for eye yoga steps."""

    def __init__(
        self,
        anim_type: str = "palming",
        reduced_motion: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._anim_type = anim_type
        self._reduced_motion = reduced_motion
        self._phase = 0.0
        self.setMinimumSize(380, 220)

        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._on_tick)
        if not self._reduced_motion:
            self._timer.start()

    @property
    def anim_type(self) -> str:
        return self._anim_type

    @property
    def reduced_motion(self) -> bool:
        return self._reduced_motion

    def set_anim_type(self, anim_type: str) -> None:
        self._anim_type = anim_type
        self._phase = 0.0
        self.update()

    def set_reduced_motion(self, reduced: bool) -> None:
        self._reduced_motion = reduced
        if reduced:
            self._timer.stop()
        else:
            if not self._timer.isActive():
                self._timer.start()
        self.update()

    def _on_tick(self) -> None:
        self._phase = (self._phase + 0.08) % (2.0 * math.pi)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = float(self.width())
        height = float(self.height())
        cx = width / 2.0
        cy = height / 2.0

        if self._anim_type == "palming":
            self._paint_palming(painter, cx, cy)
        elif self._anim_type == "blink":
            self._paint_blink(painter, cx, cy)
        elif self._anim_type == "fig8":
            self._paint_fig8(painter, cx, cy)
        elif self._anim_type == "nearfar":
            self._paint_nearfar(painter, cx, cy)
        elif self._anim_type == "compass":
            self._paint_compass(painter, cx, cy)
        elif self._anim_type == "roll":
            self._paint_roll(painter, cx, cy)
        else:
            self._paint_palming(painter, cx, cy)

        painter.end()

    def _paint_palming(self, p: QPainter, cx: float, cy: float) -> None:
        scale = 1.0 if self._reduced_motion else 1.0 + 0.12 * math.sin(self._phase)
        radius = 60.0 * scale

        p.setPen(Qt.PenStyle.NoPen)
        glow_color = QColor(CALM)
        glow_color.setAlpha(45)
        p.setBrush(glow_color)
        p.drawEllipse(QPointF(cx, cy), radius + 20, radius + 20)

        p.setPen(QPen(QColor(PRIMARY), 2.5))
        p.setBrush(QColor("#081514"))
        p.drawEllipse(QPointF(cx - 42, cy), 36, 48)
        p.drawEllipse(QPointF(cx + 42, cy), 36, 48)

    def _paint_blink(self, p: QPainter, cx: float, cy: float) -> None:
        openness = 0.5 if self._reduced_motion else 0.5 + 0.5 * math.cos(self._phase)
        eye_w = 96.0
        eye_h = max(5.0, 48.0 * openness)

        p.setPen(QPen(QColor(PRIMARY), 2.5))
        p.setBrush(QColor("#081514"))
        p.drawEllipse(QRectF(cx - eye_w / 2, cy - eye_h / 2, eye_w, eye_h))

        if eye_h > 12.0:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(ACCENT))
            p.drawEllipse(QPointF(cx, cy), min(15.0, eye_h / 2), min(15.0, eye_h / 2))

    def _paint_fig8(self, p: QPainter, cx: float, cy: float) -> None:
        a = 90.0
        b = 48.0

        p.setPen(QPen(QColor("#2d403d"), 1.5, Qt.PenStyle.DashLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        points = []
        for i in range(60):
            t = (i / 60.0) * 2.0 * math.pi
            denom = 1.0 + math.sin(t) ** 2
            px = cx + (a * math.cos(t)) / denom
            py = cy + (b * math.sin(t) * math.cos(t)) / denom
            points.append(QPointF(px, py))
        if points:
            for i in range(len(points)):
                p.drawLine(points[i], points[(i + 1) % len(points)])

        t = 0.0 if self._reduced_motion else self._phase
        denom = 1.0 + math.sin(t) ** 2
        px = cx + (a * math.cos(t)) / denom
        py = cy + (b * math.sin(t) * math.cos(t)) / denom

        p.setPen(QPen(QColor("#FFFFFF"), 2))
        p.setBrush(QColor(PRIMARY))
        p.drawEllipse(QPointF(px, py), 10, 10)

    def _paint_nearfar(self, p: QPainter, cx: float, cy: float) -> None:
        depth = 0.5 if self._reduced_motion else 0.5 + 0.5 * math.sin(self._phase)
        size = 18.0 + 52.0 * depth

        p.setPen(QPen(QColor("#223330"), 1.5, Qt.PenStyle.DotLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), 24, 24)
        p.drawEllipse(QPointF(cx, cy), 72, 72)

        p.setPen(QPen(QColor(ACCENT), 2.0))
        p.setBrush(QColor(PRIMARY))
        p.drawEllipse(QPointF(cx, cy), size / 2.0, size / 2.0)

    def _paint_compass(self, p: QPainter, cx: float, cy: float) -> None:
        span = 62.0
        p.setPen(QPen(QColor("#223330"), 1.5, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(cx, cy - span), QPointF(cx, cy + span))
        p.drawLine(QPointF(cx - span, cy), QPointF(cx + span, cy))

        if self._reduced_motion:
            px, py = cx, cy
        else:
            step = int((self._phase / (2.0 * math.pi)) * 4) % 4
            prog = (self._phase / (2.0 * math.pi) * 4) % 1.0
            smooth = math.sin(prog * math.pi)
            if step == 0:
                px, py = cx, cy - span * smooth
            elif step == 1:
                px, py = cx, cy + span * smooth
            elif step == 2:
                px, py = cx - span * smooth, cy
            else:
                px, py = cx + span * smooth, cy

        p.setPen(QPen(QColor("#FFFFFF"), 2))
        p.setBrush(QColor(PRIMARY))
        p.drawEllipse(QPointF(px, py), 10, 10)

    def _paint_roll(self, p: QPainter, cx: float, cy: float) -> None:
        radius = 56.0
        p.setPen(QPen(QColor("#223330"), 1.5, Qt.PenStyle.DotLine))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(QPointF(cx, cy), radius, radius)

        t = 0.0 if self._reduced_motion else self._phase
        px = cx + radius * math.cos(t)
        py = cy + radius * math.sin(t)

        p.setPen(QPen(QColor("#FFFFFF"), 2))
        p.setBrush(QColor(PRIMARY))
        p.drawEllipse(QPointF(px, py), 10, 10)
