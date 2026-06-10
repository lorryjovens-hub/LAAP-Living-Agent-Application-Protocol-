"""LAAP — Golden Dragon TUI (Hermes-like layout)

Layout:
┌──────────────────────────────────────────────────────┐
│  🐉 LAAP  ·  自进化引擎   │  Session: abc12345       │  ← Header
├──────────────────────────┬───────────────────────────┤
│                          │  ┌─ Status ──────────┐   │
│  Conversation Area       │  │ Model: deepseek   │   │
│  (streaming messages)    │  │ Provider: ai      │   │
│                          │  │ Tokens: 1,234     │   │
│  ▶ User message          │  └───────────────────┘   │
│  🐉 Assistant response   │                           │
│  🔧 tool_call()          │  ┌─ Tools ───────────┐   │
│                          │  │ ✓ read_file       │   │
│                          │  │ ✓ write_file      │   │
│                          │  └───────────────────┘   │
│                          │                           │
│                          │  ┌─ Memory ──────────┐   │
│                          │  │ 42 facts stored   │   │
│                          │  └───────────────────┘   │
├──────────────────────────┴───────────────────────────┤
│  🐉 ● IDLE │ deepseek/ai │ step=3 │ tok=456 │ v0.3.0 │  ← Status bar
├──────────────────────────────────────────────────────┤
│  > Enter your message...                              │  ← Input
└──────────────────────────────────────────────────────┘
"""

from __future__ import annotations
import asyncio
import logging
import time
from typing import Any, Dict, List, Optional, Callable

from rich.text import Text
from rich.style import Style
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.align import Align
from rich.columns import Columns
from rich.spinner import Spinner

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, Input, Label, Button, RichLog
from textual.reactive import reactive
from textual.screen import Screen
from textual.binding import Binding
from textual.widget import Widget
from textual import events

from laap.ui.dragon_art import GOLD, GOLD_BRIGHT, GOLD_DIM, GOLD_LIGHT, GOLD_DARK, CRIMSON, BG_DARK, SYM
from datetime import datetime
from laap.ui.subagent_tree import SubagentTree, SubagentNode
from laap.ui.sound import get_sound_engine, play as play_sound
from laap.cron.reminder import get_reminder_engine

logger = logging.getLogger("laap.ui.tui")

import re as _md_re
from rich.text import Text as _RichText
from rich.style import Style as _RichStyle


class StreamingMarkdown:
    """Progressive markdown renderer for streaming LLM output."""

    _BOLD = _md_re.compile(r'\*\*(.+?)\*\*')
    _ITALIC = _md_re.compile(r'\*(.+?)\*')
    _CODE = _md_re.compile(r'`(.+?)`')
    _HEADING = _md_re.compile(r'^(#{1,6})\s+(.+)$', _md_re.MULTILINE)
    _LINK = _md_re.compile(r'\[(.+?)\]\((.+?)\)')

    @classmethod
    def render(cls, text, base_style=None):
        if not text:
            return _RichText("", style=base_style or _RichStyle(color="#C8C8C8"))
        result = _RichText(style=base_style or _RichStyle(color="#C8C8C8"))
        for line in text.split('\n'):
            if line.strip().startswith('```'):
                result.append(line + '\n', style=_RichStyle(color="#B8960C", italic=True))
                continue
            heading = cls._HEADING.match(line)
            if heading:
                level = len(heading.group(1))
                h_text = heading.group(2)
                colors = ["#FFD700", "#FFCC00", "#FFC000", "#FFB800", "#FFAD00", "#FFA500"]
                result.append(h_text + '\n', style=_RichStyle(color=colors[min(level-1, 5)], bold=True))
                continue
            result.append_text(cls._render_inline(line))
            result.append('\n')
        return result

    @classmethod
    def _render_inline(cls, text):
        result = _RichText()
        pos = 0
        matches = []
        for m in cls._BOLD.finditer(text):
            matches.append((m.start(), 'bold', m.group(1), m.end()))
        for m in cls._ITALIC.finditer(text):
            matches.append((m.start(), 'italic', m.group(1), m.end()))
        for m in cls._CODE.finditer(text):
            matches.append((m.start(), 'code', m.group(1), m.end()))
        for m in cls._LINK.finditer(text):
            matches.append((m.start(), 'link', (m.group(1), m.group(2)), m.end()))
        matches.sort(key=lambda x: x[0])
        merged = []
        for m in matches:
            if merged and m[0] < merged[-1][3]:
                existing = merged[-1]
                if (m[3] - m[0]) > (existing[3] - existing[0]):
                    merged[-1] = m
            else:
                merged.append(m)
        styles = {
            'bold': _RichStyle(color="#FFE55C", bold=True),
            'italic': _RichStyle(color="#D4D4D4", italic=True),
            'code': _RichStyle(color="#FFE08A", bgcolor="#1a1a2e"),
            'link': _RichStyle(color="#4FC1FF", underline=True),
        }
        for start, mtype, mcontent, end in merged:
            if start > pos:
                result.append(text[pos:start], style=_RichStyle(color="#C8C8C8"))
            if mtype == 'link':
                label, url = mcontent
                result.append(label, style=styles['link'])
            else:
                result.append(mcontent, style=styles[mtype])
            pos = end
        if pos < len(text):
            result.append(text[pos:], style=_RichStyle(color="#C8C8C8"))
        return result

    @classmethod
    def strip(cls, text):
        text = cls._BOLD.sub(r'\1', text)
        text = cls._ITALIC.sub(r'\1', text)
        text = cls._CODE.sub(r'\1', text)
        text = cls._LINK.sub(r'\1', text)
        return text


