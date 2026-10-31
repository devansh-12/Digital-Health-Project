"""Implement platform interfaces for Linux with safe fallbacks."""

import logging
import os
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from screensense.platform_adapters.base import PowerEvent, Rect, WindowInfo

_LOGGER = logging.getLogger(__name__)


class LinuxAppDataProvider:
    """Resolve ScreenSense's per-user data directory under XDG or ~/.local/share."""

    def application_data_dir(self) -> Path:
        """Create and return `$XDG_DATA_HOME/ScreenSense` or `~/.local/share/ScreenSense`."""
        xdg_data = os.environ.get("XDG_DATA_HOME")
        if xdg_data:
            base_dir = Path(xdg_data)
        else:
            base_dir = Path.home() / ".local" / "share"
        directory = base_dir / "ScreenSense"
        directory.mkdir(parents=True, exist_ok=True)
        return directory


class LinuxIdleProvider:
    """Read user idle time on Linux with fallback to 0.0."""

    def __init__(self) -> None:
        """Initialize the idle provider."""
        self._xprintidle_path = shutil.which("xprintidle")

    def seconds_since_input(self) -> float:
        """Return idle seconds using xprintidle if available, else 0.0."""
        if self._xprintidle_path:
            try:
                import subprocess

                output = subprocess.check_output(
                    [self._xprintidle_path],
                    timeout=0.5,
                    text=True,
                    stderr=subprocess.DEVNULL,
                ).strip()
                return max(0.0, float(output) / 1000.0)
            except Exception:
                pass
        return 0.0


class LinuxWindowProvider:
    """Read foreground window metadata on Linux."""

    def foreground(self) -> WindowInfo | None:
        """Return foreground window metadata if available, otherwise None."""
        return None


class LinuxPowerProvider:
    """Publish power/session transitions on Linux."""

    def __init__(self) -> None:
        """Initialize Linux power provider."""
        self._handlers: list[Callable[[PowerEvent], None]] = []

    def start(self) -> None:
        """Start listening for system power signals."""

    def stop(self) -> None:
        """Stop listening for system power signals."""

    def subscribe(self, handler: Callable[[PowerEvent], None]) -> Callable[[], None]:
        """Subscribe to power transitions."""
        self._handlers.append(handler)

        def unsubscribe() -> None:
            if handler in self._handlers:
                self._handlers.remove(handler)

        return unsubscribe

    def emit(self, event: PowerEvent) -> None:
        """Emit a power transition to all subscribers."""
        for handler in tuple(self._handlers):
            handler(event)


class LinuxAutostartProvider:
    """Control autostart on Linux using standard XDG .desktop entries."""

    def __init__(self, command: str | None = None) -> None:
        """Initialize autostart provider with the startup command."""
        self._command = command or f"{sys.executable} -m screensense.app"

    @property
    def _desktop_file_path(self) -> Path:
        """Return the user autostart desktop entry path."""
        config_dir = os.environ.get("XDG_CONFIG_HOME")
        base_dir = Path(config_dir) if config_dir else Path.home() / ".config"
        return base_dir / "autostart" / "screensense.desktop"

    def enable(self) -> None:
        """Write an autostart desktop entry."""
        path = self._desktop_file_path
        path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            "[Desktop Entry]\n"
            "Type=Application\n"
            "Name=ScreenSense\n"
            f"Exec={self._command}\n"
            "Hidden=false\n"
            "NoDisplay=false\n"
            "X-GNOME-Autostart-enabled=true\n"
        )
        path.write_text(content, encoding="utf-8")

    def disable(self) -> None:
        """Remove the autostart desktop entry if it exists."""
        path = self._desktop_file_path
        if path.exists():
            path.unlink()

    def is_enabled(self) -> bool:
        """Return whether the autostart desktop entry exists."""
        return self._desktop_file_path.exists()
