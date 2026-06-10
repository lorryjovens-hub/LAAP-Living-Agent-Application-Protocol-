"""Rollback Manager for Evolution"""
from __future__ import annotations
import time, json, copy, logging, threading
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from laap.engine.evolution.proposal import EvolutionProposal, ProposalStatus

logger = logging.getLogger("engine.evolution.rollback")

class RollbackStrategy(str, Enum):
    FULL = "full"
    PARTIAL = "partial"
    CONFIG_ONLY = "config_only"

@dataclass
class Snapshot:
    id: str = ""
    proposal_id: str = ""
    state: Dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    config_backup: Dict = field(default_factory=dict)

class SnapshotManager:
    def __init__(self):
        self._snapshots: Dict[str, Snapshot] = {}
        self._lock = threading.RLock()
    def create_snapshot(self, proposal_id: str, state: Dict, config: Dict = None) -> str:
        snap = Snapshot(id=f"snap_{int(time.time()*1e6)}", proposal_id=proposal_id,
                       state=copy.deepcopy(state), config_backup=copy.deepcopy(config or {}))
        with self._lock:
            self._snapshots[snap.id] = snap
        return snap.id
    def get_snapshot(self, snap_id: str) -> Optional[Snapshot]:
        return self._snapshots.get(snap_id)
    def get_by_proposal(self, proposal_id: str) -> Optional[Snapshot]:
        for snap in self._snapshots.values():
            if snap.proposal_id == proposal_id:
                return snap
        return None

class StateRestorer:
    def restore(self, snapshot: Snapshot) -> bool:
        logger.info(f"Restoring state from snapshot {snapshot.id}")
        return True

class RollbackHistory:
    def __init__(self):
        self._history: List[Dict] = []
        self._lock = threading.RLock()
    def record(self, proposal_id: str, strategy: RollbackStrategy, reason: str):
        with self._lock:
            self._history.append({"proposal_id": proposal_id, "strategy": strategy.value,
                                 "reason": reason, "timestamp": time.time()})
    def get_recent(self, n: int = 10) -> List[Dict]:
        return self._history[-n:]

class RollbackManager:
    def __init__(self):
        self.snapshot_mgr = SnapshotManager()
        self.restorer = StateRestorer()
        self.history = RollbackHistory()
    def rollback(self, proposal: EvolutionProposal, strategy: RollbackStrategy = RollbackStrategy.FULL) -> bool:
        snap = self.snapshot_mgr.get_by_proposal(proposal.id)
        if not snap:
            logger.warning(f"No snapshot found for {proposal.id}")
            return False
        success = self.restorer.restore(snap)
        if success:
            self.history.record(proposal.id, strategy, "manual_rollback")
            proposal.status = ProposalStatus.ROLLED_BACK
        return success
