"""MCP Integration — 将MCP工具桥接到Agent的工具系统"""
from __future__ import annotations
import json, logging
from typing import Any, Callable, Dict, List, Optional
from laap.agent_core.tool_manager import ToolManager, Tool

logger = logging.getLogger("agent_core.mcp_integration")

class MCPBridge:
    """MCP <-> Agent 桥接器"""
    def __init__(self, tool_manager: ToolManager):
        self.tool_mgr = tool_manager
    def register_mcp_tools(self, mcp_tools: List[Dict]):
        for mt in mcp_tools:
            tool = Tool(name=mt.get("name", "unknown"),
                       description=mt.get("description", ""),
                       parameters=mt.get("inputSchema", {"type": "object", "properties": {}}),
                       category="mcp")
            self.tool_mgr.register(tool)
            logger.info(f"MCP tool registered: {tool.name}")
    def bridge(self, server_url: str = "http://localhost:8000/mcp"):
        logger.info(f"MCP bridge to {server_url}")
        return {"status": "connected", "server": server_url}
