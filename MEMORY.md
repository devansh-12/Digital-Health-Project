# ScreenSense: Project Memory

> Living context file. Paste it at the start of any new AI/chat/coding session (or save it as `CLAUDE.md` / `AGENTS.md` in the repo root) so the assistant instantly knows the project. **Update the "Current State" and "Decision Log" at the end of each session.**

---

## 1. Project Snapshot

- **Name:** ScreenSense: eye wellness, smart screen time and wellness app
- **Context:** Digital Health course project (academic, not a commercial/medical product)
- **Platform (v1):** Windows 10/11 desktop, tray app
- **Stack:** Python 3.11+, PyQt6, SQLite, OpenCV + MediaPipe (optional blink module), pytest, PyInstaller
- **One-liner:** Privacy-first desktop app that actively guides eye recovery (60 s Eye Yoga), stays quiet in meetings/fullscreen/idle, and builds habits with a Wellness Score and streaks, all on-device.

## 2. The Four Novelty Pillars (never lose these)

1. **Active intervention:** guided interactive 60-second Eye Yoga, not a passive popup.
2. **Context-aware scheduling:** suppress during fullscreen apps, calls, idle; queue and deliver later.
3. **Positive behavioral nudging:** Wellness Score + streaks (with weekly freeze), badges; no punishment, no screen locking.
4. **Privacy-first local architecture:** local SQLite, no accounts, no cloud, no stored images.

## 3. Hard Constraints / Rules for Any Assistant

- NEVER add networking, telemetry, accounts, or cloud features.
- NEVER store camera frames or window titles. The blink module outputs aggregated numbers only.
- NEVER make medical claims. Use wording from `STYLE_GUIDE.md` §1.3 and include the disclaimer.
- NEVER lock/block the screen. Every overlay must be dismissible.
- Do NOT copy code from reference repos (Blink Eye is GPLv3 with extra commercial restrictions). Reimplement ideas independently.
- `core/` must not import `ui/` or OS-specific modules; OS access only through `platform/` interfaces.
- Use an injected Clock for all time logic (testability).
- Keep scope per `PHASES.md`; cut order is defined there.

## 4. Reference Projects (inspiration only)

| Repo | What we take as an *idea* |
|------|---------------------------|
| nomandhoni-cs/blink-eye | 20-20-20 timers, full-screen reminder UX, usage stats, workday scheduling. GPLv3 + commercial restrictions → don't copy |
| Aarchishya/VigilAI | MediaPipe face mesh, EAR/MAR concepts, CSV logging, threshold validation (drop its screenshot saving) |
| andregaeta/BlinkWell, ikenai-lab/void-tracker, AbhiEE03/Eye_Strain_Detector, TanishkaVashishth/attention-drift-and-fatigue-detection | *Not yet reviewed.* TODO: skim READMEs and record takeaways here |

## 5. Key Specs (quick reference)

- Defaults: work interval 20 min · quick break 20 s · long break 5 min every 3rd break · idle threshold 120 s · snooze 5 min · screen goal 8 h · yoga target 3/day
- Context priority: LOCKED > OUTSIDE_HOURS > IDLE > CALL > FULLSCREEN > FREE
- Yoga routine: Palming, Fast blinking, Figure eight, Near-far focus, Up-down-left-right, Slow eye rolls (10 s each)
- Score weights (blink on): breaks 40 / yoga 20 / screen 25 / blink 15. Blink off: 50 / 25 / 25 / 0
- Streak day counts if score ≥ 60 and ≥ 1 break completed; 1 freeze per ISO week
- Blink: EAR threshold = 0.75 × calibrated baseline (fallback 0.21); blink = 2-6 frames below; adaptive trigger if < 8 blinks/min for 3 min

## 6. Document Map

| File | Purpose |
|------|---------|
| `PRD.md` | What and why: goals, personas, stories, requirements, evaluation |
| `ARCHITECTURE.md` | How: modules, state machine, data model, vision pipeline, security |
| `PHASES.md` | When: roadmap, gates, scope-cut order |
| `STYLE_GUIDE.md` | Voice, UI design system, code and doc conventions |
| `MEMORY.md` | This file: session context and decisions |
| `README.md` | Index of these docs |

## 7. Current State *(update every session)*

