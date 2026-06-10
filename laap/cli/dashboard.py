"""LAAP — System Dashboard (Terminal UI)

参考 Hermes dashboard_auth/ 设计。
终端仪表盘：Agent状态/工具统计/记忆使用/最近对话/系统负载。
自动刷新（每5秒），表格+彩色输出。
"""
from __future__ import annotations

import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from laap.cli.skins.dragon import GOLD, GOLD_BRIGHT, GOLD_DIM, RESET, BOLD, SYM
except ImportError:
    GOLD = GOLD_BRIGHT = GOLD_DIM = RESET = BOLD = ""
    SYM = {"dragon": "?"}

CONFIG_DIR = Path.home() / ".laap"
MEMORY_DIR = CONFIG_DIR / "memory"
LOG_DIR = CONFIG_DIR / "logs"
CONFIG_PATH = CONFIG_DIR / "config.json"


@dataclass
class DashboardData:
    agent_status: str = "stopped"
    uptime_seconds: float = 0.0
    active_sessions: int = 0
    total_memories: int = 0
    memory_backend: str = "json"
    tools_available: int = 0
    tools_enabled: int = 0
    tool_calls_today: int = 0
    total_conversations: int = 0
    total_messages: int = 0
    last_conversation: str = "N/A"
    last_activity: str = "N/A"
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_usage_percent: float = 0.0
    config_model: str = "not set"
    config_provider: str = "not set"
    api_keys_configured: int = 0
    plugin_count: int = 0
    skill_count: int = 0
    errors_last_hour: int = 0
    python_version: str = ""


def _try_get(path: Path, default: Any = 0) -> Any:
    try:
        if path.is_file():
            return path.read_text("utf-8").strip()
        return default
    except (OSError, IOError):
        return default


def _try_json(path: Path, default: Any = None) -> Any:
    try:
        if path.is_file():
            return json.loads(path.read_text("utf-8"))
        return default if default is not None else {}
    except (json.JSONDecodeError, OSError, IOError):
        return default if default is not None else {}


def _count_lines(path: Path) -> int:
    try:
        if not path.is_file():
            return 0
        content = path.read_text("utf-8").strip()
        if not content:
            return 0
        return len([l for l in content.splitlines() if l.strip()])
    except (OSError, IOError):
        return 0


def _get_terminal_size() -> tuple:
    try:
        sz = shutil.get_terminal_size()
        return sz.columns, sz.lines
    except Exception:
        return 80, 24


class DashboardCollector:
    def __init__(self) -> None:
        self._start_time = time.time()
        self._previous_data: Optional[DashboardData] = None

    def collect(self) -> DashboardData:
        d = DashboardData()
        d.python_version = sys.version.split()[0]
        cfg = _try_json(CONFIG_PATH)
        d.config_model = cfg.get("model", "not set")
        d.config_provider = cfg.get("provider", "not set")
        d.api_keys_configured = self._count_api_keys()
        d.tools_enabled = len(cfg.get("tools_enabled", {}))
        d.tools_available = 8
        memory_cfg = cfg.get("memory", {})
        d.memory_backend = memory_cfg.get("backend", "json")
        memory_file = MEMORY_DIR / "memories.json"
        if memory_file.exists():
            memories = _try_json(memory_file, [])
            if isinstance(memories, list):
                d.total_memories = len(memories)
            elif isinstance(memories, dict):
                d.total_memories = len(memories)
        d.total_conversations = _count_lines(LOG_DIR / "conversations.log") if LOG_DIR.exists() else 0
        d.total_messages = _count_lines(LOG_DIR / "messages.log") if LOG_DIR.exists() else 0
        log_file = LOG_DIR / "activity.log"
        if log_file.exists():
            last_line = _try_get(log_file, "")
            if last_line:
                d.last_activity = last_line[:50]
        conv_file = LOG_DIR / "conversations.log"
        if conv_file.exists():
            last = _try_get(conv_file, "")
            if last:
                d.last_conversation = last[:60]
        d.uptime_seconds = time.time() - self._start_time
        d.agent_status = "running" if d.uptime_seconds > 0 else "stopped"
        try:
            import psutil
            d.cpu_percent = psutil.cpu_percent(interval=0.1)
            d.memory_percent = psutil.virtual_memory().percent
            d.disk_usage_percent = psutil.disk_usage("/").percent
        except ImportError:
            pass
        plugin_dir = Path.cwd() / "plugins"
        d.plugin_count = len([p for p in plugin_dir.iterdir() if p.is_dir()]) if plugin_dir.exists() else 0
        skill_dir = CONFIG_DIR / "skills"
        d.skill_count = len([p for p in skill_dir.iterdir() if p.is_dir()]) if skill_dir.exists() else 0
        self._previous_data = d
        return d

    def _count_api_keys(self) -> int:
        count = 0
        env_keys = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "DEEPSEEK_API_KEY",
                     "GEMINI_API_KEY", "GROQ_API_KEY", "COHERE_API_KEY"]
        for k in env_keys:
            if os.environ.get(k):
                count += 1
        env_file = CONFIG_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text("utf-8").splitlines():
                line = line.strip()
                if line and "=" in line and not line.startswith("#"):
                    key, val = line.split("=", 1)
                    if val.strip():
                        count += 1
        return count


