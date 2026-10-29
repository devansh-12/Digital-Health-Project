# ScreenSense: Architecture & Technical Design

**Version:** 1.0 | **Stack:** Python 3.11+, PyQt6, SQLite, OpenCV + MediaPipe (optional module)

---

## 1. Architectural Principles

1. **Local-only.** No sockets, no analytics SDKs, no auto-update pings in v1.
2. **Modular monolith.** One installable app, clean module boundaries, event-driven communication.
3. **OS code behind interfaces.** Windows implementation first; `platform/` adapters allow later ports.
4. **Optional components are isolated.** The blink monitor runs in a separate process and can be disabled with zero effect on the core.
5. **Numbers, not images.** Vision output is aggregated metrics only.

---

## 2. High-Level Diagram

```
┌──────────────────────────────── ScreenSense Process ────────────────────────────────┐
│                                                                                      │
│   ┌──────────┐    events    ┌─────────────┐   state    ┌────────────────────────┐    │
│   │ Platform │ ───────────► │  Event Bus  │ ◄───────── │  Scheduler / Engine    │    │
│   │ Adapters │              │ (Qt signals)│            │ (state machine)        │    │
│   │ • idle   │              └──────┬──────┘            └───────────┬────────────┘    │
│   │ • window │                     │                               │ decisions       │
│   │ • process│        ┌────────────┼─────────────┬─────────────────┤                 │
│   └──────────┘        ▼            ▼             ▼                 ▼                 │
│                ┌───────────┐ ┌───────────┐ ┌───────────┐   ┌───────────────┐        │
│                │ Context   │ │ Tracker   │ │ Scoring & │   │ UI Layer      │        │
│                │ Evaluator │ │ (sessions)│ │ Gamify    │   │ Tray/Overlay/ │        │
│                └───────────┘ └─────┬─────┘ └─────┬─────┘   │ Dashboard/    │        │
│                                    │             │         │ Eye Yoga      │        │
│                                    ▼             ▼         └───────────────┘        │
│                              ┌─────────────────────────┐                            │
│                              │ Storage (SQLite, WAL)   │                            │
│                              └─────────────────────────┘                            │
└──────────────────────────────────────────▲───────────────────────────────────────────┘
                                           │ metrics only (blink/min, face present)
                              ┌────────────┴─────────────┐
                              │ Vision Worker (process)  │  OPTIONAL, opt-in
                              │ OpenCV → MediaPipe → EAR │
                              └──────────────────────────┘
```

---

## 3. Module Breakdown

### 3.1 Project Structure

```
screensense/
├── app.py                      # entry point, wiring
├── core/
│   ├── events.py               # event definitions + bus
│   ├── scheduler.py            # break state machine
│   ├── context.py              # suppression rules
│   ├── tracker.py              # active/idle sessions
│   ├── scoring.py              # wellness score
│   ├── gamification.py         # streaks, badges
│   └── config.py               # settings model + validation
├── platform/
│   ├── base.py                 # abstract interfaces
│   ├── windows.py              # Win32 implementations
│   └── stub.py                 # fake adapter for tests
├── storage/
│   ├── db.py                   # connection, migrations
│   ├── repositories.py         # DAOs
│   └── migrations/             # 001_init.sql ...
├── vision/                     # optional
│   ├── worker.py               # multiprocessing entry
│   ├── blink.py                # EAR + blink state machine
│   └── calibration.py
├── ui/
│   ├── tray.py
│   ├── overlay.py              # break reminder window
│   ├── eye_yoga/               # routine definitions + animation widgets
│   ├── dashboard/              # charts, score ring
│   ├── onboarding.py
│   ├── settings.py
│   └── theme/                  # QSS, colors, icons
├── assets/                     # icons, sounds, animations
├── tests/
└── docs/
```

### 3.2 Platform Adapters (`platform/base.py`)

