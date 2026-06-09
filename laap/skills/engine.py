"""LAAP Skill Engine — Load, parse, discover, and execute skills.

A skill is a SKILL.md file with YAML frontmatter containing:
  name, description, version, platforms, tags, etc.
"""

from __future__ import annotations
import hashlib
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

logger = logging.getLogger("laap.skills.engine")


@dataclass
class Skill:
    """A loaded skill with parsed frontmatter and body."""
    name: str
    description: str = ""
    version: str = "1.0.0"
    body: str = ""
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    path: Optional[Path] = None
    platform: str = "all"
    tags: List[str] = field(default_factory=list)
    category: str = "general"
    author: str = ""
    enabled: bool = True
    loaded_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description[:120],
            "version": self.version,
            "category": self.category,
            "tags": self.tags,
            "platform": self.platform,
            "enabled": self.enabled,
            "body_size": len(self.body),
        }

    def to_short_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description[:80],
            "category": self.category,
        }


def parse_frontmatter(content: str) -> Tuple[Dict[str, Any], str]:
    """Parse YAML frontmatter from SKILL.md content.

    Returns (frontmatter_dict, body_string).
    Frontmatter is between --- delimiters at the start of the file.
    """
    content = content.lstrip("\ufeff")  # Strip BOM
    if not content.startswith("---"):
        return {}, content

    # Find closing ---
    end_idx = content.find("---", 3)
    if end_idx == -1:
        return {}, content

    yaml_str = content[3:end_idx].strip()
    body = content[end_idx + 3:].strip()

    try:
        frontmatter = yaml.safe_load(yaml_str) or {}
    except yaml.YAMLError as e:
        logger.warning(f"YAML parse error: {e}")
        frontmatter = {}

    return frontmatter, body


def _make_skill_name(name: str) -> str:
    """Normalize skill name to slug format."""
    name = name.lower().strip()
    name = re.sub(r"[^a-z0-9-]", "-", name)
    name = re.sub(r"-+", "-", name)
    return name.strip("-")


class SkillEngine:
    """Discovers, loads, and manages skills from skill directories."""

    def __init__(self, dirs: Optional[List[Path]] = None):
        self._skills: Dict[str, Skill] = {}
        self._dirs: List[Path] = []
        if dirs:
            for d in dirs:
                self.add_dir(d)

    def add_dir(self, path: Path):
        """Add a skill directory to scan."""
        path = Path(path).resolve()
        if path not in self._dirs and path.is_dir():
            self._dirs.append(path)
            logger.info(f"Skill dir added: {path}")

    def discover(self) -> List[str]:
        """Scan all skill directories and load skills.

        Returns list of skill names discovered.
        """
        found = []
        for d in self._dirs:
            if not d.is_dir():
                continue
            # Scan for SKILL.md files
            for skill_path in d.rglob("SKILL.md"):
                try:
                    skill = self._load_skill(skill_path)
                    if skill:
                        self._skills[skill.name] = skill
                        found.append(skill.name)
                except Exception as e:
                    logger.warning(f"Failed to load skill {skill_path}: {e}")
        logger.info(f"Discovered {len(found)} skills")
        return found

    def _load_skill(self, path: Path) -> Optional[Skill]:
        """Load a single skill from its SKILL.md file."""
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            return None

        frontmatter, body = parse_frontmatter(content)
        if not frontmatter or "name" not in frontmatter:
            return None

        name = _make_skill_name(frontmatter.get("name", path.parent.name))
        metadata = frontmatter.get("metadata", {})
        hermes_meta = metadata.get("hermes", {}) if isinstance(metadata, dict) else {}

        return Skill(
            name=name,
            description=frontmatter.get("description", ""),
            version=str(frontmatter.get("version", "1.0.0")),
            body=body,
            frontmatter=frontmatter,
            path=path,
            platform=frontmatter.get("platform", "all"),
            tags=hermes_meta.get("tags", []) if isinstance(hermes_meta, dict)
                  else frontmatter.get("tags", []),
            category=frontmatter.get("category", "general"),
            author=frontmatter.get("author", ""),
            enabled=frontmatter.get("enabled", True),
        )

    def get(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self._skills.get(_make_skill_name(name))

    def get_all(self) -> List[Skill]:
        """Get all loaded skills."""
        return list(self._skills.values())

    def get_by_category(self, category: str) -> List[Skill]:
        """Get skills in a category."""
        return [s for s in self._skills.values() if s.category == category]

    def search(self, query: str) -> List[Skill]:
        """Search skills by name, description, or tags."""
        q = query.lower()
        results = []
        for s in self._skills.values():
            if (q in s.name.lower() or q in s.description.lower()
                    or any(q in t.lower() for t in s.tags)):
                results.append(s)
        return results

    def remove(self, name: str) -> bool:
        """Remove a skill from the loaded set."""
        key = _make_skill_name(name)
        return self._skills.pop(key, None) is not None

    def reload(self) -> int:
        """Reload all skills from directories."""
        self._skills.clear()
        return len(self.discover())

    def count(self) -> int:
        return len(self._skills)

    def build_system_prompt(self) -> str:
        """Build a system prompt block listing available skills."""
        if not self._skills:
            return ""
        skills_list = "\n".join(
            f"  /{s.name} — {s.description[:80]}"
            for s in sorted(self._skills.values(), key=lambda x: x.name)
        )
        return f"\n[Available Skills]\nUse /skill-name to invoke a skill.\n{skills_list}"
