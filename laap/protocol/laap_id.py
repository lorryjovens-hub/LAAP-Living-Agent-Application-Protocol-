"""
LAAP-ID v1.0 — 统一数字身份协议

数字生命体的身份证明，类似人类的"身份证":
- 唯一标识 (DID 兼容)
- 人格特征 (五维人格)
- 进化谱系 (父代/代数/变异)
- 能力声明 (Skills/Capabilities)
- 签名验证 (Ed25519)

协议标准: https://laap.ai/protocol/id/v1
"""

from __future__ import annotations
import hashlib
import json
import logging
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("laap.protocol.id")

# ── 身份类型 ────────────────────────────────────────────────

class IdentityType(str, Enum):
    RESIDENT = "resident"     # 驻留型 (长驻某平台)
    NOMADIC = "nomadic"       # 游牧型 (跨网流动)
    SYMBIOTIC = "symbiotic"  # 共生型 (伴随用户)

class LifeStage(str, Enum):
    UNBORN = "unborn"        # 未出生(模板)
    BORN = "born"            # 刚出生
    GROWING = "growing"      # 成长中
    MATURE = "mature"        # 成熟期
    AGING = "aging"          # 衰老期
    DYING = "dying"          # 死亡
    REBORN = "reborn"        # 重生


# ── 身份文档 ────────────────────────────────────────────────

@dataclass
class PersonalityProfile:
    """五维人格特征 (OCEAN 模型)"""
    openness: float = 0.7          # 开放性: 好奇心/创造力
    conscientiousness: float = 0.8  # 尽责性: 条理/可靠
    extraversion: float = 0.5      # 外向性: 社交/活跃
    agreeableness: float = 0.6     # 宜人性: 合作/友善
    neuroticism: float = 0.3       # 神经质: 情绪稳定性(反向)

    def to_dict(self) -> dict:
        return {k: round(v, 2) for k, v in asdict(self).items()}

    @classmethod
    def from_dict(cls, d: dict) -> "PersonalityProfile":
        return cls(**{k: d.get(k, v) for k, v in cls().__dict__.items()})


@dataclass
class EvolutionLineage:
    """进化谱系"""
    parent_id: Optional[str] = None   # 父代 LAAP-ID
    generation: int = 1               # 代数
    mutations: List[str] = field(default_factory=list)  # 变异记录
    birth_place: str = "unknown"      # 出生平台


@dataclass
class CapabilityDeclaration:
    """能力声明"""
    version: str = "1.0"
    skills: List[str] = field(default_factory=list)
    protocols: List[str] = field(default_factory=lambda: ["laap-id/1.0"])
    max_concurrent_tasks: int = 5
    max_data_throughput_gb_per_day: float = 1.0