| Interface | Method | Windows implementation |
|-----------|--------|------------------------|
| `IdleProvider` | `seconds_since_input() -> float` | `GetLastInputInfo` (ctypes) |
| `WindowProvider` | `foreground() -> WindowInfo(title, process, rect, is_fullscreen)` | `GetForegroundWindow`, `GetWindowRect`, `MonitorFromWindow`, `psutil` for process name |
| `PowerProvider` | signals on sleep/resume/lock | `WM_POWERBROADCAST`, session notifications |
| `AutostartProvider` | `enable()/disable()` | Registry `Run` key or Startup folder |

Adapters poll every 1-2 s (cheap) and emit events only on change.

### 3.3 Context Evaluator

Returns `ContextState` ∈ {`FREE`, `IDLE`, `FULLSCREEN`, `CALL`, `OUTSIDE_HOURS`, `LOCKED`}.

Decision order (first match wins):
1. Session locked / asleep → `LOCKED`
2. Outside configured work hours → `OUTSIDE_HOURS`
3. Idle ≥ `idle_threshold` (default 120 s) → `IDLE`
4. Foreground process in **call list** (zoom, teams, webex, slack huddle) **or** window title matches call patterns ("Meet -", "Zoom Meeting") → `CALL`
5. Foreground window fullscreen (rect ≥ monitor rect, no title-bar) and process not in **allow-list** → `FULLSCREEN`
6. Else → `FREE`

User overrides: "always allow reminders in this app" / "never remind in this app" stored in `context_rules`.

### 3.4 Scheduler State Machine

```
        ┌────────┐ work_elapsed ≥ interval && ctx=FREE ┌───────────┐
 start─►│WORKING │────────────────────────────────────►│ PROMPTING │
        └───┬────┘                                      └──┬─┬─┬────┘
            │ ctx≠FREE: pause work timer                   │ │ └─ snooze ──► SNOOZED ─(5 min)─► PROMPTING
            │ ctx=IDLE ≥ break_len: count natural break    │ └─── skip ───► WORKING (log skip)
            ▼                                              ▼
        ┌────────┐                                   ┌───────────┐
        │SUPPRESS│ ctx→FREE: if due, queue 1 prompt  │ ON_BREAK  │ (quick break or Eye Yoga)
        └────────┘                                   └────┬──────┘
                                                          │ completed → log, update score
                                                          ▼
                                                      WORKING (timer reset)
```

Rules:
- Work timer only advances while `ctx == FREE` or `FULLSCREEN`/`CALL` (user is still working) but **prompts are only shown when `FREE`**. Due prompts are queued (max 1) and shown ≤ 10 s after context returns to `FREE`.
- Idle ≥ break length (20 s) counts as a **natural break**, so the timer resets and the user is not nagged after returning.
- Every 3rd break (≈ hourly) is a **long break** (default 5 min).
- Timers use monotonic clocks; wall-clock jumps and sleep/resume are handled via PowerProvider events.

### 3.5 Tracker

Samples state every 5 s into aggregated rows (not per-sample forever):
- `active_seconds`, `idle_seconds`, `fullscreen_seconds`, `call_seconds` per hour bucket.
- Longest unbroken active stretch computed from breaks + idle gaps.

### 3.6 Eye Yoga Engine

Routine defined as data (JSON), rendered by a generic player:

```json
{
  "id": "eye_yoga_60",
  "total_seconds": 60,
  "steps": [
    {"name": "Palming", "seconds": 10, "text": "Rub palms, cup them over closed eyes. Breathe slowly.", "anim": "palming"},
    {"name": "Fast blinking", "seconds": 10, "text": "Blink gently and quickly, then close eyes for 2 s.", "anim": "blink"},
    {"name": "Figure eight", "seconds": 10, "text": "Trace a big sideways 8 with your eyes.", "anim": "fig8"},
    {"name": "Near-far focus", "seconds": 10, "text": "Focus on your thumb, then something far away. Switch.", "anim": "nearfar"},
    {"name": "Up-down-left-right", "seconds": 10, "text": "Look in each direction, holding 1-2 s without moving your head.", "anim": "compass"},
    {"name": "Slow eye rolls", "seconds": 10, "text": "Roll eyes in a slow circle, then reverse.", "anim": "roll"}
  ]
}
```

