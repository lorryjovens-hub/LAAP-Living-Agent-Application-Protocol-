"""LAAP Skill Template Engine"""
from __future__ import annotations
import logging, re, subprocess
from pathlib import Path
from typing import Optional
logger = logging.getLogger("laap.skills.template")
_TEMPLATE_RE = re.compile(r"\$\{(LAAP_SKILL_DIR|LAAP_SESSION_ID|LAAP_HOME)\}")
_INLINE_SHELL_RE = re.compile(r"!`([^`\n]+)`")
_MAX_OUT = 4000

def substitute_vars(content: str, skill_dir: Optional[Path] = None, session_id: Optional[str] = None) -> str:
    if not content: return content
    sd = str(skill_dir) if skill_dir else None
    lh = str(Path.home() / ".laap")
    def _rep(m):
        t = m.group(1)
        if t == "LAAP_SKILL_DIR" and sd: return sd
        if t == "LAAP_SESSION_ID" and session_id: return session_id
        if t == "LAAP_HOME": return lh
        return m.group(0)
    return _TEMPLATE_RE.sub(_rep, content)

def run_inline_shell(command: str, cwd: Optional[Path] = None, timeout: int = 10) -> str:
    try:
        r = subprocess.run(["bash", "-c", command], cwd=str(cwd) if cwd else None,
                          capture_output=True, text=True, timeout=max(1, timeout))
    except subprocess.TimeoutExpired: return f"[timeout: {command}]"
    except FileNotFoundError: return "[error: bash not found]"
    except Exception as e: return f"[error: {e}]"
    out = (r.stdout or "").rstrip("\n") or (r.stderr or "").rstrip("\n")
    return out[:_MAX_OUT] + "..." if len(out) > _MAX_OUT else out

def expand_inline_shell(content: str, skill_dir: Optional[Path] = None, timeout: int = 10) -> str:
    if "!`" not in content: return content
    def _rep(m): cmd = m.group(1).strip(); return run_inline_shell(cmd, skill_dir, timeout) if cmd else ""
    return _INLINE_SHELL_RE.sub(_rep, content)

def preprocess(content: str, skill_dir: Optional[Path] = None, session_id: Optional[str] = None,
               enable_shell: bool = False, shell_timeout: int = 10) -> str:
    if not content: return content
    content = substitute_vars(content, skill_dir, session_id)
    if enable_shell: content = expand_inline_shell(content, skill_dir, shell_timeout)
    return content