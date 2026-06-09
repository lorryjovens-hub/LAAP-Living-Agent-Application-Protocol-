"""LAAP Skills System — Load, manage, and invoke skills."""

from laap.skills.engine import SkillEngine, Skill, parse_frontmatter
from laap.skills.manager import SkillManager
from laap.skills.template import preprocess, substitute_vars, expand_inline_shell

__all__ = [
    "SkillEngine", "Skill", "parse_frontmatter",
    "SkillManager",
    "preprocess", "substitute_vars", "expand_inline_shell",
]
