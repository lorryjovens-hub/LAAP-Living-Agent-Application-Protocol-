"""Display -- terminal display engine"""
from __future__ import annotations
import time, sys, shutil, threading, re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, TextIO
from enum import Enum

class Color:
    RESET = "[0m"
    BOLD = "[1m"
    DIM = "[2m"
    RED = "[31m"; GREEN = "[32m"
    YELLOW = "[33m"; BLUE = "[34m"
    MAGENTA = "[35m"; CYAN = "[36m"
    GRAY = "[90m"
    BRIGHT_GREEN = "[92m"; BRIGHT_CYAN = "[96m"
    BRIGHT_YELLOW = "[93m"; BRIGHT_MAGENTA = "[95m"
    BRIGHT_WHITE = "[97m"
    BG_BLACK = "[40m"
    @staticmethod
    def strip(text): return re.sub(r"\[[0-9;]*m", "", text)

@dataclass
class Theme:
    primary: str = Color.CYAN; secondary: str = Color.GRAY
    success: str = Color.GREEN; warning: str = Color.YELLOW
    error: str = Color.RED; info: str = Color.BLUE
    bold: str = Color.BOLD; dim: str = Color.DIM
    reset: str = Color.RESET
    user_tag: str = Color.BRIGHT_GREEN
    assistant_tag: str = Color.BRIGHT_CYAN
    system_tag: str = Color.BRIGHT_YELLOW
    tool_tag: str = Color.BRIGHT_MAGENTA
    token_color: str = Color.GREEN
DEFAULT_THEME = Theme()

class SpinnerStyle(str, Enum):
    DOTS = "dots"; LINE = "line"; ARC = "arc"

SPINNER_PATTERNS = {
    SpinnerStyle.DOTS: ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"],
    SpinnerStyle.LINE: ["|","/","-","\\"],
    SpinnerStyle.ARC: ["◜","◝","◞","◟"],
}

