"""Terminal Tool — 安全命令执行"""
from __future__ import annotations
import subprocess, json, logging, os, time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("agent_core.tools.terminal")

class TerminalTool:
    def __init__(self):
        self._workdir = os.getcwd()
    
    def execute(self, command: str, timeout: int = 30, workdir: str = "") -> str:
        """执行Shell命令"""
        try:
            cwd = workdir or self._workdir
            result = subprocess.run(command, shell=True, capture_output=True,
                                   timeout=timeout, cwd=cwd)
            return json.dumps({
                "stdout": result.stdout.decode(errors='replace')[:5000],
                "stderr": result.stderr.decode(errors='replace')[:1000],
                "returncode": result.returncode,
                "command": command[:100],
            }, ensure_ascii=False)
        except subprocess.TimeoutExpired:
            return json.dumps({"error": f"Timeout after {timeout}s", "command": command[:50]})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def set_workdir(self, path: str) -> str:
        """设置工作目录"""
        if os.path.isdir(path):
            self._workdir = path
            return json.dumps({"workdir": path})
        return json.dumps({"error": f"Not a directory: {path}"})

TOOL_DEFS = [
    {"name":"run_command","fn":TerminalTool().execute,"desc":"执行Shell命令","params":{"command":{"type":"string"},"timeout":{"type":"integer"},"workdir":{"type":"string"}},"req":["command"]},
    {"name":"set_workdir","fn":TerminalTool().set_workdir,"desc":"设置工作目录","params":{"path":{"type":"string"}},"req":["path"]},
]
