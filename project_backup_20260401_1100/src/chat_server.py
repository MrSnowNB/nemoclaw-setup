print('--- BOOTING VERSION 3 ---')
"""
Alice in Cyberland - WebSocket Chat Server with SHRP v1.0 Integration
SELF-HEALING RECOVERY PROTOCOL (SHRP) v1.0 - Comprehensive Resilience Framework

Handles real-time chat with Ollama, TTS, and video state management
Integrated with SHRP for self-healing, structured logging, and event emission
"""

import asyncio
from contextlib import asynccontextmanager
import json
import uuid
import time
from typing import Dict, Set, List
from pathlib import Path
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from pydantic import BaseModel

from .tts_engine import AliceTTSEngine
from .video_duration_matcher import VideoDurationMatcher
from .shrp_logger import get_logger, EventType
from .shrp_checkpoint_manager import get_checkpoint_manager
from .shrp_recovery_engine import get_recovery_engine
from .shrp_event_emitter import get_event_emitter

import sys
sys.path.insert(0, str(Path(__file__).parent))
import state_bus
import librosa  # Audio duration measurement
import yaml
import requests
import os

# Load configuration
DATA_DIR = Path("/home/mr-snow/alice_cyberland/project/data")
manifest_path = DATA_DIR / "video_manifest.yaml"
with open(manifest_path, "r") as f:
    MANIFEST = yaml.safe_load(f)