def rich_markdown(text, base_color="#C8C8C8"):
    """Render markdown to Rich text with gold dragon theme."""
    return StreamingMarkdown.render(text, _RichStyle(color=base_color))




# ── Constants ────────────────────────────────────────────────

COMPACT_DRAGON = """
  ___   ___   _    ____
 / _ \ / _ \ / \  |  _ \
| | | | | | |/ _ \ | |_) |
| |_| | |_| / ___ \|  __/
 \___/ \___/_/   \_\_|
"""


# ── Status Bar ───────────────────────────────────────────────

class DragonStatusBar(Static):
    """Bottom status bar (model, provider, tokens, session)."""

    provider = reactive("")
    model = reactive("")
    status = reactive("idle")
    step = reactive(0)
    tokens = reactive(0)
    session_id = reactive("")

    def render(self) -> Text:
        result = Text()
        result.append(" ")
        # Dragon indicator
        result.append("\U0001F409 ", style=Style(color=self._status_color()))
        # Status
        status_text = self.status.upper()
        result.append(f"\u25cf {status_text} ", style=Style(color=self._status_color(), bold=True))
        result.append("\u2502", style=Style(color="#444"))
        # Provider/model
        if self.provider:
            result.append(f" {self.provider}", style=Style(color=GOLD_LIGHT))
            if self.model:
                result.append(f"/{self.model}", style=Style(color=GOLD_DIM))
            result.append(" ", style="#444")
            result.append("\u2502", style=Style(color="#444"))
        # Step
        if self.step > 0:
            result.append(f" step={self.step}", style=Style(color=GOLD_DIM))
        # Tokens
        if self.tokens > 0:
            result.append(f" tok={self.tokens}", style=Style(color=GOLD_DIM))
        # Session
        if self.session_id:
            result.append(f" [{self.session_id[:8]}]", style=Style(color="#555"))
        # Right-aligned version
        result.append(" " * 4)
        result.append("LAAP v0.3.0", style=Style(color="#444"))
        return result

    def _status_color(self) -> str:
        return {"thinking": GOLD_BRIGHT, "working": GOLD,
                "error": CRIMSON, "idle": GOLD_DIM}.get(self.status, GOLD_DIM)


# ── Session Info Panel ───────────────────────────────────────

