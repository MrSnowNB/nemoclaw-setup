# Replication Notes - RICo Phase 2

Last Updated: 2025-11-06

---

## Environment

- **Machine**: Z8 Workstation
- **OS**: Linux
- **Python**: 3.13.5 (INCOMPATIBLE with MediaPipe)
- **Working Branch**: rico-phase1-complete (baseline)

---

## Known Pitfalls to Avoid Next Run

1. ❌ **DO NOT** install MediaPipe on Python 3.12+ (incompatible)
2. ❌ **DO NOT** remove Phase 1 code when adding Phase 2
3. ❌ **DO NOT** commit changes to chat_server.py without testing Phase 1 mode first
4. ✅ **DO** test each component in isolation before integration
5. ✅ **DO** verify fallback path explicitly (force errors)
6. ✅ **DO** keep ENABLE_RICO_PHASE2 default as false
7. ✅ **DO** use Python 3.10 or 3.11 venv for Phase 2 development (not system Python 3.13)

---

## Replicable Setup Checklist

- [ ] Git branch: rico-phase1-complete (verified working)
- [ ] Python 3.10 in clean venv (NOT 3.13!)
- [ ] pip install -r requirements.txt
- [ ] Test Phase 1: python -m uvicorn src.chat_server:app
- [ ] Browser test: Send message, verify video plays
- [ ] pip install mediapipe opencv-python (Phase 2 deps)
- [ ] Test imports: python -c "import mediapipe, cv2"
- [ ] Create isolated components (mouth_tracker, etc)
- [ ] Test each component standalone
- [ ] Add feature flag to chat_server.py
- [ ] Test Phase 1 mode after flag (must still work)
- [ ] Add RICo integration with try/except
- [ ] Test fallback path (force Phase 2 error)
- [ ] Final validation: Phase 1 and Phase 2 modes

---

## Flaky Tests

None documented yet.

---

## Recurring Errors

- MediaPipe installation fails on Python 3.13+
- Solution: Use Python 3.10 or 3.11
- Mouth tracker test fails with 0.0% detection rate on existing video clips
- Solution: Use videos with clear, detectable human faces (existing clips may be animated avatars)

---

## RICo Pipeline Integration Failure (2025-11-06 11:50am)

**Issue**: Integration test generates video but no mouth sync applied
**Agent behavior**: Claimed success based on video file existence, not content
**Human verification**: Caught the bug - mouth static in output

**Root cause investigation needed:**
- Verify compositor is being called per-frame
- Check if compositor is actually modifying frames
- Confirm viseme mapping producing different outputs per phoneme

**Lesson learned**: File existence ≠ correct content
**Prevention**: Require visual diff check or frame comparison in tests

## [2026-03-30] — Migration from vLLM to Ollama

**Environment Delta:** Shifted inference from vLLM (incompatible with Ampere A6000 for BF16/FP8 Nemotron) to local Ollama service.
**Hardware Notes:** 4x NVIDIA RTX A6000 (Compute Capability 8.6). Models stored on 7.3TB HDD and linked to ~/.ollama/models.
**Model Used:** qwen3.5:35b (Q4_K_M GGUF).
**Connection:** OpenAI-compatible endpoint at http://localhost:11434/v1.


## [2026-03-30] — Node.js v22 Environment Update

- **Status:** OpenClaw core functional on Node v22.22.2.
- **Verification:** 'openclaw channels list' returns successful empty list.


## [2026-03-30] — MILESTONE: NEO SANDWICH Operational

**Status:** VERIFIED WORKING.
**Performance:** 4-hop chain executed in 4374ms total.
- lore: 138ms (classification)
- alice: 2451ms (initial thought)
- neo: 406ms (adversarial approval)
- alice: 1347ms (final refinement)
**Architecture:** state_bus.py (44 lines), one table (hop), three primitives (hop, chain, score).
**Environment:** All models warm and resident across 4x A6000.
**Next Steps:** Implement Telegram channel and wire chat_server.py to neo_sandwich().


## [2026-03-30] — MILESTONE 2: Telegram Channel Operational

**Status:** LIVE.
**Verification:** 'telegram sendMessage ok chat=8689455578' confirmed in logs.
**Architecture:** 
- OpenClaw gateway running as systemd user service on port 18789.
- Inference routing to local Ollama (qwen3.5:35b) via OpenAI-compatible API.
- Telegram bot @EveryRickNeedsMortyBot is active and paired.
**Pending:** 
- Wiring NEO SANDWICH loop as the primary gateway inference handler.
- Secure token rotation into .env environment.

