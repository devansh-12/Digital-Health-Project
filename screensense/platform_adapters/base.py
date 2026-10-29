"""Define OS adapter protocols without importing platform-specific modules."""

from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

Rect = tuple[int, int, int, int]


@dataclass(frozen=True, slots=True)
class WindowInfo:
    """Describe a foreground window; its title is memory-only and must never be persisted."""

    title: str
    process: str
    rect: Rect
    is_fullscreen: bool


class PowerEvent(StrEnum):
    """Power and session transitions reported by a platform adapter."""

    SLEEP = "sleep"
    RESUME = "resume"
    LOCK = "lock"
    UNLOCK = "unlock"


class IdleProvider(Protocol):
    """Report seconds since the last user input."""

    def seconds_since_input(self) -> float:
        """Return elapsed seconds since keyboard or pointer input."""


class WindowProvider(Protocol):
    """Report the current foreground window, when available."""

    def foreground(self) -> WindowInfo | None:
        """Return in-memory foreground metadata or None if unavailable."""


class PowerProvider(Protocol):
    """Publish sleep, resume, and session-lock transitions to a handler."""

    def start(self) -> None:
        """Start receiving native power and session events."""

    def stop(self) -> None:
        """Stop receiving native events and release platform resources."""

    def subscribe(self, handler: Callable[[PowerEvent], None]) -> Callable[[], None]:
        """Subscribe to power transitions and return an unsubscribe callback."""


class AutostartProvider(Protocol):
    """Control whether the application starts with the operating system."""

    def enable(self) -> None:
        """Enable application autostart."""

    def disable(self) -> None:
        """Disable application autostart."""

    def is_enabled(self) -> bool:
        """Return whether application autostart is enabled."""
