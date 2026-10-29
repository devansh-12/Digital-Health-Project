"""Test queued delivery of worker-thread platform events to Qt."""

import os
import threading

import pytest
from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QApplication

from screensense.platform_adapters.base import PowerEvent
from screensense.ui.platform_event_bridge import PowerEventBridge


@pytest.fixture(scope="module")
def app() -> QApplication:
    """Create an offscreen QApplication for signal delivery tests."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def test_power_events_are_queued_onto_qt_thread(app: QApplication) -> None:
    """Handle events emitted from a worker only after Qt processes the queue."""
    received: list[tuple[PowerEvent, QThread]] = []
    bridge = PowerEventBridge(
        lambda event: received.append((event, QThread.currentThread())), parent=app
    )
    worker = threading.Thread(target=bridge.enqueue, args=(PowerEvent.LOCK,))

    worker.start()
    worker.join()
    assert received == []
    app.processEvents()

    assert received == [(PowerEvent.LOCK, app.thread())]
    bridge.deleteLater()
