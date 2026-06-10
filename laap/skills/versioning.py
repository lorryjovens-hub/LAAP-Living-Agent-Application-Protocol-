"""Skill Versioning"""
from __future__ import annotations
import re
from dataclasses import dataclass
from typing import Optional

@dataclass
class Version:
    major: int = 1
    minor: int = 0
    patch: int = 0
    
    @classmethod
    def parse(cls, s: str) -> Optional["Version"]:
        m = re.match(r"(\d+)\.(\d+)\.?(\d*)?", s)
        if m:
            return cls(int(m.group(1)), int(m.group(2)), int(m.group(3) or "0"))
        return None
    
    def __str__(self):
        return f"{self.major}.{self.minor}.{self.patch}"
    
    def __lt__(self, other):
        return (self.major, self.minor, self.patch) < (other.major, other.minor, other.patch)
    
    def compatible_with(self, other: "Version") -> bool:
        return self.major == other.major

def check_compatibility(v1: str, v2: str) -> bool:
    a, b = Version.parse(v1), Version.parse(v2)
    return a and b and a.compatible_with(b)
