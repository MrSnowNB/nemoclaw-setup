---
title: "RICo MVP Implementation - Policy Document"
version: "3.0.0"
date: "2025-11-06"
status: "ACTIVE"
baseline: "rico-phase1-complete branch"
objective: "Patent-ready RICo MVP with mouth synchronization"
agent_mode: "STRICT_POLICY_ENFORCEMENT"
---

# RICo MVP Implementation Policy

## ⚠️ CRITICAL MISSION

**Primary Goal:** Create working RICo mouth-sync demo for patent application (PPA filing)

**Success Criteria:**
- Static proof-of-concept video demonstrating phoneme-synchronized mouth movement
- Documentation sufficient for USPTO provisional patent application
- Evidence of end-to-end pipeline functionality

**Phase 1 MUST remain working at all times** - this is fallback for production.

---

## POLICY FRAMEWORK

### Core Principles

1. **All files are markdown with YAML frontmatter or pure YAML**
2. **Each task is atomic, testable, and gated**
3. **On any failure/uncertainty: update living docs, then STOP for human input**
4. **Lifecycle: Plan → Build → Validate → Review → Release (sequential only)**

### Validation Gates

Every task must pass ALL applicable gates:

- **unit**: `pytest -q` green (for testable components)
- **lint**: `ruff` or `flake8` clean (for Python code)
- **type**: `mypy` or `pyright` clean (for typed code)
- **docs**: Spec drift check passes
- **runtime**: Actual execution evidence REQUIRED
- **visual**: Output video/frames inspected by human

### Failure Handling Protocol

**Mandatory sequence on ANY failure:**

1. **Capture logs** → `outputs/logs/failure_YYYYMMDD_HHMMSS.log`
2. **Update TROUBLESHOOTING.md** with new entry
3. **Update REPLICATION-NOTES.md** with environment context
4. **Create ISSUE-{task_id}.md** with failure details
5. **HALT** and wait for human input

**NO RETRIES** without human approval.

---

## STRATEGIC CONTEXT

### Why Phase 2A Failed

Previous attempt at RICo integration produced working components but **no actual mouth synchronization** in output video. Root causes:
- Pipeline integration incomplete
- No frame-by-frame phoneme-to-mouth mapping
- Batch processing logic never assembled

### New Approach: MVP-First

**Focus on patent-ready proof, not production deployment.**

Three phases:
1. **Phase MVP-1**: Static proof-of-concept (THIS WEEK - Patent filing)
2. **Phase MVP-2**: Chat integration with pre-processing (NEXT WEEK - Demo)
3. **Phase 3**: Real-time high-frequency compression (FUTURE - Production)

---

## TASK SEQUENCE: MVP-1 (PATENT PROOF)

### Objective

Generate single video demonstrating RICo protocol end-to-end with verifiable mouth synchronization.

---

### TASK MVP-1.1: Integration Test Framework

**File:** `TASK-MVP1.1-INTEGRATION-TEST.md`

