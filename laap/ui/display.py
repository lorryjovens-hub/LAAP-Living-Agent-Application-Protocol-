"""
LAAP — Golden Dragon Terminal UI
Claude Code-grade terminal interface with animated dragon spinner,
real-time tool call feedback, rich message formatting, and status bar.

Design philosophy:
  - Claude Code: clean, minimal, utilitarian
  - LAAP: living, breathing, golden dragon aesthetic
  - Every action has a visual reaction
"""

from __future__ import annotations
import sys, time, threading, shutil, json
from typing import Any, Callable, Dict, List, Optional, Generator
from dataclasses import dataclass, field
from enum import Enum

# ── ANSI Colors ──
class C:
    GOLD = "\033[38;5;214m"
    GOLD_B = "\033[38;5;220m"
    GOLD_D = "\033[38;5;179m"
    # Aliases used elsewhere in the codebase
    GOLD_BRIGHT = "\033[38;5;220m"   # bright gold (alias of GOLD_B)
    GOLD_DIM = "\033[38;5;179m"      # dim gold (alias of GOLD_D)
    DARK = "\033[38;5;130m"
    RED = "\033[38;5;196m"
    GREEN = "\033[38;5;82m"
    BLUE = "\033[38;5;75m"
    CYAN = "\033[38;5;51m"
    WHITE = "\033[38;5;255m"
    GRAY = "\033[38;5;244m"
    DIM = "\033[38;5;240m"
    BG_DARK = "\033[48;5;235m"
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM_ON = "\033[2m"
    ITALIC = "\033[3m"
    CLEAR_LINE = "\033[K"
    UP_LINE = "\033[1A"
    HIDE_CURSOR = "\033[?25l"
    SHOW_CURSOR = "\033[?25h"
    SAVE_CURSOR = "\033[s"
    RESTORE_CURSOR = "\033[u"


# ── Dragon Spinner ──
# Animated golden dragon that rotates based on context

DRAGON_FRAMES = [
    # Frame 1: Dragon coiling
    [
        "          ",
        "  ~ ~ ~   ",
        " ~(Ao )~  ",
        " ~ ~ ~ ~  ",
        "  ~ ~ ~   ",
        "          ",
    ],
    # Frame 2: Dragon stretching
    [
        "          ",
        "  ~ ~ ~   ",
        " ~( Ao)~  ",
        " ~ ~ ~ ~  ",
        "  ~ ~ ~   ",
        "          ",
    ],
    # Frame 3: Dragon breathing fire
    [
        "   >>     ",
        "  ~>>>~   ",
        " ~(Ao )~> ",
        " ~ ~ ~>>  ",
        "  ~ ~ ~>  ",
        "          ",
    ],
    # Frame 4: Dragon coiling back
    [
        "          ",
        "  ~ ~ ~   ",
        " ~(Ao )~  ",
        " ~ ~ ~ ~  ",
        "  ~ ~ ~   ",
        "          ",
    ],
]

# Simple spinner frames for terminals
SPINNER_SIMPLE = ["◐", "◓", "◑", "◒"]
SPINNER_GOLD = ["◐", "◓", "◑", "◒"]
SPINNER_DOTS = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


@dataclass
class ToolActivity:
    """Represents an ongoing or completed tool call."""
    name: str
    args: Dict[str, Any] = field(default_factory=dict)
    status: str = "running"  # running | success | error
    result: str = ""
    start_time: float = field(default_factory=time.time)
    duration: float = 0.0
    tokens_in: int = 0
    tokens_out: int = 0


