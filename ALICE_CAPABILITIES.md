# 🤖 Alice: Capabilities & User Guide

Alice is a high-performance agentic assistant integrated with your local system and the web. This guide serves as a reference for her available tools, their options, and how to command her effectively.

---

## 🐚 1. System & Terminal (CLI Focus)

These tools allow Alice to interact directly with your Linux environment.

### 🖥️ `shell-command`
Allows Alice to execute bash commands.
- **Usage:** "Alice, check the disk space," or "Alice, find all .log files in /tmp and delete them."
- **Autonomy:** She can run single commands or complex piped scripts.
- **Safety:** She inherits your user permissions. Exercise caution with destructive prompts.

### 🧵 `tmux`
Remote-control for terminal sessions.
- **Usage:** "Alice, start a new tmux session named 'monitor' and run htop," or "Alice, check the output of the 'inference' pane."
- **Pro-Tip:** Use this for long-running tasks you want to check on later via Telegram.

### 📁 `workspace`
Persistent memory and file management.
- **Usage:** "Alice, what do you remember about our vibe?" or "Alice, update your identity to reflect that I am a Senior Dev."
- **Files:** Primarily manages `~/.openclaw/workspace/IDENTITY.md` and `MEMORY.md`.

---

## 🌐 2. Web & Research

Alice uses these to fetch real-time information from the outside world.

### 🦆 `duckduckgo` / `google-search`
Standard web searching.
- **Options:** You can specify `region` (e.g., "in the UK") or `time` (e.g., "past 24 hours").
- **Usage:** "Alice, find the latest news on NVIDIA H200 availability."

### 🔗 `web-fetch`
"Reading" specific URLs.
- **Usage:** "Alice, read this article and summarize the key points: [URL]."
- **Capabilities:** Can handle HTML-to-Markdown conversion for clean reading.

### 🗺️ `apple-map-search`
Spatial and location queries.
- **Usage:** "Alice, find coffee shops near me."

---

## 📊 3. Utilities & Media

### ☔ `weather`
Real-time atmospheric conditions.
- **Usage:** "Alice, what's the weather like?" or "Alice, should I wear a jacket in New York today?"
- **Backend:** Uses `wttr.in`. No API key needed.

### 🎬 `video-frames`
Visual analysis of video files.
- **Usage:** "Alice, look at this video and tell me what color the car is."
- **Note:** She extracts frames and passes them to her vision-capable brain.

### 📈 `stock`
Market data.
- **Usage:** "Alice, how is NVDA performing today?"

---

## 💡 Pro-Tips for Prompting Alice

1.  **Be Explicit about Tools:** If you want a terminal command specifically, say "Alice, use the shell to..."
2.  **Chaining:** You can ask for multiple things: "Alice, check the weather, then find a news article about it and summarize it for me."
3.  **Self-Correction:** If she fails an edit, you can tell her: "Alice, you don't have permission for that file, try checking your workspace directory instead."

---
*Last Updated: 2026-04-02*