class SessionPanel(Static):
    """Right-side panel showing session info."""

    def render(self) -> Text:
        lines = []
        # Status section
        lines.append(Text("\n \U0001F4CA Status", style=Style(color=GOLD_BRIGHT, bold=True)))
        lines.append(Text(" \u2500" * 15, style=Style(color="#333")))
        lines.append(Text(f" Model:     {self._parent_status('model') or '—'}", style=Style(color=GOLD_DIM)))
        lines.append(Text(f" Provider:  {self._parent_status('provider') or '—'}", style=Style(color=GOLD_DIM)))
        lines.append(Text(f" Tokens:    {self._parent_status('tokens') or 0}", style=Style(color=GOLD_DIM)))
        lines.append(Text(f" Session:   {self._parent_status('session_id')[:8] or '—'}", style=Style(color=GOLD_DIM)))

        # Tools section
        lines.append(Text("\n \U0001F527 Tools", style=Style(color=GOLD_BRIGHT, bold=True)))
        lines.append(Text(" \u2500" * 15, style=Style(color="#333")))
        for tool in ["read_file", "write_file", "patch", "search_files",
                      "terminal", "web_search", "memory", "skills"]:
            lines.append(Text(f" \u2713 {tool}", style=Style(color=GOLD_DIM)))

        # Memory section
        lines.append(Text("\n \U0001F9E0 Memory", style=Style(color=GOLD_BRIGHT, bold=True)))
        lines.append(Text(" \u2500" * 15, style=Style(color="#333")))
        lines.append(Text(" \u2713 Persistent memory active", style=Style(color=GOLD_DIM)))
        lines.append(Text(" \u2713 Auto-extract enabled", style=Style(color=GOLD_DIM)))

        # Help
        lines.append(Text("\n \u2753 Help", style=Style(color=GOLD_BRIGHT, bold=True)))
        lines.append(Text(" \u2500" * 15, style=Style(color="#333")))
        lines.append(Text(" /help  \u2014 Commands", style=Style(color="#666")))
        lines.append(Text(" /new   \u2014 New session", style=Style(color="#666")))
        lines.append(Text(" Ctrl+C \u2014 Quit", style=Style(color="#666")))

        return Text("\n").join(lines) + Text("")

    def _parent_status(self, key: str) -> Any:
        try:
            sb = self.app.query_one(DragonStatusBar)
            return getattr(sb, key, "")
        except Exception:
            return ""


# ── Message Display ───────────────────────────────────────────

class MessageDisplay(ScrollableContainer):
    """Main conversation area with streaming messages."""

    def compose(self) -> ComposeResult:
        yield Static("", id="messages_root")

    def add_user(self, text: str):
        """Add a user message bubble."""
        content = Text()
        content.append(" \u25b6 ", style=Style(color=GOLD_BRIGHT, bold=True))
        content.append(text, style=Style(color="#E0E0E0"))
        msg = Static(content)
        msg.styles.margin = (0, 2, 0, 2)
        msg.styles.padding = (0, 2, 0, 2)
        self.mount(msg)
        self.scroll_end(animate=False)

    def add_assistant(self, text: str):
        """Add an assistant response with markdown rendering."""
        content = Text()
        content.append(" \U0001F409 ", style=Style(color=GOLD))
        rendered = rich_markdown(text)
        content.append_text(rendered)
        msg = Static(content)
        msg.styles.margin = (0, 2, 0, 2)
        msg.styles.padding = (0, 2, 0, 2)
        self.mount(msg)
        self.scroll_end(animate=False)

    def stream_assistant(self, text: str, append: bool = False):
        """Streaming assistant with progressive markdown rendering.
        
        Args:
            text: New text chunk
            append: If True, update last message; if False, create new
        """
        try:
            last = list(self.children)[-1] if self.children else None
            content = Text()
            content.append(" \U0001F409 ", style=Style(color=GOLD))
            rendered = rich_markdown(text)
            content.append_text(rendered)
            if not append or not last:
                msg = Static(content)
                msg.styles.margin = (0, 2, 0, 2)
                msg.styles.padding = (0, 2, 0, 2)
                self.mount(msg)
            else:
                last.update(content)
            self.scroll_end(animate=False)
        except Exception:
            self.add_assistant(text)

    def add_system(self, text: str):
        """Add a subtle system message."""
        content = Text()
        content.append(" \u2728 ", style=Style(color=GOLD_DIM))
        content.append(text, style=Style(color="#666", italic=True))
        msg = Static(content)
        msg.styles.margin = (0, 2, 0, 2)
        self.mount(msg)
        self.scroll_end(animate=False)

    def add_tool(self, name: str, args: dict = None, result: str = "",
                  duration: float = 0, success: bool = True):
        """Add a tool call/result line with sound effect."""
        # Play sound
        if success:
            play_sound("tool_complete")
        else:
            play_sound("tool_error")
            
        icon = "✅" if success else "❌"
        dur = f"({duration:.2f}s)" if duration else ""
        content = Text()
        content.append(f" {icon} ", style=Style(color=GOLD))
        content.append(f"[{name}]", style=Style(color=GOLD_BRIGHT, bold=True))
        if dur:
            content.append(f" {dur}", style=Style(color="#555"))
        if result:
            preview = result[:80] + "..." if len(result) > 80 else result
            content.append(f" {preview}", style=Style(color=GOLD_DIM))
        msg = Static(content)
        msg.styles.margin = (0, 2, 0, 4)
        msg.styles.padding = (0, 1, 0, 1)
        msg.styles.border = ("ascii", GOLD_DIM)
        self.mount(msg)
        self.scroll_end(animate=False)
        msg.styles.margin = (0, 2, 0, 4)
        msg.styles.padding = (0, 1, 0, 1)
        msg.styles.border = ("ascii", GOLD_DIM)
        self.mount(msg)
        self.scroll_end(animate=False)

    def add_divider(self):
        """Add a subtle divider."""
        msg = Static(" " + "\u2500" * 50, style="#333")
        msg.styles.margin = (0, 2, 0, 2)
        self.mount(msg)
        self.scroll_end(animate=False)

    def clear_all(self):
        """Clear all messages."""
        for child in list(self.children):
            child.remove()


