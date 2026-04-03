"""Permission pipeline interface stub (Phase 5).

This will implement the 4-layer permission pipeline:
1. General rules (allow/deny/ask lists)
2. Tool-specific checks
3. Automated classifier
4. Interactive user approval
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from nemoclaw.models import ToolCall


class PermissionProvider(ABC):
    """Abstract permission provider interface."""

    @abstractmethod
    async def check_permission(self, tool_call: ToolCall) -> bool:
        """Check if a tool call is permitted. Returns True if allowed."""
