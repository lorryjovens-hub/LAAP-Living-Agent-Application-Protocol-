"""
LAAP — Skill Curator
Extracts reusable skills from agent conversation turns.
Inspired by the Hermes Curator pattern: agent creates skills from experience.
"""
from __future__ import annotations
import json, logging, re, hashlib
from typing import Any, Dict, List, Optional

from laap.memory.hierarchical import Skill

logger = logging.getLogger("laap.skills.curator")

TOOL_PATTERNS = [
    (r"grep.*-r.*\.", "search_code", "Search codebase with pattern"),
    (r"find.*-name", "find_files", "Find files by name pattern"),
    (r"python.*-c", "run_python", "Execute Python code"),
    (r"git\s+(\w+)", "git_op", "Git operation: {}"),
    (r"docker\s+(\w+)", "docker_op", "Docker operation: {}"),
    (r"pip\s+install", "pip_install", "Install Python package"),
    (r"npm\s+(\w+)", "npm_op", "NPM operation: {}"),
    (r"ls\s+", "list_dir", "List directory contents"),
    (r"mkdir\s+", "make_dir", "Create directory"),
    (r"curl\s+", "http_request", "Make HTTP request"),
]


class Curator:
    """Skill curator — observes agent behavior and creates reusable skills."""

    def __init__(self):
        self.skills: List[Skill] = []

    def extract_skill(self, turns: List[Dict], agent_name: str = "") -> Optional[Skill]:
        if not turns:
            return None
        tool_turn = None
        for t in turns:
            if t.get("role") == "assistant" and t.get("tool_calls"):
                tool_turn = t
                break
        if not tool_turn:
            return None
        user_prompt = ""
        for t in turns:
            if t.get("role") == "user":
                user_prompt = t.get("content", "")
                break
        for tc in tool_turn.get("tool_calls", []):
            func_name = tc.get("function", {}).get("name", "")
            func_args = tc.get("function", {}).get("arguments", "{}")
            if isinstance(func_args, str):
                try:
                    func_args = json.loads(func_args)
                except json.JSONDecodeError:
                    func_args = {}
            command = func_args.get("command", "") if isinstance(func_args, dict) else ""
            for pattern, skill_name_fmt, desc_fmt in TOOL_PATTERNS:
                m = re.search(pattern, command)
                if m:
                    op_name = m.group(1) if m.lastindex and m.groups() else ""
                    skill_name = skill_name_fmt.format(op_name) if "{}" in skill_name_fmt else skill_name_fmt
                    description = desc_fmt.format(op_name) if "{}" in desc_fmt else desc_fmt
                    skill = Skill(name=skill_name, description=f"{description}. Prompt: {user_prompt[:80]}",
                                  proficiency=0.0, code=f"Tool: {func_name}, Args: {json.dumps(func_args)[:200]}")
                    self.skills.append(skill)
                    logger.info(f"Extracted skill: {skill_name}")
                    return skill
        return None

    def register_skill_on_agent(self, skill: Skill, agent) -> bool:
        try:
            agent.memory.register_skill(name=skill.name, description=skill.description, code=skill.code)
            return True
        except Exception as e:
            logger.error(f"Failed to register skill: {e}")
            return False

    def collect_skills(self) -> List[Skill]:
        return self.skills
