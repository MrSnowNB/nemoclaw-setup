---

## 🏛️ 0. Hardware & AI-First Architecture

Alice is engineered for **Local High-Performance Inference**.
- **Brain:** `ollama/qwen3.5:35b` (Q4_K_M).
- **Endpoint:** Dedicated instance at `http://localhost:11466` (GPU 1 Pinned).
- **Reasoning:** Alice uses a **First-Principles Reasoning Engine** (see `PRINCIPLES.md` in her workspace) to break problems down into atomic steps.

---

## 📡 1. Network & External Access

- **Web Search & Fetch:** Comprehensive information retrieval (DuckDuckGo, Google, Serper).
- **Weather Info:** Real-time atmospheric forecasts via `wttr.in`.
- **Content Extraction:** Deep reading of URLs and HTML-to-Markdown summarization.

## 📁 2. File & Workspace Operations

- **Read/Write:** Full management of text, code, and image files.
- **Smart Edit:** Targeted line replacements and code refactoring.
- **Auto-Directory:** Automatic creation and recursive management of file structures.
- **Self-Modification:** Ability to evolve `IDENTITY.md` and `MEMORY.md` in the workspace.

## 🐚 3. System Commands (CLI Focus)

- **Bash Execution:** Direct shell access with background job support.
- **Long-Running Processes:** Monitoring and state preservation for dev tasks.
- **PTY Support:** Interaction with terminal UIs and TUI-based tools.
- **ElevenLabs TTS:** Voice synthesis and audio-visual sync mapping.

## 🤖 4. Session & Agent Management

- **Orchestration:** List, send, and monitor high-concurrency tool sessions.
- **Sub-Agents:** Spawn and steer specialized workers for sub-tasks.
- **Soul/Persona:** Steerable agent identities (e.g., Senior Dev, Creative, Debugger).

## 🎯 5. Task Automation & Skills

- **`video-frames`**: Extraction and analysis via `ffmpeg`.
- **`ClawFlow`**: Complex multi-step workflow orchestration patterns.
- **`healthcheck`**: Network diagnostics and security hardening.
- **`node-connect`**: IoT and device connection troubleshooting.
- **`skill-creator`**: Self-improvement and new skill generation.

## 🎨 6. Canvas & UI Presentation

- **UI Snapshot:** Take snapshots of rendered interfaces.
- **DOM Manipulation:** Evaluate JS and navigate node trees in real-time.
- **Interactive UI:** Present or hide Canvas elements for user guidance.

## 📱 7. Messaging & Connectivity

- **Cross-Platform:** Telegram, WhatsApp, Discord, Signal, Slack, and more.
- **Interaction:** Polls, reactions, threading, and interactive button support.

---

## 💡 Pro-Tips for Prompting Alice

1.  **Terminal Power:** Use "Alice, spin up a tmux session for X" to keep a process running after you disconnect.
2.  **Context Loading:** Say "Alice, fetch the docs at [URL] and tell me how to implement Y."
3.  **Visual Input:** If you send a video, Alice can use the `video-frames` skill to "see" what's inside.

---
*Last Updated: 2026-04-02*