```yaml
---
task_id: "MVP-1.1"
name: "Create RICo Integration Test Framework"
priority: "CRITICAL"
estimated_time: "2 hours"
dependencies: ["2A.2", "2A.3", "2A.4"]
phase: "BUILD"
---

## Objective

Create standalone test script that processes one phrase through complete RICo pipeline and outputs synced video.

## Steps

### Step MVP-1.1.1: Create Test Script

**Action:** Create file `tests/test_rico_mvp_proof.py`

**Content:** Full integration test with:
- Hard-coded test phrase
- TTS generation with phoneme extraction
- Frame-by-frame processing
- Mouth ROI tracking
- Viseme mapping
- ROI compositing
- Video encoding with audio

**Validation:**
```bash
python tests/test_rico_mvp_proof.py
```

**Expected Output:**
```
Starting RICo MVP proof-of-concept...
Generating TTS audio with phonemes...
Audio: outputs/audio/mvp_test.wav, Duration: 6.23s
Phonemes: 42 timestamps
Loading base video: static/video_clips/speaking-neutral.mp4
FPS: 30, Frames needed: 187
Processing frames with RICo pipeline...
Processed 30/187 frames (Time: 1.00s, Phoneme: 'HH', Viseme: 'H')
Processed 60/187 frames (Time: 2.00s, Phoneme: 'AH', Viseme: 'AA')
...
Encoding output video: outputs/patent_demo_synced.mp4
✅ RICo proof-of-concept complete!
Output: outputs/patent_demo_synced.mp4
Frames processed: 187
Processing time: 5.42s
```

**Evidence Required:**
- Terminal output showing all processing steps
- Generated video file: `outputs/patent_demo_synced.mp4`
- Audio file: `outputs/audio/mvp_test.wav`
- Phoneme timeline JSON: `outputs/patent_demo_phonemes.json`

### Step MVP-1.1.2: Verify Output Video Exists

**Action:**
```bash
ls -lh outputs/patent_demo_synced.mp4
file outputs/patent_demo_synced.mp4
ffprobe outputs/patent_demo_synced.mp4
```

**Expected:**
- File exists and is >1MB
- File type: video/mp4
- Duration matches audio (~6 seconds)
- Has both video and audio streams

**Evidence Required:**
- Screenshot of file listing with size
- ffprobe output showing video properties

## Validation Gate: GATE_MVP-1.1

**Assertions:**

- [ ] Test script created: `tests/test_rico_mvp_proof.py`
- [ ] Test executes without Python exceptions
- [ ] Output video file created
- [ ] Output video has correct duration
- [ ] All intermediate logs generated

**Criticality:** CRITICAL

**Evidence Package:**
- Terminal output log: `outputs/logs/mvp1.1_test_run.log`
- Video file: `outputs/patent_demo_synced.mp4`
- Audio file: `outputs/audio/mvp_test.wav`
- Phoneme data: `outputs/patent_demo_phonemes.json`

## On Failure

**If test script crashes:**

1. Capture full error:
   ```bash
   python tests/test_rico_mvp_proof.py 2>&1 | tee outputs/logs/failure_mvp1.1_test_crash.log
   ```

2. Update TROUBLESHOOTING.md:
   ```markdown
   ## RICo Integration Test Crashes
   
   **Context**: TASK MVP-1.1 - Running full pipeline integration test
   **Symptom**: Python exception during test execution
   **Error Snippet**: [paste actual traceback]
   **Probable Cause**: [import error / component missing / etc]
   **Quick Fix**: Verify all Phase 2A components exist and import successfully
   **Permanent Fix**: Add import validation at start of test
   **Prevention**: Run component existence check before integration
   ```

3. Update REPLICATION-NOTES.md:
   ```markdown
   ## Integration Test Failures
   
   Date: 2025-11-06
   Task: MVP-1.1
   Issue: [specific error]
   Environment: [Python version, OS, etc]
   
   **Known Pitfalls:**
   - RICo components must all be imported successfully
   - MediaPipe and OpenCV must be installed
   - Test video files must exist in static/video_clips/
   ```

4. Create ISSUE-MVP1.1.md

5. **HALT** - Do not proceed without fixing

**If output video not created:**

Same protocol, but focus on video encoding step in TROUBLESHOOTING.

## On Success

**Actions:**
```bash
# Commit test framework
git add tests/test_rico_mvp_proof.py
git add outputs/patent_demo_synced.mp4
git add outputs/patent_demo_phonemes.json
git commit -m "MVP-1.1: RICo integration test framework

- Full pipeline test: TTS → Phonemes → Frame processing → Video
- Output: outputs/patent_demo_synced.mp4
- Evidence: outputs/logs/mvp1.1_test_run.log"

git tag v-mvp1.1-integration-test
```

**Proceed to:** TASK MVP-1.2
```

---

### TASK MVP-1.2: Visual Verification (Human Required)

**File:** `TASK-MVP1.2-VISUAL-VERIFICATION.md`

