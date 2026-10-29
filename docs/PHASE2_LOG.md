# Phase 2 implementation log

## 2.1a Platform interfaces + stub

- **Files changed:** `screensense/platform_adapters/base.py`, `screensense/platform_adapters/stub.py`, `screensense/tests/platform_adapters/test_stub.py`, `screensense/core/config.py`, `screensense/tests/core/test_config.py`, `screensense/ui/overlay.py`.
- **Test result:** `ruff check .`, strict mypy on `screensense/core`, and `PYTHONPATH=. pytest -q` pass (67 passed).
- **Manual check:** none required for this chunk.

## 2.1b Windows idle provider

- **Files changed:** `screensense/platform_adapters/windows.py`, `screensense/tests/platform_adapters/test_windows_idle.py`.
- **Test result:** `ruff check .`, strict mypy on `screensense/core`, and `PYTHONPATH=. pytest -q` pass (71 passed).
- **Manual check (pending Windows):** run a short script that prints `WindowsIdleProvider().seconds_since_input()` once per second; confirm it rises while hands are off mouse/keyboard and resets close to zero after input.

## 2.1c Windows foreground + fullscreen

- **Files changed:** `screensense/platform_adapters/windows.py`, `screensense/tests/platform_adapters/test_windows_window.py`.
- **Test result:** `ruff check .`, strict mypy on `screensense/core`, and `PYTHONPATH=. pytest -q` pass (88 passed).
- **Manual check (pending Windows):** print foreground process and `is_fullscreen` while switching among a maximized browser, YouTube fullscreen via F11 and player control, and a PowerPoint slideshow. Repeat with a second monitor.
- **Edge cases:** monitor bounds come from `MonitorFromWindow(..., MONITOR_DEFAULTTONEAREST)`; borderless games qualify when they cover the selected monitor without `WS_CAPTION`; captioned maximized windows do not. Exclusive-fullscreen mode depends on Windows exposing the app's top-level window. UWP apps may report a frame-host process name. Desktop/shell windows and process access failures return `None`.

## 2.1d Windows power events + autostart

- **Files changed:** `screensense/platform_adapters/base.py`, `screensense/platform_adapters/stub.py`, `screensense/platform_adapters/windows.py`, `screensense/ui/platform_event_bridge.py`, `screensense/tests/platform_adapters/test_windows_power_autostart.py`, `screensense/tests/ui/test_platform_event_bridge.py`.
- **Test result:** `ruff check .`, strict mypy on `screensense/core`, and `PYTHONPATH=. pytest -q` pass (99 passed).
- **Manual check (pending Windows):** enable autostart and confirm ScreenSense under Task Manager > Startup; subscribe a short console harness to power events, start the provider, lock/unlock the PC and sleep/resume, confirm `LOCK`, `UNLOCK`, `SLEEP`, and `RESUME`, then stop the provider. The `PowerEventBridge` uses an explicit queued Qt connection so native-listener-thread callbacks run in the UI thread.

## 2.2a Context types + decision-table tests (red)

- **Files changed:** `screensense/core/context.py`, `screensense/tests/core/test_context.py`.
- **Test result:** `ruff check .` and strict mypy on `screensense/core` pass; full pytest has 28 expected failures because `evaluate` is not implemented and 100 passes.
- **Manual check:** none required for this test-first chunk.

## 2.2b Context evaluator (green)

- **Files changed:** `screensense/core/context.py`, `screensense/tests/core/test_context.py`.
- **Test result:** `ruff check .`, strict mypy on `screensense/core`, and full pytest pass (131 passed); `core/context.py` coverage is 100%.
- **Manual check:** none required for this pure evaluator chunk.
- **Rule assumption:** since the documented `ContextState` has no `DENIED` member, a per-process `deny` rule maps to `OUTSIDE_HOURS` as a suppressed context. Lock, work-hours, and idle checks take precedence over process rules.

## 2.2c Hysteresis + user rules

- **Files changed:** `screensense/core/context.py`, `screensense/core/events.py`, `screensense/storage/repositories.py`, `screensense/tests/core/test_context.py`, `screensense/tests/storage/test_repositories.py`.
- **Test result:** `ruff check .`, strict mypy on `screensense/core`, and full pytest pass (136 passed); `core/context.py` coverage is 97%.
- **Manual check:** none required for this deterministic context wrapper.

## 2.3a Suppression/queue tests (red)

- **Files changed:** `screensense/tests/core/test_scheduler.py`.
- **Test result:** `ruff check .` and strict mypy on `screensense/core` pass; full pytest has 2 expected failures (the queued-prompt recovery copy is not present yet) and 142 passes.
- **Manual check:** none required for this test-first scheduler chunk.

## 2.3b Suppression/queue implementation (green)

- **Files changed:** `screensense/core/events.py`, `screensense/core/scheduler.py`, `screensense/storage/repositories.py`, `screensense/ui/overlay.py`, `screensense/tests/core/test_scheduler.py`, `screensense/tests/storage/test_repositories.py`, `screensense/tests/ui/test_overlay.py`.
- **Test result:** `ruff check .`, strict mypy on `screensense/core`, and full pytest pass (147 passed).
- **Manual check:** none required for this pure scheduler/persistence behavior; the copy is covered by the overlay test.

## 2.3c Example-day sequence diagram

- **Files changed:** `docs/diagrams/example_day.md`.
- **Test result:** documentation-only chunk; `ruff check .`, strict mypy on `screensense/core`, and full pytest pass (147 passed).
- **Manual check:** review the diagram and its marked wiring gaps before wiring the app.

## 2.4a Tracker tests (red)

- **Files changed:** `.gitignore`, `screensense/core/tracker.py`, `screensense/tests/core/test_tracker.py`.
- **Test result:** `ruff check .` and strict mypy on `screensense/core` pass; full pytest has 9 expected failures because `Tracker` and `longest_unbroken_active_stretch` are not implemented, with 147 passes.
- **Manual check:** none required for this test-first aggregation chunk.

## 2.4b Tracker aggregation + longest stretch (green)

- **Files changed:** `screensense/core/tracker.py`, `screensense/tests/core/test_tracker.py`.
- **Test result:** `ruff check .`, strict mypy on `screensense/core`, and full pytest pass (156 passed).
- **Manual check:** none required for this deterministic aggregation logic.

## 2.4c Batched writer thread + flush

- **Files changed:** `screensense/core/tracker.py`, `screensense/platform_adapters/base.py`, `screensense/platform_adapters/stub.py`, `screensense/platform_adapters/windows.py`, `screensense/storage/repositories.py`, `screensense/ui/usage_flush.py`, `screensense/app.py`, `screensense/tests/core/test_tracker.py`, `screensense/tests/storage/test_repositories.py`, `screensense/tests/platform_adapters/test_stub.py`, `screensense/tests/platform_adapters/test_windows_power_autostart.py`, `screensense/tests/ui/test_usage_flush.py`, `docs/diagrams/example_day.md`.
- **Test result:** `ruff check .`, strict mypy on `screensense/core`, and full pytest pass (162 passed).
- **Manual check:** none beyond the 2.1d Windows power/autostart check already pending in this log; app wiring now flushes on exit and on sleep/lock, using worker-thread-owned SQLite connections.
