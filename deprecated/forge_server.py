"""
forge_server.py — Transparent Ollama Proxy for OpenClaw.

This server is a thin translation layer between OpenClaw (which speaks
OpenAI API) and Ollama (which has its own API). It does NOT inject system
prompts, manage memory, or run agent chains — OpenClaw handles all of that.

Architecture:
  Telegram → OpenClaw (brain) → Forge Proxy (this) → Ollama (GPU 3)
"""
import time
import uuid
import json
import asyncio
import httpx

from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

# ── Configuration ──────────────────────────────────────────────
OLLAMA_HOST = "http://127.0.0.1:11437"
DEFAULT_MODEL = "qwen3.5:35b"

app = FastAPI(title="Forge Proxy")


@app.get("/health")
async def health():
    return {"status": "ok", "server": "forge-proxy", "backend": OLLAMA_HOST}


@app.get("/v1/models")
async def list_models():
    """OpenAI-compatible model listing."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{OLLAMA_HOST}/api/tags")
            data = resp.json()
            models = []
            for m in data.get("models", []):
                models.append({
                    "id": m["name"],
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "ollama-local",
                })
            return {"object": "list", "data": models}
    except Exception as e:
        return {"object": "list", "data": [
            {"id": DEFAULT_MODEL, "object": "model", "created": int(time.time()), "owned_by": "ollama-local"}
        ]}


async def _ollama_stream(messages: list, model: str):
    """Stream tokens from Ollama and yield OpenAI SSE chunks."""
    chunk_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    ts = int(time.time())

    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {
            "num_predict": 4096,
            "keep_alive": -1,
        },
        "think": False,
    }

    try:
        async with httpx.AsyncClient(timeout=600) as client:
            async with client.stream("POST", f"{OLLAMA_HOST}/api/chat", json=payload) as resp:
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    try:
                        obj = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    content = obj.get("message", {}).get("content", "")
                    done = obj.get("done", False)

                    if content:
                        chunk = {
                            "id": chunk_id,
                            "object": "chat.completion.chunk",
                            "created": ts,
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {"content": content},
                                "finish_reason": None
                            }]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"

                    if done:
                        stop_chunk = {
                            "id": chunk_id,
                            "object": "chat.completion.chunk",
                            "created": ts,
                            "model": model,
                            "choices": [{
                                "index": 0,
                                "delta": {},
                                "finish_reason": "stop"
                            }]
                        }
                        yield f"data: {json.dumps(stop_chunk)}\n\n"
                        yield "data: [DONE]\n\n"
                        return

    except Exception as e:
        error_chunk = {
            "id": chunk_id,
            "object": "chat.completion.chunk",
            "created": ts,
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"content": f"[Ollama error: {e}]"},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(error_chunk)}\n\n"
        yield "data: [DONE]\n\n"


async def _ollama_sync(messages: list, model: str) -> str:
    """Non-streaming Ollama call."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "num_predict": 4096,
            "keep_alive": -1,
        },
        "think": False,
    }

    async with httpx.AsyncClient(timeout=600) as client:
        resp = await client.post(f"{OLLAMA_HOST}/api/chat", json=payload)
        data = resp.json()
        return data.get("message", {}).get("content", "").strip()


@app.post("/v1/chat/completions")
@app.post("/v1/completions")
async def chat_completions(request: Request):
    body = await request.json()

    model = body.get("model", DEFAULT_MODEL)
    # Strip provider prefix if present (e.g. "forge/qwen3.5:35b" -> "qwen3.5:35b")
    if "/" in model:
        model = model.split("/", 1)[-1]

    messages = body.get("messages", [])

    # Normalize structured content blocks to plain text
    normalized = []
    for m in messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        if isinstance(content, list):
            # OpenAI multi-part content -> extract text
            text_parts = []
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            content = "\n".join(text_parts) if text_parts else str(content)
        normalized.append({"role": role, "content": content})

    stream = body.get("stream", False)

    if stream:
        return StreamingResponse(
            _ollama_stream(normalized, model),
            media_type="text/event-stream",
        )

    # Non-streaming
    try:
        content = await _ollama_sync(normalized, model)
    except Exception as e:
        content = f"[Ollama error: {e}]"

    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "system_fingerprint": "fp_ollama",
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }


@app.post("/v1/responses")
async def responses_endpoint(request: Request):
    """OpenAI Responses API compatibility."""
    body = await request.json()
    model = body.get("model", DEFAULT_MODEL)
    if "/" in model:
        model = model.split("/", 1)[-1]

    messages = body.get("messages", body.get("input", []))
    if isinstance(messages, str):
        messages = [{"role": "user", "content": messages}]

    # Normalize
    normalized = []
    for m in messages:
        if isinstance(m, str):
            normalized.append({"role": "user", "content": m})
        else:
            role = m.get("role", "user")
            content = m.get("content", "")
            if isinstance(content, list):
                text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                content = "\n".join(text_parts)
            normalized.append({"role": role, "content": content})

    try:
        content = await _ollama_sync(normalized, model)
    except Exception as e:
        content = f"[Ollama error: {e}]"

    return {
        "id": f"resp-{uuid.uuid4().hex[:8]}",
        "object": "response",
        "output": [{"type": "message", "role": "assistant", "content": [{"type": "text", "text": content}]}],
    }
