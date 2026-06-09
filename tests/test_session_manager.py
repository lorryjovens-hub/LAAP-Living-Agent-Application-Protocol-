"""Tests for LAAP Session Manager"""
import pytest
import tempfile, os
from laap.store.session_manager import (
    SessionManager, SessionStore, SessionRecord,
    SessionState, FileSessionStore,
)


class TestSessionManager:
    def test_create_session(self):
        sm = SessionManager()
        session = sm.create("test-session-1")
        assert session.session_id == "test-session-1"
        assert session.state == SessionState.ACTIVE

    def test_get_session(self):
        sm = SessionManager()
        sm.create("test-session-2")
        session = sm.get("test-session-2")
        assert session is not None
        assert session.session_id == "test-session-2"

    def test_close_session(self):
        sm = SessionManager()
        sm.create("test-session-3")
        sm.close("test-session-3")
        session = sm.get("test-session-3")
        assert session.state == SessionState.CLOSED

    def test_status(self):
        sm = SessionManager()
        sm.create("test-session-4")
        status = sm.status
        assert status["active"] >= 1


class TestFileSessionStore:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            store = FileSessionStore(storage_dir=tmpdir)
            record = SessionRecord(session_id="test-fs-1", summary="test")
            store.save(record)
            loaded = store.load("test-fs-1")
            assert loaded is not None
            assert loaded.summary == "test"

    def test_delete(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            store = FileSessionStore(storage_dir=tmpdir)
            record = SessionRecord(session_id="test-fs-del")
            store.save(record)
            assert store.delete("test-fs-del")
            assert not store.delete("nonexistent")

    def test_list_sessions(self):
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmpdir:
            store = FileSessionStore(storage_dir=tmpdir)
            store.save(SessionRecord(session_id="list-test-1"))
            store.save(SessionRecord(session_id="list-test-2"))
            sessions = store.list_sessions()
            assert len(sessions) >= 2