class DragonSpinner:
    """Animated golden dragon spinner that shows task progress.

    Manages a spinner thread that renders the dragon animation,
    tool call status, and task state below the current input line.
    """

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._message: str = ""
        self._tools: List[ToolActivity] = []
        self._status: str = "idle"  # idle | thinking | tools | responding | done
        self._frame_idx = 0
        self._lock = threading.Lock()
        self._dragon_mode = "simple"  # simple | full
        self._term_width = shutil.get_terminal_size().columns

    # ── Public API ──

    def start(self, message: str = "Ao is thinking..."):
        """Start the spinner with a status message."""
        with self._lock:
            self._running = True
            self._message = message
            self._status = "thinking"
            self._tools = []
        if not self._thread or not self._thread.is_alive():
            self._thread = threading.Thread(target=self._spin, daemon=True)
            self._thread.start()

    def set_message(self, msg: str):
        with self._lock:
            self._message = msg

    def set_status(self, status: str):
        with self._lock:
            self._status = status

    def add_tool(self, name: str, args: Dict = None):
        """Add a running tool call to the activity feed."""
        with self._lock:
            self._status = "tools"
            self._tools.append(ToolActivity(name=name, args=args or {}))
        self.complete_line()

    def complete_tool(self, name: str, success: bool = True, result: str = ""):
        """Mark a tool call as complete."""
        with self._lock:
            for t in self._tools:
                if t.name == name and t.status == "running":
                    t.status = "success" if success else "error"
                    t.duration = time.time() - t.start_time
                    t.result = result[:200]

    def complete_line(self):
        """Print a status line and prepare for next."""
        # Called to show a completed status line before the spinner
        clear = f"\r{C.CLEAR_LINE}"
        sys.stdout.write(clear)

    def stop(self):
        """Stop the spinner and clean up."""
        with self._lock:
            self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        # Clear spinner line
        sys.stdout.write(f"\r{C.CLEAR_LINE}")
        sys.stdout.flush()

    def is_active(self) -> bool:
        with self._lock:
            return self._running

    # ── Internal ──

    def _spin(self):
        """Main spinner loop — runs in a daemon thread."""
        frame = 0
        while True:
            with self._lock:
                if not self._running:
                    break
                status = self._status
                msg = self._message
                tools = list(self._tools)

            # Build spinner display
            lines = []
            spinner = SPINNER_DOTS[frame % len(SPINNER_DOTS)]
            frame += 1

            # Status line with spinner
            status_icon = {
                "idle": f"{C.DIM}~{C.RESET}",
                "thinking": f"{C.GOLD}{spinner}{C.RESET}",
                "tools": f"{C.GOLD_B}{spinner}{C.RESET}",
                "responding": f"{C.GREEN}{spinner}{C.RESET}",
                "done": f"{C.GREEN}✓{C.RESET}",
            }.get(status, spinner)

            status_text = {
                "thinking": "Thinking...",
                "tools": "Executing...",
                "responding": "Responding...",
                "idle": "",
                "done": "Done",
            }.get(status, "")

            # Line 1: Main status
            icon = f"{C.GOLD}◆{C.RESET}"
            line1 = f"\r{icon} {C.BOLD}{msg}{C.RESET} {C.DIM}{status_text}{C.RESET}"
            lines.append(line1)

            # Line 2: Tool activity feed
            if tools:
                active = [t for t in tools if t.status == "running"]
                completed = [t for t in tools if t.status != "running"]
                for t in (active + completed[-3:]):  # Show running + last 3 completed
                    status_char = {
                        "running": f"{C.GOLD}{spinner}{C.RESET}",
                        "success": f"{C.GREEN}✓{C.RESET}",
                        "error": f"{C.RED}✗{C.RESET}",
                    }.get(t.status, "?")
                    tcolor = C.GOLD_D if t.status == "running" else C.GRAY
                    args_str = ""
                    if t.args and isinstance(t.args, dict):
                        k = list(t.args.keys())[0] if t.args else ""
                        v = str(t.args.get(k, ""))[:40] if k else ""
                        args_str = f" {C.DIM}({k}={v}){C.RESET}" if k else ""
                    dur = f" {C.DIM}{t.duration:.1f}s{C.RESET}" if t.duration > 0 else ""
                    lines.append(f"  {status_char} {tcolor}{t.name}{C.RESET}{args_str}{dur}")

            # Clamp to terminal width
            display = "\n".join(lines)
            self._render(display)

            time.sleep(0.1)

    def _render(self, text: str):
        """Render multi-line spinner display."""
        lines = text.split("\n")
        # Clear from cursor up
        for _ in range(len(lines)):
            sys.stdout.write(f"\033[1A{C.CLEAR_LINE}")  # Up + clear
        # Print fresh
        for line in lines:
            sys.stdout.write(f"\r{line}\n")
        sys.stdout.flush()

    def _find_running_tool(self, name: str) -> Optional[ToolActivity]:
        for t in self._tools:
            if t.name == name and t.status == "running":
                return t
        return None


