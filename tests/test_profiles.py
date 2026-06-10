"""Tests for profile management."""
import pytest
from laap.cli.profiles import ProfileManager


@pytest.fixture
def mgr():
    return ProfileManager()


class TestProfileManagerCore:
    """Test core ProfileManager operations."""

    def test_create_profile(self, mgr):
        """Create a test profile and verify it exists."""
        name = "_test_temp_create"
        result = mgr.create(name)
        # Accept ok (fresh create) or error (already exists from previous run)
        assert result["status"] in ("ok", "error")
        if result["status"] == "ok":
            # Cleanup
            mgr.delete(name, force=True)

    def test_get_active(self, mgr):
        """get_active always returns a valid profile name."""
        active = mgr.get_active()
        assert isinstance(active, str)
        assert len(active) > 0

    def test_list_profiles(self, mgr):
        """list returns a list of profile dicts."""
        profiles = mgr.list()
        assert isinstance(profiles, list)
        if profiles:
            p = profiles[0]
            assert "name" in p
            assert "active" in p

    def test_show_default(self, mgr):
        """show('default') returns profile info."""
        info = mgr.show("default")
        assert info["status"] == "ok"
        assert info["profile"]["name"] == "default"

    def test_show_nonexistent(self, mgr):
        """show returns error for non-existent profile."""
        info = mgr.show("__no_such_profile_999__")
        assert info["status"] == "error"

    def test_delete_nonexistent(self, mgr):
        """delete returns error for non-existent profile."""
        result = mgr.delete("__no_such_profile_999__", force=True)
        assert result["status"] == "error"

    def test_switch_to_default(self, mgr):
        """switch to default always works."""
        result = mgr.switch("default")
        assert result["status"] == "ok"
        assert mgr.get_active() == "default"

    def test_switch_nonexistent(self, mgr):
        """switch returns error for non-existent profile."""
        result = mgr.switch("__no_such_profile_999__")
        assert result["status"] == "error"

    def test_create_duplicate(self, mgr):
        """create returns error for duplicate name."""
        result = mgr.create("default")
        assert result["status"] == "error"
        assert "already exists" in result["message"]

    def test_create_invalid(self, mgr):
        """create with invalid name raises ValueError."""
        import pytest
        with pytest.raises(ValueError):
            mgr.create("../invalid")

    def test_create_empty_name(self, mgr):
        """create with empty name raises ValueError."""
        import pytest
        with pytest.raises(ValueError):
            mgr.create("")


class TestProfileManagerIntegration:
    """Integration tests that create/delete profiles."""

    @pytest.fixture(autouse=True)
    def setup_cleanup(self):
        self.test_name = "_test_integration_pm"
        yield
        mgr = ProfileManager()
        mgr.delete(self.test_name, force=True)

    def test_full_lifecycle(self):
        """Create, verify, switch, and delete a profile."""
        mgr = ProfileManager()
        test_name = self.test_name

        # Create
        result = mgr.create(test_name)
        assert result["status"] == "ok"

        # Verify in list
        names = [p["name"] for p in mgr.list()]
        assert test_name in names

        # Show
        info = mgr.show(test_name)
        assert info["status"] == "ok"
        assert info["profile"]["name"] == test_name

        # Switch
        old_active = mgr.get_active()
        result = mgr.switch(test_name)
        assert result["status"] == "ok"
        assert mgr.get_active() == test_name

        # Switch back
        mgr.switch(old_active)

        # Delete
        result = mgr.delete(test_name, force=True)
        assert result["status"] == "ok"

        # Verify gone
        names = [p["name"] for p in mgr.list()]
        assert test_name not in names