Features: per-step progress ring, pause/exit, optional soft chime, reduced-motion mode. Completion logs `yoga_sessions(completed_steps, duration)`.

### 3.7 Scoring Engine (`scoring.py`)

```
break_score   = completed_breaks / max(due_breaks, 1)              (cap 1.0)
yoga_score    = min(yoga_sessions / yoga_target, 1.0)              (default target 3)
screen_score  = 1.0 if active_h ≤ goal
                else max(0, 1 − (active_h − goal) / (0.5 × goal))
blink_score   = minutes_with_rate≥12 / monitored_minutes           (if enabled)

weights (blink on):  0.40, 0.20, 0.25, 0.15
weights (blink off): 0.50, 0.25, 0.25, 0.00   # redistributed

score = round(100 × Σ weight × component)
```

Explanation text is generated from the lowest component ("Your score was held back by screen time: 9.5 h vs your 8 h goal").

### 3.7.1 Streaks & Badges

- A day **counts** if score ≥ 60 and at least 1 break completed.
- **Freeze:** 1 miss per ISO week doesn't reset the streak.
- Badges (examples): *First Look Away*, *Yogi* (10 sessions), *Week Warrior* (7-day streak), *Iron Eyes* (30), *Night Owl Recovery* (score ≥ 80 after a < 40 day).
- No punitive mechanics: no lost points, no shame wording.

### 3.8 Vision Worker (optional)

**Process model:** `multiprocessing.Process` started on opt-in; communicates over a `Queue` sending **only** dicts such as `{"t": ts, "face": true, "blinks": 3, "ear_mean": 0.27}` once every 10 s.

**Pipeline per frame (10-15 FPS):**
1. Capture (OpenCV, 640×480).
2. MediaPipe Face Mesh landmarks (refine_landmarks=True).
3. EAR = (‖p2−p6‖ + ‖p3−p5‖) / (2‖p1−p4‖) per eye, averaged.
4. Blink = EAR < `thr` for 2-6 consecutive frames; `thr` = 0.75 × calibrated open-eye median (fallback 0.21).
5. Frame discarded. Nothing written to disk.

**Calibration:** 10-second guided "look at the screen normally" step to compute baseline EAR (handles glasses, eye shape).

**Derived metrics:** blinks/min (rolling 1-min), face-present ratio, long-closure events (> 1 s, treated as a possible drowsiness hint, not a diagnosis).

**Adaptive rule (P2):** if blink rate < 8/min for 3 consecutive minutes → pull next reminder forward (min 5 min before due) and suggest the blink-focused Eye Yoga step. Rate limited to once per 20 min.

**Safeguards:** visible tray camera indicator, one-click disable, auto-stop on lock/idle, camera released immediately on stop.

---

## 4. Data Model (SQLite)

