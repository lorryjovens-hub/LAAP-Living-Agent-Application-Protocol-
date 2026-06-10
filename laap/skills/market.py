"""SkillMarket — 技能发现/安装/卸载/版本管理"""
from __future__ import annotations
import os, json, logging, shutil
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("skills.market")

@dataclass
class SkillPackage:
    name: str = ""
    version: str = "1.0"
    description: str = ""
    author: str = ""
    requires: List[str] = field(default_factory=list)
    category: str = "general"
    install_path: str = ""

class SkillMarket:
    def __init__(self, search_paths: List[str] = None):
        self.search_paths = search_paths or [
            os.path.expanduser("~/.laap/skills"),
            os.path.join(os.path.dirname(__file__), "builtin"),
        ]
        self._packages: Dict[str, SkillPackage] = {}
    
    def scan(self) -> List[SkillPackage]:
        packages = []
        for path in self.search_paths:
            if not os.path.isdir(path): continue
            for item in os.listdir(path):
                pkg_path = os.path.join(path, item)
                meta_file = os.path.join(pkg_path, "skill.json")
                if os.path.isdir(pkg_path) and os.path.exists(meta_file):
                    try:
                        with open(meta_file, 'r') as f:
                            meta = json.load(f)
                        pkg = SkillPackage(
                            name=meta.get("name", item),
                            version=meta.get("version", "1.0"),
                            description=meta.get("description", ""),
                            author=meta.get("author", ""),
                            requires=meta.get("requires", []),
                            category=meta.get("category", "general"),
                            install_path=pkg_path,
                        )
                        self._packages[pkg.name] = pkg
                        packages.append(pkg)
                    except: pass
        return packages
    
    def install(self, name: str, source_path: str) -> bool:
        target = os.path.join(os.path.expanduser("~/.laap/skills"), name)
        if os.path.exists(target):
            logger.warning(f"Skill {name} already installed")
            return False
        shutil.copytree(source_path, target)
        logger.info(f"Skill {name} installed")
        return True
    
    def uninstall(self, name: str) -> bool:
        target = os.path.join(os.path.expanduser("~/.laap/skills"), name)
        if os.path.exists(target):
            shutil.rmtree(target)
            self._packages.pop(name, None)
            return True
        return False
    
    def search(self, query: str) -> List[SkillPackage]:
        q = query.lower()
        return [p for p in self._packages.values()
                if q in p.name.lower() or q in p.description.lower()]
    
    def get_stats(self) -> dict:
        return {"packages": len(self._packages)}
