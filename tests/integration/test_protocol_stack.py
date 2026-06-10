"""Integration tests for protocol stack"""
from laap.protocol.registry import ProtocolRegistry, register_default_protocols

def test_full_protocol_registration():
    registry = register_default_protocols()
    protocols = registry.get_all_active()
    assert len(protocols) >= 4  # At least 4 protocols

def test_protocol_discovery():
    registry = register_default_protocols()
    results = registry.discover("identity")
    assert len(results) >= 1
