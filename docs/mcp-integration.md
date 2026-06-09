# MCP Integration

## Model Context Protocol

LAAP implements the Model Context Protocol (MCP) for standardized tool discovery and execution.

### Architecture

```
LAAP Agent ←→ MCP Client ←→ MCP Server (stdio/HTTP)
                              │
                    ┌─────────┼─────────┐
                    │         │         │
               Filesystem    DB    Browser
```

### Server Capabilities

- **Tools**: Expose callable functions
- **Resources**: Expose readable data
- **Lifecycle**: Health monitoring + auto-restart

### Configuration

```json
{
  "mcp_servers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/workspace"]
    }
  }
}
```

### Lifecycle Management

Each MCP server goes through:
```
STOPPED → STARTING → RUNNING ↔ DEGRADED → STOPPING → STOPPED
                                              ↓
                                           FAILED
```

Auto-restart with configurable retry limits and health checks.
