"""Tests for protocol validator"""
from laap.protocol.validator import *

def test_schema_validator():
    v = SchemaValidator()
    schema = {"type": "object", "required": ["name"], "properties": {"name": {"type": "string"}}}
    result = v.validate({"name": "test"}, schema)
    assert result.valid

def test_protocol_validator():
    v = ProtocolValidator()
    result = v.validate_message({"protocol": "LAAP-ID", "version": "1.0"})
    assert result is not None
