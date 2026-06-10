"""Tests for LAAP-SYNC protocol"""
from laap.protocol.laap_sync import *

def test_version_vector():
    vv = VersionVector()
    vv.increment("replica_1")
    assert vv.get("replica_1") == 1

def test_crdt_document():
    doc = CRDTDocument(doc_id="test_doc")
    doc.set("key1", "value1")
    assert doc.get("key1") == "value1"

def test_sync_session():
    session = SyncSession(session_id="s1", source="a", target="b")
    assert session.source == "a"
    assert session.target == "b"

def test_conflict_resolver():
    resolver = ConflictResolver(strategy=ConflictStrategy.LWW)
    result = resolver.resolve("key", {"v": 1}, {"v": 2})
    assert result is not None
