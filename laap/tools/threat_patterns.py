"""LAAP — Threat Detection Patterns (ported from Hermes Agent)

Detects potentially dangerous commands, file operations, and
prompt injection attempts before execution.
"""

from __future__ import annotations
import re
from typing import List, Tuple

# ── Dangerous Command Patterns ─────────────────────────────

DANGEROUS_COMMANDS = [
    (r"rm\s+-rf\s+[/~]", "Recursive root/home deletion"),
    (r"mkfs\b", "Filesystem format"),
    (r"dd\s+if=", "Raw disk write"),
    (r">\s*/dev/", "Device write"),
    (r"chmod\s+777\s+/", "World-writable root"),
    (r":\(\)\s*\{\s*:\(\)\s*\|", "Fork bomb"),
    (r"wget\s+.*\||curl\s+.*\|", "Download to pipe"),
    (r"eval\s+\$\(|eval\s+`", "Eval injection"),
    (r"sudo\s+rm\s+-rf", "Sudo recursive delete"),
    (r"shutdown|reboot|halt|poweroff", "System shutdown"),
    (r"passwd\s+|chpasswd|userdel|groupdel", "User management"),
]

SENSITIVE_PATHS = [
    r"/etc/passwd", r"/etc/shadow", r"/etc/sudoers",
    r"~/.ssh/", r"/var/log/auth", r"/etc/kubernetes/",
    r"/etc/ssl/", r"/etc/letsencrypt/",
]

SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|apikey|secret|token|password)\s*[:=]\s*.{16,}", "API Key/Token leak"),
    (r"(?i)(BEGIN\s+(RSA|EC|DSA|OPENSSH)\s+PRIVATE\s+KEY)", "Private key exposure"),
    (r"(?i)sk-[A-Za-z0-9]{20,}", "OpenAI API key format"),
    (r"(?i)ghp_[A-Za-z0-9]{36}", "GitHub personal access token"),
]

# ── Shell Injection Patterns ───────────────────────────────

INJECTION_PATTERNS = [
    (r"[;&|]\s*(wget|curl|bash|sh|python|perl|ruby)\s", "Command injection"),
    (r"`[^`]+`", "Backtick injection"),
    (r"\$\([^)]+\)", "Subshell injection"),
    (r"\|\s*(sh|bash)\b", "Pipe to shell"),
]


def check_command_safety(command: str) -> List[Tuple[str, str, str]]:
    """Check a shell command for dangerous patterns.

    Returns list of (pattern, severity, description) tuples.
    """
    warnings = []
    for pattern, desc in DANGEROUS_COMMANDS:
        if re.search(pattern, command):
            warnings.append((pattern, "CRITICAL", desc))
    for pattern, desc in INJECTION_PATTERNS:
        if re.search(pattern, command):
            warnings.append((pattern, "HIGH", desc))
    return warnings


def check_path_safety(path: str) -> List[Tuple[str, str]]:
    """Check if a path accesses sensitive files."""
    for pattern in SENSITIVE_PATHS:
        expanded = os.path.expanduser(path) if "~" in path else path
        if re.search(pattern, expanded):
            return [(pattern, "Sensitive system path")]
    return []


def detect_secrets(content: str) -> List[Tuple[str, str]]:
    """Detect secrets or credentials in content."""
    findings = []
    for pattern, desc in SECRET_PATTERNS:
        matches = re.findall(pattern, content)
        if matches:
            findings.append((pattern, desc))
    return findings


def sanitize_secrets(text: str) -> str:
    """Redact secrets from text for safe logging."""
    for pattern, _ in SECRET_PATTERNS:
        text = re.sub(pattern, "[REDACTED]", text)
    return text