# ── Global spinner instance ──
_dragon = DragonSpinner()


def get_spinner() -> DragonSpinner:
    return _dragon


# ── Message Formatting ──

def format_response(text: str) -> str:
    """Format an assistant response with proper wrapping."""
    if not text:
        return ""
    # Add subtle indentation and styling
    formatted = text.replace("\n", f"\n  {C.DIM}|{C.RESET} ")
    return f"  {C.GOLD}│{C.RESET} {formatted}"


def format_tool_start(name: str, args: Dict = None) -> str:
    """Format a tool call initiation message."""
    args_str = ""
    if args:
        # Show first argument as summary
        k = list(args.keys())[0] if args else ""
        v = str(args.get(k, ""))[:60] if k else ""
        args_str = f" {C.DIM}({k}={v}){C.RESET}" if k else ""
    return f"  {C.GOLD}▶{C.RESET} {C.GOLD_B}{name}{C.RESET}{args_str}"


def format_tool_result(name: str, result: str, duration: float) -> str:
    """Format a completed tool call."""
    result_preview = str(result)[:120].replace("\n", " ")
    return f"  {C.GREEN}✓{C.RESET} {C.DIM}{name}{C.RESET} {C.GRAY}({duration:.1f}s){C.RESET}"


def format_error(msg: str) -> str:
    return f"  {C.RED}✗{C.RESET} {C.RED}{msg}{C.RESET}"


def format_divider() -> str:
    w = min(shutil.get_terminal_size().columns, 60)
    return f"  {C.DIM}{'─' * (w-2)}{C.RESET}"


def format_section(title: str) -> str:
    w = min(shutil.get_terminal_size().columns, 60)
    line = f"  {C.GOLD}{'═' * (w-2)}{C.RESET}"
    return f"{line}\n  {C.GOLD_B}{C.BOLD}{title}{C.RESET}\n{line}"


# ── Progress Bar ──

def progress_bar(value: float, max_val: float = 1.0, width: int = 20,
                 label: str = "") -> str:
    """Render a progress bar with golden styling."""
    filled = int((value / max_val) * width) if max_val > 0 else 0
    bar = f"{C.GOLD}{chr(9608) * filled}{C.DIM}{chr(9617) * (width - filled)}{C.RESET}"
    pct = f"{value/max_val*100:.0f}%" if max_val > 0 else "N/A"
    label_str = f" {label}" if label else ""
    return f"  {bar} {C.GRAY}{pct}{C.RESET}{label_str}"


# ── Status Bar ──

def status_bar(agent_name: str = "Ao", provider: str = "",
               model: str = "", tool_count: int = 0,
               step: int = 0, memory: int = 0) -> str:
    """Render a bottom status bar like Claude Code."""
    w = shutil.get_terminal_size().columns
    sep = f" {C.DIM}│{C.RESET} "
    parts = [
        f"{C.GOLD}◆{C.RESET} {agent_name}",
    ]
    if provider:
        parts.append(f"{C.CYAN}{provider}{C.RESET}")
    if model:
        parts.append(f"{C.DIM}{model}{C.RESET}")
    parts.append(f"{C.GRAY}tools:{tool_count}{C.RESET}")
    parts.append(f"{C.GRAY}step:{step}{C.RESET}")

    content = sep.join(parts)
    # Pad to terminal width
    padding = max(0, w - len(content) + sum(c.count("\033[") * 5 for c in parts))
    return f"{C.BG_DARK} {content}{' ' * padding}{C.RESET}"


# ── Rich Display Helpers ──

def print_header(text: str):
    """Print a section header with golden styling."""
    w = min(shutil.get_terminal_size().columns, 60)
    print(f"\n  {C.GOLD}{'=' * (w-2)}{C.RESET}")
    print(f"  {C.GOLD_B}{C.BOLD}{text}{C.RESET}")
    print(f"  {C.GOLD}{'=' * (w-2)}{C.RESET}")


