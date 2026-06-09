"""Test session persistence system"""
import sys, tempfile
sys.path.insert(0, r"D:\LAAP")
from pathlib import Path
from laap.store.session import AoDB
from laap.store.session_manager import SessionManager
from tests.fixtures import create_test_agent


def test_aodb_create_session():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db = AoDB(db_path=Path(tmp) / "state.db")
        ok = db.create_session("test-1", name="Test Session", source="cli")
        assert ok
        s = db.get_session("test-1")
        assert s is not None
        assert s["name"] == "Test Session"
        db.close()


def test_aodb_duplicate_session():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db = AoDB(db_path=Path(tmp) / "state.db")
        db.create_session("dup-session")
        ok = db.create_session("dup-session")
        assert not ok
        db.close()


def test_aodb_list_sessions():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db = AoDB(db_path=Path(tmp) / "state.db")
        for i in range(3):
            db.create_session(f"session-{i}")
        assert len(db.list_sessions()) == 3
        db.close()


def test_aodb_append_and_get_messages():
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db = AoDB(db_path=Path(tmp) / "state.db")
        db.create_session("msg-test")
        db.append_message("msg-test", "user", "Hello!")
        db.append_message("msg-test", "assistant", "Hi there!")
        msgs = db.get_messages("msg-test")
        assert len(msgs) == 2
        db.close()


def test_session_save_agent_state():
    """SessionManager should save agent cognitive state"""
    import os
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        os.chdir(tmp)
        sm = SessionManager()
        agent = create_test_agent()
        path = sm.save_agent_state("test-save", agent)
        assert path is not None
        assert Path(path).exists()


def test_session_load_agent_state():
    """SessionManager should load agent cognitive state"""
    import os
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        os.chdir(tmp)
        sm = SessionManager()
        agent = create_test_agent()
        agent.config.exploration_rate = 0.42
        agent.step_count = 15
        sm.save_agent_state("load-test", agent)
        restored = create_test_agent()
        ok = sm.load_agent_state("load-test", restored)
        assert ok
        assert restored.config.exploration_rate == 0.42
        assert restored.step_count == 15


def test_session_list_agent_states():
    import os
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        os.chdir(tmp)
        sm = SessionManager()
        sm.save_agent_state("state-a", create_test_agent())
        sm.save_agent_state("state-b", create_test_agent())
        states = sm.list_agent_states()
        assert len(states) == 2


def test_session_delete_agent_state():
    import os
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        os.chdir(tmp)
        sm = SessionManager()
        sm.save_agent_state("delete-me", create_test_agent())
        assert sm.delete_agent_state("delete-me")
        assert not sm.list_agent_states()
