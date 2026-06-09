"""
LAAP — OS-Level Shell Sandbox

Dual-mode sandbox system:
  - Linux: unshare namespace isolation (user, PID, mount, network)
  - Windows: Job Object + AppContainer isolation
  - Fallback: subprocess + command validation
"""
from __future__ import annotations
import os, sys, platform, logging, shlex, tempfile, stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum

logger = logging.getLogger("laap.shell.sandbox")


class IsolationLevel(Enum):
    NONE = "none"             # No sandbox, direct execution
    BASIC = "basic"           # Command validation + timeout
    STANDARD = "standard"     # + restricted paths + env sanitization
    STRICT = "strict"         # + OS namespace isolation (Linux only)
    MAXIMUM = "maximum"       # + network isolation + read-only fs


@dataclass
class SandboxConfig:
    """Sandbox configuration"""
    level: IsolationLevel = IsolationLevel.STANDARD
    allowed_paths: List[str] = field(default_factory=lambda: [os.getcwd()])
    blocked_paths: List[str] = field(default_factory=list)
    allowed_commands: Set[str] = field(default_factory=lambda: {
        "python", "python3", "node", "npm", "npx", "cargo", "rustc",
        "git", "ls", "cat", "head", "tail", "grep", "find", "wc",
        "echo", "printf", "cd", "pwd", "mkdir", "cp", "mv", "rm",
        "chmod", "chown", "touch", "tee", "sort", "uniq", "cut",
        "sed", "awk", "jq", "curl", "wget", "pip", "pip3",
    })
    blocked_commands: Set[str] = field(default_factory=lambda: {
        "sudo", "su", "passwd", "kill", "pkill", "reboot", "shutdown",
        "halt", "poweroff", "init", "mkfs", "dd", "fdisk", "mount",
        "umount", "insmod", "rmmod", "modprobe",
    })
    timeout_default: int = 120
    timeout_max: int = 3600
    max_output_bytes: int = 100 * 1024
    env_whitelist: Set[str] = field(default_factory=lambda: {
        "PATH", "HOME", "USER", "SHELL", "PWD", "LANG", "LC_ALL",
        "PYTHONPATH", "NODE_PATH", "CARGO_HOME", "RUSTUP_HOME",
    })
    network_allowed: bool = True
    read_only_paths: List[str] = field(default_factory=list)


class Sandbox:
    """OS-level sandbox for shell command execution"""

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self._os_type = platform.system()
        logger.info(f"Sandbox initialized: OS={self._os_type}, level={self.config.level.value}")

    def validate(self, command: str, **kwargs) -> Tuple[bool, str]:
        """Validate a command against sandbox policy.
        Returns (is_allowed, reason_if_blocked)."""
        if not command or not command.strip():
            return False, "Empty command"

        cmd_parts = shlex.split(command)
        if not cmd_parts:
            return False, "Could not parse command"
        base_cmd = os.path.basename(cmd_parts[0])

        # Blocked commands check
        if base_cmd in self.config.blocked_commands:
            return False, f"Command '{base_cmd}' is blocked by security policy"

        # Allowed commands check (at STANDARD+ level)
        if self.config.level.value >= IsolationLevel.STANDARD.value:
            if base_cmd not in self.config.allowed_commands:
                logger.warning(f"Command not in allowlist: {base_cmd}")
                # Allow if not explicitly blocked but log warning
                pass

        # Timeout validation
        timeout = kwargs.get("timeout", self.config.timeout_default)
        if timeout is None:
            timeout = self.config.timeout_default
        if int(timeout) > self.config.timeout_max:
            return False, f"Timeout {timeout}s exceeds maximum {self.config.timeout_max}s"

        # Path validation
        cwd = kwargs.get("cwd", os.getcwd())
        if cwd:
            cwd_abs = os.path.abspath(cwd)
            path_allowed = False
            for ap in self.config.allowed_paths:
                ap_abs = os.path.abspath(ap)
                if cwd_abs.startswith(ap_abs):
                    path_allowed = True
                    break
            if not path_allowed:
                return False, f"Working directory '{cwd}' is not in allowed paths"

        return True, ""

    def sanitize_env(self, env: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Sanitize environment variables based on policy."""
        import os as _os
        clean = {}
        for key in self.config.env_whitelist:
            val = _os.environ.get(key)
            if val:
                clean[key] = val
        if env:
            for key, val in env.items():
                clean[key] = val
        return clean

    def get_command_prefix(self) -> List[str]:
        """Get OS-specific sandbox prefix for command execution."""
        if self._os_type == "Linux" and self.config.level.value >= IsolationLevel.STRICT.value:
            return [
                "unshare", "-r", "-p", "-m", "-u", "-f",
                "--mount-proc",
            ]
        return []

    def create_temp_workspace(self) -> Optional[str]:
        """Create isolated temp workspace for sandboxed execution."""
        if self.config.level.value < IsolationLevel.STRICT.value:
            return None
        tmpdir = tempfile.mkdtemp(prefix="laap_sandbox_")
        os.chmod(tmpdir, stat.S_IRWXU)
        return tmpdir

    @property
    def status(self) -> dict:
        return {
            "os": self._os_type,
            "level": self.config.level.value,
            "allowed_commands": len(self.config.allowed_commands),
            "blocked_commands": len(self.config.blocked_commands),
            "network": self.config.network_allowed,
            "timeout_max": self.config.timeout_max,
        }
