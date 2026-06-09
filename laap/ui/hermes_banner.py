"""
LAAP — Hermes-style Welcome Banner

Inspired by the Hermes Agent welcome banner:
  https://github.com/NousResearch/hermes-agent
Layout (top to bottom):

    [ LAAP-AGENT large gradient ASCII ]            (terminal width >= 95)
    [ Welcome panel: ]
        ┌─ LAAP Agent v0.3.0 (date) ─────────┐
        │  [dragon icon]  │  Available Tools │
        │   model         │  group: tools    │
        │   cwd           │  ...             │
        │   session       │  Available Skills│
        │                 │  group: skills   │
        │                 │  ...             │
        │                 │  X tools · Y sk  │
        └─────────────────┴──────────────────┘
    [ Welcome tip line ]
    [ Bottom status bar (optional) ]
"""

from __future__ import annotations
import os
import sys
import shutil
import logging
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger("laap.ui.hermes_banner")

# ── LAAP colors (Hermes-inspired gold/bronze palette) ──────────

GOLD       = "#FFD700"   # primary gold (titles, accents)
GOLD_BRIGHT= "#FFE55C"   # bright gold
GOLD_LIGHT = "#FFED80"   # very light gold
GOLD_DIM   = "#B8960C"   # dim gold
GOLD_DARK  = "#8B6914"   # dark gold
BRONZE     = "#CD7F32"   # bronze (borders, secondary)
BRONZE_DARK= "#8B6914"   # dark bronze
CRIMSON    = "#DC143C"   # crimson (errors, warnings)
CORNSILK   = "#FFF8DC"   # corn silk (text on dark)
BG_DARK    = "#1A1A2E"   # dark background

# Tool category colors (subtle accent variations)
CAT_COLORS = {
    "core":        "#FFBF00",   # amber
    "code":        "#FF6347",   # tomato
    "shell":       "#32CD32",   # lime green
    "git":         "#FFA500",   # orange
    "web":         "#1E90FF",   # dodger blue
    "memory":      "#DA70D6",   # orchid
    "agent":       "#FFD700",   # gold
    "mcp":         "#40E0D0",   # turquoise
    "custom":      "#A9A9A9",   # dark gray
    "general":     "#A9A9A9",
    "system":      "#FF4500",   # orange-red
    "development": "#FF6347",
    "memory_h":    "#DA70D6",
    "productivity":"#32CD32",
    "research":    "#1E90FF",
    "creative":    "#FF69B4",
    "data":        "#40E0D0",
    "devops":      "#FFA500",
    "security":    "#FF4500",
    "design":      "#FF69B4",
}


# ── Big ASCII Logo ─────────────────────────────────────────────
# 6 lines, gradient gold → bronze, with crimson accents.
# Two variants: wide (terminal width >= 100) and compact (>= 60).
# Each cell is a single Unicode block character for full width coverage.

LAAP_AGENT_LOGO_WIDE = r"""[bold #FFD700]██╗      █████╗  █████╗ ██████╗ [/][bold #FFE55C]   █████╗  ██████╗ ███████╗███╗   ██╗████████╗[/]
[bold #FFD700]██║     ██╔══██╗██╔══██╗██╔══██╗[/][bold #FFE55C]  ██╔══██╗██╔════╝ ██╔════╝████╗  ██║╚══██╔══╝[/]
[bold #FFED80]██║     ███████║███████║██████╔╝[/][#FFBF00] ███████║██║  ███╗█████╗  ██╔██╗ ██║   ██║[/]
[bold #FFED80]██║     ██╔══██║██╔══██║██╔═══╝ [/][#FFBF00] ██╔══██║██║   ██║██╔══╝  ██║╚██╗██║   ██║[/]
[bold #CD7F32]███████╗██║  ██║██║  ██║██║     [/][bold #CD7F32] ██║  ██║╚██████╔╝███████╗██║ ╚████║   ██║[/]
[bold #CD7F32]╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     [/][bold #CD7F32] ╚═╝  ╚═╝ ╚═════╝ ╚══════╝╚═╝  ╚═══╝   ╚═╝[/]"""

