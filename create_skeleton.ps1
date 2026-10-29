$ErrorActionPreference = "Stop"

$root = Join-Path $PSScriptRoot "screensense"

$directories = @(
    "core",
    "platform_adapters",
    "storage/migrations",
    "vision",
    "ui/eye_yoga",
    "ui/dashboard",
    "ui/theme",
    "assets",
    "tests",
    "docs"
)

foreach ($directory in $directories) {
    New-Item -ItemType Directory -Path (Join-Path $root $directory) -Force | Out-Null
}

$files = @{
    "app.py" = '"""Wire together the ScreenSense application."""'
    "core/__init__.py" = '"""Core application logic without UI or operating-system access."""'
    "core/events.py" = '"""Define application events and their bus."""'
    "core/scheduler.py" = '"""Manage break scheduling and state transitions."""'
    "core/context.py" = '"""Evaluate context and reminder suppression rules."""'
    "core/tracker.py" = '"""Track aggregated active and idle sessions."""'
    "core/scoring.py" = '"""Calculate the daily wellness score."""'
    "core/gamification.py" = '"""Manage streaks and badges."""'
    "core/config.py" = '"""Define and validate application settings."""'
    "platform_adapters/__init__.py" = '"""Provide operating-system adapters behind interfaces."""'
    "platform_adapters/base.py" = '"""Define platform adapter interfaces."""'
    "platform_adapters/windows.py" = '"""Implement platform interfaces for Windows."""'
    "platform_adapters/stub.py" = '"""Provide fake platform adapters for tests."""'
    "storage/__init__.py" = '"""Provide local database storage and repositories."""'
    "storage/db.py" = '"""Manage the database connection and migrations."""'
    "storage/repositories.py" = '"""Provide data access repositories."""'
    "vision/__init__.py" = '"""Provide optional, local-only vision features."""'
    "vision/worker.py" = '"""Run the optional vision worker process."""'
    "vision/blink.py" = '"""Calculate eye aspect ratio and detect blinks."""'
    "vision/calibration.py" = '"""Calibrate blink detection from aggregated measurements."""'
    "ui/__init__.py" = '"""Provide the PyQt6 user interface."""'
    "ui/tray.py" = '"""Display and manage the system tray interface."""'
    "ui/overlay.py" = '"""Display a dismissible break reminder."""'
    "ui/eye_yoga/__init__.py" = '"""Provide eye-yoga routines and animation widgets."""'
    "ui/dashboard/__init__.py" = '"""Provide dashboard charts and score visuals."""'
    "ui/onboarding.py" = '"""Guide users through initial application setup."""'
    "ui/settings.py" = '"""Display and edit application settings."""'
    "ui/theme/__init__.py" = '"""Provide application colors, styles, and icons."""'
}

foreach ($entry in $files.GetEnumerator()) {
    $path = Join-Path $root $entry.Key
    if (-not (Test-Path $path)) {
        Set-Content -Path $path -Value $entry.Value -Encoding utf8
    }
}