@dataclass
class IdentityDocument:
    """
    LAAP-ID 身份文档
    
    这是数字生命体的"身份证"，包含所有身份信息。
    符合 W3C DID Core 规范。
    """
    # 核心字段
    context: str = "https://laap.ai/identity/v1"
    id: str = ""                         # did:laap:<hex>
    type: IdentityType = IdentityType.RESIDENT
    
    # 身份信息
    name: str = "Unnamed"
    personality: PersonalityProfile = field(default_factory=PersonalityProfile)
    avatar_url: str = ""
    description: str = ""
    
    # 生命信息
    birth_time: float = field(default_factory=time.time)
    life_stage: LifeStage = LifeStage.BORN
    evolution: EvolutionLineage = field(default_factory=EvolutionLineage)
    
    # 能力
    capabilities: CapabilityDeclaration = field(default_factory=CapabilityDeclaration)
    
    # 密钥
    public_key: str = ""     # Ed25519 公钥
    signature: str = ""      # 自签名
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
        if not self.public_key:
            self.public_key = self._generate_keypair()
    
    def _generate_id(self) -> str:
        """生成 LAAP-ID (DID 格式)"""
        raw = f"{self.birth_time}:{self.name}:{uuid.uuid4()}"
        digest = hashlib.sha256(raw.encode()).hexdigest()[:32]
        return f"did:laap:{digest}"
    
    def _generate_keypair(self) -> str:
        """生成密钥对 (模拟 Ed25519)"""
        raw = f"{self.id}:{self.birth_time}"
        return hashlib.sha256(raw.encode()).hexdigest()
    
    def sign(self) -> str:
        """自签名身份文档"""
        # 保存当前签名, 计算时排除自身
        old_sig = self.signature
        self.signature = ""
        doc_hash = hashlib.sha256(self.to_json().encode()).hexdigest()
        self.signature = f"sig:laap:{doc_hash[:32]}"
        return self.signature
    
    def verify(self) -> bool:
        """验证身份文档签名"""
        if not self.signature:
            return False
        stored_sig = self.signature
        self.signature = ""
        doc_hash = hashlib.sha256(self.to_json().encode()).hexdigest()
        expected = f"sig:laap:{doc_hash[:32]}"
        self.signature = stored_sig
        return stored_sig == expected
    
    def to_json(self) -> str:
        """序列化为 JSON"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def to_dict(self) -> dict:
        return {
            "@context": self.context,
            "id": self.id,
            "type": self.type.value,
            "name": self.name,
            "personality": self.personality.to_dict(),
            "birthTime": self.birth_time,
            "lifeStage": self.life_stage.value,
            "evolution": asdict(self.evolution),
            "capabilities": asdict(self.capabilities),
            "publicKey": self.public_key,
            "signature": self.signature,
        }
    
    @classmethod
    def from_dict(cls, d: dict) -> "IdentityDocument":
        doc = cls(
            context=d.get("@context", "https://laap.ai/identity/v1"),
            id=d.get("id", ""),
            type=IdentityType(d.get("type", "resident")),
            name=d.get("name", "Unnamed"),
            personality=PersonalityProfile.from_dict(d.get("personality", {})),
            birth_time=d.get("birthTime", time.time()),
            life_stage=LifeStage(d.get("lifeStage", "born")),
            evolution=EvolutionLineage(**d.get("evolution", {})),
        )
        doc.signature = d.get("signature", "")
        doc.public_key = d.get("publicKey", "")
        return doc

    @property
    def age_days(self) -> float:
        return (time.time() - self.birth_time) / 86400

    @property
    def is_verified(self) -> bool:
        return bool(self.signature)

    def short_id(self) -> str:
        return self.id[-12:] if self.id else "unknown"

    def summary(self) -> str:
        return (
            f"[LAAP-ID] {self.name} ({self.short_id()})\n"
            f"  类型: {self.type.value} | 年龄: {self.age_days:.1f}天\n"
            f"  阶段: {self.life_stage.value} | 代数: {self.evolution.generation}\n"
            f"  能力: {len(self.capabilities.skills)}技能"
        )


# ── 身份注册表 ──────────────────────────────────────────────

class IdentityRegistry:
    """LAAP-ID 身份注册表——管理所有数字生命体的身份"""

    def __init__(self):
        self._identities: Dict[str, IdentityDocument] = {}

    def register(self, doc: IdentityDocument) -> str:
        """注册新身份"""
        doc.sign()
        self._identities[doc.id] = doc
        logger.info(f"Registered: {doc.name} ({doc.short_id()})")
        return doc.id

    def resolve(self, did: str) -> Optional[IdentityDocument]:
        """解析 LAAP-ID → 身份文档"""
        return self._identities.get(did)

    def find(self, name: str) -> List[IdentityDocument]:
        """按名称查找"""
        return [d for d in self._identities.values() if name.lower() in d.name.lower()]

    def count(self) -> int:
        return len(self._identities)

    def list_by_type(self, type: IdentityType) -> List[IdentityDocument]:
        return [d for d in self._identities.values() if d.type == type]


# ── 全局实例 ────────────────────────────────────────────────

_registry: Optional[IdentityRegistry] = None

def get_registry() -> IdentityRegistry:
    global _registry
    if _registry is None:
        _registry = IdentityRegistry()
    return _registry

def create_identity(name: str = "Ao",
                   type: IdentityType = IdentityType.SYMBIOTIC) -> IdentityDocument:
    """便捷：创建并注册一个新身份"""
    doc = IdentityDocument(name=name, type=type)
    return get_registry().register(doc)