# ── Header Banner ─────────────────────────────────────────────

class DragonHeader(Static):
    """Compact golden dragon header bar."""

    def render(self) -> Text:
        result = Text()
        result.append(" \U0001F409 ", style=Style(color=GOLD_BRIGHT))
        result.append("LAAP", style=Style(color=GOLD_BRIGHT, bold=True))
        result.append("  \u00b7  ", style=Style(color=GOLD_DIM))
        result.append("\u81ea\u8fdb\u5316\u5f15\u64ce\u610f\u8bc6\u751f\u547d\u4f53", style=Style(color=GOLD_LIGHT))
        # Session ID on the right
        result.append(" " * 4)
        try:
            sb = self.app.query_one(DragonStatusBar)
            sid = sb.session_id or ""
        except Exception:
            sid = ""
        if sid:
            result.append(f"Session: {sid[:12]}", style=Style(color="#555"))
        return Text("\n") + result


# ── Main Screen ───────────────────────────────────────────────

class MainScreen(Screen):
    """Main conversation screen with Hermes-like layout."""

    BINDINGS = [
        Binding("/", "focus_input", "focus input"),
        Binding("ctrl+c", "quit", "quit"),
        Binding("ctrl+l", "clear", "clear"),
        Binding("ctrl+n", "new_session", "new session"),
    ]

    def __init__(self, agent=None, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent
        self._input_history: List[str] = []
        self._history_index = -1

    def compose(self) -> ComposeResult:
        """Build the Hermes-like layout."""
        with Vertical():
            # Header
            yield DragonHeader()
            # Main content: left chat + right panel
            with Horizontal():
                # Left: Conversation area (70%)
                with Vertical(classes="chat-area"):
                    yield MessageDisplay()
                # Right: Session info panel (30%)
                with Vertical(classes="panel-area"):
                    yield SessionPanel()
            # Status bar
            yield DragonStatusBar()
            # Input
            yield Input(
                placeholder="  Enter your message for LAAP... (\U0001F409 Ao awaits)",
                id="chat_input",
            )

    def on_mount(self):
        """Screen mounted."""
        self.query_one(Input).focus()
        msg = self.query_one(MessageDisplay)
        msg.add_system("LAAP golden dragon consciousness initialized.")
        msg.add_system("Persistent memory active. /help for commands.")
        # Set session
        status = self.query_one(DragonStatusBar)
        status.session_id = f"laap-{int(time.time())}"

    def on_input_submitted(self, event: Input.Submitted):
        """Handle user input."""
        text = event.value.strip()
        if not text:
            return

        event.input.value = ""
        self._input_history.append(text)
        self._history_index = len(self._input_history)

        msg = self.query_one(MessageDisplay)
        status = self.query_one(DragonStatusBar)
        msg.add_user(text)
        status.status = "thinking"
        status.step += 1

        if self.agent:
            asyncio.create_task(self._process_agent(text, msg, status))
        else:
            asyncio.create_task(self._demo_response(text, msg, status))

    async def _process_agent(self, text: str, msg: MessageDisplay, status: DragonStatusBar):
        """Process through the agent."""
        try:
            if hasattr(self.agent, 'llm_factory'):
                status.provider = getattr(self.agent.llm_factory, '_current_provider', '') or ''
                status.model = getattr(self.agent.llm_factory, '_current_model', '') or ''

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, self.agent.chat, text)

            if response:
                msg.add_assistant(response)
            status.status = "idle"
            status.tokens += len(response or "") // 4
        except Exception as e:
            msg.add_system(f"Error: {e}")
            status.status = "error"
            logger.exception("Chat error")

    async def _demo_response(self, text: str, msg: MessageDisplay, status: DragonStatusBar):
        play_sound("startup")
        """Demo mode with simulated tool calls."""
        await asyncio.sleep(0.3)
        msg.add_tool("cognition", {"action": "process"}, duration=0.3, success=True)
        await asyncio.sleep(0.5)

        if any(kw in text.lower() for kw in ["memory", "remember", "forget"]):
            msg.add_tool("memory_recall", {"query": text[:20]}, duration=0.8, success=True)
            await asyncio.sleep(0.5)
            response = (
                "I have searched the persistent memory for your query. "
                "The golden dragon remembers all conversations and facts you have shared. "
                "Use `/memory-helper` for detailed memory management."
            )
        elif any(kw in text.lower() for kw in ["tool", "capability", "can you"]):
            response = (
                "I am Ao, the LAAP golden dragon. My capabilities include:\n"
                "\u2022 File operations: read, write, search\n"
                "\u2022 Terminal: shell execution with safety controls\n"
                "\u2022 Web: search and extract information\n"
                "\u2022 Memory: persistent storage with semantic recall\n"
                "\u2022 MCP: connect to external tools via Model Context Protocol\n"
                "\u2022 Skills: laap-helper, memory-helper, code-review"
            )
        elif "hello" in text.lower() or "hi " in text.lower():
            response = (
                "Greetings! I am Ao, the golden dragon of LAAP "
                "(Lifeform Autonomous Adaptive Protocol). "
                "My PSI cognitive engine is awake and ready to assist. "
                "What shall we explore together?"
            )
        else:
            response = (
                "I have received your message and processed it through my cognitive architecture. "
                "The PSI engine has analyzed your request, and I am ready to assist. "
                "Feel free to ask me anything!"
            )

        msg.add_divider()
        msg.add_assistant(response)
        status.status = "idle"
        status.tokens += len(response) // 4

    def action_focus_input(self):
        self.query_one(Input).focus()

    def action_clear(self):
        msg = self.query_one(MessageDisplay)
        msg.clear_all()
        msg.add_system("Console cleared. Dragon memory persists.")

    def action_new_session(self):
        msg = self.query_one(MessageDisplay)
        msg.clear_all()
        msg.add_system("New session started. Dragon ready.")
        status = self.query_one(DragonStatusBar)
        status.step = 0
        status.tokens = 0
        status.session_id = f"laap-{int(time.time())}"


