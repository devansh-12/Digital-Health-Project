# ScreenSense: Product Requirements Document (PRD)

**Version:** 1.0 | **Status:** Draft | **Course:** Digital Health | **Platform:** Windows desktop (v1)

---

## 1. Overview

ScreenSense is a privacy-first desktop app that reduces digital eye strain. Instead of showing a passive "take a break" popup, it guides the user through a 60-second Eye Yoga routine, stays quiet when interruptions would be harmful (presentations, calls, idle time), and builds habits through positive reinforcement (Wellness Score, streaks). All data stays on the device.

### 1.1 Problem

- Digital Eye Strain / Computer Vision Syndrome (symptoms: dry eyes, headaches, blurred vision, neck strain) is widespread among students and office workers.
- Existing reminders are easy to dismiss, interrupt at the wrong moment, and get uninstalled.
- Many wellness trackers require accounts or cloud sync, which raises privacy concerns.

### 1.2 Vision

*"A calm, respectful companion that helps your eyes recover, without ever nagging, locking, or watching you in the cloud."*

### 1.3 Goals

| # | Goal | Success Metric |
|---|------|----------------|
| G1 | Users actually take breaks | ≥ 60% of reminders result in a completed or started break |
| G2 | Interruptions feel fair | ≤ 5% of reminders dismissed as "bad timing"; 0 popups during fullscreen/call |
| G3 | Habit formation | Median user reaches a 5-day streak within 2 weeks of pilot |
| G4 | Privacy by design | 0 network calls; 0 stored images/video; verifiable by user |
| G5 | Low overhead | < 3% CPU idle, < 150 MB RAM (excluding blink monitor); < 15% CPU with blink monitor |

### 1.4 Non-Goals (v1)

- Medical diagnosis, treatment, or any clinical claim.
- Cloud sync, accounts, social features or leaderboards.
- Mobile apps, browser extensions.
- Locking or blocking the screen.
- Posture correction beyond optional distance nudges (stretch goal).

---

## 2. Target Users & Personas

**P1: Aisha, 21, CS student.** 8-10 hrs/day on laptop, frequent night coding, skips breaks. Wants minimal friction and something that doesn't interrupt her during Zoom lectures.

**P2: Rahul, 34, remote analyst.** Back-to-back video calls, shares screen often. Hates popups during meetings. Cares about privacy at work.

**P3: Meera, 28, designer.** Dry eyes, already knows 20-20-20 but forgets. Responds well to streaks and progress charts.

---

## 3. User Stories

### Epic A: Break Reminders
- **A1** As a user, I want a reminder every N minutes (default 20) so I can rest my eyes.
- **A2** As a user, I want to snooze (5 min) or skip a reminder, so I stay in control.
- **A3** As a user, I want short breaks (20 s) and long breaks (5 min every 60 min) configurable.

### Epic B: Eye Yoga
- **B1** As a user, I want a guided 60-second routine with on-screen animation and countdown, so I know exactly what to do.
- **B2** As a user, I want to start Eye Yoga manually at any time from the tray.
- **B3** As a user, I want a mid-routine Pause and Exit, so I never feel trapped.

### Epic C: Context-Aware Scheduling
- **C1** As a user, I want no popups during fullscreen apps (slides, video, games).
- **C2** As a user, I want no popups while I'm in a call (Zoom/Teams/Meet/etc.).
- **C3** As a user, I want idle time (no input ≥ 2 min) to pause the work timer, and a long idle (≥ 5 min) to count as a natural break.
- **C4** As a user, I want suppressed reminders to be shown (gently) when the context ends.

### Epic D: Tracking & Insights
- **D1** As a user, I want to see today's active screen time and number of breaks.
- **D2** As a user, I want 7-day and 30-day trends.
- **D3** As a user, I want to see my longest unbroken stretch.

### Epic E: Positive Gamification
- **E1** As a user, I want a daily Wellness Score (0-100) with a plain-language explanation.
- **E2** As a user, I want a streak counter that forgives one missed day per week ("freeze").
- **E3** As a user, I want badges for milestones (first Eye Yoga, 7-day streak, etc.).

### Epic F: Privacy
- **F1** As a user, I want all data stored locally with clear "what is stored" screen.
- **F2** As a user, I want one-click export (CSV/JSON) and one-click delete-all.
- **F3** As a user, I want the app to work with no account and no internet.

### Epic G: Optional Blink Monitor (opt-in)
- **G1** As a user, I want to enable webcam blink monitoring explicitly, with a consent screen.
- **G2** As a user, I want to see a camera-active indicator whenever it runs.
- **G3** As a user, I want only aggregated numbers (blinks/min) saved, never images.
- **G4** As a user, I want reminders to arrive earlier when my blink rate drops.

---

## 4. Functional Requirements

