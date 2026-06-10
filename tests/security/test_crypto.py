"""Tests for crypto"""
from laap.security.crypto.did import *
from laap.security.crypto.keys import *

def test_did_creation():
    creator = DIDCreator()
    doc = creator.create("laap", "test_seed")
    assert doc.id.startswith("did:laap:")

def test_key_manager():
    km = KeyManager()
    kp = km.generate("test_key")
    sig = km.sign("test_key", "hello")
    assert km.verify(kp.public_key, "hello", sig) is True
