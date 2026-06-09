"""
LAAP — Dragon Logo Renderer
============================
Loads the project's dragon image and renders it as ANSI gold text
on demand, with optional animation frames.
"""

import os
import sys
import time
import threading
from pathlib import Path
from typing import List, Optional

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

# ── Gold palette (brightest → darkest) ────────────────────
GOLD_PALETTE = [
    (255, 225, 140),  # highlight
    (255, 200, 80),
    (255, 175, 40),
    (220, 160, 30),
    (185, 135, 20),
    (130, 90, 10),
    (70, 45, 5),
]
DENSITY_CHARS = ".,:;+*#@"

# ── Possible image locations (in priority order) ──────────
DRAGON_IMAGE_CANDIDATES = [
    r"D:\LAAP\龙logo.jpg",
    os.path.join(os.path.dirname(__file__), "..", "..", "龙logo.jpg"),
    os.path.join(os.path.expanduser("~"), "龙logo.jpg"),
    os.path.join(os.path.dirname(__file__), "..", "..", "logo.png"),
    os.path.join(os.path.dirname(__file__), "..", "..", "logo.jpg"),
]


def _find_dragon_image() -> Optional[str]:
    """Find the dragon image file. Returns path or None."""
    for cand in DRAGON_IMAGE_CANDIDATES:
        if os.path.exists(cand):
            return os.path.abspath(cand)
    return None


def _luminance(rgb):
    r, g, b = rgb[:3]
    return 0.299 * r + 0.587 * g + 0.114 * b


def _color_for_lum(lum: int) -> tuple:
    idx = int((255 - lum) / 255 * (len(GOLD_PALETTE) - 1))
    idx = max(0, min(len(GOLD_PALETTE) - 1, idx))
    return GOLD_PALETTE[idx]


def _char_for_lum(lum: int) -> str:
    if lum < 18:
        return " "
    char_idx = int((255 - lum) / 255 * (len(DENSITY_CHARS) - 1))
    char_idx = max(0, min(len(DENSITY_CHARS) - 1, char_idx))
    return DENSITY_CHARS[char_idx]


# ── Cached rendering ──────────────────────────────────────
_CACHE: dict = {}
_CACHE_LOCK = threading.Lock()


def _render_cached(img_path: str, width: int, char_aspect: float = 0.5) -> str:
    """Render and cache. Each (path, width) is cached separately."""
    key = (os.path.getmtime(img_path), width, char_aspect)
    with _CACHE_LOCK:
        if key in _CACHE:
            return _CACHE[key]
    if not HAS_PIL:
        return ""
    img = Image.open(img_path)
    w, h = img.size
    aspect = h / w
    height = max(1, int(width * aspect * char_aspect))
    img2 = img.convert("L").resize((width, height), Image.LANCZOS)
    px = img2.load()

    lines = []
    for row in range(height):
        line = ""
        for col in range(width):
            v = px[col, row]
            if v < 18:
                line += " "
                continue
            r, g, b = _color_for_lum(v)
            ch = _char_for_lum(v)
            line += f"\033[38;2;{r};{g};{b}m{ch}\033[0m"
        lines.append(line)
    out = "\n".join(lines)
    with _CACHE_LOCK:
        _CACHE[key] = out
    return out


def render_dragon(width: int = 60, use_color: bool = True) -> str:
    """
    Render the dragon image as ANSI text.
    width: target width in characters
    use_color: if False, returns plain ASCII (256-color safe fallback)
    """
    if not use_color:
        return render_dragon_plain(width)
    img_path = _find_dragon_image()
    if not img_path or not HAS_PIL:
        return ""
    return _render_cached(img_path, width)


def render_dragon_plain(width: int = 60) -> str:
    """Plaintext fallback (no color)."""
    img_path = _find_dragon_image()
    if not img_path or not HAS_PIL:
        return ""
    img = Image.open(img_path)
    w, h = img.size
    aspect = h / w
    height = max(1, int(width * aspect * 0.5))
    img2 = img.convert("L").resize((width, height), Image.LANCZOS)
    px = img2.load()
    lines = []
    for row in range(height):
        line = ""
        for col in range(width):
            v = px[col, row]
            line += _char_for_lum(v)
        lines.append(line)
    return "\n".join(lines)


def make_animation_frames(width: int = 60, frame_count: int = 3) -> List[str]:
    """
    Create animation frames by slightly shifting the image horizontally.
    Simulates a "floating/swaying" dragon.
    """
    img_path = _find_dragon_image()
    if not img_path or not HAS_PIL:
        return []
    img = Image.open(img_path)
    w, h = img.size

    out = []
    for i in range(frame_count):
        dx = (i - frame_count // 2) * max(2, w // 200)  # ~0.5% shift
        if dx >= 0:
            cropped = img.crop((dx, 0, w, h))
        else:
            cropped = img.crop((0, 0, w + dx, h))
        # Save to temp and render
        tmp = img_path + f".tmp_frame_{i}.jpg"
        cropped.save(tmp, "JPEG", quality=85)
        try:
            out.append(_render_cached(tmp, width))
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
    return out


def animated_print(width: int = 60, frame_delay: float = 0.18, cycles: int = 2):
    """
    Print the dragon with simple horizontal-sway animation.
    Each cycle goes through all frames. Use cursor-hide/show for clean output.
    """
    frames = make_animation_frames(width)
    if not frames:
        return
    height = frames[0].count("\n") + 1

    sys.stdout.write("\033[?25l")  # hide cursor
    try:
        for _ in range(cycles):
            for frame in frames:
                # clear previous frame
                sys.stdout.write(f"\033[{height}A")  # move up
                sys.stdout.write("\033[J")             # clear from cursor
                sys.stdout.write(frame + "\n")
                sys.stdout.flush()
                time.sleep(frame_delay)
        # final hold on first frame
        sys.stdout.write(f"\033[{height}A\033[J")
        sys.stdout.write(frames[0] + "\n")
        sys.stdout.flush()
    finally:
        sys.stdout.write("\033[?25h")  # show cursor


# ── Self-test ─────────────────────────────────────────────
if __name__ == "__main__":
    print(f"Dragon image: {_find_dragon_image()}")
    print(f"PIL available: {HAS_PIL}")
    art = render_dragon(60)
    if art:
        print(art)
    else:
        print("(no dragon image found)")
