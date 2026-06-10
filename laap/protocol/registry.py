"""
LAAP Protocol Registry v1.0

协议注册中心 — 管理所有LAAP协议的注册/发现/版本控制
"""

from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type

logger = logging.getLogger("laap.protocol.registry")


class ProtocolStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    BETA = "beta"
    DRAFT = "draft"
    RETIRED = "retired"


@dataclass
class ProtocolCapability:
    """协议能力声明"""
    name: str
    version: str
    description: str = ""
    endpoints: List[str] = field(default_factory=list)
    message_types: List[str] = field(default_factory=list)
    features: List[str] = field(default_factory=list)
    dependencies: List[str] = field(default_factory=list)
    status: ProtocolStatus = ProtocolStatus.ACTIVE
    registered_at: float = field(default_factory=time.time)
    
    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "endpoints": self.endpoints,
            "message_types": self.message_types,
            "features": self.features,
            "dependencies": self.dependencies,
            "status": self.status.value,
            "registered_at": self.registered_at,
        }


class VersionManager:
    """版本管理器"""
    
    def __init__(self):
        self._versions: Dict[str, List[str]] = {}
        self._deprecations: Dict[str, float] = {}
    
    def register_version(self, protocol: str, version: str):
        if protocol not in self._versions:
            self._versions[protocol] = []
        if version not in self._versions[protocol]:
            self._versions[protocol].append(version)
            self._versions[protocol].sort()
    
    def deprecate_version(self, protocol: str, version: str):
        key = f"{protocol}:{version}"
        self._deprecations[key] = time.time()
    
    def is_deprecated(self, protocol: str, version: str) -> bool:
        key = f"{protocol}:{version}"
        return key in self._deprecations
    
    def get_latest(self, protocol: str) -> Optional[str]:
        versions = self._versions.get(protocol, [])
        return versions[-1] if versions else None
    
    def get_supported_versions(self, protocol: str) -> List[str]:
        versions = self._versions.get(protocol, [])
        return [v for v in versions if not self.is_deprecated(protocol, v)]
    
    def check_compatibility(self, protocol: str, v1: str, v2: str) -> bool:
        """检查两个版本是否兼容"""
        return v1 == v2  # 语义版本兼容性检查


