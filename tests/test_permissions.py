"""Tests for permission system."""
import pytest
from laap.permissions.enforcer import PermissionEnforcer, AccessLevel, PermissionRule

class TestPermissionEnforcer:
    def test_init(self):
        e = PermissionEnforcer()
        assert e is not None

    def test_check_defaults(self):
        e = PermissionEnforcer()
        assert e.check("shell") == AccessLevel.CONFIRM
        assert e.check("file:read") == AccessLevel.ALLOW

    def test_add_rule(self):
        e = PermissionEnforcer()
        e.add_rule("custom", PermissionRule("custom", AccessLevel.DENY))
        assert e.check("custom") == AccessLevel.DENY

    def test_resources_exist(self):
        e = PermissionEnforcer()
        assert "shell" in e._rules
        assert "file:delete" in e._rules
