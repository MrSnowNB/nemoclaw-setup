"""Abstract LLM provider protocol."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncIterator

from nemoclaw.models import Message, TokenUsage


class LLMProvider(ABC):
    """Protocol for LLM providers.

    Any OpenAI-compatible endpoint (Ollama, vLLM, OpenRouter, OpenAI)
    can implement this interface.
    """

    @abstractmethod
    async def chat_completion(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """Send a chat completion request (non-streaming).

        Returns the full response dict with 'choices' and 'usage'.
        """

    @abstractmethod
    async def chat_completion_stream(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[dict]:
        """Send a streaming chat completion request.

        Yields SSE chunk dicts with delta content and tool_calls.
        """

    @abstractmethod
    async def close(self) -> None:
        """Clean up resources."""

    def get_last_usage(self) -> TokenUsage:
        """Return token usage from the last non-streaming call."""
        return TokenUsage()
