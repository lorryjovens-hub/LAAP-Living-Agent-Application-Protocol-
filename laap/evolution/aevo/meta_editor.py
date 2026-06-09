"""AEvo — Meta-Agent 编辑器

两阶段核心: Meta-Editing Phase (本模块) ↔ Evolution Segment (harness.py)
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
import json, logging

logger = logging.getLogger("laap.evolution.aevo.editor")


class EditTarget(Enum):
    PROCEDURE = "procedure"
    CONTEXT = "context"
    PARAMETERS = "parameters"
    SKILLS = "skills"
    GOALS = "goals"


@dataclass
class EditPlan:
    target: EditTarget = EditTarget.PARAMETERS
    hypothesis: str = ""
    changes: Dict[str, Any] = field(default_factory=dict)
    focus_area: str = "balance"
    iterations: int = 20
    confidence: float = 0.5
    reasoning: str = ""


class MetaEditor:
    """AEvo Meta-Agent 编辑器 — 观察→分析→编辑→RunPlan"""

    def __init__(self, llm_provider=None, edit_interval: int = 20):
        self.llm = llm_provider
        self.edit_interval = edit_interval
        self.edit_history: List[EditPlan] = []
        self.last_edit_step = 0

    def should_edit(self, current_step: int) -> bool:
        return (current_step - self.last_edit_step) >= self.edit_interval

    def meta_edit(self, agent, history) -> Optional["RunPlan"]:
        from laap.evolution.aevo.harness import RunPlan
        context = self._collect_context(agent, history)
        logger.info(f"MetaEditor: analyzing at step {context['step']}")
        plan = self._llm_analyze(context) if self.llm else self._rule_analyze(context)
        if plan is None:
            return None
        self._apply_edit(agent, plan)
        self.edit_history.append(plan)
        self.last_edit_step = getattr(agent, 'step_count', 0)
        return RunPlan(
            iterations=plan.iterations,
            focus_area=plan.focus_area,
            parameter_overrides=plan.changes if plan.target == EditTarget.PARAMETERS else {},
        )

    def _collect_context(self, agent, history) -> dict:
        ctx = {
            "step": getattr(agent, 'step_count', 0),
            "fitness_history": history.fitness_trend(),
            "failure_patterns": history.failure_patterns(),
            "exploration_rate": getattr(agent.config, 'exploration_rate', 0.2),
            "learning_rate": getattr(agent.config, 'learning_rate', 0.1),
            "needs": {}, "emotion": {},
            "adoption_rate": 0.0, "noise": 0.0, "meaning": 0.0,
            "skill_count": 0,
        }
        if hasattr(agent, 'needs') and agent.needs:
            for nt, need in agent.needs.needs.items():
                ctx["needs"][nt.value] = round(need.current_level, 3)
        if hasattr(agent, 'emotion_gradient'):
            eg = agent.emotion_gradient
            ctx["emotion"] = {"valence": round(eg.state.valence, 3),
                              "confidence": round(eg.state.confidence, 3)}
        if hasattr(agent, 'memory'):
            ctx["skill_count"] = len(agent.memory.skills)
        if hasattr(agent, 'rsi_engine'):
            ctx["adoption_rate"] = round(agent.rsi_engine.adoption_rate(), 3)
            ctx["noise"] = round(agent.rsi_engine.noise_level, 4)
        return ctx

    def _context_summary(self, ctx: dict) -> str:
        lines = ["=== Evolution Context ==="]
        lines.append(f"Step: {ctx['step']}")
        fh = ctx.get("fitness_history", [])
        if len(fh) >= 5:
            slope = fh[-1] - fh[0]
            trend = "↑ rising" if slope > 0.02 else ("↓ declining" if slope < -0.02 else "→ plateau")
            lines.append(f"Fitness: {trend} ({slope:+.4f})")
        lines.append(f"Exploration: {ctx['exploration_rate']:.3f}, LR: {ctx['learning_rate']:.3f}")
        if ctx["needs"]:
            lines.append(f"Needs: {ctx['needs']}")
        if ctx["emotion"]:
            lines.append(f"Emotion: {ctx['emotion']}")
        if ctx["failure_patterns"]:
            lines.append(f"Failures: {ctx['failure_patterns']}")
        lines.append(f"Skills: {ctx['skill_count']}, Adoption: {ctx['adoption_rate']}")
        return "\n".join(lines)

    def _llm_analyze(self, context: dict) -> Optional[EditPlan]:
        try:
            from laap.llm.provider import Message
            prompt = (
                "You are an AI evolution engineer. Propose ONE edit to improve "
                "the agent's evolution process.\n\n"
                f"{self._context_summary(context)}\n\n"
                "Output EXACT format:\n"
                "OBSERVATION: <notice>\n"
                "HYPOTHESIS: <what to change and why>\n"
                "EDIT_TARGET: procedure|context|parameters|skills|goals\n"
                "CHANGES: <JSON>\nFOCUS_AREA: explore|exploit|balance|skills|needs\n"
                "ITERATIONS: <10-50>\nCONFIDENCE: <0.0-1.0>"
            )
            messages = [Message.system("Output in the specified format only."), Message.user(prompt)]
            content = ""
            for event in self.llm.chat_stream(messages):
                if event.type == "token":
                    content += event.content
            return self._parse_llm_response(content)
        except Exception as e:
            logger.warning(f"LLM analyze failed: {e}")
            return self._rule_analyze(context)

    def _parse_llm_response(self, content: str) -> Optional[EditPlan]:
        plan = EditPlan()
        changes_text = "{}"
        for line in content.strip().split("\n"):
            line = line.strip()
            if line.startswith("HYPOTHESIS:"):
                plan.hypothesis = line[11:].strip()[:200]
            elif line.startswith("EDIT_TARGET:"):
                t = line[12:].strip().lower()
                for et in EditTarget:
                    if et.value == t:
                        plan.target = et; break
            elif line.startswith("CHANGES:"):
                changes_text = line[8:].strip()
            elif line.startswith("FOCUS_AREA:"):
                plan.focus_area = line[11:].strip()
            elif line.startswith("ITERATIONS:"):
                try: plan.iterations = max(5, min(100, int(line[11:].strip())))
                except ValueError: pass
            elif line.startswith("CONFIDENCE:"):
                try: plan.confidence = float(line[11:].strip().split()[0])
                except (ValueError, IndexError): pass
        try: plan.changes = json.loads(changes_text)
        except json.JSONDecodeError: plan.changes = {}
        return plan if plan.hypothesis else None

    def _rule_analyze(self, context: dict) -> Optional[EditPlan]:
        """基于规则降级 (LLM 不可用时)"""
        plan = EditPlan()
        fh = context.get("fitness_history", [])
        eps = context["exploration_rate"]
        if len(fh) >= 5:
            slope = fh[-1] - fh[0]
            if slope < -0.02:
                plan.hypothesis = "Fitness declining, increase exploration"
                plan.changes = {"exploration_rate": min(0.5, eps + 0.1)}
                plan.focus_area = "explore"; plan.iterations = 30; plan.confidence = 0.5
            elif abs(slope) < 0.02:
                plan.hypothesis = "Fitness plateaued, adjust learning rate"
                plan.changes = {"learning_rate": min(0.3, context["learning_rate"] * 1.2)}
                plan.focus_area = "balance"; plan.iterations = 25; plan.confidence = 0.4
            else:
                plan.hypothesis = f"Fitness rising (slope={slope:+.3f}), shift to exploit"
                plan.changes = {"exploration_rate": max(0.05, eps - 0.03)}
                plan.focus_area = "exploit"; plan.iterations = 20; plan.confidence = 0.6
        else:
            plan.hypothesis = "Initial exploration"
            plan.focus_area = "explore"; plan.iterations = 20; plan.confidence = 0.3
        plan.reasoning = f"auto-rule, trend={'rising' if eps < 0.5 else 'plateau'}"
        return plan

    def _apply_edit(self, agent, plan: EditPlan) -> bool:
        try:
            if plan.target == EditTarget.PARAMETERS:
                cfg = agent.config
                for key, value in plan.changes.items():
                    if hasattr(cfg, key):
                        old = getattr(cfg, key)
                        setattr(cfg, key, value)
                        logger.info(f"MetaEditor: {key}: {old} → {value}")
            logger.info(f"MetaEditor: applied — {plan.hypothesis[:60]}")
            return True
        except Exception as e:
            logger.warning(f"MetaEditor apply failed: {e}")
            return False

    def edit_summary(self) -> dict:
        return {"total_edits": len(self.edit_history),
                "recent": [{"h": e.hypothesis[:50], "target": e.target.value, "conf": e.confidence}
                           for e in self.edit_history[-5:]] if self.edit_history else []}