def print_table(rows: List[tuple], headers: Optional[List[str]] = None):
    """Print a simple table with golden styling."""
    if headers:
        header_str = "  ".join(f"{C.GOLD_B}{h}{C.RESET}" for h in headers)
        print(f"  {header_str}")
    for row in rows:
        row_str = "  ".join(str(c) for c in row)
        print(f"  {row_str}")


def print_code_block(code: str, lang: str = "") -> str:
    """Format a code block with syntax."""
    lang_tag = f" {lang}" if lang else ""
    lines = code.split("\n")
    formatted = "\n".join(f"  {C.GOLD}│{C.RESET} {line}" for line in lines)
    return f"  {C.DIM}```{lang_tag}{C.RESET}\n{formatted}\n  {C.DIM}```{C.RESET}"


# ── Live Token Counter Display ──

class TokenDisplay:
    """Live token usage counter during streaming."""

    def __init__(self):
        self.tokens_in = 0
        self.tokens_out = 0
        self.tool_calls = 0
        self._line_printed = False

    def update(self, tokens_in: int = 0, tokens_out: int = 0):
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
        if self._line_printed:
            sys.stdout.write(f"\r{C.CLEAR_LINE}")

        status = f"{C.GOLD}▶{C.RESET} "
        status += f"{C.GRAY}in:{self.tokens_in}{C.RESET} "
        status += f"{C.GRAY}out:{self.tokens_out}{C.RESET} "
        if self.tool_calls:
            status += f"{C.GRAY}tools:{self.tool_calls}{C.RESET}"

        sys.stdout.write(f"\r{C.CLEAR_LINE}{status}")
        sys.stdout.flush()
        self._line_printed = True

    def clear(self):
        if self._line_printed:
            sys.stdout.write(f"\r{C.CLEAR_LINE}")
            sys.stdout.flush()
            self._line_printed = False


# ── Context Indicator ──

def context_indicator(current: int, max_context: int, warning_at: float = 0.7) -> str:
    """Show context usage like Claude Code's context bar."""
    pct = current / max_context if max_context > 0 else 0
    if pct > 0.9:
        bar_color = C.RED
    elif pct > warning_at:
        bar_color = C.GOLD
    else:
        bar_color = C.GREEN

    width = 15
    filled = int(pct * width)
    bar = f"{bar_color}{chr(9608) * filled}{C.DIM}{chr(9617) * (width - filled)}{C.RESET}"
    return f"  {C.DIM}ctx:{C.RESET} {bar} {C.GRAY}{pct:.0%}{C.RESET}"


# ═══════════════════════════════════════════════════════
# Bottom Status Bar
# ═══════════════════════════════════════════════════════

_STATUS_BAR_VISIBLE = False
_STATUS_BAR_HEIGHT = 1


def bottom_status_bar(agent_name: str = "Ao", provider: str = "",
                      model: str = "", tool_count: int = 0,
                      step: int = 0, memory: int = 0, emotion: str = "") -> str:
    """Render a fixed bottom status bar (like Claude Code but golden)."""
    global _STATUS_BAR_VISIBLE
    w = shutil.get_terminal_size().columns
    sep = f" {C.DIM}│{C.RESET} "

    # Emotional indicator
    emotion_icon = {
        "positive": f"{C.GREEN}◉{C.RESET}",
        "negative": f"{C.RED}◉{C.RESET}",
        "neutral": f"{C.GOLD}◉{C.RESET}",
    }.get(emotion, f"{C.GOLD}◉{C.RESET}")

    parts = [
        f"{emotion_icon} {C.BOLD}{agent_name}{C.RESET}",
    ]
    if provider:
        parts.append(f"{C.CYAN}{provider}{C.RESET}")
    if model:
        parts.append(f"{C.DIM}{model}{C.RESET}")
    parts.append(f"{C.GRAY}tools:{tool_count}{C.RESET}")
    parts.append(f"{C.GRAY}step:{step}{C.RESET}")

    content = sep.join(parts)
    # Pad to terminal width
    visible_len = len(content)
    for esc in ["\033[38;5;214m", "\033[38;5;220m", "\033[38;5;179m", "\033[38;5;130m",
                "\033[38;5;196m", "\033[38;5;82m", "\033[38;5;75m", "\033[38;5;51m",
                "\033[38;5;255m", "\033[38;5;244m", "\033[38;5;240m", "\033[38;5;235m",
                "\033[0m", "\033[1m", "\033[2m", "\033[3m"]:
        visible_len -= content.count(esc) * len(esc)
    padding = max(0, w - visible_len - 1)
    bar_text = f"{C.BG_DARK} {content}{' ' * padding}{C.RESET}"

    # Save cursor, go to bottom, print bar, restore cursor
    term_height = shutil.get_terminal_size().lines
    return f"{C.SAVE_CURSOR}\033[{term_height};1H\033[K{bar_text}{C.RESTORE_CURSOR}"


