"""Three-tier memory store.

Tier 1: MEMORY.md — short pointers (~150 chars each), always in system prompt.
Tier 2: memory/topics/ — detailed topic files, loaded on demand.
Tier 3: Session transcripts — raw JSONL, search-only.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from nemoclaw.memory.base import MemoryProvider

logger = logging.getLogger(__name__)

# Tier 1 limits
MAX_MEMORY_ENTRIES = 50
MAX_ENTRY_LENGTH = 150


class MemoryStore(MemoryProvider):
    """Manages the three-tier memory architecture."""

    def __init__(self, memory_dir: Path, sessions_dir: Path | None = None) -> None:
        self.memory_dir = memory_dir
        self.sessions_dir = sessions_dir
        self.memory_file = memory_dir / "MEMORY.md"
        self.topics_dir = memory_dir / "topics"

        # Ensure directories exist
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.topics_dir.mkdir(parents=True, exist_ok=True)

    # ── Tier 1: MEMORY.md ───────────────────────────────────────────

    def get_memory_block(self) -> str:
        """Read MEMORY.md and return its content for system prompt injection."""
        if not self.memory_file.exists():
            return "No memory loaded for this session."
        content = self.memory_file.read_text(encoding="utf-8").strip()
        return content if content else "No memory loaded for this session."

    def get_entries(self) -> list[str]:
        """Parse MEMORY.md into a list of entries."""
        if not self.memory_file.exists():
            return []
        content = self.memory_file.read_text(encoding="utf-8")
        entries = []
        for line in content.splitlines():
            line = line.strip()
            if line.startswith("- "):
                entries.append(line[2:])
        return entries

    def remember(self, content: str, category: str = "general") -> str:
        """Add a fact to Tier 1 MEMORY.md.

        Returns a confirmation message.
        """
        entry = f"[{category}] {content}"
        if len(entry) > MAX_ENTRY_LENGTH:
            entry = entry[:MAX_ENTRY_LENGTH]

        entries = self.get_entries()

        # Check for duplicates
        for existing in entries:
            if content.lower() in existing.lower():
                return f"Already remembered: {existing}"

        # Evict oldest if at capacity
        if len(entries) >= MAX_MEMORY_ENTRIES:
            entries.pop(0)

        entries.append(entry)
        self._write_entries(entries)
        logger.info("Remembered: %s", entry)
        return f"Remembered: {entry}"

    def forget(self, content: str) -> str:
        """Remove entries matching content from Tier 1 MEMORY.md."""
        entries = self.get_entries()
        original_count = len(entries)
        entries = [e for e in entries if content.lower() not in e.lower()]
        removed = original_count - len(entries)

        if removed == 0:
            return f"No matching entries found for: {content}"

        self._write_entries(entries)
        logger.info("Forgot %d entries matching: %s", removed, content)
        return f"Forgot {removed} entries matching: {content}"

    def _write_entries(self, entries: list[str]) -> None:
        """Write entries back to MEMORY.md."""
        lines = [f"- {entry}" for entry in entries]
        self.memory_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # ── Tier 2: Topic Files ─────────────────────────────────────────

    def write_topic(self, topic: str, content: str) -> str:
        """Create or update a topic file in Tier 2."""
        slug = self._slugify(topic)
        topic_file = self.topics_dir / f"{slug}.md"
        topic_file.write_text(
            f"# {topic}\n\n{content}\n",
            encoding="utf-8",
        )
        logger.info("Wrote topic file: %s", topic_file)
        return f"Saved topic '{topic}' to {slug}.md"

    def read_topic(self, topic: str) -> str | None:
        """Read a topic file from Tier 2."""
        slug = self._slugify(topic)
        topic_file = self.topics_dir / f"{slug}.md"
        if topic_file.exists():
            return topic_file.read_text(encoding="utf-8")
        return None

    def list_topics(self) -> list[str]:
        """List all available topic slugs."""
        return [f.stem for f in self.topics_dir.glob("*.md")]

    # ── Tier 3: Session Transcript Search ───────────────────────────

    def search_sessions(self, query: str, max_results: int = 10) -> list[dict]:
        """Search across session JSONL transcripts for keyword matches."""
        results: list[dict] = []
        if not self.sessions_dir or not self.sessions_dir.exists():
            return results

        query_lower = query.lower()
        for session_dir in sorted(self.sessions_dir.iterdir(), reverse=True):
            jsonl_file = session_dir / "messages.jsonl"
            if not jsonl_file.exists():
                continue

            import json

            with open(jsonl_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                    except Exception:
                        continue
                    content = entry.get("content", "") or ""
                    if query_lower in content.lower():
                        results.append({
                            "session": session_dir.name,
                            "role": entry.get("role", ""),
                            "content": content[:200],
                            "timestamp": entry.get("timestamp", ""),
                        })
                        if len(results) >= max_results:
                            return results

        return results

    # ── Cross-tier Search ───────────────────────────────────────────

    def search(self, query: str) -> list[dict]:
        """Search across all three memory tiers."""
        results: list[dict] = []
        query_lower = query.lower()

        # Tier 1: MEMORY.md entries
        for entry in self.get_entries():
            if query_lower in entry.lower():
                results.append({"tier": 1, "source": "MEMORY.md", "content": entry})

        # Tier 2: Topic files
        for topic_file in self.topics_dir.glob("*.md"):
            content = topic_file.read_text(encoding="utf-8")
            if query_lower in content.lower():
                # Extract matching lines for context
                matching_lines = [
                    line.strip()
                    for line in content.splitlines()
                    if query_lower in line.lower()
                ]
                results.append({
                    "tier": 2,
                    "source": f"topics/{topic_file.name}",
                    "content": "\n".join(matching_lines[:5]),
                })

        # Tier 3: Session transcripts
        session_results = self.search_sessions(query, max_results=5)
        for sr in session_results:
            results.append({
                "tier": 3,
                "source": f"session/{sr['session']}",
                "content": sr["content"],
            })

        return results

    @staticmethod
    def _slugify(text: str) -> str:
        """Convert text to a filesystem-safe slug."""
        slug = text.lower().strip()
        slug = re.sub(r"[^\w\s-]", "", slug)
        slug = re.sub(r"[\s_-]+", "-", slug)
        return slug.strip("-")[:64]
