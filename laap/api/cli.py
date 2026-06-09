"""
LAAP — CLI Entry Point
Golden dragon startup, interactive REPL, single task execution, configuration wizard.
"""

from __future__ import annotations
import sys, os
# Ensure laap package is importable (works without pip install)
_laap_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _laap_root not in sys.path:
    sys.path.insert(0, _laap_root)

import argparse, sys, os, json, logging, subprocess, time
from typing import Any, Dict, List, Optional

from laap import __version__
from laap.agent.base import Agent, AgentConfig
from laap.agent.lifelike import LifelikeAgent, LifelikeConfig
from laap.agent.codex import CodexAgent, CodexConfig
from laap.llm.factory import LLMFactory
from laap.cli.repl import LAAP_REPL
from laap.cli.skins import render_logo, GOLD, GOLD_BRIGHT, GOLD_DIM, RESET, BOLD, SYM
from laap.cli.config_manager import config_manager
from laap.cli.wizard.startup import show_logo, show_intro, run_wizard, check_config, show_help
from laap.ui import LAAP_TUI




def run_gateway(args):
    """Run the LAAP Gateway server."""
    import asyncio
    from laap.gateway.engine import GatewayEngine
    from laap.gateway.platforms.telegram import TelegramAdapter
    from laap.gateway.platforms.discord import DiscordAdapter
    from laap.gateway.platforms.slack import SlackAdapter
    from laap.gateway.platforms.webhook import WebhookAdapter

    engine = GatewayEngine(agent=None)  # Agent loaded lazily

    # Configure from env / args
    tg_token = args.gateway_token or os.environ.get("TELEGRAM_BOT_TOKEN", "")
    dc_token = args.gateway_token or os.environ.get("DISCORD_BOT_TOKEN", "")
    sl_token = os.environ.get("SLACK_BOT_TOKEN", "")
    wh_port = os.environ.get("WEBHOOK_PORT", "8765")

    if args.gateway_platform in ("telegram", "all") and tg_token:
        engine.register_platform("telegram", TelegramAdapter, {"token": tg_token})
    if args.gateway_platform in ("discord", "all") and dc_token:
        engine.register_platform("discord", DiscordAdapter, {"token": dc_token})
    if args.gateway_platform in ("slack", "all") and sl_token:
        engine.register_platform("slack", SlackAdapter, {"token": sl_token})
    if args.gateway_platform in ("webhook", "all"):
        engine.register_platform("webhook", WebhookAdapter, {"port": wh_port})

    print(f"  {SYM['dragon']} {GOLD_BRIGHT}LAAP Gateway starting...{RESET}")
    print(f"  {GOLD_DIM}Platforms: {args.gateway_platform or 'auto'}{RESET}")

    asyncio.run(engine.start())




def animated_startup(agent=None):
    """Show the Hermes-style welcome banner.

    Renders a centered LAAP-AGENT ASCII logo, then a bordered panel
    containing a small dragon icon (with model/cwd/session) on the
    left and Available Tools / Available Skills / summary on the right.
    A random tip is shown below.
    """
    try:
        from laap.ui.hermes_banner import print_banner
        print_banner()
        return
    except Exception as e:
        logger.debug(f"Hermes banner failed: {e}")

    # Fall back to the old dragon + typewriter animation
    import time, sys
    try:
        from laap.ui.dragon_logo import render_dragon
        dragon_art = render_dragon(width=60, use_color=True)
    except Exception:
        dragon_art = ""
    if not dragon_art or not dragon_art.strip():
        from laap.cli.logo_art import render_dragon as render_logo
        dragon_art = render_logo(use_color=True)
    lines = dragon_art.split("\n")
    sys.stdout.write("\033[?25l")
    try:
        for i in range(len(lines) + 1):
            if i > 0:
                sys.stdout.write(f"\033[{i}A")
            sys.stdout.write("\033[J")
            for line in lines[:i]:
                sys.stdout.write("  " + line + "\n")
            sys.stdout.flush()
            time.sleep(0.04)
        time.sleep(0.4)
        title = "LAAP - Lifeform Autonomous Adaptive Protocol"
        sys.stdout.write("\n")
        for i in range(len(title)):
            sys.stdout.write(f"\r  {GOLD_BRIGHT}{title[:i+1]}{RESET}")
            sys.stdout.flush()
            time.sleep(0.015)
        sys.stdout.write("\n\n")
        sys.stdout.flush()
    finally:
        sys.stdout.write("\033[?25h")
    sys.stdout.write("\n")
    time.sleep(0.2)