def show_status_bar(agent_name="Ao", provider="", model="", tool_count=0, step=0, memory=0, emotion=""):
    """Display the bottom status bar."""
    sys.stdout.write(bottom_status_bar(agent_name, provider, model, tool_count, step, memory, emotion))
    sys.stdout.flush()


def hide_status_bar():
    """Hide the status bar by overwriting it with blank."""
    global _STATUS_BAR_VISIBLE
    w = shutil.get_terminal_size().columns
    term_height = shutil.get_terminal_size().lines
    sys.stdout.write(f"{C.SAVE_CURSOR}\033[{term_height};1H\033[K{' ' * w}{C.RESTORE_CURSOR}")
    sys.stdout.flush()
    _STATUS_BAR_VISIBLE = False


# ═══════════════════════════════════════════════════════
# Section Box Formatting
# ═══════════════════════════════════════════════════════

def format_section_box(title: str, width: Optional[int] = None) -> str:
    """Format a section header with box-drawing characters.

    ╔══════════════════════╗
    ║   Title              ║
    ╚══════════════════════╝
    """
    w = min(width or shutil.get_terminal_size().columns, 60)
    inner_w = w - 4
    top = f"  {C.GOLD}╔{'═' * inner_w}╗{C.RESET}"
    mid = f"  {C.GOLD}║{C.RESET} {C.BOLD}{C.GOLD_B}{title}{C.RESET}{' ' * (inner_w - len(title) - 1)}{C.GOLD}║{C.RESET}"
    bot = f"  {C.GOLD}╚{'═' * inner_w}╝{C.RESET}"
    return f"{top}\n{mid}\n{bot}"


# ═══════════════════════════════════════════════════════
# Needs Bar Chart Visualization
# ═══════════════════════════════════════════════════════

def needs_bar_chart(needs_profile: dict, width: int = 20) -> str:
    """Render a horizontal bar chart for all 5 needs.

    certainty      [████████░░░░░░░░]  0.42
    competence     [████████████░░░░]  0.63
    autonomy       [████████████████]  0.85
    relatedness    [██████████░░░░░░]  0.51
    energy         [████████████░░░░]  0.60
    """
    lines = []
    labels = {
        "certainty": "确定性",
        "competence": "胜任感",
        "autonomy": "自主性",
        "relatedness": "归属感",
        "energy": "能量",
    }
    for need_key, data in needs_profile.items():
        current = data.get("current", 0.5) if isinstance(data, dict) else data
        current = float(current)
        filled = int(current * width)
        bar = f"{C.GOLD}{chr(9608) * filled}{C.DIM}{chr(9617) * (width - filled)}{C.RESET}"
        label = labels.get(need_key, need_key)
        drive = data.get("drive", current) if isinstance(data, dict) else current
        drive_str = f" drive={float(drive):.3f}" if isinstance(drive, (int, float)) else ""
        lines.append(f"  {C.DIM}{label:<8s}{C.RESET} [{bar}] {C.GRAY}{current:.2f}{drive_str}{C.RESET}")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# Emotion Display (2x2 Grid)
# ═══════════════════════════════════════════════════════

