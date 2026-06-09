"""LAAP UI modules - Golden Dragon TUI.

Import strategy
---------------
- **Theme / dragon art** are eagerly imported; they're cheap and every
  CLI subcommand (``laap --version``, ``laap -q ...``, ``laap -i``)
  needs them to render the Hermes banner.
- **TUI / Textual** are heavy optional dependencies. They're exposed
  via PEP 562 ``__getattr__`` so a bare ``uv tool install laap`` (with
  no ``[tui]`` extra) doesn't blow up at startup with
  ``ModuleNotFoundError: No module named 'textual'``.
"""

# Eagerly import the cheap pieces used by the banner / REPL.
from laap.ui.theme import DragonColors, DRAGON, gold_style, gradient_text
from laap.ui.dragon_art import DRAGON_FRAMES, GOLD, GOLD_BRIGHT, SYM, TITLE_CN


# PEP 562 lazy attribute access for TUI-only symbols.
def __getattr__(name):
    """Resolve ``laap.ui.<tui_symbol>`` on first access."""
    if name in {
        "run_tui",
        "GoldenDragonTUI", "GoldenDragonApp",
        "MainScreen", "MessageDisplay", "DragonBanner",
    }:
        from laap.ui import tui as _tui_mod  # noqa: WPS433
        return getattr(_tui_mod, name)
    if name == "LAAP_TUI":
        from laap.ui import tui as _tui_mod  # noqa: WPS433
        return _tui_mod.LAAP_TUI
    raise AttributeError(f"module 'laap.ui' has no attribute {name!r}")


__all__ = [
    # cheap / always available
    "DRAGON", "gold_style", "gradient_text", "DragonColors",
    "DRAGON_FRAMES", "GOLD", "GOLD_BRIGHT", "SYM", "TITLE_CN",
    # TUI — lazy-loaded on access
    "run_tui", "GoldenDragonTUI", "GoldenDragonApp",
    "MainScreen", "MessageDisplay", "DragonBanner",
    "LAAP_TUI",
]
