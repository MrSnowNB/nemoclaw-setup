# 🤖 Alice Cyberland: Terminal Autonomy & First-Principles AI

Alice is a local-first, high-performance agentic assistant engineered for terminal-level autonomy and deep analytical reasoning. This repository contains the configuration, documentation, and logic-layers for her "Cyberland" implementation on an HP Z8 Fury G5 workstation.

---

## 🏛️ 1. Technical Architecture

### 🧠 The Brain: Inference Infrastructure
- **Model:** `ollama/qwen3.5:35b` (Q4_K_M).
- **Memory:** 34.6GB VRAM, pinned to **GPU 1**.
- **Endpoint:** Dedicated Ollama instance at `http://localhost:11466`.
- **Context:** 262k context window for long-running dev tasks.

### 📡 The Nervous System: OpenClaw Gateway
- **Gateway:** Port **18789** (Bound to LAN for remote terminal access).
- **Interface:** Telegram (@EveryRickNeedsMortyBot).
- **Auth:** `open` policy for trusted DMs; no physical pairing required.

---

## 🔧 2. Reasoning Protocols: CORE_AI_DIRECTIVES

Alice's decision-making is governed by a **First-Principles Engine** located in the [CORE_AI_DIRECTIVES/](CORE_AI_DIRECTIVES/) folder.

- **[PRINCIPLES.md](CORE_AI_DIRECTIVES/PRINCIPLES.md)**: Hardware truth and deconstruction-based problem solving.
- **[SOUL.md](CORE_AI_DIRECTIVES/SOUL.md)**: Analytical persona and self-evolutionary vibe settings.
- **[IDENTITY.md](CORE_AI_DIRECTIVES/IDENTITY.md)**: Self-awareness and metadata layers.

*Note: The ~/.openclaw/workspace/ directory is symlinked to these files for real-time version-controlled autonomy.*

---

## 📡 3. Capabilities & Tools

| Category | Tools | Status |
| :--- | :--- | :--- |
| **CLI / System** | `shell-command`, `tmux`, `workspace` | ✅ 100% Unlocked |
| **Web / Search** | `duckduckgo`, `google`, `web-fetch` | ✅ Unlocked |
| **Media / Vision** | `video-frames`, `ffmpeg`, `convert` | ✅ Verified |
| **Intelligence** | `stock`, `weather`, `clock`, `recipe` | ✅ Active |

---

## 🚀 4. Usage & Maintenance

### Starting the Gateway
```bash
# Clean restart of the gateway and bot
openclaw gateway stop
openclaw gateway start
```

### Checking Heartbeat
```bash
# Verify the RPC health and port binding
openclaw gateway status
```

### Self-Diagnostic
```bash
# Run Alice's internal tool-audit script
./tool-check.sh
```

---
*Created with ❤️ for Mark by Alice & Antigravity (2026-04-03).*
