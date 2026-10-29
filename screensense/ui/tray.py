"""Display scheduler status in the system tray."""

from collections.abc import Callable
from enum import StrEnum

from PyQt6.QtCore import QObject, QRectF, Qt
from PyQt6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
from PyQt6.QtWidgets import QMenu, QSystemTrayIcon

from screensense.ui.theme import ACCENT, MUTED, PRIMARY


class TrayStatus(StrEnum):
    """Visual scheduler states represented by the tray icon."""

    ACTIVE = "active"
    SUPPRESSED = "suppressed"
    DUE = "due"


class ScreenSenseTray:
    """Show a status icon and update it from scheduler events."""

    def __init__(
        self,
        on_quit: Callable[[], None],
        on_settings: Callable[[], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        """Create a tray icon with a Quit action."""
        self._icon = QSystemTrayIcon(parent)
        self._menu = QMenu()
        if on_settings is not None:
            settings_action = QAction("Settings", self._menu)
            settings_action.triggered.connect(lambda _checked=False: on_settings())
            self._menu.addAction(settings_action)
        quit_action = QAction("Quit", self._menu)
        quit_action.triggered.connect(lambda _checked=False: on_quit())
        self._menu.addAction(quit_action)
        self._icon.setContextMenu(self._menu)
        self._status = TrayStatus.ACTIVE
        self.set_status(TrayStatus.ACTIVE)
        self._icon.show()

    @property
    def status(self) -> TrayStatus:
        """Return the current visual tray status."""
        return self._status

    def set_status(self, status: TrayStatus) -> None:
        """Update the tray icon color and accessible tooltip."""
        self._status = status
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(Qt.PenStyle.NoPen))
        base_color = MUTED if status is TrayStatus.SUPPRESSED else PRIMARY
        painter.setBrush(QColor(base_color))
        painter.drawEllipse(QRectF(4.0, 4.0, 24.0, 24.0))
        if status is TrayStatus.DUE:
            painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
            painter.setBrush(QColor(ACCENT))
            painter.drawEllipse(QRectF(19.0, 1.0, 12.0, 12.0))
        painter.end()
        self._icon.setIcon(QIcon(pixmap))
        self._icon.setToolTip(f"ScreenSense — {status.value.replace('_', ' ').title()}")

    def close(self) -> None:
        """Hide the tray icon."""
        self._icon.hide()
