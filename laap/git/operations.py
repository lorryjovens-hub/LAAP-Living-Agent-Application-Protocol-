"""
LAAP — Git Operations
Git integration for the LAAP code agent.
"""

from __future__ import annotations
import subprocess, logging
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("laap.git")


class GitOps:
    """Git operations with safe wrappers."""

    @staticmethod
    def status(path: str = ".") -> Dict[str, Any]:
        try:
            result = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, timeout=10, cwd=path)
            if result.returncode != 0:
                return {"success": False, "error": result.stderr[:500], "is_git_repo": False}
            files = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    files.append({"path": line[3:], "status": line[:2].strip()})
            branch_result = subprocess.run(["git", "branch", "--show-current"], capture_output=True, text=True, timeout=5, cwd=path)
            branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""
            return {"success": True, "is_git_repo": True, "branch": branch, "files": files,
                    "modified": sum(1 for f in files if f["status"] == "M"),
                    "untracked": sum(1 for f in files if f["status"] == "??")}
        except FileNotFoundError:
            return {"success": False, "error": "Git not installed", "is_git_repo": False}
        except subprocess.TimeoutExpired:
            return {"success": False, "error": "Git timeout", "is_git_repo": False}

    @staticmethod
    def diff(path: str = ".", staged: bool = False) -> Dict[str, Any]:
        cmd = ["git", "diff"]
        if staged: cmd.append("--cached")
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15, cwd=path)
            return {"success": True, "diff": result.stdout[:100000], "files_changed": result.stdout.count("diff --git")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def log(path: str = ".", count: int = 20) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["git", "log", f"--max-count={count}", "--pretty=format:%h|%an|%ar|%s"],
                capture_output=True, text=True, timeout=10, cwd=path)
            commits = []
            for line in result.stdout.strip().split("\n"):
                if "|" in line:
                    p = line.split("|", 3)
                    commits.append({"hash": p[0], "author": p[1], "date": p[2], "message": p[3] if len(p) > 3 else ""})
            return {"success": True, "commits": commits}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def commit(message: str, path: str = ".", add_all: bool = True) -> Dict[str, Any]:
        try:
            if add_all: subprocess.run(["git", "add", "-A"], capture_output=True, timeout=10, cwd=path)
            result = subprocess.run(["git", "commit", "-m", message], capture_output=True, text=True, timeout=10, cwd=path)
            return {"success": result.returncode == 0, "output": result.stdout.strip()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def branch(name: str = "", path: str = ".") -> Dict[str, Any]:
        if name:
            try:
                r = subprocess.run(["git", "checkout", "-b", name], capture_output=True, text=True, timeout=10, cwd=path)
                return {"success": r.returncode == 0}
            except Exception as e:
                return {"success": False, "error": str(e)}
        try:
            r = subprocess.run(["git", "branch"], capture_output=True, text=True, timeout=5, cwd=path)
            return {"success": True, "branches": [b.strip() for b in r.stdout.strip().split("\n") if b.strip()]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @staticmethod
    def is_git_repo(path: str = ".") -> bool:
        return (Path(path) / ".git").exists()

    @staticmethod
    def add(files: List[str], path: str = ".") -> Dict[str, Any]:
        try:
            r = subprocess.run(["git", "add", "--"] + files, capture_output=True, text=True, timeout=10, cwd=path)
            return {"success": r.returncode == 0}
        except Exception as e:
            return {"success": False, "error": str(e)}


git = GitOps()
