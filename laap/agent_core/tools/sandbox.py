"""Tool Sandbox — 工具安全执行沙箱"""
from __future__ import annotations
import os, sys, json, logging, subprocess, tempfile, time
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger("agent_core.tools.sandbox")

class ToolSandbox:
    """工具沙箱 — 安全隔离/超时/资源限制/审计"""
    
    def __init__(self, workdir: str = ""):
        self.workdir = workdir or os.path.expanduser("~/.laap/sandbox")
        self._allowed_commands = ["python3", "python", "pip", "git", "ls", "cat", "echo", "mkdir", "cp", "mv", "rm"]
        self._blocked_patterns = ["rm -rf /", "mkfs", "dd if=", "> /dev/", ":(){ :|:& };:"]
        self._max_output = 10000
        self._timeout = 30
        self._audit: List[Dict] = []
        os.makedirs(self.workdir, exist_ok=True)
    
    def check_command(self, command: str) -> Tuple[bool, str]:
        """检查命令是否安全"""
        for pattern in self._blocked_patterns:
            if pattern in command.lower():
                return False, f"Blocked: dangerous pattern '{pattern}'"
        cmd_name = command.split()[0] if command.split() else ""
        if cmd_name and cmd_name not in self._allowed_commands:
            return False, f"Blocked: command '{cmd_name}' not in allowed list"
        return True, "ok"
    
    def execute(self, command: str, timeout: int = None) -> Dict:
        """在沙箱中执行命令"""
        safe, msg = self.check_command(command)
        if not safe:
            self._audit.append({"command": command, "status": "blocked", "reason": msg})
            return {"status": "blocked", "error": msg}
        try:
            start = time.time()
            result = subprocess.run(
                command, shell=True, capture_output=True,
                timeout=timeout or self._timeout,
                cwd=self.workdir
            )
            elapsed = round((time.time() - start) * 1000, 2)
            output = {
                "stdout": result.stdout.decode(errors='replace')[:self._max_output],
                "stderr": result.stderr.decode(errors='replace')[:1000],
                "returncode": result.returncode,
                "elapsed_ms": elapsed
            }
            status = "completed" if result.returncode == 0 else "error"
            self._audit.append({"command": command[:50], "status": status, "elapsed": elapsed})
            return output
        except subprocess.TimeoutExpired:
            self._audit.append({"command": command[:50], "status": "timeout"})
            return {"status": "timeout", "error": f"Timeout after {timeout or self._timeout}s"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
    
    def execute_python(self, code: str, timeout: int = 10) -> Dict:
        """安全执行Python代码"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, dir=self.workdir) as f:
            f.write(code)
            fpath = f.name
        try:
            return self.execute(f"python3 {fpath}", timeout)
        finally:
            try: os.unlink(fpath)
            except: pass
    
    def get_audit_log(self) -> List[Dict]:
        return list(self._audit)
    
    def get_stats(self) -> dict:
        total = len(self._audit)
        blocked = sum(1 for a in self._audit if a.get("status") == "blocked")
        return {"total_executions": total, "blocked": blocked, "workdir": self.workdir}
