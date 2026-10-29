"""Run queued hourly usage persistence on a Qt worker pool."""

from PyQt6.QtCore import (
    QObject,
    QRunnable,
    Qt,
    QThreadPool,
    QTimer,
    pyqtSignal,
    pyqtSlot,
)

from screensense.core.tracker import Tracker, UsageWriter
from screensense.platform_adapters.base import PowerEvent


class _FlushSignals(QObject):
    """Report completion from one background flush task."""

    finished = pyqtSignal(bool)


class _FlushTask(QRunnable):
    """Run one tracker flush without importing Qt into core logic."""

    def __init__(self, tracker: Tracker, writer: UsageWriter) -> None:
        """Capture the tracker and storage writer for one task."""
        super().__init__()
        self._tracker = tracker
        self._writer = writer
        self.signals = _FlushSignals()

    def run(self) -> None:
        """Flush pending buckets and notify the controller of completion."""
        self.signals.finished.emit(self._tracker.flush(self._writer))


class UsageFlushController(QObject):
    """Flush tracker data every 60 seconds and synchronously on shutdown/power."""

    FLUSH_INTERVAL_MS = 60_000

    def __init__(
        self, tracker: Tracker, writer: UsageWriter, parent: QObject | None = None
    ) -> None:
        """Start periodic background persistence for the supplied tracker."""
        super().__init__(parent)
        self._tracker = tracker
        self._writer = writer
        self._pool = QThreadPool(self)
        self._pool.setMaxThreadCount(1)
        self._flush_in_progress = False
        self._locked = False
        self._asleep = False
        self._timer = QTimer(self)
        self._timer.setInterval(self.FLUSH_INTERVAL_MS)
        self._timer.timeout.connect(self.flush_now)
        self._timer.start()

    def flush_now(self) -> None:
        """Schedule a flush unless one is already running."""
        if self._flush_in_progress:
            return
        self._flush_in_progress = True
        task = _FlushTask(self._tracker, self._writer)
        task.signals.finished.connect(
            self._on_flush_finished, Qt.ConnectionType.QueuedConnection
        )
        self._pool.start(task)

    def flush_and_wait(self) -> None:
        """Stop periodic writes and wait for one final background flush."""
        self._timer.stop()
        if not self._flush_in_progress:
            self.flush_now()
        self._pool.waitForDone()
        self._flush_in_progress = False

    def handle_power_event(self, event: PowerEvent) -> None:
        """Flush and pause before sleep/lock; resume sampling after both clear."""
        if event in (PowerEvent.SLEEP, PowerEvent.LOCK):
            self._asleep = self._asleep or event is PowerEvent.SLEEP
            self._locked = self._locked or event is PowerEvent.LOCK
            self._tracker.pause()
            self.flush_and_wait()
        elif event is PowerEvent.RESUME:
            self._asleep = False
            if not self._locked:
                self._tracker.resume()
                self._timer.start()
        elif event is PowerEvent.UNLOCK:
            self._locked = False
            if not self._asleep:
                self._tracker.resume()
                self._timer.start()

    @pyqtSlot(bool)
    def _on_flush_finished(self, _success: bool) -> None:
        """Allow the next periodic flush after the current task completes."""
        self._flush_in_progress = False
