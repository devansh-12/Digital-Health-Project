"""Provide ScreenSense color tokens and the Qt stylesheet loader."""

from pathlib import Path

BG = "#F7FAF9"
SURFACE = "#FFFFFF"
TEXT = "#14201E"
MUTED = "#5B6B68"
PRIMARY = "#2A9D8F"
ACCENT = "#E9C46A"
CALM = "#A8DADC"
WARN = "#F4A261"
DANGER = "#E76F51"


def load_stylesheet() -> str:
    """Read the bundled Qt stylesheet."""
    stylesheet_path = Path(__file__).with_name("theme.qss")
    return stylesheet_path.read_text(encoding="utf-8")
