"""Pydantic data models for the agent harness."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ToolCall(BaseModel):
    """A tool call requested by the LLM."""

    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class Message(BaseModel):
    """A single message in a conversation."""

    role: str  # system, user, assistant, tool
    content: str | list[dict[str, Any]] | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None


class ToolResult(BaseModel):
    """Result from executing a tool."""

    tool_call_id: str
    content: str
    is_error: bool = False


class TokenUsage(BaseModel):
    """Token usage from an LLM call."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class AgentResponse(BaseModel):
    """Final response from the agent loop."""

    content: str
    tool_calls_made: list[ToolCall] = Field(default_factory=list)
    token_usage: TokenUsage = Field(default_factory=TokenUsage)
    turns_used: int = 0
