"""Telegram bot transport using python-telegram-bot v21+."""

from __future__ import annotations

import asyncio
import logging
import re
import signal
from pathlib import Path
from typing import Any

from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from nemoclaw.agent.loop import run_agent_loop
from nemoclaw.agent.prompt import build_system_prompt
from nemoclaw.config import Settings
from nemoclaw.guards.clause_guards import ClauseGuards
from nemoclaw.llm.base import LLMProvider
from nemoclaw.memory.store import MemoryStore
from nemoclaw.memory.tools import MemorySearchTool, MemoryWriteTool
from nemoclaw.models import Message
from nemoclaw.permissions.pipeline import PermissionPipeline
from nemoclaw.session.manager import SessionManager
from nemoclaw.tools.registry import ToolRegistry
from nemoclaw.transport.base import Transport

logger = logging.getLogger(__name__)


def _escape_mdv2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    special = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(special)}])", r"\\\1", text)


def _split_message(text: str, max_length: int = 4096) -> list[str]:
    """Split a long message into chunks that fit Telegram's limit."""
    if len(text) <= max_length:
        return [text]
    chunks: list[str] = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        # Try to split at a newline near the limit
        split_at = text.rfind("\n", 0, max_length)
        if split_at == -1 or split_at < max_length // 2:
            split_at = max_length
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


