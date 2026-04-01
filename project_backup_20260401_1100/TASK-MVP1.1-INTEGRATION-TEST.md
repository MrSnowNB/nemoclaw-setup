---
task_id: "MVP-1.1"
name: "Create RICo Integration Test Framework"
priority: "CRITICAL"
estimated_time: "2 hours"
dependencies: ["2A.2", "2A.3", "2A.4"]
phase: "BUILD"
status: "complete"
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
