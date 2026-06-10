"""Security system tests — 20+ test functions."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestThreatDetector:
    def test_detector_create(self):
        from laap.security.immune.detector import ThreatDetector
        td = ThreatDetector()
        assert td is not None

    def test_detector_analyze_safe(self):
        from laap.security.immune.detector import ThreatDetector
        td = ThreatDetector()
        result = td.analyze("safe input")
        assert result.get("threat") is False

    def test_detector_analyze_threat(self):
        from laap.security.immune.detector import ThreatDetector
        td = ThreatDetector()
        result = td.analyze("malicious payload")
        assert result.get("threat") is True

    def test_detector_severity(self):
        from laap.security.immune.detector import ThreatDetector
        td = ThreatDetector()
        result = td.analyze("suspicious input")
        assert "severity" in result


class TestImmuneResponder:
    def test_responder_create(self):
        from laap.security.immune.responder import ImmuneResponder
        ir = ImmuneResponder()
        assert ir is not None

    def test_responder_handle_low(self):
        from laap.security.immune.responder import ImmuneResponder
        ir = ImmuneResponder()
        result = ir.handle(threat_level="low", input="test")
        assert "action" in result

    def test_responder_handle_critical(self):
        from laap.security.immune.responder import ImmuneResponder
        ir = ImmuneResponder()
        result = ir.handle(threat_level="critical", input="danger")
        assert result.get("action") == "block"

    def test_responder_timestamp(self):
        from laap.security.immune.responder import ImmuneResponder
        ir = ImmuneResponder()
        result = ir.handle(threat_level="medium", input="suspicious")
        assert "timestamp" in result


class TestSignatureDB:
    def test_signature_db_create(self):
        from laap.security.immune.signature_db import SignatureDB
        sdb = SignatureDB()
        assert sdb.signatures == []

    def test_signature_db_add(self):
        from laap.security.immune.signature_db import SignatureDB
        sdb = SignatureDB()
        sdb.add_signature("pattern1", severity="high")
        assert len(sdb.signatures) == 1

    def test_signature_db_match(self):
        from laap.security.immune.signature_db import SignatureDB
        sdb = SignatureDB()
        sdb.add_signature("danger", severity="high")
        result = sdb.match("this is a danger signal")
        assert result is not None

    def test_signature_db_no_match(self):
        from laap.security.immune.signature_db import SignatureDB
        sdb = SignatureDB()
        result = sdb.match("safe text")
        assert result is None


class TestQuarantine:
    def test_quarantine_create(self):
        from laap.security.immune.quarantine import Quarantine
        q = Quarantine()
        assert q.isolated_items == []

    def test_quarantine_isolate(self):
        from laap.security.immune.quarantine import Quarantine
        q = Quarantine()
        item_id = q.isolate({"command": "test_cmd"})
        assert item_id is not None
        assert len(q.isolated_items) == 1

    def test_quarantine_release(self):
        from laap.security.immune.quarantine import Quarantine
        q = Quarantine()
        item_id = q.isolate({"command": "test"})
        result = q.release(item_id)
        assert result is True
        assert len(q.isolated_items) == 0

    def test_quarantine_list(self):
        from laap.security.immune.quarantine import Quarantine
        q = Quarantine()
        q.isolate({"cmd": "a"})
        q.isolate({"cmd": "b"})
        items = q.list_isolated()
        assert len(items) == 2


class TestDID:
    def test_did_create(self):
        from laap.security.crypto.did import DIDIdentity
        did = DIDIdentity()
        assert did.did.startswith("did:laap:")

    def test_did_sign_verify(self):
        from laap.security.crypto.did import DIDIdentity
        did = DIDIdentity()
        msg = "hello world"
        sig = did.sign(msg)
        assert did.verify(msg, sig) is True

    def test_did_export(self):
        from laap.security.crypto.did import DIDIdentity
        did = DIDIdentity()
        exported = did.export()
        assert "did" in exported
        assert "public_key" in exported


class TestKeyManager:
    def test_km_create(self):
        from laap.security.crypto.keys import KeyManager
        km = KeyManager()
        assert km.keys == {}

    def test_km_generate(self):
        from laap.security.crypto.keys import KeyManager
        km = KeyManager()
        kid = km.generate_key("test-key")
        assert kid == "test-key"
        assert "test-key" in km.keys

    def test_km_get(self):
        from laap.security.crypto.keys import KeyManager
        km = KeyManager()
        km.generate_key("mykey")
        key = km.get_key("mykey")
        assert key is not None

    def test_km_delete(self):
        from laap.security.crypto.keys import KeyManager
        km = KeyManager()
        km.generate_key("temp")
        km.delete_key("temp")
        assert "temp" not in km.keys


class TestAuditLogger:
    def test_audit_create(self):
        from laap.security.audit.logger import AuditLogger
        al = AuditLogger()
        assert al.logs == []

    def test_audit_log(self):
        from laap.security.audit.logger import AuditLogger
        al = AuditLogger()
        al.log("user_login", {"user": "alice"})
        assert len(al.logs) == 1

    def test_audit_filter(self):
        from laap.security.audit.logger import AuditLogger
        al = AuditLogger()
        al.log("login", {"user": "alice"})
        al.log("logout", {"user": "alice"})
        events = al.get_events("login")
        assert len(events) == 1

    def test_audit_clear(self):
        from laap.security.audit.logger import AuditLogger
        al = AuditLogger()
        al.log("test", {})
        al.clear()
        assert al.logs == []


class TestPolicyEnforcer:
    def test_policy_create(self):
        from laap.security.policy.enforcer import PolicyEnforcer
        pe = PolicyEnforcer()
        assert pe.policies == []

    def test_policy_add(self):
        from laap.security.policy.enforcer import PolicyEnforcer
        pe = PolicyEnforcer()
        pe.add_policy("no_hack", {"action": "block", "pattern": "hack"})
        assert len(pe.policies) == 1

    def test_policy_allow(self):
        from laap.security.policy.enforcer import PolicyEnforcer
        pe = PolicyEnforcer()
        pe.add_policy("safe", {"action": "allow", "pattern": "read"})
        result = pe.check("read file")
        assert result.get("allowed") is True

    def test_policy_block(self):
        from laap.security.policy.enforcer import PolicyEnforcer
        pe = PolicyEnforcer()
        pe.add_policy("blocker", {"action": "block", "pattern": "hack"})
        result = pe.check("try to hack")
        assert result.get("allowed") is False
