"""LAAP MCP — Lifecycle Manager

Full lifecycle management for MCP servers: start, stop, health check,
auto-reconnect, and status tracking.
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("laap.mcp.lifecycle")


class ServerState(Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"
    RECONNECTING = "reconnecting"


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server connection."""
    name: str
    command: str = ""
    args: List[str] = field(default_factory=list)
    url: str = ""
    env: Dict[str, str] = field(default_factory=dict)
    transport: str = "stdio"  # stdio or sse
    auto_reconnect: bool = True
    max_retries: int = 3
    health_check_interval: float = 30.0
    enabled: bool = True


class MCPServerInstance:
    """A managed MCP server instance."""

    def __init__(self, config: MCPServerConfig, client_manager):
        self.config = config
        self.client_manager = client_manager
        self.state = ServerState.STOPPED
        self._retry_count = 0
        self._last_error: Optional[str] = None
        self._started_at: Optional[float] = None
        self._health_task: Optional[asyncio.Task] = None
        self._tool_count = 0

    async def start(self) -> bool:
        self.state = ServerState.STARTING
        logger.info(f"MCP: starting {self.config.name}")

        if self.config.transport == "stdio":
            self.client_manager.add_stdio(
                self.config.name, self.config.command,
                self.config.args, self.config.env,
            )
        else:
            self.client_manager.add_sse(self.config.name, self.config.url)

        ok = await self.client_manager.connect_one(self.config.name)
        if ok:
            self.state = ServerState.RUNNING
            self._retry_count = 0
            self._started_at = time.time()
            conn = self.client_manager.get_connection(self.config.name)
            self._tool_count = len(conn.tools) if conn else 0
            # Start health check
            self._health_task = asyncio.create_task(self._health_loop())
            logger.info(f"MCP: {self.config.name} started ({self._tool_count} tools)")
            return True
        else:
            self.state = ServerState.ERROR
            self._last_error = "Failed to connect"
            return False

    async def stop(self, timeout: int = 10):
        self.state = ServerState.STOPPED
        if self._health_task:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        await self.client_manager.disconnect_all()
        logger.info(f"MCP: {self.config.name} stopped")

    async def restart(self) -> bool:
        await self.stop()
        return await self.start()

    async def _health_loop(self):
        while self.state == ServerState.RUNNING:
            await asyncio.sleep(self.config.health_check_interval)
            conn = self.client_manager.get_connection(self.config.name)
            if not conn or not conn.connected:
                logger.warning(f"MCP: {self.config.name} health check failed")
                if self.config.auto_reconnect and self._retry_count < self.config.max_retries:
                    self.state = ServerState.RECONNECTING
                    self._retry_count += 1
                    logger.info(f"MCP: reconnecting {self.config.name} (attempt {self._retry_count})")
                    ok = await self.client_manager.connect_one(self.config.name)
                    if ok:
                        self.state = ServerState.RUNNING
                        self._retry_count = 0
                        logger.info(f"MCP: {self.config.name} reconnected")
                    else:
                        self.state = ServerState.ERROR
                        self._last_error = f"Reconnect failed (attempt {self._retry_count})"
                else:
                    self.state = ServerState.ERROR
                    self._last_error = "Health check failed"

    def status(self) -> dict:
        return {
            "name": self.config.name,
            "state": self.state.value,
            "transport": self.config.transport,
            "tool_count": self._tool_count,
            "retry_count": self._retry_count,
            "last_error": self._last_error,
            "uptime": time.time() - self._started_at if self._started_at else 0,
            "enabled": self.config.enabled,
        }


class MCPLifecycleManager:
    """Manages lifecycle of multiple MCP server instances."""

    def __init__(self, client_manager=None):
        self.client_manager = client_manager or __import__(
            "laap.mcp.client", fromlist=["MCPClientManager"]
        ).MCPClientManager()
        self._instances: Dict[str, MCPServerInstance] = {}

    def register(self, config: MCPServerConfig) -> MCPServerInstance:
        instance = MCPServerInstance(config, self.client_manager)
        self._instances[config.name] = instance
        return instance

    def get(self, name: str) -> Optional[MCPServerInstance]:
        return self._instances.get(name)

    def remove(self, name: str) -> bool:
        inst = self._instances.pop(name, None)
        if inst:
            asyncio.create_task(inst.stop())
            return True
        return False

    async def start_all(self) -> List[str]:
        started = []
        for name, inst in self._instances.items():
            if inst.config.enabled and inst.state == ServerState.STOPPED:
                if await inst.start():
                    started.append(name)
        return started

    async def stop_all(self):
        for inst in self._instances.values():
            await inst.stop()

    def status(self) -> Dict[str, dict]:
        return {n: inst.status() for n, inst in self._instances.items()}

    def get_all_tools(self) -> list:
        return self.client_manager.get_all_tools()