- **Phase:** 2 (tracking & context awareness; runbook implementation chunks complete, gate not yet passed)
- **Done:** Phase 0 and Phase 1 implementation; Phase 2 chunks 2.1a–2.7, including Windows adapter code, context evaluation, suppression/queueing, hourly tracking, SQLite persistence, work-hours/process-rule settings, simulated eight-hour integration test, and the manual test matrix. Phase 2 checks: ruff clean, strict mypy on `screensense/core` clean, 166 pytest tests pass.
- **In progress:** Windows 10/11 manual validation. Production `app.py` still does not poll idle/window adapters or drive `ContextEvaluator` and `Scheduler.tick`; this runtime wiring must be completed before the manual gate can be meaningfully run.
- **Next up:** (1) wire production adapter polling/context evaluation/scheduler ticks using injected time and persisted settings/rules; (2) run the Windows 10/11 adapter, settings, and manual matrix checks; (3) after the Phase 2 gate passes, begin Phase 3 Eye Yoga.
- **Blockers / open questions:** the Phase 2 gate remains unmet pending runtime wiring and Windows evidence; other open questions are listed in §9.

## 8. Decision Log

| Date | Decision | Reason |
|------|----------|--------|
| (start) | Python + PyQt6 over Tauri/Rust | Faster delivery; reuse MediaPipe/OpenCV; team skills |
| (start) | Windows-only v1 | Fullscreen/idle detection is OS-specific; limits test matrix |
| (start) | Blink monitor is opt-in and a stretch phase | Privacy perception and schedule risk; core novelty doesn't depend on it |
| (start) | No window titles stored | Privacy; only process names kept in rules |
| (start) | Streak freeze (1/week) | Positive nudging; avoids punitive resets |
| 2026-10-30 | Context rules are matched against normalized executable names; work hours use local weekdays and an exclusive end time | Keep persisted context data to process names and make schedule boundaries deterministic |
| 2026-10-30 | Completing a queued reminder finalizes its existing suppressed row; skipping it leaves the row suppressed | Avoid duplicate break records while preserving suppressed-versus-completed outcomes |
| 2026-10-30 | Phase 2 code tests do not substitute for the Windows gate; production polling and scheduler tick wiring remains required | The current app entry point does not yet connect platform sampling to context evaluation and scheduler decisions |

## 9. Open Questions

- [ ] Team size and exact deadline (adjust PHASES.md)
- [ ] Is a webcam feature acceptable to the course instructor's ethics expectations? (consent flow is designed; confirm)
- [ ] Which symptom questionnaire to adapt for pre/post evaluation?
- [ ] License for our own code (MIT vs Apache-2.0)?
- [ ] Review the 4 unread reference repos
- [ ] Complete production idle/window polling, ContextEvaluator wiring, and scheduler ticking before attempting the Phase 2 manual gate.
- [ ] Run 2.1b idle detection check on Windows 10 and 11.
- [ ] Run 2.1c foreground/fullscreen checks on Windows 10 and 11, including multi-monitor cases.
- [ ] Run 2.1d autostart and lock/unlock/sleep/resume checks on Windows 10 and 11.
- [ ] Run 2.6 settings persistence and “Always allow here” process-only check on Windows 10 and 11.
- [ ] Run all rows in `docs/PHASE2_MANUAL_TEST_MATRIX.md` on Windows 10 and 11 and capture the required sanitized timing evidence.

## 10. Glossary

**CVS / DES:** Computer Vision Syndrome / Digital Eye Strain · **20-20-20:** every 20 min, look 20 ft away for 20 s · **EAR:** Eye Aspect Ratio (landmark-based eye openness) · **MAR:** Mouth Aspect Ratio (yawn cue) · **Natural break:** idle time ≥ break length, counted as a break · **Suppression:** withholding a reminder due to context · **Wellness Score:** 0-100 daily habit score (not a medical metric)

## 11. Prompt Starter for New Sessions

> You are helping me build ScreenSense (see MEMORY.md). Follow the hard constraints in §3. We are in Phase X working on Y. Before coding, restate the relevant requirement IDs from PRD.md and the module boundaries from ARCHITECTURE.md. Write tests alongside code. At the end, give me an updated "Current State" and any new Decision Log entries.
