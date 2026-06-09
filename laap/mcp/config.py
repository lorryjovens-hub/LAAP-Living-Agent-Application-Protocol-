"""LAAP MCP — Configuration

Persistent MCP server configuration management.
"""

from __future__ import annotations
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from laap.mcp.lifecycle import MCPServerConfig

logger = logging.getLogger("laap.mcp.config")

CONFIG_DIR = Path.home() / ".laap" / "mcp"
CONFIG_FILE = CONFIG_DIR / "servers.json"


def _ensure_dir():
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_config() -> Dict[str, dict]:
    """Load MCP server configurations from disk."""
    _ensure_dir()
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        logger.warning(f"Failed to load MCP config: {e}")
        return {}


def save_config(config: Dict[str, dict]):
    """Save MCP server configurations to disk."""
    _ensure_dir()
    try:
        CONFIG_FILE.write_text(
            json.dumps(config, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
    except OSError as e:
        logger.error(f"Failed to save MCP config: {e}")


def add_server(name: str, command: str = "",
               args: Optional[List[str]] = None,
               url: str = "",
               transport: str = "stdio",
               env: Optional[Dict[str, str]] = None,
               enabled: bool = True) -> bool:
    """Add an MCP server configuration."""
    config = load_config()
    if name in config:
        return False
    config[name] = {
        "name": name,
        "command": command,
        "args": args or [],
        "url": url,
        "transport": transport,
        "env": env or {},
        "enabled": enabled,
        "auto_reconnect": True,
    }
    save_config(config)
    return True


def remove_server(name: str) -> bool:
    """Remove an MCP server configuration."""
    config = load_config()
    if name not in config:
        return False
    del config[name]
    save_config(config)
    return True


def list_servers() -> List[Dict]:
    """List all configured MCP servers."""
    config = load_config()
    return list(config.values())


def get_server(name: str) -> Optional[dict]:
    """Get a specific MCP server configuration."""
    config = load_config()
    return config.get(name)


def to_lifecycle_configs() -> List[MCPServerConfig]:
    """Convert saved configs to MCPServerConfig objects."""
    configs = []
    for data in list_servers():
        configs.append(MCPServerConfig(
            name=data.get("name", ""),
            command=data.get("command", ""),
            args=data.get("args", []),
            url=data.get("url", ""),
            transport=data.get("transport", "stdio"),
            env=data.get("env", {}),
            auto_reconnect=data.get("auto_reconnect", True),
            enabled=data.get("enabled", True),
        ))
    return configs