# Compact version for narrow terminals — uses "L A A P  A G E N T" as inline characters
LAAP_AGENT_LOGO_COMPACT = r"""[#FFD700] __         _____ ___    _    _____   _   _ _____ ____    _____ ___  _   _ [/]
[#FFD700] \ \       / ____|__ \  | |  | ____| | \ | | ____|  _ \  |_   _/ _ \| \ | |[/]
[#FFBF00]  \ \  /\ / / _   __) | | |  |  _|   |  \| |  _| | |_) |   | || | | |  \| |[/]
[#FFBF00]   \ \/  v / | | |__ <  | |  | |___  | |\  | |___|  _ <    | || |_| | |\  |[/]
[#CD7F32]    \  /\ /  | | ___) | | |__|_____| | | \_|_____|_| \_\  | | \___/| | \_|[/]
[#CD7F32]     \/  \/   |_||____/ |_____|     |_| (_)_____(_)  (_) |_|     |_| (_)[/]"""

LAAP_AGENT_LOGO = LAAP_AGENT_LOGO_WIDE


# ── Small dragon icon for left column ─────────────────────────

DRAGON_ICON = f"""[#CD7F32]⠀⠀⠀⠀⠀⠀⢀⣠⣴⣾⣇⠸⣿⠇⣸⣿⣷⣦⣄[/]
[#FFBF00]⢀⣠⣴⣶⠿⠋⣩⡿⣿⠟⢿⣿⢿⣍⠙⠿⣦⣄[/]
[#FFD700]⠀⠀⣴⣿⡿⠛⢁⡈⠛⢿⣿⣦[/]
[#FFBF00]⠀⠀⠈⠉⠻⢿⣿⣦⡉⠁[/]
[#CD7F32]⠀⠘⢷⣦⣈⠛⠃[/]
[#B8860B]⠀⠀⠉⠛⠷⠄[/]
[#B8860B]⠀⠀⣀⠑⢶⣄⡀[/]
[#B8860B]⠀⠀⣿⠁⢰⡆⠈⡿[/]
[#B8860B]⠀⠀⠈⠳⠈⣡⠞⠁[/]"""


# ── Curated tips corpus ────────────────────────────────────────

TIPS = [
    # Slash commands
    "/status — Show Ao's current PSI needs, mood, and step count.",
    "/needs — Visualize the five intrinsic needs (certainty, competence, autonomy, relatedness, energy).",
    "/evolve — Trigger an RSI (Recursive Self-Improvement) cycle in a sandbox.",
    "/fitness — Run a fitness evaluation against the current population.",
    "/lineage — Inspect the agent family tree (forks, mutations, fitness lineage).",
    "/swarm — Coordinate multiple agents via the SharedStateBus.",
    "/immune — Inspect the immune system (threat patterns blocked this session).",
    "/protocol — Show lifecycle state and trust contract with the user.",
    "/tools — List all registered tools grouped by category.",
    "/skills — List installed skills grouped by category.",
    "/model — Switch LLM model mid-session.",
    "/memory — Search the persistent hierarchical memory store.",
    # @ references (Hermes-style)
    "@file:src/main.py injects a file's contents into your next message.",
    "@file:main.py:10-50 injects only a slice of a file.",
    "@diff injects your current git diff into the message.",
    # Keybindings
    "Ctrl+C interrupts the running agent. Press twice to force exit.",
    "Ctrl+L clears the chat (memory persists).",
    "/clear — Reset the conversation view; persistent memory is untouched.",
    # Agent concepts
    "Ao is a PSI-driven agent: needs, drives, and emotions shape every action.",
    "Persistent memory has 4 layers: working, episodic, semantic, procedural.",
    "RSI (Recursive Self-Improvement) uses a sandbox to test changes before adoption.",
    "Every tool call is classified by the immune system before execution.",
    "Ao can fork itself — try /fork to spawn a child agent with a strategy.",
    # CLI flags
    "laap.py -q \"query\" runs a single non-interactive query and exits.",
    "laap.py -i forces interactive REPL mode (no full-screen TUI).",
    "laap.py --task \"...\" runs a one-shot task and prints the result.",
    # General
    "Ao's emotional state affects its decision thresholds — high uncertainty explores more.",
    "Use /config to manage multiple API providers (OpenAI, Anthropic, DeepSeek, custom).",
    "Ao learns from every successful tool call — proficiency grows with use.",
]


