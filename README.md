# ScreenSense Documentation

Eye wellness and smart screen-time app (Digital Health course project).

| Doc | Read it when you want to know... |
|-----|----------------------------------|
| [PRD.md](PRD.md) | what we're building, for whom, and how we'll judge success |
| [ARCHITECTURE.md](ARCHITECTURE.md) | how it works: modules, state machine, DB schema, blink pipeline |
| [PHASES.md](PHASES.md) | the 10-week plan, gates, and what to cut if late |
| [STYLE_GUIDE.md](STYLE_GUIDE.md) | voice and wording, UI design tokens, code and doc conventions |
| [MEMORY.md](MEMORY.md) | project context to paste into any new AI session; decision log |
| [docs/USER_GUIDE.md](docs/USER_GUIDE.md) | installation, daily use, privacy, troubleshooting, and packaging |
| [docs/DEMO_VIDEO_SCRIPT.md](docs/DEMO_VIDEO_SCRIPT.md) | short demonstration outline |

**Suggested reading order:** PRD → ARCHITECTURE → PHASES → STYLE_GUIDE. Keep MEMORY.md updated after each session.

The first launch includes privacy and setup onboarding. Preferences include light/dark
themes, reduced motion, and optional operating-system autostart. See the [user guide](docs/USER_GUIDE.md)
for setup and build instructions.

The webcam blink monitor is optional and disabled by default. To install its local-only
vision dependencies, run `pip install -r requirements-vision.txt`. Enable it in Settings
only after reviewing the consent prompt; the tray camera indicator remains visible while
the worker is running, and **Stop Blink Monitoring** immediately ends camera access.
Video frames are processed in memory and discarded; only per-minute aggregate metrics
are stored locally. If the optional dependencies are not installed, the rest of the app
continues to work and the monitor reports that it could not start.

> ScreenSense supports healthy screen habits. It is not a medical device and does not diagnose or treat any condition.
