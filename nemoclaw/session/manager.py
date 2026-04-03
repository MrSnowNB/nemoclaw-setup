"""Session manager — JSONL-based session persistence.

Creates a session directory under ~/.nemoclaw/sessions/YYYY-MM-DD_HHMMSS/,
writes every message exchange as JSONL, and supports --continue/--resume.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from nemoclaw.models import Message, ToolCall

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages session persistence via JSONL files.

    Each session lives in its own directory with:
    - session.json: metadata (id, started_at, model, persona, message_count)
    - messages.jsonl: one JSON object per line for each message
    """

    def __init__(self, sessions_dir: Path, model: str = "", persona: str = "") -> None:
        self.sessions_dir = sessions_dir
        self.model = model
        self.persona = persona
        self.session_id: str = ""
        self.session_path: Path = Path()
        self.messages_file: Path = Path()
        self.message_count: int = 0

    def start_new_session(self) -> str:
        """Create a new session directory and metadata file."""
        now = datetime.now(timezone.utc)
        self.session_id = now.strftime("%Y-%m-%d_%H%M%S")
        self.session_path = self.sessions_dir / self.session_id
        self.session_path.mkdir(parents=True, exist_ok=True)
        self.messages_file = self.session_path / "messages.jsonl"
        self.message_count = 0

        metadata = {
            "id": self.session_id,
            "started_at": now.isoformat(),
            "model": self.model,
            "persona": self.persona,
            "message_count": 0,
        }
        self._write_metadata(metadata)
        logger.info("Started new session: %s", self.session_id)
        return self.session_id

    def resume_session(self, session_id: str) -> list[Message]:
        """Resume a specific session by ID, loading its history."""
        self.session_id = session_id
        self.session_path = self.sessions_dir / session_id
        self.messages_file = self.session_path / "messages.jsonl"

        if not self.session_path.exists():
            raise FileNotFoundError(f"Session not found: {session_id}")

        from nemoclaw.session.loader import load_messages_from_jsonl

        messages = load_messages_from_jsonl(self.messages_file)
        self.message_count = len(messages)
        logger.info("Resumed session %s with %d messages", session_id, self.message_count)
        return messages

    def continue_last_session(self) -> list[Message]:
        """Resume the most recent session."""
        from nemoclaw.session.loader import find_latest_session

        latest = find_latest_session(self.sessions_dir)
        if latest is None:
            raise FileNotFoundError("No previous sessions found")
        return self.resume_session(latest)

    def log_message(
        self,
        role: str,
        content: str | None = None,
        tool_calls: list[ToolCall] | None = None,
        tool_call_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Append a message to the JSONL log."""
        if not self.session_id:
            raise RuntimeError(
                "SessionManager: call start_new_session() or resume_session() before log_message()"
            )
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "content": content,
        }
        if tool_calls:
            entry["tool_calls"] = [tc.model_dump() for tc in tool_calls]
        if tool_call_id:
            entry["tool_call_id"] = tool_call_id
        if metadata:
            entry["metadata"] = metadata

        with open(self.messages_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        self.message_count += 1
        if self.message_count % 10 == 0:
            self.flush_metadata()

    def flush_metadata(self) -> None:
        """Flush the current message_count to session.json."""
        meta_path = self.session_path / "session.json"
        if meta_path.exists():
            with open(meta_path) as f:
                metadata = json.load(f)
            metadata["message_count"] = self.message_count
            self._write_metadata(metadata)

    def _write_metadata(self, metadata: dict[str, Any]) -> None:
        """Write session metadata to session.json."""
        meta_path = self.session_path / "session.json"
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