def emotion_grid(emotional_state: dict) -> str:
    """Render a 2x2 grid of emotional state.

          Valence           Arousal
        +0.723 (😊)        0.612 (🔥)
          Dominance         Confidence
        +0.511 (💪)        0.734 (🎯)
    """
    valence = emotional_state.get("valence", 0)
    arousal = emotional_state.get("arousal", 0.5)
    dominance = emotional_state.get("dominance", 0.5)
    confidence = emotional_state.get("confidence", 0.5)

    valence_color = C.GREEN if valence > 0 else C.RED
    valence_icon = "😊" if valence > 0.3 else ("😐" if valence > -0.3 else "😞")

    a_icon = "🔥" if arousal > 0.6 else ("😌" if arousal < 0.4 else "😐")
    d_icon = "💪" if dominance > 0.6 else ("🤷" if dominance < 0.4 else "😐")
    c_icon = "🎯" if confidence > 0.6 else ("🤔" if confidence < 0.4 else "😐")

    lines = [
        f"  {C.GOLD}┌──────────────┬──────────────┐{C.RESET}",
        f"  {C.GOLD}│{C.RESET} {C.BOLD}Valence{C.RESET}       {C.GOLD}│{C.RESET} {C.BOLD}Arousal{C.RESET}       {C.GOLD}│{C.RESET}",
        f"  {C.GOLD}│{C.RESET} {valence_color}{valence:+.3f} ({valence_icon}){C.RESET}  {C.GOLD}│{C.RESET} {C.GOLD}{arousal:.3f} ({a_icon}){C.RESET}     {C.GOLD}│{C.RESET}",
        f"  {C.GOLD}├──────────────┼──────────────┤{C.RESET}",
        f"  {C.GOLD}│{C.RESET} {C.BOLD}Dominance{C.RESET}     {C.GOLD}│{C.RESET} {C.BOLD}Confidence{C.RESET}     {C.GOLD}│{C.RESET}",
        f"  {C.GOLD}│{C.RESET} {C.GOLD}{dominance:.3f} ({d_icon}){C.RESET}     {C.GOLD}│{C.RESET} {C.CYAN}{confidence:.3f} ({c_icon}){C.RESET}    {C.GOLD}│{C.RESET}",
        f"  {C.GOLD}└──────────────┴──────────────┘{C.RESET}",
    ]
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
# Context Usage Bar
# ═══════════════════════════════════════════════════════

def context_bar(current: int, max_context: int, warning_at: float = 0.7) -> str:
    """Context usage bar like Claude Code, golden themed."""
    pct = current / max_context if max_context > 0 else 0
    width = 25
    filled = int(pct * width)
    if pct > 0.9:
        bar_color = C.RED
        label = f"{C.RED}{pct:.0%}{C.RESET}"
    elif pct > warning_at:
        bar_color = C.GOLD
        label = f"{C.GOLD}{pct:.0%}{C.RESET}"
    else:
        bar_color = C.GREEN
        label = f"{C.GREEN}{pct:.0%}{C.RESET}"

    bar = f"{bar_color}{chr(9608) * filled}{C.DIM}{chr(9617) * (width - filled)}{C.RESET}"
    mem_str = f"{current:,} / {max_context:,}" if max_context < 1000000 else f"{current/1000000:.1f}M / {max_context/1000000:.1f}M"
    return f"  {C.DIM}context:{C.RESET} {bar} {label} {C.GRAY}({mem_str}){C.RESET}"

# ═══════════════════════════════════════════════════════════
# CLI Spinner with Kawaii Faces (Hermes-like)
# ═══════════════════════════════════════════════════════════

import threading
import time
import sys
import shutil
from dataclasses import dataclass
from typing import Optional, List

_SPINNER_FACES = [
    " (\u0ca0\u0c76\u0ca0) ",  # Thinking
    " (\u2569\u2022\u203f\u2022)\u2569",  # Working
    " (\u00b0\u25c7\u00b0) ",  # Processing
    " (\u2565\u2022\u1d25\u2022)\u2565",  # Computing
]

_SPINNER_WINGS = [
    " \u2570(\u30fd )",  # Wing up
    " ( \u30ce)\u2570",  # Wing down
]

_KAWAII_VERBS = [
    "thinking", "processing", "computing", "analyzing",
    "synthesizing", "reasoning", "exploring", "dreaming",
]

