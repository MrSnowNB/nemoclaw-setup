"""LLM provider registry and factory."""

from __future__ import annotations

from nemoclaw.config import Settings
from nemoclaw.llm.base import LLMProvider
from nemoclaw.llm.openai_compat import OpenAICompatClient


def create_llm_provider(settings: Settings) -> LLMProvider:
    """Create an LLM provider from settings.

    Currently only the OpenAI-compatible client is implemented,
    which covers Ollama, vLLM, OpenRouter, and OpenAI.
    """
    return OpenAICompatClient(
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
    )
