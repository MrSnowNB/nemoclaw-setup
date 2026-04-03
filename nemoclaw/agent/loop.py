"""Core ReAct agent loop — the heart of NemoClaw.

The loop:
1. Build messages (system + history + user input)
2. Run clause guards on input
3. Call LLM with tool definitions
4. Run permission check on tool calls
5. If tool_calls in response: execute tools, append results, loop
6. Run PII guard on output
7. If text only: return response, break
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Coroutine

from nemoclaw.agent.compaction import CompactionManager
from nemoclaw.guards.clause_guards import ClauseGuardRunner
from nemoclaw.llm.base import LLMProvider
from nemoclaw.models import AgentResponse, Message, ToolCall, ToolResult, TokenUsage
from nemoclaw.permissions.pipeline import PermissionPipeline
from nemoclaw.session.manager import SessionManager
from nemoclaw.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


def _parse_tool_calls(raw_tool_calls: list[dict]) -> list[ToolCall]:
    """Parse tool_calls from the LLM response into ToolCall models."""
    calls = []
    for tc in raw_tool_calls:
        func = tc.get("function", {})
        args_raw = func.get("arguments", "{}")
        if isinstance(args_raw, str):
            try:
                args = json.loads(args_raw)
            except json.JSONDecodeError:
                args = {"raw": args_raw}
        else:
            args = args_raw
        calls.append(ToolCall(
            id=tc.get("id", ""),
            name=func.get("name", ""),
            arguments=args,
        ))
    return calls


async def _execute_tool(
    tool_call: ToolCall,
    registry: ToolRegistry,
    on_tool_call: Callable[..., Coroutine] | None = None,
) -> ToolResult:
    """Execute a single tool call and return the result."""
    tool = registry.get(tool_call.name)
    if tool is None:
        return ToolResult(
            tool_call_id=tool_call.id,
            content=f"Unknown tool: {tool_call.name}",
            is_error=True,
        )

    if on_tool_call:
        await on_tool_call(tool_call.name, "running")

    result = await tool.execute(tool_call_id=tool_call.id, **tool_call.arguments)

    if on_tool_call:
        status = "error" if result.is_error else "done"
        await on_tool_call(tool_call.name, status, result.content[:200])

    return result


async def _execute_tools(
    tool_calls: list[ToolCall],
    registry: ToolRegistry,
    on_tool_call: Callable[..., Coroutine] | None = None,
) -> list[ToolResult]:
    """Execute tool calls — read-only tools concurrently, mutating tools serially."""
    read_only: list[ToolCall] = []
    mutating: list[ToolCall] = []

    for tc in tool_calls:
        tool = registry.get(tc.name)
        if tool and tool.is_read_only and tool.is_concurrency_safe:
            read_only.append(tc)
        else:
            mutating.append(tc)

    results: list[ToolResult] = []

    # Run read-only tools concurrently
    if read_only:
        coros = [_execute_tool(tc, registry, on_tool_call) for tc in read_only]
        results.extend(await asyncio.gather(*coros))

    # Run mutating tools serially
    for tc in mutating:
        results.append(await _execute_tool(tc, registry, on_tool_call))

    return results


async def run_agent_loop(
    user_input: str,
    llm: LLMProvider,
    tools: ToolRegistry,
    system_prompt: str,
    history: list[Message],
    max_turns: int = 25,
    stream: bool = True,
    on_chunk: Callable[[str], Coroutine] | None = None,
    on_tool_call: Callable[..., Coroutine] | None = None,
    session_manager: SessionManager | None = None,
    guards: ClauseGuardRunner | None = None,
    permissions: PermissionPipeline | None = None,
    compaction: CompactionManager | None = None,
    user_id: str = "default",
) -> AgentResponse:
    """Run the core ReAct agent loop.

    Args:
        user_input: The user's message.
        llm: LLM provider instance.
        tools: Tool registry with available tools.
        system_prompt: System prompt (persona + context).
        history: Conversation history (mutated in place).
        max_turns: Maximum tool-use turns before forcing a text response.
        stream: Whether to stream the final text response.
        on_chunk: Callback for streaming text chunks.
        on_tool_call: Callback for tool execution status.
        session_manager: Optional session manager for JSONL logging.
        guards: Optional clause guard runner for safety checks.
        permissions: Optional permission pipeline for tool authorization.
        compaction: Optional compaction manager for context management.
        user_id: User identifier for rate limiting.

    Returns:
        AgentResponse with the final text content and metadata.
    """
    # ── Input guards ───────────────────────────────────────────────
    if guards:
        guard_result = guards.check_input(user_input, user_id=user_id)
        if guard_result.blocked:
            logger.info("Guard %s blocked input", guard_result.guard_id)
            blocked_response = Message(role="assistant", content=guard_result.response)
            history.append(Message(role="user", content=user_input))
            history.append(blocked_response)
            if session_manager:
                session_manager.log_message(history[-2])
                session_manager.log_message(history[-1])
            return AgentResponse(
                content=guard_result.response,
                tool_calls_made=[],
                token_usage=TokenUsage(),
                turns_used=0,
            )

    # Add user message to history
    user_msg = Message(role="user", content=user_input)
    history.append(user_msg)
    if session_manager:
        session_manager.log_message(user_msg)

    # ── Context compaction ─────────────────────────────────────────
    if compaction and compaction.needs_compaction(history, system_prompt):
        logger.info("Context compaction triggered")
        history[:] = compaction.compact(history)

    all_tool_calls: list[ToolCall] = []
    total_usage = TokenUsage()
    tool_schemas = tools.get_openai_schemas()
    turns = 0

    while turns < max_turns:
        turns += 1

        # Build message list: system + history
        messages = [Message(role="system", content=system_prompt)] + history

        if stream and turns == 1:
            pass

        # Non-streaming call to get tool calls or final response
        response = await llm.chat_completion(
            messages=messages,
            tools=tool_schemas if tool_schemas else None,
            stream=False,
        )

        usage = llm.get_last_usage()
        total_usage.prompt_tokens += usage.prompt_tokens
        total_usage.completion_tokens += usage.completion_tokens
        total_usage.total_tokens += usage.total_tokens

        choice = response.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content")
        raw_tool_calls = message.get("tool_calls")

        if raw_tool_calls:
            # LLM wants to call tools
            tool_calls = _parse_tool_calls(raw_tool_calls)
            all_tool_calls.extend(tool_calls)

            # ── Permission check ───────────────────────────────────
            if permissions:
                allowed_calls = []
                for tc in tool_calls:
                    if await permissions.check_permission(tc):
                        allowed_calls.append(tc)
                    else:
                        logger.warning("Permission denied for tool: %s", tc.name)
                tool_calls = allowed_calls

                if not tool_calls:
                    # All tools were denied — return a message
                    denied_msg = Message(
                        role="assistant",
                        content="Tool calls were not permitted.",
                    )
                    history.append(denied_msg)
                    if session_manager:
                        session_manager.log_message(denied_msg)
                    return AgentResponse(
                        content="Tool calls were not permitted.",
                        tool_calls_made=all_tool_calls,
                        token_usage=total_usage,
                        turns_used=turns,
                    )

            # Append assistant message with tool calls to history
            assistant_msg = Message(
                role="assistant",
                content=content,
                tool_calls=tool_calls,
            )
            history.append(assistant_msg)
            if session_manager:
                session_manager.log_message(assistant_msg)

            # Execute tools
            results = await _execute_tools(tool_calls, tools, on_tool_call)

            # Append tool results to history
            for result in results:
                tool_msg = Message(
                    role="tool",
                    content=result.content,
                    tool_call_id=result.tool_call_id,
                )
                history.append(tool_msg)
                if session_manager:
                    session_manager.log_message(tool_msg)

            # Continue the loop — LLM will see tool results and decide next action
            continue

        # No tool calls — this is the final text response
        final_content = content or ""

        # ── Output guards (PII redaction) ──────────────────────────
        if guards:
            output_result = guards.check_output(final_content)
            if output_result.modified_content is not None:
                final_content = output_result.modified_content

        # Stream the final response if requested
        if stream and on_chunk and final_content:
            for i in range(0, len(final_content), 20):
                await on_chunk(final_content[i:i + 20])

        # Append assistant response to history
        assistant_msg = Message(role="assistant", content=final_content)
        history.append(assistant_msg)
        if session_manager:
            session_manager.log_message(assistant_msg)

        return AgentResponse(
            content=final_content,
            tool_calls_made=all_tool_calls,
            token_usage=total_usage,
            turns_used=turns,
        )

    # Max turns reached — return whatever we have
    max_msg = Message(
        role="assistant",
        content="[Reached maximum tool-use turns. Stopping.]",
    )
    history.append(max_msg)
    if session_manager:
        session_manager.log_message(max_msg)

    return AgentResponse(
        content="[Reached maximum tool-use turns. Stopping.]",
        tool_calls_made=all_tool_calls,
        token_usage=total_usage,
        turns_used=turns,
    )
