# ScreenSense

Eye wellness and smart screen-time app (Digital Health course project).

## Quick start

**Requirements:** Python 3.11 or newer, a graphical desktop, and a system tray.

The first launch includes privacy and setup onboarding. Preferences include light/dark
themes, reduced motion, and optional operating-system autostart.

### Windows 10/11

```powershell
git clone https://github.com/directionlessvector/Digital-Health-Project.git
cd Digital-Health-Project

py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m screensense.app
```

If PowerShell blocks activation, allow it for the current session:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

You can also run the app without activating the environment:

```powershell
.\.venv\Scripts\python.exe -m screensense.app
```

### Linux

Install Python and the Qt/XCB runtime libraries. On Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y \
  python3 python3-venv python3-pip \
  libgl1 libegl1 libglib2.0-0 libdbus-1-3 \
  libxkbcommon-x11-0 libxcb-cursor0 libxcb-xinerama0 \
  libxcb-icccm4 libxcb-image0 libxcb-keysyms1 \
  libxcb-render-util0 libxcb-shape0 \
  xprintidle
```

Then clone and run:

```bash
git clone https://github.com/directionlessvector/Digital-Health-Project.git
cd Digital-Health-Project

python3 -m venv .venv
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

python -m screensense.app
```

Linux notes:

- `xprintidle` is optional; without it idle detection falls back to `0`.
- The app lives in the system tray. On GNOME, install an AppIndicator/KStatusNotifierItem
  tray extension if the icon is not visible.
- On Wayland, if the tray does not appear, try
  `QT_QPA_PLATFORM=xcb python -m screensense.app`.

### Run checks

```bash
python -m ruff check .
python -m pytest
```

### Optional webcam monitoring

The webcam blink monitor is off by default. To install its local-only dependencies:

```bash
python -m pip install -r requirements-vision.txt
```

Enable it in Settings only after reviewing the consent prompt. While the worker is
running, the tray camera indicator remains visible, and **Stop Blink Monitoring**
immediately ends camera access. Video frames are processed in memory and discarded;
only per-minute aggregate metrics are stored locally. If the optional dependencies
are missing, the rest of the app continues to work and the monitor reports that it
could not start. See the [user guide](docs/USER_GUIDE.md) for privacy details and
troubleshooting.

### Data and logs

- Windows: `%APPDATA%\ScreenSense\`
- Linux: `~/.local/share/ScreenSense/` (or `$XDG_DATA_HOME/ScreenSense/`)

The SQLite database and `screensense.log` are stored there.

### Build a Windows executable

On a Windows build machine:

```powershell
python -m pip install -r requirements-packaging.txt
python -m PyInstaller --clean --noconfirm screensense.spec
```

The executable is written to `dist\ScreenSense\ScreenSense.exe`. The standard spec
does not bundle the optional webcam dependencies.

## Documentation

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

> ScreenSense supports healthy screen habits. It is not a medical device and does not diagnose or treat any condition.
