# ScreenSense: Phased Roadmap

**Assumption:** ~10 weeks, 1-3 people. Compress or stretch by merging phases. Each phase ends with a **gate**: don't start the next until the gate is met.

---

## Phase 0: Foundations (Week 1)

**Goal:** Decide scope, set up tooling, finish literature basis.

- [ ] Finalize PRD scope (freeze P0 list)
- [ ] Repo, venv, `pyproject.toml`, pre-commit (ruff, black), pytest
- [ ] Read/inspect reference repos (Blink Eye, VigilAI, etc.) and note ideas (not code)
- [ ] Collect 6-10 citations: CVS prevalence, 20-20-20 rule, blink rate reduction at screens, habit-formation/gamification in digital health
- [ ] Wireframes (tray, overlay, Eye Yoga, dashboard, onboarding)

**Deliverables:** `PRD.md` frozen, wireframes, repo skeleton, reference list
**Gate:** Skeleton app launches a tray icon; CI runs an empty test suite.

---

## Phase 1: Core Reminder Engine, MVP (Weeks 2-3)

**Goal:** A working tray app with reliable break timing.

- [ ] Config model + settings persistence
- [ ] Scheduler state machine (WORKING → PROMPTING → ON_BREAK → WORKING), snooze/skip
- [ ] Break overlay (simple 20 s countdown)
- [ ] SQLite schema v1 (`settings`, `breaks`), migrations
- [ ] Unit tests for scheduler with fake clock

**Gate:** App runs 2 hours unattended, reminders fire on time, survives sleep/resume.

---

## Phase 2: Tracking & Context Awareness (Weeks 3-4)

**Goal:** Know what the user is doing; stay quiet when needed.

- [ ] Windows adapters: idle, foreground window, fullscreen, power events
- [ ] Context evaluator with decision table + tests
- [ ] Suppress/queue logic; natural-break detection
- [ ] Tracker writes `usage_hourly`
- [ ] Settings: work hours, allow/deny lists
- [ ] Manual test matrix: PowerPoint slideshow, YouTube fullscreen, Zoom/Teams call, game, lock screen

**Gate:** Zero popups across the manual matrix; queued reminder shows ≤ 10 s after context clears.

---

## Phase 3: Active Intervention, Eye Yoga (Weeks 4-5)

**Goal:** Deliver the core novelty.

- [ ] Routine JSON + player (6 × 10 s steps)
- [ ] Animations per step (simple vector/Lottie-like; reduced-motion fallback)
- [ ] Pause/exit, optional audio cue
- [ ] Manual launch from tray; "Start Eye Yoga" from reminder
- [ ] Log `yoga_sessions`
- [ ] Review exercise wording (general relaxation guidance; add disclaimer)

**Gate:** 3 test users complete routine without help; average rating ≥ 4/5 for clarity.

---

## Phase 4: Dashboard, Score & Gamification (Weeks 5-7)

**Goal:** Insight and positive reinforcement.

- [ ] Scoring engine + tests with edge cases (no breaks due, partial day)
- [ ] Daily rollup job (at midnight and on app start for missed days)
- [ ] Streaks with weekly freeze; badges
- [ ] Dashboard: score ring, timeline, 7/30-day charts, longest stretch
- [ ] Insight text generator
- [ ] Export (CSV/JSON) + delete-all

**Gate:** Simulated 30-day dataset produces correct scores/streaks; dashboard renders < 1 s.

---

## Phase 5: Optional Blink Monitor (Weeks 7-8) *(stretch, cut first if late)*

**Goal:** Privacy-safe blink-rate sensing.

- [ ] Consent screen + tray camera indicator + kill switch
- [ ] Vision worker process (OpenCV + MediaPipe), EAR computation
- [ ] Calibration flow (10 s)
- [ ] Blink state machine; per-minute aggregation → `blink_minutely`
- [ ] Integrate blink component into score
- [ ] (P2) Adaptive reminder pull-forward
- [ ] Verification: no images on disk, no network traffic

**Gate:** ≥ 90% agreement with manual blink counts on 10 clips (state conditions: lighting, glasses); CPU ≤ 15%.

---

## Phase 6: Polish, Onboarding & Packaging (Week 9)

- [ ] Onboarding (3 screens), privacy promise, "what we store" screen
- [ ] Themes (dark/light), accessibility pass (keyboard, contrast, reduced motion)
- [ ] Autostart toggle, crash recovery
- [ ] PyInstaller build + clean-machine install test
- [ ] README, user guide, demo video script

**Gate:** Fresh Windows machine: install → first reminder in < 2 min.

---

## Phase 7: Evaluation & Final Report (Week 10)

- [ ] Pilot with 5-10 users (≥ 3 days): SUS, break completion, suppression stats, pre/post symptom self-report
- [ ] Technical evaluation: CPU/RAM, blink accuracy, privacy audit
- [ ] Limitations and ethics section, future work
- [ ] Final report, slides, live demo rehearsal

**Gate:** Report + demo ready.

---

## Timeline Summary

| Week | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|------|---|---|---|---|---|---|---|---|---|----|
| Phase 0 | ■ | | | | | | | | | |
| Phase 1 | | ■ | ■ | | | | | | | |
| Phase 2 | | | ■ | ■ | | | | | | |
| Phase 3 | | | | ■ | ■ | | | | | |
| Phase 4 | | | | | ■ | ■ | ■ | | | |
| Phase 5 | | | | | | | ■ | ■ | | |
| Phase 6 | | | | | | | | | ■ | |
| Phase 7 | | | | | | | | | | ■ |

## Scope-Cut Order (if behind schedule)

1. Adaptive reminders (FR-17), then weekly insights (FR-18)
2. Entire blink monitor (Phase 5); the project still matches all four novelty claims without it
3. Badges, then themes
4. Call detection by window title (keep process-name only)

## Definition of Done (per feature)

Code merged with tests · documented in README/CHANGELOG · manually verified on Windows 10 and 11 · no new network or disk-persisted image paths · wording reviewed against STYLE_GUIDE.