```yaml
---
task_id: "MVP-1.2"
name: "Human Visual Verification of Mouth Sync"
priority: "CRITICAL"
estimated_time: "30 minutes"
dependencies: ["MVP-1.1"]
phase: "VALIDATE"
---

## Objective

**HUMAN VERIFICATION REQUIRED** - Agent cannot complete this task.

Visually confirm that mouth movements in output video are synchronized with speech audio.

## Human Verification Procedure

### 1. Play Output Video

**Action:**
```bash
# Open video in player
vlc outputs/patent_demo_synced.mp4
# or
open outputs/patent_demo_synced.mp4  # Mac
xdg-open outputs/patent_demo_synced.mp4  # Linux
```

**Watch carefully for:**
- Mouth opening/closing during speech
- Mouth shapes changing between phonemes
- Timing alignment with audio
- Smooth transitions between visemes

### 2. Frame-by-Frame Analysis

**Action:** Extract key frames for inspection
```bash
mkdir -p outputs/debug/frame_analysis
ffmpeg -i outputs/patent_demo_synced.mp4 -vf "select='between(n\,0\,60)'" -vsync 0 outputs/debug/frame_analysis/frame_%04d.png
```

**Inspect frames 0, 15, 30, 45, 60:**
- Are mouth shapes visibly different?
- Do closed mouths correspond to silent phonemes?
- Do open mouths correspond to vowel sounds?

**Evidence Required:**
- Screenshots of 5+ different frames showing mouth variation
- Side-by-side comparison with audio waveform

### 3. Audio Waveform Comparison

**Action:** Generate waveform visualization
```bash
ffmpeg -i outputs/audio/mvp_test.wav -filter_complex "showwavespic=s=1920x480" outputs/debug/waveform.png
```

**Compare:**
- Mouth movements during high-amplitude audio (speech)
- Mouth closed during low-amplitude (pauses)
- Timing correlation

**Evidence Required:**
- Screenshot of waveform
- Timestamp correlation notes

### 4. Phoneme Timeline Inspection

**Action:** Review phoneme data
```bash
cat outputs/patent_demo_phonemes.json | jq '.'
```

**Verify:**
- Phonemes have start/end timestamps
- Phonemes cover full audio duration
- No gaps in timeline

### 5. Test with Multiple Phrases (Optional but Recommended)

**Action:** Modify test script to use different phrases:
- "The quick brown fox jumps over the lazy dog"
- "How are you doing today?"
- "This is a test of the RICo protocol"

**Run tests and compare outputs**

## Validation Gate: GATE_MVP-1.2

**HUMAN MUST CONFIRM:**

- [ ] Mouth visibly opens and closes during speech
- [ ] Different mouth shapes observed across frames
- [ ] Timing appears aligned with audio (±0.1 sec acceptable)
- [ ] No obvious glitches or frozen frames
- [ ] Output is suitable for patent demonstration

**Evidence Package (MANDATORY):**

1. Video recording of screen showing synced playback
2. 5+ frame screenshots with mouth variation
3. Waveform comparison image
4. Written assessment (see template below)

## Assessment Template

```markdown
# RICo MVP Visual Verification Report

**Date:** 2025-11-06
**Reviewer:** [Your name]
**Video:** outputs/patent_demo_synced.mp4

## Mouth Synchronization Assessment

**Rating:** [Excellent / Good / Acceptable / Poor / Failed]

**Observations:**
- Mouth opening: [Yes / No / Partially]
- Viseme variation: [Yes / No]
- Timing accuracy: [Within 0.1s / Within 0.5s / Not aligned]
- Visual quality: [Good / Acceptable / Poor]

**Issues Found:**
- [List any problems]

**Specific Frames Reviewed:**
- Frame 15 (0.5s): Mouth [open/closed], Phoneme: [X], Expected: [Y]
- Frame 30 (1.0s): Mouth [open/closed], Phoneme: [X], Expected: [Y]
- Frame 45 (1.5s): Mouth [open/closed], Phoneme: [X], Expected: [Y]

## Patent Suitability

**Suitable for patent filing?** [Yes / No / Needs improvement]

**Reason:**
[Explanation]

## Recommendations