class TelegramTransport(Transport):
    """Telegram bot transport using python-telegram-bot v21+.

    Each Telegram user gets their own conversation history and session.
    Uses message editing to simulate streaming.
    """

    def __init__(
        self,
        settings: Settings,
        llm: LLMProvider,
        tool_registry: ToolRegistry,
        memory_store: MemoryStore,
        clause_guards: ClauseGuards,
        permission_pipeline: PermissionPipeline,
    ) -> None:
        self.settings = settings
        self.llm = llm
        self.tool_registry = tool_registry
        self.memory_store = memory_store
        self.clause_guards = clause_guards
        self.permission_pipeline = permission_pipeline

        self._max_len = settings.telegram_max_message_length
        self._edit_interval = settings.telegram_edit_interval
        self._allowed_users = settings.telegram_allowed_users

        # Per-user state
        self._histories: dict[int, list[Message]] = {}
        self._sessions: dict[int, SessionManager] = {}

        # Build system prompt once
        memory_block = memory_store.get_memory_block()
        tool_descriptions = [
            f"{t.name}: {t.description}" for t in tool_registry.tools.values()
        ]
        self._system_prompt = build_system_prompt(
            persona_path=settings.persona_path,
            tool_descriptions=tool_descriptions if tool_descriptions else None,
            memory_block=memory_block,
        )

    def _is_user_allowed(self, user_id: int, username: str | None) -> bool:
        """Check if a user is in the allowed list."""
        if "*" in self._allowed_users:
            return True
        allowed = {a.lower() for a in self._allowed_users}
        if str(user_id) in allowed:
            return True
        if username and username.lower() in allowed:
            return True
        return False

    def _get_session(self, chat_id: int) -> SessionManager:
        """Get or create a SessionManager for a chat."""
        if chat_id not in self._sessions:
            session_dir = self.settings.session_dir / f"tg_{chat_id}"
            session_mgr = SessionManager(
                sessions_dir=session_dir,
                model=self.settings.llm_model,
                persona=str(self.settings.persona_path),
            )
            session_mgr.start_new_session()
            self._sessions[chat_id] = session_mgr
        return self._sessions[chat_id]

    def _get_history(self, chat_id: int) -> list[Message]:
        """Get or create conversation history for a chat."""
        if chat_id not in self._histories:
            self._histories[chat_id] = []
        return self._histories[chat_id]

    # ── Command Handlers ───────────────────────────────────────────

    async def _cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command."""
        if not update.effective_chat or not update.effective_user:
            return
        chat_id = update.effective_chat.id
        username = update.effective_user.username
        if not self._is_user_allowed(update.effective_user.id, username):
            await update.message.reply_text("You are not authorized to use this bot.")  # type: ignore[union-attr]
            return

        self._histories[chat_id] = []
        self._get_session(chat_id)
        await update.message.reply_text(  # type: ignore[union-attr]
            "Welcome to NemoClaw! Send me a message to start chatting.\n"
            "Commands: /clear /tools /history /status"
        )

    async def _cmd_clear(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /clear command."""
        if not update.effective_chat:
            return
        chat_id = update.effective_chat.id
        self._histories[chat_id] = []
        # Start a fresh session
        if chat_id in self._sessions:
            self._sessions[chat_id].start_new_session()
        await update.message.reply_text("Conversation cleared.")  # type: ignore[union-attr]

    async def _cmd_tools(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /tools command."""
        tool_names = list(self.tool_registry.tools.keys())
        if tool_names:
            lines = ["Available tools:"] + [f"  - {name}" for name in tool_names]
            await update.message.reply_text("\n".join(lines))  # type: ignore[union-attr]
        else:
            await update.message.reply_text("No tools available.")  # type: ignore[union-attr]

    async def _cmd_history(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /history command."""
        if not update.effective_chat:
            return
        chat_id = update.effective_chat.id
        history = self._get_history(chat_id)
        if not history:
            await update.message.reply_text("No conversation history yet.")  # type: ignore[union-attr]
            return
        lines: list[str] = []
        for msg in history[-20:]:
            role = msg.role
            content = (msg.content or "")[:150]
            lines.append(f"{role}: {content}")
        await update.message.reply_text("\n".join(lines))  # type: ignore[union-attr]

    async def _cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command."""
        if not update.effective_chat:
            return
        chat_id = update.effective_chat.id
        history = self._get_history(chat_id)
        session = self._sessions.get(chat_id)
        status_lines = [
            f"Chat ID: {chat_id}",
            f"Messages in history: {len(history)}",
            f"Session ID: {session.session_id if session else 'none'}",
            f"Model: {self.settings.llm_model}",
            f"Tools: {len(self.tool_registry.tools)}",
        ]
        await update.message.reply_text("\n".join(status_lines))  # type: ignore[union-attr]

    # ── Message Handler ────────────────────────────────────────────

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle incoming text messages — run the agent loop."""
        if not update.effective_chat or not update.effective_user or not update.message:
            return

        chat_id = update.effective_chat.id
        user_id = update.effective_user.id
        username = update.effective_user.username
        user_text = update.message.text or ""

        if not self._is_user_allowed(user_id, username):
            await update.message.reply_text("You are not authorized to use this bot.")
            return

        if not user_text.strip():
            return

        history = self._get_history(chat_id)
        session_mgr = self._get_session(chat_id)

        # Send "thinking..." placeholder
        placeholder = await update.message.reply_text("Thinking...")

        accumulated_text = ""
        last_edit_time = asyncio.get_event_loop().time()

        async def on_chunk(chunk: str) -> None:
            nonlocal accumulated_text, last_edit_time
            accumulated_text += chunk
            now = asyncio.get_event_loop().time()
            if now - last_edit_time >= self._edit_interval:
                display = accumulated_text[:self._max_len]
                try:
                    await placeholder.edit_text(display or "...")
                except Exception:
                    pass  # Ignore edit errors (message not modified, etc.)
                last_edit_time = now

        async def on_tool_call(tool_name: str, status: str, result: str | None = None) -> None:
            nonlocal accumulated_text, last_edit_time
            if status == "running":
                line = f"Running {tool_name}..."
            elif result:
                preview = result[:80].replace("\n", " ")
                line = f"{tool_name} done: {preview}"
            else:
                line = f"{tool_name} {status}"
            accumulated_text += f"\n_{line}_\n"
            try:
                display = accumulated_text[:self._max_len]
                await placeholder.edit_text(display or "...")
            except Exception:
                pass
            last_edit_time = asyncio.get_event_loop().time()

        try:
            response = await run_agent_loop(
                user_input=user_text,
                llm=self.llm,
                tools=self.tool_registry,
                system_prompt=self._system_prompt,
                history=history,
                max_turns=self.settings.max_turns,
                stream=True,
                on_chunk=on_chunk,
                on_tool_call=on_tool_call,
                session_manager=session_mgr,
                clause_guards=self.clause_guards,
                permission_pipeline=self.permission_pipeline,
            )

            final_text = response.content or "(No response)"
            # Split long responses
            chunks = _split_message(final_text, self._max_len)

            # Edit placeholder with the first chunk
            try:
                await placeholder.edit_text(chunks[0])
            except Exception:
                pass

            # Send remaining chunks as separate messages
            for chunk in chunks[1:]:
                await update.effective_chat.send_message(chunk)

        except Exception as e:
            logger.exception("Error in agent loop for chat %d", chat_id)
            try:
                await placeholder.edit_text(f"Error: {e}")
            except Exception:
                await update.effective_chat.send_message(f"Error: {e}")

    # ── Transport ABC (used for standalone mode) ───────────────────

    async def get_input(self) -> str:
        # Not used in Telegram mode — polling drives input
        return ""

    async def send_chunk(self, chunk: str) -> None:
        pass  # Handled via on_chunk callback in _handle_message

    async def send_tool_status(
        self, tool_name: str, status: str, result: str | None = None,
    ) -> None:
        pass  # Handled via on_tool_call callback in _handle_message

    async def send_response(self, response: str) -> None:
        pass  # Handled in _handle_message

    async def show_error(self, error: str) -> None:
        pass  # Handled in _handle_message

    # ── Run ────────────────────────────────────────────────────────

    async def run(self) -> None:
        """Start the Telegram bot with polling."""
        token = self.settings.telegram_token
        if not token:
            raise ValueError(
                "Telegram token not set. Set NEMOCLAW_TELEGRAM_TOKEN env var."
            )

        app = Application.builder().token(token).build()

        # Register handlers
        app.add_handler(CommandHandler("start", self._cmd_start))
        app.add_handler(CommandHandler("clear", self._cmd_clear))
        app.add_handler(CommandHandler("tools", self._cmd_tools))
        app.add_handler(CommandHandler("history", self._cmd_history))
        app.add_handler(CommandHandler("status", self._cmd_status))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message))

        logger.info("Starting Telegram bot polling...")
        await app.initialize()
        await app.start()
        await app.updater.start_polling()  # type: ignore[union-attr]

        # Wait for shutdown signal
        stop_event = asyncio.Event()

        def _signal_handler() -> None:
            stop_event.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                loop.add_signal_handler(sig, _signal_handler)
            except NotImplementedError:
                pass  # Windows doesn't support add_signal_handler

        await stop_event.wait()

        logger.info("Shutting down Telegram bot...")
        await app.updater.stop()  # type: ignore[union-attr]
        await app.stop()
        await app.shutdown()
        await self.llm.close()
