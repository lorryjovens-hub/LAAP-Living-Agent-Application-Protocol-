"""
LAAP-SYNC v1.0 — 同步协议

数字生命体数据同步协议，定义版本向量、CRDT文档、冲突解决、同步会话管理
和离线支持，确保多端数据一致性。

协议标准: https://laap.ai/protocol/sync/v1
"""

from __future__ import annotations
import enum
import hashlib
import json
import logging
import threading
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum, auto
from typing import Any, Dict, List, Optional, Tuple, Union, Callable, Set

logger = logging.getLogger("laap.protocol.sync")

class SyncOpType(str, Enum):
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    MERGE = "merge"
    PATCH = "patch"
    UPSERT = "upsert"
    REPLACE = "replace"
    BATCH = "batch"
    TRANSACTION = "transaction"
    ROLLBACK = "rollback"

class ConflictStrategy(str, Enum):
    LWW = "lww"
    MVCC = "mvcc"
    CRDT = "crdt"
    MERGE = "merge"
    INTERACTIVE = "interactive"
    CUSTOM = "custom"

class SyncStatus(str, Enum):
    PENDING = "pending"
    SYNCING = "syncing"
    CONFIRMED = "confirmed"
    FAILED = "failed"
    CONFLICT = "conflict"
    ROLLED_BACK = "rolled_back"
    PARTIAL = "partial"
    TIMEOUT = "timeout"

