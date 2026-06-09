"""Tests for LAAP Path Scope Enforcer"""
import pytest
import tempfile, os
from laap.editor.path_scope import PathScopeEnforcer, PathScopeConfig


class TestPathScopeEnforcer:
    def test_allowed_path(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            config = PathScopeConfig(allowed_dirs=[tmpdir])
            enforcer = PathScopeEnforcer(config=config)
            allowed, reason = enforcer.check(os.path.join(tmpdir, "test.txt"))
            assert allowed, reason

    def test_blocked_pattern(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            config = PathScopeConfig(
                allowed_dirs=[tmpdir],
                blocked_patterns=["*.pyc"],
            )
            enforcer = PathScopeEnforcer(config=config)
            allowed, reason = enforcer.check(os.path.join(tmpdir, "test.pyc"))
            assert not allowed, "Should block .pyc files"
            assert "pyc" in reason

    def test_path_outside_allowed(self):
        enforcer = PathScopeEnforcer()
        allowed, reason = enforcer.check("/etc/passwd")
        assert not allowed

    def test_restrict_function(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            config = PathScopeConfig(allowed_dirs=[tmpdir])
            enforcer = PathScopeEnforcer(config=config)
            valid_path = os.path.join(tmpdir, "valid.txt")
            assert enforcer.restrict(valid_path) == valid_path

    def test_add_allowed_dir(self):
        enforcer = PathScopeEnforcer()
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            enforcer.add_allowed_dir(tmpdir)
            allowed, _ = enforcer.check(os.path.join(tmpdir, "file.txt"))
            assert allowed

    def test_deep_path_blocked(self):
        config = PathScopeConfig(max_path_depth=10)
        enforcer = PathScopeEnforcer(config=config)
        deep = "/" + "/".join(["a"] * 20)
        allowed, reason = enforcer.check(deep)
        assert not allowed
        assert "depth" in reason
