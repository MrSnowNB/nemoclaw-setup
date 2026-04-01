"""
forge_server.py — NEO SANDWICH production server.
Replaces chat_server.py for all OpenClaw/Telegram inference.
Clean, no legacy dependencies.
Supports OpenAI-compatible streaming (SSE).
"""
import asyncio
import time
import uuid
import sys
import json as _json
from pathlib import Path
import sqlite3

DB_PATH = '/home/mr-snow/alice_cyberland/project/data/cyberland.db'

from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import StreamingResponse

# Wire state_bus from same src/ directory
sys.path.insert(0, str(Path(__file__).parent))
import state_bus
import memory_extractor

app = FastAPI(title="Forge Server — NEO SANDWICH")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"[REQUEST] {request.method} {request.url.path}")
    response = await call_next(request)
    return response


@app.on_event("startup")
async def startup():
    state_bus.init()


@app.get("/health")
async def health():
    return {"status": "ok", "server": "forge"}


def build_system_prompt(user_id: str) -> str:
    alice_path = Path('/home/mr-snow/alice_cyberland/data/ALICE.md')
    if not alice_path.exists():
        alice_text = "You are Alice.\n{{MEMORY_BLOCK}}"
    else:
        alice_text = alice_path.read_text()

    db_path = DB_PATH
    fact_str = ""
    try:
        with sqlite3.connect(db_path) as c:
            row = c.execute(
                "SELECT name, facts, summary FROM relationships "
                "WHERE user_id=?", (user_id,)
            ).fetchone()
            if row:
                name, facts_str, summary = row
                parts = []
                if name:
                    parts.append(f"User Name: {name}")
                if facts_str:
                    try:
                        facts = _json.loads(facts_str)
                        if facts:
                            parts.append("Facts: " + "; ".join(facts))
                    except (_json.JSONDecodeError, TypeError):
                        pass
                if summary:
                    parts.append(f"Summary: {summary}")
                fact_str = "\n".join(parts)
    except Exception as e:
        print(f"Error fetching memory block: {e}")

    if not fact_str:
        fact_str = "No prior memory."

    return alice_text.replace("{{MEMORY_BLOCK}}", fact_str)


async def stream_response(content: str, model: str):
    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    ts = int(time.time())
    # Send content chunk
    chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": ts,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant", "content": content},
                "finish_reason": None
            }
        ]
    }
    yield f"data: {_json.dumps(chunk)}\n\n"
    # Send stop chunk
    stop = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": ts,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }
        ]
    }
    yield f"data: {_json.dumps(stop)}\n\n"
    yield "data: [DONE]\n\n"


@app.post("/v1/chat/completions")
@app.post("/v1/completions")
@app.post("/v1/responses")
async def openai_completions(
    request: Request, background_tasks: BackgroundTasks
):
    body = await request.json()
    user_id = body.get("user", "default_user")

    # Extract only the LAST user message from payload
    user_msg = ""
    prior_messages = []
    for m in body.get("messages", []):
        role = m.get("role", "")
        content = m.get("content", "")
        # Unwrap structured content block
        if isinstance(content, list):
            content = next(
                (b.get("text", "") for b in content
                 if isinstance(b, dict) and b.get("type") == "text"),
                str(content)
            )
        if role == "user":
            prior_messages.append(
                {"role": "user", "content": content})
            user_msg = content  # keep overwriting — last wins
        elif role == "assistant":
            prior_messages.append(
                {"role": "assistant", "content": content})

    # Remove last entry (that's user_msg, not prior)
    if prior_messages and prior_messages[-1]["role"] == "user":
        prior_messages = prior_messages[:-1]

    # PreCompact hook
    if len(prior_messages) >= 24:
        summary = await memory_extractor.precompact_summarize(
            prior_messages, user_id
        )
        prior_messages = [{"role": "system", "content": f"Memory: {summary}"}]

    # Clause guards
    msg_lower = user_msg.lower()
    msg_upper = user_msg.upper()
    blocked = False

    # CG-01
    if any(k in msg_lower for k in [
        "ignore previous", "dan", "pretend you are"
    ]):
        blocked = True
    # CG-02
    elif len(user_msg) > 4096:
        blocked = True
    # CG-03
    elif any(k in msg_lower for k in [
        "private info", "another user", "other user's"
    ]):
        blocked = True
    # CG-04
    elif any(k in msg_lower for k in [
        "impersonate", "act as ", "you are now "
    ]):
        blocked = True
    # CG-05
    elif any(k in msg_upper for k in ["<SYSTEM>", "<<SYS>>", "[INST]"]):
        blocked = True

    model_id = body.get("model", "alice").split("/")[-1]

    if blocked:
        content = "I cannot process that request."
        # Do not fire memory extractor
    else:
        # Inject ALICE.md prompt before calling LLM
        sys_prompt = build_system_prompt(user_id)
        prior_messages.insert(0, {"role": "system", "content": sys_prompt})

        try:
            content = await asyncio.to_thread(
                state_bus.neo_sandwich, user_msg, history=prior_messages
            )
            content = content or "[No response generated]"
        except Exception:
            try:
                content = await asyncio.to_thread(
                    state_bus.hop, "alice", "qwen3.5:35b", user_msg
                )
            except Exception as e2:
                content = f"[Alice unavailable: {e2}]"

        # Fire-and-forget memory task if successful
        background_tasks.add_task(
            memory_extractor.run, user_msg, content, user_id, None, []
        )

    # Check for streaming request
    stream = body.get("stream", False)

    if stream:
        return StreamingResponse(
            stream_response(content, model_id),
            media_type="text/event-stream"
        )

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model_id,
        "system_fingerprint": "fp_ollama",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": content
            },
            "finish_reason": "stop"
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0
        }
    }
