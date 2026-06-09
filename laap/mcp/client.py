"""LAAP MCP — Client"""
from __future__ import annotations
import asyncio, json, logging, os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("laap.mcp.client")

@dataclass
class MCPToolDef:
    server_name: str
    name: str
    description: str = ""
    input_schema: Dict = field(default_factory=dict)

class MCPClientConnection:
    def __init__(self, name: str, command: str = "",
                 args: Optional[List[str]] = None,
                 url: str = "",
                 env: Optional[Dict[str, str]] = None):
        self.name = name
        self.command = command
        self.args = args or []
        self.url = url
        self.env = env or {}
        self._session = None
        self._read = None
        self._write = None
        self._tools: List[MCPToolDef] = []
        self._connected = False

    async def connect(self) -> bool:
        try:
            from mcp import ClientSession, StdioServerParameters
            from mcp.client.stdio import stdio_client
            from mcp.client.sse import sse_client
            if self.url:
                self._read, self._write = await sse_client(self.url)
            else:
                params = StdioServerParameters(
                    command=self.command, args=self.args,
                    env={**os.environ, **self.env},
                )
                self._read, self._write = await stdio_client(params)
            self._session = await ClientSession(self._read, self._write)
            await self._session.initialize()
            result = await self._session.list_tools()
            self._tools = [
                MCPToolDef(server_name=self.name, name=t.name,
                          description=t.description or "",
                          input_schema=t.inputSchema or {})
                for t in result.tools
            ]
            self._connected = True
            logger.info(f"MCP: {self.name} connected ({len(self._tools)} tools)")
            return True
        except Exception as e:
            logger.error(f"MCP: connect {self.name} failed: {e}")
            return False

    async def call_tool(self, tool_name: str, arguments: Dict) -> str:
        if not self._session or not self._connected:
            return json.dumps({"error": "Not connected"})
        try:
            result = await self._session.call_tool(tool_name, arguments)
            texts = []
            for content in (result.content or []):
                if hasattr(content, 'text'):
                    texts.append(content.text)
                elif isinstance(content, dict):
                    texts.append(content.get('text', str(content)))
            return "\n".join(texts) if texts else "(no output)"
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def disconnect(self):
        self._connected = False
        if self._session:
            try:
                await self._session.__aexit__(None, None, None)
            except Exception:
                pass
        logger.info(f"MCP: {self.name} disconnected")

    @property
    def tools(self) -> List[MCPToolDef]:
        return list(self._tools)

    @property
    def connected(self) -> bool:
        return self._connected

class MCPClientManager:
    def __init__(self):
        self._connections: Dict[str, MCPClientConnection] = {}

    def add_stdio(self, name: str, command: str, args=None, env=None):
        self._connections[name] = MCPClientConnection(
            name=name, command=command, args=args or [], env=env or {})

    def add_sse(self, name: str, url: str):
        self._connections[name] = MCPClientConnection(name=name, url=url)

    async def connect_all(self) -> List[str]:
        ok_list = []
        for name, conn in self._connections.items():
            if await conn.connect():
                ok_list.append(name)
        return ok_list

    def get_connection(self, name: str) -> Optional[MCPClientConnection]:
        return self._connections.get(name)

    def get_all_tools(self) -> List[MCPToolDef]:
        tools = []
        for c in self._connections.values():
            if c.connected:
                tools.extend(c.tools)
        return tools

    async def call_tool(self, server: str, tool: str, args: Dict) -> str:
        conn = self._connections.get(server)
        if not conn:
            return json.dumps({"error": f"Server {server} not found"})
        return await conn.call_tool(tool, args)

    async def disconnect_all(self):
        for c in self._connections.values():
            await c.disconnect()

    def remove(self, name: str) -> bool:
        conn = self._connections.pop(name, None)
        if conn:
            import asyncio
            asyncio.create_task(conn.disconnect())
            return True
        return False
