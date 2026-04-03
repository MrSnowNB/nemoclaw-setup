"""NemoClaw entry point — python -m nemoclaw."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

from nemoclaw.agent.hooks import post_response_hook, pre_response_hook
from nemoclaw.agent.loop import run_agent_loop
from nemoclaw.agent.prompt import build_system_prompt
from nemoclaw.config import Settings
from nemoclaw.llm.registry import create_llm_provider
from nemoclaw.models import Message
from nemoclaw.tools.registry import ToolRegistry
from nemoclaw.transport.cli import CLITransport


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="nemoclaw",
        description="NemoClaw agent harness — a tool-using AI assistant",
    )
    parser.add_argument(
        "--transport", choices=["cli", "telegram"], default=None,
        help="I/O transport (default: cli)",
    )
    parser.add_argument(
        "--model", default=None,
        help="LLM model name (default: from config)",
    )
    parser.add_argument(
        "--base-url", default=None,
        help="LLM API base URL (default: from config)",
    )
    parser.add_argument(
        "--config", default=None,
        help="Path to YAML config file",
    )
    parser.add_argument(
        "--persona", default=None,
        help="Path to persona file (e.g. alice/ALICE.md)",
    )
    parser.add_argument(
        "--max-turns", type=int, default=None,
        help="Maximum agent loop turns (default: 25)",
    )
    parser.add_argument(
        "--no-tools", action="store_true",
        help="Disable tools (pure chat mode)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


async def run(args: argparse.Namespace) -> None:
    """Main async entry point."""
    # Build settings with CLI overrides
    overrides: dict = {}
    if args.transport:
        overrides["transport"] = args.transport
    if args.model:
        overrides["llm_model"] = args.model
    if args.base_url:
        overrides["llm_base_url"] = args.base_url
    if args.persona:
        overrides["persona_path"] = args.persona
    if args.max_turns:
        overrides["max_turns"] = args.max_turns

    settings = Settings.from_yaml(yaml_path=args.config, **overrides)

    # Configure logging
    level = logging.DEBUG if args.verbose else logging.WARNING
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

    # Initialize components
    llm = create_llm_provider(settings)
    tool_registry = ToolRegistry()
    if not args.no_tools:
        tool_registry.register_defaults()

    # Build system prompt
    tool_descriptions = [
        f"{t.name}: {t.description}" for t in tool_registry.tools.values()
    ]
    system_prompt = build_system_prompt(
        persona_path=settings.persona_path,
        tool_descriptions=tool_descriptions if tool_descriptions else None,
    )

    # Initialize transport
    transport = CLITransport()

    # Conversation state
    history: list[Message] = []

    await transport.startup()

    try:
        while True:
            user_input = await transport.get_input()

            if not user_input:
                break
            if user_input == "/clear":
                history.clear()
                continue
            if user_input == "/history":
                continue
            if user_input == "/tools":
                transport.show_tools(list(tool_registry.tools.keys()))
                continue

            # Record user message for transport history
            transport._conversation_history.append(
                {"role": "user", "content": user_input},
            )

            # Pre-response hook
            await pre_response_hook(user_input)

            try:
                response = await run_agent_loop(
                    user_input=user_input,
                    llm=llm,
                    tools=tool_registry,
                    system_prompt=system_prompt,
                    history=history,
                    max_turns=settings.max_turns,
                    stream=True,
                    on_chunk=transport.send_chunk,
                    on_tool_call=transport.send_tool_status,
                )

                await transport.send_response(response.content)

                # Post-response hook
                await post_response_hook(user_input, response)

            except ConnectionError as e:
                await transport.show_error(str(e))
            except Exception as e:
                logging.exception("Agent loop error")
                await transport.show_error(f"Unexpected error: {e}")

    finally:
        await transport.shutdown()
        await llm.close()


def main() -> None:
    """Sync entry point for console_scripts."""
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
