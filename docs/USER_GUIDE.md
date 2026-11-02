# ScreenSense User Guide

## Install and start

On Windows 10/11, install Python 3.11 or use the packaged `ScreenSense.exe`.
For a source install:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m screensense.app
```

The app stays in the system tray. On first launch, follow the three-step onboarding.
The webcam monitor is optional, remains off unless you explicitly enable it, and
requires the optional dependencies described below.

## Everyday use

- Open the tray menu and choose **Open Dashboard** to view the daily score, activity,
  streak, and trends.
- Choose **Start Eye Yoga (60s)** for a guided session.
- Use **Settings** to choose work hours, app rules, light/dark theme, reduced motion,
  optional blink monitoring, and sign-in autostart.
- If monitoring is active, a camera indicator appears on the tray icon. Choose
  **Stop Blink Monitoring** to stop webcam use immediately.

## Privacy and data

Activity and preferences are stored locally in the ScreenSense SQLite database. Optional
blink monitoring processes frames in memory and stores only per-minute aggregate
estimates; frames, face landmarks, and window titles are not stored. Error diagnostics
are kept in a local `screensense.log` file beside the database. Use **Export JSON** to
export stored data or **Clear History** to remove historical records.

ScreenSense supports healthy screen habits. It is not a medical device and does not
diagnose or treat any condition.

## Optional webcam monitoring

Install the extra vision dependencies before enabling the feature:

```powershell
python -m pip install -r requirements-vision.txt
```

Accept the consent prompt in onboarding or turn on webcam blink monitoring in Settings.
If the camera or optional libraries are unavailable, the app explains the failure and
continues without monitoring.

## Troubleshooting

- If the tray icon is not visible, check the operating system's hidden-icons area.
- If the camera monitor does not start, install the optional dependencies, check camera
  permission, and enable the setting again.
- If the app exits unexpectedly, restart it. A local diagnostic log is available beside
  the database; it contains technical error details and should be treated as private.
- To disable automatic startup, uncheck **Start ScreenSense when I sign in** in Settings.

## Build a Windows executable

On a Windows build machine:

```powershell
python -m pip install -r requirements-packaging.txt
python -m PyInstaller --clean --noconfirm screensense.spec
```

The executable is written to `dist/ScreenSense/ScreenSense.exe`. The webcam dependencies
are not bundled by the standard spec; install `requirements-vision.txt` and use PyInstaller's
`--collect-all cv2 --collect-all mediapipe` options if producing a build that includes
the optional monitor. Test a release on a clean Windows 10/11 machine.
