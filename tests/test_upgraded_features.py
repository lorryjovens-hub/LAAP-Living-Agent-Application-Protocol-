"""Tests for threat detection, permissions, commands, memory, markdown."""
import pytest, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

class TestThreatDetection:
    def test_dangerous_rm(self):
        from laap.tools.threat_patterns import check_command_safety
        w = check_command_safety("rm -rf /")
        assert len(w) >= 1

    def test_safe_command(self):
        from laap.tools.threat_patterns import check_command_safety
        assert len(check_command_safety("ls -la")) == 0

class TestPermissions:
    def test_init(self):
        from laap.permissions.enforcer import PermissionEnforcer
        assert PermissionEnforcer() is not None

    def test_add_rule(self):
        from laap.permissions.enforcer import PermissionEnforcer, AccessLevel, PermissionRule
        e = PermissionEnforcer()
        e.add_rule("x", PermissionRule("x", AccessLevel.DENY))
        assert e.check("x") == AccessLevel.DENY

class TestCommands:
    def test_resolve(self):
        from laap.cli.commands import resolve
        assert resolve("help") == "help"

    def test_help_text(self):
        from laap.cli.commands import help_text
        assert "help" in help_text()

class TestMemory:
    def test_store_recall(self):
        import tempfile
        from pathlib import Path
        from laap.memory.persistent import PersistentMemoryEngine, MemoryEntry
        d = Path(tempfile.mkdtemp()) / "m.db"
        if d.exists(): d.unlink()
        e = PersistentMemoryEngine(d)
        e.store(MemoryEntry(content="Test memory"))
        assert e.count() == 1
        e.close()

    def test_delete(self):
        import tempfile
        from pathlib import Path
        from laap.memory.persistent import PersistentMemoryEngine, MemoryEntry
        d = Path(tempfile.mkdtemp()) / "m2.db"
        if d.exists(): d.unlink()
        e = PersistentMemoryEngine(d)
        i = e.store(MemoryEntry(content="Delete me"))
        assert e.delete(i)
        e.close()
