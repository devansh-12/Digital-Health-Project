# Phase 2 example day

This sequence describes how the implemented module APIs are intended to cooperate. Items marked **pending wiring** are not currently connected by `screensense/app.py`.

```mermaid
sequenceDiagram
    autonumber
    participant App as App orchestration
    participant Platform as Windows adapters
    participant Context as Context evaluator
    participant Bus as Event bus
    participant Scheduler
    participant Overlay
    participant Storage as SQLite repositories

    Note over App,Storage: 10:00 Zoom call; the reminder becomes due at 10:20
    App->>Platform: poll idle, foreground, power state (pending wiring)
    Platform-->>App: idle seconds + WindowInfo (title memory-only)
    App->>Context: evaluate(inputs with now and current rules)
    Context->>Storage: ContextRulesRepository.load_all()
    Storage-->>Context: process rules
    Context->>Bus: publish ContextChanged(CALL)
    Note over App,Scheduler: Pending wiring: subscribe to ContextChanged and call scheduler.tick(CALL)
    App->>Scheduler: tick(CALL) (pending wiring)
    Note over Scheduler: Work time continues; no prompt while CALL
    App->>Scheduler: tick(CALL) at 10:20 (pending periodic tick)
    Scheduler->>Storage: record_suppressed(due time, quick/long kind)
    Note over Scheduler: Keep one queued prompt during the call

    Note over App,Storage: 10:25 call ends
    App->>Platform: poll foreground state (pending wiring)
    Platform-->>App: FREE context inputs
    App->>Context: evaluate(FREE)
    Context->>Bus: publish ContextChanged(FREE) after 2 s stable
    App->>Scheduler: tick(FREE) (pending wiring)
    Scheduler->>Bus: publish ShowPrompt with recovery copy
    Bus-->>Overlay: queued Qt delivery
    Overlay-->>App: user chooses an action

    Note over App,Storage: Lunch idle lasts longer than the break threshold
    App->>Platform: poll idle duration (pending wiring)
    Platform-->>App: idle >= configured threshold
    App->>Context: evaluate(IDLE)
    Context->>Bus: publish ContextChanged(IDLE)
    App->>Scheduler: tick(IDLE) (pending wiring)
    Scheduler->>Storage: record_natural(due time, duration)
    Scheduler->>Bus: publish BreakCompleted(kind=natural)

    Note over App,Storage: Afternoon YouTube fullscreen; due prompt waits until fullscreen clears
    App->>Platform: poll foreground rectangle and style (pending wiring)
    Platform-->>App: WindowInfo(is_fullscreen=true)
    App->>Context: evaluate(FULLSCREEN)
    Context->>Bus: publish ContextChanged(FULLSCREEN)
    App->>Scheduler: tick(FULLSCREEN) (pending wiring)
    Note over Scheduler: Work time continues; a due prompt is queued once
    Scheduler->>Storage: record_suppressed(due time, quick/long kind)
    App->>Platform: observe player exits fullscreen (pending wiring)
    Platform-->>App: FREE context inputs
    App->>Context: evaluate(FREE)
    Context->>Bus: publish ContextChanged(FREE) after 2 s stable
    App->>Scheduler: tick(FREE) (pending wiring)
    Scheduler->>Bus: publish one ShowPrompt within 10 s
    Bus-->>Overlay: queued Qt delivery
```

## Verified implementation gaps

- `screensense/app.py` currently creates the scheduler, event bus, overlay, and tray, but it does not create platform providers, `ContextEvaluator`, repositories, or a periodic timer that calls `Scheduler.tick`.
- `ContextEvaluator` publishes `ContextChanged`; no current subscriber converts that event into a scheduler tick.
- The scheduler accepts an optional breaks repository and records suppression/natural breaks when one is supplied. The app does not currently supply one.
- The Qt event bridge already queues scheduler UI events to the Qt thread; the Windows power provider's callbacks need the platform event bridge before any UI-thread consumer handles them.
- There is no Phase 2 usage tracker or `usage_hourly` writer yet; those are covered by chunks 2.4a–2.4c.

These gaps are intentionally left for their later runbook chunks or app integration; the diagram labels all expected-but-unwired calls.
