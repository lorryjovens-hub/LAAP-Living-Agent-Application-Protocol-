"""FileSafety — 文件操作安全管控"""
from __future__ import annotations
import os, re, logging
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("agent_core.file_safety")

DEFAULT_ALLOWED_DIRS = [os.path.expanduser("~"), os.getcwd()]
DEFAULT_BLOCKED_PATTERNS = [r"\.env", r"id_rsa", r"\.ssh", r"config\.json$", r"credentials", r"token", r"secret", r"key\.pem"]
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
MAX_FILES_PER_OP = 100

class FileSafetyManager:
    """文件安全管控 — 路径校验/黑名单/大小限制/审计"""
    
    def __init__(self):
        self.allowed_dirs = list(DEFAULT_ALLOWED_DIRS)
        self.blocked_patterns = list(DEFAULT_BLOCKED_PATTERNS)
        self.max_file_size = MAX_FILE_SIZE
        self._audit_log: List[Dict] = []
    
    def add_allowed_dir(self, path: str):
        self.allowed_dirs.append(os.path.abspath(path))
    
    def check_path(self, path: str) -> Tuple[bool, str]:
        """检查路径是否安全"""
        abs_path = os.path.abspath(path)
        
        # 检查路径穿越
        if ".." in path.split(os.sep):
            return False, "路径穿越攻击被阻止"
        
        # 检查是否在允许目录内
        allowed = False
        for d in self.allowed_dirs:
            if abs_path.startswith(os.path.abspath(d)):
                allowed = True
                break
        if not allowed:
            return False, f"路径不在允许目录内: {abs_path}"
        
        # 检查黑名单模式
        for pattern in self.blocked_patterns:
            if re.search(pattern, abs_path, re.IGNORECASE):
                return False, f"文件匹配安全黑名单: {pattern}"
        
        # 检查文件大小
        if os.path.exists(abs_path) and os.path.isfile(abs_path):
            size = os.path.getsize(abs_path)
            if size > self.max_file_size:
                return False, f"文件过大: {size} > {self.max_file_size}"
        
        return True, "ok"
    
    def log_operation(self, op: str, path: str, user: str = "agent", success: bool = True):
        self._audit_log.append({
            "op": op, "path": path, "user": user, "success": success,
            "timestamp": __import__('time').time()
        })
    
    def set_max_file_size(self, size: int):
        self.max_file_size = size
    
    def add_blocked_pattern(self, pattern: str):
        self.blocked_patterns.append(pattern)
    
    def get_stats(self) -> dict:
        total = len(self._audit_log)
        blocked = sum(1 for a in self._audit_log if not a["success"])
        return {"total_ops": total, "blocked": blocked, "allowed_dirs": len(self.allowed_dirs)}