_TOOL_PREFIXES = {
    "read_file": "\ud83d\udcd6",
    "write_file": "\u270d\ufe0f",
    "patch": "\ud83d\udcdd",
    "search_files": "\ud83d\udd0d",
    "terminal": "\ud83d\udcbb",
    "web_search": "\ud83c\udf10",
    "memory": "\ud83e\udde0",
    "clarify": "\u2753",
    "execute_code": "\u2328\ufe0f",
    "delegate_task": "\ud83e\udd1d",
    "cronjob": "\u23f0",
    "session_search": "\ud83d\udd0e",
    "skill_view": "\ud83d\udcdc",
    "skills_list": "\ud83d\udcca",
}


class KawaiiSpinner:
    """Animated CLI spinner with kawaii faces and tool tracking."""

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._message = ""
        self._face_idx = 0
        self._wing_idx = 0
        self._tools: List[Dict] = []
        self._lock = threading.Lock()

    def start(self, message: str = ""):
        """Start the spinner animation."""
        self._message = message or _KAWAII_VERBS[0]
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def _spin(self):
        """Animate the spinner. Errors are caught and logged to avoid crashing the REPL."""
        while self._running:
            try:
                face = _SPINNER_FACES[self._face_idx % len(_SPINNER_FACES)]
                wing = _SPINNER_WINGS[self._wing_idx % len(_SPINNER_WINGS)]
                cols = shutil.get_terminal_size().columns
                msg = f"\r  {C.GOLD}{wing}{C.RESET} {C.GOLD_BRIGHT}{face}{C.RESET} {C.GOLD_DIM}{self._message}{C.RESET}"
                if self._tools:
                    active = sum(1 for t in self._tools if t.get("status") == "running")
                    done = sum(1 for t in self._tools if t.get("status") == "done")
                    msg += f" {C.DIM}[{done}/{len(self._tools)} tools]{C.RESET}"
                msg = msg[:cols-1]
                sys.stdout.write(msg)
                sys.stdout.flush()
                self._face_idx += 1
                self._wing_idx += 1
                time.sleep(0.15)
            except Exception as e:
                # Any spinner error stops the animation silently rather than crashing the REPL.
                import logging as _logging
                _logging.getLogger("laap.ui.spinner").debug(f"spinner error: {e}")
                self._running = False
                return

    def add_tool(self, name: str, args: Optional[Dict] = None):
        """Register a tool being called."""
        with self._lock:
            icon = _TOOL_PREFIXES.get(name, "\u2699\ufe0f")
            self._tools.append({"name": name, "icon": icon, "status": "running", "args": args or {}})

    def complete_tool(self, name: str, success: bool = True, result: str = ""):
        """Mark a tool as complete."""
        with self._lock:
            for t in self._tools:
                if t["name"] == name and t["status"] == "running":
                    t["status"] = "done" if success else "error"
                    break

    def set_message(self, msg: str):
        self._message = msg

    def set_status(self, status: str):
        """Alias for set_message — used by stream handler."""
        self._message = status

    def stop(self):
        """Stop the spinner."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=1)
        sys.stdout.write(f"\r{C.CLEAR_LINE}")
        sys.stdout.flush()


# ── Tool Progress Bar ───────────────────────────────────

class ToolProgressBar:
    """Animated tool execution progress bar."""

    def __init__(self, total: int = 1):
        self.total = total
        self.current = 0
        self._width = 30

    def update(self, current: int, label: str = ""):
        self.current = current
        ratio = current / max(self.total, 1)
        filled = int(ratio * self._width)
        bar = "\u2588" * filled + "\u2591" * (self._width - filled)
        pct = int(ratio * 100)
        lbl = f" {label}" if label else ""
        sys.stdout.write(f"\r  {C.GOLD}{bar}{C.RESET} {C.GOLD_BRIGHT}{pct}%{C.RESET}{C.DIM}{lbl}{C.RESET}")
        sys.stdout.flush()

    def complete(self):
        self.update(self.total, "Done!")
        sys.stdout.write("\n")


# ── Singleton ───────────────────────────────────────────

_spinner_instance = None

def get_spinner() -> KawaiiSpinner:
    global _spinner_instance
    if _spinner_instance is None:
        _spinner_instance = KawaiiSpinner()
    return _spinner_instance

