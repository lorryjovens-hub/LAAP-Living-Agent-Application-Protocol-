"""LAAP — First-Run Onboarding Wizard"""
from __future__ import annotations
import os, sys, time

from laap.cli.skins import GOLD, GOLD_BRIGHT, GOLD_DIM, RESET, BOLD, SYM

def show_logo() -> str:
    return r"""                                 _____
      /\                  / ____|
     /  \   ___ ___  ___ | |  __  __ _ _ __ ___   ___
    / /\ \ / __/ __|/ _ \| | |_ |/ _` | '_ ` _ \ / _ \
   / ____ \\__ \__ \ (_) | |__| | (_| | | | | | |  __/
  /_/    \_\___/___/\___/ \_____|\__,_|_| |_| |_|\___|
    """

def show_intro() -> str:
    return "Lifeform Autonomous Adaptive Protocol — 自进化引擎意识生命体"

def show_help() -> str:
    return f"""
  {GOLD_BRIGHT}Commands:{RESET}
    {GOLD}/help{RESET}     — Show help
    {GOLD}/exit{RESET}     — Exit
    {GOLD}/status{RESET}   — Agent status
    {GOLD}/new{RESET}      — New session
    {GOLD}/memory{RESET}   — Memory tools
    {GOLD}/model{RESET}    — Switch model
    {GOLD}/config{RESET}   — Configuration
    """

def check_config() -> bool:
    """Check if API keys are configured."""
    providers = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY"]
    found = [k for k in providers if os.environ.get(k)]
    return len(found) > 0

def run_wizard() -> bool:
    """Interactive setup wizard for first run."""
    print(f"\n  {GOLD_BRIGHT}{SYM['dragon']} Welcome to LAAP! Let's get you set up.{RESET}\n")
    
    providers = {
        "1": ("OpenAI", "OPENAI_API_KEY"),
        "2": ("Anthropic Claude", "ANTHROPIC_API_KEY"),
        "3": ("DeepSeek", "DEEPSEEK_API_KEY"), 
        "4": ("Google Gemini", "GEMINI_API_KEY"),
    }
    
    print(f"  {GOLD}Select your LLM provider:{RESET}")
    for k, (name, _) in providers.items():
        print(f"    {GOLD}{k}{RESET}) {name}")
    
    choice = input(f"\n  {GOLD}Choice [1]: {RESET}").strip() or "1"
    
    if choice in providers:
        name, env_key = providers[choice]
        print(f"\n  {GOLD_DIM}Enter your {name} API key:{RESET}")
        key = input(f"  {GOLD}>{RESET} ").strip()
        if key:
            os.environ[env_key] = key
            # Save to .env
            env_path = os.path.expanduser("~/.laap/.env")
            os.makedirs(os.path.dirname(env_path), exist_ok=True)
            with open(env_path, "a") as f:
                f.write(f"{env_key}={key}\n")
            print(f"  {GOLD}✅ API key saved!{RESET}")
            return True
    
    print(f"  {GOLD_DIM}You can always configure later with --config{RESET}")
    return False

def config_wizard():
    """Configuration wizard (separate entry point)."""
    print(f"\n  {GOLD_BRIGHT}LAAP Configuration Wizard{RESET}")
    run_wizard()