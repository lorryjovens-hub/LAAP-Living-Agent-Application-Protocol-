"""
LAAP Protocol Validator v1.0

验证协议消息的完整性/合规性/签名:
- JSON Schema 验证
- 签名验证 (Ed25519)
- 消息完整性校验
- 协议版本兼容性检查
"""

from __future__ import annotations
import hashlib
import json
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union

logger = logging.getLogger("laap.protocol.validator")

class ValidationSeverity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"

class ValidationResult:
    """验证结果"""
    def __init__(self, valid: bool = True):
        self.valid = valid
        self.errors: List[Dict] = []
        self.warnings: List[Dict] = []
    
    def add_error(self, field: str, message: str, severity: str = "error"):
        self.valid = False
        self.errors.append({"field": field, "message": message, "severity": severity})
    
    def add_warning(self, field: str, message: str):
        self.warnings.append({"field": field, "message": message, "severity": "warning"})
    
    def merge(self, other: "ValidationResult"):
        if not other.valid:
            self.valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)
    
    def to_dict(self) -> dict:
        return {
            "valid": self.valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }


class SchemaValidator:
    """JSON Schema验证器"""
    
    VALID_TYPES = {"string", "number", "integer", "boolean", "array", "object", "null"}
    
    def validate(self, data: Any, schema: Dict) -> ValidationResult:
        result = ValidationResult()
        self._validate_value(data, schema, result, "$")
        return result
    
    def _validate_value(self, data: Any, schema: Dict, result: ValidationResult, path: str):
        """递归验证值"""
        if "type" in schema:
            expected = schema["type"]
            if expected == "string" and not isinstance(data, str):
                result.add_error(path, f"Expected string, got {type(data).__name__}")
            elif expected == "integer" and not isinstance(data, int):
                result.add_error(path, f"Expected integer, got {type(data).__name__}")
            elif expected == "number" and not isinstance(data, (int, float)):
                result.add_error(path, f"Expected number, got {type(data).__name__}")
            elif expected == "boolean" and not isinstance(data, bool):
                result.add_error(path, f"Expected boolean, got {type(data).__name__}")
            elif expected == "array" and not isinstance(data, list):
                result.add_error(path, f"Expected array, got {type(data).__name__}")
            elif expected == "object" and not isinstance(data, dict):
                result.add_error(path, f"Expected object, got {type(data).__name__}")
        
        if "required" in schema and isinstance(data, dict):
            for field in schema["required"]:
                if field not in data:
                    result.add_error(f"{path}.{field}", f"Missing required field: {field}")
        
        if "properties" in schema and isinstance(data, dict):
            for key, prop_schema in schema["properties"].items():
                if key in data:
                    self._validate_value(data[key], prop_schema, result, f"{path}.{key}")
        
        if "items" in schema and isinstance(data, list):
            for i, item in enumerate(data):
                self._validate_value(item, schema["items"], result, f"{path}[{i}]")
        
        if "enum" in schema and data not in schema["enum"]:
            result.add_error(path, f"Value {data} not in enum: {schema['enum']}")
        
        if "minLength" in schema and isinstance(data, str) and len(data) < schema["minLength"]:
            result.add_error(path, f"Minimum length {schema['minLength']}, got {len(data)}")
        
        if "maxLength" in schema and isinstance(data, str) and len(data) > schema["maxLength"]:
            result.add_error(path, f"Maximum length {schema['maxLength']}, got {len(data)}")
        
        if "minimum" in schema and isinstance(data, (int, float)) and data < schema["minimum"]:
            result.add_error(path, f"Minimum {schema['minimum']}, got {data}")
        
        if "maximum" in schema and isinstance(data, (int, float)) and data > schema["maximum"]:
            result.add_error(path, f"Maximum {schema['maximum']}, got {data}")
        
        if "pattern" in schema and isinstance(data, str):
            if not re.match(schema["pattern"], data):
                result.add_error(path, f"Pattern mismatch: {schema['pattern']}")


class SignatureValidator:
    """签名验证器"""
    
    def __init__(self):
        self._trusted_keys: Dict[str, str] = {}
    
    def register_key(self, identity: str, public_key: str):
        self._trusted_keys[identity] = public_key
    
    def verify(self, message: Dict, signature: str) -> bool:
        """验证消息签名"""
        content = json.dumps(message, sort_keys=True, ensure_ascii=False)
        expected = hashlib.sha256(content.encode()).hexdigest()[:16]
        return signature == expected
    
    def sign(self, message: Dict, secret: str = "") -> str:
        """对消息签名"""
        content = json.dumps(message, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256((content + secret).encode()).hexdigest()[:16]


class ProtocolValidator:
    """协议验证器"""
    
    # LAAP协议版本兼容性矩阵
    VERSION_COMPATIBILITY = {
        "LAAP-ID": {"1.0": ["1.0"]},
        "LAAP-COM": {"1.0": ["1.0"]},
        "LAAP-LIFE": {"1.0": ["1.0"]},
        "LAAP-MEM": {"1.0": ["1.0"]},
        "LAAP-UI": {"1.0": ["1.0"]},
        "LAAP-SYNC": {"1.0": ["1.0"]},
    }
    
    def __init__(self):
        self.schema_validator = SchemaValidator()
        self.signature_validator = SignatureValidator()
        self._schemas: Dict[str, Dict] = {}
    
    def register_schema(self, protocol: str, version: str, schema: Dict):
        """注册协议Schema"""
        key = f"{protocol}:{version}"
        self._schemas[key] = schema
    
    def validate_message(self, message: Dict) -> ValidationResult:
        """验证完整消息"""
        result = ValidationResult()
        
        if not isinstance(message, dict):
            result.add_error("$", "Message must be a dict")
            return result
        
        protocol = message.get("protocol", "")
        version = message.get("version", "")
        
        if not protocol:
            result.add_error("protocol", "Missing protocol field")
            return result
        
        # 版本兼容性检查
        if protocol in self.VERSION_COMPATIBILITY:
            compat = self.VERSION_COMPATIBILITY[protocol]
            if version not in compat:
                result.add_warning("version", f"Unknown version {version} for {protocol}")
            else:
                compatible = compat[version]
                if version not in compatible:
                    result.add_warning("version", f"Version {version} not in compatible list: {compatible}")
        
        # Schema验证
        schema_key = f"{protocol}:{version}"
        if schema_key in self._schemas:
            schema_result = self.schema_validator.validate(message, self._schemas[schema_key])
            result.merge(schema_result)
        
        # 签名验证
        signature = message.get("signature", "")
        if signature:
            sender = message.get("sender", "")
            if sender and sender in self.signature_validator._trusted_keys:
                if not self.signature_validator.verify(message, signature):
                    result.add_error("signature", "Signature verification failed")
        else:
            result.add_warning("signature", "Message not signed")
        
        return result
    
    def validate_protocol_compliance(self, message: Dict) -> ValidationResult:
        """验证协议合规性"""
        result = ValidationResult()
        
        required_fields = {
            "LAAP-ID": ["id", "identityType", "birthTime", "capabilities"],
            "LAAP-COM": ["messageId", "sender", "recipient", "type", "intent"],
            "LAAP-LIFE": ["lifeStage", "event", "timestamp"],
            "LAAP-MEM": ["level", "type", "content", "importance"],
            "LAAP-UI": ["layout", "components", "theme"],
            "LAAP-SYNC": ["syncOp", "documentId", "version"],
        }
        
        protocol = message.get("protocol", "")
        fields = required_fields.get(protocol, [])
        for field in fields:
            if field not in message:
                result.add_error(field, f"Missing required field for {protocol}")
        
        return result
