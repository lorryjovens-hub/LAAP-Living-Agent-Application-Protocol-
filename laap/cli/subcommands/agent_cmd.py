"""Agent interactive mode — Enhanced

支持流式/非流式模式，--model/--provider参数，
实时token使用显示，历史记录。
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

try:
    from laap.cli.skins.dragon import GOLD, GOLD_BRIGHT, GOLD_DIM, RESET, BOLD, SYM
except ImportError:
    GOLD = GOLD_BRIGHT = GOLD_DIM = RESET = BOLD = ""
    SYM = {"dragon": "?"}

HISTORY_DIR = Path.home() / ".laap" / "history"
HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _load_history() -> list:
    path = HISTORY_DIR / "agent_history.json"
    if path.exists():
        try:
            return json.loads(path.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return []


def _save_history(msg: str, response: str, model: str, usage: Dict[str, int]) -> None:
    history = _load_history()
    history.append({
        "timestamp": datetime.now().isoformat(),
        "message": msg,
        "response": response[:200],
        "model": model,
        "usage": usage,
    })
    if len(history) > 500:
        history = history[-500:]
    try:
        (HISTORY_DIR / "agent_history.json").write_text(
            json.dumps(history, indent=2, ensure_ascii=False), "utf-8"
        )
    except OSError:
        pass


def _get_model_from_config() -> Dict[str, str]:
    cfg_path = Path.home() / ".laap" / "config.json"
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text("utf-8"))
            return {
                "model": cfg.get("model", "gpt-4o"),
                "provider": cfg.get("provider", "OpenAI"),
            }
        except (json.JSONDecodeError, OSError):
            pass
    return {"model": "gpt-4o", "provider": "OpenAI"}


def _fmt_usage(usage: Dict[str, int]) -> str:
    parts = []
    if "prompt_tokens" in usage:
        parts.append(f"{GOLD_DIM}prompt{RESET}:{usage.get('prompt_tokens', 0)}")
    if "completion_tokens" in usage:
        parts.append(f"{GOLD_DIM}completion{RESET}:{usage.get('completion_tokens', 0)}")
    if "total_tokens" in usage:
        parts.append(f"{GOLD}total{RESET}:{usage.get('total_tokens', 0)}")
    return " | ".join(parts) if parts else ""


def run(args: Any) -> None:
    from laap.agent_core.agent import Agent, AgentConfig

    cfg = _get_model_from_config()
    model = getattr(args, "model", None) or cfg["model"]
    provider = getattr(args, "provider", None) or cfg["provider"]
    stream = not getattr(args, "no_stream", False)
    json_output = getattr(args, "json", False)

    config = AgentConfig(
        name="LAAP-CLI",
        model=model,
        provider=provider,
        enable_tools=not getattr(args, "no_tools", False),
    )
    agent = Agent(config)

    print(f"\n  {GOLD_BRIGHT}{SYM['dragon']} LAAP Agent — {model} ({provider}){RESET}")
    print(f"  {GOLD_DIM}Commands: /exit, /help, /history, /clear, /model <name>{RESET}")
    print(f"  {GOLD_DIM}Streaming: {'ON' if stream else 'OFF'}{RESET}")
    print()

    history = _load_history()
    session_usage: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}

    try:
        while True:
            try:
                msg = input(f"  {GOLD}You:{RESET} ")
            except EOFError:
                print()
                break

            msg = msg.strip()
            if not msg:
                continue

            if msg.lower() == "/exit":
                break
            elif msg.lower() == "/help":
                print(f"\n  {GOLD}Commands:{RESET}")
                print(f"    {GOLD}/exit{RESET}     Exit")
                print(f"    {GOLD}/help{RESET}     Show this help")
                print(f"    {GOLD}/history{RESET}  Show recent history")
                print(f"    {GOLD}/clear{RESET}    Clear screen")
                print(f"    {GOLD}/model{RESET}    Show current model")
                print(f"    {GOLD}/usage{RESET}    Show token usage")
                print()
                continue
            elif msg.lower() == "/history":
                hist = _load_history()
                if hist:
                    print(f"\n  {GOLD}Recent conversations:{RESET}")
                    for h in hist[-5:]:
                        print(f"    {GOLD_DIM}{h['timestamp'][:19]}{RESET} "
                              f"{h['message'][:50]} -> {h['response'][:50]}...")
                else:
                    print(f"\n  {GOLD_DIM}No history yet.{RESET}")
                print()
                continue
            elif msg.lower() == "/clear":
                os.system("cls" if os.name == "nt" else "clear")
                continue
            elif msg.lower() == "/model":
                print(f"\n  {GOLD}Current model:{RESET} {model}  ({provider})")
                print()
                continue
            elif msg.lower() == "/usage":
                print(f"\n  {GOLD}Session token usage:{RESET}")
                print(f"    {GOLD_DIM}Prompt:{RESET} {session_usage.get('prompt_tokens', 0)}")
                print(f"    {GOLD_DIM}Completion:{RESET} {session_usage.get('completion_tokens', 0)}")
                print(f"    {GOLD}Total:{RESET} {session_usage.get('total_tokens', 0)}")
                print()
                continue
            elif msg.lower().startswith("/model "):
                model = msg.split(" ", 1)[1].strip()
                config.model = model
                agent = Agent(config)
                print(f"\n  {GOLD}Switched to model:{RESET} {model}")
                print()
                continue

            print(f"  {GOLD_BRIGHT}LAAP:{RESET}", end=" ", flush=True)

            start_time = time.time()
            try:
                if stream:
                    response = ""
                    for chunk in agent.chat_stream(msg):
                        response += chunk
                        sys.stdout.write(chunk)
                        sys.stdout.flush()
                    usage = getattr(agent, "last_usage", {})
                else:
                    response = agent.chat(msg)
                    usage = getattr(agent, "last_usage", {})
                    print(f"{response}", end="")

                elapsed = time.time() - start_time
                for k in usage:
                    session_usage[k] = session_usage.get(k, 0) + usage.get(k, 0)

                usage_str = _fmt_usage(usage)
                if usage_str:
                    print(f"\n  {GOLD_DIM}[{usage_str} | {elapsed:.1f}s]{RESET}")
                else:
                    print(f"\n  {GOLD_DIM}[{elapsed:.1f}s]{RESET}")

                _save_history(msg, response, model, usage)

            except Exception as e:
                print(f"\n  {GOLD_DIM}Error: {e}{RESET}")

    except KeyboardInterrupt:
        print(f"\n  {GOLD_DIM}Session ended.{RESET}")

    total = session_usage.get("total_tokens", 0)
    if total > 0:
        print(f"\n  {GOLD_DIM}Session total: {total} tokens{RESET}")
    print(f"  {GOLD_BRIGHT}Bye!{RESET}")
