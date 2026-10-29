"""Provide controllable in-memory platform adapters for tests and demos."""

from collections.abc import Callable

from screensense.platform_adapters.base import PowerEvent, WindowInfo


class StubIdleProvider:
    """Return a configurable idle duration."""

    def __init__(self, idle_seconds: float = 0.0) -> None:
        """Initialize the fake idle duration."""
        self.idle_seconds = idle_seconds

    def seconds_since_input(self) -> float:
        """Return the configured idle duration."""
        return self.idle_seconds


class StubWindowProvider:
    """Return a configurable foreground window."""

    def __init__(self, window: WindowInfo | None = None) -> None:
        """Initialize the fake foreground window."""
        self.window = window

    def foreground(self) -> WindowInfo | None:
        """Return the configured foreground window."""
        return self.window


class StubPowerProvider:
    """Emit power events to registered handlers on demand."""

    def __init__(self) -> None:
        """Initialize an empty power event subscriber list."""
        self._handlers: list[Callable[[PowerEvent], None]] = []

    def subscribe(self, handler: Callable[[PowerEvent], None]) -> Callable[[], None]:
        """Register a handler and return a callback that removes it."""
        self._handlers.append(handler)

        def unsubscribe() -> None:
            if handler in self._handlers:
                self._handlers.remove(handler)

        return unsubscribe

    def emit(self, event: PowerEvent) -> None:
        """Deliver a power event to a snapshot of current subscribers."""
        for handler in tuple(self._handlers):
            handler(event)


class StubAutostartProvider:
    """Track autostart state in memory."""

    def __init__(self, enabled: bool = False) -> None:
        """Initialize the fake autostart state."""
        self._enabled = enabled

    def enable(self) -> None:
        """Set autostart enabled."""
        self._enabled = True

    def disable(self) -> None:
        """Set autostart disabled."""
        self._enabled = False

    def is_enabled(self) -> bool:
        """Return the fake autostart state."""
        return self._enabled
