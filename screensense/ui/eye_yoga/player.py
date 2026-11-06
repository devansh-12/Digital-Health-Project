"""Display the guided 60-second Eye Yoga interactive player."""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QCloseEvent, QKeyEvent
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from screensense.core.clock import Clock
from screensense.core.yoga import DEFAULT_EYE_YOGA_ROUTINE, YogaRoutine
from screensense.platform_adapters.clock import SystemClock
from screensense.ui.eye_yoga.animations import EyeYogaAnimationWidget
from screensense.ui.overlay import CountdownRing


class EyeYogaPlayer(QWidget):
    """An interactive player for guided Eye Yoga routines."""

    session_completed = pyqtSignal(int, int, int)
    session_exited = pyqtSignal(int, int, int)

    def __init__(
        self,
        clock: Clock | None = None,
        routine: YogaRoutine = DEFAULT_EYE_YOGA_ROUTINE,
        reduced_motion: bool = False,
        theme: str = "dark",
        parent: QWidget | None = None,
    ) -> None:
        """Initialize the Eye Yoga player window."""
        super().__init__(parent)
        self._clock = clock if clock is not None else SystemClock()
        self._routine = routine
        self._reduced_motion = reduced_motion
        if theme not in {"dark", "light"}:
            raise ValueError(f"Unsupported theme: {theme}")
        self._theme = theme

        self._current_step_index = 0
        self._step_remaining_s = float(
            self._routine.steps[0].seconds if self._routine.steps else 10
        )
        self._is_paused = False
        self._is_finished = False
        self._total_elapsed_s = 0.0
        self._last_tick_time = self._clock.monotonic()

        self.setWindowTitle("ScreenSense — Eye Yoga")
        self.setObjectName("eyeYogaPlayer")
        self.setMinimumSize(520, 520)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        self._build_ui()
        self._apply_theme()

        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.timeout.connect(self._on_tick)

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 20, 28, 24)
        layout.setSpacing(16)

        header_layout = QHBoxLayout()
        self._step_counter = QLabel("")
        self._step_counter.setStyleSheet(
            "font-size: 14px; color: #2A9D8F; letter-spacing: 6px;"
        )
        header_layout.addWidget(self._step_counter)

        header_layout.addStretch()

        self._exit_button = QPushButton("✕", self)
        self._exit_button.setFixedSize(30, 30)
        self._exit_button.setStyleSheet(
            "QPushButton { border: none; background: transparent; color: #666666; font-size: 16px; }"
            "QPushButton:hover { color: #ffffff; }"
        )
        self._exit_button.clicked.connect(self._handle_exit)
        header_layout.addWidget(self._exit_button)
        layout.addLayout(header_layout)

        initial_anim = self._routine.steps[0].anim if self._routine.steps else "palming"
        self._anim_widget = EyeYogaAnimationWidget(
            initial_anim, reduced_motion=self._reduced_motion, parent=self
        )
        self._anim_widget.setStyleSheet("background: transparent;")
        layout.addWidget(self._anim_widget, alignment=Qt.AlignmentFlag.AlignCenter)

        text_layout = QVBoxLayout()
        text_layout.setSpacing(6)
        text_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._step_title = QLabel("")
        self._step_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._step_title.setStyleSheet(
            "font-size: 22px; font-weight: 400; letter-spacing: 1.5px; color: #ffffff;"
        )
        text_layout.addWidget(self._step_title)

        self._step_instruction = QLabel("")
        self._step_instruction.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._step_instruction.setWordWrap(True)
        self._step_instruction.setStyleSheet(
            "color: #cccccc; font-size: 15px; font-weight: 500;"
        )
        text_layout.addWidget(self._step_instruction)

        layout.addLayout(text_layout)

        layout.addSpacing(4)

        timer_layout = QHBoxLayout()
        timer_layout.addStretch()
        step_sec = self._routine.steps[0].seconds if self._routine.steps else 10
        self._countdown_ring = CountdownRing(
            float(step_sec), parent=self, text_color="#FFFFFF"
        )
        timer_layout.addWidget(self._countdown_ring)
        timer_layout.addStretch()
        layout.addLayout(timer_layout)

        layout.addSpacing(4)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self._control_button = QPushButton("Pause", self)
        self._control_button.setFixedSize(140, 40)
        self._control_button.setStyleSheet(
            "QPushButton { border: 1px solid #2a2a2a; border-radius: 20px; background-color: #0d0d0d; color: #aaaaaa; font-size: 13px; font-weight: 500; }"
            "QPushButton:hover { border-color: #2A9D8F; color: #ffffff; background-color: #14201e; }"
            "QPushButton:focus { border-color: #2A9D8F; }"
        )
        self._control_button.clicked.connect(self._toggle_pause)
        button_layout.addWidget(self._control_button)
        button_layout.addStretch()
        layout.addLayout(button_layout)

        self._update_step_display()

    def start(self) -> None:
        self._is_paused = False
        self._is_finished = False
        self._current_step_index = 0
        step_sec = self._routine.steps[0].seconds if self._routine.steps else 10
        self._step_remaining_s = float(step_sec)
        self._total_elapsed_s = 0.0
        self._last_tick_time = self._clock.monotonic()

        self._anim_widget.show()
        self._countdown_ring.show()
        self._countdown_ring.reset(float(step_sec))
        self._control_button.setText("Pause")
        self._control_button.setEnabled(True)
        self._exit_button.setEnabled(True)
        self._update_step_display()
        self._apply_theme()

        self.show()
        self.raise_()
        self.activateWindow()
        self._control_button.setFocus()
        self._timer.start()

    def set_reduced_motion(self, reduced: bool) -> None:
        """Update animation motion preference for the active or next routine."""
        self._anim_widget.set_reduced_motion(reduced)

    def set_theme(self, theme: str) -> None:
        """Apply the selected light or dark palette to the routine player."""
        if theme not in {"dark", "light"}:
            raise ValueError(f"Unsupported theme: {theme}")
        self._theme = theme
        self._apply_theme()

    def _apply_theme(self) -> None:
        dark = self._theme == "dark"
        background = "#000000" if dark else "#F7FAF9"
        title_color = "#ffffff" if dark else "#14201E"
        body_color = "#cccccc" if dark else "#14201E"
        muted_color = "#aaaaaa" if dark else "#5B6B68"
        self.setStyleSheet(f"background-color: {background}; color: {body_color};")
        self._step_counter.setStyleSheet(
            "font-size: 14px; color: #2A9D8F; letter-spacing: 6px;"
        )
        self._exit_button.setStyleSheet(
            "QPushButton { border: none; background: transparent; "
            f"color: {muted_color}; font-size: 16px; }}"
            f"QPushButton:hover {{ color: {title_color}; }}"
        )
        self._step_title.setStyleSheet(
            "font-size: 22px; font-weight: 400; letter-spacing: 1.5px; "
            f"color: {title_color};"
        )
        self._step_instruction.setStyleSheet(
            f"color: {body_color}; font-size: 15px; font-weight: 500;"
        )
        self._control_button.setStyleSheet(
            "QPushButton { border: 1px solid #2a2a2a; border-radius: 20px; "
            f"background-color: {background}; color: {muted_color}; "
            "font-size: 13px; font-weight: 500; }"
            "QPushButton:hover { border-color: #2A9D8F; "
            f"color: {title_color}; background-color: "
            f"{'#14201e' if dark else '#E8F3F0'}; }}"
            "QPushButton:focus { border-color: #2A9D8F; }"
        )

    def _update_step_display(self) -> None:
        if not self._routine.steps or self._current_step_index >= len(
            self._routine.steps
        ):
            return
        step = self._routine.steps[self._current_step_index]
        self._step_title.setText(step.name)
        self._step_instruction.setText(step.text)
        dots = " ".join(
            "●" if i <= self._current_step_index else "○"
            for i in range(len(self._routine.steps))
        )
        self._step_counter.setText(dots)
        self._anim_widget.set_anim_type(step.anim)
        self._countdown_ring.set_remaining_seconds(self._step_remaining_s)

    def _on_tick(self) -> None:
        now = self._clock.monotonic()
        delta = max(0.0, now - self._last_tick_time)
        self._last_tick_time = now

        if self._is_paused or self._is_finished:
            return

        self._total_elapsed_s += delta
        self._step_remaining_s = max(0.0, self._step_remaining_s - delta)
        self._countdown_ring.set_remaining_seconds(self._step_remaining_s)

        if self._step_remaining_s <= 0.0:
            self._advance_step()

    def _advance_step(self) -> None:
        self._current_step_index += 1
        if self._current_step_index >= len(self._routine.steps):
            self._finish_routine()
        else:
            step = self._routine.steps[self._current_step_index]
            self._step_remaining_s = float(step.seconds)
            self._countdown_ring.reset(float(step.seconds))
            self._update_step_display()

    def _finish_routine(self) -> None:
        self._is_finished = True
        self._timer.stop()

        self._anim_widget.hide()
        self._countdown_ring.hide()

        dark = self._theme == "dark"
        title_color = "#ffffff" if dark else "#14201E"
        body_color = "#dddddd" if dark else "#2c2c2c"

        self._step_title.setText("Rest complete")
        self._step_title.setStyleSheet(
            f"font-size: 26px; font-weight: 600; letter-spacing: 1px; color: {title_color};"
        )
        self._step_instruction.setText("Your eyes are refreshed.")
        self._step_instruction.setStyleSheet(
            f"font-size: 16px; font-weight: 500; color: {body_color};"
        )
        self._step_counter.setText(
            " ".join("●" for _ in range(len(self._routine.steps)))
        )

        self._control_button.setText("Done")
        self._control_button.setEnabled(True)
        self._exit_button.setEnabled(False)
        self._control_button.setFocus()

    def _toggle_pause(self) -> None:
        """Toggle paused state or close if finished."""
        if self._is_finished:
            self.session_completed.emit(
                len(self._routine.steps),
                len(self._routine.steps),
                round(self._total_elapsed_s),
            )
            self.close()
            return

        self._is_paused = not self._is_paused
        if self._is_paused:
            self._control_button.setText("Resume")
            self._anim_widget.set_reduced_motion(True)
        else:
            self._control_button.setText("Pause")
            self._last_tick_time = self._clock.monotonic()
            if not self._reduced_motion:
                self._anim_widget.set_reduced_motion(False)

    def _handle_exit(self) -> None:
        """Exit the routine early and emit session_exited."""
        self._timer.stop()
        completed = self._current_step_index
        total = len(self._routine.steps)
        self.session_exited.emit(completed, total, round(self._total_elapsed_s))
        self.close()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Handle keyboard accessibility shortcuts: Space to pause, Esc to exit."""
        if event.key() == Qt.Key.Key_Space:
            self._toggle_pause()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self._handle_exit()
            event.accept()
        else:
            super().keyPressEvent(event)

    def closeEvent(self, event: QCloseEvent) -> None:
        """Ensure timer is stopped on close."""
        self._timer.stop()
        super().closeEvent(event)