class Spinner:
    def __init__(self, message="", style=SpinnerStyle.DOTS,
                 color=Color.CYAN, stream=sys.stdout, delay=0.1):
        self.message = message; self.style = style
        self.color = color; self.stream = stream; self.delay = delay
        self._running = False; self._thread = None
        self._pattern = SPINNER_PATTERNS.get(style, SPINNER_PATTERNS[SpinnerStyle.DOTS])
        self._idx = 0

    def _spin(self):
        while self._running:
            frame = self._pattern[self._idx % len(self._pattern)]
            self.stream.write(f"{self.color}{frame} {self.message}{Color.RESET}")
            self.stream.flush(); self._idx += 1; time.sleep(self.delay)

    def start(self, message=None):
        if message: self.message = message
        self._running = True
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self, final_message=None):
        self._running = False
        if self._thread: self._thread.join(timeout=1.0)
        if final_message:
            self.stream.write(f"{final_message}
")
        else:
            self.stream.write("" + " " * (len(self.message) + 4) + "")
        self.stream.flush()

    def update(self, message): self.message = message
    def __enter__(self): self.start(); return self
    def __exit__(self, *a): self.stop()

class ProgressBar:
    def __init__(self, total=100, width=40, color=Color.CYAN, stream=sys.stdout):
        self.total = total; self.width = width; self.color = color; self.stream = stream
        self._current = 0; self._message = ""; self._start = time.time()

    def update(self, value, message=""):
        self._current = min(value, self.total)
        if message: self._message = message
        ratio = self._current / max(self.total, 1)
        filled = int(self.width * ratio)
        bar = "█" * filled + "░" * (self.width - filled)
        rate = self._current / max(time.time() - self._start, 0.001)
        eta = (self.total - self._current) / max(rate, 0.001)
        self.stream.write(f"{self.color}{bar}{Color.RESET}"
                       f" {ratio*100:5.1f}% [{self._current}/{self.total}]"
                       f" ETA:{eta:.1f}s {self._message}")
        self.stream.flush()

    def advance(self, step=1, msg=""): self.update(self._current + step, msg)
    def finish(self, msg="Done"):
        self._current = self.total; self._message = msg
        self.update(self.total); self.stream.write("
")
    def __enter__(self): return self
    def __exit__(self, *a): self.finish()

class MarkdownRenderer:
    def __init__(self, theme=None): self.theme = theme or DEFAULT_THEME

    def render(self, text):
        if not text: return ""
        r = text
        r = re.sub(r"",
            lambda m: f"
{self.theme.dim}[{m.group(1) or ""}]
{self.theme.reset}
{self.theme.secondary}{m.group(2)}{self.theme.reset}
", r)
        r = re.sub(r"^(#{1,6})\s+(.+)$",
            lambda m: f"
{self.theme.bold}{self.theme.primary}
{m.group(1)} {m.group(2)}{self.theme.reset}
", r, flags=re.MULTILINE)
        r = re.sub(r"\*\*(.+?)\*\*",
            lambda m: f"{self.theme.bold}{m.group(1)}{self.theme.reset}", r)
        r = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
            lambda m: f"{self.theme.secondary}{m.group(1)}
{self.theme.reset}({self.theme.info}{m.group(2)}{self.theme.reset})", r)
        return r

class Display:
    def __init__(self, theme=None, stream=sys.stdout, use_color=True):
        self.theme = theme or DEFAULT_THEME
        self.stream = stream; self.use_color = use_color
        self._spinner = None
        self._md = MarkdownRenderer(self.theme)

    def print(self, *args, color="", bold=False, **kw):
        t = " ".join(str(x) for x in args)
        if color and self.use_color: t = f"{color}{t}{Color.RESET}"
        if bold and self.use_color: t = f"{Color.BOLD}{t}{Color.RESET}"
        print(t, file=self.stream, **kw)

    def info(self, m): self.print(f"Info: {m}", color=self.theme.info)
    def success(self, m): self.print(f"OK: {m}", color=self.theme.success)
    def warning(self, m): self.print(f"Warn: {m}", color=self.theme.warning)
    def error(self, m): self.print(f"Err: {m}", color=self.theme.error)
    def debug(self, m): self.print(f"Dbg: {m}", color=self.theme.secondary)

    def show_user(self, content, tag="User"):
        tag_c = f"{self.theme.user_tag}[{tag}]{Color.RESET}" if self.use_color else f"[{tag}]"
        self.print(f"{tag_c} {content}")

    def show_assistant(self, content, tag="Asst"):
        tag_c = f"{self.theme.assistant_tag}[{tag}]{Color.RESET}" if self.use_color else f"[{tag}]"
        rendered = self._md.render(content) if self.use_color else content
        self.print(f"{tag_c} {rendered}")

    def show_system(self, content, tag="Sys"):
        tag_c = f"{self.theme.system_tag}[{tag}]{Color.RESET}" if self.use_color else f"[{tag}]"
        self.print(f"{tag_c} {content}")

    def show_tool(self, content, tag="Tool"):
        tag_c = f"{self.theme.tool_tag}[{tag}]{Color.RESET}" if self.use_color else f"[{tag}]"
        self.print(f"{tag_c} {content[:500]}")

    def spinner(self, msg="", style=SpinnerStyle.DOTS):
        self._spinner = Spinner(msg, style=style, color=self.theme.primary, stream=self.stream)
        self._spinner.start(); return self._spinner

    def stop_spinner(self, msg=None):
        if self._spinner: self._spinner.stop(msg); self._spinner = None

    def progress(self, total=100):
        return ProgressBar(total=total, color=self.theme.primary, stream=self.stream)

    def separator(self, ch="─", length=None):
        if length is None: length = shutil.get_terminal_size().columns
        self.print(ch * length, color=self.theme.secondary)

    def header(self, text):
        w = shutil.get_terminal_size().columns
        self.print(f"
 {text} ", color=self.theme.primary, bold=True)
        self.separator("═", w)

    def clear(self):
        self.stream.write("[2J[H"); self.stream.flush()

display = Display()