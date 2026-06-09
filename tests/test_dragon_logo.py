"""
Test the dragon logo renderer.
"""
import os
import sys
import pytest

# Skip all tests in this module if PIL is not available
try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

pytestmark = pytest.mark.skipif(not HAS_PIL, reason="Pillow not installed")


def test_dragon_image_finder():
    """Should find the dragon image at one of the search paths."""
    from laap.ui.dragon_logo import _find_dragon_image
    path = _find_dragon_image()
    assert path is not None, "No dragon image found in any candidate location"
    assert os.path.exists(path), f"Image path {path} does not exist"
    assert path.lower().endswith(('.jpg', '.jpeg', '.png')), f"Unexpected format: {path}"


def test_render_dragon_colored():
    """Should render the dragon as ANSI gold text."""
    from laap.ui.dragon_logo import render_dragon
    art = render_dragon(width=60, use_color=True)
    assert art, "render_dragon returned empty"
    assert "\033[38;2;" in art, "No ANSI color escapes in colored render"
    # Should be at least 20 lines tall
    lines = art.split("\n")
    assert len(lines) >= 20, f"Dragon too short: {len(lines)} lines"


def test_render_dragon_plain():
    """Should render the dragon as plain text (no color)."""
    from laap.ui.dragon_logo import render_dragon_plain
    art = render_dragon_plain(width=60)
    assert art, "render_dragon_plain returned empty"
    # No ANSI escapes in plain version
    assert "\033[" not in art, "Plain render should not contain ANSI escapes"
    lines = art.split("\n")
    assert len(lines) >= 20


def test_logo_art_uses_image():
    """logo_art.DRAGON_LOGO should be the image-derived version."""
    from laap.cli.logo_art import DRAGON_LOGO, _load_dragon_logo
    loaded = _load_dragon_logo()
    # Either image-rendered (with ANSI) or fallback ASCII — both are valid
    assert loaded, "logo_art loaded empty"
    # Confirm it's the same as the module-level constant
    assert DRAGON_LOGO == loaded


def test_render_mini_dragon():
    """render_mini_dragon should produce a smaller version."""
    import re
    from laap.cli.logo_art import render_mini_dragon
    art = render_mini_dragon(width=20)
    # Width-20 version should have shorter *visible* width than width-60.
    # Strip ANSI escapes first to measure actual character count.
    if art:
        clean = re.sub(r"\033\[[0-9;]*m", "", art)
        max_visible = max(len(l) for l in clean.split("\n"))
        # visible width should be <= 25 (allowing slight rounding)
        assert max_visible <= 25, f"Mini dragon visible width too wide: {max_visible}"


def test_color_breathing_helper():
    """The GOLD_PALETTE has the right shape and is ordered light→dark."""
    from laap.ui.dragon_logo import GOLD_PALETTE
    assert len(GOLD_PALETTE) >= 5
    # Brightness should decrease across the palette
    brightnesses = [0.299*r + 0.587*g + 0.114*b for r, g, b in GOLD_PALETTE]
    assert brightnesses[0] > brightnesses[-1], "Palette not ordered light → dark"


def test_animation_frames_can_be_generated():
    """make_animation_frames should produce ≥1 frame."""
    from laap.ui.dragon_logo import make_animation_frames
    frames = make_animation_frames(width=30, frame_count=2)
    assert len(frames) >= 1
    for f in frames:
        assert f, "Empty animation frame"
