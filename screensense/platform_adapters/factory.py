"""Provide a factory to automatically select platform adapters based on the operating system."""

import sys
from dataclasses import dataclass

from screensense.platform_adapters.base import (
    AppDataProvider,
    AutostartProvider,
    IdleProvider,
    PowerProvider,
    WindowProvider,
)


@dataclass(frozen=True, slots=True)
class PlatformProviders:
    """Hold resolved platform adapter instances for the active operating system."""

    app_data: AppDataProvider
    idle: IdleProvider
    window: WindowProvider
    power: PowerProvider
    autostart: AutostartProvider


def get_platform_providers() -> PlatformProviders:
    """Detect the current operating system and return the appropriate platform adapters."""
    if sys.platform == "win32":
        from screensense.platform_adapters.windows import (
            WindowsAppDataProvider,
            WindowsAutostartProvider,
            WindowsIdleProvider,
            WindowsPowerProvider,
            WindowsWindowProvider,
        )

        return PlatformProviders(
            app_data=WindowsAppDataProvider(),
            idle=WindowsIdleProvider(),
            window=WindowsWindowProvider(),
            power=WindowsPowerProvider(),
            autostart=WindowsAutostartProvider(),
        )

    if sys.platform.startswith("linux"):
        from screensense.platform_adapters.linux import (
            LinuxAppDataProvider,
            LinuxAutostartProvider,
            LinuxIdleProvider,
            LinuxPowerProvider,
            LinuxWindowProvider,
        )

        return PlatformProviders(
            app_data=LinuxAppDataProvider(),
            idle=LinuxIdleProvider(),
            window=LinuxWindowProvider(),
            power=LinuxPowerProvider(),
            autostart=LinuxAutostartProvider(),
        )

    from screensense.platform_adapters.stub import (
        StubAppDataProvider,
        StubAutostartProvider,
        StubIdleProvider,
        StubPowerProvider,
        StubWindowProvider,
    )
    from pathlib import Path

    return PlatformProviders(
        app_data=StubAppDataProvider(Path.home() / ".screensense"),
        idle=StubIdleProvider(),
        window=StubWindowProvider(),
        power=StubPowerProvider(),
        autostart=StubAutostartProvider(),
    )