class ReplicaType(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    READ_ONLY = "read_only"
    EDGE = "edge"
    MOBILE = "mobile"
    CLOUD = "cloud"
    PEER = "peer"

@dataclass
class VersionVector:
    versions: Dict[str, int] = field(default_factory=dict)

    def increment(self, replica_id: str):
        new_vec = VersionVector(dict(self.versions))
        new_vec.versions[replica_id] = new_vec.versions.get(replica_id, 0) + 1
        return new_vec

    def get(self, replica_id: str) -> int:
        return self.versions.get(replica_id, 0)

    def set(self, replica_id: str, version: int):
        self.versions[replica_id] = version

    def merge(self, other):
        merged = VersionVector(dict(self.versions))
        for rid, ver in other.versions.items():
            merged.versions[rid] = max(merged.versions.get(rid, 0), ver)
        return merged

    def compare(self, other):
        all_keys = set(self.versions.keys()) | set(other.versions.keys())
        le = all(self.versions.get(k, 0) <= other.versions.get(k, 0) for k in all_keys)
        ge = all(self.versions.get(k, 0) >= other.versions.get(k, 0) for k in all_keys)
        if le and ge: return "equal"
        if le: return "before"
        if ge: return "after"
        return "concurrent"

    def __le__(self, other):
        all_keys = set(self.versions.keys()) | set(other.versions.keys())
        return all(self.versions.get(k, 0) <= other.versions.get(k, 0) for k in all_keys)

    def __ge__(self, other):
        all_keys = set(self.versions.keys()) | set(other.versions.keys())
        return all(self.versions.get(k, 0) >= other.versions.get(k, 0) for k in all_keys)

    def __eq__(self, other):
        if not isinstance(other, VersionVector): return NotImplemented
        return self.versions == other.versions

    def to_dict(self):
        return dict(self.versions)

    @staticmethod
    def from_dict(data):
        return VersionVector(versions=dict(data))

    def clone(self):
        return VersionVector(dict(self.versions))

    def is_empty(self):
        return len(self.versions) == 0

    def all_versions(self):
        return sorted(self.versions.items(), key=lambda x: x[0])

    def __repr__(self):
        parts = [f"{rid}:{ver}" for rid, ver in sorted(self.versions.items())]
        return f"VV({','.join(parts)})"

    def __hash__(self):
        return hash(tuple(sorted(self.versions.items())))

    def to_json(self):
        return json.dumps(self.versions, separators=(",", ":"))

    @staticmethod
    def from_json(data: str):
        return VersionVector.from_dict(json.loads(data))

@dataclass
class SyncOp:
    op_type: SyncOpType
    key: str
    value: Any = None
    version_vector: Optional[VersionVector] = None
    replica_id: str = ""
    timestamp: float = 0.0
    op_id: str = ""
    parent_op_id: Optional[str] = None
    transaction_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    checksum: Optional[str] = None
    retry_count: int = 0
    priority: int = 0

    def __post_init__(self):
        if not self.op_id:
            self.op_id = f"op_{uuid.uuid4().hex}"
        if not self.timestamp:
            self.timestamp = time.time()
        if not self.replica_id:
            self.replica_id = f"replica_{uuid.uuid4().hex[:8]}"

    def to_dict(self):
        return {
            "op_type": self.op_type.value,
            "key": self.key,
            "value": self.value,
            "version_vector": self.version_vector.to_dict() if self.version_vector else None,
            "replica_id": self.replica_id,
            "timestamp": self.timestamp,
            "op_id": self.op_id,
            "parent_op_id": self.parent_op_id,
            "transaction_id": self.transaction_id,
            "metadata": self.metadata,
            "checksum": self.checksum,
            "retry_count": self.retry_count,
            "priority": self.priority,
        }

    @staticmethod
    def from_dict(data):
        return SyncOp(
            op_type=SyncOpType(data["op_type"]),
            key=data["key"],
            value=data.get("value"),
            version_vector=VersionVector.from_dict(data["version_vector"]) if data.get("version_vector") else None,
            replica_id=data.get("replica_id", ""),
            timestamp=data.get("timestamp", 0.0),
            op_id=data.get("op_id", ""),
            parent_op_id=data.get("parent_op_id"),
            transaction_id=data.get("transaction_id"),
            metadata=data.get("metadata", {}),
            checksum=data.get("checksum"),
            retry_count=data.get("retry_count", 0),
            priority=data.get("priority", 0),
        )

    def compute_checksum(self):
        content = json.dumps({"op_type": self.op_type.value, "key": self.key, "value": self.value},
                             sort_keys=True, ensure_ascii=False)
        self.checksum = hashlib.sha256(content.encode()).hexdigest()
        return self.checksum

    def verify_checksum(self) -> bool:
        if not self.checksum:
            return True
        return self.compute_checksum() == self.checksum

@dataclass
class CRDTDocument:
    """
    CRDT无冲突文档

    基于操作变换(OT)和状态向量的无冲突复制数据类型。
    支持自动合并并发更新，无需中心协调节点。
    """
    doc_id: str = ""
    replica_id: str = ""
    state: Dict[str, Any] = field(default_factory=dict)
    version_vector: VersionVector = field(default_factory=VersionVector)
    operations: List[SyncOp] = field(default_factory=list)
    tombstone: Set[str] = field(default_factory=set)
    created_at: float = 0.0
    updated_at: float = 0.0
    vector_clock: Dict[str, int] = field(default_factory=dict)

    def __post_init__(self):
        if not self.doc_id:
            self.doc_id = f"doc_{uuid.uuid4().hex[:12]}"
        if not self.created_at:
            self.created_at = time.time()
        if not self.updated_at:
            self.updated_at = self.created_at

    def apply_op(self, op: SyncOp) -> bool:
        if op.checksum and not op.verify_checksum():
            logger.warning(f"Checksum verification failed for op {op.op_id}")
            return False

        if op.op_type == SyncOpType.CREATE:
            self.state[op.key] = op.value
        elif op.op_type == SyncOpType.UPDATE:
            self.state[op.key] = op.value
        elif op.op_type == SyncOpType.DELETE:
            self.state.pop(op.key, None)
            self.tombstone.add(op.key)
        elif op.op_type == SyncOpType.MERGE:
            if isinstance(op.value, dict) and isinstance(self.state.get(op.key), dict):
                self.state[op.key].update(op.value)
            else:
                self.state[op.key] = op.value
        elif op.op_type == SyncOpType.PATCH:
            if isinstance(op.value, dict):
                existing = self.state.get(op.key, {})
                if isinstance(existing, dict):
                    existing.update(op.value)
                    self.state[op.key] = existing
                else:
                    self.state[op.key] = op.value
            else:
                self.state[op.key] = op.value
        elif op.op_type == SyncOpType.UPSERT:
            self.state[op.key] = op.value
        elif op.op_type == SyncOpType.REPLACE:
            self.state[op.key] = op.value
        else:
            logger.warning(f"Unknown op type: {op.op_type}")
            return False

        if op.version_vector:
            self.version_vector = self.version_vector.merge(op.version_vector)
            self.vector_clock[op.replica_id] = op.version_vector.get(op.replica_id)

        self.operations.append(op)
        self.updated_at = time.time()
        return True

    def merge(self, other: CRDTDocument) -> CRDTDocument:
        merged = CRDTDocument(
            doc_id=self.doc_id,
            replica_id=self.replica_id,
            state=dict(self.state),
            version_vector=self.version_vector.merge(other.version_vector),
            created_at=min(self.created_at, other.created_at),
        )

        for key in set(self.state.keys()) | set(other.state.keys()):
            sv = self.version_vector
            ov = other.version_vector
            if key in self.tombstone and key not in other.tombstone:
                continue
            if key in other.tombstone and key not in self.tombstone:
                continue
            if key in self.tombstone and key in other.tombstone:
                merged.tombstone.add(key)
                merged.state.pop(key, None)
                continue

            sv_val = sv.versions.get(self.replica_id, 0)
            ov_val = ov.versions.get(other.replica_id, 0)
            if key not in other.state:
                merged.state[key] = self.state[key]
            elif key not in self.state:
                merged.state[key] = other.state[key]
            elif sv.compare(ov) in ("after", "equal"):
                merged.state[key] = self.state[key]
            elif ov.compare(sv) == "after":
                merged.state[key] = other.state[key]
            else:
                merged.state[key] = self._resolve_concurrent(key, self.state[key], other.state[key])

        merged.operations = self.operations + other.operations
        merged.tombstone = self.tombstone | other.tombstone
        merged.updated_at = time.time()
        return merged

    def _resolve_concurrent(self, key: str, val_a: Any, val_b: Any) -> Any:
        if isinstance(val_a, (int, float)) and isinstance(val_b, (int, float)):
            return max(val_a, val_b)
        if isinstance(val_a, dict) and isinstance(val_b, dict):
            merged = dict(val_a)
            merged.update(val_b)
            return merged
        if isinstance(val_a, set) and isinstance(val_b, set):
            return val_a | val_b
        if isinstance(val_a, list) and isinstance(val_b, list):
            return val_a + [v for v in val_b if v not in val_a]
        return val_a

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def set(self, key: str, value: Any, replica_id: Optional[str] = None) -> SyncOp:
        rid = replica_id or self.replica_id
        vv = self.version_vector.increment(rid)
        op = SyncOp(
            op_type=SyncOpType.UPDATE,
            key=key, value=value,
            version_vector=vv,
            replica_id=rid,
        )
        op.compute_checksum()
        self.apply_op(op)
        return op

    def delete(self, key: str, replica_id: Optional[str] = None) -> SyncOp:
        rid = replica_id or self.replica_id
        vv = self.version_vector.increment(rid)
        op = SyncOp(
            op_type=SyncOpType.DELETE, key=key,
            version_vector=vv, replica_id=rid,
        )
        op.compute_checksum()
        self.apply_op(op)
        return op

    def to_dict(self):
        return {
            "doc_id": self.doc_id,
            "replica_id": self.replica_id,
            "state": self.state,
            "version_vector": self.version_vector.to_dict(),
            "operations": [op.to_dict() for op in self.operations[-100:]],
            "tombstone": list(self.tombstone),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "vector_clock": self.vector_clock,
        }

    @staticmethod
    def from_dict(data):
        doc = CRDTDocument(
            doc_id=data.get("doc_id", ""),
            replica_id=data.get("replica_id", ""),
            state=data.get("state", {}),
            version_vector=VersionVector.from_dict(data.get("version_vector", {})),
            created_at=data.get("created_at", 0.0),
            updated_at=data.get("updated_at", 0.0),
            vector_clock=data.get("vector_clock", {}),
        )
        doc.tombstone = set(data.get("tombstone", []))
        for op_data in data.get("operations", []):
            doc.operations.append(SyncOp.from_dict(op_data))
        return doc

    def snapshot(self):
        return {
            "state": dict(self.state),
            "version_vector": self.version_vector.clone(),
            "timestamp": self.updated_at,
        }

    def size(self) -> int:
        return len(self.state)

    def diff_since(self, since_vv: VersionVector) -> List[SyncOp]:
        ops = []
        for op in self.operations:
            if op.version_vector and since_vv.compare(op.version_vector) == "before":
                ops.append(op)
        return ops

class ConflictInfo:
    def __init__(self, key: str, local_val: Any, remote_val: Any,
                 local_vv: VersionVector, remote_vv: VersionVector,
                 local_replica: str, remote_replica: str):
        self.key = key
        self.local_val = local_val
        self.remote_val = remote_val
        self.local_vv = local_vv
        self.remote_vv = remote_vv
        self.local_replica = local_replica
        self.remote_replica = remote_replica
        self.timestamp = time.time()
        self.conflict_id = f"conflict_{uuid.uuid4().hex[:8]}"
        self.resolved = False
        self.resolution: Optional[Any] = None

    def to_dict(self):
        return {
            "conflict_id": self.conflict_id,
            "key": self.key,
            "local_val": self.local_val,
            "remote_val": self.remote_val,
            "local_vv": self.local_vv.to_dict(),
            "remote_vv": self.remote_vv.to_dict(),
            "local_replica": self.local_replica,
            "remote_replica": self.remote_replica,
            "timestamp": self.timestamp,
            "resolved": self.resolved,
            "resolution": self.resolution,
        }

class ConflictResolver:
    def __init__(self, strategy: ConflictStrategy = ConflictStrategy.LWW):
        self.strategy = strategy
        self._custom_resolvers: Dict[str, Callable] = {}
        self._conflict_log: List[ConflictInfo] = []
        self._stats = {"total": 0, "auto_resolved": 0, "pending": 0}

    def resolve(self, key: str, local_val: Any, remote_val: Any,
                local_vv: VersionVector, remote_vv: VersionVector,
                local_replica: str, remote_replica: str) -> Tuple[Any, bool]:
        self._stats["total"] += 1
        info = ConflictInfo(key, local_val, remote_val, local_vv, remote_vv,
                           local_replica, remote_replica)
        self._conflict_log.append(info)

        if key in self._custom_resolvers:
            result = self._custom_resolvers[key](info)
            info.resolved = True
            info.resolution = result
            self._stats["auto_resolved"] += 1
            return result, True

        if self.strategy == ConflictStrategy.LWW:
            result = self._lww_resolve(info)
            info.resolved = True
            info.resolution = result
            self._stats["auto_resolved"] += 1
            return result, True

        elif self.strategy == ConflictStrategy.CRDT:
            result = self._crdt_resolve(info)
            info.resolved = True
            info.resolution = result
            self._stats["auto_resolved"] += 1
            return result, True

        elif self.strategy == ConflictStrategy.MVCC:
            result = self._mvcc_resolve(info)
            info.resolved = True
            info.resolution = result
            self._stats["auto_resolved"] += 1
            return result, True

        elif self.strategy == ConflictStrategy.MERGE:
            result = self._merge_resolve(info)
            info.resolved = True
            info.resolution = result
            self._stats["auto_resolved"] += 1
            return result, True

        self._stats["pending"] += 1
        return None, False

    def _lww_resolve(self, info: ConflictInfo) -> Any:
        if info.local_vv.__ge__(info.remote_vv):
            return info.local_val
        elif info.remote_vv.__ge__(info.local_vv):
            return info.remote_val
        return info.remote_val

    def _crdt_resolve(self, info: ConflictInfo) -> Any:
        if isinstance(info.local_val, (int, float)) and isinstance(info.remote_val, (int, float)):
            return max(info.local_val, info.remote_val)
        if isinstance(info.local_val, dict) and isinstance(info.remote_val, dict):
            merged = dict(info.local_val)
            merged.update(info.remote_val)
            return merged
        if isinstance(info.local_val, set) and isinstance(info.remote_val, set):
            return info.local_val | info.remote_val
        if isinstance(info.local_val, list) and isinstance(info.remote_val, list):
            return info.local_val + [v for v in info.remote_val if v not in info.local_val]
        return info.remote_val

    def _mvcc_resolve(self, info: ConflictInfo) -> Any:
        lv = info.local_vv.versions.get(info.local_replica, 0)
        rv = info.remote_vv.versions.get(info.remote_replica, 0)
        if lv >= rv: return info.local_val
        return info.remote_val

    def _merge_resolve(self, info: ConflictInfo) -> Any:
        if isinstance(info.local_val, dict) and isinstance(info.remote_val, dict):
            merged = dict(info.local_val)
            merged.update(info.remote_val)
            return merged
        return info.remote_val

    def register_custom(self, key: str, resolver: Callable):
        self._custom_resolvers[key] = resolver

    def remove_custom(self, key: str):
        self._custom_resolvers.pop(key, None)

    def get_conflicts(self, resolved: Optional[bool] = None) -> List[ConflictInfo]:
        if resolved is None:
            return list(self._conflict_log)
        return [c for c in self._conflict_log if c.resolved == resolved]

    def get_stats(self):
        return dict(self._stats)

    def reset(self):
        self._conflict_log = []
        self._stats = {"total": 0, "auto_resolved": 0, "pending": 0}

class SyncSession:
    def __init__(self, session_id: str = "", local_replica_id: str = "",
                 remote_replica_id: str = ""):
        self.session_id = session_id or f"session_{uuid.uuid4().hex[:12]}"
        self.local_replica_id = local_replica_id or f"replica_{uuid.uuid4().hex[:8]}"
        self.remote_replica_id = remote_replica_id
        self.status: SyncStatus = SyncStatus.PENDING
        self.start_time = time.time()
        self.end_time: Optional[float] = None
        self.operations: List[SyncOp] = []
        self.confirmed_ops: List[str] = []
        self.failed_ops: List[str] = []
        self.version_vector: VersionVector = VersionVector()
        self.metadata: Dict[str, Any] = field(default_factory=dict)
        self._lock = threading.Lock()

    def add_operation(self, op: SyncOp):
        with self._lock:
            self.operations.append(op)
            self.status = SyncStatus.SYNCING

    def confirm_operation(self, op_id: str):
        with self._lock:
            self.confirmed_ops.append(op_id)
            if op_id in self.failed_ops:
                self.failed_ops.remove(op_id)

    def fail_operation(self, op_id: str, reason: str = ""):
        with self._lock:
            self.failed_ops.append(op_id)
            if op_id in self.confirmed_ops:
                self.confirmed_ops.remove(op_id)

    def is_complete(self) -> bool:
        return len(self.confirmed_ops) == len(self.operations)

    def progress(self) -> float:
        if not self.operations:
            return 1.0
        return len(self.confirmed_ops) / len(self.operations)

    def close(self, status: SyncStatus = SyncStatus.CONFIRMED):
        with self._lock:
            self.status = status
            self.end_time = time.time()

    def duration(self) -> float:
        end = self.end_time or time.time()
        return end - self.start_time

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "local_replica_id": self.local_replica_id,
            "remote_replica_id": self.remote_replica_id,
            "status": self.status.value,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "total_ops": len(self.operations),
            "confirmed": len(self.confirmed_ops),
            "failed": len(self.failed_ops),
            "progress": self.progress(),
            "duration": self.duration(),
        }

