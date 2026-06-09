"""
LAAP — Growth & Learning System
Continuous learning through experience consolidation, skill acquisition,
and behavioral refinement. The agent learns from every interaction.

Key concepts:
  - Experience: a (context, action, outcome, success) tuple
  - Pattern: recurring experience → generalized knowledge
  - Skill: procedural knowledge derived from successful patterns
  - Consolidation: periodic pattern discovery across experiences
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from collections import defaultdict
import json, logging, os, time, threading
import numpy as np

logger = logging.getLogger("laap.growth")


@dataclass
class Experience:
    """A single experience entry."""
    context: str
    action: str
    outcome: str
    success: bool
    pattern: str = ""
    timestamp: float = field(default_factory=time.time)
    reinforcement: int = 1
    pattern_id: str = ""

    def to_dict(self) -> dict:
        return {"context": self.context[:60], "action": self.action[:40],
                "outcome": self.outcome[:60], "success": self.success,
                "pattern": self.pattern[:40], "reinforcement": self.reinforcement}

    @classmethod
    def from_turn(cls, context: str, action: str, outcome: str,
                  success: float) -> "Experience":
        """Create an experience from an agent turn."""
        return cls(
            context=context,
            action=action,
            outcome=outcome,
            success=success > 0.5,
            pattern=cls._extract_pattern(context, action),
        )

    @staticmethod
    def _extract_pattern(context: str, action: str) -> str:
        """Extract a generalizable pattern from context + action."""
        # Simple pattern extraction: remove specific values
        import re
        ctx = re.sub(r'\d+\.?\d*', 'N', context[:80])
        act = action[:30]
        return f"{ctx[:40]} -> {act}"


@dataclass
class GeneralizedPattern:
    """A pattern learned across multiple experiences."""
    description: str
    success_rate: float = 0.0
    total_attempts: int = 0
    successful_attempts: int = 0
    examples: List[str] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    last_applied: float = 0.0
    abstraction_level: int = 0  # 0=concrete, 1=abstracted, 2=generalized

    def to_dict(self) -> dict:
        return {"description": self.description[:60], "success_rate": round(self.success_rate, 2),
                "total": self.total_attempts, "examples": len(self.examples)}


@dataclass
class AcquiredSkill:
    """A skill the agent has learned."""
    name: str
    description: str = ""
    trigger_pattern: str = ""  # When to use this skill
    steps: List[str] = field(default_factory=list)
    proficiency: float = 0.0  # 0-1
    source: str = "experience"  # experience, tool, builtin, transfer
    created_at: float = field(default_factory=time.time)
    used_count: int = 0

    def to_dict(self) -> dict:
        return {"name": self.name, "proficiency": round(self.proficiency, 2),
                "steps": len(self.steps), "used": self.used_count}


class GrowthSystem:
    """Continuous learning system — experiences → patterns → skills.

    The growth system is the agent's long-term learning mechanism.
    Every turn produces an experience. Experiences are consolidated
    into patterns. Successful patterns become skills.
    """

    def __init__(self, store_path: str = ""):
        self.store_path = store_path or os.path.expanduser("~/.laap/growth/")
        os.makedirs(self.store_path, exist_ok=True)

        self.experiences: List[Experience] = []
        self.patterns: Dict[str, GeneralizedPattern] = {}
        self.skills: Dict[str, AcquiredSkill] = {}
        self._lock = threading.Lock()
        self._save_timer: float = time.time()
        self._consolidation_interval = 50  # Consolidate every N experiences
        self._load()

    # ── Recording ──

    def record_turn(self, context: str, action: str, outcome: str,
                    success: float, pattern_hint: str = "") -> Experience:
        """Record an experience from a turn."""
        exp = Experience.from_turn(context, action, outcome, success)
        if pattern_hint:
            exp.pattern = pattern_hint

        with self._lock:
            # Check for reinforcement of existing pattern
            for existing in self.experiences:
                if existing.pattern == exp.pattern and existing.context[:30] == exp.context[:30]:
                    existing.reinforcement += 1
                    existing.success = existing.success or exp.success
                    self._maybe_save()
                    return existing

            self.experiences.append(exp)

            # Trigger consolidation periodically
            if len(self.experiences) % self._consolidation_interval == 0:
                self.consolidate()

            self._maybe_save()
        return exp

    def record_reflection(self, observation: str, hypothesis: str,
                          outcome: str, reward_delta: float):
        """Record a self-reflection as an experience."""
        exp = Experience(
            context=f"Reflection: {observation}",
            action=f"Hypothesis: {hypothesis}",
            outcome=outcome,
            success=reward_delta > 0,
            pattern=f"self_reflection_{observation[:40]}",
        )
        with self._lock:
            self.experiences.append(exp)
            if len(self.experiences) % self._consolidation_interval == 0:
                self.consolidate()
            self._maybe_save()

    # ── Consolidation ──

    def consolidate(self):
        """Core growth mechanism: find patterns across experiences."""
        with self._lock:
            if len(self.experiences) < 5:
                return

            # Group by pattern
            pattern_groups: Dict[str, List[Experience]] = defaultdict(list)
            for exp in self.experiences:
                pattern_groups[exp.pattern].append(exp)

            consolidations = []
            for pattern, group in pattern_groups.items():
                if not pattern:
                    continue
                successes = sum(1 for e in group if e.success)
                total = len(group)
                rate = successes / total if total > 0 else 0

                if pattern in self.patterns:
                    p = self.patterns[pattern]
                    p.total_attempts = total
                    p.successful_attempts = successes
                    p.success_rate = rate
                    p.last_applied = time.time()
                else:
                    self.patterns[pattern] = GeneralizedPattern(
                        description=pattern,
                        success_rate=rate,
                        total_attempts=total,
                        successful_attempts=successes,
                        examples=[e.context[:40] for e in group[:5]],
                    )

                # Promote well-learned patterns to skills
                if rate > 0.7 and total >= 5 and pattern not in self.skills:
                    self._promote_to_skill(pattern, group)
                    consolidations.append(f"New skill: {pattern}")

            # Cross-pattern generalization
            self._generalize_patterns()

            logger.info("Consolidated %d experiences -> %d patterns, %d skills",
                        len(self.experiences), len(self.patterns), len(self.skills))
            return consolidations

    def _promote_to_skill(self, pattern: str, examples: List[Experience]):
        """Promote a successful pattern to a learned skill."""
        # Extract common steps from successful examples
        successful = [e for e in examples if e.success]
        if len(successful) < 3:
            return

        common_outcomes = list(set(e.outcome[:40] for e in successful))
        skill = AcquiredSkill(
            name=f"learned_{len(self.skills) + 1}",
            description=pattern[:100],
            trigger_pattern=pattern,
            steps=common_outcomes[:5],
            proficiency=min(1.0, len(successful) / 10.0),
            source="experience",
        )
        self.skills[skill.name] = skill

    def _generalize_patterns(self):
        """Cross-pattern generalization: find meta-patterns."""
        # Group highly-related patterns
        pattern_items = list(self.patterns.items())
        for i, (p1_name, p1) in enumerate(pattern_items):
            for p2_name, p2 in pattern_items[i+1:]:
                if p1.total_attempts >= 3 and p2.total_attempts >= 3:
                    # Check if patterns share keywords
                    p1_words = set(p1_name.lower().split())
                    p2_words = set(p2_name.lower().split())
                    overlap = p1_words & p2_words
                    if len(overlap) >= 2:
                        # These patterns are related — note for future abstraction
                        pass

    # ── Query ──

    def get_relevant_experiences(self, context: str, top_k: int = 5) -> List[Experience]:
        """Get experiences relevant to current context."""
        context_lower = context.lower()
        scored = []
        for exp in self.experiences:
            score = 0.0
            if context_lower in exp.context.lower():
                score += 0.3
            if context_lower in exp.pattern.lower():
                score += 0.2
            score += exp.reinforcement * 0.05
            score += 0.5 if exp.success else 0.0
            scored.append((score, exp))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in scored[:top_k]]

    def get_relevant_skills(self, context: str, top_k: int = 3) -> List[AcquiredSkill]:
        """Get skills relevant to current context."""
        ctx = context.lower()
        scored = []
        for skill in self.skills.values():
            score = 0.0
            if skill.trigger_pattern and ctx in skill.trigger_pattern.lower():
                score += 0.4
            score += skill.proficiency * 0.3
            scored.append((score, skill))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [s for _, s in scored[:top_k]]

    def get_stats(self) -> dict:
        return {
            "experiences": len(self.experiences),
            "patterns": len(self.patterns),
            "skills": len(self.skills),
            "consolidations": len(self.patterns),
            "top_patterns": [p.to_dict() for p in
                          sorted(self.patterns.values(), key=lambda x: x.total_attempts, reverse=True)[:5]],
            "top_skills": [s.to_dict() for s in
                         sorted(self.skills.values(), key=lambda x: x.proficiency, reverse=True)[:5]],
        }

    # ── Persistence ──

    def _maybe_save(self):
        if time.time() - self._save_timer > 30:
            self._save()
            self._save_timer = time.time()

    def _save(self):
        """Persist growth data."""
        with self._lock:
            data = {
                "experiences": [{
                    "context": e.context[:200], "action": e.action[:100],
                    "outcome": e.outcome[:200], "success": e.success,
                    "pattern": e.pattern, "reinforcement": e.reinforcement,
                    "timestamp": e.timestamp,
                } for e in self.experiences[-500:]],  # Keep last 500
                "patterns": {k: {"description": v.description[:200],
                                 "success_rate": v.success_rate,
                                 "total": v.total_attempts,
                                 "successful": v.successful_attempts,
                                 "abstraction_level": v.abstraction_level}
                            for k, v in self.patterns.items()},
                "skills": {k: {"name": v.name, "description": v.description[:200],
                               "trigger": v.trigger_pattern, "proficiency": v.proficiency,
                               "steps": v.steps[:5], "used": v.used_count}
                          for k, v in self.skills.items()},
            }
            path = os.path.join(self.store_path, "growth.json")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self):
        """Load persisted growth data."""
        path = os.path.join(self.store_path, "growth.json")
        if not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for ed in data.get("experiences", []):
                self.experiences.append(Experience(**ed))
            for k, v in data.get("patterns", {}).items():
                self.patterns[k] = GeneralizedPattern(**v)
            for k, v in data.get("skills", {}).items():
                self.skills[k] = AcquiredSkill(**v)
            logger.info("Growth: loaded %d experiences, %d patterns, %d skills",
                        len(self.experiences), len(self.patterns), len(self.skills))
        except Exception as e:
            logger.warning("Growth load: %s", e)


# Global growth system
growth_system = GrowthSystem()
