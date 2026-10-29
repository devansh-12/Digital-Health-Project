"""Provide the system implementation of the core clock interface."""

import time


class SystemClock:
    """Read wall and monotonic time from the operating system."""

    def monotonic(self) -> float:
        """Return system monotonic seconds for elapsed-time measurements."""
        return time.monotonic()

    def wall_time(self) -> float:
        """Return system wall-clock seconds since the Unix epoch."""
        return time.time()
