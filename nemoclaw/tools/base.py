"""Base tool interface for the agent harness."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from nemoclaw.models import ToolResult


class BaseTool(ABC):
    """Abstract base class for all tools.

    Every tool must define its identity (name, description, parameters)
    and implement the execute method.
    """

    name: str
    description: str
    parameters: dict[str, Any]
    is_read_only: bool = True
    is_concurrency_safe: bool = True
    requires_confirmation: bool = False

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with the given arguments."""

    def validate_input(self, **kwargs: Any) -> bool:
        """Validate input against the parameter schema. Returns True if valid."""
        required = self.parameters.get("required", [])
        for param in required:
            if param not in kwargs:
                return False
        return True

    def to_openai_schema(self) -> dict:
        """Convert this tool to OpenAI function calling format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
