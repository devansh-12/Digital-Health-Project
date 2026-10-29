"""Test Windows idle tick arithmetic without calling Windows APIs."""

import pytest

from screensense.platform_adapters import windows
from screensense.platform_adapters.windows import WindowsIdleProvider


@pytest.mark.parametrize(
    ("ticks", "expected_seconds"),
    [
        ((12_000, 7_000), 5.0),
        ((4_294_967_000, 4_294_966_000), 1.0),
        ((250, 4_294_967_000), 0.546),
    ],
)
def test_windows_idle_provider_handles_elapsed_and_wrapped_ticks(
    monkeypatch: pytest.MonkeyPatch,
    ticks: tuple[int, int],
    expected_seconds: float,
) -> None:
    """Convert elapsed DWORD ticks to seconds, handling tick wraparound."""
    monkeypatch.setattr(windows, "_get_idle_ticks", lambda: ticks)

    assert WindowsIdleProvider().seconds_since_input() == pytest.approx(
        expected_seconds
    )


def test_get_idle_ticks_fails_safely_off_windows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the Windows-only API failure explicit on other operating systems."""
    monkeypatch.setattr(windows.sys, "platform", "darwin")

    with pytest.raises(OSError, match="only on Windows"):
        windows._get_idle_ticks()