# ── Tooltip / context helpers ─────────────────────────────────

def _format_context_length(tokens: int) -> str:
    """Format context length like '128K' or '1M'."""
    if tokens >= 1_000_000:
        v = tokens / 1_000_000
        return f"{v:.1f}M" if abs(v - round(v)) > 0.05 else f"{round(v)}M"
    if tokens >= 1_000:
        v = tokens / 1_000
        return f"{v:.1f}K" if abs(v - round(v)) > 0.05 else f"{round(v)}K"
    return str(tokens)


def _display_toolset_name(name: str) -> str:
    """Normalize toolset identifier (strip `_tools` suffix)."""
    if not name:
        return "unknown"
    return name[:-6] if name.endswith("_tools") else name


# ── Inventory collectors ──────────────────────────────────────

def collect_tools() -> List[Tuple[str, str, str]]:
    """Collect all available tools, returning (name, category, description).

    Tries to load the agent's tool registry first (which has 21+ tools),
    falls back to the global AoRegistry auto-discovery.
    """
    out: List[Tuple[str, str, str]] = []
    try:
        from laap.tools.tool_registry import ToolRegistry
        from laap.tools.code_edit import register_all as _r1
        from laap.tools.shell import register_all as _r2
        from laap.tools.web import register_all as _r3
        r = ToolRegistry()
        _r1(r); _r2(r); _r3(r)
        for t in r.list():
            out.append((t.name, t.category or "general", t.description or ""))
    except Exception as e:
        logger.debug(f"Tool collection failed: {e}")
    return out


def collect_skills() -> List[Tuple[str, str, str]]:
    """Collect installed skills, returning (name, category, description)."""
    out: List[Tuple[str, str, str]] = []
    try:
        from laap.skills.manager import SkillManager
        mgr = SkillManager()
        # Also scan the package's skills/ dir for SKILL.md files
        skills_pkg = Path(__file__).resolve().parent.parent / "skills"
        if skills_pkg.is_dir():
            mgr.engine.add_dir(skills_pkg)
            mgr.engine.discover()
        for s in mgr.list_skills():
            out.append((s["name"], s.get("category") or "general", s.get("description", "")))
    except Exception as e:
        logger.debug(f"Skill collection failed: {e}")
    return out


def get_active_model() -> Tuple[str, str, Optional[int]]:
    """Return (model_name, provider, context_length) from current config."""
    try:
        from laap.cli.config_manager import config_manager
        if config_manager.is_configured():
            active = config_manager.get_active()
            if active:
                model = active.model
                provider = config_manager.config.active_provider
                ctx = None
                try:
                    from laap.llm.models_dev import lookup_model
                    info = lookup_model(model)
                    if info and "context_length" in info:
                        ctx = info["context_length"]
                except Exception:
                    pass
                return (model, provider, ctx)
    except Exception:
        pass
    return ("(not configured)", "—", None)


def get_session_id() -> str:
    """Return a short session id."""
    import time
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def get_random_tip() -> str:
    """Pick a random tip from the corpus."""
    import random
    return random.choice(TIPS)


# ── Banner builders ──────────────────────────────────────────

