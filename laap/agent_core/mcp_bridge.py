"""MCP Bridge — 将MCP服务器桥接到Agent工具系统"""
from __future__ import annotations
import json, os, logging, subprocess, threading, time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent_core.mcp_bridge")
from laap.agent_core.tool_manager import ToolManager, Tool

class MCPBridge:
    def __init__(self, tool_manager=None):
        self.tool_mgr = tool_manager
        self._servers: Dict[str, Dict] = {}
        self._tools_registered: List[str] = []
        self._lock = threading.RLock()
        self._call_count = 0
        self._error_count = 0
    
    def load_config(self, config_path=None) -> Dict[str, Dict]:
        if config_path is None:
            config_path = os.path.expanduser("~/.laap/mcp/servers.json")
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    servers = json.load(f)
                if isinstance(servers, dict):
                    parsed = {}
                    for name, cfg in servers.items():
                        parsed[name] = {"name": name, **(cfg if isinstance(cfg, dict) else {})}
                    servers = parsed
                elif isinstance(servers, list):
                    servers = {s.get("name", f"mcp_{i}"): s for i, s in enumerate(servers)}
                with self._lock:
                    self._servers = servers if isinstance(servers, dict) else {}
                logger.info(f"Loaded {len(self._servers)} MCP servers")
            except Exception as e:
                logger.error(f"Failed to load MCP config: {e}")
        return dict(self._servers)
    
    def register_builtin_servers(self):
        builtin = {
            "filesystem": {"command":"npx","args":["-y","@modelcontextprotocol/server-filesystem",os.path.expanduser("~")],"description":"MCP文件系统"},
            "sqlite": {"command":"npx","args":["-y","@modelcontextprotocol/server-sqlite",":memory:"],"description":"MCP SQLite"},
            "github": {"command":"npx","args":["-y","@modelcontextprotocol/server-github"],"description":"MCP GitHub"},
            "brave-search": {"command":"npx","args":["-y","@modelcontextprotocol/server-brave-search"],"description":"MCP搜索"},
            "fetch": {"command":"uvx","args":["mcp-server-fetch"],"description":"MCP网页抓取"},
            "memory": {"command":"npx","args":["-y","@modelcontextprotocol/server-memory"],"description":"MCP记忆"},
        }
        with self._lock:
            for name, cfg in builtin.items():
                if name not in self._servers:
                    self._servers[name] = {"name": name, **cfg}
    
    def discover_tools(self) -> List[Dict]:
        if self.tool_mgr is None:
            return []
        tools_info = []
        with self._lock:
            for name, config in self._servers.items():
                cmd = config.get("command", "")
                if not cmd:
                    continue
                tool_name = f"mcp_{name}"
                tool = Tool(name=tool_name, description=config.get("description", f"MCP:{name}"),
                          parameters={"type":"object","properties":{"input":{"type":"string"},"timeout":{"type":"integer","default":30}},"required":["input"]},
                          handler=lambda inp, to=30, n=name: json.dumps(self._call_mcp(n, inp, to), ensure_ascii=False, default=str),
                          category="mcp")
                self.tool_mgr.register(tool)
                self._tools_registered.append(tool_name)
                tools_info.append({"name": name, "tool_name": tool_name})
        return tools_info
    
    def _call_mcp(self, server_name, input_data, timeout=30):
        config = self._servers.get(server_name, {})
        cmd = config.get("command", "")
        args_list = config.get("args", [])
        env_vars = config.get("env", {})
        if not cmd:
            return {"error": f"Server '{server_name}' not configured"}
        self._call_count += 1
        try:
            full_cmd = [cmd] + (args_list or [])
            merged_env = os.environ.copy()
            merged_env.update(env_vars)
            result = subprocess.run(full_cmd, input=str(input_data).encode("utf-8") if not isinstance(input_data, bytes) else input_data,
                                   capture_output=True, timeout=timeout, env=merged_env)
            return {"stdout": result.stdout.decode("utf-8", errors="replace")[:2000],
                    "stderr": result.stderr.decode("utf-8", errors="replace")[:500],
                    "returncode": result.returncode}
        except subprocess.TimeoutExpired:
            self._error_count += 1
            return {"error": f"Timeout after {timeout}s"}
        except FileNotFoundError:
            return {"error": f"Command '{cmd}' not found"}
        except Exception as e:
            self._error_count += 1
            return {"error": str(e)}
    
    def list_servers(self) -> List[Dict]:
        with self._lock:
            return [{"name": n, "command": c.get("command",""), "description": c.get("description","")} for n, c in self._servers.items()]
    
    def get_stats(self) -> Dict:
        with self._lock:
            return {"servers": len(self._servers), "tools_registered": len(self._tools_registered),
                    "calls": self._call_count, "errors": self._error_count}

def create_mcp_bridge(tool_manager):
    bridge = MCPBridge(tool_manager)
    bridge.load_config()
    bridge.register_builtin_servers()
    bridge.discover_tools()
    return bridge
