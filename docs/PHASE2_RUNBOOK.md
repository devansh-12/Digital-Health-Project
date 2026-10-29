# ScreenSense: Phase 2 Runbook (Tracking & Context Awareness)

Save this file as `docs/PHASE2_RUNBOOK.md` in the repo (next to `MEMORY.md` / `CLAUDE.md`).
You will only ever type ONE line per step (see "Driver prompts"). Everything else is in this file.

---

## How to use

**Claude Code (recommended):** the assistant can read this file itself.
1. Start a session (MEMORY.md saved as CLAUDE.md so it loads automatically).
2. Type: `Run the next unchecked chunk in docs/PHASE2_RUNBOOK.md`
3. Check the result, run tests, commit, then type the same line again.

**Plain chat (no file access):** paste this whole file once at the start of the chat, plus MEMORY.md, then type `next` for each step.

---

## Driver prompts (the only things you type)

| When | Type this |
|------|-----------|
| Start next chunk | `Run the next unchecked chunk in docs/PHASE2_RUNBOOK.md` (chat: `next`) |
| Chunk was wrong | `This violates [rule]. Redo the current chunk following ARCHITECTURE.md section [X].` |
| Test/run error | `Fails on Windows 11. Traceback: [paste]. Root cause in 3 sentences, minimal diff, add a regression test.` |
| Review after a module | `Review the files from the last chunk against STYLE_GUIDE.md and ARCHITECTURE.md. Prioritized list: blocker / should-fix / nit, with diffs.` |
| End of session | `Run the Session wrap-up chunk (W) in docs/PHASE2_RUNBOOK.md` |
| Idea outside scope | `Scope guard: I want to add [feature]. Compare to PRD goals/non-goals and PHASES.md.` |

---

## Standing rules (apply to EVERY chunk, do not repeat them)

1. Read MEMORY.md section 3 and the ARCHITECTURE.md sections named in the chunk first.
2. Restate the requirement IDs in one line, then state any assumption in one line.
3. Do ONLY the current chunk. Do not build ahead.
4. Show the file path above every code block. Type hints, Google-style docstrings.
5. `core/` imports no UI or OS modules. OS calls only via `platform/` interfaces.
6. Inject a Clock. No `time.sleep`, no `datetime.now()` in core logic.
7. Never store window titles or images. No networking. Do not log window titles or user content.
8. Tests mirror source paths (`core/context.py` -> `tests/core/test_context.py`). Test names describe behavior.
9. Run `ruff`, `mypy` (strict on `core/`) and `pytest` before declaring done, and report the output.
10. When finished: tick the chunk's checkbox in this file, then print:
    (a) how to run it, (b) how to test it, (c) what I should check manually, (d) a suggested commit message (Conventional Commits, with requirement IDs).
11. Then STOP and wait. Do not start the next chunk.

---

## Progress checklist (the assistant ticks these)

- [x] 2.1a Platform interfaces + stub
- [x] 2.1b Windows idle provider
- [x] 2.1c Windows foreground + fullscreen
- [x] 2.1d Windows power events + autostart
- [x] 2.2a Context types + decision-table tests (red)
- [x] 2.2b Context evaluator (green)
- [x] 2.2c Hysteresis + user rules
- [x] 2.3a Suppression/queue tests (red)
- [x] 2.3b Suppression/queue implementation (green)
- [x] 2.3c Example-day sequence diagram
- [x] 2.4a Tracker tests (red)
- [x] 2.4b Tracker aggregation + longest stretch (green)
- [x] 2.4c Batched writer thread + flush
- [x] 2.5 Integration test: simulated 8-hour day
- [x] 2.6 Settings hooks: work hours + allow/deny rules
- [ ] 2.7 Manual test matrix + gate check
- [ ] W Session wrap-up

---

## Chunks

### 2.1a Platform interfaces + stub
**Reqs:** FR-05, FR-06, FR-07 | **Read:** ARCHITECTURE.md 3.2
**Task:** In `platform/base.py` define `IdleProvider`, `WindowProvider`, `PowerProvider`, `AutostartProvider` as Protocols/ABCs, plus frozen dataclasses `WindowInfo(title, process, rect, is_fullscreen)` and `PowerEvent` enum (SLEEP, RESUME, LOCK, UNLOCK). Note in the docstring that `title` is memory-only and must never be persisted. In `platform/stub.py` write controllable fakes (set idle seconds, set foreground window, fire power events). Use the package name chosen in Phase 0 (if `platform` shadows the stdlib, use the safe alternative).
**Done when:** the stub can drive a test; mypy strict passes; a tiny test proves each fake returns what was set.

