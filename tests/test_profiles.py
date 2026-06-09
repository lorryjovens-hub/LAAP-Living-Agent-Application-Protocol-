"""Tests for profile management."""
import pytest
import os
import json
import tempfile
from pathlib import Path


class TestProfileManager:
    """Test ProfileManager operations."""

    @pytest.fixture
    def manager(self):
        from laap.cli.profiles import ProfileManager
        with tempfile.TemporaryDirectory() as tmpdir:
            laap_home = Path(tmpdir)
            mgr = ProfileManager(laap_home)
            # Override paths for testing
            mgr._profiles_dir = laap_home / "profiles"
            mgr._active_file = laap_home / "active_profile"
            yield mgr

    def test_create_profile(self, manager):
        mgr = manager
        result = mgr.create("test-profile")
        assert result is True
        profile_dir = mgr._profiles_dir / "test-profile"
        assert profile_dir.exists()
        assert (profile_dir / "config.yaml").exists()
        assert (profile_dir / "sessions").exists()
        assert (profile_dir / "skills").exists()

    def test_list_profiles(self, manager):
        mgr = manager
        mgr.create("profile-a")
        mgr.create("profile-b")
        profiles = mgr.list()
        names = [p["name"] for p in profiles]
        assert "profile-a" in names
        assert "profile-b" in names
        assert "default" in names  # auto-created

    def test_delete_profile(self, manager):
        mgr = manager
        mgr.create("to-delete")
        assert (mgr._profiles_dir / "to-delete").exists()
        result = mgr.delete("to-delete")
        assert result is True
        assert not (mgr._profiles_dir / "to-delete").exists()

    def test_delete_default_protected(self, manager):
        mgr = manager
        # Default should be auto-created
        mgr._get_or_create_default()
        result = mgr.delete("default")
        assert result is False  # Cannot delete default

    def test_delete_nonexistent(self, manager):
        mgr = manager
        result = mgr.delete("no-such-profile")
        assert result is False

    def test_get_active_default(self, manager):
        mgr = manager
        active = mgr.get_active()
        assert active == "default"

    def test_switch_profile(self, manager):
        mgr = manager
        mgr.create("switched")
        result = mgr.switch("switched")
        assert result is True
        active = mgr.get_active()
        assert active == "switched"

    def test_show_profile(self, manager):
        mgr = manager
        mgr.create("visible")
        info = mgr.show("visible")
        assert info["name"] == "visible"
        assert "created_at" in info
        assert "exists" not in info or info.get("exists", True) is not False

    def test_show_nonexistent(self, manager):
        mgr = manager
        info = mgr.show("no-such")
        assert info is None or info.get("exists") == False

    def test_create_without_name(self, manager):
        mgr = manager
        result = mgr.create("")
        assert result is False

    def test_create_invalid_name(self, manager):
        mgr = manager
        # Names with path separators should be rejected
        result = mgr.create("../escape")
        assert result is False

    def test_export_profile(self, manager):
        import tarfile
        mgr = manager
        mgr.create("exportable")
        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "exported.tar.gz"
            result = mgr.export("exportable", str(out_path))
            assert result is True
            assert out_path.exists()
            # Verify it's a valid tar.gz
            with tarfile.open(str(out_path), "r:gz") as tar:
                names = tar.getnames()
                assert len(names) > 0

    def test_duplicate_create(self, manager):
        mgr = manager
        mgr.create("unique")
        result = mgr.create("unique")  # Second time
        assert result is True  # Should succeed (or return True if exists)

    def test_list_after_delete(self, manager):
        mgr = manager
        mgr.create("temp")
        mgr.delete("temp")
        profiles = mgr.list()
        names = [p["name"] for p in profiles]
        assert "temp" not in names

    def test_profile_dir_isolation(self, manager):
        mgr = manager
        mgr.create("alpha")
        mgr.create("beta")
        alpha_dir = mgr._profiles_dir / "alpha"
        beta_dir = mgr._profiles_dir / "beta"
        # Config files should be independent
        cfg_a = alpha_dir / "config.yaml"
        cfg_b = beta_dir / "config.yaml"
        cfg_a.write_text("alpha_config: true")
        cfg_b.write_text("beta_config: true")
        assert cfg_a.read_text() != cfg_b.read_text()
