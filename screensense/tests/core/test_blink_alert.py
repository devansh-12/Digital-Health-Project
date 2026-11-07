"""Test BlinkAlertEvaluator logic."""

from screensense.core.blink_alert import BlinkAlertEvaluator
from screensense.core.clock import FakeClock


def test_blink_alert_evaluator_triggers_after_consecutive_low_minutes() -> None:
    clock = FakeClock()
    evaluator = BlinkAlertEvaluator(
        clock=clock,
        low_blink_threshold=8,
        consecutive_minutes_required=3,
        cooldown_seconds=1200.0,
    )

    # Normal minutes - no alert
    assert not evaluator.record_minute(blinks=15, face_present_ratio=0.8)
    assert evaluator.consecutive_low_minutes == 0

    # Low blink minute 1
    clock.advance(60)
    assert not evaluator.record_minute(blinks=5, face_present_ratio=0.8)
    assert evaluator.consecutive_low_minutes == 1

    # Low blink minute 2
    clock.advance(60)
    assert not evaluator.record_minute(blinks=6, face_present_ratio=0.7)
    assert evaluator.consecutive_low_minutes == 2

    # High blink minute resets the streak
    clock.advance(60)
    assert not evaluator.record_minute(blinks=14, face_present_ratio=0.9)
    assert evaluator.consecutive_low_minutes == 0

    # Re-accumulate 3 consecutive low-blink minutes
    clock.advance(60)
    assert not evaluator.record_minute(blinks=4, face_present_ratio=0.9)
    clock.advance(60)
    assert not evaluator.record_minute(blinks=3, face_present_ratio=0.85)
    clock.advance(60)
    # 3rd minute triggers alert
    assert evaluator.record_minute(blinks=2, face_present_ratio=0.8)
    assert evaluator.consecutive_low_minutes == 0

    # Cooldown prevents immediate re-alerting even if low blinks continue
    clock.advance(60)
    assert not evaluator.record_minute(blinks=2, face_present_ratio=0.8)
    clock.advance(60)
    assert not evaluator.record_minute(blinks=2, face_present_ratio=0.8)
    clock.advance(60)
    assert not evaluator.record_minute(blinks=2, face_present_ratio=0.8)

    # After cooldown (1200 s = 20 min), another 3 consecutive low minutes can alert
    clock.advance(1200)
    clock.advance(60)
    assert not evaluator.record_minute(blinks=2, face_present_ratio=0.8)
    clock.advance(60)
    assert not evaluator.record_minute(blinks=2, face_present_ratio=0.8)
    clock.advance(60)
    assert evaluator.record_minute(blinks=2, face_present_ratio=0.8)


def test_blink_alert_evaluator_ignores_absent_face() -> None:
    clock = FakeClock()
    evaluator = BlinkAlertEvaluator(clock=clock)

    # Low blinks but face_present_ratio < 0.3 means user is away / not monitored
    assert not evaluator.record_minute(blinks=0, face_present_ratio=0.1)
    assert evaluator.consecutive_low_minutes == 0

