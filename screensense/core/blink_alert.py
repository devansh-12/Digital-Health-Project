"""Evaluate rolling blink metrics to trigger proactive break nudges."""

from screensense.core.clock import Clock


class BlinkAlertEvaluator:
    """Detect sustained periods of reduced blink rate to nudge break intervals."""

    LOW_BLINK_THRESHOLD = 8
    CONSECUTIVE_MINUTES_REQUIRED = 3
    COOLDOWN_SECONDS = 20 * 60
    MIN_FACE_PRESENT_RATIO = 0.3

    def __init__(
        self,
        clock: Clock,
        low_blink_threshold: int = LOW_BLINK_THRESHOLD,
        consecutive_minutes_required: int = CONSECUTIVE_MINUTES_REQUIRED,
        cooldown_seconds: float = COOLDOWN_SECONDS,
    ) -> None:
        self._clock = clock
        self._threshold = low_blink_threshold
        self._required_consecutive = consecutive_minutes_required
        self._cooldown = cooldown_seconds
        self._consecutive_low_minutes = 0
        self._last_alert_monotonic: float = -self._cooldown

    @property
    def consecutive_low_minutes(self) -> int:
        """Return the current run of low-blink minutes."""
        return self._consecutive_low_minutes

    def record_minute(self, blinks: int, face_present_ratio: float) -> bool:
        """Process one minute of aggregates and return True if a break should be nudged."""
        if face_present_ratio < self.MIN_FACE_PRESENT_RATIO:
            # User was away or face was largely not detected; do not penalize
            return False

        if blinks < self._threshold:
            self._consecutive_low_minutes += 1
        else:
            self._consecutive_low_minutes = 0

        if self._consecutive_low_minutes >= self._required_consecutive:
            now = self._clock.monotonic()
            self._consecutive_low_minutes = 0
            if now - self._last_alert_monotonic >= self._cooldown:
                self._last_alert_monotonic = now
                return True

        return False

