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


def load_stylesheet(theme: str = "dark") -> str:
    """Read the bundled dark or light Qt stylesheet."""
    if theme not in {"dark", "light"}:
        raise ValueError(f"Unsupported theme: {theme}")
    filename = "theme.qss" if theme == "dark" else "theme-light.qss"
    stylesheet_path = Path(__file__).with_name(filename)
    return stylesheet_path.read_text(encoding="utf-8")
