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
        on_eye_yoga: Callable[[], None] | None = None,
        on_dashboard: Callable[[], None] | None = None,
        on_stop_blink_monitor: Callable[[], None] | None = None,
        parent: QObject | None = None,
    ) -> None:
        self._icon = QSystemTrayIcon(parent)
        self._menu = QMenu()
        if on_dashboard is not None:
            dashboard_action = QAction("Open Dashboard", self._menu)
            dashboard_action.triggered.connect(lambda _checked=False: on_dashboard())
            self._menu.addAction(dashboard_action)
        if on_eye_yoga is not None:
            eye_yoga_action = QAction("Start Eye Yoga (60s)", self._menu)
            eye_yoga_action.triggered.connect(lambda _checked=False: on_eye_yoga())
            self._menu.addAction(eye_yoga_action)
        if on_settings is not None:
            settings_action = QAction("Settings", self._menu)
            settings_action.triggered.connect(lambda _checked=False: on_settings())
            self._menu.addAction(settings_action)
        self._stop_blink_action: QAction | None = None
        if on_stop_blink_monitor is not None:
            self._stop_blink_action = QAction("Stop Blink Monitoring", self._menu)
            self._stop_blink_action.setEnabled(False)
            self._stop_blink_action.triggered.connect(
                lambda _checked=False: on_stop_blink_monitor()
            )
            self._menu.addAction(self._stop_blink_action)
        quit_action = QAction("Quit", self._menu)
        quit_action.triggered.connect(lambda _checked=False: on_quit())
        self._menu.addAction(quit_action)
        self._icon.setContextMenu(self._menu)
        if on_dashboard is not None:
            self._icon.activated.connect(
                lambda reason: on_dashboard()
                if reason in (
                    QSystemTrayIcon.ActivationReason.DoubleClick,
                    QSystemTrayIcon.ActivationReason.Trigger,
                )
                else None
            )
        self._status = TrayStatus.ACTIVE
        self._camera_active = False
        self._camera_status = "Monitoring"
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
        if self._camera_active:
            painter.setPen(QPen(QColor("#FFFFFF"), 1.5))
            painter.setBrush(QColor("#D94F4F"))
            painter.drawEllipse(QRectF(19.0, 19.0, 12.0, 12.0))
        painter.end()
        self._icon.setIcon(QIcon(pixmap))
        tooltip = f"ScreenSense — {status.value.replace('_', ' ').title()}"
        if self._camera_active:
            tooltip += f" · Camera active: {self._camera_status}"
        self._icon.setToolTip(tooltip)

    def set_camera_active(self, active: bool, status: str = "Monitoring") -> None:
        """Show a persistent camera indicator and expose the tray kill switch."""
        self._camera_active = active
        self._camera_status = status
        if self._stop_blink_action is not None:
            self._stop_blink_action.setEnabled(active)
        self.set_status(self._status)

    def show_message(self, title: str, message: str, icon: QSystemTrayIcon.MessageIcon) -> None:
        """Surface a worker startup or runtime failure to the user."""
        self._icon.showMessage(title, message, icon)

    def close(self) -> None:
        """Hide the tray icon."""
        self._icon.hide()