class ProtocolRegistry:
    """协议注册中心 — 单例"""
    
    _instance: Optional["ProtocolRegistry"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._protocols: Dict[str, ProtocolCapability] = {}
        self._message_handlers: Dict[str, Callable] = {}
        self._encoders: Dict[str, Callable] = {}
        self._decoders: Dict[str, Callable] = {}
        self.version_manager = VersionManager()
        self._event_listeners: Dict[str, List[Callable]] = {}
    
    def register(self, capability: ProtocolCapability):
        """注册协议"""
        key = f"{capability.name}:{capability.version}"
        self._protocols[key] = capability
        self.version_manager.register_version(capability.name, capability.version)
        logger.info(f"Registered protocol: {key}")
        self._emit("protocol.registered", {"protocol": key})
    
    def unregister(self, name: str, version: str):
        key = f"{name}:{version}"
        if key in self._protocols:
            del self._protocols[key]
            logger.info(f"Unregistered protocol: {key}")
            self._emit("protocol.unregistered", {"protocol": key})
    
    def get(self, name: str, version: str) -> Optional[ProtocolCapability]:
        return self._protocols.get(f"{name}:{version}")
    
    def find_by_name(self, name: str) -> List[ProtocolCapability]:
        return [v for k, v in self._protocols.items() if k.startswith(f"{name}:")]
    
    def find_by_feature(self, feature: str) -> List[ProtocolCapability]:
        return [v for v in self._protocols.values() if feature in v.features]
    
    def get_all_active(self) -> List[ProtocolCapability]:
        return [v for v in self._protocols.values() if v.status == ProtocolStatus.ACTIVE]
    
    def register_handler(self, message_type: str, handler: Callable):
        self._message_handlers[message_type] = handler
    
    def dispatch(self, message_type: str, message: Any) -> Any:
        handler = self._message_handlers.get(message_type)
        if handler:
            return handler(message)
        logger.warning(f"No handler for message type: {message_type}")
        return None
    
    def register_codec(self, protocol: str, version: str, encoder: Callable, decoder: Callable):
        key = f"{protocol}:{version}"
        self._encoders[key] = encoder
        self._decoders[key] = decoder
    
    def encode(self, protocol: str, version: str, data: Any) -> bytes:
        key = f"{protocol}:{version}"
        encoder = self._encoders.get(key)
        if encoder:
            return encoder(data)
        return json.dumps(data).encode()
    
    def decode(self, protocol: str, version: str, data: bytes) -> Any:
        key = f"{protocol}:{version}"
        decoder = self._decoders.get(key)
        if decoder:
            return decoder(data)
        return json.loads(data.decode())
    
    def on(self, event: str, listener: Callable):
        if event not in self._event_listeners:
            self._event_listeners[event] = []
        self._event_listeners[event].append(listener)
    
    def _emit(self, event: str, data: Any):
        for listener in self._event_listeners.get(event, []):
            try:
                listener(data)
            except Exception as e:
                logger.error(f"Event listener error: {e}")
    
    def discover(self, feature: str) -> List[Dict]:
        """发现支持特定特性的协议"""
        results = []
        for cap in self._protocols.values():
            if feature in cap.features or feature in cap.name.lower():
                results.append(cap.to_dict())
        return results
    
    def to_dict(self) -> dict:
        return {
            "protocols": {k: v.to_dict() for k, v in self._protocols.items()},
            "handlers": list(self._message_handlers.keys()),
            "versions": {k: list(v) for k, v in self.version_manager._versions.items()},
        }


class ProtocolCapabilityBuilder:
    """协议能力构建器 (Builder模式)"""
    
    def __init__(self, name: str, version: str):
        self._cap = ProtocolCapability(name=name, version=version)
    
    def description(self, desc: str) -> "ProtocolCapabilityBuilder":
        self._cap.description = desc
        return self
    
    def add_endpoint(self, endpoint: str) -> "ProtocolCapabilityBuilder":
        self._cap.endpoints.append(endpoint)
        return self
    
    def add_message_type(self, msg_type: str) -> "ProtocolCapabilityBuilder":
        self._cap.message_types.append(msg_type)
        return self
    
    def add_feature(self, feature: str) -> "ProtocolCapabilityBuilder":
        self._cap.features.append(feature)
        return self
    
    def add_dependency(self, dep: str) -> "ProtocolCapabilityBuilder":
        self._cap.dependencies.append(dep)
        return self
    
    def status(self, status: ProtocolStatus) -> "ProtocolCapabilityBuilder":
        self._cap.status = status
        return self
    
    def build(self) -> ProtocolCapability:
        return self._cap


# 默认注册所有LAAP协议
def register_default_protocols():
    registry = ProtocolRegistry()
    
    protocols = [
        ProtocolCapabilityBuilder("LAAP-ID", "1.0")
            .description("统一数字身份协议 - DID兼容的身份管理")
            .add_feature("identity").add_feature("authentication")
            .add_feature("personality").add_feature("evolution_lineage")
            .add_message_type("identity_document").add_message_type("verification")
            .build(),
        ProtocolCapabilityBuilder("LAAP-COM", "1.0")
            .description("数字生命体通信协议 - 意图驱动的消息传递")
            .add_feature("messaging").add_feature("routing")
            .add_feature("encryption").add_feature("priority")
            .add_message_type("request").add_message_type("response")
            .add_message_type("event").add_message_type("broadcast")
            .build(),
        ProtocolCapabilityBuilder("LAAP-LIFE", "1.0")
            .description("生命周期协议 - 确定性状态机管理")
            .add_feature("state_machine").add_feature("lifecycle")
            .add_feature("guards").add_feature("transitions")
            .add_message_type("state_change").add_message_type("life_event")
            .build(),
        ProtocolCapabilityBuilder("LAAP-MEM", "1.0")
            .description("记忆协议 - 分层记忆架构 (Atkinson-Shiffrin)")
            .add_feature("memory").add_feature("forgetting_curve")
            .add_feature("consolidation").add_feature("retrieval")
            .add_message_type("memory_store").add_message_type("memory_recall")
            .build(),
        ProtocolCapabilityBuilder("LAAP-UI", "1.0")
            .description("渲染协议 - 跨端声明式UI渲染")
            .add_feature("rendering").add_feature("layout")
            .add_feature("theming").add_feature("interaction")
            .add_message_type("render_command").add_message_type("event_binding")
            .build(),
        ProtocolCapabilityBuilder("LAAP-SYNC", "1.0")
            .description("同步协议 - CRDT跨端状态同步")
            .add_feature("synchronization").add_feature("crdt")
            .add_feature("conflict_resolution").add_feature("offline")
            .add_message_type("sync_op").add_message_type("version_vector")
            .build(),
    ]
    
    for p in protocols:
        registry.register(p)
    
    return registry