### 2.1b Windows idle provider
**Reqs:** FR-05 | **Read:** ARCHITECTURE.md 3.2
**Task:** In `platform/windows.py` implement `IdleProvider.seconds_since_input()` using `GetLastInputInfo` via ctypes. Handle the 49.7-day tick-count wraparound. Keep the ctypes call in a thin function so tests can mock it; guard imports so the module still imports on non-Windows (CI).
**Done when:** unit tests with a mocked ctypes call pass, including the wraparound case.
**Manual:** run a 10-line script that prints idle seconds; stop touching the mouse and confirm it climbs.

### 2.1c Windows foreground window + fullscreen
**Reqs:** FR-06, FR-07 | **Read:** ARCHITECTURE.md 3.2, 3.3
**Task:** Implement `WindowProvider.foreground()` with `GetForegroundWindow`, `GetWindowRect`, `MonitorFromWindow`/`GetMonitorInfo`, and psutil for the process name. `is_fullscreen` = window rect covers the whole monitor rect and has no title bar/caption style. Return `None` safely for the desktop/shell windows and on access-denied errors. Explain the edge cases: multi-monitor, borderless-windowed games, exclusive fullscreen, maximized-but-not-fullscreen windows, UWP frame host processes. Keep the pure rect comparison in a separate function and unit test it with many rect combinations.
**Done when:** rect logic tests pass; ctypes parts are mocked in tests.
**Manual:** print foreground process + is_fullscreen while switching between a maximized browser, YouTube fullscreen (F11 and the player button), and a PowerPoint slideshow.

### 2.1d Windows power events + autostart
**Reqs:** FR-01, FR-05 | **Read:** ARCHITECTURE.md 3.2
**Task:** Implement `PowerProvider` (sleep/resume via `WM_POWERBROADCAST`, lock/unlock via session notifications) and `AutostartProvider` (registry Run key, enable/disable/is_enabled). Isolate the registry access behind a small function so it can be mocked. Document how events reach the Qt thread safely.
**Done when:** autostart logic tested against a mocked registry; power event translation tested with fake messages.
**Manual:** toggle autostart and confirm in Task Manager > Startup; lock the PC and confirm the LOCK event prints.

### 2.2a Context types + decision-table tests (red)
**Reqs:** FR-05, FR-06, FR-07, FR-14, C1-C3 | **Read:** ARCHITECTURE.md 3.3
**Task:** Do NOT implement yet. Define `ContextState` (LOCKED, OUTSIDE_HOURS, IDLE, CALL, FULLSCREEN, FREE), an input dataclass (`ContextInputs`: locked, asleep, now, work_hours, idle_seconds, idle_threshold, window, rules), and `ContextRule` (allow/deny/call/fullscreen_ok). Write a parameterized decision-table test with at least 25 cases covering the priority order, every state, rule overrides (deny, allow, call, fullscreen_ok), work-hours boundaries, and title-pattern call detection. Tests must fail for now.
**Done when:** tests are collected and fail only because `evaluate` is missing.

### 2.2b Context evaluator (green)
**Reqs:** same as 2.2a
**Task:** Implement `core/context.py` `evaluate(inputs) -> ContextState` as a pure function using the decision order in ARCHITECTURE.md 3.3 (first match wins). Make all 2.2a tests pass without editing them (if a test is wrong, say why and propose the change first).
**Done when:** 25+ tests pass; coverage on `core/context.py` is at least 90%.

### 2.2c Hysteresis + user rules
**Reqs:** C1-C2, risk mitigation in PRD section 8
**Task:** Add a stateful `ContextEvaluator` wrapper with the injected Clock that debounces changes shorter than 2 seconds (no flicker between states), loads `context_rules` from the repository, and emits a `ContextChanged` event only on actual change. Tests with FakeClock for rapid flapping, a change that persists past 2 s, and rule updates taking effect immediately.
**Done when:** hysteresis tests pass; no real sleeping in tests.

### 2.3a Suppression/queue tests (red)
**Reqs:** FR-08, C3, C4, A1 | **Read:** ARCHITECTURE.md 3.4
**Task:** Do NOT implement yet. Extend the scheduler tests with FakeClock for: prompt due during CALL is queued (max one) and delivered within 10 s after FREE with the copy "Meeting's over. Want a quick eye break?"; two prompts due while suppressed still yield one; idle at least as long as the break length counts as a natural break and resets the work timer; timer behavior while CALL/FULLSCREEN (keeps advancing, prompt withheld); IDLE and LOCKED pause the timer.
**Done when:** new tests fail for the right reasons.

