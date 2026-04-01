---
task_id: "2A.2"
name: "Create Standalone Mouth Tracker"
status: "RESOLVED"
date: "2025-11-06"
resolution_date: "2025-11-06"
---

# ISSUE-2A2: Mouth Tracker Test Failure - No Face Detection

## Problem Summary

MouthROITracker test fails with 0.0% face detection rate. MediaPipe Face Mesh cannot detect faces in the test video `data/video_clips/speaking-neutral.mp4`.

## Error Details

**Test Command:**
```bash
cd /home/mr-snow/Documents/Testing\ the\ Beast/Alice\ in\ Cyberland && source venv-phase2/bin/activate && PYTHONPATH=/home/mr-snow/Documents/Testing\ the\ Beast/Alice\ in\ Cyberland python tests/test_mouth_tracker_standalone.py
```

**Videos Tested:**
1. `data/video_clips/speaking-neutral.mp4` - 0.0% detection rate
2. `data/video_clips/concerned-deep-breath.mp4` - 0.0% detection rate

**Test Results (both videos):**
```
Starting isolated mouth tracker test...
INFO:src.mouth_tracker:MouthROITracker initialized with 40 landmarks
Processing frames...
WARNING:src.mouth_tracker:Mouth occluded (confidence: 0.00)
[... repeated for all 30 frames ...]
✅ Processed 30 frames
✅ Detection rate: 0.0%
✅ Avg confidence: 0.00
❌ TEST FAILED: Detection rate too low: 0.0%
```

## Root Cause Analysis

- **MouthROITracker code**: Working correctly (initializes with 40 landmarks)
- **MediaPipe Face Mesh**: Functional (no crashes or import errors)
- **Test video**: `data/video_clips/speaking-neutral.mp4` does not contain detectable faces
- **Detection threshold**: min_detection_confidence=0.5 may be too high for this video

## Impact Assessment

- **Phase 1**: Unaffected (still working)
- **Phase 2**: Cannot proceed without working face detection
- **Timeline**: Blocked until suitable test video is identified or detection parameters are tuned

## Proposed Solutions

### Option 1: Use Different Test Video (Recommended)
- Find/create a video with clear, well-lit faces
- Verify the video contains detectable faces before testing
- Use videos from the existing collection or create new test footage

### Option 2: Adjust Detection Parameters
- Lower `min_detection_confidence` from 0.5 to 0.3 or 0.2
- Test with multiple parameter combinations
- May reduce accuracy but could work for testing

### Option 3: Skip Standalone Testing
- Proceed to integration testing (TASK 2B.1) with fallback to Phase 1
- Accept that mouth tracking may not work initially
- Focus on ensuring Phase 1 remains functional

## Immediate Actions Taken

1. ✅ **Captured failure logs**: `outputs/logs/failure_2a2_mouth_tracker_test.log`
2. ✅ **Updated TROUBLESHOOTING.md** with "Mouth Tracker Test Failure - No Face Detection" entry
3. ✅ **Updated REPLICATION-NOTES.md** with recurring error about face detection
4. ✅ **Created this ISSUE-2A2.md** file

## Next Steps Required

**HALTED** - Awaiting human input for resolution approach.

## Evidence Files

- `outputs/logs/failure_2a2_mouth_tracker_test.log` - Complete test output
- `src/mouth_tracker.py` - Working MouthROITracker implementation
- `tests/test_mouth_tracker_standalone.py` - Test that exposes the issue
- `data/video_clips/speaking-neutral.mp4` - Test video that fails detection

## Prevention Measures

- Add video validation step to TASK 2A.2
- Require manual verification that test videos contain detectable faces
- Consider adding face detection validation before running mouth tracker tests
- Document working video characteristics (lighting, angle, quality)
