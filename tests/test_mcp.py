"""Tests for LAAP MCP Server & Lifecycle"""
import pytest
import json
from laap.mcp.server import LAAPMCPServer
from laap.mcp.lifecycle import MCPServerConfig, MCPServerInstance, ServerState, MCPLifecycleManager
from laap.mcp.config import add_server, remove_server, list_servers


class TestLAAPMCPServer:
    """Tests for the FastMCP-based LAAP MCP Server."""

    def test_build_server(self):
        """Server should build without error."""
        server = LAAPMCPServer("test")
        mcp = server.build_server()
        assert mcp is not None
        assert mcp.name == "test"

    def test_server_name(self):
        """Server name should be configurable."""
        server = LAAPMCPServer("my-agent")
        assert server.name == "my-agent"

    def test_server_stop(self):
        """Stop should not raise."""
        server = LAAPMCPServer("test")
        server.stop()  # Should be safe


class TestMCPLifecycle:
    """Tests for MCP lifecycle management."""

    def test_server_config_defaults(self):
        cfg = MCPServerConfig(name="test")
        assert cfg.name == "test"
        assert cfg.transport == "stdio"
        assert cfg.auto_reconnect == True

    def test_server_config_stdio(self):
        cfg = MCPServerConfig(
            name="test", command="python", args=["-m", "http.server"],
            transport="stdio",
        )
        assert cfg.command == "python"
        assert cfg.args == ["-m", "http.server"]

    def test_server_config_sse(self):
        cfg = MCPServerConfig(
            name="test", url="http://localhost:8080/sse",
            transport="sse",
        )
        assert cfg.url == "http://localhost:8080/sse"
        assert cfg.transport == "sse"

    def test_server_state_enum(self):
        assert ServerState.STOPPED.value == "stopped"
        assert ServerState.RUNNING.value == "running"
        assert ServerState.ERROR.value == "error"

    def test_lifecycle_manager_init(self):
        mgr = MCPLifecycleManager()
        assert mgr.status() == {}

    def test_lifecycle_manager_register(self):
        mgr = MCPLifecycleManager()
        cfg = MCPServerConfig(name="test")
        inst = mgr.register(cfg)
        assert inst is not None
        assert mgr.get("test") is not None
        assert mgr.get("test").config.name == "test"

    def test_lifecycle_manager_register_and_get(self):
        mgr = MCPLifecycleManager()
        cfg = MCPServerConfig(name="test")
        inst = mgr.register(cfg)
        assert mgr.get("test") is not None
        assert mgr.get("test").config.name == "test"

    def test_instance_initial_state(self):
        from laap.mcp.client import MCPClientManager
        cm = MCPClientManager()
        cfg = MCPServerConfig(name="test")
        inst = MCPServerInstance(cfg, cm)
        assert inst.state == ServerState.STOPPED

    def test_instance_status_dict(self):
        from laap.mcp.client import MCPClientManager
        cm = MCPClientManager()
        cfg = MCPServerConfig(name="test")
        inst = MCPServerInstance(cfg, cm)
        status = inst.status()
        assert status["name"] == "test"
        assert status["state"] == "stopped"
        assert status["enabled"] == True


class TestMCPConfig:
    """Tests for MCP configuration persistence."""

    def test_add_list_remove(self):
        add_server("test-cfg", command="echo")
        servers = list_servers()
        assert any(s["name"] == "test-cfg" for s in servers)
        remove_server("test-cfg")
        servers = list_servers()
        assert not any(s["name"] == "test-cfg" for s in servers)

    def test_add_duplicate(self):
        add_server("dup-test", command="echo")
        result = add_server("dup-test", command="other")
        assert result == False
        remove_server("dup-test")
        servers = list_servers()
        assert not any(s["name"] == "dup-test" for s in servers)

    def test_remove_nonexistent(self):
        result = remove_server("nonexistent-server-xyz")
        assert result == False