### 2.3b Suppression/queue implementation (green)
**Reqs:** same as 2.3a
**Task:** Extend `core/scheduler.py` to make the tests pass, following the SUPPRESSED rules in ARCHITECTURE.md 3.4. Record suppressed prompts via the breaks repository (`outcome='suppressed'`) and natural breaks (`kind='natural'`). Do not break the Phase 1 scheduler tests.
**Done when:** all scheduler tests (old and new) pass.

### 2.3c Example-day sequence diagram
**Task:** Produce a Mermaid `sequenceDiagram` of one example day (Zoom call at 10:00, idle lunch, YouTube fullscreen, returning to work) showing platform adapters, context evaluator, scheduler, overlay, and storage. Save to `docs/diagrams/example_day.md`. Verify it matches the real code behavior and list any mismatch.

### 2.4a Tracker tests (red)
**Reqs:** D1, D3, FR-09 | **Read:** ARCHITECTURE.md 3.5, 4
**Task:** Do NOT implement yet. Write tests for hourly bucket aggregation (`active`, `idle`, `fullscreen`, `call` seconds from 5 s samples), buckets spanning an hour boundary, midnight rollover, sleep gaps (not counted), and `longest_unbroken_active_stretch` (resets on breaks and on idle gaps). Include a simulated 8-hour day fixture.
**Done when:** tests fail for the right reasons.

### 2.4b Tracker aggregation + longest stretch (green)
**Task:** Implement `core/tracker.py` pure logic: sample context every 5 s via the injected Clock into hourly buckets, plus the longest-stretch function. Make 2.4a pass.

### 2.4c Batched writer thread + flush
**Reqs:** FR-09, NFR performance | **Read:** ARCHITECTURE.md 5
**Task:** Add the persistence side: batch-write every 60 s on a worker thread (QThreadPool in `app` wiring, not in `core/`; use a small writer interface so `core/` stays Qt-free), upsert into `usage_hourly`, flush on exit and on SLEEP/LOCK. Tests with a temp DB: no data loss on flush, upsert merges partial hours, a write failure does not crash the app (log without user content).
**Done when:** persistence tests pass.

### 2.5 Integration test: simulated 8-hour day
**Task:** One integration test wiring stub adapters + context evaluator + scheduler + tracker + temp DB with FakeClock. Script a day: work, call, lunch idle, fullscreen video, sleep/resume, midnight rollover. Assert breaks logged (completed, suppressed, natural), `usage_hourly` totals, and that no prompt is ever shown during CALL/FULLSCREEN.

### 2.6 Settings hooks: work hours + allow/deny rules
**Reqs:** FR-14, C1-C2
**Task:** Add work-hours schedule (e.g., Mon-Fri 9-18) and the allow/deny/call/fullscreen_ok rules to the config model and repository, plus a minimal settings UI section (list editor for rules, day/hour pickers) with inline validation and keyboard navigation. Add a "Not now / Always allow here" action on the overlay that writes a rule for the current process name only.

### 2.7 Manual test matrix + gate check
**Task:** Produce a printable checklist table for: PowerPoint slideshow, YouTube fullscreen, Zoom/Teams call, a game (exclusive and borderless), lock screen, sleep/resume, multi-monitor, idle 2 min and 5 min. Columns: scenario, steps, expected, pass/fail, notes. Then restate the **Phase 2 gate** from PHASES.md and list exactly what evidence I need to collect.
**Gate:** zero popups across the matrix; queued reminder appears within 10 s after context clears.

### W Session wrap-up
**Task:** Summarize this session for MEMORY.md in the exact format of sections 7, 8, and 9: what was completed (with requirement IDs), in progress, decisions and why, new open questions, and the next 3 tasks. Also update the checkboxes in this file.

---

## Quick troubleshooting

| Symptom | Fix |
|---------|-----|
| Assistant builds the next chunk too | Reply: `Stop. Rule 11: only the current chunk. Revert anything beyond it.` |
| Assistant invents Win32 behavior | Reply: `State which API each line relies on and what you are unsure about, then add a mock-based test for it.` |
| Tests pass but behavior feels wrong | Run the manual check in the chunk, paste the observed vs expected, use the Test/run error driver prompt |
| Context getting long | Run chunk W, start a fresh session with MEMORY.md, then `Run the next unchecked chunk...` |
| `platform` name clash | Use the renamed package from Phase 0 everywhere, including mypy and ruff config |