Priority: **P0** must-have, **P1** should-have, **P2** nice-to-have.

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-01 | System tray app that auto-starts with OS (toggle) | P0 |
| FR-02 | Configurable work interval (10-60 min, default 20) and break length (10-60 s, default 20) | P0 |
| FR-03 | Reminder overlay with snooze/skip/start-Eye-Yoga | P0 |
| FR-04 | Eye Yoga: 6 exercises × 10 s with animation, countdown, audio cue (optional) | P0 |
| FR-05 | Active vs idle detection using OS input timestamps | P0 |
| FR-06 | Fullscreen detection (foreground window covers monitor) → suppress | P0 |
| FR-07 | Call detection (process name + window title heuristic) → suppress | P1 |
| FR-08 | Deferred reminder delivered when context clears (max one queued) | P1 |
| FR-09 | SQLite local storage for all events | P0 |
| FR-10 | Dashboard: today, 7-day, 30-day charts | P0 |
| FR-11 | Wellness Score computed daily and shown with breakdown | P0 |
| FR-12 | Streaks with weekly freeze; badges | P1 |
| FR-13 | Export (CSV/JSON) and delete-all | P0 |
| FR-14 | Work hours schedule (e.g., Mon-Fri 9-18) | P1 |
| FR-15 | Dark/light theme | P2 |
| FR-16 | Blink monitor (EAR via MediaPipe), opt-in, on-device | P1 |
| FR-17 | Adaptive reminder timing from blink rate | P2 |
| FR-18 | Weekly insights summary text | P2 |

---

## 5. Non-Functional Requirements

| Category | Requirement |
|----------|-------------|
| **Privacy** | No network access. No telemetry. No frames written to disk. Camera frames processed in memory and discarded immediately. |
| **Performance** | Idle CPU < 3%; blink monitor at ≤ 15 FPS, < 15% CPU on a mid-range laptop |
| **Reliability** | Timers survive sleep/resume and clock changes; app recovers state on crash |
| **Usability** | First run to first reminder < 2 min; SUS score ≥ 70 in pilot |
| **Accessibility** | Keyboard operable; high-contrast theme; no flashing > 3 Hz; Eye Yoga offers text + visual instructions |
| **Portability** | Windows 10/11 for v1; architecture keeps OS-specific code behind an interface for macOS/Linux later |
| **Maintainability** | Modular code, ≥ 70% unit-test coverage on core logic (scheduler, scoring) |

---

## 6. Wellness Score Specification (summary)

Score (0-100) = weighted sum, computed at end of each day (and live):

| Component | Weight | Definition |
|-----------|--------|-----------|
| Break compliance | 40% | breaks completed ÷ breaks due |
| Eye Yoga | 20% | min(yoga sessions ÷ target (default 3), 1) |
| Screen-time balance | 25% | 1.0 if ≤ goal (default 8 h); linear decay to 0 at 1.5× goal |
| Blink health | 15% | share of monitored minutes with blink rate ≥ 12/min (only if enabled; otherwise weight redistributed) |

Bands: 80-100 Great, 60-79 Good, 40-59 Needs attention, < 40 Rest your eyes. Full details in `ARCHITECTURE.md`.

---

## 7. UX Flow (summary)

1. **Onboarding (3 screens):** welcome + privacy promise → set interval and work hours → optional blink monitor consent (default OFF).
2. **Daily loop:** tray icon (green/amber) → gentle overlay at break time → choose *Eye Yoga / Quick 20 s / Snooze / Skip* → completion animation + score update.
3. **Dashboard:** score ring, today's timeline, streak, 7-day chart, insights.
4. **Settings:** intervals, schedule, context rules (allow/deny list), privacy (export/delete), theme.

---

## 8. Assumptions, Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Fullscreen/call detection false positives/negatives | Annoying or missed reminders | Allow/deny lists in settings; "Not now / Always allow here" feedback |
| Webcam blink detection varies (glasses, lighting) | Inaccurate metrics | Per-user calibration; present as an estimate; validate against manual count |
| Users perceive webcam as surveillance | Low adoption of blink feature | Opt-in, visible indicator, no stored frames, source code inspectable |
| Health claims overreach | Ethical/academic issue | Wording rules in STYLE_GUIDE; disclaimer in app |
| Scope creep | Late delivery | Strict phase gates (see PHASES.md) |
| GPL licensing of reference projects | Legal | Reimplement ideas; do not copy GPL code (Blink Eye is GPLv3 + commercial restrictions) |

---

## 9. Evaluation Plan (for course report)

- **Usability:** SUS questionnaire, 5-10 participants, 1-week pilot.
- **Behavior:** break completion rate, reminders suppressed vs shown, streak length.
- **Subjective:** pre/post eye-strain self-report (e.g., 5-item symptom checklist adapted from CVS-Q style questions; state as a non-validated adaptation).
- **Technical:** blink detection accuracy vs manual count on 10 short clips; CPU/RAM profiling.
- **Privacy audit:** verify no outbound connections (e.g., firewall log / Wireshark) and no image files on disk.

---

## 10. Out-of-Scope Ideas (Backlog)

Posture detection, macOS/Linux ports, wearable integration, doctor-share report (user-initiated PDF), localization, ambient-light advice.
