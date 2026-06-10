"""Evolution Proposal — 进化提案数据模型"""
from __future__ import annotations
import time, json, uuid, logging
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("engine.evolution.proposal")

class ProposalStatus(str, Enum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    REJECTED = "rejected"
    TESTING = "testing"
    STAGING = "staging"
    DEPLOYED = "deployed"
    ROLLED_BACK = "rolled_back"
    FAILED = "failed"

class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class EvolutionProposal:
    """进化提案"""
    id: str = ""
    target: str = ""
    current_value: Any = None
    proposed_value: Any = None
    rationale: str = ""
    expected_gain: float = 0.0
    risk_level: RiskLevel = RiskLevel.LOW
    constraints: Dict = field(default_factory=lambda: {"min": 0.0, "max": 1.0, "type": "float"})
    required_tests: List[str] = field(default_factory=list)
    status: ProposalStatus = ProposalStatus.PROPOSED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    creator: str = ""
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        d = asdict(self)
        d["risk_level"] = self.risk_level.value if isinstance(self.risk_level, RiskLevel) else self.risk_level
        d["status"] = self.status.value if isinstance(self.status, ProposalStatus) else self.status
        return d
    
    @classmethod
    def from_dict(cls, d: dict) -> "EvolutionProposal":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})

class ProposalFactory:
    """提案工厂"""
    @staticmethod
    def create(target: str, current: Any, proposed: Any, rationale: str = "",
               gain: float = 0.0, risk: str = "low", constraints: Dict = None) -> EvolutionProposal:
        return EvolutionProposal(
            id=f"prop_{uuid.uuid4().hex[:8]}",
            target=target,
            current_value=current,
            proposed_value=proposed,
            rationale=rationale,
            expected_gain=gain,
            risk_level=RiskLevel(risk),
            constraints=constraints or {"min": 0.0, "max": 1.0, "type": "float"},
        )

class ProposalValidator:
    """提案验证器"""
    @staticmethod
    def validate(proposal: EvolutionProposal) -> List[str]:
        errors = []
        if not proposal.target:
            errors.append("target is required")
        if proposal.current_value == proposal.proposed_value:
            errors.append("no actual change")
        if not proposal.rationale:
            errors.append("rationale is required")
        if proposal.expected_gain <= 0:
            errors.append("expected_gain must be positive")
        return errors
