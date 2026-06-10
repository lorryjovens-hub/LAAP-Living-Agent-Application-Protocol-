"""LAAP — Interactive Configuration Wizard (Enhanced)

参考 Hermes wizard/startup.py 设计。
提供完整交互式配置向导：API Key配置→模型选择→工具启用→记忆设置→完成。
自动保存配置到 ~/.laap/config.json。
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from laap.cli.skins.dragon import GOLD, GOLD_BRIGHT, GOLD_DIM, RESET, BOLD, SYM
except ImportError:
    GOLD = GOLD_BRIGHT = GOLD_DIM = RESET = BOLD = ""
    SYM = {"dragon": "?"}

CONFIG_DIR = Path.home() / ".laap"
CONFIG_PATH = CONFIG_DIR / "config.json"
ENV_PATH = CONFIG_DIR / ".env"


def cprint(text: str, color: str = GOLD, bold: bool = False, end: str = "\n") -> None:
    prefix = BOLD if bold else ""
    sys.stdout.write(f"{prefix}{color}{text}{RESET}{end}")
    sys.stdout.flush()


def prompt(text: str, default: str = "", secret: bool = False) -> str:
    if secret:
        val = input(f"  {GOLD}{text}{RESET} ")
    else:
        val = input(f"  {GOLD}{text}{RESET} ") or default
    return val.strip()


def show_title(text: str) -> None:
    print()
    cprint(f"  ╔══ {'═' * (len(text) + 2)} ╗", bold=True)
    cprint(f"  ║   {text}   ║", bold=True)
    cprint(f"  ╚══ {'═' * (len(text) + 2)} ╝", bold=True)
    print()


def load_config() -> Dict[str, Any]:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text("utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    return {}


def save_config(cfg: Dict[str, Any]) -> bool:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), "utf-8")
        return True
    except OSError:
        return False


def save_env(key: str, value: str) -> bool:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        with open(str(ENV_PATH), "a") as f:
            f.write(f"{key}={value}\n")
        return True
    except OSError:
        return False


def load_env() -> Dict[str, str]:
    env = {}
    if ENV_PATH.exists():
        for line in ENV_PATH.read_text("utf-8").strip().splitlines():
            line = line.strip()
            if line and "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


PROVIDERS: Dict[str, Tuple[str, str, str]] = {
    "1": ("OpenAI", "OPENAI_API_KEY", "sk-..."),
    "2": ("Anthropic Claude", "ANTHROPIC_API_KEY", "sk-ant-..."),
    "3": ("DeepSeek", "DEEPSEEK_API_KEY", "sk-..."),
    "4": ("Google Gemini", "GEMINI_API_KEY", "AIza..."),
    "5": ("Ollama (Local)", "OLLAMA_BASE_URL", "http://localhost:11434"),
}

MODELS: Dict[str, List[str]] = {
    "OpenAI": ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"],
    "Anthropic Claude": ["claude-sonnet-4-20250514", "claude-3-5-sonnet-20241022", "claude-3-5-haiku-20241022"],
    "DeepSeek": ["deepseek-chat", "deepseek-reasoner"],
    "Google Gemini": ["gemini-2.0-flash", "gemini-2.0-pro"],
    "Ollama (Local)": ["llama3", "mistral", "qwen2.5"],
}


def step_welcome() -> bool:
    print()
    cprint(f"  {SYM['dragon']}  WELCOME TO LAAP — Lifeform Autonomous Adaptive Protocol", bold=True)
    print()
    print(f"  {GOLD_DIM}This wizard will help you configure LAAP for first use.{RESET}")
    print(f"  {GOLD_DIM}You can re-run this at any time with:{RESET} {GOLD}laap wizard{RESET}")
    print()
    ans = input(f"  {GOLD}Continue? [Y/n]: {RESET}").strip().lower()
    return ans not in ("n", "no")


def step_api_key() -> Dict[str, str]:
    show_title("Step 1: API Key Configuration")
    print(f"  {GOLD_DIM}Select an LLM provider to configure:{RESET}")
    print()
    for k, (name, _, example) in PROVIDERS.items():
        print(f"    {GOLD}{k}{RESET}) {GOLD_BRIGHT}{name}{RESET}  ({GOLD_DIM}{example}{RESET})")
    print(f"    {GOLD}s{RESET})  {GOLD_DIM}Skip (configure later){RESET}")
    print()
    choice = prompt("Choice [1]:", default="1").lower()
    if choice == "s":
        return {}
    if choice in PROVIDERS:
        name, env_key, example = PROVIDERS[choice]
        print(f"\n  {GOLD_DIM}Enter your {GOLD_BRIGHT}{name}{GOLD_DIM} API key:{RESET}")
        print(f"  {GOLD_DIM}(e.g., {example}){RESET}")
        key = prompt("API Key:", secret=True)
        if key:
            if len(key) < 8:
                print(f"\n  {GOLD_DIM} Warning: That doesn't look like a valid key.{RESET}")
            else:
                print(f"\n  {GOLD} Key saved!{RESET}")
            os.environ[env_key] = key
            save_env(env_key, key)
            return {env_key: key, "provider": name}
    print(f"  {GOLD_DIM}Skipping API key setup.{RESET}")
    return {}


def step_model_selection(provider: str = "") -> Dict[str, str]:
    show_title("Step 2: Model Selection")
    print(f"  {GOLD_DIM}Choose your default model:{RESET}\n")
    avail_models = ["gpt-4o", "claude-sonnet-4-20250514", "deepseek-chat"]
    if provider and provider in MODELS:
        avail_models = MODELS[provider]
    elif not provider:
        avail_models = []
        for mlist in MODELS.values():
            avail_models.extend(mlist[:1])
    for i, m in enumerate(avail_models[:8], 1):
        print(f"    {GOLD}{i}{RESET}) {GOLD_BRIGHT}{m}{RESET}")
    print(f"    {GOLD}c{RESET}) {GOLD_DIM}Custom model name{RESET}")
    print()
    choice = prompt(f"Choice [1]:", default="1")
    if choice.lower() == "c":
        model = prompt("Enter model name:")
        return {"model": model} if model else {"model": avail_models[0] if avail_models else "gpt-4o"}
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(avail_models):
            return {"model": avail_models[idx]}
    except ValueError:
        pass
    return {"model": avail_models[0] if avail_models else "gpt-4o"}


def step_tools() -> Dict[str, bool]:
    show_title("Step 3: Tool Configuration")
    print(f"  {GOLD_DIM}LAAP can use tools to extend its capabilities.{RESET}\n")
    tools = {
        "web_search": "Web Search",
        "code_exec": "Code Execution",
        "file_ops": "File Operations",
        "memory": "Memory System",
        "web_browser": "Web Browser",
        "image_gen": "Image Generation",
    }
    enabled = {}
    for key, desc in tools.items():
        ans = prompt(f"Enable {GOLD_BRIGHT}{desc}{RESET}? [Y/n]:", default="y").lower()
        enabled[key] = ans not in ("n", "no")
    return {"tools_enabled": enabled}


def step_memory() -> Dict[str, Any]:
    show_title("Step 4: Memory Configuration")
    print(f"  {GOLD_DIM}Configure how LAAP remembers conversations.{RESET}\n")
    memory_backend = prompt("Memory backend [json/local/sqlite]:", default="json").strip().lower()
    if memory_backend not in ("json", "local", "sqlite"):
        memory_backend = "json"
    max_memories = prompt("Max memories to retain [1000]:", default="1000")
    try:
        max_memories = int(max_memories)
    except ValueError:
        max_memories = 1000
    auto_summarize = prompt("Auto-summarize conversations? [Y/n]:", default="y").lower() not in ("n", "no")
    return {
        "memory": {
            "backend": memory_backend,
            "max_memories": max_memories,
            "auto_summarize": auto_summarize,
        }
    }


def step_complete(cfg: Dict[str, Any]) -> None:
    show_title("Configuration Complete!")
    print(f"  {GOLD_BRIGHT}Here's a summary of your configuration:{RESET}\n")
    api_keys = [k for k in cfg if k.endswith("_API_KEY") or k.endswith("_BASE_URL")]
    if api_keys:
        print(f"    {GOLD} {RESET} {GOLD_BRIGHT}API Keys:{RESET} {len(api_keys)} configured")
    else:
        print(f"    {GOLD_DIM}o{RESET} {GOLD_DIM}API Keys: None configured (use 'laap config' later){RESET}")
    if "model" in cfg:
        print(f"    {GOLD} {RESET} {GOLD_BRIGHT}Model:{RESET} {cfg['model']}")
    tools = cfg.get("tools_enabled", {})
    if tools:
        enabled_count = sum(1 for v in tools.values() if v)
        print(f"    {GOLD} {RESET} {GOLD_BRIGHT}Tools:{RESET} {enabled_count}/{len(tools)} enabled")
    mem = cfg.get("memory", {})
    if mem:
        print(f"    {GOLD} {RESET} {GOLD_BRIGHT}Memory:{RESET} backend={mem.get('backend','json')}, max={mem.get('max_memories',1000)}")
    print()
    if save_config(cfg):
        print(f"  {GOLD} Configuration saved to {CONFIG_PATH}{RESET}")
    else:
        print(f"  {GOLD_DIM} Failed to save configuration!{RESET}")
    print(f"\n  {GOLD_BRIGHT}You're all set! Run 'laap agent' to start chatting.{RESET}")
    print()


class Wizard:
    """Interactive configuration wizard for LAAP."""

    def __init__(self) -> None:
        self.config: Dict[str, Any] = load_config()
        self._env: Dict[str, str] = load_env()

    def run(self) -> bool:
        if not step_welcome():
            print(f"\n  {GOLD_DIM}Wizard cancelled.{RESET}")
            return False
        api_result = step_api_key()
        provider = api_result.get("provider", "")
        if api_result:
            self.config.update(api_result)
        model_result = step_model_selection(provider)
        self.config.update(model_result)
        tools_result = step_tools()
        self.config.update(tools_result)
        memory_result = step_memory()
        self.config.update(memory_result)
        step_complete(self.config)
        return True

    def quick_configure(self, api_key: str = "", provider: str = "OpenAI",
                        model: str = "gpt-4o", **kwargs: Any) -> bool:
        if api_key:
            for pname, env_key, _ in PROVIDERS.values():
                if pname.lower() == provider.lower():
                    self.config[env_key] = api_key
                    save_env(env_key, api_key)
                    break
        self.config["model"] = model
        if kwargs:
            self.config.update(kwargs)
        return save_config(self.config)

    def status(self) -> Dict[str, Any]:
        cfg = load_config()
        env = load_env()
        return {
            "configured": bool(cfg or env),
            "api_keys": sum(1 for k in env if k.endswith("_API_KEY")),
            "model": cfg.get("model", "not set"),
            "tools": cfg.get("tools_enabled", {}),
            "memory": cfg.get("memory", {}),
        }


def run_wizard() -> bool:
    w = Wizard()
    return w.run()


def quick_setup(provider: str = "OpenAI", model: str = "gpt-4o") -> bool:
    w = Wizard()
    return w.quick_configure(provider=provider, model=model)


if __name__ == "__main__":
    run_wizard()