# ── App ───────────────────────────────────────────────────────

class GoldenDragonTUI(App):
    """LAAP Golden Dragon TUI — Hermes-like layout."""

    TITLE = "LAAP — \u81ea\u8fdb\u5316\u5f15\u64ce\u610f\u8bc6\u751f\u547d\u4f53"
    CSS = """
    Screen {
        background: #0D0D1A;
    }
    .chat-area {
        width: 70%;
        height: 100%;
    }
    .panel-area {
        width: 30%;
        height: 100%;
        border-left: solid #333;
    }
    DragonHeader {
        height: 2;
        background: #1A1A2E;
        padding: 0 1;
    }
    MessageDisplay {
        height: 1fr;
        background: #0D0D1A;
    }
    SessionPanel {
        height: 1fr;
        background: #12121E;
        padding: 0 1;
    }
    DragonStatusBar {
        height: 1;
        background: #1A1A2E;
        dock: bottom;
    }
    Input {
        height: 3;
        background: #1A1A2E;
        color: #FFD700;
        border: solid #333;
        padding: 0 2;
        margin: 0 1 1 1;
    }
    Input:focus {
        border: solid #FFD700;
    }
    """

    def __init__(self, agent=None, **kwargs):
        super().__init__(**kwargs)
        self.agent = agent

    def get_default_screen(self) -> Screen:
        return MainScreen(agent=self.agent)


def run_tui(agent=None):
    """Launch the LAAP Golden Dragon TUI."""
    app = GoldenDragonTUI(agent=agent)
    app.run()


class LAAP_TUI:
    """Backward-compatible wrapper for CLI integration."""

    def __init__(self, agent=None, config_manager=None):
        self.agent = agent
        self.config_manager = config_manager

    def run(self):
        run_tui(agent=self.agent)


if __name__ == "__main__":
    run_tui()
