"""NemoClaw entry point — python -m nemoclaw."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from nemoclaw.agent.compaction import CompactionManager
from nemoclaw.agent.hooks import post_response_hook, pre_response_hook
from nemoclaw.agent.loop import run_agent_loop
from nemoclaw.agent.prompt import build_system_prompt
from nemoclaw.agent.router import ROUTE_TOOLS, classify_intent
from nemoclaw.config import Settings
from nemoclaw.guards.clause_guards import ClauseGuards
from nemoclaw.llm.registry import create_llm_provider
from nemoclaw.memory.store import MemoryStore
from nemoclaw.memory.tools import MemorySearchTool, MemoryWriteTool
from nemoclaw.models import Message
from nemoclaw.permissions.pipeline import PermissionPipeline
from nemoclaw.session.manager import SessionManager
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
        "--continue", dest="continue_session", action="store_true",
        help="Resume the most recent session",
    )
    parser.add_argument(
        "--resume", metavar="SESSION_ID", default=None,
        help="Resume a specific session by ID",
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

    # ── Memory Store ────────────────────────────────────────────────
    memory_store = MemoryStore(
        memory_dir=settings.memory_dir,
        sessions_dir=settings.session_dir,
    )

    # ── Tool Registry ───────────────────────────────────────────────
    tool_registry = ToolRegistry()
    if not args.no_tools:
        tool_registry.register_defaults()
        tool_registry.register(MemoryWriteTool(memory_store))
        tool_registry.register(MemorySearchTool(memory_store))

    # ── Clause Guards ───────────────────────────────────────────────
    clause_guards = ClauseGuards(
        patterns_path=settings.guards_patterns_path,
        enabled=settings.guards_enabled,
    )

    # ── Permission Pipeline ─────────────────────────────────────────
    permission_pipeline = PermissionPipeline(
        always_allow=settings.permissions_always_allow,
        always_deny=settings.permissions_always_deny,
        always_ask=settings.permissions_always_ask,
        auto_allow_after_n=settings.permissions_auto_allow_after_n,
    )

    # ── Telegram Transport ─────────────────────────────────────────
    if settings.transport == "telegram":
        from nemoclaw.transport.telegram import TelegramTransport

        transport = TelegramTransport(
            settings=settings,
            llm=llm,
            tool_registry=tool_registry,
            memory_store=memory_store,
            clause_guards=clause_guards,
            permission_pipeline=permission_pipeline,
        )
        await transport.run()
        return

    # ── CLI Transport ──────────────────────────────────────────────
    session_mgr = SessionManager(
        sessions_dir=settings.session_dir,
        model=settings.llm_model,
        persona=str(settings.persona_path),
    )

    history: list[Message] = []

    if args.resume:
        history = session_mgr.resume_session(args.resume)
    elif args.continue_session:
        try:
            history = session_mgr.continue_last_session()
        except FileNotFoundError:
            session_mgr.start_new_session()
    else:
        session_mgr.start_new_session()

    compaction_mgr = CompactionManager(
        max_context_tokens=settings.max_context_tokens,
        memory_store=memory_store,
    )

    memory_block = memory_store.get_memory_block()
    tool_descriptions = [
        f"{t.name}: {t.description}" for t in tool_registry.tools.values()
    ]
    system_prompt = build_system_prompt(
        persona_path=settings.persona_path,
        tool_descriptions=tool_descriptions if tool_descriptions else None,
        memory_block=memory_block,
    )

    cli_transport = CLITransport()
    await cli_transport.startup()

    try:
        while True:
            user_input = await cli_transport.get_input()

            if not user_input:
                break
            if user_input == "/clear":
                history.clear()
                continue
            if user_input == "/history":
                cli_transport._show_history()
                continue
            if user_input == "/tools":
                cli_transport.show_tools(list(tool_registry.tools.keys()))
                continue

            cli_transport.add_user_message(user_input)

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
                    on_chunk=cli_transport.send_chunk,
                    on_tool_call=cli_transport.send_tool_status,
                    session_manager=session_mgr,
                    clause_guards=clause_guards,
                    permission_pipeline=permission_pipeline,
                    compaction_manager=compaction_mgr,
                )

                await cli_transport.send_response(response.content)
                await post_response_hook(user_input, response)

            except ConnectionError as e:
                await cli_transport.show_error(str(e))
            except Exception as e:
                logging.exception("Agent loop error")
                await cli_transport.show_error(f"Unexpected error: {e}")

    finally:
        await cli_transport.shutdown()
        await llm.close()


def main() -> None:
    """Sync entry point for console_scripts."""
    args = parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
