"""Tests for immune system"""
from laap.security.immune.detector import *
from laap.security.immune.responder import *

def test_threat_detector():
    detector = ThreatDetector()
    threat = detector.detect("sql_injection", "test_source", "Found SQL injection pattern")
    assert threat.type == "sql_injection"
    assert threat.level == ThreatLevel.INFO

def test_immune_responder():
    detector = ThreatDetector()
    responder = ImmuneResponder()
    threat = detector.detect("test", "source", "test threat")
    incident = responder.respond(threat)
    assert incident.status == "open"
