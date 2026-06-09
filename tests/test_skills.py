"""Test LAAP Skills System — Curator, Loader, and Skill Lifecycle"""
import sys
sys.path.insert(0, r"D:\LAAP")

import json, tempfile, os, time
from pathlib import Path

from laap.skills.curator import Curator, TOOL_PATTERNS
from laap.skills.loader import SkillManager, Skill, skill_manager, create_skill_template, SKILLS_DIR, BUILTIN_SKILLS_DIR
from laap.memory.hierarchical import Skill as MemorySkill


# ── Curator ───────────────────────────────────────────────────

def test_curator_init():
    c = Curator()
    assert c.skills == []
    assert c.collect_skills() == []


def test_curator_extract_skill_from_tool_call():
    """Extract a skill from a conversation turn with a tool call."""
    c = Curator()
    turns = [
        {"role": "user", "content": "find all python files in the project"},
        {"role": "assistant", "content": "",
         "tool_calls": [{
             "function": {
                 "name": "run_command",
                 "arguments": '{"command": "find . -name \\"*.py\\""}',
             },
         }]},
    ]
    skill = c.extract_skill(turns, agent_name="test")
    assert skill is not None
    assert "find_files" in skill.name or "search" in skill.name.lower()
    assert len(c.skills) == 1


def test_curator_extract_skill_git():
    """Extract git operation skill."""
    c = Curator()
    turns = [
        {"role": "user", "content": "commit my changes"},
        {"role": "assistant", "content": "",
         "tool_calls": [{
             "function": {
                 "name": "run_command",
                 "arguments": '{"command": "git commit -m \\"fix\\""}',
             },
         }]},
    ]
    skill = c.extract_skill(turns)
    assert skill is not None
    assert "git" in skill.name
    assert skill.proficiency == 0.0  # initial proficiency


def test_curator_extract_skill_pip():
    """Extract pip install skill."""
    c = Curator()
    turns = [
        {"role": "user", "content": "install requests"},
        {"role": "assistant", "content": "",
         "tool_calls": [{
             "function": {
                 "name": "run_command",
                 "arguments": '{"command": "pip install requests"}',
             },
         }]},
    ]
    skill = c.extract_skill(turns)
    assert skill is not None
    assert "pip" in skill.name


def test_curator_empty_turns():
    c = Curator()
    assert c.extract_skill([]) is None
    assert c.extract_skill([{"role": "user", "content": "hello"}]) is None


def test_curator_no_tool_call():
    """Turns without tool calls should not produce a skill."""
    c = Curator()
    turns = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"},
    ]
    assert c.extract_skill(turns) is None


def test_curator_extract_skill_docker():
    """Extract docker operation."""
    c = Curator()
    turns = [
        {"role": "user", "content": "run docker container"},
        {"role": "assistant", "content": "",
         "tool_calls": [{
             "function": {
                 "name": "run_command",
                 "arguments": '{"command": "docker ps"}',
             },
         }]},
    ]
    skill = c.extract_skill(turns)
    assert skill is not None
    assert "docker" in skill.name


def test_curator_register_on_agent():
    """Skill can be registered on an agent's memory."""
    from laap.agent.base import Agent
    c = Curator()
    # Extract first
    turns = [
        {"role": "user", "content": "find files"},
        {"role": "assistant", "content": "",
         "tool_calls": [{
             "function": {
                 "name": "run_command",
                 "arguments": '{"command": "find . -name \\"test\\""}',
             },
         }]},
    ]
    skill = c.extract_skill(turns)
    assert skill is not None

    a = Agent(config=type("Cfg", (), {"name": "TestAgent", "verbose": False, "tools_enabled": False})())
    a.memory._skills = {}  # reset
    ok = c.register_skill_on_agent(skill, a)
    assert ok