class SyncEngine:
    def __init__(self, replica_id: str = "", local_replica_type: ReplicaType = ReplicaType.PRIMARY):
        self.replica_id = replica_id or f"engine_{uuid.uuid4().hex[:8]}"
        self.replica_type = local_replica_type
        self.documents: Dict[str, CRDTDocument] = {}
        self.sessions: Dict[str, SyncSession] = {}
        self.conflict_resolver = ConflictResolver(ConflictStrategy.LWW)
        self._lock = threading.RLock()
        self._event_listeners: Dict[str, List[Callable]] = {
            "sync_start": [], "sync_complete": [], "conflict": [],
            "op_applied": [], "error": [], "session_update": [],
        }
        self._stats = {
            "total_syncs": 0, "successful_syncs": 0,
            "failed_syncs": 0, "conflicts_resolved": 0,
            "ops_processed": 0, "bytes_synced": 0,
        }

    def create_document(self, doc_id: str = "") -> CRDTDocument:
        doc = CRDTDocument(doc_id=doc_id, replica_id=self.replica_id)
        with self._lock:
            self.documents[doc.doc_id] = doc
        return doc

    def get_document(self, doc_id: str) -> Optional[CRDTDocument]:
        return self.documents.get(doc_id)

    def delete_document(self, doc_id: str):
        with self._lock:
            self.documents.pop(doc_id, None)

    def start_sync(self, remote_replica_id: str) -> SyncSession:
        session = SyncSession(
            local_replica_id=self.replica_id,
            remote_replica_id=remote_replica_id,
        )
        with self._lock:
            self.sessions[session.session_id] = session
            self._stats["total_syncs"] += 1
        self._emit("sync_start", session)
        return session

    def end_sync(self, session_id: str, status: SyncStatus = SyncStatus.CONFIRMED):
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return
            session.close(status)
            if status == SyncStatus.CONFIRMED:
                self._stats["successful_syncs"] += 1
            else:
                self._stats["failed_syncs"] += 1
        self._emit("sync_complete", session)

    def apply_operation(self, op: SyncOp, doc_id: str) -> bool:
        with self._lock:
            doc = self.documents.get(doc_id)
            if not doc:
                logger.warning(f"Document {doc_id} not found")
                return False

            existing = doc.state.get(op.key)
            if existing is not None and op.op_type in (SyncOpType.UPDATE, SyncOpType.UPSERT):
                if op.version_vector and doc.version_vector:
                    comp = op.version_vector.compare(doc.version_vector)
                    if comp == "concurrent":
                        resolved, auto = self.conflict_resolver.resolve(
                            op.key, existing, op.value,
                            doc.version_vector, op.version_vector,
                            doc.replica_id, op.replica_id,
                        )
                        if auto:
                            op.value = resolved
                            self._stats["conflicts_resolved"] += 1
                            self._emit("conflict", {"key": op.key, "resolved": True})
                        else:
                            self._emit("conflict", {"key": op.key, "resolved": False})
                            return False

            result = doc.apply_op(op)
            if result:
                self._stats["ops_processed"] += 1
                if op.checksum:
                    self._stats["bytes_synced"] += len(op.checksum)
                self._emit("op_applied", {"op": op, "doc_id": doc_id})
            return result

    def sync_document(self, doc_id: str, remote_doc: CRDTDocument) -> SyncSession:
        session = self.start_sync(remote_doc.replica_id)
        local_doc = self.documents.get(doc_id)

        if not local_doc:
            local_doc = self.create_document(doc_id)
            for op in remote_doc.operations:
                self.apply_operation(op, doc_id)
            self.end_sync(session.session_id, SyncStatus.CONFIRMED)
            return session

        merged = local_doc.merge(remote_doc)
        self.documents[doc_id] = merged
        self.end_sync(session.session_id, SyncStatus.CONFIRMED)
        return session

    def batch_sync(self, doc_map: Dict[str, CRDTDocument]) -> Dict[str, SyncSession]:
        results = {}
        for doc_id, remote_doc in doc_map.items():
            results[doc_id] = self.sync_document(doc_id, remote_doc)
        return results

    def get_all_document_snapshots(self):
        return {did: doc.snapshot() for did, doc in self.documents.items()}

    def on(self, event: str, listener: Callable):
        if event in self._event_listeners:
            self._event_listeners[event].append(listener)

    def off(self, event: str, listener: Callable):
        if event in self._event_listeners:
            self._event_listeners[event] = [l for l in self._event_listeners[event] if l != listener]

    def _emit(self, event: str, data: Any):
        for listener in self._event_listeners.get(event, []):
            try:
                listener(data)
            except Exception as e:
                logger.error(f"Event listener error: {e}")

    def get_stats(self):
        return dict(self._stats)

    def get_sessions(self, status: Optional[SyncStatus] = None) -> List[SyncSession]:
        if status is None:
            return list(self.sessions.values())
        return [s for s in self.sessions.values() if s.status == status]

    def cleanup_old_sessions(self, max_age: float = 3600):
        now = time.time()
        to_remove = []
        for sid, session in self.sessions.items():
            if session.end_time and (now - session.end_time) > max_age:
                to_remove.append(sid)
        for sid in to_remove:
            self.sessions.pop(sid, None)

    def reset_stats(self):
        self._stats = {
            "total_syncs": 0, "successful_syncs": 0,
            "failed_syncs": 0, "conflicts_resolved": 0,
            "ops_processed": 0, "bytes_synced": 0,
        }

