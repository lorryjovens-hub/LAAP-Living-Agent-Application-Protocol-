"""Tests for LAAP Shell Sandbox"""
import pytest
import os, tempfile
from laap.shell.sandbox import Sandbox, SandboxConfig, IsolationLevel


class TestSandbox:
    def test_basic_validation(self):
        sandbox = Sandbox()
        allowed, reason = sandbox.validate("ls -la")
        assert allowed, "Should allow basic command"

    def test_block_dangerous(self):
        sandbox = Sandbox()
        allowed, _ = sandbox.validate("sudo rm -rf /")
        assert not allowed

    def test_timeout_validation(self):
        sandbox = Sandbox()
        allowed, reason = sandbox.validate("sleep 1", timeout=9999)
        assert not allowed

    def test_path_validation(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            config = SandboxConfig(allowed_paths=[tmpdir])
            sandbox = Sandbox(config=config)
            allowed, _ = sandbox.validate("ls", cwd=tmpdir)
            assert allowed

    def test_env_sanitization(self):
        sandbox = Sandbox()
        env = sandbox.sanitize_env({"CUSTOM_VAR": "test"})
        assert "CUSTOM_VAR" in env

    def test_empty_command(self):
        sandbox = Sandbox()
        allowed, reason = sandbox.validate("")
        assert not allowed

    def test_status_report(self):
        sandbox = Sandbox()
        status = sandbox.status
        assert "level" in status
        assert "allowed_commands" in status
