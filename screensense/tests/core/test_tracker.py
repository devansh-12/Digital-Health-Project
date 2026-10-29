"""Aggregation specifications for the not-yet-implemented tracker."""

from collections.abc import Iterator, Sequence
from typing import Any

import pytest

from screensense.core import tracker as tracker_module
from screensense.core.clock import FakeClock
from screensense.core.context import ContextState
from screensense.core.tracker import ActivitySegment, UsageBucket


def make_tracker(wall_seconds: float = 0.0) -> tuple[Any, FakeClock]:
    """Build the expected tracker interface with a deterministic clock."""
    tracker_type = getattr(tracker_module, "Tracker", None)
    assert tracker_type is not None, "Tracker aggregation has not been implemented"
    clock = FakeClock(wall_seconds=wall_seconds)
    return tracker_type(clock), clock


@pytest.mark.parametrize(
    ("context", "field"),
    [
        (ContextState.FREE, "active_s"),
        (ContextState.IDLE, "idle_s"),
        (ContextState.FULLSCREEN, "fullscreen_s"),
        (ContextState.CALL, "call_s"),
    ],
)
def test_five_second_samples_increment_the_matching_hourly_counter(
    context: ContextState, field: str
) -> None:
    """Add five seconds to exactly the counter matching each sampled context."""
    tracker, clock = make_tracker()
    tracker.sample(ContextState.FREE)
    clock.advance(5)
    tracker.sample(context)

    bucket = tracker.buckets[0]
    assert getattr(bucket, field) == 5
    assert sum(
        getattr(bucket, name)
        for name in ("active_s", "idle_s", "fullscreen_s", "call_s")
    ) == 5


def test_sample_spanning_hour_boundary_splits_seconds_between_buckets() -> None:
    """Split a five-second sample at the exact Unix-hour boundary."""
    tracker, clock = make_tracker(wall_seconds=3_598)
    tracker.sample(ContextState.FREE)
    clock.advance(5)
    tracker.sample(ContextState.FREE)

    assert tracker.buckets[0].active_s == 2
    assert tracker.buckets[3_600].active_s == 3


def test_samples_roll_over_at_midnight_without_losing_seconds() -> None:
    """Split elapsed activity across the midnight hour boundary."""
    tracker, clock = make_tracker(wall_seconds=86_395)
    tracker.sample(ContextState.FREE)
    clock.advance(10)
    tracker.sample(ContextState.FREE)

    assert tracker.buckets[82_800].active_s == 5
    assert tracker.buckets[86_400].active_s == 5


def test_sleep_gap_is_not_added_to_hourly_usage() -> None:
    """Resume from a fresh baseline so asleep time is excluded."""
    tracker, clock = make_tracker(wall_seconds=500)
    tracker.sample(ContextState.FREE)
    clock.advance(5)
    tracker.sample(ContextState.FREE)
    tracker.pause()
    clock.advance(3 * 60 * 60)
    tracker.resume()
    clock.advance(5)
    tracker.sample(ContextState.FREE)

    assert sum(bucket.active_s for bucket in tracker.buckets.values()) == 10
    assert sum(bucket.idle_s for bucket in tracker.buckets.values()) == 0


def test_longest_active_stretch_resets_on_idle_and_completed_break() -> None:
    """Count active contexts together, resetting at idle gaps and breaks."""
    longest = getattr(tracker_module, "longest_unbroken_active_stretch", None)
    assert callable(longest), "Longest-stretch calculation has not been implemented"
    segments = [
        ActivitySegment(ContextState.FREE, 100),
        ActivitySegment(ContextState.CALL, 50),
        ActivitySegment(ContextState.IDLE, 10),
        ActivitySegment(ContextState.FREE, 200),
        ActivitySegment(ContextState.FREE, 30, break_completed=True),
        ActivitySegment(ContextState.FREE, 80),
    ]

    assert longest(segments) == 200


@pytest.fixture
def simulated_eight_hour_samples() -> Iterator[list[ContextState]]:
    """Provide the context sequence for 5-second samples over eight hours."""
    pattern = (
        ContextState.FREE,
        ContextState.IDLE,
        ContextState.CALL,
        ContextState.FULLSCREEN,
    )
    yield [pattern[sample_index % len(pattern)] for sample_index in range(8 * 60 * 12)]


def test_simulated_eight_hour_day_aggregates_all_samples(
    simulated_eight_hour_samples: list[ContextState],
) -> None:
    """Aggregate 5,760 five-second samples into eight complete hour buckets."""
    tracker, clock = make_tracker(wall_seconds=86_400)
    tracker.sample(ContextState.FREE)
    for context in simulated_eight_hour_samples:
        clock.advance(5)
        tracker.sample(context)

    assert len(tracker.buckets) == 8
    totals = {
        field: sum(getattr(bucket, field) for bucket in tracker.buckets.values())
        for field in ("active_s", "idle_s", "fullscreen_s", "call_s")
    }
    assert totals == {
        "active_s": 7_200,
        "idle_s": 7_200,
        "fullscreen_s": 7_200,
        "call_s": 7_200,
    }


def test_flush_retains_failed_data_and_samples_added_during_write(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Retain failed batches and preserve samples added while a writer runs."""
    tracker, clock = make_tracker()
    tracker.sample(ContextState.FREE)
    clock.advance(5)
    tracker.sample(ContextState.FREE)

    class FailingWriter:
        """Simulate a storage error with a sensitive exception message."""

        def write_usage(self, buckets: Sequence[UsageBucket]) -> None:
            raise RuntimeError("private value must not reach logs")

    assert not tracker.flush(FailingWriter())
    assert tracker.buckets[0].active_s == 5
    assert "Hourly usage flush failed" in caplog.text
    assert "private value" not in caplog.text

    class SamplingWriter:
        """Add another sample during the write to verify acknowledgement safety."""

        def __init__(self) -> None:
            self.written: list[UsageBucket] = []
            self._sample_added = False

        def write_usage(self, buckets: Sequence[UsageBucket]) -> None:
            self.written.extend(buckets)
            if not self._sample_added:
                self._sample_added = True
                clock.advance(5)
                tracker.sample(ContextState.FREE)

    writer = SamplingWriter()
    assert tracker.flush(writer)
    assert sum(bucket.active_s for bucket in writer.written) == 5
    assert tracker.buckets[0].active_s == 5
    assert tracker.flush(writer)
    assert sum(bucket.active_s for bucket in writer.written) == 10
    assert tracker.buckets == {}
