"""LAAP Skill Manager"""
from __future__ import annotations
import logging, re, shutil
from pathlib import Path
from typing import Any, Dict, List, Optional
from laap.skills.engine import SkillEngine, Skill

logger = logging.getLogger("laap.skills.manager")
_DEFAULT_SKILLS_DIR = Path.home() / ".laap" / "skills"


def slug(name: str) -> str:
    n = name.lower().strip()
    n = re.sub(r"[^a-z0-9-]", "-", n)
    return re.sub(r"-+", "-", n).strip("-")


class SkillManager:
    def __init__(self):
        self.engine = SkillEngine()
        self._init_dirs()

    def _init_dirs(self):
        builtin = Path(__file__).resolve().parent / "builtin"
        if builtin.is_dir():
            self.engine.add_dir(builtin)
        _DEFAULT_SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        self.engine.add_dir(_DEFAULT_SKILLS_DIR)
        self.engine.discover()

    def list_skills(self, category: Optional[str] = None) -> List[Dict]:
        skills = self.engine.get_by_category(category) if category else self.engine.get_all()
        return [s.to_dict() for s in sorted(skills, key=lambda x: x.name)]

    def get_skill(self, name: str) -> Optional[Skill]:
        return self.engine.get(name)

    def view_skill(self, name: str) -> Optional[str]:
        skill = self.engine.get(name)
        if not skill or not skill.path:
            return None
        if skill.path.exists():
            return skill.path.read_text(encoding="utf-8")
        return None

    def install_from_path(self, name: str, source_path: Path) -> bool:
        target = _DEFAULT_SKILLS_DIR / slug(name)
        target.mkdir(parents=True, exist_ok=True)
        src = Path(source_path)
        if src.is_file():
            shutil.copy2(str(src), str(target / "SKILL.md"))
        elif src.is_dir():
            md = src / "SKILL.md"
            if md.exists():
                shutil.copy2(str(md), str(target / "SKILL.md"))
            for f in src.glob("*"):
                if f.name not in ("SKILL.md", "__pycache__"):
                    d = target / f.name
                    if f.is_file():
                        shutil.copy2(str(f), str(d))
                    elif f.is_dir():
                        shutil.copytree(str(f), str(d), dirs_exist_ok=True)
        else:
            return False
        self.engine.reload()
        return self.engine.get(name) is not None

    def remove_skill(self, name: str) -> bool:
        return self.engine.remove(name)

    def build_prompt_block(self) -> str:
        return self.engine.build_system_prompt()
