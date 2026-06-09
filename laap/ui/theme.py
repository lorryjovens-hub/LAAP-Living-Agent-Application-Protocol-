"""
LAAP — Golden Dragon Theme
Color themes and styling constants for the LAAP TUI.
"""

from dataclasses import dataclass
from rich.style import Style
from rich.color import Color
from rich.text import Text


# ── Color Palette ──────────────────────────────────────────────

@dataclass
class DragonColors:
    """Golden dragon color palette."""
    gold: str = "#FFD700"
    gold_bright: str = "#FFE55C"
    gold_dim: str = "#B8960C"
    gold_light: str = "#FFED80"
    gold_dark: str = "#8B6914"
    crimson: str = "#DC143C"
    crimson_light: str = "#FF3366"
    eye_glow: str = "#FF4400"
    bg_dark: str = "#0D0D1A"
    bg_mid: str = "#1A1A2E"
    bg_light: str = "#2A2A4A"
    text_primary: str = "#E8E8E8"
    text_secondary: str = "#AAAAAA"
    text_dim: str = "#666666"
    success: str = "#00D68F"
    error: str = "#FF4444"
    warning: str = "#FFAA00"
    info: str = "#44AAFF"


DRAGON = DragonColors()


# ── Rich Styles ────────────────────────────────────────────────

def gold_style(bold: bool = False, dim: bool = False) -> Style:
    """Create a golden style."""
    color = DRAGON.gold_dim if dim else DRAGON.gold
    return Style(color=color, bold=bold)


def gradient_text(text: str, colors: list[str] = None) -> Text:
    """Create text with a gradient effect."""
    if colors is None:
        colors = [DRAGON.gold_dim, DRAGON.gold, DRAGON.gold_bright, DRAGON.gold_light]
    result = Text()
    n = len(text)
    for i, ch in enumerate(text):
        color_idx = min(int(i / max(n, 1) * len(colors)), len(colors) - 1)
        result.append(ch, Style(color=colors[color_idx]))
    return result


def dragon_divider(char: str = "═", width: int = 60) -> Text:
    """Create a golden divider line."""
    return Text(" " + char * width, style=Style(color=DRAGON.gold_dim, dim=True))


def status_icon(active: bool = True) -> Text:
    """Create a status icon (breathing/awake)."""
    if active:
        return Text("🐉", style=Style(color=DRAGON.gold_bright))
    return Text("🐉", style=Style(color=DRAGON.gold_dim))


# ── Theme for Textual ──────────────────────────────────────────

GOLDEN_THEME = {
    "primary": DRAGON.gold,
    "secondary": DRAGON.gold_dim,
    "background": DRAGON.bg_dark,
    "surface": DRAGON.bg_mid,
    "error": DRAGON.error,
    "success": DRAGON.success,
    "warning": DRAGON.warning,
    "accent": DRAGON.gold_bright,
}


def apply_golden_theme(app):
    """Apply the golden dragon theme to a Textual app."""
    from textual.theme import Theme
    theme = Theme(
        name="golden-dragon",
        primary=DRAGON.gold,
        secondary=DRAGON.gold_dim,
        background=DRAGON.bg_dark,
        surface=DRAGON.bg_mid,
        error=DRAGON.error,
        success=DRAGON.success,
        warning=DRAGON.warning,
        accent=DRAGON.gold_bright,
        dark=True,
    )
    app.theme = "golden-dragon"
