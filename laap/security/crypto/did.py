"""DID (Decentralized Identifier) — W3C DID兼容"""
from __future__ import annotations
import time, json, hashlib, logging, uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger("security.crypto.did")

@dataclass
class DIDDocument:
    id: str = ""
    public_key: str = ""
    authentication: List[str] = field(default_factory=list)
    service: List[Dict] = field(default_factory=list)
    created: float = field(default_factory=time.time)
    updated: float = field(default_factory=time.time)
    proof: Dict = field(default_factory=dict)
    
    def to_json(self) -> str:
        return json.dumps({
            "@context": "https://www.w3.org/ns/did/v1",
            "id": self.id,
            "publicKey": [{"id": f"{self.id}#keys-1", "type": "Ed25519VerificationKey2018", "publicKeyHex": self.public_key}],
            "authentication": self.authentication or [f"{self.id}#keys-1"],
            "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.created)),
        }, indent=2)

class DIDCreator:
    @staticmethod
    def create(method: str = "laap", seed: str = "") -> DIDDocument:
        doc_id = f"did:{method}:{hashlib.sha256((seed + str(time.time())).encode()).hexdigest()[:16]}"
        key = hashlib.sha256(seed.encode()).hexdigest()[:32] if seed else uuid.uuid4().hex
        return DIDDocument(id=doc_id, public_key=key)

class DIDResolver:
    def __init__(self):
        self._registry: Dict[str, DIDDocument] = {}
    def register(self, doc: DIDDocument):
        self._registry[doc.id] = doc
    def resolve(self, did: str) -> Optional[DIDDocument]:
        return self._registry.get(did)
    def verify(self, doc: DIDDocument, signature: str, message: str) -> bool:
        expected = hashlib.sha256((message + doc.public_key).encode()).hexdigest()[:16]
        return signature == expected
