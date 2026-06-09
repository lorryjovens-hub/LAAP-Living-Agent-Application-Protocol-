"""LAAP — Model Context Protocol (MCP)

Full MCP lifecycle management:
- Server: expose LAAP tools as MCP tools via FastMCP
- Client: connect to external MCP servers and discover tools
- Lifecycle: start/stop/health-check/auto-reconnect
- OAuth: authorization code flow for authenticated MCP servers
- Config: persistent server configuration
"""

from laap.mcp.server import LAAPMCPServer
# Backward compat alias
MCPServer = LAAPMCPServer
from laap.mcp.client import MCPClientManager, MCPClientConnection, MCPToolDef
from laap.mcp.lifecycle import MCPLifecycleManager, MCPServerConfig, MCPServerInstance, ServerState
from laap.mcp.oauth import oauth_flow, get_token, has_token, remove_token
from laap.mcp.config import add_server, remove_server, list_servers, load_config
