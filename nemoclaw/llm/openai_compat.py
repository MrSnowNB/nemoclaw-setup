"""OpenAI-compatible LLM client.

Works with any endpoint that implements the OpenAI chat/completions API:
Ollama, vLLM, OpenRouter, OpenAI, etc.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

import httpx

from nemoclaw.llm.base import LLMProvider
from nemoclaw.models import Message, TokenUsage

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3
_BACKOFF_BASE = 1.0


class OpenAICompatClient(LLMProvider):
    """Async client for OpenAI-compatible chat/completions endpoints."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434/v1",
        model: str = "qwen3.5:35b",
        api_key: str = "ollama",
        timeout: float = 300.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout, connect=10.0),
        )
        self._last_usage = TokenUsage()

    def _build_payload(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Build the request payload."""
        msg_dicts = []
        for m in messages:
            d: dict[str, Any] = {"role": m.role}
            if m.content is not None:
                if isinstance(m.content, list):
                    # Extract only text parts for non-vision models
                    text_parts = [
                        p.get("text", "")
                        for p in m.content
                        if isinstance(p, dict) and p.get("type") == "text"
                    ]
                    d["content"] = " ".join(text_parts) or None
                else:
                    d["content"] = m.content

            if m.tool_calls:
                d["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in m.tool_calls
                ]
            if m.tool_call_id:
                d["tool_call_id"] = m.tool_call_id
            msg_dicts.append(d)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": msg_dicts,
            "stream": stream,
        }

        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if tools:
            payload["tools"] = tools

        return payload

    async def chat_completion(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict:
        """Send a non-streaming chat completion request with retries."""
        payload = self._build_payload(
            messages, tools, stream=False,
            temperature=temperature, max_tokens=max_tokens,
        )

        last_err: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                resp = await self._client.post("/chat/completions", json=payload)
                resp.raise_for_status()
                data = resp.json()

                # --- DEBUG LOGGING START ---
                import json, datetime
                try:
                    with open("/tmp/nemoclaw_llm_debug.jsonl", "a") as f:
                        choice = data.get("choices", [{}])[0]
                        msg = choice.get("message", {})
                        entry = {
                            "timestamp": datetime.datetime.now().isoformat(),
                            "content": msg.get("content"),
                            "tool_calls": msg.get("tool_calls"),
                            "finish_reason": choice.get("finish_reason")
                        }
                        f.write(json.dumps(entry) + "\n")
                except Exception as log_err:
                    logger.warning("Debug logging failed: %s", log_err)
                # --- DEBUG LOGGING END ---

                usage = data.get("usage", {})
                self._last_usage = TokenUsage(
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                )
                return data
            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout) as e:
                last_err = e
                if attempt < _MAX_RETRIES - 1:
                    wait = _BACKOFF_BASE * (2 ** attempt)
                    logger.warning(
                        "LLM request failed (attempt %d/%d): %s — retrying in %.1fs",
                        attempt + 1, _MAX_RETRIES, e, wait,
                    )
                    await asyncio.sleep(wait)
        raise ConnectionError(f"LLM request failed after {_MAX_RETRIES} attempts: {last_err}")

    async def chat_completion_stream(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[dict]:
        """Send a streaming chat completion request. Yields parsed SSE chunks."""
        payload = self._build_payload(
            messages, tools, stream=True,
            temperature=temperature, max_tokens=max_tokens,
        )

        last_err: Exception | None = None
        for attempt in range(_MAX_RETRIES):
            try:
                async with self._client.stream(
                    "POST", "/chat/completions", json=payload,
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        line = line.strip()
                        if not line:
                            continue
                        if line == "data: [DONE]":
                            return
                        if line.startswith("data: "):
                            try:
                                chunk = json.loads(line[6:])
                                
                                # --- DEBUG LOGGING START ---
                                import json, datetime
                                try:
                                    with open("/tmp/nemoclaw_llm_debug.jsonl", "a") as f:
                                        entry = {
                                            "timestamp": datetime.datetime.now().isoformat(),
                                            "stream_chunk": chunk
                                        }
                                        f.write(json.dumps(entry) + "\n")
                                except Exception:
                                    pass
                                # --- DEBUG LOGGING END ---

                                yield chunk
                            except json.JSONDecodeError:
                                continue
                return  # Stream completed normally
            except (httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout) as e:
                last_err = e
                if attempt < _MAX_RETRIES - 1:
                    wait = _BACKOFF_BASE * (2 ** attempt)
                    logger.warning(
                        "LLM stream failed (attempt %d/%d): %s — retrying in %.1fs",
                        attempt + 1, _MAX_RETRIES, e, wait,
                    )
                    await asyncio.sleep(wait)
        raise ConnectionError(f"LLM stream failed after {_MAX_RETRIES} attempts: {last_err}")

    async def close(self) -> None:
        """Close the underlying httpx client."""
        await self._client.aclose()

    def get_last_usage(self) -> TokenUsage:
        """Return token usage from the last non-streaming call."""
        return self._last_usage


class VisionClient(OpenAICompatClient):
    """Client for vision-capable endpoints. Allows image data in messages."""

    def _build_payload(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        stream: bool = False,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        """Build the request payload WITHOUT stripping images."""
        msg_dicts = []
        for m in messages:
            d: dict[str, Any] = {"role": m.role}
            if m.content is not None:
                # For vision, we keep the content as-is (could be list or str)
                d["content"] = m.content

            # Vision models in this setup usually don't do tool calls,
            # but we keep the structure for compatibility.
            if m.tool_calls:
                d["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments),
                        },
                    }
                    for tc in m.tool_calls
                ]
            if m.tool_call_id:
                d["tool_call_id"] = m.tool_call_id
            msg_dicts.append(d)

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": msg_dicts,
            "stream": stream,
        }

        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        # We usually don't send tools to the vision model
        if tools:
            payload["tools"] = tools

        return payload
