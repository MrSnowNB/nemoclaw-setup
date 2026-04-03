"""Session manager — JSONL logging and session lifecycle.

Creates session directories under ~/.nemoclaw/sessions/YYYY-MM-DD_HHMMSS/,
writes every message exchange as JSONL, and manages session metadata.
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
    """Manages a single session's JSONL log and metadata."""

    def __init__(self, session_dir: Path, model: str = "", persona: str = "") -> None:
        self._base_dir = Path(session_dir).expanduser()
        self._model = model
        self._persona = persona
        self._session_path: Path | None = None
        self._log_file: Path | None = None
        self._metadata_file: Path | None = None
        self._message_count: int = 0
        self._session_id: str = ""
        self._started_at: str = ""

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def session_path(self) -> Path | None:
        return self._session_path

    @property
    def message_count(self) -> int:
        return self._message_count

    def start_new_session(self) -> Path:
        """Create a new session directory and initialize files."""
        now = datetime.now(timezone.utc)
        self._session_id = now.strftime("%Y-%m-%d_%H%M%S")
        self._started_at = now.isoformat()
        self._session_path = self._base_dir / self._session_id
        self._session_path.mkdir(parents=True, exist_ok=True)

        self._log_file = self._session_path / "messages.jsonl"
        self._metadata_file = self._session_path / "session.json"
        self._message_count = 0

        self._write_metadata()
        logger.info("Started session %s at %s", self._session_id, self._session_path)
        return self._session_path

    def resume_session(self, session_path: Path) -> int:
        """Resume an existing session, returning the message count loaded."""
        self._session_path = Path(session_path)
        self._log_file = self._session_path / "messages.jsonl"
        self._metadata_file = self._session_path / "session.json"

        # Load metadata
        if self._metadata_file.exists():
            meta = json.loads(self._metadata_file.read_text(encoding="utf-8"))
            self._session_id = meta.get("id", self._session_path.name)
            self._started_at = meta.get("started_at", "")
            self._message_count = meta.get("message_count", 0)
        else:
            self._session_id = self._session_path.name
            self._started_at = ""
            self._message_count = 0

        # Count existing lines
        if self._log_file.exists():
            with open(self._log_file, encoding="utf-8") as f:
                self._message_count = sum(1 for _ in f)

        logger.info("Resumed session %s (%d messages)", self._session_id, self._message_count)
        return self._message_count

    def log_message(self, message: Message) -> None:
        """Append a message to the JSONL log."""
        if self._log_file is None:
            return

        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": message.role,
            "content": message.content,
        }
        if message.tool_calls:
            entry["tool_calls"] = [
                {"id": tc.id, "name": tc.name, "arguments": tc.arguments}
                for tc in message.tool_calls
            ]
        if message.tool_call_id:
            entry["tool_call_id"] = message.tool_call_id

        with open(self._log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        self._message_count += 1
        self._write_metadata()

    def _write_metadata(self) -> None:
        """Write/update the session metadata file."""
        if self._metadata_file is None:
            return

        meta = {
            "id": self._session_id,
            "started_at": self._started_at,
            "model": self._model,
            "persona": self._persona,
            "message_count": self._message_count,
        }
        self._metadata_file.write_text(
            json.dumps(meta, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
