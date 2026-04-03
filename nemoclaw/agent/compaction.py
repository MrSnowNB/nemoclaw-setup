"""Context compaction — manages context window size.

Strategies:
1. Tool result trimming — truncate old tool results to summaries.
2. Conversation summarization — summarize older messages when context exceeds threshold.
3. Memory extraction — extract key facts into MEMORY.md before compacting.

Token estimation uses word_count * 1.3 (no external dependency).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from nemoclaw.models import Message

if TYPE_CHECKING:
    from nemoclaw.memory.store import MemoryStore

logger = logging.getLogger(__name__)

# Token estimation factor: roughly 1.3 tokens per word for English text
TOKEN_FACTOR = 1.3


def estimate_tokens(text: str) -> int:
    """Estimate token count from text using word count heuristic."""
    if not text:
        return 0
    return int(len(text.split()) * TOKEN_FACTOR)


def estimate_messages_tokens(messages: list[Message]) -> int:
    """Estimate total token count for a list of messages."""
    total = 0
    for msg in messages:
        if msg.content:
            total += estimate_tokens(msg.content)
        if msg.tool_calls:
            for tc in msg.tool_calls:
                total += estimate_tokens(str(tc.arguments))
    return total


class CompactionManager:
    """Monitors context size and applies compaction strategies."""

    def __init__(
        self,
        max_context_tokens: int = 32768,
        threshold_ratio: float = 0.7,
        memory_store: MemoryStore | None = None,
    ) -> None:
        self.max_context_tokens = max_context_tokens
        self.threshold = int(max_context_tokens * threshold_ratio)
        self.memory_store = memory_store

    def needs_compaction(self, system_prompt: str, history: list[Message]) -> bool:
        """Check if the context exceeds the compaction threshold."""
        total = estimate_tokens(system_prompt) + estimate_messages_tokens(history)
        return total > self.threshold

    def compact(self, system_prompt: str, history: list[Message]) -> list[Message]:
        """Apply compaction strategies to reduce context size.

        Modifies history in place and returns it. The system prompt is NOT
        modified (persona is pinned).

        Strategy order:
        1. Trim old tool results
        2. Summarize old conversation turns
        """
        if not self.needs_compaction(system_prompt, history):
            return history

        logger.info(
            "Context compaction triggered (estimated %d tokens, threshold %d)",
            estimate_tokens(system_prompt) + estimate_messages_tokens(history),
            self.threshold,
        )

        # Strategy 1: Trim old tool results (keep last 5 tool exchanges)
        history = self._trim_tool_results(history)

        # Strategy 2: Summarize old conversation if still over threshold
        if self.needs_compaction(system_prompt, history):
            history = self._summarize_old_messages(history)

        return history

    def _trim_tool_results(self, history: list[Message]) -> list[Message]:
        """Truncate old tool result messages to short summaries."""
        # Find tool messages and keep only the last 5 with full content
        tool_indices = [
            i for i, m in enumerate(history) if m.role == "tool"
        ]

        if len(tool_indices) <= 5:
            return history

        # Truncate older tool results
        cutoff = tool_indices[-5]
        for i in tool_indices:
            if i < cutoff and history[i].content:
                original_len = len(history[i].content)
                history[i] = Message(
                    role=history[i].role,
                    content=f"[Tool result truncated — was {original_len} chars]",
                    tool_call_id=history[i].tool_call_id,
                )

        logger.debug("Trimmed %d old tool results", len(tool_indices) - 5)
        return history

    def _summarize_old_messages(self, history: list[Message]) -> list[Message]:
        """Summarize older user/assistant message pairs into a single summary.

        Keeps the most recent 10 messages intact.
        """
        if len(history) <= 10:
            return history

        # Keep last 10 messages, summarize the rest
        old_messages = history[:-10]
        recent_messages = history[-10:]

        # Build a simple summary from old messages
        summary_parts: list[str] = []
        for msg in old_messages:
            if msg.role in ("user", "assistant") and msg.content:
                prefix = "User" if msg.role == "user" else "Assistant"
                snippet = msg.content[:100]
                if len(msg.content) > 100:
                    snippet += "..."
                summary_parts.append(f"- {prefix}: {snippet}")

        if summary_parts:
            summary = "Summary of earlier conversation:\n" + "\n".join(summary_parts)

            # Extract facts to memory if available
            if self.memory_store:
                self._extract_facts_to_memory(old_messages)

            summarized = [Message(role="system", content=summary)]
            return summarized + recent_messages

        return history

    def _extract_facts_to_memory(self, messages: list[Message]) -> None:
        """Extract key facts from messages and save to MEMORY.md."""
        # Simple heuristic: save user messages that mention names, preferences, etc.
        for msg in messages:
            if msg.role == "user" and msg.content:
                content = msg.content
                # Only extract from substantive messages
                if len(content) > 50:
                    # Save a shortened version as a memory entry
                    snippet = content[:120]
                    self.memory_store.remember(snippet, category="conversation")
