"""Calculate eye aspect ratios and detect blinks from face landmarks."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from math import dist, isfinite

Point = tuple[float, float]
EAR_EYE_INDICES = ((362, 385, 387, 263, 373, 380), (33, 160, 158, 133, 153, 144))


def _eye_aspect_ratio(points: Sequence[Point]) -> float:
    if len(points) != 6:
        raise ValueError("an eye requires exactly six landmark points")
    vertical = dist(points[1], points[5]) + dist(points[2], points[4])
    horizontal = dist(points[0], points[3])
    if horizontal == 0:
        raise ValueError("eye corner landmarks must not overlap")
    ratio = vertical / (2.0 * horizontal)
    if not isfinite(ratio):
        raise ValueError("eye landmarks must be finite")
    return ratio


def calculate_face_ear(landmarks: Sequence[Point]) -> float:
    """Return mean EAR for both eyes using MediaPipe Face Mesh landmark indices."""
    required_index = max(index for eye in EAR_EYE_INDICES for index in eye)
    if len(landmarks) <= required_index:
        raise ValueError("face landmarks do not contain the eye points")
    return sum(
        _eye_aspect_ratio([landmarks[index] for index in eye])
        for eye in EAR_EYE_INDICES
    ) / len(EAR_EYE_INDICES)


@dataclass(slots=True)
class BlinkDetector:
    """Detect 2-6 frame eye closures below a calibrated EAR threshold."""

    baseline_ear: float
    threshold_ratio: float = 0.75
    minimum_closed_frames: int = 2
    maximum_closed_frames: int = 6

    def __post_init__(self) -> None:
        if self.baseline_ear <= 0:
            raise ValueError("baseline_ear must be positive")
        if not 0 < self.threshold_ratio < 1:
            raise ValueError("threshold_ratio must be between zero and one")
        if self.minimum_closed_frames < 1 or self.maximum_closed_frames < self.minimum_closed_frames:
            raise ValueError("invalid closed-frame range")
        self._closed_frames = 0

    _closed_frames: int = field(init=False, default=0)

    @property
    def threshold(self) -> float:
        return self.baseline_ear * self.threshold_ratio

    def add(self, ear: float) -> bool:
        """Return true when a valid short closure is followed by an open eye."""
        if ear < 0:
            raise ValueError("ear must be non-negative")
        if ear < self.threshold:
            self._closed_frames += 1
            return False

        blink = self.minimum_closed_frames <= self._closed_frames <= self.maximum_closed_frames
        self._closed_frames = 0
        return blink

    def reset(self) -> None:
        """Discard a partial closure, for example when a face leaves the frame."""
        self._closed_frames = 0


class BlinkCalibrator:
    """Collect a ten-second EAR baseline, falling back when no face is available."""

    def __init__(
        self,
        duration_s: float = 10.0,
        minimum_samples: int = 10,
        fallback_ear: float = 0.21,
    ) -> None:
        if duration_s <= 0 or minimum_samples < 1 or fallback_ear <= 0:
            raise ValueError("calibration settings must be positive")
        self.duration_s = duration_s
        self.minimum_samples = minimum_samples
        self.fallback_ear = fallback_ear
        self._started_at: float | None = None
        self._samples: list[float] = []
        self._baseline: float | None = None

    @property
    def baseline(self) -> float | None:
        return self._baseline

    def add(self, ear: float | None, timestamp: float) -> float | None:
        """Add a sample and return the baseline once the calibration window ends."""
        if self._baseline is not None:
            return self._baseline
        if self._started_at is None:
            self._started_at = timestamp
        if ear is not None:
            if ear <= 0:
                raise ValueError("ear samples must be positive")
            self._samples.append(ear)
        if timestamp - self._started_at < self.duration_s:
            return None

        if len(self._samples) >= self.minimum_samples:
            ordered = sorted(self._samples)
            middle = len(ordered) // 2
            self._baseline = (
                ordered[middle]
                if len(ordered) % 2
                else (ordered[middle - 1] + ordered[middle]) / 2
            )
        else:
            self._baseline = self.fallback_ear
        return self._baseline


@dataclass(frozen=True, slots=True)
class BlinkMinute:
    """Privacy-safe aggregate for one minute; contains no image or face landmarks."""

    minute_start: int
    blinks: int
    face_present_ratio: float
    ear_mean: float | None


class MinuteAccumulator:
    """Aggregate sampling results for a single wall-clock minute."""

    def __init__(self, minute_start: int) -> None:
        self.minute_start = minute_start
        self._frames = 0
        self._face_frames = 0
        self._ear_total = 0.0
        self._blinks = 0

    def add(self, ear: float | None, blink: bool = False) -> None:
        self._frames += 1
        if ear is not None:
            self._face_frames += 1
            self._ear_total += ear
        if blink:
            self._blinks += 1

    def finish(self) -> BlinkMinute:
        if self._frames == 0:
            raise ValueError("cannot aggregate a minute without sampled frames")
        return BlinkMinute(
            minute_start=self.minute_start,
            blinks=self._blinks,
            face_present_ratio=self._face_frames / self._frames,
            ear_mean=self._ear_total / self._face_frames if self._face_frames else None,
        )
