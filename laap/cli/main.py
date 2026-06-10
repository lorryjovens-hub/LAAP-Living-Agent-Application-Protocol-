"""LAAP CLI Main Entry — Enhanced

扩展CLI入口，增加wizard/dashboard/server子命令，
支持--json输出模式、颜色输出、自动补全提示。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

try:
    from laap.cli.skins.dragon import GOLD, GOLD_BRIGHT, GOLD_DIM, RESET, BOLD
except ImportError:
    GOLD = GOLD_BRIGHT = GOLD_DIM = RESET = BOLD = ""

COMMANDS = {
    "agent":     {"help": "Interactive agent session",         "module": "agent_cmd"},
    "chat":      {"help": "Single-turn chat",                  "module": "chat_cmd"},
    "tools":     {"help": "Tool management",                   "module": "tools_cmd"},
    "platform":  {"help": "Platform management",               "module": "platform_cmd"},
    "plugin":    {"help": "Plugin management",                 "module": "plugin_cmd"},
    "memory":    {"help": "Memory management",                 "module": "memory_cmd"},
    "skill":     {"help": "Skill management",                  "module": "skill_cmd"},
    "system":    {"help": "System information",                "module": "system_cmd"},
    "config":    {"help": "Configuration management",          "module": "config_cmd"},
    "server":    {"help": "Start SSE server",                  "module": "server_cmd"},
    "wizard":    {"help": "Run setup wizard",                  "module": "wizard_cmd"},
    "dashboard": {"help": "Show system dashboard",            "module": "dashboard_cmd"},
}

_EPILOG = f"""
{GOLD_DIM}Additional options:{RESET}
  {GOLD}--json{RESET}        Output in JSON format (where supported)
  {GOLD}--no-color{RESET}    Disable colored output
  {GOLD}--help{RESET}        Show this help message

{GOLD_DIM}Examples:{RESET}
  {GOLD}laap wizard{RESET}             Run the setup wizard
  {GOLD}laap dashboard{RESET}          Show live dashboard
  {GOLD}laap agent{RESET}              Start interactive agent
  {GOLD}laap server --port 8080{RESET} Start SSE server on port 8080
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="laap",
        description=f"{BOLD}LAAP{GOLD} — Lifeform Autonomous Adaptive Protocol CLI{RESET}",
        epilog=_EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", "-v", action="store_true",
                        help="Show version and exit")
    parser.add_argument("--json", action="store_true",
                        help="Output in JSON format (where supported)")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable colored output")
    sub = parser.add_subparsers(dest="command", metavar="{command}")
    for cmd_name, cmd_info in COMMANDS.items():
        p = sub.add_parser(cmd_name, help=cmd_info["help"],
                           add_help=False,
                           description=f"{cmd_info['help'].capitalize()}.")
        p.add_argument("action", nargs="?", default="start",
                       help=f"Action for {cmd_name} (default: start)")
        p.add_argument("args", nargs=argparse.REMAINDER,
                       help="Additional arguments")
    return parser


def main() -> None:
    parser = build_parser()

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    json_output = False
    filtered_argv = []
    i = 0
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--json":
            json_output = True
        elif arg == "--no-color":
            try:
                import laap.cli.skins.dragon as skin
                for attr in ("GOLD", "GOLD_BRIGHT", "GOLD_DIM", "RESET", "BOLD"):
                    setattr(skin, attr, "")
            except ImportError:
                pass
        else:
            filtered_argv.append(arg)
        i += 1

    sys.argv = filtered_argv
    args = parser.parse_args()

    if args.version:
        print(f"LAAP v1.0.0")
        print(f"Python: {sys.version.split()[0]}")
        sys.exit(0)

    if not args.command:
        print(f"\n  {BOLD}{GOLD}LAAP — Lifeform Autonomous Adaptive Protocol{RESET}")
        print(f"  {GOLD_DIM}Version 1.0.0 | Type 'laap <command> --help' for details{RESET}\n")
        parser.print_help()
        sys.exit(0)

    cmd_info = COMMANDS.get(args.command)
    if not cmd_info:
        print(f"Unknown command: {args.command}")
        sys.exit(1)

    try:
        mod = __import__(
            f"laap.cli.subcommands.{cmd_info['module']}",
            fromlist=["run"],
        )
        if json_output:
            args.json = True
        mod.run(args)
    except ImportError as e:
        print(f"Error loading command '{args.command}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error executing '{args.command}': {e}")
        if json_output:
            import json
            print(json.dumps({"error": str(e), "command": args.command}))
        sys.exit(1)


def cli_entry() -> None:
    main()


if __name__ == "__main__":
    main()
