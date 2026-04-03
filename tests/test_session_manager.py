"""Tests for session manager and session loader."""

import json
import pytest
from pathlib import Path

from nemoclaw.models import ToolCall
from nemoclaw.session.loader import find_latest_session, list_sessions, load_messages_from_jsonl
from nemoclaw.session.manager import SessionManager


@pytest.fixture
def sessions_dir(tmp_path: Path) -> Path:
    """Create a temporary sessions directory."""
    sess_dir = tmp_path / "sessions"
    sess_dir.mkdir()
    return sess_dir


@pytest.fixture
def manager(sessions_dir: Path) -> SessionManager:
    """Create a SessionManager with a temporary directory."""
    return SessionManager(
        sessions_dir=sessions_dir,
        model="test-model",
        persona="test-persona",
    )


class TestSessionManager:
    """Test SessionManager."""

    def test_start_new_session(self, manager: SessionManager) -> None:
        session_id = manager.start_new_session()
        assert session_id
        assert manager.session_path.exists()
        assert (manager.session_path / "session.json").exists()

    def test_session_metadata(self, manager: SessionManager) -> None:
        manager.start_new_session()
        meta_path = manager.session_path / "session.json"
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["model"] == "test-model"
        assert meta["persona"] == "test-persona"
        assert meta["message_count"] == 0

    def test_log_message(self, manager: SessionManager) -> None:
        manager.start_new_session()
        manager.log_message("user", "Hello!")
        manager.log_message("assistant", "Hi there!")

        assert manager.message_count == 2

        # Verify JSONL file
        with open(manager.messages_file) as f:
            lines = f.readlines()
        assert len(lines) == 2

        msg1 = json.loads(lines[0])
        assert msg1["role"] == "user"
        assert msg1["content"] == "Hello!"

    def test_log_message_with_tool_calls(self, manager: SessionManager) -> None:
        manager.start_new_session()
        tc = ToolCall(id="tc1", name="read_file", arguments={"path": "/tmp/test"})
        manager.log_message("assistant", "Let me read that.", tool_calls=[tc])

        with open(manager.messages_file) as f:
            entry = json.loads(f.readline())
        assert entry["tool_calls"][0]["name"] == "read_file"

    def test_resume_session(self, manager: SessionManager, sessions_dir: Path) -> None:
        session_id = manager.start_new_session()
        manager.log_message("user", "First message")
        manager.log_message("assistant", "First response")

        # Create a new manager and resume
        mgr2 = SessionManager(sessions_dir=sessions_dir)
        messages = mgr2.resume_session(session_id)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "First message"

    def test_resume_nonexistent_session(self, manager: SessionManager) -> None:
        with pytest.raises(FileNotFoundError):
            manager.resume_session("nonexistent-session")

    def test_continue_last_session(self, manager: SessionManager, sessions_dir: Path) -> None:
        session_id = manager.start_new_session()
        manager.log_message("user", "Test message")

        mgr2 = SessionManager(sessions_dir=sessions_dir)
        messages = mgr2.continue_last_session()
        assert len(messages) == 1

    def test_continue_no_sessions(self, sessions_dir: Path) -> None:
        mgr = SessionManager(sessions_dir=sessions_dir)
        with pytest.raises(FileNotFoundError):
            mgr.continue_last_session()

    def test_message_count_updates_metadata(self, manager: SessionManager) -> None:
        manager.start_new_session()
        manager.log_message("user", "msg1")
        manager.log_message("assistant", "msg2")

        meta_path = manager.session_path / "session.json"
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["message_count"] == 2


class TestSessionLoader:
    """Test session loader functions."""

    def test_load_messages_from_jsonl(self, tmp_path: Path) -> None:
        jsonl_path = tmp_path / "messages.jsonl"
        entries = [
            {"timestamp": "2026-01-01T00:00:00Z", "role": "user", "content": "Hi"},
            {"timestamp": "2026-01-01T00:00:01Z", "role": "assistant", "content": "Hello!"},
        ]
        with open(jsonl_path, "w") as f:
            for entry in entries:
                f.write(json.dumps(entry) + "\n")

        messages = load_messages_from_jsonl(jsonl_path)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[1].content == "Hello!"

    def test_load_messages_empty_file(self, tmp_path: Path) -> None:
        jsonl_path = tmp_path / "messages.jsonl"
        jsonl_path.write_text("")
        messages = load_messages_from_jsonl(jsonl_path)
        assert messages == []

    def test_load_messages_missing_file(self, tmp_path: Path) -> None:
        jsonl_path = tmp_path / "nonexistent.jsonl"
        messages = load_messages_from_jsonl(jsonl_path)
        assert messages == []

    def test_find_latest_session(self, sessions_dir: Path) -> None:
        (sessions_dir / "2026-01-01_000000").mkdir()
        (sessions_dir / "2026-01-02_120000").mkdir()
        (sessions_dir / "2026-01-01_120000").mkdir()

        latest = find_latest_session(sessions_dir)
        assert latest == "2026-01-02_120000"

    def test_find_latest_session_empty(self, sessions_dir: Path) -> None:
        assert find_latest_session(sessions_dir) is None

    def test_list_sessions(self, sessions_dir: Path) -> None:
        d1 = sessions_dir / "2026-01-01_000000"
        d1.mkdir()
        with open(d1 / "session.json", "w") as f:
            json.dump({"id": "2026-01-01_000000", "message_count": 5}, f)

        d2 = sessions_dir / "2026-01-02_000000"
        d2.mkdir()

        sessions = list_sessions(sessions_dir)
        assert len(sessions) == 2