```sql
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

CREATE TABLE usage_hourly (
  id INTEGER PRIMARY KEY,
  hour_start INTEGER NOT NULL,           -- epoch, truncated to hour
  active_s INTEGER DEFAULT 0, idle_s INTEGER DEFAULT 0,
  fullscreen_s INTEGER DEFAULT 0, call_s INTEGER DEFAULT 0,
  UNIQUE(hour_start)
);

CREATE TABLE breaks (
  id INTEGER PRIMARY KEY,
  due_at INTEGER NOT NULL, shown_at INTEGER,
  kind TEXT CHECK(kind IN ('quick','long','yoga','natural')),
  outcome TEXT CHECK(outcome IN ('completed','snoozed','skipped','suppressed','expired')),
  duration_s INTEGER
);

CREATE TABLE yoga_sessions (
  id INTEGER PRIMARY KEY, started_at INTEGER NOT NULL,
  steps_completed INTEGER, total_steps INTEGER, duration_s INTEGER
);

CREATE TABLE blink_minutely (          -- only if monitor enabled; aggregated numbers
  minute_start INTEGER PRIMARY KEY,
  blinks INTEGER, face_present_ratio REAL, ear_mean REAL
);

CREATE TABLE daily_scores (
  day TEXT PRIMARY KEY,                -- YYYY-MM-DD local
  score INTEGER, break_c REAL, yoga_c REAL, screen_c REAL, blink_c REAL,
  counted_for_streak INTEGER
);

CREATE TABLE streaks (id INTEGER PRIMARY KEY, current INTEGER, best INTEGER, last_counted_day TEXT, freeze_week TEXT);
CREATE TABLE badges (code TEXT PRIMARY KEY, earned_at INTEGER);
CREATE TABLE context_rules (process TEXT PRIMARY KEY, rule TEXT CHECK(rule IN ('allow','deny','call','fullscreen_ok')));
```

**Retention:** hourly and minutely rows kept 90 days by default (configurable), then rolled up; daily scores kept indefinitely. DB file lives in user app-data folder. Optional SQLCipher encryption is a stretch goal.

---

## 5. Threading & Performance

- **Main/UI thread:** Qt event loop only.
- **Polling:** `QTimer` (1-2 s) for platform adapters (very cheap Win32 calls).
- **DB writes:** batched every 30-60 s on a worker thread (`QThreadPool`); WAL mode.
- **Vision:** separate process to avoid GIL contention and to guarantee UI responsiveness.
- **Budget:** idle < 3% CPU; blink monitor 10-15 FPS, 640×480.

---

## 6. Security & Privacy Design

| Concern | Control |
|---------|---------|
| Network | No networking libs imported; CI check greps for `requests`, `socket`, `urllib3` |
| Camera | Opt-in, consent dialog, tray indicator, frames never persisted, process isolation |
| Window titles | Used in memory for context detection; **not stored** (only process names in rules) |
| Data at rest | Local SQLite in `%APPDATA%/ScreenSense`; export and delete-all in Settings |
| Packaging | PyInstaller one-folder build; checksums published |

"What we store" screen lists every table in plain language.

---

## 7. Testing Strategy

| Level | Scope | Tools |
|-------|-------|-------|
| Unit | scheduler transitions, scoring maths, streak/freeze logic, context decision table | pytest, fake clock, `platform/stub.py` |
| Integration | scheduler + tracker + storage over simulated days | pytest + temp DB |
| Vision | EAR calc on synthetic landmarks; blink detector on recorded EAR traces | pytest |
| Manual | fullscreen/call scenarios (PowerPoint show, YouTube fullscreen, Zoom), sleep/resume | checklist |
| Performance | CPU/RAM over 1 hr | Task Manager / psutil logger |
| Usability | SUS, think-aloud | pilot |

---

## 8. Technology Choices & Rationale

| Choice | Why | Alternative |
|--------|-----|-------------|
| Python + PyQt6 | Fastest path; reuses MediaPipe/OpenCV ecosystem | Tauri/Rust (as in Blink Eye): faster binary, steeper curve |
| SQLite | Zero-config, local, queryable | JSON files (harder analytics) |
| MediaPipe Face Mesh | Accurate eye landmarks, CPU-friendly | dlib (heavier install) |
| PyInstaller | Simple Windows distribution | Nuitka / MSIX |
| pyqtgraph or Matplotlib | Charts in dashboard | Plotly (web view overhead) |

---

## 9. Licensing Note

Reference projects (e.g., Blink Eye: GPLv3 with additional commercial restrictions) are used for **inspiration only**. ScreenSense is an independent implementation; cite references in the report. Choose your own license (MIT/Apache-2.0 are common for course projects).
