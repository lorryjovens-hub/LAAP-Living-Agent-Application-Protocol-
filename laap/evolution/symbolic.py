"""
LAAP — 符号递归层

基于 Psi-Omega Protocol 概念：
  Agent -> Fork -> 变异 -> [Collapse | Fusion]
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import numpy as np, time, uuid, logging

from laap.evolution.mutation import MutationStrategy
from laap.evaluation.fitness import FitnessEvaluator
from laap.agent.base import Agent, AgentConfig


@dataclass
class AgentLineage:
    agent_id: str; generation: int; parent_id: Optional[str]
    birth_time: float = field(default_factory=time.time)
    mutation_history: List[str] = field(default_factory=list)
    forks: List[str] = field(default_factory=list)
    fitness_scores: List[float] = field(default_factory=list)
    collapsed: bool = False; collapse_reason: Optional[str] = None


@dataclass
class NullAgent:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    contradiction: str = ""
    threshold: float = 0.5
    resolved: bool = False; resolved_by: Optional[str] = None


class SymbolicRecursionLayer:
    """符号递归层：种群级开放式进化"""

    def __init__(self, max_population: int = 20):
        self.logger = logging.getLogger("laap.evolution.symbolic")
        self.mutation = MutationStrategy()
        self.evaluator = FitnessEvaluator()
        self.population: Dict[str, Agent] = {}
        self.lineages: Dict[str, AgentLineage] = {}
        self.null_agents: List[NullAgent] = []
        self.max_population = max_population
        self.generation_counter = 0
        self.total_forks = 0; self.total_collapses = 0; self.total_fusions = 0
        self.entropy_history: List[float] = []

    def fork(self, parent_id: str, strategy: Optional[str] = None) -> Optional[Agent]:
        parent = self.population.get(parent_id)
        if not parent:
            return None
        if len(self.population) >= self.max_population:
            self._cull()

        state = {
            "config": {
                "exploration_rate": parent.config.exploration_rate,
                "learning_rate": parent.config.learning_rate,
                "name": f"{parent.config.name}-F{self.total_forks}",
            },
            "needs": [],
            "goals": [],
            "skills": list(parent.memory.skills.keys()),
        }

        result = self.mutation.apply(state, strategy)
        mut_state = result["mutated"]
        cfg = mut_state["config"]

        child = Agent(config=AgentConfig(
            name=cfg.get("name", "child"),
            exploration_rate=cfg.get("exploration_rate", 0.2),
            learning_rate=cfg.get("learning_rate", 0.1),
        ))
        for sk in mut_state.get("skills", []):
            child.register_tool(sk, lambda **kw: None, f"inherit from {parent_id}")

        self.population[child.id] = child
        self.generation_counter += 1
        self.total_forks += 1

        lineage = AgentLineage(
            agent_id=child.id,
            generation=(self.lineages[parent_id].generation + 1) if parent_id in self.lineages else 1,
            parent_id=parent_id,
            mutation_history=[result["strategy"]],
        )
        self.lineages[child.id] = lineage
        if parent_id in self.lineages:
            self.lineages[parent_id].forks.append(child.id)

        self.logger.info(f"Fork [{child.id[:8]}] <- [{parent_id[:8]}] ({result['strategy']})")
        return child

    def inject_null(self, contradiction: str, threshold=0.5) -> NullAgent:
        null = NullAgent(contradiction=contradiction, threshold=threshold)
        self.null_agents.append(null)
        resolver = self._find_resolver(contradiction)
        if resolver:
            null.resolved = True
            null.resolved_by = resolver.id
        return null

    def _find_resolver(self, contradiction: str) -> Optional[Agent]:
        best_aid, best_score = None, -float("inf")
        for aid, agent in self.population.items():
            conf = getattr(getattr(agent, 'emotion_gradient', None), 'state', None)
            conf = getattr(conf, 'confidence', 0.5) if conf else 0.5
            need_level = 0.5
            if hasattr(agent, 'needs') and agent.needs:
                need_list = list(agent.needs.needs.values())
                if need_list:
                    need_level = need_list[1].current_level if len(need_list) > 1 else need_list[0].current_level
            score = conf * 0.6 + need_level * 0.4
            if score > best_score:
                best_score, best_aid = score, aid
        return self.population.get(best_aid) if best_aid else None

    def detect_collapse(self, agent_id: str) -> Tuple[bool, Optional[str]]:
        agent = self.population.get(agent_id)
        if not agent or not agent.alive:
            return True, "dead"
        # Gracefully handle agents without emotion_gradient (base Agent)
        eg = getattr(agent, 'emotion_gradient', None)
        v = eg.state.valence if eg else 0.0
        conf = eg.state.confidence if eg else 0.5
        reasons = []
        if v < -0.5 and hasattr(agent, '_reward_history') and len(agent._reward_history) > 10:
            reasons.append(f"valence={v:.2f}")
        if conf < 0.1:
            reasons.append(f"confidence={conf:.2f}")
        return (True, "; ".join(reasons)) if len(reasons) >= 2 else (False, None)

    def collapse(self, agent_id: str, reason="unknown"):
        if agent_id in self.population:
            self.population[agent_id].die(reason)
        if agent_id in self.lineages:
            self.lineages[agent_id].collapsed = True
            self.lineages[agent_id].collapse_reason = reason
        self.population.pop(agent_id, None)
        self.total_collapses += 1

    def _cull(self):
        scored = [(self.evaluator.composite_fitness(a), aid)
                  for aid, a in self.population.items()]
        scored.sort()
        for _, aid in scored[:max(1, len(scored) - self.max_population + 2)]:
            self.collapse(aid, "culled")

    def tick(self) -> dict:
        for aid in list(self.population.keys()):
            doit, reason = self.detect_collapse(aid)
            if doit:
                self.collapse(aid, reason or "auto")
        return {"size": len(self.population), "forks": self.total_forks,
                "collapses": self.total_collapses, "fusions": self.total_fusions}

    def report(self) -> dict:
        return {"size": len(self.population), "max": self.max_population,
                "forks": self.total_forks, "collapses": self.total_collapses,
                "fusions": self.total_fusions, "generations": self.generation_counter,
                "lineages": [{"id": lid, "gen": self.lineages[lid].generation,
                              "parent": self.lineages[lid].parent_id,
                              "collapsed": self.lineages[lid].collapsed}
                             for lid in list(self.lineages.keys())[:10]]}
