"""CLI transport using Rich for output and prompt_toolkit for input."""

from __future__ import annotations

import asyncio
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text

from nemoclaw.transport.base import Transport


class CLITransport(Transport):
    """Rich terminal transport with prompt_toolkit input."""

    def __init__(self) -> None:
        self.console = Console()
        self._history = InMemoryHistory()
        self._session: PromptSession[str] = PromptSession(history=self._history)
        self._turn_count = 0
        self._conversation_history: list[dict[str, str]] = []

    async def startup(self) -> None:
        """Display welcome banner."""
        self.console.print(
            Panel(
                "[bold cyan]NemoClaw Agent Harness[/bold cyan]\n"
                "[dim]Type /quit to exit, /clear to reset, /tools to list tools, /history to show history[/dim]",
                border_style="cyan",
            )
        )

    async def get_input(self) -> str:
        """Get user input via prompt_toolkit (supports history, editing)."""
        try:
            # Run prompt_toolkit in a thread since it's synchronous
            text = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._session.prompt("you> "),
            )
            text = text.strip()

            # Handle special commands
            if text in ("/quit", "/exit", "/q"):
                return ""
            if text == "/clear":
                self.console.clear()
                self._turn_count = 0
                self._conversation_history.clear()
                self.console.print("[dim]Conversation cleared.[/dim]")
                return "/clear"
            if text == "/history":
                self._show_history()
                return "/history"
            if text == "/tools":
                return "/tools"

            return text

        except (EOFError, KeyboardInterrupt):
            return ""

    async def send_chunk(self, chunk: str) -> None:
        """Stream a text chunk to the console."""
        self.console.print(chunk, end="", highlight=False)

    async def send_tool_status(
        self, tool_name: str, status: str, result: str | None = None,
    ) -> None:
        """Show tool execution status with indicators."""
        icons = {"running": "[yellow]⟳[/yellow]", "done": "[green]✓[/green]", "error": "[red]✗[/red]"}
        icon = icons.get(status, "·")

        if status == "running":
            self.console.print(f"  {icon} [bold]{tool_name}[/bold]", highlight=False)
        elif result:
            preview = result[:120].replace("\n", " ")
            self.console.print(f"  {icon} [bold]{tool_name}[/bold] → [dim]{preview}[/dim]", highlight=False)
        else:
            self.console.print(f"  {icon} [bold]{tool_name}[/bold]", highlight=False)

    async def send_response(self, response: str) -> None:
        """Send the final response, rendered as markdown."""
        self._turn_count += 1
        self.console.print()
        self.console.print(Markdown(response))
        self.console.print()
        self._conversation_history.append({"role": "assistant", "content": response})

    async def show_error(self, error: str) -> None:
        """Display an error."""
        self.console.print(f"[red bold]Error:[/red bold] {error}")

    async def shutdown(self) -> None:
        """Display goodbye."""
        self.console.print("\n[dim]Goodbye.[/dim]")

    def _show_history(self) -> None:
        """Display conversation history."""
        if not self._conversation_history:
            self.console.print("[dim]No conversation history yet.[/dim]")
            return
        for entry in self._conversation_history:
            role = entry["role"]
            content = entry["content"][:200]
            if role == "user":
                self.console.print(f"[cyan]you>[/cyan] {content}")
            else:
                self.console.print(f"[green]assistant>[/green] {content}")

    def show_tools(self, tool_names: list[str]) -> None:
        """Display available tools."""
        self.console.print("\n[bold]Available tools:[/bold]")
        for name in tool_names:
            self.console.print(f"  • {name}")
        self.console.print()
