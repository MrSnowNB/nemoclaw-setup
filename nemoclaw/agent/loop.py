"""Core ReAct agent loop — the heart of NemoClaw.

The loop:
1. Build messages (system + history + user input)
2. Call LLM with tool definitions
3. If tool_calls in response: execute tools, append results, loop
4. If text only: return response, break
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, Callable, Coroutine

from nemoclaw.llm.base import LLMProvider
from nemoclaw.models import AgentResponse, Message, ToolCall, ToolResult, TokenUsage
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

    Returns:
        AgentResponse with the final text content and metadata.
    """
    # Add user message to history
    history.append(Message(role="user", content=user_input))

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
            # For tool-calling turns we use non-streaming to get the full response
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

            # Append assistant message with tool calls to history
            history.append(Message(
                role="assistant",
                content=content,
                tool_calls=tool_calls,
            ))

            # Execute tools
            results = await _execute_tools(tool_calls, tools, on_tool_call)

            # Append tool results to history
            for result in results:
                history.append(Message(
                    role="tool",
                    content=result.content,
                    tool_call_id=result.tool_call_id,
                ))

            # Continue the loop — LLM will see tool results and decide next action
            continue

        # No tool calls — this is the final text response
        final_content = content or ""

        # Stream the final response if requested
        if stream and on_chunk and final_content:
            # Since we already have the full response, simulate chunk delivery
            # In a future optimization, the final turn could use true streaming
            for i in range(0, len(final_content), 20):
                await on_chunk(final_content[i:i + 20])

        # Append assistant response to history
        history.append(Message(role="assistant", content=final_content))

        return AgentResponse(
            content=final_content,
            tool_calls_made=all_tool_calls,
            token_usage=total_usage,
            turns_used=turns,
        )

    # Max turns reached — return whatever we have
    history.append(Message(
        role="assistant",
        content="[Reached maximum tool-use turns. Stopping.]",
    ))
    return AgentResponse(
        content="[Reached maximum tool-use turns. Stopping.]",
        tool_calls_made=all_tool_calls,
        token_usage=total_usage,
        turns_used=turns,
    )
