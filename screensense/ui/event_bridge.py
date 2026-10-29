"""Marshal pure-Python scheduler events onto the Qt UI thread."""

from PyQt6.QtCore import QObject, Qt, pyqtSignal, pyqtSlot

from screensense.core.events import (
    BreakCompleted,
    BreakSkipped,
    EventBus,
    ShowPrompt,
    Unsubscribe,
)
from screensense.core.scheduler import Scheduler
from screensense.ui.overlay import BreakOverlay
from screensense.ui.tray import ScreenSenseTray, TrayStatus


class SchedulerUiBridge(QObject):
    """Forward scheduler events to widgets and UI actions to the scheduler."""

    event_received = pyqtSignal(object)

    def __init__(
        self,
        event_bus: EventBus,
        scheduler: Scheduler,
        overlay: BreakOverlay,
        tray: ScreenSenseTray,
        parent: QObject | None = None,
    ) -> None:
        """Subscribe to core events and connect overlay actions."""
        super().__init__(parent)
        self._scheduler = scheduler
        self._overlay = overlay
        self._tray = tray
        self._closed = False
        self.event_received.connect(
            self._handle_event, Qt.ConnectionType.QueuedConnection
        )
        self._subscriptions: list[Unsubscribe] = [
            event_bus.subscribe(ShowPrompt, self._queue_event),
            event_bus.subscribe(BreakCompleted, self._queue_event),
            event_bus.subscribe(BreakSkipped, self._queue_event),
        ]

        overlay.eye_yoga_requested.connect(self._start_yoga)
        overlay.quick_break_requested.connect(self._start_quick_break)
        overlay.snooze_requested.connect(self._snooze)
        overlay.skip_requested.connect(scheduler.skip)

    def close(self) -> None:
        """Remove subscriptions and signal connections."""
        if self._closed:
            return
        for unsubscribe in self._subscriptions:
            unsubscribe()
        self._subscriptions.clear()
        self._overlay.eye_yoga_requested.disconnect(self._start_yoga)
        self._overlay.quick_break_requested.disconnect(self._start_quick_break)
        self._overlay.snooze_requested.disconnect(self._snooze)
        self._overlay.skip_requested.disconnect(self._scheduler.skip)
        self._closed = True

    def _queue_event(self, event: object) -> None:
        """Queue an event for processing on the Qt object's thread."""
        self.event_received.emit(event)

    @pyqtSlot(object)
    def _handle_event(self, event: object) -> None:
        """Update the overlay and tray for a scheduler event."""
        if self._closed:
            return
        if isinstance(event, ShowPrompt):
            self._overlay.show_prompt(event)
            self._tray.set_status(TrayStatus.DUE)
        elif isinstance(event, (BreakCompleted, BreakSkipped)):
            self._overlay.close()
            self._tray.set_status(TrayStatus.ACTIVE)

    def _start_yoga(self) -> None:
        """Start the Eye Yoga break and restore the tray's active status."""
        self._scheduler.start_break(kind="yoga")
        self._tray.set_status(TrayStatus.ACTIVE)

    def _start_quick_break(self) -> None:
        """Start a quick break and restore the tray's active status."""
        self._scheduler.start_break(kind="quick")
        self._tray.set_status(TrayStatus.ACTIVE)

    def _snooze(self) -> None:
        """Snooze the scheduler prompt and mark reminders as suppressed."""
        self._scheduler.snooze()
        self._tray.set_status(TrayStatus.SUPPRESSED)
