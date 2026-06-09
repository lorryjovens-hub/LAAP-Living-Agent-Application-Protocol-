"""
LAAP — Production Shell Tools
Shell execution, python runner, git integration.
"""

from __future__ import annotations
import json, logging

from laap.shell.executor import shell
from laap.git.operations import git

logger = logging.getLogger("laap.tools.shell")


def register_all(registry):
    """注册所有 Shell 工具 - 幂等安全"""
    _registered = getattr(registry, '_shell_tools_registered', False)
    if _registered:
        return
    registry._shell_tools_registered = True

    @registry.tool(name="run_command", category="shell",
                   description="Execute any shell command. Use for running tests, builds, git, npm/pip, etc.")
    def run_command(command: str, timeout: int = 60, workdir: str = "") -> str:
        """Run a shell command and return its output.

        Args:
            command: The shell command to execute
            timeout: Max execution time in seconds (default 60)
            workdir: Working directory (default: current)
        """
        result = shell.run(command, cwd=workdir or None, timeout=timeout)
        return json.dumps({
            "success": result["success"],
            "exit_code": result["exit_code"],
            "stdout": result.get("stdout", ""),
            "stderr": result.get("stderr", ""),
        }, ensure_ascii=False)

    @registry.tool(name="run_python", category="shell",
                   description="Execute Python code and return the output.")
    def run_python(code: str, timeout: int = 30) -> str:
        """Execute Python code snippet.

        Args:
            code: Python code to execute
            timeout: Max execution time in seconds
        """
        result = shell.run_python(code, timeout)
        return json.dumps(result, ensure_ascii=False)

    @registry.tool(name="run_script", category="shell",
                   description="Execute a local script file with optional arguments.")
    def run_script(script_path: str, args: str = "", timeout: int = 60) -> str:
        """Run a script file.

        Args:
            script_path: Path to the script
            args: Command-line arguments
            timeout: Max execution time
        """
        result = shell.run_script(script_path, args, timeout)
        return json.dumps(result, ensure_ascii=False)

    @registry.tool(name="git_status", category="git",
                   description="Show git status: branch, modified/untracked/staged files.")
    def git_status(path: str = ".") -> str:
        """Check git repository status.

        Args:
            path: Git repository path
        """
        result = git.status(path)
        return json.dumps(result, ensure_ascii=False)

    @registry.tool(name="git_diff", category="git",
                   description="Show git diff of uncommitted changes.")
    def git_diff(path: str = ".", staged: bool = False) -> str:
        """Show git diff.

        Args:
            path: Git repository path
            staged: Show staged changes only
        """
        result = git.diff(path, staged)
        return json.dumps(result, ensure_ascii=False)

    @registry.tool(name="git_log", category="git",
                   description="Show recent git commit history.")
    def git_log(path: str = ".", count: int = 10) -> str:
        """Show git log.

        Args:
            path: Git repository path
            count: Number of commits to show
        """
        result = git.log(path, count)
        return json.dumps(result, ensure_ascii=False)

    @registry.tool(name="git_commit", category="git",
                   description="Stage all changes and create a git commit.")
    def git_commit(message: str, path: str = ".", add_all: bool = True) -> str:
        """Create a git commit.

        Args:
            message: Commit message
            path: Git repository path
            add_all: Auto-stage all changes first
        """
        result = git.commit(message, path, add_all)
        return json.dumps(result, ensure_ascii=False)

    @registry.tool(name="git_branch", category="git",
                   description="List git branches or create a new branch.")
    def git_branch(name: str = "", path: str = ".") -> str:
        """Manage git branches.

        Args:
            name: Branch name (empty = list, non-empty = create & checkout)
            path: Git repository path
        """
        result = git.branch(name, path)
        return json.dumps(result, ensure_ascii=False)

    @registry.tool(name="shell_session", category="shell",
                   description="Create a persistent shell session for interactive commands.")
    def shell_session(action: str = "create", session_id: str = "",
                      command: str = "", cwd: str = "") -> str:
        """Manage persistent shell sessions.

        Args:
            action: create | write | read | close | list
            session_id: Session ID (for write/read/close)
            command: Command to write (for write action)
            cwd: Working directory (for create)
        """
        if action == "create":
            result = shell.create_session(cwd or None)
        elif action == "write":
            result = shell.write_session(session_id, command)
        elif action == "read":
            result = shell.read_session(session_id)
        elif action == "close":
            result = shell.close_session(session_id)
        elif action == "list":
            sessions = shell.list_sessions()
            return json.dumps({"success": True, "sessions": sessions})
        else:
            return json.dumps({"success": False, "error": f"Unknown action: {action}"})
        return json.dumps(result)
