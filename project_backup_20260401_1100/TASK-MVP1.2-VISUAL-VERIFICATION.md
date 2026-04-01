---
task_id: "MVP-1.2"
name: "Human Visual Verification of Mouth Sync"
priority: "CRITICAL"
estimated_time: "30 minutes"
dependencies: ["MVP-1.1"]
phase: "VALIDATE"
status: "in_progress"
---

## Objective

**HUMAN VERIFICATION REQUIRED** - Agent cannot complete this task.

Visually confirm that mouth movements in output video are synchronized with speech audio.

## Generated Files to Verify

**Demonstration Video:** `outputs/patent_demo_synced_with_audio.mp4`
- Size: 1.7MB
- Duration: ~3.5 seconds (video), ~3.6 seconds (audio)
- Test phrase: "Hello, I'm Alice. This is a test of mouth synchronization."
- **HAS AUDIO**: TTS synchronized with video mouth movements

**Supporting Files:**
- `outputs/audio/mvp_test.wav` - Generated TTS audio
- `outputs/patent_demo_phonemes.json` - Phoneme timing data

## Human Verification Procedure

### 1. Play Output Video

**Action:**
```bash
# Open video in player (WITH AUDIO)
vlc outputs/patent_demo_synced_with_audio.mp4
# or
open outputs/patent_demo_synced_with_audio.mp4  # Mac
xdg-open outputs/patent_demo_synced_with_audio.mp4  # Linux
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
ffmpeg -i outputs/patent_demo_synced_with_audio.mp4 -vf "select='between(n\,0\,60)'" -vsync 0 outputs/debug/frame_analysis/frame_%04d.png
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
**Video:** outputs/patent_demo_synced_with_audio.mp4

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
   - Frame processing loop bug
   **Quick Fix**: Add debug logging to identify where sync breaks
   **Permanent Fix**:
   - Unit test each pipeline stage with known inputs
   - Add per-frame verification
   - Visual inspection of intermediate outputs
   **Prevention**:
   - Test components individually before integration
   - Require frame-by-frame logging in tests

   **Evidence:**
   - Video: outputs/patent_demo_synced.mp4
   - Phonemes: outputs/patent_demo_phonemes.json
   - Frame analysis: outputs/debug/frame_analysis/
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
