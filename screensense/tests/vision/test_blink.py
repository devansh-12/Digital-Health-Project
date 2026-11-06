import pytest

from screensense.vision.blink import (
    EAR_EYE_INDICES,
    BlinkCalibrator,
    BlinkDetector,
    MinuteAccumulator,
    calculate_face_ear,
)


def _landmarks(ear: float = 0.3) -> list[tuple[float, float]]:
    landmarks = [(0.0, 0.0)] * 478
    for eye in EAR_EYE_INDICES:
        landmarks[eye[0]] = (0.0, 0.5)
        landmarks[eye[3]] = (1.0, 0.5)
        landmarks[eye[1]] = (0.25, 0.5 + ear)
        landmarks[eye[5]] = (0.25, 0.5 - ear)
        landmarks[eye[2]] = (0.75, 0.5 + ear)
        landmarks[eye[4]] = (0.75, 0.5 - ear)
    return landmarks


def test_face_ear_averages_both_eye_landmarks() -> None:
    assert calculate_face_ear(_landmarks()) == pytest.approx(0.6)


def test_blink_requires_two_to_six_closed_frames_then_reopening() -> None:
    detector = BlinkDetector(0.3)
    assert not detector.add(0.1)
    assert not detector.add(0.1)
    assert detector.add(0.3)

    for _ in range(7):
        assert not detector.add(0.1)
    assert not detector.add(0.3)


def test_missing_face_resets_partial_closure() -> None:
    detector = BlinkDetector(0.3)
    detector.add(0.1)
    detector.reset()
    assert not detector.add(0.3)


def test_calibration_takes_ten_seconds_and_uses_median() -> None:
    calibration = BlinkCalibrator(minimum_samples=2)
    assert calibration.add(0.3, 10.0) is None
    assert calibration.add(0.4, 15.0) is None
    assert calibration.add(0.5, 20.0) == pytest.approx(0.4)


def test_calibration_uses_fallback_when_no_face_is_available() -> None:
    calibration = BlinkCalibrator()
    assert calibration.add(None, 1.0) is None
    assert calibration.add(None, 11.0) == pytest.approx(0.21)


def test_minute_accumulator_emits_only_aggregated_metrics() -> None:
    accumulator = MinuteAccumulator(120)
    accumulator.add(0.3, blink=True)
    accumulator.add(None)
    aggregate = accumulator.finish()

    assert aggregate.minute_start == 120
    assert aggregate.blinks == 1
    assert aggregate.face_present_ratio == pytest.approx(0.5)
    assert aggregate.ear_mean == pytest.approx(0.3)
    assert not hasattr(aggregate, "frame")
