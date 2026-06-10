"""SkillStore — 技能持久化"""
from __future__ import annotations
import os, json, logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("skills.store")

class SkillStore:
    def __init__(self, base_path: str = ""):
        self.base_path = base_path or os.path.expanduser("~/.laap/skills")
        os.makedirs(self.base_path, exist_ok=True)
    
    def save_meta(self, name: str, meta: Dict):
        path = os.path.join(self.base_path, name, "skill.json")
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, indent=2, ensure_ascii=False)
    
    def load_meta(self, name: str) -> Optional[Dict]:
        path = os.path.join(self.base_path, name, "skill.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None
    
    def save_index(self, skills: List[Dict]):
        path = os.path.join(self.base_path, "index.json")
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(skills, f, indent=2, ensure_ascii=False)
    
    def load_index(self) -> List[Dict]:
        path = os.path.join(self.base_path, "index.json")
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    
    def export_skill(self, name: str, export_path: str) -> bool:
        src = os.path.join(self.base_path, name)
        if os.path.exists(src):
            import shutil
            shutil.make_archive(export_path, 'zip', src)
            return True
        return False
    
    def import_skill(self, import_path: str) -> bool:
        import zipfile
        name = os.path.splitext(os.path.basename(import_path))[0]
        dst = os.path.join(self.base_path, name)
        with zipfile.ZipFile(import_path, 'r') as zf:
            zf.extractall(dst)
        return True