class Dashboard:
    def __init__(self, refresh_interval: int = 5) -> None:
        self.refresh_interval = max(1, refresh_interval)
        self.collector = DashboardCollector()
        self._running = False

    def _render_header(self, cols: int) -> str:
        lines = []
        lines.append(f"{BOLD}{GOLD_BRIGHT}{'=' * cols}{RESET}")
        title = f"  {SYM['dragon']}  LAAP SYSTEM DASHBOARD  {SYM['dragon']}  "
        padded = title.center(cols)
        lines.append(f"{BOLD}{GOLD_BRIGHT}{padded}{RESET}")
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        lines.append(f"{GOLD_DIM}{'-' * cols}{RESET}")
        lines.append(f"  {GOLD}Time:{RESET} {now}  |  {GOLD}Refresh:{RESET} every {self.refresh_interval}s  |  {GOLD}Ctrl+C{RESET} to exit")
        lines.append(f"{GOLD_DIM}{'-' * cols}{RESET}")
        return "\n".join(lines)

    def _render_agent_status(self, d: DashboardData, cols: int) -> str:
        lines = []
        lines.append(f"\n  {BOLD}{GOLD}AGENT STATUS{RESET}")
        lines.append(f"  {GOLD_DIM}{'-' * (cols - 4)}{RESET}")
        status_color = GOLD_BRIGHT if d.agent_status == "running" else GOLD_DIM
        lines.append(f"    {GOLD}Status:    {RESET}{status_color}{d.agent_status.upper()}{RESET}")
        uptime_str = f"{d.uptime_seconds / 60:.1f}m" if d.uptime_seconds < 3600 else f"{d.uptime_seconds / 3600:.1f}h"
        lines.append(f"    {GOLD}Uptime:    {RESET}{uptime_str}")
        lines.append(f"    {GOLD}Sessions:  {RESET}{d.active_sessions}")
        lines.append(f"    {GOLD}Model:     {RESET}{d.config_model}  ({GOLD_DIM}{d.config_provider}{RESET})")
        lines.append(f"    {GOLD}API Keys:  {RESET}{d.api_keys_configured} configured")
        return "\n".join(lines)

    def _render_tools(self, d: DashboardData, cols: int) -> str:
        lines = []
        lines.append(f"\n  {BOLD}{GOLD}TOOLS{RESET}")
        lines.append(f"  {GOLD_DIM}{'-' * (cols - 4)}{RESET}")
        bar_width = cols - 20
        pct = (d.tools_enabled / max(d.tools_available, 1)) * 100
        filled = int(bar_width * pct / 100)
        bar = f"{GOLD}{'#' * filled}{GOLD_DIM}{'.' * (bar_width - filled)}{RESET}"
        lines.append(f"    {GOLD}Enabled:   {RESET}{bar}  {d.tools_enabled}/{d.tools_available}")
        lines.append(f"    {GOLD}Calls:     {RESET}{d.tool_calls_today} today")
        lines.append(f"    {GOLD}Plugins:   {RESET}{d.plugin_count}")
        lines.append(f"    {GOLD}Skills:    {RESET}{d.skill_count}")
        return "\n".join(lines)

    def _render_memory(self, d: DashboardData, cols: int) -> str:
        lines = []
        lines.append(f"\n  {BOLD}{GOLD}MEMORY{RESET}")
        lines.append(f"  {GOLD_DIM}{'-' * (cols - 4)}{RESET}")
        lines.append(f"    {GOLD}Backend:   {RESET}{d.memory_backend}")
        lines.append(f"    {GOLD}Memories:  {RESET}{d.total_memories}")
        lines.append(f"    {GOLD}Convs:     {RESET}{d.total_conversations}")
        lines.append(f"    {GOLD}Messages:  {RESET}{d.total_messages}")
        return "\n".join(lines)

    def _render_activity(self, d: DashboardData, cols: int) -> str:
        lines = []
        lines.append(f"\n  {BOLD}{GOLD}RECENT ACTIVITY{RESET}")
        lines.append(f"  {GOLD_DIM}{'-' * (cols - 4)}{RESET}")
        lines.append(f"    {GOLD}Last:      {RESET}{d.last_activity[:cols - 20]}")
        lines.append(f"    {GOLD}Conv:      {RESET}{d.last_conversation[:cols - 20]}")
        return "\n".join(lines)

    def _render_system(self, d: DashboardData, cols: int) -> str:
        lines = []
        lines.append(f"\n  {BOLD}{GOLD}SYSTEM{RESET}")
        lines.append(f"  {GOLD_DIM}{'-' * (cols - 4)}{RESET}")
        lines.append(f"    {GOLD}Python:    {RESET}{d.python_version}")
        if d.cpu_percent > 0:
            bar_width = cols - 22
            cpu_filled = int(bar_width * d.cpu_percent / 100)
            cpu_bar = f"{GOLD}{'#' * cpu_filled}{GOLD_DIM}{'.' * (bar_width - cpu_filled)}{RESET}"
            lines.append(f"    {GOLD}CPU:       {RESET}{cpu_bar}  {d.cpu_percent:.1f}%")
            mem_filled = int(bar_width * d.memory_percent / 100)
            mem_bar = f"{GOLD}{'#' * mem_filled}{GOLD_DIM}{'.' * (bar_width - mem_filled)}{RESET}"
            lines.append(f"    {GOLD}Memory:    {RESET}{mem_bar}  {d.memory_percent:.1f}%")
            disk_filled = int(bar_width * d.disk_usage_percent / 100)
            disk_bar = f"{GOLD}{'#' * disk_filled}{GOLD_DIM}{'.' * (bar_width - disk_filled)}{RESET}"
            lines.append(f"    {GOLD}Disk:      {RESET}{disk_bar}  {d.disk_usage_percent:.1f}%")
        else:
            lines.append(f"    {GOLD_DIM}CPU/Memory/Disk: install 'psutil' for metrics{RESET}")
        return "\n".join(lines)

    def render(self, data: Optional[DashboardData] = None) -> str:
        if data is None:
            data = self.collector.collect()
        cols, _ = _get_terminal_size()
        cols = max(60, min(cols, 120))
        sections = [
            self._render_header(cols),
            self._render_agent_status(data, cols),
            self._render_tools(data, cols),
            self._render_memory(data, cols),
            self._render_activity(data, cols),
            self._render_system(data, cols),
            f"\n{BOLD}{GOLD_BRIGHT}{'=' * cols}{RESET}",
        ]
        return "\n".join(sections)

    def run(self) -> None:
        self._running = True
        try:
            while self._running:
                data = self.collector.collect()
                os.system("cls" if os.name == "nt" else "clear")
                print(self.render(data))
                time.sleep(self.refresh_interval)
        except KeyboardInterrupt:
            self._running = False
            print(f"\n  {GOLD_DIM}Dashboard closed.{RESET}")

    def snapshot(self, as_json: bool = False) -> str:
        data = self.collector.collect()
        if as_json:
            return json.dumps({
                "agent_status": data.agent_status,
                "uptime_seconds": data.uptime_seconds,
                "total_memories": data.total_memories,
                "tools_enabled": data.tools_enabled,
                "cpu_percent": data.cpu_percent,
                "memory_percent": data.memory_percent,
                "disk_usage_percent": data.disk_usage_percent,
                "model": data.config_model,
                "api_keys": data.api_keys_configured,
                "total_conversations": data.total_conversations,
                "total_messages": data.total_messages,
                "errors_last_hour": data.errors_last_hour,
            }, indent=2)
        return self.render(data)


def run_dashboard(refresh: int = 5) -> None:
    d = Dashboard(refresh_interval=refresh)
    d.run()


def show_snapshot(json_output: bool = False) -> str:
    d = Dashboard()
    return d.snapshot(as_json=json_output)


if __name__ == "__main__":
    run_dashboard()
