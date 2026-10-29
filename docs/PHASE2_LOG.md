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
