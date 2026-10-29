"""Tests for the pure-Python event bus."""

from dataclasses import dataclass

from screensense.core.events import EventBus, SchedulerTick


@dataclass(frozen=True)
class OtherEvent:
    """An unrelated event used to verify exact-type dispatch."""


def test_event_bus_publishes_to_matching_subscribers() -> None:
    """Deliver each event only to its exact-type subscribers."""
    bus = EventBus()
    received_ticks: list[SchedulerTick] = []
    received_other: list[OtherEvent] = []
    bus.subscribe(SchedulerTick, received_ticks.append)
    bus.subscribe(OtherEvent, received_other.append)

    bus.publish(SchedulerTick())

    assert received_ticks == [SchedulerTick()]
    assert received_other == []


def test_event_bus_unsubscribe_stops_future_delivery() -> None:
    """Stop delivering events after the returned unsubscribe function runs."""
    bus = EventBus()
    received: list[SchedulerTick] = []
    unsubscribe = bus.subscribe(SchedulerTick, received.append)

    unsubscribe()
    unsubscribe()
    bus.publish(SchedulerTick())

    assert received == []
