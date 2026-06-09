"""
LAAP — Branch Lock & Stale Detection

Prevent concurrent modifications to protected branches
and detect stale/inactive branches.
"""

from __future__ import annotations
import logging, os, time, json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("laap.git.branch_lock")


@dataclass
class BranchLock:
    """A lock on a git branch"""
    branch: str
    agent_id: str
    session_id: str = ""
    acquired_at: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    reason: str = ""

    @property
    def expired(self) -> bool:
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def age(self) -> float:
        return time.time() - self.acquired_at

    def to_dict(self) -> dict:
        return {
            "branch": self.branch,
            "agent_id": self.agent_id[:12],
            "session_id": self.session_id[:12],
            "acquired_at": self.acquired_at,
            "expired": self.expired,
            "age_s": round(self.age, 1),
            "reason": self.reason[:80],
        }


class BranchLockManager:
    """Manage locks on git branches"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = repo_path
        self._lock_dir = Path(repo_path) / ".laap" / "locks"
        self._lock_dir.mkdir(parents=True, exist_ok=True)
        self._locks: Dict[str, BranchLock] = {}
        self._load_locks()

    def _lock_path(self, branch: str) -> Path:
        safe = branch.replace("/", "__").replace("\\", "__")
        return self._lock_dir / f"{safe}.json"

    def _load_locks(self):
        for lock_file in self._lock_dir.glob("*.json"):
            try:
                with open(lock_file) as f:
                    data = json.load(f)
                lock = BranchLock(
                    branch=data["branch"],
                    agent_id=data["agent_id"],
                    session_id=data.get("session_id", ""),
                    acquired_at=data.get("acquired_at", 0),
                    expires_at=data.get("expires_at"),
                    reason=data.get("reason", ""),
                )
                if not lock.expired:
                    self._locks[lock.branch] = lock
                else:
                    lock_file.unlink()
            except Exception:
                pass

    def acquire(self, branch: str, agent_id: str,
                session_id: str = "", reason: str = "",
                ttl: Optional[int] = 3600) -> Optional[BranchLock]:
        """Acquire a lock on a branch. Returns None if already locked."""
        existing = self._locks.get(branch)
        if existing and not existing.expired:
            logger.warning(f"Branch '{branch}' locked by agent {existing.agent_id[:12]}")
            return None

        expires_at = time.time() + ttl if ttl else None
        lock = BranchLock(
            branch=branch, agent_id=agent_id,
            session_id=session_id, reason=reason,
            expires_at=expires_at,
        )
        self._locks[branch] = lock
        self._persist(lock)
        logger.info(f"Lock acquired on '{branch}' by {agent_id[:12]}")
        return lock

    def release(self, branch: str) -> bool:
        lock = self._locks.pop(branch, None)
        if lock:
            lock_path = self._lock_path(branch)
            if lock_path.exists():
                lock_path.unlink()
            logger.info(f"Lock released on '{branch}'")
            return True
        return False

    def is_locked(self, branch: str) -> bool:
        lock = self._locks.get(branch)
        if lock and lock.expired:
            self.release(branch)
            return False
        return lock is not None

    def _persist(self, lock: BranchLock):
        lock_path = self._lock_path(lock.branch)
        with open(lock_path, "w") as f:
            json.dump(lock.to_dict(), f)

    def list_locks(self) -> List[dict]:
        return [lock.to_dict() for lock in self._locks.values() if not lock.expired]

    def clean_expired(self):
        expired = [b for b, l in self._locks.items() if l.expired]
        for branch in expired:
            self.release(branch)

    @property
    def status(self) -> dict:
        self.clean_expired()
        return {
            "active_locks": len(self._locks),
            "locks": self.list_locks(),
        }