[What to do next]
```

## On Failure

**If mouth does NOT sync:**

1. **CRITICAL ISSUE** - Pipeline not working correctly

2. Update TROUBLESHOOTING.md:
   ```markdown
   ## Mouth Not Syncing in Integration Test
   
   **Context**: MVP-1.2 - Visual verification of RICo output
   **Symptom**: Mouth movements not aligned with speech, or static mouth
   **Probable Cause**: 
   - Phoneme timeline not applied to frames
   - ROI compositor not changing mouth shapes
   - Frame processing loop not using per-frame phonemes
   **Quick Fix**: None - requires pipeline debugging
   **Permanent Fix**: Add per-frame logging to identify where sync breaks
   **Prevention**: Unit test each component with known inputs before integration
   ```

3. Create ISSUE-MVP1.2-MOUTH-NOT-SYNCING.md with:
   - Detailed observations
   - Frame screenshots
   - Suspected failure point in pipeline

4. **DO NOT PROCEED** - Pipeline must be fixed before patent filing

5. Consider these debugging steps:
   - Add per-frame logging to test script
   - Save intermediate mouth ROI images
   - Verify viseme mapper output
   - Check if compositor is actually replacing mouth

## On Success

**If mouth sync is confirmed:**

1. Save all evidence:
   ```bash
   mkdir -p outputs/patent_evidence
   cp outputs/patent_demo_synced.mp4 outputs/patent_evidence/
   cp outputs/debug/frame_analysis/* outputs/patent_evidence/frames/
   cp outputs/debug/waveform.png outputs/patent_evidence/
   ```

2. Create verification report:
   ```bash
   # Save assessment as markdown
   vim outputs/patent_evidence/VISUAL_VERIFICATION_REPORT.md
   ```

3. Commit evidence:
   ```bash
   git add outputs/patent_evidence/
   git commit -m "MVP-1.2: Visual verification PASSED - Mouth sync confirmed

   - Reviewed: outputs/patent_demo_synced.mp4
   - Mouth movements aligned with speech
   - Frame analysis shows viseme variation
   - Suitable for patent filing
   - Evidence: outputs/patent_evidence/"
   
   git tag v-mvp1.2-visual-verified
   ```

4. **Proceed to:** TASK MVP-1.3 (Patent documentation)
```

---

### TASK MVP-1.3: Patent Evidence Documentation

**File:** `TASK-MVP1.3-PATENT-DOCS.md`

```yaml
---
task_id: "MVP-1.3"
name: "Generate Patent Application Evidence"
priority: "CRITICAL"
estimated_time: "2 hours"
dependencies: ["MVP-1.2"]
phase: "REVIEW"
---

## Objective

Create comprehensive documentation package for USPTO provisional patent application (PPA).

## Steps

### Step MVP-1.3.1: Generate Evidence Report

**Action:** Run automated evidence generator
```bash
python scripts/generate_patent_evidence.py
```

**Output:** `outputs/patent_evidence/PATENT_EVIDENCE_REPORT.md`

**Must include:**
- Test parameters (input text, duration, frame count)
- Phoneme timeline with timestamps
- RICo pipeline steps diagram
- Frame-by-frame processing log
- Performance metrics
- Visual evidence (screenshots, video)

### Step MVP-1.3.2: Create System Architecture Diagram

**Action:** Document RICo protocol architecture

**Create:** `outputs/patent_evidence/RICO_ARCHITECTURE.md`

**Include:**
```markdown
# RICo Protocol Architecture

## System Overview
[Block diagram showing: Input → TTS → Phonemes → MouthTracker → VisemeMapper → ROICompositor → Output]

## Component Descriptions

### 1. TTS Engine with Phoneme Extraction
- Converts text to speech audio
- Extracts phoneme timestamps
- Output: Audio file + phoneme timeline

### 2. Mouth ROI Tracker
- Uses MediaPipe Face Mesh
- Extracts mouth region from base video frames
- Handles occlusion and head rotation

### 3. Viseme Mapper
- Maps phonemes to visual mouth shapes (visemes)
- 15 viseme classes covering all English phonemes
- Temporal alignment with audio

### 4. ROI Compositor
- Composites target mouth shape onto base frame
- Per-frame processing at 30fps
- Seamless blending for natural appearance

### 5. Video Encoder
- Encodes processed frames to MP4
- Muxes with audio stream
- Output: Synchronized avatar video

## Innovation: High-Frequency Data Compression

RICo extends to Phase 3 real-time streaming:
- Base video reference (cached)
- Stream only mouth ROI deltas
- 95% bandwidth reduction vs full video
- <100ms latency

## Patent Claims

1. Method for phoneme-synchronized avatar animation
2. Per-frame mouth ROI compositing pipeline
3. High-frequency compression for avatar streaming
4. Emotion-based base video selection with dynamic overlay
```

### Step MVP-1.3.3: Code Annotation for Patent

**Action:** Add patent-focused comments to key files

**Files to annotate:**
- `tests/test_rico_mvp_proof.py`
- `src/mouth_tracker.py`
- `src/viseme_mapper.py`
- `src/roi_compositor.py`

**Comment style:**
```python
# PATENT CLAIM: Per-frame phoneme-to-viseme mapping
# This method maps each phoneme in the audio timeline to its corresponding
# visual representation (viseme) at frame-level granularity, enabling
# precise mouth synchronization.
def map_phoneme_to_viseme(phoneme: str, frame_time: float) -> Viseme:
    ...
```

### Step MVP-1.3.4: Create Evidence Package Index

**Action:** Create `outputs/patent_evidence/INDEX.md`

```markdown
# RICo Protocol - Patent Evidence Package

**Date:** 2025-11-06
**Inventor:** [Your name]
**Title:** Method and System for Real-Time Phoneme-Synchronized Avatar Animation

## Evidence Files

### 1. Demonstration Video
- **File:** `patent_demo_synced.mp4`
- **Description:** Complete RICo pipeline demonstration showing mouth-synced avatar
- **Duration:** 6.23 seconds
- **Test phrase:** "Hello, I'm Alice. This is a test of mouth synchronization."

### 2. Audio File
- **File:** `mvp_test.wav`
- **Description:** Generated TTS audio with phoneme timing

### 3. Phoneme Timeline
- **File:** `patent_demo_phonemes.json`
- **Description:** Complete phoneme-to-timestamp mapping

### 4. Visual Evidence
- **Directory:** `frames/`
- **Description:** Frame-by-frame screenshots showing mouth variation

### 5. Technical Documentation
- **File:** `PATENT_EVIDENCE_REPORT.md`
- **File:** `RICO_ARCHITECTURE.md`
- **File:** `VISUAL_VERIFICATION_REPORT.md`

### 6. Source Code
- **File:** `../tests/test_rico_mvp_proof.py`
- **File:** `../src/mouth_tracker.py`
- **File:** `../src/viseme_mapper.py`
- **File:** `../src/roi_compositor.py`

## Patent Claims Summary

1. **Method for real-time avatar mouth synchronization**
2. **System for phoneme-to-viseme mapping and compositing**
3. **High-frequency data compression for avatar streaming**
4. **Emotion-based video selection with dynamic facial overlay**

## USPTO Submission Checklist

- [ ] PPA application form (USPTO Form SB/16)
- [ ] Specification document
- [ ] Claims (at least 3 independent claims)
- [ ] Abstract
- [ ] Drawings/diagrams
- [ ] Evidence package (this directory)
- [ ] Filing fee payment

## Next Steps

1. Consult with patent attorney
2. Refine claims based on prior art search
3. Prepare formal specification document
4. File PPA with USPTO
5. Begin utility patent preparation (within 12 months)
```

## Validation Gate: GATE_MVP-1.3

**Assertions:**

- [ ] Patent evidence report generated
- [ ] Architecture diagram created
- [ ] Code annotated with patent-focused comments
- [ ] Evidence package index complete
- [ ] All files organized in `outputs/patent_evidence/`

**Criticality:** CRITICAL

**Evidence Package:**
- Complete `outputs/patent_evidence/` directory
- All documents review-ready for attorney

## On Success

```bash
# Create archive for attorney
cd outputs/patent_evidence
zip -r rico_patent_evidence_$(date +%Y%m%d).zip .
cd ../..

# Commit everything
git add outputs/patent_evidence/
git commit -m "MVP-1.3: Complete patent evidence package

- Patent evidence report
- Architecture documentation
- Visual verification
- Code annotations
- Ready for USPTO filing"

git tag v-mvp1.3-patent-ready

# Create release
git tag -a v1.0-rico-mvp -m "RICo MVP - Patent Ready
- Working mouth synchronization
- Complete evidence package
- Ready for PPA filing"
```

**Proceed to:** Attorney review and USPTO filing
```

---

## LIVING DOCUMENTS

### TROUBLESHOOTING.md Updates

Add these entries to existing TROUBLESHOOTING.md:

```markdown
## RICo Integration Test Fails to Generate Video

**Context**: MVP-1.1 integration test
**Symptom**: Test completes but no video file created
**Error Snippet**: N/A or ffmpeg encoding errors
**Probable Cause**: 
- ffmpeg not installed or not in PATH
- Video encoding codec missing
- Output directory permissions issue
**Quick Fix**: 
```bash
# Install ffmpeg
sudo apt install ffmpeg  # Linux
brew install ffmpeg      # Mac
```
**Permanent Fix**: Add ffmpeg check to test prerequisites
**Prevention**: Document ffmpeg as required dependency in README

---

## Mouth Not Syncing in Output Video

**Context**: MVP-1.2 visual verification
**Symptom**: Mouth static or not aligned with speech
**Probable Cause**:
- Phoneme timeline not applied per-frame
- ROI compositor using static mouth shape
- Frame processing loop bug
**Quick Fix**: Add debug logging to identify where sync breaks
**Permanent Fix**: 
- Unit test each pipeline stage
- Add per-frame verification
- Visual inspection of intermediate outputs
**Prevention**: 
- Test components individually before integration
- Require frame-by-frame logging in tests

---

## Phase 3 Real-Time Streaming Not Implemented

**Context**: Future development
**Symptom**: N/A - not built yet
**Note**: Phase 3 is documented for patent purposes but not required for MVP
**Implementation**: See docs/PHASE3_REALTIME_STREAMING.md
```

### REPLICATION-NOTES.md Updates

```markdown
## RICo MVP Development (2025-11-06)

**Objective:** Patent-ready proof-of-concept

**Environment:**
- Python 3.10 required
- MediaPipe, OpenCV, ffmpeg dependencies
- Test video files in static/video_clips/

**Process:**
1. MVP-1.1: Integration test framework
2. MVP-1.2: Visual verification (human)
3. MVP-1.3: Patent documentation

**Known Pitfalls:**
- ❌ Python 3.12+ breaks MediaPipe
- ❌ Missing ffmpeg prevents video encoding
- ❌ Test videos must exist before running tests
- ✅ Always visually verify output (don't trust logs alone)

**Replicable Setup Checklist:**
- [ ] Python 3.10 environment active
- [ ] All Phase 2A components working (`2A.2`, `2A.3`, `2A.4`)
- [ ] ffmpeg installed and in PATH
- [ ] Test video files present: `static/video_clips/speaking-neutral.mp4`
- [ ] Output directories exist: `outputs/audio/`, `outputs/ricovideos/`, `outputs/patent_evidence/`
```

---

## AGENT EXECUTION INSTRUCTIONS

**For coding agent to follow this policy:**

```yaml
agent_instructions:
  mode: "MVP_PATENT_FOCUSED"
  priority: "Speed to patent filing"
  
  task_sequence:
    - "MVP-1.1: Create integration test"
    - "MVP-1.2: HALT for human visual verification"
    - "MVP-1.3: Generate patent docs"
  
  mandatory_behaviors:
    - "Execute full test, capture ALL output"
    - "Save video file, verify it exists"
    - "HALT at MVP-1.2 for human review"
    - "Do not proceed without visual verification"
    - "Update living docs on any error"
  
  prohibited_behaviors:
    - "Claiming mouth sync works without video evidence"
    - "Skipping visual verification gate"
    - "Proceeding to MVP-1.3 without human approval"
  
  on_failure:
    - "Capture full error log"
    - "Update TROUBLESHOOTING.md"
    - "Create ISSUE-MVP1.X.md"
    - "HALT immediately"
```

---

## SUCCESS CRITERIA

**MVP is complete when:**

- ✅ Integration test generates video file
- ✅ Human verifies mouth sync in video
- ✅ Patent evidence package complete
- ✅ All documentation ready for attorney
- ✅ No blockers to USPTO PPA filing

**Timeline:** This week (2-3 days)

---

**This policy ensures rapid, reliable path to patent-ready RICo MVP while maintaining quality and evidence standards for USPTO filing.**
