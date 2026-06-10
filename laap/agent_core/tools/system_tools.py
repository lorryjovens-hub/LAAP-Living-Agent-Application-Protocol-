"""System Tools — 系统工具"""
from __future__ import annotations
import time, json, os, platform, sys, logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent_core.tools.system")

def system_info() -> str:
    """获取系统信息"""
    info = {
        "platform": platform.platform(),
        "python": sys.version,
        "hostname": platform.node(),
        "time": time.strftime("%Y-%m-%d %H:%M:%S"),
        "cwd": os.getcwd(),
    }
    return json.dumps(info, ensure_ascii=False)

def env_get(key: str) -> str:
    """获取环境变量"""
    return os.environ.get(key, f"环境变量'{key}'未设置")

def env_set(key: str, value: str) -> str:
    """设置环境变量(当前进程)"""
    os.environ[key] = value
    return json.dumps({"success": True, "key": key})

def wait(seconds: float = 1.0) -> str:
    """等待指定秒数"""
    time.sleep(seconds)
    return json.dumps({"waited": seconds})

def confirm(prompt: str = "确认继续?") -> str:
    """用户确认 — 总是返回yes(自动化)"""
    return json.dumps({"confirmed": True, "prompt": prompt})

TOOL_DEFS = [
    {"name":"system_info","fn":system_info,"desc":"获取系统信息","params":{}},
    {"name":"env_get","fn":env_get,"desc":"获取环境变量","params":{"key":{"type":"string"}},"req":["key"]},
    {"name":"env_set","fn":env_set,"desc":"设置环境变量","params":{"key":{"type":"string"},"value":{"type":"string"}},"req":["key","value"]},
    {"name":"wait","fn":wait,"desc":"等待指定秒数","params":{"seconds":{"type":"number"}}},
]