# Chat state manager with SHRP v1.0 integration
class ChatStateManager:
    def __init__(self):
        # Core components
        self.tts_engine = AliceTTSEngine()
        self.video_matcher = VideoDurationMatcher()  # RICo Phase 1: Duration matching

        # SHRP v1.0 Integration
        self.logger = get_logger()
        self.checkpoint_manager = get_checkpoint_manager()
        self.recovery_engine = get_recovery_engine()
        self.event_emitter = get_event_emitter()

        # Load configuration
        self.state_transitions = MANIFEST.get('state_transitions', {})
        self.video_states = MANIFEST.get('video_clips', {})
        self.active_clients: Set[WebSocket] = set()
        self.current_video_state = "idle"

        # SHRP Session Management
        self.session_id = str(uuid.uuid4())
        self.task_counter = 0

        # System state for checkpointing
        self.system_state = {
            "current_video_state": self.current_video_state,
            "active_clients_count": 0,
            "total_messages_processed": 0,
            "last_message_timestamp": None,
            "recovery_metrics": {},
            "checkpoint_version": "1.0"
        }

        # Initialize SHRP systems
        self._initialize_shrp()
        self.logger.set_context("component", "chat_server")
        self.logger.set_context("session_id", self.session_id)

        # Initial checkpoint
        self._create_checkpoint("system_startup")

        # Session start event
        self.event_emitter.emit_session_event(
            EventType.SESSION_START,
            self.session_id,
            {"message": "Alice in Cyberland chat server initialized with SHRP v1.0"}
        )

    def _initialize_shrp(self):
        """Initialize SHRP v1.0 systems and components"""
        self.logger.log_event(
            EventType.SYSTEM_INFO,
            {
                "operation": "shrp_initialization",
                "component": "chat_server",
                "shrp_version": "1.0"
            },
            tags=["initialization", "shrp"]
        )

        # Verify SHRP component health
        try:
            shrp_health = {
                "logger_active": self.logger is not None,
                "checkpoint_manager_active": self.checkpoint_manager is not None,
                "recovery_engine_active": self.recovery_engine is not None,
                "event_emitter_active": self.event_emitter is not None,
                "session_initialized": self.session_id is not None
            }

            self.logger.log_system_health_check(
                component="shrp_integration",
                status="healthy" if all(shrp_health.values()) else "degraded",
                metrics={"components": shrp_health}
            )

        except Exception as e:
            self.logger.log_event(
                EventType.SYSTEM_ERROR,
                {
                    "operation": "shrp_initialization",
                    "error": str(e),
                    "component": "chat_server"
                },
                severity="err",
                tags=["initialization", "error"]
            )

    def _create_checkpoint(self, context: str):
        """Create a system state checkpoint"""
        try:
            # Update current system state
            self.system_state.update({
                "current_video_state": self.current_video_state,
                "active_clients_count": len(self.active_clients),
                "last_checkpoint_context": context,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            # Create checkpoint
            checkpoint_id = self.checkpoint_manager.create_checkpoint(
                state=self.system_state.copy(),
                metadata={
                    "context": context,
                    "session_id": self.session_id,
                    "component": "chat_server"
                }
            )

            # Emit checkpoint event
            self.event_emitter.emit_checkpoint_event(
                EventType.CHECKPOINT_CREATE,
                checkpoint_id,
                {"context": context, "state_keys": list(self.system_state.keys())}
            )

            return checkpoint_id

        except Exception as e:
            self.logger.log_event(
                EventType.SYSTEM_ERROR,
                {
                    "operation": "checkpoint_creation",
                    "context": context,
                    "error": str(e)
                },
                severity="err",
                tags=["checkpoint", "error"]
            )
            return None

    async def broadcast(self, message: dict):
        """Broadcast message to all connected clients"""
        disconnected = set()
        for websocket in self.active_clients:
            try:
                await websocket.send_json(message)
            except Exception as e:
                print(f"Broadcast error: {e}")
                disconnected.add(websocket)

        # Remove disconnected clients
        self.active_clients -= disconnected

    def get_video_state_for_message(self, message: str) -> str:
        """Determine appropriate video state based on message content"""
        message_lower = message.lower()

        # Response states
        if any(word in message_lower for word in ['great', 'wonderful', 'excellent', 'amazing']):
            return "friendly_speaking"
        elif any(word in message_lower for word in ['sorry', 'concerned', 'worried', 'help']):
            return "empathetic"
        elif any(word in message_lower for word in ['goodbye', 'bye', 'see you']):
            return "farewell"
        else:
            return "neutral_speaking"

    async def handle_user_message(self, user_message: str) -> Dict:
        """Process user message and generate AI response with SHRP monitoring"""
        task_id = f"task_{self.task_counter}"
        self.task_counter += 1

        # Log task start
        self.logger.log_task_start(
            task_id,
            "process_user_message",
            {"user_message": user_message, "length": len(user_message)}
        )
        self.event_emitter.emit_task_event(
            task_id,
            EventType.TASK_START,
            "process_user_message",
            {"user_message": user_message}
        )

        try:
            # Change to listening state
            await self.broadcast({
                "type": "video_state",
                "state": "listening",
                "loop": self.video_states["listening"].get("loop", True)
            })

            # Log LLM request start
            llm_request_id = f"llm_{task_id}"
            self.logger.set_context("correlation_id", llm_request_id)
            self.event_emitter.emit_llm_event(
                EventType.LLM_REQUEST,
                llm_request_id,
                {"user_message": user_message, "model": "llama3.1:8b-instruct-q4_K_M"}
            )

            # Get AI response from Ollama
            start_time = datetime.now(timezone.utc)
            ollama_response = await self.call_ollama(user_message)
            end_time = datetime.now(timezone.utc)

            # Log LLM response
            duration_ms = int((end_time - start_time).total_seconds() * 1000)
            if ollama_response.startswith("Connection error"):
                self.event_emitter.emit_llm_event(
                    EventType.LLM_ERROR,
                    llm_request_id,
                    {
                        "error": "connection_failed",
                        "response": ollama_response,
                        "duration_ms": duration_ms
                    }
                )
                # Trigger recovery for LLM failure
                self.recovery_engine.detect_failure(
                    "llm_request_failed",
                    {"request_id": llm_request_id, "error": "connection_failed"},
                    {"user_message": user_message, "session_id": self.session_id}
                )
            else:
                self.event_emitter.emit_llm_event(
                    EventType.LLM_RESPONSE,
                    llm_request_id,
                    {
                        "response_length": len(ollama_response),
                        "duration_ms": duration_ms
                    }
                )

            # Determine video state for response
            video_state = self.get_video_state_for_message(ollama_response)

            # Generate audio with SHRP monitoring
            tts_request_id = f"tts_{task_id}"
            self.logger.set_context("correlation_id", tts_request_id)
            self.event_emitter.emit_tts_event(
                EventType.TTS_REQUEST,
                tts_request_id,
                {"text_length": len(ollama_response)}
            )

            audio_path = self.tts_engine.synthesize(
                ollama_response,
                output_dir="outputs/audio"
            )

            # Validate audio generation
            audio_success = False
            audio_size = 0
            if audio_path and os.path.exists(audio_path):
                audio_size = os.path.getsize(audio_path)
                audio_success = audio_size > 1000  # Minimum file size check

            if audio_success:
                self.event_emitter.emit_tts_event(
                    EventType.TTS_COMPLETE,
                    tts_request_id,
                    {"audio_path": audio_path, "file_size": audio_size}
                )
            else:
                # TTS failure - trigger recovery
                error_details = {
                    "request_id": tts_request_id,
                    "audio_path": audio_path,
                    "file_exists": os.path.exists(audio_path) if audio_path else False,
                    "file_size": audio_size if audio_path else 0
                }

                if audio_path and not os.path.exists(audio_path):
                    self.event_emitter.emit_tts_event(
                        EventType.TTS_FILE_MISSING,
                        tts_request_id,
                        error_details
                    )
                else:
                    self.event_emitter.emit_tts_event(
                        EventType.TTS_ERROR,
                        tts_request_id,
                        error_details
                    )

                # Trigger recovery for TTS failure
                self.recovery_engine.detect_failure(
                    "tts_generation_failed",
                    error_details,
                    {"response_text": ollama_response, "session_id": self.session_id}
                )

            # Update system state
            self.system_state["total_messages_processed"] += 1
            self.system_state["last_message_timestamp"] = datetime.now(timezone.utc).isoformat()

            # Periodic checkpoint (every 10 messages)
            if self.system_state["total_messages_processed"] % 10 == 0:
                self._create_checkpoint(f"message_{self.system_state['total_messages_processed']}")

            if audio_success:
                # RICo Phase 1: Measure audio duration
                audio_duration = librosa.get_duration(filename=audio_path)

                # RICo Phase 1: Create duration-matched video
                video_path = self.video_matcher.create_duration_matched_clip(
                    emotion_state=video_state,
                    target_duration=audio_duration
                )

                assert audio_path is not None, "audio_path must not be None in audio_success block"
                assert video_path is not None, "video_path must not be None in audio_success block"

                response = {
                    "type": "ai_response",
                    "audio_url": f"/audio/{os.path.basename(audio_path)}",
                    "video": f"/ricovideos/{os.path.basename(video_path)}",
                    "text": ollama_response,
                    "duration": audio_duration
                }
            else:
                # SHRP R2.1 Fix: Fallback TTS generation when primary method fails
                audio_filename = f"response_{uuid.uuid4().hex[:8]}.wav"
                audio_path = os.path.join("outputs/audio", audio_filename)
                os.makedirs("outputs/audio", exist_ok=True)

                # Use pyttsx3 directly for TTS (SHRP critical fix)
                import pyttsx3
                tts_engine = pyttsx3.init()
                tts_engine.save_to_file(ollama_response, audio_path)
                tts_engine.runAndWait()

                # Verify file was created
                if os.path.exists(audio_path) and os.path.getsize(audio_path) > 1000:
                    audio_success_fixed = True
                    self.event_emitter.emit_tts_event(
                        EventType.TTS_COMPLETE,
                        f"tts_fixed_{task_id}",
                        {"audio_path": audio_path, "file_size": os.path.getsize(audio_path)}
                    )
                else:
                    audio_success_fixed = False

                if audio_success_fixed:
                    # RICo Phase 1: Measure audio duration
                    audio_duration = librosa.get_duration(filename=audio_path)

                    # RICo Phase 1: Create duration-matched video
                    video_path = self.video_matcher.create_duration_matched_clip(
                        emotion_state=video_state,
                        target_duration=audio_duration
                    )

                    response = {
                        "type": "ai_response",
                        "audio_url": f"/audio/{audio_filename}",
                        "video": f"/ricovideos/{os.path.basename(video_path)}" if video_path else "/video/idle-loop.mp4",
                        "text": ollama_response,
                        "duration": audio_duration
                    }
                else:
                    # Absolute fallback - no audio
                    video_path = self.video_matcher.create_duration_matched_clip(
                        emotion_state=video_state,
                        target_duration=3.0
                    )

                    response = {
                        "type": "ai_response",
                        "audio_url": None,
                        "video": f"/video/{os.path.basename(video_path)}" if video_path else "/video/idle-loop.mp4",
                        "text": ollama_response,
                        "duration": 3.0
                    }

            # Log task completion
            self.logger.log_task_complete(task_id, {"response_type": response["type"], "has_audio": response["audio_url"] is not None})
            self.event_emitter.emit_task_event(
                task_id,
                EventType.TASK_COMPLETE,
                "process_user_message",
                {"response_type": response["type"], "audio_present": response["audio_url"] is not None}
            )

            # Clear correlation context
            self.logger.clear_context("correlation_id")

            return response

        except Exception as e:
            # Log task error
            self.logger.log_task_error(task_id, e, {"user_message": user_message})
            self.event_emitter.emit_task_event(
                task_id,
                EventType.TASK_ERROR,
                "process_user_message",
                {"error": str(e), "user_message": user_message}
            )

            # Trigger general system error recovery
            self.recovery_engine.detect_failure(
                "message_processing_failed",
                {"error": str(e), "task_id": task_id, "user_message": user_message},
                {"session_id": self.session_id}
            )

            # Return fallback response
            return {
                "type": "ai_response",
                "audio_url": None,
                "video": "/video/idle-loop.mp4",
                "text": "I encountered an error processing your message. Please try again.",
                "duration": 3.0
            }

    async def call_ollama(self, message: str) -> str:
        """Call Ollama API for AI response via NEO SANDWICH loop with fallback"""
        try:
            result = await asyncio.to_thread(
                state_bus.neo_sandwich, message
            )
            return result or "[No response generated]"
        except Exception as e:
            # Fallback: single hop, never silent
            try:
                return await asyncio.to_thread(
                    state_bus.hop,
                    "alice", "qwen3.5:35b", message
                )
            except Exception as e2:
                print(f"Ollama Fallback Error: {e2}")
                return f"[Alice unavailable: {e2}]"

# Global state manager
state_manager = ChatStateManager()

# FastAPI app
app = FastAPI(title="Alice in Cyberland Chat")

# Serve static files
app.mount("/static", StaticFiles(directory="static", html=True), name="static")
app.mount("/audio", StaticFiles(directory="outputs/audio"), name="audio")
# Note: /video serves the original clips, /ricovideos serves generated duration-matched videos
app.mount("/video", StaticFiles(directory=str(DATA_DIR / "video_clips")), name="video")
app.mount("/ricovideos", StaticFiles(directory="outputs/video"), name="ricovideos")

@app.get("/ricovideos/{filename}")
async def serve_rico_video(filename: str):
    """Serve RICo-generated duration-matched video files"""
    from fastapi.responses import FileResponse
    video_path = Path("outputs/video") / filename
    if video_path.exists():
        return FileResponse(video_path, media_type="video/mp4")
    # Fallback to .mov extension (depending on FFmpeg output)
    video_path_mov = Path("outputs/video") / Path(filename).with_suffix('.mov')
    if video_path_mov.exists():
        return FileResponse(video_path_mov, media_type="video/mp4")
    return JSONResponse({"error": "RICo video not found"}, status_code=404)

@app.post("/v1/chat/completions")
async def openai_completions(request: Request):
    """OpenAI-compatible shim — routes all inference
    through neo_sandwich() adversarial loop."""
    body = await request.json()
    messages = body.get("messages", [])
    user_msg = next(
        (m["content"] for m in reversed(messages)
         if m.get("role") == "user"), ""
    )
    try:
        result = await asyncio.to_thread(
            state_bus.neo_sandwich, user_msg
        )
        content = result or "[No response generated]"
    except Exception as e:
        try:
            content = await asyncio.to_thread(
                state_bus.hop,
                "alice", "qwen3.5:35b", user_msg
            )
        except Exception as e2:
            content = f"[Alice unavailable: {e2}]"
    return {
        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.get("model", "alice"),
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

# WebSocket endpoint
@app.websocket("/ws/chat")
async def chat_websocket(websocket: WebSocket):
    await websocket.accept()
    state_manager.active_clients.add(websocket)

    try:
        # Send welcome message with greeting clip
        greeting_clip = state_manager.video_matcher.create_duration_matched_clip(
            emotion_state="greeting",
            target_duration=6.0  # Standard greeting duration
        )

        assert greeting_clip is not None, "greeting_clip must not be None"

        # Send initial greeting without video (waits for user interaction)
        await websocket.send_json({
            "type": "ai_response",
            "video": f"/ricovideos/{os.path.basename(greeting_clip)}",
            "text": "Hello! I'm Alice, your guide to Cyberland. Click anywhere to start chatting!",
            "audio_url": None,
            "duration": 6.0
        })

        while True:
            # Receive user message
            data = await websocket.receive_json()
            user_message = data.get("message", "")

            if user_message.strip():
                # Process message and respond
                response = await state_manager.handle_user_message(user_message.strip())
                await websocket.send_json(response)

    except WebSocketDisconnect:
        print("Client disconnected")
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        state_manager.active_clients.remove(websocket)

# HTTP endpoint for health check
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "clients": len(state_manager.active_clients),
        "model": "llama3.1:8b-instruct-q4_K_M"
    }

# Serve chat interface
@app.get("/")
async def get_chat_interface():
    return HTMLResponse(open("static/index.html").read())

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "src.chat_server:app",
        host="0.0.0.0",
        port=8080,
        reload=True,
        log_level="info"
    )