def build_banner(
    model: Optional[str] = None,
    provider: Optional[str] = None,
    context_length: Optional[int] = None,
    cwd: Optional[str] = None,
    session_id: Optional[str] = None,
    tools: Optional[List[Tuple[str, str, str]]] = None,
    skills: Optional[List[Tuple[str, str, str]]] = None,
    show_tip: bool = True,
    show_warnings: bool = True,
) -> "ConsoleRenderable":
    """Build the full welcome banner as a Rich renderable.

    Returns a Rich Group of (logo, panel, tip) ready for console.print.
    """
    from rich.console import Group
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
    from rich.align import Align

    # Resolve defaults
    if model is None or provider is None:
        m, p, c = get_active_model()
        model = model or m
        provider = provider or p
        context_length = context_length or c
    cwd = cwd or os.getcwd()
    session_id = session_id or get_session_id()
    tools = tools if tools is not None else collect_tools()
    skills = skills if skills is not None else collect_skills()

    # ── Build left column (dragon icon + model info)
    left_lines: List[Text] = []
    left_lines.append(Text(DRAGON_ICON))
    left_lines.append(Text(""))
    model_short = model.split("/")[-1] if "/" in model else model
    if model_short.endswith(".gguf"):
        model_short = model_short[:-5]
    if len(model_short) > 28:
        model_short = model_short[:25] + "..."
    ctx_str = ""
    if context_length:
        ctx_str = f" [dim {GOLD_DARK}]·[/] [dim {GOLD_DARK}]{_format_context_length(context_length)} context[/]"
    left_lines.append(Text.from_markup(
        f"[bold {GOLD}]{model_short}[/]{ctx_str} [dim {GOLD_DARK}]·[/] [dim {GOLD_DARK}]Ao Cognition[/]"
    ))
    left_lines.append(Text.from_markup(f"[dim {GOLD_DARK}]{cwd}[/]"))
    left_lines.append(Text.from_markup(
        f"[dim {BRONZE}]Session: {session_id}[/]"
    ))
    if show_warnings:
        try:
            from laap.cli.config_manager import config_manager
            if not config_manager.is_configured():
                left_lines.append(Text(""))
                left_lines.append(Text.from_markup(
                    f"[bold yellow]⚠ No API key configured[/]"
                    f"[dim yellow] — run /config to set up a provider[/]"
                ))
        except Exception:
            pass
    left_content = Text("\n").join(left_lines)

    # ── Build right column (Tools + Skills)
    right_lines: List[Text] = [Text.from_markup(f"[bold {GOLD}]Available Tools[/]")]

    # Group tools by category
    toolsets: Dict[str, List[str]] = {}
    for tname, tcat, _tdesc in tools:
        cat = _display_toolset_name(tcat)
        toolsets.setdefault(cat, []).append(tname)
    sorted_ts = sorted(toolsets.keys())
    for ts in sorted_ts[:8]:
        names = sorted(toolsets[ts])
        color = CAT_COLORS.get(ts, CORNSILK)
        # Truncate long lists
        if len(", ".join(names)) > 45:
            short, total_len = [], 0
            for n in names:
                if total_len + len(n) + 2 > 42:
                    short.append("...")
                    break
                short.append(n)
                total_len += len(n) + 2
            names = short
        names_str = ", ".join(names)
        right_lines.append(Text.from_markup(
            f"[dim {GOLD_DARK}]{ts}:[/] [{color}]{names_str}[/]"
        ))

    if len(sorted_ts) > 8:
        right_lines.append(Text.from_markup(
            f"[dim {GOLD_DARK}](and {len(sorted_ts) - 8} more toolsets...)[/]"
        ))

    # Skills
    right_lines.append(Text(""))
    right_lines.append(Text.from_markup(f"[bold {GOLD}]Available Skills[/]"))
    skills_by_cat: Dict[str, List[str]] = {}
    for sname, scat, _sdesc in skills:
        skills_by_cat.setdefault(scat or "general", []).append(sname)
    if skills_by_cat:
        for cat in sorted(skills_by_cat.keys()):
            names = sorted(skills_by_cat[cat])
            color = CAT_COLORS.get(cat, CORNSILK)
            if len(names) > 8:
                display = names[:8]
                names_str = ", ".join(display) + f" +{len(names) - 8} more"
            else:
                names_str = ", ".join(names)
            if len(names_str) > 50:
                names_str = names_str[:47] + "..."
            right_lines.append(Text.from_markup(
                f"[dim {GOLD_DARK}]{cat}:[/] [{color}]{names_str}[/]"
            ))
    else:
        right_lines.append(Text.from_markup(f"[dim {GOLD_DARK}]No skills installed[/]"))

    # Summary
    right_lines.append(Text(""))
    total_skills = sum(len(v) for v in skills_by_cat.values())
    summary = f"{len(tools)} tools · {total_skills} skills · /help for commands"
    right_lines.append(Text.from_markup(f"[dim {GOLD_DARK}]{summary}[/]"))

    right_content = Text("\n").join(right_lines)

    # ── Assemble left + right into a grid panel
    grid = Table.grid(padding=(0, 2))
    grid.add_column("left", justify="center")
    grid.add_column("right", justify="left")
    grid.add_row(left_content, right_content)

    from laap import __version__ as VERSION
    # version label
    base = f"LAAP Agent v{VERSION} ({datetime.now().strftime('%Y.%m.%d')})"
    title_markup = f"[bold {GOLD}]{base}[/]"

    panel = Panel(
        grid,
        title=title_markup,
        border_style=BRONZE,
        padding=(0, 2),
    )

    # ── Build the full Group
    parts: List = []
    term_width = shutil.get_terminal_size().columns
    if term_width >= 100:
        # Wide logo (with "AGENT" suffix)
        logo_text = Text.from_markup(LAAP_AGENT_LOGO_WIDE)
        parts.append(Align.center(logo_text))
    elif term_width >= 60:
        # Compact logo (LAAP only)
        logo_text = Text.from_markup(LAAP_AGENT_LOGO_COMPACT)
        parts.append(Align.center(logo_text))
    else:
        # Very narrow — text-only title
        from laap import __version__ as VERSION
        parts.append(Align.center(Text.from_markup(
            f"[bold {GOLD}]LAAP AGENT v{VERSION}[/]"
        )))
    parts.append(Text(""))
    parts.append(panel)

    if show_tip:
        tip = get_random_tip()
        parts.append(Text(""))
        parts.append(Text.from_markup(
            f"[bold {GOLD}]Welcome to LAAP Agent![/] "
            f"[dim {GOLD_DARK}]Type your message or /help for commands.[/]"
        ))
        parts.append(Text.from_markup(
            f"[dim {BRONZE}]• tip:[/] [italic {CORNSILK}]{tip}[/]"
        ))

    return Group(*parts)


