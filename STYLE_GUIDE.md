# ScreenSense: Style Guide

Covers **brand & voice**, **UI/UX design system**, **code style**, and **documentation style**.

---

## Part 1: Brand & Voice

### 1.1 Personality
Calm · Caring · Respectful · Quietly encouraging. Think *a thoughtful friend*, not a drill sergeant or a doctor.

### 1.2 Voice Principles
1. **Invite, don't command.** "Ready to rest your eyes?" not "Take a break NOW!"
2. **Celebrate effort, never shame lapses.** "Fresh start tomorrow" not "You failed your streak."
3. **Plain language.** Avoid jargon; explain once if needed.
4. **Short.** Overlay text ≤ 12 words; one idea per message.
5. **Honest health claims.** Wellness support, not medicine.

### 1.3 Wording Rules (health & ethics)
| Use | Avoid |
|-----|-------|
| "may help reduce eye strain" | "cures / treats / prevents eye disease" |
| "blink rate estimate" | "diagnosed dry eye" |
| "wellness score" | "health score", "medical score" |
| "possible tiredness signal" | "you are fatigued/sick" |
| "If symptoms persist, talk to an eye-care professional." | any diagnostic language |

**Mandatory disclaimer** (Settings → About, onboarding, report): *"ScreenSense supports healthy screen habits. It is not a medical device and does not diagnose or treat any condition."*

### 1.4 Sample Microcopy
| Moment | Copy |
|--------|------|
| Reminder | "Time to rest your eyes 👀" |
| Buttons | **Eye Yoga (60s)** · Quick break (20s) · Snooze 5 min · Skip |
| Completed | "Nice. Your eyes thank you." |
| Skipped | (no message; just logged) |
| Suppressed (shown later) | "Meeting's over. Want a quick eye break?" |
| Streak freeze used | "Streak protected. Rest days happen." |
| Streak reset | "New streak starting. Day 1 today!" |
| Low score | "Today was a heavy screen day. A short Eye Yoga could help." |
| Camera consent | "Blink monitoring uses your webcam on this device only. No video or images are saved or sent anywhere." |

---

## Part 2: UI / UX Design System

### 2.1 Principles
1. **Quiet by default:** low-saturation, no sudden motion, no sounds unless enabled.
2. **Always escapable:** every overlay has Skip/Close; Esc works.
3. **Glanceable:** score ring, one primary number per card.
4. **Respect attention:** never interrupt when context says no.
5. **Accessible:** WCAG AA contrast, keyboard navigation, reduced-motion mode.

### 2.2 Color Tokens

| Token | Light | Dark | Use |
|-------|-------|------|-----|
| `--bg` | `#F7FAF9` | `#101615` | App background |
| `--surface` | `#FFFFFF` | `#18201F` | Cards |
| `--text` | `#14201E` | `#E6F0EE` | Body text |
| `--muted` | `#5B6B68` | `#8FA09C` | Secondary text |
| `--primary` | `#2A9D8F` | `#3BB8A8` | Primary actions, ring |
| `--accent` | `#E9C46A` | `#E9C46A` | Streaks, highlights |
| `--calm` | `#A8DADC` | `#2B4B4D` | Eye Yoga background |
| `--warn` | `#F4A261` | `#F4A261` | Needs-attention score |
| `--danger` | `#E76F51` | `#E76F51` | Destructive (delete data) only |

Score bands: Great `--primary`, Good `#8AB17D`, Needs attention `--warn`, Rest `--danger`-soft. Never rely on color alone: always pair with label/icon.

### 2.3 Typography
- Font: **Inter** (fallback Segoe UI, system-ui).
- Scale: 12 caption · 14 body · 16 emphasis · 20 H3 · 28 H2 · 40 score number.
- Line height 1.4-1.5. Min text size 12 px.

### 2.4 Spacing & Shape
8-px grid (4 / 8 / 16 / 24 / 32). Corner radius 12 px (cards), 999 px (pills). Soft shadow `0 2 8 rgba(0,0,0,.08)`.

### 2.5 Components
- **Break overlay:** centered card, dimmed background (not full black), 20 s ring countdown, 4 buttons (1 primary). Not click-through blocking: user can always dismiss.
- **Score ring:** 0-100 arc, number center, band label below.
- **Eye Yoga player:** large animation, step name, one-line instruction, progress ring, Pause/Exit.
- **Cards:** Today, Streak, Trend (7-day), Insight.
- **Tray icon:** green (active), grey (paused/suppressed), amber dot (reminder due), camera dot (monitor running).

### 2.6 Motion
Gentle ease-in-out, 200-400 ms; Eye Yoga animations ≤ 0.5 Hz motion, nothing flashing. **Reduced-motion setting** replaces animation with static illustration + text.

### 2.7 Accessibility Checklist
- [ ] Contrast ≥ 4.5:1 body, ≥ 3:1 large text/icons
- [ ] All actions keyboard reachable; visible focus ring
- [ ] Text instructions for every Eye Yoga step (no animation-only info)
- [ ] Scalable UI (100-150%)
- [ ] Sound optional and never the only cue

---

## Part 3: Code Style (Python)

### 3.1 Tooling
`ruff` (lint + import sort) · `black` (format, line length 100) · `mypy` (strict on `core/`) · `pytest` · `pre-commit`.

### 3.2 Conventions
- Python 3.11+, type hints on all public functions.
- Names: `snake_case` functions/vars, `PascalCase` classes, `UPPER_SNAKE` constants.
- One responsibility per module; `core/` must **not** import `ui/` or OS-specific code.
- OS calls only via `platform/` interfaces.
- Time: always use an injected `Clock` (monotonic + wall) so tests can fake time.
- No bare `except:`; log with `logging` (no `print`). Never log window titles or any user content.
- Docstrings (Google style) for public classes/functions.
- Settings keys defined in one enum; no magic strings.

### 3.3 Git
- Branches: `feat/…`, `fix/…`, `docs/…`.
- **Conventional Commits:** `feat(scheduler): queue prompt when context clears`.
- PRs need: description, tests, screenshots for UI changes, privacy-impact line ("no new data stored / sent").

### 3.4 Testing Conventions
- File mirrors source: `core/scoring.py` → `tests/core/test_scoring.py`.
- Test names describe behavior: `test_idle_longer_than_break_resets_timer`.
- No real sleeping; use fake clock.

---

## Part 4: Documentation Style

- Markdown, ATX headings, one H1 per file, sentence-case headings.
- Tables for comparisons, checklists for tasks, code fences with language tags.
- Requirements use IDs (`FR-04`, `NFR-…`), referenced from tests and commits.
- Docs live in `/docs`; `MEMORY.md` is updated at the end of every working session.
- Diagrams: ASCII or Mermaid so they diff well in Git.
- Citations: IEEE or APA, consistent; keep in `docs/REFERENCES.md`.
