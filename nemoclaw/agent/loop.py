"""Core ReAct agent loop — the heart of NemoClaw.

The loop:
1. Build messages (system + history + user input)
2. Run input guards (CG-01..CG-05)
3. Check permissions on tool calls
4. Call LLM with tool definitions
5. If tool_calls in response: execute tools, append results, loop
6. Run output guards (PII redaction)
7. Log all messages via session manager
8. If text only: return response, break
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
    session_manager: Any | None = None,
    clause_guards: Any | None = None,
    permission_pipeline: Any | None = None,
    compaction_manager: Any | None = None,
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
        session_manager: Optional SessionManager for JSONL logging.
        clause_guards: Optional ClauseGuards for input/output filtering.
        permission_pipeline: Optional PermissionPipeline for tool access control.
        compaction_manager: Optional CompactionManager for context size management.

    Returns:
        AgentResponse with the final text content and metadata.
    """
    # ── Input Guards ────────────────────────────────────────────────
    if clause_guards:
        guard_result = clause_guards.check_input(user_input)
        if not guard_result.passed:
            logger.info("Guard %s blocked input", guard_result.guard_id)
            blocked_content = guard_result.message
            history.append(Message(role="user", content=user_input))
            history.append(Message(role="assistant", content=blocked_content))
            if session_manager:
                session_manager.log_message("user", user_input)
                session_manager.log_message(
                    "assistant", blocked_content,
                    metadata={"guard": guard_result.guard_id},
                )
            return AgentResponse(
                content=blocked_content,
                tool_calls_made=[],
                token_usage=TokenUsage(),
                turns_used=0,
            )

    # Add user message to history
    history.append(Message(role="user", content=user_input))
    if session_manager:
        session_manager.log_message("user", user_input)

    # ── Context Compaction ──────────────────────────────────────────
    if compaction_manager and compaction_manager.needs_compaction(system_prompt, history):
        history[:] = compaction_manager.compact(system_prompt, history)

    all_tool_calls: list[ToolCall] = []
    total_usage = TokenUsage()
    tool_schemas = tools.get_openai_schemas()
    turns = 0

    while turns < max_turns:
        turns += 1

        # Build message list: system + history
        messages = [Message(role="system", content=system_prompt)] + history

        if stream and turns == 1:
            # First turn — try streaming for the initial response
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

            # ── Permission Check ────────────────────────────────
            if permission_pipeline:
                permitted_calls = []
                for tc in tool_calls:
                    allowed = await permission_pipeline.check_permission(tc)
                    if allowed:
                        permitted_calls.append(tc)
                    else:
                        logger.warning("Permission denied for tool: %s", tc.name)
                        history.append(Message(
                            role="tool",
                            content=f"Permission denied for tool: {tc.name}",
                            tool_call_id=tc.id,
                        ))
                tool_calls = permitted_calls

            # Append assistant message with tool calls to history
            assistant_msg = Message(
                role="assistant",
                content=content,
                tool_calls=tool_calls if tool_calls else None,
            ))
            if session_manager:
                session_manager.log_message(
                    "assistant", content,
                    tool_calls=tool_calls if tool_calls else None,
                )

            if not tool_calls:
                # All tools were denied — continue loop to let LLM retry
                continue

            # Execute tools
            results = await _execute_tools(tool_calls, tools, on_tool_call)

            # Append tool results to history
            for result in results:
                tool_msg = Message(
                    role="tool",
                    content=result.content,
                    tool_call_id=result.tool_call_id,
                ))
                if session_manager:
                    session_manager.log_message(
                        "tool", result.content,
                        tool_call_id=result.tool_call_id,
                    )

            continue

        # No tool calls — this is the final text response
        final_content = content or ""

        # ── Output Guards (PII redaction) ───────────────────────
        if clause_guards:
            output_result = clause_guards.check_output(final_content)
            if output_result.modified_output is not None:
                final_content = output_result.modified_output

        # Stream the final response if requested
        if stream and on_chunk and final_content:
            for i in range(0, len(final_content), 20):
                await on_chunk(final_content[i:i + 20])

        # Append assistant response to history
        history.append(Message(role="assistant", content=final_content))
        if session_manager:
            session_manager.log_message("assistant", final_content)

        return AgentResponse(
            content=final_content,
            tool_calls_made=all_tool_calls,
            token_usage=total_usage,
            turns_used=turns,
        )

    # Max turns reached — return whatever we have
    max_turns_msg = "[Reached maximum tool-use turns. Stopping.]"
    history.append(Message(role="assistant", content=max_turns_msg))
    if session_manager:
        session_manager.log_message("assistant", max_turns_msg)

    return AgentResponse(
        content=max_turns_msg,
        tool_calls_made=all_tool_calls,
        token_usage=total_usage,
        turns_used=turns,
    )