def print_banner(console=None, **kwargs):
    """Print the Hermes-style welcome banner.

    Args:
        console: Optional Rich Console. Defaults to a new one.
        **kwargs: Forwarded to build_banner.
    """
    from rich.console import Console
    if console is None:
        console = Console()
    console.print()
    console.print(build_banner(**kwargs))
    console.print()


# ── Convenience: ANSI (no-rich) fallback ──────────────────────

_ANSI_RESET = "\033[0m"
_ANSI_BOLD  = "\033[1m"
_ANSI_DIM   = "\033[2m"
_ANSI_GOLD  = "\033[38;2;255;215;0m"
_ANSI_BRONZE= "\033[38;2;205;127;50m"
_ANSI_DIMGOLD = "\033[38;2;184;150;12m"


def print_banner_plain():
    """Minimal ANSI-only banner for terminals without Rich support."""
    print()
    print(f"  {_ANSI_BOLD}{_ANSI_GOLD}LAAP Agent v{_get_version()} ({datetime.now().strftime('%Y.%m.%d')}){_ANSI_RESET}")
    print(f"  {_ANSI_DIM}{_ANSI_DIMGOLD}{'─' * 60}{_ANSI_RESET}")
    tools = collect_tools()
    skills = collect_skills()
    print(f"  {_ANSI_BOLD}{_ANSI_GOLD}Available Tools{_ANSI_RESET}  ({len(tools)})")
    grouped: Dict[str, List[str]] = {}
    for n, c, _ in tools:
        grouped.setdefault(_display_toolset_name(c), []).append(n)
    for ts in sorted(grouped.keys()):
        print(f"    {_ANSI_DIM}{_ANSI_DIMGOLD}{ts}:{_ANSI_RESET} {', '.join(sorted(grouped[ts]))}")
    print(f"  {_ANSI_BOLD}{_ANSI_GOLD}Available Skills{_ANSI_RESET}  ({len(skills)})")
    sk_grouped: Dict[str, List[str]] = {}
    for n, c, _ in skills:
        sk_grouped.setdefault(c or "general", []).append(n)
    for cat in sorted(sk_grouped.keys()):
        print(f"    {_ANSI_DIM}{_ANSI_DIMGOLD}{cat}:{_ANSI_RESET} {', '.join(sorted(sk_grouped[cat]))}")
    print(f"  {_ANSI_DIM}{_ANSI_DIMGOLD}/help for commands · {len(tools)} tools · {len(skills)} skills{_ANSI_RESET}")
    print()


def _get_version() -> str:
    try:
        from laap import __version__
        return __version__
    except Exception:
        return "0.3.0"


if __name__ == "__main__":
    print_banner()
