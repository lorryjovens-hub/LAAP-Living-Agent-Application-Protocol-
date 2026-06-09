"""
LAAP — Skills System
Load, manage, and execute skills — reusable capability modules.
Inspired by Hermes skills but designed for the Living Computation Paradigm.
"""

from __future__ import annotations
import importlib, json, logging, os, sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger("laap.skills")

SKILLS_DIR = Path.home() / ".laap" / "skills"
BUILTIN_SKILLS_DIR = Path(__file__).resolve().parent / "bundled"


@dataclass
class Skill:
    name: str
    description: str = ""
    version: str = "1.0"
    author: str = ""
    commands: Dict[str, Callable] = field(default_factory=dict)
    tools: List[Dict] = field(default_factory=list)
    category: str = "general"
    enabled: bool = True
    path: Optional[str] = None


class SkillManager:
    """Discover, load, and manage skills."""

    def __init__(self):
        self.skills: Dict[str, Skill] = {}
        self._discover()

    def _discover(self):
        """Scan skill directories."""
        # Built-in skills
        if BUILTIN_SKILLS_DIR.exists():
            for f in BUILTIN_SKILLS_DIR.glob("*.py"):
                self._load_skill_file(f, "builtin")
        # User skills
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        for f in SKILLS_DIR.glob("*.py"):
            self._load_skill_file(f, "user")

    def _load_skill_file(self, path: Path, source: str):
        name = path.stem
        if name.startswith("_"):
            return
        try:
            spec = importlib.util.spec_from_file_location(f"laap.skills.{name}", path)
            if spec and spec.loader:
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                skill = Skill(
                    name=name,
                    description=getattr(mod, "__description__", name),
                    version=getattr(mod, "__version__", "1.0"),
                    author=getattr(mod, "__author__", ""),
                    category=getattr(mod, "__category__", "general"),
                    path=str(path),
                )
                # Collect exported functions
                for attr in dir(mod):
                    if attr.startswith("skill_"):
                        skill.commands[attr[6:]] = getattr(mod, attr)
                    elif attr.startswith("tool_"):
                        skill.commands[attr[5:]] = getattr(mod, attr)
                self.skills[name] = skill
                logger.info("Skill loaded: %s (%s)", name, source)
        except Exception as e:
            logger.warning("Skill %s load failed: %s", name, e)

    def install(self, source: str) -> bool:
        """Install a skill from URL or file path."""
        import urllib.request, shutil
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        try:
            name = os.path.basename(source)
            if name.endswith(".py"):
                target = SKILLS_DIR / name
                if source.startswith(("http://", "https://")):
                    urllib.request.urlretrieve(source, target)
                else:
                    shutil.copy2(source, target)
                self._load_skill_file(target, "user")
                logger.info("Skill installed: %s", name)
                return True
        except Exception as e:
            logger.error("Skill install %s: %s", source, e)
        return False

    def run_command(self, skill_name: str, command: str, **kwargs) -> Any:
        """Execute a skill command."""
        skill = self.skills.get(skill_name)
        if not skill:
            return f"Unknown skill: {skill_name}"
        handler = skill.commands.get(command)
        if not handler:
            return f"Unknown command '{command}' in skill '{skill_name}'"
        try:
            return handler(**kwargs)
        except Exception as e:
            return f"Skill error: {e}"

    def call_tool(self, name: str, **kwargs) -> Optional[str]:
        """Call a tool across all skills."""
        for skill in self.skills.values():
            handler = skill.commands.get(f"tool_{name}")
            if handler:
                try:
                    return handler(**kwargs)
                except Exception as e:
                    return f"Tool error: {e}"
        return None

    def list(self, category: str = "") -> List[dict]:
        """List installed skills."""
        result = []
        for name, skill in self.skills.items():
            if category and skill.category != category:
                continue
            result.append({
                "name": name, "description": skill.description,
                "version": skill.version, "category": skill.category,
                "commands": list(skill.commands.keys()),
            })
        return result

    def uninstall(self, name: str) -> bool:
        """Remove a skill."""
        if name in self.skills:
            skill = self.skills[name]
            if skill.path:
                try:
                    os.remove(skill.path)
                except Exception:
                    pass
            del self.skills[name]
            return True
        return False


# Test skill template
SAMPLE_SKILL = '''"""
LAAP Skill: {name}
{description}
"""
__description__ = "{description}"
__version__ = "1.0"
__author__ = "LAAP"
__category__ = "{category}"

def skill_hello(**kwargs) -> str:
    """Hello world command."""
    return "Hello from {name} skill!"


def tool_{name}(action: str = "ping") -> str:
    """Tool available to the agent.

    Args:
        action: The action to perform
    """
    return f"{{action}} from {{name}}"
'''


def create_skill_template(name: str, description: str = "",
                          category: str = "general") -> str:
    """Generate a skill template file."""
    SKILLS_DIR.mkdir(parents=True, exist_ok=True)
    path = SKILLS_DIR / f"{name}.py"
    content = SAMPLE_SKILL.format(name=name, description=description or name,
                                  category=category)
    path.write_text(content, encoding="utf-8")
    logger.info("Skill template created: %s", path)
    return str(path)


# Global manager
skill_manager = SkillManager()
