"""Skill Template — 技能创建模板"""
from __future__ import annotations
import os, json, logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("skills.template")

SKILL_CODE = '"""%s - %s"""\ndef init_plugin(agent=None, config=None):\n    return {"status": "ok"}\n\ndef shutdown():\n    pass\n'

class SkillTemplate:
    @staticmethod
    def create(name, description, output_dir):
        skill_dir = os.path.join(output_dir, name)
        os.makedirs(skill_dir, exist_ok=True)
        meta = {"name": name, "version": "1.0", "description": description, "category": "general"}
        with open(os.path.join(skill_dir, "skill.json"), "w") as f:
            json.dump(meta, f, indent=2)
        with open(os.path.join(skill_dir, "__init__.py"), "w") as f:
            f.write(SKILL_CODE % (name, description))
        return skill_dir
    
    @staticmethod
    def list_templates():
        return [{"name": "basic", "description": "Basic template"}]
