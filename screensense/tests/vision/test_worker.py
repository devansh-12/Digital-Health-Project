"""Tests for the vision worker process and face landmark detector."""

import queue

import numpy as np
import pytest

from screensense.vision.blink import BlinkMinute
from screensense.vision.worker import FaceLandmarkDetector, _publish_minute


def test_face_landmark_detector_initializes_and_processes_frame() -> None:
    """Verify detector handles modern MediaPipe Tasks and accepts numpy frames."""
    detector = FaceLandmarkDetector()
    try:
        # 640x480 black RGB frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        landmarks = detector.process(frame)
        # On a blank frame, no face should be detected
        assert landmarks is None
    finally:
        detector.close()


def test_publish_minute_emits_expected_queue_payload() -> None:
    """Verify aggregated minute dictionary format matches expected protocol."""
    q = queue.Queue()
    sample = BlinkMinute(
        minute_start=1700000000,
        blinks=15,
        face_present_ratio=0.92,
        ear_mean=0.28,
    )
    _publish_minute(q, sample)

    item = q.get_nowait()
    assert item["type"] == "metrics"
    metrics = item["metrics"]
    assert metrics["minute_start"] == 1700000000
    assert metrics["blinks"] == 15
    assert metrics["face_present_ratio"] == pytest.approx(0.92)
    assert metrics["ear_mean"] == pytest.approx(0.28)