def show_golden_dragon():
    """Display golden dragon logo and intro."""
    dragon = show_logo()
    print(f"\n{GOLD_BRIGHT}{BOLD}{dragon}{RESET}")
    print(f"{GOLD_DIM}{show_intro()}{RESET}")
    print(f"  {GOLD}{'='*54}{RESET}\n")


def first_run_experience() -> bool:
    """First-run: show logo, intro, and configuration wizard."""
    show_golden_dragon()

    print(f"  {SYM['dragon']} {GOLD_BRIGHT}Welcome to LAAP!{RESET}")
    print(f"  {GOLD_DIM}This appears to be your first launch.{RESET}")
    print(f"  {GOLD_DIM}Let's get you configured to use the full power of Ao.{RESET}\n")

    print(f"  {GOLD}1{RESET}) Configure now (recommended)")
    print(f"  {GOLD}2{RESET}) Skip — use local-only mode")
    print(f"  {GOLD}3{RESET}) Show quick-start guide\n")

    choice = input(f"  {SYM['dragon']} Choose [1]: ").strip() or "1"

    if choice == "3":
        print(show_help())
        return False
    elif choice == "2":
        print(f"\n  {SYM['warn']} Skipping configuration. Use --config anytime.\n")
        config_manager.config.first_run = False
        config_manager.save()
        return False

    print(f"\n  {GOLD_DIM}Launching configuration wizard...{RESET}\n")
    result = run_wizard()
    config_manager.config.first_run = False
    config_manager.save()
    return bool(result.get("api_key"))


def config_wizard():
    """Run the configuration wizard."""
    print(f"\n  {GOLD}{'='*54}{RESET}")
    print(f"  {GOLD_BRIGHT}{BOLD}LAAP Configuration{RESET}")
    print(f"  {GOLD}{'='*54}{RESET}\n")
    run_wizard()


def check_api_keys() -> Dict[str, str]:
    result = {}
    for pid, p in config_manager.config.providers.items():
        if p.api_key or pid == "ollama":
            result[pid] = p.model or "configured"
    return result


def create_agent(args) -> Agent:
    config_manager.apply_to_environment()
    provider = args.provider or os.environ.get("LAAP_PROVIDER", "openai")
    model = args.model or os.environ.get("LAAP_MODEL", "")
    factory = LLMFactory(default_provider=provider, default_model=model or None)

    # Keep verbose=True for streaming output, but suppress init banner in single-task mode
    show_banner = not (args.quiet or bool(args.task))

    if args.type == "codex":
        config = CodexConfig(name=args.name or "Codex", workspace_dir=args.workspace or os.getcwd(),
                             verbose=True, rsi_enabled=not args.no_rsi)
        return CodexAgent(config=config, llm_factory=factory, show_banner=show_banner)
    elif args.type in ("lifelike", "psi"):
        config = LifelikeConfig(name=args.name or "Ao", verbose=True,
                                rsi_enabled=not args.no_rsi, rsi_interval=args.rsi_interval or 20)
        agent = LifelikeAgent(config=config, llm_factory=factory, show_banner=show_banner)
        if args.task and hasattr(agent, 'awareness') and agent.awareness:
            agent.awareness.set_task(args.task)
        return agent
    else:
        return Agent(config=AgentConfig(name=args.name or "Agent", verbose=True),
                     llm_factory=factory, show_banner=show_banner)


def run_task(agent: Agent, task: str):
    print(f"\n  {SYM['dragon']} {GOLD_BRIGHT}Task{RESET}: {task}")
    print(f"  {GOLD}{'-'*40}{RESET}")
    if not getattr(agent, 'llm', None):
        print(f"  {SYM['warn']} No LLM configured. Use --config to set up.\n")
        return
    # Streaming output is handled by StreamHandler inside agent.chat()
    agent.run(task)
    # Don't print result again — streaming already showed it
    if hasattr(agent, 'complete_status'):
        s = agent.complete_status()
        fv = s.get("fitness", {}).get("fitness", "N/A") if s.get("fitness") else "N/A"
    else:
        fv = "N/A"
    rv = getattr(agent, 'total_reward', 'N/A')
    print(f"\n  {GOLD_DIM}Steps: {agent.step_count} | Fitness: {fv} | Reward: {rv}{RESET}\n")