class StateSynchronizer:
    def __init__(self, engine: SyncEngine):
        self.engine = engine
        self._snapshots: Dict[str, Dict] = {}
        self._sync_intervals: Dict[str, float] = {}
        self._last_sync: Dict[str, float] = {}

    def capture_snapshot(self, doc_id: str):
        doc = self.engine.get_document(doc_id)
        if doc:
            self._snapshots[doc_id] = doc.snapshot()
            return self._snapshots[doc_id]
        return None

    def detect_changes(self, doc_id: str) -> bool:
        doc = self.engine.get_document(doc_id)
        if not doc or doc_id not in self._snapshots:
            return False
        old_snap = self._snapshots[doc_id]
        current_snap = doc.snapshot()
        return old_snap != current_snap

    def get_changes_since(self, doc_id: str, since_vv: VersionVector) -> List[SyncOp]:
        doc = self.engine.get_document(doc_id)
        if not doc:
            return []
        return doc.diff_since(since_vv)

    def get_state_delta(self, doc_id: str, old_vv: VersionVector,
                        new_vv: VersionVector) -> Dict[str, Any]:
        doc = self.engine.get_document(doc_id)
        if not doc:
            return {}
        affected_keys = set()
        for op in doc.operations:
            if op.version_vector:
                ov = op.version_vector
                if old_vv.compare(ov) == "before" and new_vv.compare(ov) != "before":
                    affected_keys.add(op.key)
        return {k: doc.state.get(k) for k in affected_keys if k in doc.state}

    def set_sync_interval(self, doc_id: str, interval: float):
        self._sync_intervals[doc_id] = interval

    def should_sync(self, doc_id: str) -> bool:
        interval = self._sync_intervals.get(doc_id, 60)
        last = self._last_sync.get(doc_id, 0)
        return (time.time() - last) >= interval

    def mark_synced(self, doc_id: str):
        self._last_sync[doc_id] = time.time()

    def full_state_sync(self, doc_id: str, remote_doc: CRDTDocument) -> bool:
        session = self.engine.sync_document(doc_id, remote_doc)
        if session.status == SyncStatus.CONFIRMED:
            self.capture_snapshot(doc_id)
            self.mark_synced(doc_id)
            return True
        return False

    def selective_sync(self, doc_id: str, keys: List[str],
                       remote_doc: CRDTDocument) -> bool:
        local_doc = self.engine.get_document(doc_id)
        if not local_doc:
            return self.full_state_sync(doc_id, remote_doc)

        for key in keys:
            local_val = local_doc.state.get(key)
            remote_val = remote_doc.state.get(key)
            if local_val != remote_val:
                op = SyncOp(
                    op_type=SyncOpType.UPDATE, key=key, value=remote_val,
                    replica_id=remote_doc.replica_id,
                )
                self.engine.apply_operation(op, doc_id)

        self.capture_snapshot(doc_id)
        self.mark_synced(doc_id)
        return True

    def resolve_state_conflicts(self, doc_id: str) -> int:
        doc = self.engine.get_document(doc_id)
        if not doc:
            return 0
        conflicts = self.engine.conflict_resolver.get_conflicts(resolved=False)
        resolved_count = 0
        for conflict in conflicts:
            if conflict.key in doc.state:
                resolved, _ = self.engine.conflict_resolver.resolve(
                    conflict.key, conflict.local_val, conflict.remote_val,
                    conflict.local_vv, conflict.remote_vv,
                    conflict.local_replica, conflict.remote_replica,
                )
                if resolved is not None:
                    op = SyncOp(
                        op_type=SyncOpType.UPDATE, key=conflict.key,
                        value=resolved, replica_id=self.engine.replica_id,
                    )
                    self.engine.apply_operation(op, doc_id)
                    resolved_count += 1
        return resolved_count