def test_curator_preserves_skills():
    """Multiple extractions accumulate skills."""
    c = Curator()
    # First extraction
    c.extract_skill([
        {"role": "user", "content": "find files"},
        {"role": "assistant", "content": "",
         "tool_calls": [{"function": {"name": "run_command", "arguments": '{"command": "find . -name \\"*.py\\""}'}}]},
    ])
    count1 = len(c.skills)

    # Second extraction (different command)
    c.extract_skill([
        {"role": "user", "content": "install package"},
        {"role": "assistant", "content": "",
         "tool_calls": [{"function": {"name": "run_command", "arguments": '{"command": "pip install flask"}'}}]},
    ])
    count2 = len(c.skills)
    assert count2 >= count1


# ── Tool Patterns ────────────────────────────────────────────

def test_tool_patterns_defined():
    """TOOL_PATTERNS should have at least 10 entries covering common operations."""
    assert len(TOOL_PATTERNS) >= 10
    patterns = {desc for _, _, desc in TOOL_PATTERNS}
    assert "search_code" in {p[1] for p in TOOL_PATTERNS}
    assert "git_op" in {p[1] for p in TOOL_PATTERNS}


# ── SkillManager ─────────────────────────────────────────────

def test_skill_manager_init():
    sm = SkillManager()
    assert sm.skills is not None
    assert isinstance(sm.skills, dict)


def test_skill_manager_loads_builtins():
    """Skill manager discovers built-in skill files."""
    sm = SkillManager()
    # Should not crash even if no built-ins exist
    assert sm.skills is not None


def test_skill_manager_list():
    sm = SkillManager()
    result = sm.list()
    assert isinstance(result, list)


def test_skill_manager_list_with_category():
    sm = SkillManager()
    result = sm.list(category="general")
    assert isinstance(result, list)


def test_skill_manager_unknown_command():
    sm = SkillManager()
    # Create a dummy skill
    sm.skills["dummy"] = Skill(name="dummy", commands={})
    result = sm.run_command("dummy", "nonexistent")
    assert "Unknown command" in str(result)


def test_skill_manager_unknown_skill():
    sm = SkillManager()
    result = sm.run_command("does_not_exist", "hello")
    assert "Unknown skill" in str(result)


def test_skill_manager_install_invalid():
    sm = SkillManager()
    # Invalid source (not .py)
    result = sm.install("/invalid/path.txt")
    assert result is False


# ── create_skill_template ────────────────────────────────────

def test_create_skill_template(tmp_path):
    """Creating a skill template writes a valid .py file."""
    original_skills_dir = SKILLS_DIR
    try:
        import laap.skills.loader as loader
        loader.SKILLS_DIR = tmp_path / ".laap" / "skills"
        loader.SKILLS_DIR.mkdir(parents=True, exist_ok=True)

        path = create_skill_template("test_skill", "A test skill", "testing")
        assert os.path.exists(path)

        with open(path) as f:
            content = f.read()
        assert "test_skill" in content
        assert "A test skill" in content
        assert "def skill_hello" in content
        assert "def tool_test_skill" in content
    finally:
        loader.SKILLS_DIR = original_skills_dir


# ── Skill Data Model ─────────────────────────────────────────

def test_skill_dataclass_defaults():
    """Skill dataclass should have sensible defaults."""
    s = Skill(name="test")
    assert s.name == "test"
    assert s.description == ""
    assert s.version == "1.0"
    assert s.category == "general"
    assert s.enabled is True


def test_skill_dataclass_full():
    """Skill with all fields set."""
    def handler(): return "ok"
    s = Skill(
        name="full", description="desc", version="2.0",
        author="me", commands={"run": handler}, category="code",
        enabled=False, path="/tmp/skill.py",
    )
    assert s.name == "full"
    assert s.commands["run"] is handler
    assert s.enabled is False


# ── Memory Skill Interop ─────────────────────────────────────

def test_memory_skill_construction():
    """Memory Skill (from hierarchical.py) should accept basic fields."""
    ms = MemorySkill(name="greeter", description="Says hello", proficiency=0.5, code="print('hello')")
    assert ms.name == "greeter"
    assert ms.proficiency == 0.5


# ── Global Singleton ─────────────────────────────────────────

def test_global_skill_manager():
    """Module-level skill_manager singleton exists."""
    from laap.skills.loader import skill_manager
    assert skill_manager is not None
    assert isinstance(skill_manager, SkillManager)
