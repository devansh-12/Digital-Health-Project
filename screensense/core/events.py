"""Define typed domain events and a synchronous pure-Python event bus."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, TypeVar, cast

if TYPE_CHECKING:
    from screensense.core.context import ContextState

EventT = TypeVar("EventT")
EventHandler = Callable[[EventT], None]
Unsubscribe = Callable[[], None]
BreakKind = Literal["quick", "long", "yoga", "natural"]


@dataclass(frozen=True, slots=True)
class ShowPrompt:
    """Request that the UI show a break prompt of the given kind."""

    kind: BreakKind


@dataclass(frozen=True, slots=True)
class BreakCompleted:
    """Report a completed break and its duration in seconds."""

    kind: BreakKind
    duration_s: int


@dataclass(frozen=True, slots=True)
class BreakSkipped:
    """Report that a user skipped a break prompt."""

    kind: BreakKind


@dataclass(frozen=True, slots=True)
class SchedulerTick:
    """Signal that the scheduler should evaluate its current state."""


@dataclass(frozen=True, slots=True)
class ContextChanged:
    """Report a confirmed context-state transition."""

    previous: ContextState | None
    current: ContextState


class EventBus:
    """Dispatch events synchronously to subscribers of the exact event type."""

    def __init__(self) -> None:
        """Initialize an empty event subscription registry."""
        self._handlers: dict[type[object], list[Callable[[object], None]]] = {}

    def subscribe(
        self, event_type: type[EventT], handler: EventHandler[EventT]
    ) -> Unsubscribe:
        """Subscribe to an event type and return a function to unsubscribe."""
        event_key = cast(type[object], event_type)

        def dispatch(event: object) -> None:
            handler(cast(EventT, event))

        self._handlers.setdefault(event_key, []).append(dispatch)

        def unsubscribe() -> None:
            handlers = self._handlers.get(event_key)
            if handlers is None:
                return
            try:
                handlers.remove(dispatch)
            except ValueError:
                return
            if not handlers:
                del self._handlers[event_key]

        return unsubscribe

    def publish(self, event: EventT) -> None:
        """Send an event to a snapshot of its exact-type subscribers."""
        event_key = cast(type[object], type(event))
        for handler in tuple(self._handlers.get(event_key, ())):
            handler(cast(object, event))
