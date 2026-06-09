"""
LAAP — Golden Dragon CLI Skin
Uses the actual golden dragon ASCII art generated from the logo.png
"""

from __future__ import annotations
from laap.cli.logo_art import render_dragon, render_title, GOLD, GOLD_BRIGHT, GOLD_DIM, DARK, RESET, BOLD

# Export for other modules
__all__ = ["render_logo", "render_title", "GOLD", "GOLD_BRIGHT", "GOLD_DIM", "RESET", "BOLD", "SYM", "PLAIN_SYM"]

# Status symbols in gold
SYM = {
    "dragon": f"{GOLD}◆{RESET}",
    "psi": f"{GOLD}Ψ{RESET}",
    "ok": f"{GOLD}✓{RESET}",
    "warn": f"{DARK}⚠{RESET}",
    "err": "\033[31m✗\033[0m",
    "inf": f"{GOLD_DIM}∞{RESET}",
    "evo": f"{GOLD}⟁{RESET}",
    "scan": f"{GOLD}◎{RESET}",
    "seed": f"{GOLD}◆{RESET}",
    "node": f"{GOLD}⬡{RESET}",
    "life": f"{GOLD}⚕{RESET}",
    "arrow": f"{GOLD}▶{RESET}",
}

# Plain-unicode symbols (no ANSI codes — safe for Rich panels, logs, etc.)
PLAIN_SYM = {
    "dragon": "\u25c6",
    "psi": "\u03a8",
    "ok": "\u2713",
    "warn": "\u26a0",
    "err": "\u2717",
    "inf": "\u221e",
    "evo": "\u27c1",
    "scan": "\u25ce",
    "seed": "\u25c6",
    "node": "\u2b21",
    "life": "\u2695",
    "arrow": "\u25b6",
}


def render_logo(style: str = "color") -> str:
    """Render the golden dragon logo"""
    return render_dragon(use_color=(style == "color"))
