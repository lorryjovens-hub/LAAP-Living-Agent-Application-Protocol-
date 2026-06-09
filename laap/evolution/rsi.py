"""
LAAP — RSI 递归自我改进引擎 (含 AEvo Controller 集成)

实现 Darwin-Gödel Machine 风格的自我改进循环：
  观察 -> 提案 -> 沙盒测试 -> 评估 -> 采纳/拒绝
+ 可选 AEvo Controller 提供元编辑层
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
import numpy as np, time, logging

logger = logging.getLogger("laap.evolution.rsi")


@dataclass
class ImprovementProposal:
    id: str = ""
    episode: int = 0
    hypothesis: str = ""
    modification: Dict[str, Any] = field(default_factory=dict)
    expected_impact: float = 0.0
    confidence: float = 0.5
    tested: bool = False
    test_result: Optional[float] = None
    adopted: bool = False
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "episode": self.episode,
            "hypothesis": self.hypothesis[:60],
            "mod_type": self.modification.get("type", "unknown"),
            "expected_impact": round(self.expected_impact, 3),
            "confidence": round(self.confidence, 2),
            "tested": self.tested,
            "test_result": round(self.test_result, 3) if self.test_result is not None else None,
            "adopted": self.adopted,
        }


@dataclass
class SandboxResult:
    proposal_id: str; success: bool; score_delta: float
    side_effects: List[str]; error: Optional[str] = None


class RSIEngine:
    """递归自我改进引擎"""

    def __init__(self, proposal_interval: int = 20,
                 adoption_threshold: float = 0.05):
        self.proposal_interval = proposal_interval
        self.adoption_threshold = adoption_threshold
        self.proposals: List[ImprovementProposal] = []
        self.adopted_count = 0
        self.test_count = 0
        self.last_proposal_step = 0
        self.fitness_history: List[float] = []
        self.noise_level = 0.0
        self.meaning_density = 0.0
        self.fixed_point_count = 0
        self._templates = [
            self._propose_adjust_exploration,
            self._propose_adjust_learning_rate,
            self._propose_adjust_needs,
            self._propose_exploit_skill,
        ]
        # AEvo Controller 集成 (可选元编辑层)
        self._aevo_harness = None

    def attach_aevo(self, harness: "EvolutionHarness") -> None:
        """挂载 AEvo EvolutionHarness 作为上层控制器"""
        self._aevo_harness = harness

    def generate_candidate(self, agent) -> Optional[ImprovementProposal]:
        """生成候选人 — 供 AEvo Harness 调用"""
        return self._generate(agent)

    def step(self, agent, force=False) -> Optional[ImprovementProposal]:
        if not force and agent.step_count - self.last_proposal_step < self.proposal_interval:
            logger.debug(
                f"[RSI] step: skipped, step_count={agent.step_count} "
                f"last_proposal_step={self.last_proposal_step} interval={self.proposal_interval}"
            )
            return None

        logger.info(f"[RSI] step: triggered at step={agent.step_count} force={force}")
        from laap.evaluation.fitness import FitnessEvaluator
        ev = FitnessEvaluator()
        fitness = ev.composite_fitness(agent)
        self.fitness_history.append(fitness)
        self._update_noise_meaning()
        logger.debug(f"[RSI] step: fitness={fitness:.4f} history_len={len(self.fitness_history)}")

        proposal = self._generate(agent)
        if not proposal:
            logger.warning("[RSI] step: no proposal generated, aborting step")
            return None

        self.proposals.append(proposal)
        self.last_proposal_step = agent.step_count
        logger.info(
            f"[RSI] step: generated proposal id={proposal.id} "
            f"type={proposal.modification.get('type')} impact={proposal.expected_impact:.3f}"
        )

        if len(self.fitness_history) >= 2:
            result = self._sandbox_test(agent, proposal)
            self.test_count += 1
            logger.info(
                f"[RSI] step: sandbox result id={proposal.id} success={result.success} "
                f"delta={result.score_delta:+.4f} side_effects={result.side_effects}"
            )
            if result.success and result.score_delta > self.adoption_threshold:
                self._adopt(agent, proposal, result)
            else:
                logger.debug(
                    f"[RSI] step: proposal NOT adopted "
                    f"(success={result.success} delta={result.score_delta:+.4f} threshold={self.adoption_threshold})"
                )
        else:
            logger.debug("[RSI] step: skipping sandbox test (need >=2 fitness history points)")

        return proposal

    def _generate(self, agent) -> Optional[ImprovementProposal]:
        """Generate a proposal — try LLM first, fall back to templates."""
        llm = getattr(agent, 'llm', None)
        if llm and hasattr(llm, 'chat_stream'):
            logger.debug(f"[RSI] _generate: trying LLM-generated proposal (llm={type(llm).__name__})")
            proposal = self._llm_generate_proposal(agent)
            if proposal:
                logger.info(f"[RSI] _generate: LLM proposal accepted id={proposal.id}")
                return proposal
            logger.debug("[RSI] _generate: LLM proposal unavailable, falling back to template")
        # Fallback: template-based
        refs = agent.memory.recent_reflections(3)
        if refs:
            for ref in refs:
                if "下降" in ref.observation or "reward_trend" in str(ref.outcome):
                    proposal = self._propose_adjust_exploration(agent)
                    logger.info(f"[RSI] _generate: reflection-driven proposal id={proposal.id} reason='reward_trend下降'")
                    return proposal
        chosen_template = np.random.choice(self._templates)
        proposal = chosen_template(agent)
        logger.info(f"[RSI] _generate: random template proposal id={proposal.id} template={chosen_template.__name__}")
        return proposal

    def _state_summary(self, agent) -> str:
        """Build a concise summary of agent state for the LLM."""
        lines = ["=== Agent State ==="]
        lines.append(f"Step: {agent.step_count}")
        lines.append(f"Exploration rate: {getattr(agent.config, 'exploration_rate', 0.2):.3f}")
        lines.append(f"Learning rate: {getattr(agent.config, 'learning_rate', 0.1):.3f}")

        if hasattr(agent, 'needs'):
            lines.append("\nNeeds:")
            for nt, need in agent.needs.needs.items():
                lines.append(f"  {nt.value}: cur={need.current_level:.3f} target={need.target_level:.3f} drive={need.compute_drive():.3f}")

        if hasattr(agent, 'emotion_gradient'):
            eg = agent.emotion_gradient
            lines.append(f"\nEmotion: valence={eg.state.valence:+.3f} arousal={eg.state.arousal:.3f} confidence={eg.state.confidence:.3f}")
            lines.append(f"Mean reward: {eg.mean_reward:.4f}")

        if hasattr(agent, 'tool_registry'):
            lines.append(f"Tools: {agent.tool_registry.count}")

        # Recent reflections
        refs = agent.memory.recent_reflections(3)
        if refs:
            lines.append("\nRecent reflections:")
            for r in refs:
                lines.append(f"  - {r.observation}: {r.hypothesis}")

        fitness = self.fitness_history[-1] if self.fitness_history else 0.5
        lines.append(f"Fitness: {fitness:.4f}")

        return "\n".join(lines)

    def _llm_generate_proposal(self, agent) -> Optional[ImprovementProposal]:
        """Use LLM to generate a novel improvement proposal."""
        # Bug fix: capture `llm` from agent here (was undefined in inner closure)
        llm = getattr(agent, 'llm', None)
        if not llm or not hasattr(llm, 'chat_stream'):
            logger.debug("[RSI] _llm_generate_proposal: no LLM attached to agent, will fall back to template")
            return None

        try:
            from laap.llm.provider import Message, ToolDef
            state_summary = self._state_summary(agent)
            logger.info(f"[RSI] _llm_generate_proposal: invoking LLM, state_summary_len={len(state_summary)}")

            system_prompt = (
                "You are an AI evolution engineer. Analyze the agent's state and propose ONE "
                "improvement. Output in this exact format:\n"
                "OBSERVATION: <what you notice>\n"
                "HYPOTHESIS: <what to change and why>\n"
                "MOD_TYPE: <adjust_exploration|adjust_learning_rate|adjust_needs>\n"
                "PARAMS: <JSON of parameters>\n"
                "IMPACT: <0.0-1.0 expected impact>\n"
                "CONFIDENCE: <0.0-1.0>"
            )

            messages = [
                Message.system(system_prompt),
                Message.user(state_summary),
            ]

            content = ""
            chunk_count = 0
            logger.debug(f"[RSI] _llm_generate_proposal: starting stream from LLM={type(llm).__name__}")
            for event in llm.chat_stream(messages):
                if event.type == "token":
                    content += event.content
                    chunk_count += 1
                elif event.type == "error":
                    logger.warning(f"[RSI] _llm_generate_proposal: LLM stream error: {event.error}")
                    return None

            logger.info(f"[RSI] _llm_generate_proposal: received {chunk_count} chunks, total_chars={len(content)}")
            if not content:
                logger.debug("[RSI] _llm_generate_proposal: empty content, falling back to template")
                return None

            # Parse structured response
            hypothesis = ""
            mod_type = "adjust_exploration"
            params = {}
            impact = 0.1
            confidence = 0.5

            for line in content.strip().split("\n"):
                line = line.strip()
                if line.startswith("OBSERVATION:"):
                    pass
                elif line.startswith("HYPOTHESIS:"):
                    hypothesis = line[11:].strip()[:100]
                elif line.startswith("MOD_TYPE:"):
                    mod_type = line[9:].strip()
                elif line.startswith("PARAMS:"):
                    try:
                        import json as _json
                        params_text = line[7:].strip()
                        parsed = _json.loads(params_text)
                        if isinstance(parsed, dict):
                            params = parsed
                    except Exception:
                        params = {}
                elif line.startswith("IMPACT:"):
                    try:
                        impact = float(line[7:].strip().split()[0])
                    except (ValueError, IndexError):
                        impact = 0.1
                elif line.startswith("CONFIDENCE:"):
                    try:
                        confidence = float(line[11:].strip().split()[0])
                    except (ValueError, IndexError):
                        confidence = 0.5

            if not hypothesis:
                hypothesis = f"LLM proposed {mod_type}"
            if not params and mod_type == "adjust_exploration":
                params = {"value": 0.15}
            if not params and mod_type == "adjust_learning_rate":
                params = {"value": 0.08}
            if not params and mod_type == "adjust_needs":
                params = {"competence": {"importance": 1.5}}

            logger.info(
                f"[RSI] _llm_generate_proposal: parsed proposal mod_type={mod_type} "
                f"impact={impact:.3f} confidence={confidence:.2f} params={params}"
            )
            return ImprovementProposal(
                id=f"LLM-{len(self.proposals)}",
                episode=agent.step_count,
                hypothesis=hypothesis,
                modification={"type": mod_type, "params": params},
                expected_impact=impact,
                confidence=confidence,
            )
        except Exception as e:
            logger.warning(f"[RSI] _llm_generate_proposal: LLM proposal failed: {e}", exc_info=True)
            return None

    def _propose_adjust_exploration(self, agent):
        cur = agent.config.exploration_rate
        conf = agent.emotion_gradient.state.confidence
        if conf < 0.3:
            new_v = min(0.5, cur + 0.1)
            hyp = "置信度偏低，增加探索以收集信息"
        else:
            new_v = max(0.05, cur - 0.05)
            hyp = "置信度足够，降低探索提高利用"
        return ImprovementProposal(
            id=f"RSI-{len(self.proposals)}", episode=agent.step_count,
            hypothesis=hyp,
            modification={"type": "adjust_exploration", "params": {"value": new_v}},
            expected_impact=0.1 * (cur - new_v),
            confidence=0.6 + 0.3 * conf,
        )

    def _propose_adjust_learning_rate(self, agent):
        vol = agent.emotion_gradient.reward_volatility
        cur = agent.config.learning_rate
        if (vol or 0) > 0.3:
            new_v = max(0.01, cur * 0.8); hyp = "奖励波动大，降低学习率"
        else:
            new_v = min(0.3, cur * 1.2); hyp = "环境稳定，增加学习率"
        return ImprovementProposal(
            id=f"RSI-{len(self.proposals)}", episode=agent.step_count,
            hypothesis=hyp,
            modification={"type": "adjust_learning_rate", "params": {"value": new_v}},
            expected_impact=0.05, confidence=0.5,
        )

    def _propose_adjust_needs(self, agent):
        from laap.cognition.needs import NeedType
        dominant, _ = agent.needs.get_dominant_need()
        if not dominant:
            return self._propose_adjust_exploration(agent)
        key = dominant.value
        if agent.needs.needs[dominant].current_level < 0.3:
            adj = {key: {"decay_rate": 0.005}}
            hyp = f"需求 {key} 长期匮乏，降低衰减"
        else:
            adj = {key: {"importance": 1.2}}
            hyp = f"增强需求 {key} 影响权重"
        return ImprovementProposal(
            id=f"RSI-{len(self.proposals)}", episode=agent.step_count,
            hypothesis=hyp,
            modification={"type": "adjust_needs", "params": adj},
            expected_impact=0.08, confidence=0.55,
        )

    def _propose_exploit_skill(self, agent):
        best = agent.memory.best_skills(1)
        if not best:
            return self._propose_adjust_exploration(agent)
        if best[0].success_rate > 0.8 and best[0].proficiency > 0.7:
            new_eps = max(0.05, agent.config.exploration_rate * 0.7)
            return ImprovementProposal(
                id=f"RSI-{len(self.proposals)}", episode=agent.step_count,
                hypothesis=f"利用高熟练技能 {best[0].name}",
                modification={"type": "adjust_exploration", "params": {"value": new_eps}},
                expected_impact=0.1, confidence=0.7,
            )
        return self._propose_adjust_exploration(agent)

    def _sandbox_test(self, agent, proposal) -> SandboxResult:
        from laap.evaluation.fitness import FitnessEvaluator
        ev = FitnessEvaluator()
        baseline = ev.composite_fitness(agent)
        orig_eps = agent.config.exploration_rate
        orig_lr = agent.config.learning_rate

        success = agent.apply_modification(proposal.modification)
        if not success:
            return SandboxResult(proposal.id, False, 0.0, ["error"])

        post = ev.composite_fitness(agent)
        agent.config.exploration_rate = orig_eps
        agent.config.learning_rate = orig_lr
        delta = post - baseline
        proposal.tested = True
        proposal.test_result = delta
        logger.info(f"  Sandbox: {baseline:.4f} -> {post:.4f} (delta={delta:+.4f})")
        return SandboxResult(proposal.id, delta > 0, delta, [] if delta > 0 else ["negative"])

    def _adopt(self, agent, proposal, result):
        if agent.apply_modification(proposal.modification):
            proposal.adopted = True
            self.adopted_count += 1
            logger.info(f"  Adopted [{proposal.id}]: {proposal.hypothesis[:50]}")

    def _update_noise_meaning(self):
        """N2M-RSI 噪声到意义更新"""
        if len(self.fitness_history) < 5:
            return
        recent = self.fitness_history[-5:]
        self.noise_level = float(np.std(recent))
        deltas = np.diff(recent)
        meaningful = [d for d in deltas if abs(d) > 0.01]
        self.meaning_density = len(meaningful) / max(1, len(deltas))
        self.fixed_point_count = 0 if self.noise_level >= 0.01 else self.fixed_point_count + 1

    def info_integration(self) -> float:
        """N2M-RSI 信息整合度"""
        return self.meaning_density / max(0.01, self.noise_level) if self.noise_level > 0 else 0.0

    def adoption_rate(self, window=20) -> float:
        recent = self.proposals[-window:] if self.proposals else []
        if not recent:
            return 0.0
        tested = [p for p in recent if p.tested]
        return sum(1 for p in tested if p.adopted) / max(1, len(tested))

    def status(self) -> dict:
        return {
            "total": len(self.proposals),
            "adopted": self.adopted_count,
            "test_count": self.test_count,
            "adoption_rate": round(self.adoption_rate(), 3),
            "noise": round(self.noise_level, 4),
            "meaning": round(self.meaning_density, 4),
            "info_integration": round(self.info_integration(), 4),
            "stuck": self.fixed_point_count >= 10,
            "recent": [p.to_dict() for p in self.proposals[-5:]],
        }
