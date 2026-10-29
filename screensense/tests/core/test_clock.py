"""Tests for deterministic clock behavior."""

import pytest

from screensense.core.clock import FakeClock


def test_fake_clock_advance_moves_monotonic_and_wall_time() -> None:
    """Advance both clock readings by the requested duration."""
    clock = FakeClock(monotonic_seconds=10.0, wall_seconds=1_000.0)

    clock.advance(2.5)

    assert clock.monotonic() == 12.5
    assert clock.wall_time() == 1_002.5


@pytest.mark.parametrize("seconds", [-1.0, float("inf"), float("nan")])
def test_fake_clock_rejects_invalid_advance(seconds: float) -> None:
    """Reject negative and non-finite clock advances."""
    with pytest.raises(ValueError):
        FakeClock().advance(seconds)
