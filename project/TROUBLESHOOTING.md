## RICo Integration Test Produces Video But No Mouth Sync

**Context**: MVP-1.2 visual verification - output video has no mouth synchronization
**Symptom**: Video plays but mouth is static/unchanged from base video
**Observed**: Video duration correct, has audio, but mouth movements don't match speech
**Probable Cause**:
- ROI compositor not actually replacing mouth regions in frames
- Per-frame processing loop not applying viseme changes
- Pipeline using base video frames directly without compositing
- Compositor function exists but returns original frame unchanged
**Quick Fix**: Add per-frame visual debug output to verify compositing
**Permanent Fix**: Add unit test for compositor with known input/output pairs
**Prevention**: Require visual diff between base frame and composited frame in tests

## [2026-03-30] — OpenAI-Compatible Ollama Integration Limitations

**Context:** Updating call_ollama to v1/chat/completions.
**Symptom:** Potential for timeouts or fixed response lengths.
**Known Limitations:**
3. Model ID 'qwen3.5:35b' is hardcoded (needs OLLAMA_MODEL variable support).
4. No retry logic on connection errors (needs 3-attempt backoff implementation).


## [2026-03-30] — Qwen 3.5 Reasoning Field Behavior

**Context:** Model output via OpenAI-compatible API.
**Symptom:** 'content' field may be empty while model is in 'Thinking Process'.
**Observation:** Ollama returns thinking process in 'choices[0].message.reasoning'. If 'max_tokens' is too low, the model may hit the limit before completing the thinking phase and starting the actual 'content' response.
**Recommendation:** Keep 'max_tokens' >= 1024 to ensure enough headroom for both reasoning and response.


### [CLAW-002] OpenClaw CLI Missing or Not Built
- **Date:** 2026-03-30
- **Status:** RESOLVED
- **Context:** Verifying NemoClaw environment after discovering source in ~/.nemoclaw/source
- **Symptom:** 'openclaw' command not found; no binary in ~/.nemoclaw/source/bin/
- **Error Snippet:** bash: openclaw: command not found
- **Probable Cause:** Node.js dependencies not installed or CLI not linked/built from source.
- **Quick Fix:** Run 'npm install && npm run build' in ~/.nemoclaw/source
- **Permanent Fix:** Add CLI build step to the automated setup checklist.
- **Prevention:** Always check for 'node_modules' and 'dist/bin' before attempting to run source-based CLIs.


### [CLAW-003] Node.js Version Incompatibility
- **Date:** 2026-03-30
- **Status:** RESOLVED
- **Context:** Running openclaw core binary after build
- **Symptom:** Command fails with engine version error
- **Error Snippet:** openclaw: Node.js v22.12+ is required (current: v20.19.5).
- **Probable Cause:** System/Workspace Node.js version (v20) is lower than the required v22 for OpenClaw 2026.x.
- **Quick Fix:** Install Node 22 via nvm: 'nvm install 22 && nvm use 22'
- **Permanent Fix:** Update the workstation's default Node.js runtime or ensure the shell environment uses a compatible version.
- **Prevention:** Always verify 'node --version' against the 'engines' field in package.json before execution.

