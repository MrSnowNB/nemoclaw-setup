"""Context compaction — manages token budget for long conversations.

Strategies:
1. Tool result trimming — truncate old tool results to summaries
2. Conversation summarization — compress older messages
3. Memory extraction — extract key facts before compacting

Token estimation uses word_count * 1.3 (no external dependency).
"""

from __future__ import annotations

import logging
from typing import Any

from nemoclaw.models import Message

logger = logging.getLogger(__name__)

# Approximate tokens per word for estimation (good enough for English)
_TOKENS_PER_WORD = 1.3

# How many recent turns to keep untouched
_KEEP_RECENT_TURNS = 6

# Max length for trimmed tool results
_TOOL_RESULT_MAX_CHARS = 200


def estimate_tokens(text: str) -> int:
    """Estimate token count from text using word count heuristic."""
    if not text:
        return 0
    return int(len(text.split()) * _TOKENS_PER_WORD)


def estimate_messages_tokens(messages: list[Message]) -> int:
    """Estimate total tokens across a list of messages."""
    total = 0
    for msg in messages:
        if msg.content:
            total += estimate_tokens(msg.content)
        if msg.tool_calls:
            for tc in msg.tool_calls:
                total += estimate_tokens(str(tc.arguments))
    return total


class CompactionManager:
    """Monitors context size and compacts conversation history when needed."""

    def __init__(
        self,
        max_context_tokens: int = 32768,
        trigger_ratio: float = 0.7,
        keep_recent_turns: int = _KEEP_RECENT_TURNS,
    ) -> None:
        self._max_tokens = max_context_tokens
        self._trigger_threshold = int(max_context_tokens * trigger_ratio)
        self._keep_recent = keep_recent_turns

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def trigger_threshold(self) -> int:
        return self._trigger_threshold

    def needs_compaction(self, messages: list[Message], system_prompt: str = "") -> bool:
        """Check if the context exceeds the trigger threshold."""
        total = estimate_tokens(system_prompt) + estimate_messages_tokens(messages)
        return total > self._trigger_threshold

    def compact(self, messages: list[Message]) -> list[Message]:
        """Apply compaction strategies to reduce context size.

        Strategies applied in order:
        1. Trim old tool results to summaries
        2. Summarize old conversation turns into a single summary message

        The most recent `keep_recent_turns` messages are always preserved.

        Args:
            messages: The conversation history (excluding system prompt).

        Returns:
            A new list of messages with compacted older context.
        """
        if len(messages) <= self._keep_recent:
            return messages  # Nothing to compact

        # Split into old and recent
        old = messages[:-self._keep_recent]
        recent = messages[-self._keep_recent:]

        # Strategy 1: Trim tool results in old messages
        trimmed_old = self._trim_tool_results(old)

        # Strategy 2: Summarize old conversation if still too large
        old_tokens = estimate_messages_tokens(trimmed_old)
        if old_tokens > self._trigger_threshold // 2:
            summary = self._summarize_messages(trimmed_old)
            compacted = [
                Message(
                    role="system",
                    content=f"[Conversation summary of {len(trimmed_old)} earlier messages]\n{summary}",
                ),
            ]
        else:
            compacted = trimmed_old

        return compacted + recent

    def _trim_tool_results(self, messages: list[Message]) -> list[Message]:
        """Truncate tool result messages to short summaries."""
        result: list[Message] = []
        for msg in messages:
            if msg.role == "tool" and msg.content and len(msg.content) > _TOOL_RESULT_MAX_CHARS:
                trimmed = msg.content[:_TOOL_RESULT_MAX_CHARS] + "... [truncated]"
                result.append(Message(
                    role=msg.role,
                    content=trimmed,
                    tool_call_id=msg.tool_call_id,
                ))
            else:
                result.append(msg)
        return result

    def _summarize_messages(self, messages: list[Message]) -> str:
        """Create a text summary of messages.

        This is a simple extractive summary (no LLM call).
        Extracts user questions and final assistant responses.
        """
        parts: list[str] = []
        for msg in messages:
            if msg.role == "user" and msg.content:
                text = msg.content[:150]
                parts.append(f"User asked: {text}")
            elif msg.role == "assistant" and msg.content and not msg.tool_calls:
                text = msg.content[:150]
                parts.append(f"Assistant replied: {text}")
        return "\n".join(parts) if parts else "Prior conversation occurred but details were compacted."

    def extract_facts(self, messages: list[Message]) -> list[str]:
        """Extract key facts from messages that should be persisted to memory.

        Simple heuristic: extract statements from assistant messages
        that look like facts (contain 'is', 'are', 'has', 'prefers', etc.).
        """
        facts: list[str] = []
        fact_indicators = ("is ", "are ", "has ", "prefers ", "likes ", "works ", "lives ")
        for msg in messages:
            if msg.role == "assistant" and msg.content:
                for sentence in msg.content.split(". "):
                    sentence = sentence.strip()
                    if any(ind in sentence.lower() for ind in fact_indicators) and len(sentence) < 150:
                        facts.append(sentence)
        return facts[:10]  # Cap at 10 facts per compaction
