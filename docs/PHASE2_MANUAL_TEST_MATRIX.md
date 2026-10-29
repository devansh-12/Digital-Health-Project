# Phase 2 manual test matrix

Run this checklist on Windows 10 and Windows 11 with ScreenSense active and a reminder due during each suppressing scenario. Mark one result per row. Do not record window titles, screenshots with private content, or other user content.

| Scenario | Steps | Expected | Pass/fail | Notes |
|---|---|---|---|---|
| PowerPoint slideshow | Start a slideshow; let a reminder become due; exit slideshow. | No prompt during slideshow; queued prompt appears within 10 seconds after exit. | ______ | ____________________ |
| YouTube fullscreen | Enter browser video fullscreen; let a reminder become due; exit fullscreen. | No prompt while fullscreen; queued prompt appears within 10 seconds after exit. | ______ | ____________________ |
| Zoom call | Join a call; let a reminder become due; leave the call. | No prompt during the call; queued prompt appears within 10 seconds after leaving. | ______ | ____________________ |
| Teams call | Join a call; let a reminder become due; leave the call. | No prompt during the call; queued prompt appears within 10 seconds after leaving. | ______ | ____________________ |
| Game: exclusive fullscreen | Run a game in exclusive fullscreen; let a reminder become due; return to desktop. | No prompt while the game is fullscreen; queued prompt appears within 10 seconds after returning. | ______ | ____________________ |
| Game: borderless fullscreen | Run a game borderless and covering one monitor; let a reminder become due; switch away. | No prompt while the game covers its monitor; queued prompt appears within 10 seconds after switching away. | ______ | ____________________ |
| Lock screen | Lock Windows while a reminder is due; unlock. | No prompt on the lock screen; queued prompt appears within 10 seconds after unlock. | ______ | ____________________ |
| Sleep/resume | Put the PC to sleep with a reminder due; resume. | No prompt during sleep; no sleep duration is counted as active usage; queued prompt appears within 10 seconds after context is free. | ______ | ____________________ |
| Multi-monitor | Put a fullscreen app on the secondary monitor; let a reminder become due; exit fullscreen. Repeat with the primary monitor. | Fullscreen suppression follows the app's monitor; no prompt while fullscreen; queued prompt appears within 10 seconds after exit. | ______ | ____________________ |
| Idle: 2 minutes | Stop keyboard and pointer input for 2 minutes while a reminder is due; resume input. | No prompt during idle; the work timer pauses; a queued prompt appears within 10 seconds after the context clears unless a natural break was counted. | ______ | ____________________ |
| Idle: 5 minutes | Stop keyboard and pointer input for 5 minutes; resume work. | Idle counts as a natural break; no stale prompt appears immediately after returning. | ______ | ____________________ |

## Evidence to collect

- Windows version/build and ScreenSense commit or package version for each run.
- A pass/fail result and short note for every row above, on both Windows 10 and Windows 11.
- For every suppression row, confirm the overlay stayed absent for the entire scenario.
- For every queued-reminder row, record elapsed seconds from clearing the context to the overlay appearing; each must be 10 seconds or less.
- For the 2-minute idle case, note whether the timer paused. For the 5-minute case, confirm the natural-break behavior and absence of an immediate stale prompt.
- For multi-monitor, note which monitor was used and whether fullscreen detection matched expectations.
- If any row fails, include the scenario, expected result, observed result, elapsed time, Windows version, and relevant sanitized logs. Do not include process window titles or user content.

## Phase 2 gate

`PHASES.md` defines the Phase 2 gate as: **Zero popups across the manual matrix; queued reminder shows ≤ 10 s after context clears.** The gate is met only when every matrix scenario passes on the target Windows versions and the queued-reminder timing evidence meets the 10-second limit.