class DeltaCalculator:
    def __init__(self):
        self._stats = {"deltas_computed": 0, "total_keys": 0, "changed_keys": 0}

    def compute_delta(self, old_state: Dict[str, Any],
                      new_state: Dict[str, Any]) -> Dict[str, Any]:
        self._stats["deltas_computed"] += 1
        delta = {}
        all_keys = set(old_state.keys()) | set(new_state.keys())
        self._stats["total_keys"] += len(all_keys)

        for key in all_keys:
            old_val = old_state.get(key)
            new_val = new_state.get(key)

            if key not in new_state:
                delta[key] = {"op": "delete", "old": old_val}
                self._stats["changed_keys"] += 1
            elif key not in old_state:
                delta[key] = {"op": "create", "new": new_val}
                self._stats["changed_keys"] += 1
            elif old_val != new_val:
                delta[key] = {"op": "update", "old": old_val, "new": new_val}
                self._stats["changed_keys"] += 1

        return delta

    def apply_delta(self, state: Dict[str, Any], delta: Dict[str, Any]) -> Dict[str, Any]:
        new_state = dict(state)
        for key, change in delta.items():
            if change.get("op") == "delete":
                new_state.pop(key, None)
            elif change.get("op") in ("create", "update"):
                new_state[key] = change.get("new")
        return new_state

    def delta_size(self, delta: Dict[str, Any]) -> int:
        return len(json.dumps(delta, ensure_ascii=False).encode("utf-8"))

    def compress_delta(self, delta: Dict[str, Any]) -> Dict[str, Any]:
        compressed = {}
        for key, change in delta.items():
            if change.get("op") == "update":
                compressed[key] = {"op": "u", "o": change.get("old"), "n": change.get("new")}
            elif change.get("op") == "create":
                compressed[key] = {"op": "c", "n": change.get("new")}
            elif change.get("op") == "delete":
                compressed[key] = {"op": "d"}
            else:
                compressed[key] = change
        return compressed

    def get_stats(self):
        return dict(self._stats)

