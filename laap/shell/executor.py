"""
LAAP — Production Shell Executor
Subprocess execution with streaming, sessions, safety controls.
"""

from __future__ import annotations
import asyncio, logging, os, signal, subprocess, threading, time, shlex
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from laap.shell.sandbox import Sandbox, SandboxConfig, IsolationLevel

logger = logging.getLogger("laap.shell")


@dataclass
class ShellSession:
    """A persistent shell session."""
    id: str
    cwd: str
    shell: str
    process: Optional[subprocess.Popen] = None
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)


class ShellExecutor:
    """Production shell execution engine with streaming output."""

    MAX_OUTPUT = 100 * 1024  # 100KB max output
    DEFAULT_TIMEOUT = 120
    DANGEROUS_COMMANDS = {
        "rm -rf /", "mkfs", "dd if=", "> /dev/", "chmod 777 /",
        "wget http://", "curl http://", ":(){ :|:& };:", "sudo ",
    }

    def __init__(self):
        self.sessions: Dict[str, ShellSession] = {}
        self._session_counter = 0
        self._lock = threading.Lock()
        self._blocked_commands: List[str] = []

    def run(self, command: str, cwd: Optional[str] = None,
            timeout: int = DEFAULT_TIMEOUT, check_dangerous: bool = True,
            env: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """Execute a shell command and return output (blocking).

        Args:
            command: Shell command to execute
            cwd: Working directory (default: current)
            timeout: Max execution time in seconds
            check_dangerous: Check for dangerous commands
            env: Additional environment variables

        Returns:
            Dict with stdout, stderr, exit_code, success
        """
        # Safety check — Sandbox + dangerous patterns
        if check_dangerous:
            sandbox = Sandbox(SandboxConfig())
            sb_allowed, sb_reason = sandbox.validate(command, timeout=timeout)
            if not sb_allowed:
                return {
                    "success": False,
                    "error": f"Command blocked by sandbox: {sb_reason}",
                    "exit_code": -1, "stdout": "", "stderr": "Blocked by sandbox",
                }
            danger = self._is_dangerous(command)
            if danger:
                return {
                    "success": False,
                    "error": f"Command blocked (dangerous pattern detected): {danger}",
                    "exit_code": -1,
                    "stdout": "",
                    "stderr": "Blocked by safety system",
                }

        workdir = cwd or os.getcwd()
        merged_env = os.environ.copy()
        if env:
            merged_env.update(env)

        try:
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=workdir,
                env=merged_env,
                text=True,
                encoding="utf-8",
                errors="replace",
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                return {
                    "success": False,
                    "error": f"Command timed out after {timeout}s",
                    "exit_code": -1,
                    "stdout": stdout[-self.MAX_OUTPUT:],
                    "stderr": stderr[-self.MAX_OUTPUT:],
                }

            exit_code = process.returncode

            # Truncate large outputs
            if len(stdout) > self.MAX_OUTPUT:
                stdout = stdout[-self.MAX_OUTPUT:] + "\n... (truncated)"
            if len(stderr) > self.MAX_OUTPUT // 2:
                stderr = stderr[-self.MAX_OUTPUT // 2:] + "\n... (truncated)"

            return {
                "success": exit_code == 0,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "command": command[:200],
                "cwd": workdir,
                "duration": timeout,  # approximate
            }

        except FileNotFoundError:
            return {"success": False, "error": f"Shell not found: {command.split()[0]}", "exit_code": -1}
        except Exception as e:
            return {"success": False, "error": str(e), "exit_code": -1}

    def run_python(self, code: str, timeout: int = 30) -> Dict[str, Any]:
        """Execute Python code snippet."""
        return self.run(f"python -c {shlex.quote(code)}", timeout=timeout)

    def run_script(self, script_path: str, args: str = "", timeout: int = 60) -> Dict[str, Any]:
        """Execute a script file."""
        return self.run(f"{script_path} {args}", timeout=timeout)

    def stream(self, command: str, cwd: Optional[str] = None,
               on_stdout: Optional[Callable[[str], None]] = None,
               on_stderr: Optional[Callable[[str], None]] = None,
               on_done: Optional[Callable[[int], None]] = None,
               timeout: int = DEFAULT_TIMEOUT) -> Dict[str, Any]:
        """Execute command with streaming output callbacks."""
        workdir = cwd or os.getcwd()
        process = subprocess.Popen(
            command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=workdir, text=True, encoding="utf-8", errors="replace",
        )

        stdout_buf, stderr_buf = [], []
        def _reader(pipe, buf, callback):
            for line in iter(pipe.readline, ""):
                buf.append(line)
                if callback: callback(line)
            pipe.close()

        threads = [
            threading.Thread(target=_reader, args=(process.stdout, stdout_buf, on_stdout), daemon=True),
            threading.Thread(target=_reader, args=(process.stderr, stderr_buf, on_stderr), daemon=True),
        ]
        for t in threads: t.start()

        try:
            process.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()

        for t in threads: t.join(timeout=5)

        stdout = "".join(stdout_buf)
        stderr = "".join(stderr_buf)

        if on_done: on_done(process.returncode)
        return {
            "success": process.returncode == 0,
            "exit_code": process.returncode,
            "stdout": stdout,
            "stderr": stderr,
        }

    # ── Persistent Session ──

    def create_session(self, cwd: Optional[str] = None, shell: str = "") -> Dict[str, Any]:
        """Create a persistent shell session."""
        import uuid
        sid = str(uuid.uuid4())[:8]
        shell_cmd = shell or os.environ.get("SHELL", "cmd.exe" if os.name == "nt" else "bash")

        try:
            process = subprocess.Popen(
                [shell_cmd], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, cwd=cwd or os.getcwd(),
                text=True, encoding="utf-8", errors="replace",
            )
            session = ShellSession(id=sid, cwd=cwd or os.getcwd(), shell=shell_cmd, process=process)
            with self._lock:
                self.sessions[sid] = session
            return {"success": True, "session_id": sid, "shell": shell_cmd}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def write_session(self, session_id: str, data: str) -> Dict[str, Any]:
        """Write to a session's stdin."""
        with self._lock:
            session = self.sessions.get(session_id)
        if not session or not session.process:
            return {"success": False, "error": "Session not found"}
        try:
            session.process.stdin.write(data + "\n")
            session.process.stdin.flush()
            session.last_active = time.time()
            return {"success": True}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def read_session(self, session_id: str) -> Dict[str, Any]:
        """Read pending output from a session."""
        with self._lock:
            session = self.sessions.get(session_id)
        if not session or not session.process:
            return {"success": False, "error": "Session not found"}
        try:
            import select
            if hasattr(session.process.stdout, 'fileno'):
                readable, _, _ = select.select([session.process.stdout], [], [], 0.1)
                if readable:
                    output = session.process.stdout.read()
                    return {"success": True, "output": output}
            return {"success": True, "output": ""}
        except Exception:
            return {"success": True, "output": ""}

    def close_session(self, session_id: str) -> Dict[str, Any]:
        """Close a shell session."""
        with self._lock:
            session = self.sessions.pop(session_id, None)
        if session and session.process:
            try:
                session.process.terminate()
                session.process.wait(timeout=5)
            except Exception:
                session.process.kill()
            return {"success": True}
        return {"success": False, "error": "Session not found"}

    def list_sessions(self) -> List[Dict[str, Any]]:
        """List all active sessions."""
        result = []
        with self._lock:
            for sid, session in self.sessions.items():
                alive = session.process and session.process.poll() is None
                result.append({
                    "id": sid, "shell": session.shell, "cwd": session.cwd,
                    "alive": alive, "idle_seconds": int(time.time() - session.last_active),
                })
        return result

    def _is_dangerous(self, command: str) -> Optional[str]:
        """Check if command contains dangerous patterns."""
        cmd_lower = command.lower().strip()
        for dangerous in self.DANGEROUS_COMMANDS:
            if dangerous in cmd_lower:
                return dangerous
        return None


shell = ShellExecutor()
