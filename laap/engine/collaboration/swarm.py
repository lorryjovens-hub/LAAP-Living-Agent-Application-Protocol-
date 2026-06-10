"""Swarm Coordination — 集群协作"""
from __future__ import annotations
import time, uuid, logging, threading, random
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("engine.collaboration.swarm")

class LeaderState(str, Enum):
    FOLLOWER = "follower"
    CANDIDATE = "candidate"
    LEADER = "leader"

@dataclass
class SwarmMember:
    id: str = ""
    address: str = ""
    role: str = "worker"
    state: LeaderState = LeaderState.FOLLOWER
    term: int = 0
    last_heartbeat: float = field(default_factory=time.time)
    load: float = 0.0

class SwarmCoordinator:
    def __init__(self, self_id: str, members: List[str] = None):
        self.self_id = self_id
        self._members: Dict[str, SwarmMember] = {}
        self.state = LeaderState.FOLLOWER
        self.current_leader: str = ""
        self.term = 0
        self._lock = threading.RLock()
        if members:
            for m in members:
                self._members[m] = SwarmMember(id=m)
    def join(self, member_id: str, address: str = ""):
        with self._lock:
            if member_id not in self._members:
                self._members[member_id] = SwarmMember(id=member_id, address=address)
    def leave(self, member_id: str):
        with self._lock:
            self._members.pop(member_id, None)
    def start_election(self):
        with self._lock:
            self.state = LeaderState.CANDIDATE
            self.term += 1
            votes = 1
            for mid in list(self._members.keys()):
                if mid != self.self_id:
                    votes += 1
            majority = (len(self._members) + 1) // 2 + 1
            if votes >= majority:
                self.state = LeaderState.LEADER
                self.current_leader = self.self_id
                logger.info(f"{self.self_id} elected leader (term {self.term})")
                return True
            self.state = LeaderState.FOLLOWER
            return False
    def heartbeat(self, leader_id: str, term: int):
        with self._lock:
            if term >= self.term:
                self.current_leader = leader_id
                self.state = LeaderState.FOLLOWER
                self.term = term
                if leader_id in self._members:
                    self._members[leader_id].last_heartbeat = time.time()
    def get_members(self) -> List[SwarmMember]:
        return list(self._members.values())
    def get_stats(self) -> dict:
        return {"members": len(self._members), "leader": self.current_leader, "state": self.state.value, "term": self.term}