class OfflineBuffer:
    def __init__(self, max_size: int = 10000, max_age: float = 86400):
        self._buffer: List[SyncOp] = []
        self._max_size = max_size
        self._max_age = max_age
        self._last_flush: Optional[float] = None

    def enqueue(self, op: SyncOp):
        if len(self._buffer) >= self._max_size:
            logger.warning("Offline buffer full, removing oldest operation")
            self._buffer.pop(0)
        self._buffer.append(op)

    def enqueue_many(self, ops: List[SyncOp]):
        for op in ops:
            self.enqueue(op)

    def dequeue(self, count: int = 1) -> List[SyncOp]:
        ops = self._buffer[:count]
        self._buffer = self._buffer[count:]
        return ops

    def dequeue_all(self) -> List[SyncOp]:
        ops = list(self._buffer)
        self._buffer.clear()
        return ops

    def peek(self, count: int = 1) -> List[SyncOp]:
        return self._buffer[:count]

    def size(self) -> int:
        return len(self._buffer)

    def is_empty(self) -> bool:
        return len(self._buffer) == 0

    def is_full(self) -> bool:
        return len(self._buffer) >= self._max_size

    def clear(self):
        self._buffer.clear()

    def get_expired_ops(self) -> List[SyncOp]:
        now = time.time()
        expired = []
        remaining = []
        for op in self._buffer:
            if (now - op.timestamp) > self._max_age:
                expired.append(op)
            else:
                remaining.append(op)
        self._buffer = remaining
        return expired

    def get_ops_since(self, since_timestamp: float) -> List[SyncOp]:
        return [op for op in self._buffer if op.timestamp >= since_timestamp]

    def get_ops_by_replica(self, replica_id: str) -> List[SyncOp]:
        return [op for op in self._buffer if op.replica_id == replica_id]

    def get_ops_by_key(self, key: str) -> List[SyncOp]:
        return [op for op in self._buffer if op.key == key]

    def flush(self, engine: SyncEngine, doc_id: str) -> int:
        ops = self.dequeue_all()
        count = 0
        for op in ops:
            if engine.apply_operation(op, doc_id):
                count += 1
        self._last_flush = time.time()
        return count

    def batch_flush(self, engine: SyncEngine, doc_map: Dict[str, str]) -> int:
        """doc_map: op_id -> doc_id"""
        ops = self.dequeue_all()
        count = 0
        for op in ops:
            did = doc_map.get(op.op_id, "")
            if not did:
                did = "default"
            if engine.apply_operation(op, did):
                count += 1
        self._last_flush = time.time()
        return count

    def to_dict(self):
        return {
            "size": self.size(),
            "max_size": self._max_size,
            "max_age": self._max_age,
            "last_flush": self._last_flush,
            "is_full": self.is_full(),
            "is_empty": self.is_empty(),
            "pending_ops": [op.to_dict() for op in self._buffer],
        }

    def estimate_size_bytes(self) -> int:
        return sum(len(json.dumps(op.to_dict(), ensure_ascii=False).encode()) for op in self._buffer)

__all__ = [
    "SyncOpType", "ConflictStrategy", "SyncStatus", "ReplicaType",
    "VersionVector", "SyncOp", "CRDTDocument", "ConflictInfo",
    "ConflictResolver", "SyncSession", "SyncEngine",
    "StateSynchronizer", "DeltaCalculator", "OfflineBuffer",
]
