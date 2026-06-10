"""Signature Database — 威胁特征库"""
from __future__ import annotations
import time, json, logging, hashlib, threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("security.immune.signature_db")

@dataclass
class ThreatSignature:
    id: str = ""
    name: str = ""
    pattern: str = ""
    pattern_type: str = "string"
    severity: str = "medium"
    category: str = ""
    description: str = ""
    created_at: float = field(default_factory=time.time)
    references: List[str] = field(default_factory=list)

class SignatureDatabase:
    def __init__(self):
        self._signatures: Dict[str, ThreatSignature] = {}
        self._lock = threading.RLock()
        self._init_defaults()
    def _init_defaults(self):
        defaults = [
            ThreatSignature(id="sig_001", name="sql_injection", pattern="' OR 1=1", severity="high", category="injection"),
            ThreatSignature(id="sig_002", name="path_traversal", pattern="../", severity="high", category="path"),
            ThreatSignature(id="sig_003", name="xss_script", pattern="<script>", severity="high", category="xss"),
            ThreatSignature(id="sig_004", name="command_injection", pattern="&&", severity="high", category="injection"),
            ThreatSignature(id="sig_005", name="sensitive_data", pattern="sk-", severity="medium", category="leakage"),
        ]
        for sig in defaults:
            self._signatures[sig.id] = sig
    def add(self, signature: ThreatSignature):
        with self._lock:
            self._signatures[signature.id] = signature
    def match(self, data: str) -> List[ThreatSignature]:
        matches = []
        with self._lock:
            for sig in self._signatures.values():
                if sig.pattern in data:
                    matches.append(sig)
        return matches
    def get_by_severity(self, severity: str) -> List[ThreatSignature]:
        return [s for s in self._signatures.values() if s.severity == severity]
    def count(self) -> int:
        return len(self._signatures)
