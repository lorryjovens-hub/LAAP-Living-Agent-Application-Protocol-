"""LAAP MCP — Server

FastMCP-based MCP server that exposes LAAP's tools, memory, and
cognitive capabilities as MCP tools for use by any MCP client.
"""

from __future__ import annotations
import json
import logging
import sys
from typing import Any, Dict, List, Optional

logger = logging.getLogger("laap.mcp.server")


try:
    from mcp.server.fastmcp import FastMCP
    HAS_FASTMCP = True
except ImportError:
    HAS_FASTMCP = False
    FastMCP = None  # type: ignore



class LAAPMCPServer:
    """MCP server exposing LAAP capabilities via FastMCP.

    Exposes as MCP tools:
    - LAAP agent tools (read/write/search/execute)
    - Memory tools (remember/recall/forget)
    - Cognitive tools (needs/emotion/status)
    - MCP server management tools
    """

    def __init__(self, name: str = "LAAP-Agent", agent=None):
        self.name = name
        self.agent = agent
        self._server: Optional[FastMCP] = None
        self._running = False
        self._event_bridge = None

    def build_server(self) -> FastMCP:
        """Build and configure the FastMCP server."""
        if not HAS_FASTMCP:
            raise ImportError("pip install mcp")

        mcp = FastMCP(self.name, log_level="WARNING")

        # ── Agent Tools ──────────────────────────────────────
        @mcp.tool()
        async def agent_chat(message: str) -> str:
            """Send a message to the LAAP agent and get a response."""
            if not self.agent:
                return "Agent not connected"
            import asyncio
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(None, self.agent.chat, message)

        @mcp.tool()
        async def agent_status() -> str:
            """Get the current agent status."""
            if not self.agent:
                return json.dumps({"status": "disconnected"})
            return json.dumps(self.agent.status())

        @mcp.tool()
        async def agent_memory_prefetch(query: str) -> str:
            """Retrieve relevant memories for a query."""
            if not self.agent or not hasattr(self.agent, 'memory_manager'):
                return "[]"
            ctx = self.agent.memory_manager.prefetch_all(query)
            return ctx or "[]"

        # ── File Tools ────────────────────────────────────────
        @mcp.tool()
        async def read_file(path: str) -> str:
            """Read a file from the filesystem."""
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception as e:
                return json.dumps({"error": str(e)})

        @mcp.tool()
        async def write_file(path: str, content: str) -> str:
            """Write content to a file."""
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(content)
                return json.dumps({"status": "written", "path": path})
            except Exception as e:
                return json.dumps({"error": str(e)})

        @mcp.tool()
        async def search_files(pattern: str, path: str = ".") -> str:
            """Search for files matching a pattern."""
            import glob as glob_mod
            matches = glob_mod.glob(os.path.join(path, pattern), recursive=True)
            return json.dumps(matches[:100])

        # ── Shell Tools ───────────────────────────────────────
        @mcp.tool()
        async def run_command(command: str, timeout: int = 30) -> str:
            """Run a shell command and return output."""
            import subprocess
            try:
                result = subprocess.run(
                    command, shell=True, capture_output=True,
                    text=True, timeout=timeout,
                )
                output = result.stdout[-5000:] if result.stdout else ""
                if result.stderr:
                    output += "\nSTDERR:\n" + result.stderr[-1000:]
                return output or "(no output)"
            except subprocess.TimeoutExpired:
                return "(timeout)"
            except Exception as e:
                return json.dumps({"error": str(e)})

        # ── Web Tools ─────────────────────────────────────────
        @mcp.tool()
        async def web_search(query: str) -> str:
            """Search the web for information."""
            try:
                import httpx
                url = f"https://api.duckduckgo.com/?q={query}&format=json"
                async with httpx.AsyncClient() as client:
                    resp = await client.get(url, timeout=10)
                    return resp.text[:5000]
            except Exception as e:
                return json.dumps({"error": str(e)})

        # ── Memory Tools ──────────────────────────────────────
        @mcp.tool()
        async def memory_store(content: str, memory_type: str = "fact",
                               importance: float = 0.5) -> str:
            """Store a memory in the persistent memory system."""
            if not self.agent or not hasattr(self.agent, 'memory_manager'):
                return json.dumps({"error": "memory not available"})
            from laap.memory.persistent import MemoryEntry
            provider = self.agent.memory_manager.get_provider("builtin")
            if provider:
                eid = provider._engine.store(
                    MemoryEntry(content=content, memory_type=memory_type,
                                importance=importance)
                )
                return json.dumps({"status": "stored", "id": eid[:8]})
            return json.dumps({"error": "no provider"})

        @mcp.tool()
        async def memory_recall(query: str = "", limit: int = 5) -> str:
            """Recall memories from the persistent memory system."""
            if not self.agent or not hasattr(self.agent, 'memory_manager'):
                return "[]"
            provider = self.agent.memory_manager.get_provider("builtin")
            if provider:
                result = provider.handle_tool_call("recall",
                    {"query": query, "limit": limit})
                return result
            return "[]"

        # ── Cognitive Status ──────────────────────────────────
        @mcp.tool()
        async def cognitive_status() -> str:
            """Get the cognitive state (needs, emotions, goals)."""
            if not self.agent:
                return json.dumps({"status": "no_agent"})
            state = {}
            if hasattr(self.agent, 'needs'):
                state["needs"] = {k: v.to_dict() for k, v in self.agent.needs.needs.items()}
            if hasattr(self.agent, 'emotion_gradient'):
                state["emotion"] = self.agent.emotion_gradient.state.to_dict()
            if hasattr(self.agent, 'goals'):
                state["goals"] = self.agent.goals.to_dict()
            return json.dumps(state, ensure_ascii=False)

        self._server = mcp
        return mcp

    def run_stdio(self):
        """Run the MCP server over stdio transport."""
        if not self._server:
            self.build_server()
        self._running = True
        logger.info(f"MCP server '{self.name}' running on stdio")
        self._server.run(transport="stdio")

    def run_sse(self, host: str = "127.0.0.1", port: int = 8766):
        """Run the MCP server over SSE transport."""
        if not self._server:
            self.build_server()
        self._running = True
        logger.info(f"MCP server '{self.name}' running on http://{host}:{port}/sse")
        self._server.run(transport="sse", host=host, port=port)

    def stop(self):
        """Stop the MCP server."""
        self._running = False
        logger.info("MCP server stopped")

class MCPServer(LAAPMCPServer):
    """Backward compatible alias for LAAPMCPServer."""
    pass