def main():
    # Handle "laap profile <subcommand>" before argparse
    if len(sys.argv) > 1 and sys.argv[1] == "profile":
        run_profile_command(sys.argv[2:])
        return

    parser = argparse.ArgumentParser(prog="laap",
        description="LAAP - Lifeform Autonomous Adaptive Protocol",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  laap                          TUI mode (default, golden dragon terminal UI)
  laap "analyze this project"   Single task
  laap --interactive            Classic REPL (simple text mode)
  laap --config                 Configuration wizard
  laap --version                Show version
  laap --help                   Show help""")

    parser.add_argument("task", nargs="?", help="Execute single task")
    parser.add_argument("--type", "-t", default="lifelike", choices=["base", "lifelike", "psi", "codex"], help="Agent type")
    parser.add_argument("--name", "-n", default="", help="Agent name")
    parser.add_argument("--model", "-m", default="", help="LLM model")
    parser.add_argument("--provider", "-p", default="", help="LLM provider")
    parser.add_argument("--interactive", "-i", action="store_true", help="Classic REPL mode (instead of TUI)")
    parser.add_argument("--tui", action="store_true", help="Rich TUI mode (default)")
    parser.add_argument("--gateway", action="store_true", help="Run as gateway server")
    parser.add_argument("--gateway-platform", "-gp", default="all",
                        choices=["telegram", "discord", "slack", "webhook", "all"],
                        help="Gateway platform to enable")
    parser.add_argument("--gateway-token", "-gt", default="", help="Bot token for gateway")
    parser.add_argument("--config", action="store_true", help="Configure API keys")
    parser.add_argument("--workspace", "-w", default="", help="Workspace directory")
    parser.add_argument("--no-rsi", action="store_true", help="Disable RSI")
    parser.add_argument("--rsi-interval", type=int, default=20, help="RSI interval")
    parser.add_argument("--quiet", "-q", action="store_true", help="Quiet mode")
    parser.add_argument("--version", action="store_true", help="Show version")
    parser.add_argument("--help-all", action="store_true", help="Show full documentation")
    args = parser.parse_args()

    if args.gateway:
        return run_gateway(args)

    if args.version:
        show_golden_dragon()
        return

    if args.help_all:
        show_golden_dragon()
        print(show_help())
        return

    if args.config:
        config_wizard()
        return

    # Load .env
    env_path = os.path.join(os.path.expanduser("~"), ".laap", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    if not os.environ.get(k):
                        os.environ[k] = v

    # First-run detection
    if config_manager.config.first_run and not args.task and not args.quiet:
        configured = first_run_experience()
    else:
        configured = check_config()

    config_manager.apply_to_environment()
    try:
        agent = create_agent(args)
    except Exception as e:
        print(f"  {SYM['warn']} {GOLD_DIM}Agent init: {e}{RESET}")
        print(f"  {GOLD_DIM}Launching TUI in demo mode...{RESET}")
        agent = None

    if args.task:
        run_task(agent, args.task)
    elif args.interactive:
        repl = LAAP_REPL(agent, args)
        repl.run()
    else:
        # Default: launch Rich TUI with animated startup
        # If stdin/stdout is not a real TTY (captured/redirected/IDE), fall back to REPL
        if not (sys.stdin.isatty() and sys.stdout.isatty()):
            print(f"  {SYM.get('warn', '!')} {GOLD_DIM}Stdout/stdin not a TTY — using REPL mode instead of full-screen TUI.{RESET}")
            repl = LAAP_REPL(agent, args)
            repl.run()
            return
        if not args.quiet:
            animated_startup(agent)
        try:
            tui = LAAP_TUI(agent, config_manager)
            tui.run()
        except Exception as e:
            # TUI failed (e.g. unsupported terminal in IDE) — fall back to REPL
            print(f"\n  {SYM.get('warn', '!')} {GOLD_DIM}TUI unavailable in this terminal: {e}{RESET}")
            print(f"  {GOLD_DIM}Falling back to interactive REPL...{RESET}\n")
            repl = LAAP_REPL(agent, args)
            repl.run()


if __name__ == "__main__":
    main()


# ── Profile Management ─────────────────────────────────────────────────


def run_profile_command(args_list: list) -> None:
    """Handle laap profile <subcommand>.

    Subcommands: list, create, delete, show, export, import, switch.
    """
    from laap.cli.profiles import profile_manager

    if not args_list or args_list[0] in ("--help", "-h"):
        _print_profile_help()
        return

    sub = args_list[0]

    if sub == "list":
        profiles = profile_manager.list()
        if not profiles:
            print(f"  No profiles found.")
            return
        active = profile_manager.get_active()
        print(f"  {'Active':8s} {'Name':20s} {'Size':10s} {'Sessions':10s} {'Skills':10s}")
        print(f"  {'-'*8} {'-'*20} {'-'*10} {'-'*10} {'-'*10}")
        for p in profiles:
            marker = "*" if p["active"] else " "
            name = p["name"]
            size = p.get("size_human", "0 B")
            sessions = str(p.get("session_count", 0))
            skills = str(len(p.get("skills", [])))
            print(f"  {marker:8s} {name:20s} {size:10s} {sessions:10s} {skills:10s}")

    elif sub == "create":
        if len(args_list) < 2:
            print("  Usage: laap profile create <name> [--clone-from <name>]")
            return
        name = args_list[1]
        clone_from = None
        if "--clone-from" in args_list:
            idx = args_list.index("--clone-from")
            if idx + 1 < len(args_list):
                clone_from = args_list[idx + 1]
        result = profile_manager.create(name, clone_from=clone_from)
        _print_profile_result(result)

    elif sub == "delete":
        if len(args_list) < 2:
            print("  Usage: laap profile delete <name>")
            return
        name = args_list[1]
        need_confirm = "--force" not in args_list and "-f" not in args_list
        if need_confirm:
            confirm = input(f"  Delete profile '{name}'? This cannot be undone. [y/N]: ").strip().lower()
            if confirm != "y":
                print("  Deletion cancelled.")
                return
        result = profile_manager.delete(name, force=True)
        _print_profile_result(result)

    elif sub == "show":
        if len(args_list) < 2:
            print("  Usage: laap profile show <name>")
            return
        name = args_list[1]
        result = profile_manager.show(name)
        if result["status"] == "ok":
            p = result["profile"]
            print(f"  Name:       {p['name']}")
            print(f"  Active:     {'yes' if p['active'] else 'no'}")
            print(f"  Path:       {p['path']}")
            print(f"  Size:       {p.get('size_human', 'N/A')}")
            print(f"  Files:      {p.get('files', 0)}")
            print(f"  Sessions:   {p.get('session_count', 0)}")
            print(f"  Skills:     {', '.join(p.get('skills', [])) or '(none)'}")
            print(f"  Created:    {p.get('created', 'N/A')}")
            print(f"  Modified:   {p.get('modified', 'N/A')}")
        else:
            _print_profile_result(result)

    elif sub == "export":
        if len(args_list) < 2:
            print("  Usage: laap profile export <name> [--output <path>]")
            return
        name = args_list[1]
        output_path = None
        if "--output" in args_list:
            idx = args_list.index("--output")
            if idx + 1 < len(args_list):
                output_path = args_list[idx + 1]
        result = profile_manager.export(name, output_path=output_path)
        _print_profile_result(result)

    elif sub == "import":
        if len(args_list) < 2:
            print("  Usage: laap profile import <file.tar.gz>")
            return
        file_path = args_list[1]
        result = profile_manager.import_from(file_path)
        _print_profile_result(result)

    elif sub == "switch":
        if len(args_list) < 2:
            print("  Usage: laap profile switch <name>")
            return
        name = args_list[1]
        result = profile_manager.switch(name)
        _print_profile_result(result)

    else:
        print(f"  Unknown profile subcommand: {sub}")
        _print_profile_help()


def _print_profile_help() -> None:
    """Print profile subcommand help."""
    print("""
  Profile Management Commands:

    laap profile list                  List all profiles
    laap profile create <name>         Create a new profile
      [--clone-from <name>]            Clone from existing profile
    laap profile delete <name>         Delete a profile
      [--force]                        Skip confirmation
    laap profile show <name>           Show profile details
    laap profile export <name>         Export profile to tar.gz
      [--output <path>]                Output file path
    laap profile import <file>         Import profile from tar.gz
    laap profile switch <name>         Switch active profile
""")


def _print_profile_result(result: dict) -> None:
    """Print a profile operation result."""
    status = result.get("status", "error")
    msg = result.get("message", "")
    if status == "ok":
        print(f"  {msg}")
    elif status == "error":
        print(f"  Error: {msg}")
    elif status == "confirm":
        print(f"  {msg}")
