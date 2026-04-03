"""Tool registry — discovers, validates, and manages tools."""

from __future__ import annotations

from nemoclaw.tools.base import BaseTool


class ToolRegistry:
    """Holds all registered tools and provides them as OpenAI tool schemas."""

    def __init__(self) -> None:
        self.tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """Register a tool instance."""
        self.tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        return self.tools.get(name)

    def get_openai_schemas(self) -> list[dict]:
        """Return all tools as OpenAI function calling schemas."""
        return [t.to_openai_schema() for t in self.tools.values()]

    def register_defaults(self) -> None:
        """Register all built-in tools."""
        from nemoclaw.tools.bash import BashTool
        from nemoclaw.tools.edit_file import EditFileTool
        from nemoclaw.tools.glob_tool import GlobTool
        from nemoclaw.tools.read_file import ReadFileTool
        from nemoclaw.tools.web_fetch import WebFetchTool
        from nemoclaw.tools.write_file import WriteFileTool

        for tool_cls in (BashTool, ReadFileTool, WriteFileTool, EditFileTool, WebFetchTool, GlobTool):
            self.register(tool_cls())
