"""Run the optional webcam pipeline in a separate process."""

import multiprocessing
import queue
import time
from multiprocessing.synchronize import Event
from pathlib import Path
from typing import Any

from screensense.vision.blink import (
    BlinkCalibrator,
    BlinkDetector,
    BlinkMinute,
    MinuteAccumulator,
    calculate_face_ear,
)

SAMPLE_FPS = 15
FACE_PRESENT_GOOD_MINUTE = 0.5
GOOD_BLINKS_PER_MINUTE = 12


class FaceLandmarkDetector:
    """Extract face landmarks using modern MediaPipe Tasks or legacy solutions."""

    def __init__(self, model_path: str | None = None) -> None:
        import mediapipe as mp

        self._legacy = hasattr(mp, "solutions")
        if self._legacy:
            self._detector = mp.solutions.face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=False,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            )
        else:
            from mediapipe.tasks import python
            from mediapipe.tasks.python import vision

            if model_path is None:
                model_path = str(
                    Path(__file__).parent / "models" / "face_landmarker.task"
                )
            base_options = python.BaseOptions(model_asset_path=model_path)
            options = vision.FaceLandmarkerOptions(
                base_options=base_options,
                output_face_blendshapes=False,
                num_faces=1,
            )
            self._detector = vision.FaceLandmarker.create_from_options(options)

    def process(self, rgb_frame: Any) -> list[tuple[float, float]] | None:
        """Process an RGB frame and return a list of 478 (x, y) normalized landmark points."""
        import mediapipe as mp

        if self._legacy:
            result = self._detector.process(rgb_frame)
            if result.multi_face_landmarks:
                face = result.multi_face_landmarks[0]
                return [(float(point.x), float(point.y)) for point in face.landmark]
            return None

        mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
        result = self._detector.detect(mp_image)
        if result.face_landmarks:
            face = result.face_landmarks[0]
            return [(float(point.x), float(point.y)) for point in face]
        return None

    def close(self) -> None:
        """Release underlying detector resources."""
        if hasattr(self._detector, "close"):
            self._detector.close()


def run_vision_worker(
    stop_event: Event,
    output_queue: Any,
    camera_index: int = 0,
) -> None:
    """Capture frames in memory and publish status plus per-minute aggregates only."""
    camera = None
    face_mesh = None
    try:
        import cv2

        camera = cv2.VideoCapture(camera_index)
        camera.set(cv2.CAP_PROP_FPS, SAMPLE_FPS)
        if not camera.isOpened():
            raise RuntimeError("The camera could not be opened.")
        face_mesh = FaceLandmarkDetector()
        output_queue.put({"type": "status", "status": "calibrating"})

        calibrator = BlinkCalibrator()
        detector: BlinkDetector | None = None
        current_minute: int | None = None
        accumulator: MinuteAccumulator | None = None
        last_frame_at = 0.0

        while not stop_event.is_set():
            elapsed = time.monotonic() - last_frame_at
            if elapsed < 1 / SAMPLE_FPS:
                stop_event.wait(1 / SAMPLE_FPS - elapsed)
                if stop_event.is_set():
                    break

            frame_started = time.monotonic()
            captured, frame = camera.read()
            if not captured:
                output_queue.put({"type": "error", "message": "A camera frame could not be read."})
                return

            now = time.monotonic()
            epoch = time.time()
            minute = int(epoch // 60) * 60
            if current_minute is not None and minute != current_minute and accumulator is not None:
                _publish_minute(output_queue, accumulator.finish())
                accumulator = None
            current_minute = minute

            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            landmarks = face_mesh.process(rgb_frame)
            ear: float | None = None
            if landmarks:
                ear = calculate_face_ear(landmarks)

            if detector is None:
                baseline = calibrator.add(ear, now)
                if baseline is not None:
                    detector = BlinkDetector(baseline)
                    output_queue.put({"type": "status", "status": "monitoring"})
            blink = detector.add(ear) if detector is not None and ear is not None else False
            if detector is not None:
                if ear is None:
                    detector.reset()
                if accumulator is None:
                    accumulator = MinuteAccumulator(minute)
                accumulator.add(ear, blink)

            last_frame_at = frame_started
            del frame, rgb_frame, landmarks

        if accumulator is not None:
            _publish_minute(output_queue, accumulator.finish())
    except Exception as error:  # noqa: BLE001 - report worker failures to the UI process.
        output_queue.put({"type": "error", "message": str(error) or type(error).__name__})
    finally:
        if face_mesh is not None:
            face_mesh.close()
        if camera is not None:
            camera.release()


def _publish_minute(output_queue: Any, aggregate: BlinkMinute) -> None:
    metrics = {
        "minute_start": aggregate.minute_start,
        "blinks": aggregate.blinks,
        "face_present_ratio": aggregate.face_present_ratio,
        "ear_mean": aggregate.ear_mean,
    }
    output_queue.put({"type": "metrics", "metrics": metrics})


class VisionMonitorProcess:
    """Own and shut down the isolated vision worker process."""

    def __init__(self) -> None:
        context = multiprocessing.get_context("spawn")
        self._stop_event = context.Event()
        self._messages = context.Queue()
        self._process = context.Process(
            target=run_vision_worker,
            args=(self._stop_event, self._messages),
            name="ScreenSenseVision",
            daemon=True,
        )

    @property
    def is_running(self) -> bool:
        try:
            return self._process.is_alive()
        except ValueError:
            return False

    def start(self) -> None:
        """Start monitoring once; raise if the process has already been started."""
        if self._process.pid is not None:
            raise RuntimeError("vision monitor process cannot be restarted")
        self._process.start()

    def read_messages(self) -> list[dict[str, Any]]:
        """Drain currently available status and metric messages."""
        messages: list[dict[str, Any]] = []
        while True:
            try:
                messages.append(self._messages.get_nowait())
            except queue.Empty:
                return messages

    def stop(self) -> None:
        """Request a clean stop, then terminate only if the camera driver is stuck."""
        if self._process.pid is None:
            return
        self._stop_event.set()
        self._process.join(timeout=2.0)
        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=1.0)
        self._messages.close()
        self._messages.join_thread()
        self._process.close()
