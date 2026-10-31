from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QColor, QFont, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QWidget

from screensense.core.scoring import ScoreBand
from screensense.ui.theme import ACCENT, PRIMARY


class ScoreGaugeWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._score = 0
        self._band = ScoreBand.REST_YOUR_EYES
        self.setFixedSize(130, 130)

    def set_score(self, score: int, band: ScoreBand) -> None:
        self._score = max(0, min(100, score))
        self._band = band
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(10.0, 10.0, self.width() - 20.0, self.height() - 20.0)

        track_pen = QPen(QColor("#2d2d2d"), 8.0)
        painter.setPen(track_pen)
        painter.drawEllipse(rect)

        if self._score >= 80:
            color = QColor(PRIMARY)
        elif self._score >= 60:
            color = QColor(ACCENT)
        elif self._score >= 40:
            color = QColor("#d18e52")
        else:
            color = QColor("#c95344")

        fraction = self._score / 100.0
        arc_pen = QPen(color, 8.0)
        arc_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(arc_pen)
        painter.drawArc(rect, 90 * 16, -round(360 * 16 * fraction))

        painter.setPen(QColor("#ffffff"))
        font_score = QFont()
        font_score.setPointSize(24)
        font_score.setWeight(QFont.Weight.Bold)
        painter.setFont(font_score)
        painter.drawText(
            QRectF(0, 32, self.width(), 36),
            Qt.AlignmentFlag.AlignCenter,
            str(self._score),
        )

        painter.setPen(QColor(color))
        font_band = QFont()
        font_band.setPointSize(10)
        font_band.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font_band)
        painter.drawText(
            QRectF(0, 72, self.width(), 20),
            Qt.AlignmentFlag.AlignCenter,
            self._band.value,
        )

        painter.end()


class TodayTimelineWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(80)
        self._hourly_data: list[tuple[int, int]] = []

    def set_data(self, hourly_data: list[tuple[int, int]]) -> None:
        self._hourly_data = hourly_data
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        chart_top = 4.0
        chart_bottom = h - 18.0
        max_bar_h = chart_bottom - chart_top

        total_hours = 24
        slot_w = w / total_hours
        bar_w = max(3.0, slot_w - 2.5)

        data_dict = dict(self._hourly_data)

        for hour in range(total_hours):
            x = hour * slot_w + (slot_w - bar_w) / 2.0
            active_s = data_dict.get(hour, 0)
            fraction = min(1.0, active_s / 3600.0)
            bar_h = fraction * max_bar_h

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#2d2d2d"))
            painter.drawRoundedRect(QRectF(x, chart_top, bar_w, max_bar_h), 1.5, 1.5)

            if bar_h > 0:
                painter.setBrush(QColor(PRIMARY))
                painter.drawRoundedRect(
                    QRectF(x, chart_bottom - bar_h, bar_w, bar_h), 1.5, 1.5
                )

            if hour in (0, 6, 12, 18, 23):
                painter.setPen(QColor("#666666"))
                font = QFont()
                font.setPointSize(8)
                painter.setFont(font)
                painter.drawText(
                    QRectF(x - 8, chart_bottom + 2, 20, 14),
                    Qt.AlignmentFlag.AlignCenter,
                    f"{hour:02d}",
                )

        painter.end()


class WeeklyTrendChartWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(80)
        self._data: list[tuple[str, int]] = []

    def set_data(self, data: list[tuple[str, int]]) -> None:
        self._data = data[-7:]
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = float(self.width())
        h = float(self.height())
        count = len(self._data)
        if count == 0:
            painter.setPen(QColor("#666666"))
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No score history")
            painter.end()
            return

        slot_w = w / count
        bar_w = min(22.0, slot_w * 0.5)
        chart_top = 4.0
        chart_bottom = h - 20.0
        max_h = chart_bottom - chart_top

        for i, (day_lbl, score) in enumerate(self._data):
            x_center = i * slot_w + slot_w / 2.0
            x = x_center - bar_w / 2.0
            bar_len = (score / 100.0) * max_h
            y = chart_bottom - bar_len

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#2d2d2d"))
            painter.drawRoundedRect(QRectF(x, chart_top, bar_w, max_h), 2.5, 2.5)

            is_today = (i == count - 1)
            bar_color = QColor(PRIMARY if is_today else "#1f6f65")
            painter.setBrush(bar_color)
            painter.drawRoundedRect(QRectF(x, y, bar_w, bar_len), 2.5, 2.5)

            painter.setPen(QColor("#ffffff" if is_today else "#777777"))
            font = QFont()
            font.setPointSize(8)
            if is_today:
                font.setWeight(QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(
                QRectF(x_center - 16, chart_bottom + 3, 32, 16),
                Qt.AlignmentFlag.AlignCenter,
                day_lbl,
            )

        painter.end()
