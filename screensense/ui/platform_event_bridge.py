"""Queue platform worker-thread events onto the Qt application thread."""

from collections.abc import Callable

from PyQt6.QtCore import QObject, Qt, pyqtSignal, pyqtSlot

from screensense.platform_adapters.base import PowerEvent


class PowerEventBridge(QObject):
    """Marshal Windows power callbacks to a Qt-thread handler safely."""

    event_received = pyqtSignal(object)

    def __init__(
        self, handler: Callable[[PowerEvent], None], parent: QObject | None = None
    ) -> None:
        """Connect an explicit queued signal to the UI-thread handler."""
        super().__init__(parent)
        self._handler = handler
        self.event_received.connect(
            self._handle_event, Qt.ConnectionType.QueuedConnection
        )

    def enqueue(self, event: PowerEvent) -> None:
        """Accept an event from any thread and queue it for Qt delivery."""
        self.event_received.emit(event)

    @pyqtSlot(object)
    def _handle_event(self, event: object) -> None:
        """Invoke the handler only for a valid PowerEvent value."""
        if isinstance(event, PowerEvent):
            self._handler(event)
