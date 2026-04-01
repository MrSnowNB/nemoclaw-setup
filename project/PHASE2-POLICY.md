---
title: "Phase 2 Mouth Sync - Policy-Enforced Execution Plan"
version: "2.0.0"
date: "2025-11-06"
status: "ACTIVE"
baseline: "rico-phase1-complete branch (WORKING)"
agent_mode: "STRICT_POLICY_ENFORCEMENT"
objective: "Add mouth synchronization WITHOUT breaking Phase 1"
---

# Phase 2: RICo Mouth Synchronization - Policy Document

## ⚠️ CRITICAL CONSTRAINT

**Phase 1 MUST remain working at ALL times.**

Current working state: `rico-phase1-complete` branch
- User types message
- Clicks video area
- Video plays for duration of audio
- Returns to idle loop

**If Phase 1 breaks at ANY point → IMMEDIATE ROLLBACK**

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

### Failure Handling Protocol

**Mandatory sequence on ANY failure:**

1. **Capture logs** → `outputs/logs/failure_YYYYMMDD_HHMMSS.log`
2. **Update TROUBLESHOOTING.md** with new entry
3. **Update REPLICATION-NOTES.md** with environment context
4. **Create ISSUE-{task_id}.md** with failure details
5. **HALT** and wait for human input

**NO RETRIES** without human approval.

---

## STRATEGIC APPROACH

### Why Phase 2 Failed Before

1. ❌ Big bang integration (all components at once)
2. ❌ Simulated testing (claimed success without runtime validation)
3. ❌ Broke Phase 1 code (replaced instead of augmented)
4. ❌ Missing dependencies (never verified imports)
5. ❌ No fallback testing (claimed fallback worked but never tested)

### New Phase 2 Architecture

```
User Message
    ↓
Generate AI Response + TTS Audio
    ↓
Select Emotion-Based Video Clip
    ↓
┌─────────────────────────────────────────┐
│ PHASE 2 (OPTIONAL ENHANCEMENT)          │
│                                         │
│ IF ENABLE_RICO_PHASE2=true:            │
│   Try mouth sync preprocessing         │
│   IF success: Use synced video         │
│   IF failure: Log error, continue      │
└─────────────────────────────────────────┘
    ↓
PHASE 1 (ALWAYS RUNS - FALLBACK)
    ↓
Duration Match Video to Audio
    ↓
Send to Frontend
    ↓
Click-to-Play Video + Audio
```

**Key Innovation:** Phase 2 is preprocessing step that NEVER prevents Phase 1 from working.

---

## TASK SEQUENCE

### PHASE 2A: ISOLATED COMPONENT DEVELOPMENT

**Objective:** Build ALL Phase 2 components without touching chat_server.py

---

### TASK 2A.1: Dependency Installation and Validation

**File:** `TASK-2A1-DEPENDENCIES.md`

```yaml
---
task_id: "2A.1"
name: "Install and Validate Phase 2 Dependencies"
priority: "CRITICAL"
dependencies: []
phase: "BUILD"
---

## Objective

Install MediaPipe, OpenCV, and related packages.
Verify ALL imports work BEFORE writing any code.

## Steps

### Step 2A.1.1: Install Dependencies

**Action:**
```bash
pip install mediapipe==0.10.8 \
            opencv-python==4.8.1.78 \
            opencv-contrib-python==4.8.1.78 \
            numpy==1.24.3
```

**Validation:**
```bash
pip list | grep -E "(mediapipe|opencv|numpy)"
```

**Expected Output:**
```
mediapipe                 0.10.8
numpy                     1.24.3
opencv-contrib-python     4.8.1.78
opencv-python             4.8.1.78
```

**Evidence Required:**
- Screenshot of pip install output
- Screenshot of pip list showing exact versions

### Step 2A.1.2: Verify Imports

**Action:**
```bash
python -c "import mediapipe; print('MediaPipe:', mediapipe.__version__)"
python -c "import cv2; print('OpenCV:', cv2.__version__)"
python -c "import numpy; print('NumPy:', numpy.__version__)"
```

**Expected Output:**
```
MediaPipe: 0.10.8
OpenCV: 4.8.1.78
NumPy: 1.24.3
```

**Evidence Required:**
- Screenshot of successful imports with versions

### Step 2A.1.3: Update Requirements

**Action:**
```bash
pip freeze | grep -E "(mediapipe|opencv|numpy)" > requirements-phase2.txt
echo "# Phase 2 Dependencies - Installed $(date)" >> requirements-phase2.txt
cat requirements-phase2.txt
```

**Validation:**
- File `requirements-phase2.txt` exists
- Contains pinned versions

**Evidence Required:**
- Contents of requirements-phase2.txt

## Validation Gate: GATE_2A.1

**Assertions:**

- [ ] All packages installed (pip list shows versions)
- [ ] All imports successful (no ImportError)
- [ ] requirements-phase2.txt created with pinned versions

**Criticality:** CRITICAL

**Evidence Package:**
- `outputs/logs/gate_2a1_dependencies.log` (pip outputs)
- Screenshot: pip list showing packages
- Screenshot: import statements succeeding
- File: requirements-phase2.txt

## On Failure

1. Capture error:
   ```bash
   pip install mediapipe 2>&1 | tee outputs/logs/failure_2a1_pip_install.log
   ```

2. Update TROUBLESHOOTING.md:
   ```markdown
   ## MediaPipe Installation Failure
   
   **Context**: TASK 2A.1 - Installing Phase 2 dependencies
   **Symptom**: pip install mediapipe fails
   **Error Snippet**: [paste actual error]
   **Probable Cause**: [binary compatibility / Python version / etc]
   **Quick Fix**: Try: pip install --no-binary mediapipe mediapipe
   **Permanent Fix**: Document exact working environment
   **Prevention**: Test on clean venv before production
   ```

3. Update REPLICATION-NOTES.md:
   ```markdown
   ## Dependency Installation Issues
   
   Date: 2025-11-06
   Environment: [OS, Python version]
   Issue: MediaPipe failed to install
   Resolution: [what worked]
   
   **Known Pitfalls:**
   - MediaPipe requires Python 3.8-3.11 (not 3.12+)
   - On M1/M2 Mac: May need rosetta or x86_64 build
   ```

4. Create ISSUE-2A1.md

5. **HALT** - Await human input

## On Success

**Actions:**
```bash
# Commit dependencies
git add requirements-phase2.txt
git commit -m "Phase 2A.1: Dependencies installed and validated

- MediaPipe 0.10.8
- OpenCV 4.8.1.78
- NumPy 1.24.3
- All imports verified working
- Evidence: outputs/logs/gate_2a1_dependencies.log"

# Tag
git tag v2a.1-dependencies-verified

# Update task status
echo "status: complete" >> TASK-2A1-DEPENDENCIES.md
```

**Proceed to:** TASK 2A.2
```

---

### TASK 2A.2: Mouth Tracker (Isolated)

**File:** `TASK-2A2-MOUTH-TRACKER.md`

```yaml
---
task_id: "2A.2"
name: "Create Standalone Mouth Tracker"
priority: "HIGH"
dependencies: ["2A.1"]
phase: "BUILD"
---

## Objective

Create `src/mouth_tracker.py` and test in COMPLETE ISOLATION.
Do NOT integrate with chat_server.py.

## Steps

### Step 2A.2.1: Create MouthROITracker Class

**Action:** Create file `src/mouth_tracker.py`

**Content:**
```python
"""
Mouth ROI Tracker for RICo Phase 2

Tracks mouth region using MediaPipe Face Mesh.
Handles head rotation, occlusion, and variable lighting.
"""

import mediapipe as mp
import cv2
import numpy as np
from typing import Optional, Tuple, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MouthROITracker:
    """Tracks mouth region with occlusion detection"""
    
    # MediaPipe face mesh landmark indices for mouth
    UPPER_LIP_OUTER = [61, 185, 40, 39, 37, 0, 267, 269, 270, 409, 291]
    LOWER_LIP_OUTER = [146, 91, 181, 84, 17, 314, 405, 321, 375, 291]
    UPPER_LIP_INNER = [78, 191, 80, 81, 82, 13, 312, 311, 310, 415, 308]
    LOWER_LIP_INNER = [95, 88, 178, 87, 14, 317, 402, 318, 324, 308]
    
    def __init__(self, 
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5):
        """Initialize MediaPipe Face Mesh"""
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
        # Combine all mouth landmarks
        self.ALL_MOUTH_LANDMARKS = list(set(
            self.UPPER_LIP_OUTER + self.LOWER_LIP_OUTER +
            self.UPPER_LIP_INNER + self.LOWER_LIP_INNER
        ))
        
        logger.info(f"MouthROITracker initialized with {len(self.ALL_MOUTH_LANDMARKS)} landmarks")
    
    def extract_mouth_roi(self, frame: np.ndarray) -> Tuple[Optional[Dict], float]:
        """
        Extract mouth region from frame
        
        Args:
            frame: BGR image (OpenCV format)
        
        Returns:
            (roi_data, confidence) where roi_data contains:
                - 'roi': Cropped mouth region
                - 'polygon': Mouth outline polygon
                - 'bbox': Bounding box (x, y, w, h)
            confidence: 0.0-1.0 (average visibility)
        """
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = self.face_mesh.process(rgb)
        
        if not results.multi_face_landmarks:
            logger.debug("No face detected")
            return None, 0.0
        
        landmarks = results.multi_face_landmarks[0]
        h, w = frame.shape[:2]
        
        # Extract mouth points and confidences
        mouth_points = []
        visibilities = []
        
        for idx in self.ALL_MOUTH_LANDMARKS:
            lm = landmarks.landmark[idx]
            x_px = int(lm.x * w)
            y_px = int(lm.y * h)
            mouth_points.append((x_px, y_px))
            visibilities.append(getattr(lm, 'visibility', 1.0))
        
        avg_confidence = np.mean(visibilities)
        
        if avg_confidence < 0.3:
            logger.warning(f"Mouth occluded (confidence: {avg_confidence:.2f})")
            return None, avg_confidence
        
        mouth_polygon = np.array(mouth_points, dtype=np.int32)
        x, y, w_bbox, h_bbox = cv2.boundingRect(mouth_polygon)
        
        # Add padding
        padding = 0.15
        x_pad = int(w_bbox * padding)
        y_pad = int(h_bbox * padding)
        
        x = max(0, x - x_pad)
        y = max(0, y - y_pad)
        w_bbox = min(w - x, w_bbox + 2*x_pad)
        h_bbox = min(h - y, h_bbox + 2*y_pad)
        
        roi = frame[y:y+h_bbox, x:x+w_bbox].copy()
        
        roi_data = {
            'roi': roi,
            'polygon': mouth_polygon,
            'bbox': (x, y, w_bbox, h_bbox),
            'frame_size': (w, h)
        }
        
        logger.debug(f"Mouth ROI extracted: {w_bbox}x{h_bbox}px, conf: {avg_confidence:.2f}")
        
        return roi_data, avg_confidence
    
    def release(self):
        """Cleanup resources"""
        self.face_mesh.close()
```

**Validation:**
```bash
python -c "from src.mouth_tracker import MouthROITracker; print('✅ Import successful')"
```

**Evidence Required:**
- File created: `src/mouth_tracker.py`
- Import succeeds without error

### Step 2A.2.2: Create Standalone Test

**Action:** Create file `tests/test_mouth_tracker_standalone.py`

**Content:**
```python
"""
Standalone test for MouthROITracker

Tests mouth tracking on easiest clip (speaking-nuetral.mp4)
WITHOUT any integration with chat_server.py
"""

import cv2
from src.mouth_tracker import MouthROITracker
import os


def test_mouth_tracking_isolated():
    """Test mouth tracking in complete isolation"""
    
    print("Starting isolated mouth tracker test...")
    
    tracker = MouthROITracker()
    
    # Use easiest clip first
    video_path = "static/video_clips/speaking-nuetral.mp4"
    
    if not os.path.exists(video_path):
        print(f"❌ Video not found: {video_path}")
        print("Available clips:")
        for f in os.listdir("static/video_clips"):
            print(f"  - {f}")
        raise FileNotFoundError(video_path)
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        raise RuntimeError(f"Failed to open video: {video_path}")
    
    frames_processed = 0
    frames_with_mouth = 0
    confidences = []
    
    # Process first 30 frames
    print("Processing frames...")
    for i in range(30):
        ret, frame = cap.read()
        if not ret:
            print(f"End of video at frame {i}")
            break
        
        roi_data, confidence = tracker.extract_mouth_roi(frame)
        frames_processed += 1
        
        if roi_data is not None:
            frames_with_mouth += 1
            confidences.append(confidence)
            
            # Verify ROI is valid
            assert roi_data['roi'].size > 0, "Empty ROI"
            assert len(roi_data['polygon']) > 10, "Too few landmarks"
    
    cap.release()
    tracker.release()
    
    # Calculate metrics
    detection_rate = frames_with_mouth / frames_processed if frames_processed > 0 else 0
    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
    
    print(f"\n✅ Processed {frames_processed} frames")
    print(f"✅ Detection rate: {detection_rate*100:.1f}%")
    print(f"✅ Avg confidence: {avg_confidence:.2f}")
    
    # Assertions
    assert frames_processed > 0, "No frames processed"
    assert detection_rate > 0.5, f"Detection rate too low: {detection_rate*100:.1f}%"
    assert avg_confidence > 0.5, f"Confidence too low: {avg_confidence:.2f}"
    
    print("\n✅ TEST PASSED - Mouth tracking working")
    return True


if __name__ == "__main__":
    try:
        test_mouth_tracking_isolated()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
```

**Execute:**
```bash
python tests/test_mouth_tracker_standalone.py
```

**Expected Output:**
```
Starting isolated mouth tracker test...
Processing frames...
✅ Processed 30 frames
✅ Detection rate: >50.0%
✅ Avg confidence: >0.50
✅ TEST PASSED - Mouth tracking working
```

**Evidence Required:**
- Screenshot of test output showing PASSED
- Actual detection rate and confidence values

## Validation Gate: GATE_2A.2

**Assertions:**

- [ ] src/mouth_tracker.py created
- [ ] MouthROITracker imports successfully
- [ ] Standalone test PASSES (detection rate >50%, confidence >0.5)
- [ ] No integration with chat_server.py

**Criticality:** CRITICAL

**Evidence Package:**
- File: `src/mouth_tracker.py`
- File: `tests/test_mouth_tracker_standalone.py`
- Screenshot: Test passing with actual metrics
- Log: `outputs/logs/gate_2a2_mouth_tracker_test.log`

## On Failure

1. Capture full error:
   ```bash
   python tests/test_mouth_tracker_standalone.py 2>&1 | tee outputs/logs/failure_2a2_test.log
   ```

2. Update TROUBLESHOOTING.md:
   ```markdown
   ## Mouth Tracker Test Failure
   
   **Context**: TASK 2A.2 - Testing MouthROITracker standalone
   **Symptom**: Test fails with [low detection rate / import error / etc]
   **Error Snippet**: [paste actual error]
   **Probable Cause**: [MediaPipe not detecting faces / video file issue / etc]
   **Quick Fix**: Try different video clip or adjust confidence thresholds
   **Permanent Fix**: Tune MediaPipe parameters for video characteristics
   **Prevention**: Test on multiple clips before claiming success
   ```

3. Update REPLICATION-NOTES.md with environment details

4. Create ISSUE-2A2.md

5. **HALT** - Do NOT proceed to integration

## On Success

**Actions:**
```bash
# Commit isolated component
git add src/mouth_tracker.py tests/test_mouth_tracker_standalone.py
git commit -m "Phase 2A.2: MouthROITracker standalone component

- Tracks mouth ROI using MediaPipe Face Mesh
- Handles occlusion detection
- Tested in isolation (no chat_server integration)
- Detection rate: [actual %]
- Confidence: [actual value]
- Evidence: outputs/logs/gate_2a2_mouth_tracker_test.log"

git tag v2a.2-mouth-tracker-isolated
```

**Proceed to:** TASK 2A.3 (Next isolated component)
```

---

### TASK 2A.3-2A.5: Additional Isolated Components

Following same pattern, create tasks for:

**TASK 2A.3:** `src/viseme_mapper.py` + standalone test
**TASK 2A.4:** `src/roi_compositor.py` + standalone test  
**TASK 2A.5:** `src/rico_pipeline.py` + standalone test (NO chat_server integration)

Each task:
- Creates ONE file
- Tests in COMPLETE isolation
- GATE validation with evidence
- Commits only after passing

---

### PHASE 2B: SAFE INTEGRATION

**Objective:** Add Phase 2 to chat_server.py WITHOUT breaking Phase 1

---

### TASK 2B.1: Feature Flag Implementation

**File:** `TASK-2B1-FEATURE-FLAG.md`

```yaml
---
task_id: "2B.1"
name: "Add Phase 2 Feature Flag (Default: Disabled)"
priority: "CRITICAL"
dependencies: ["2A.5"]
phase: "BUILD"
---

## Objective

Add environment variable to enable/disable Phase 2.
**Default: DISABLED (Phase 1 only)** for safety.

## Steps

### Step 2B.1.1: Add Feature Flag to chat_server.py

**Action:** Modify `src/chat_server.py`

**Add at top of file (after imports):**
```python
import os

# ============================================================================
# PHASE 2 FEATURE FLAG
# ============================================================================
# Set ENABLE_RICO_PHASE2=true to enable mouth synchronization
# Default: false (Phase 1 only for safety)

ENABLE_RICO_PHASE2 = os.getenv("ENABLE_RICO_PHASE2", "false").lower() == "true"

if ENABLE_RICO_PHASE2:
    try:
        from src.rico_pipeline import RicoPipeline
        rico_pipeline = RicoPipeline()
        logger.info("✅ Phase 2 RICo mouth sync ENABLED")
    except ImportError as e:
        logger.error(f"❌ Phase 2 import failed: {e}")
        logger.info("Falling back to Phase 1 only")
        ENABLE_RICO_PHASE2 = False
        rico_pipeline = None
    except Exception as e:
        logger.error(f"❌ Phase 2 initialization failed: {e}")
        logger.info("Falling back to Phase 1 only")
        ENABLE_RICO_PHASE2 = False
        rico_pipeline = None
else:
    logger.info("Phase 2 DISABLED - Using Phase 1 duration matching only")
    rico_pipeline = None
```

**Validation:**
```bash
# Test Phase 1 mode (default)
python -c "from src.chat_server import ENABLE_RICO_PHASE2; assert not ENABLE_RICO_PHASE2"
echo "✅ Default is Phase 1 only"

# Test Phase 2 mode
ENABLE_RICO_PHASE2=true python -c "from src.chat_server import ENABLE_RICO_PHASE2; print(f'Phase 2 enabled: {ENABLE_RICO_PHASE2}')"
```

### Step 2B.1.2: Test Both Modes

**Test 1: Phase 1 Mode (Default)**
```bash
# Start server without Phase 2
pkill -f uvicorn || true
python -m uvicorn src.chat_server:app --host 0.0.0.0 --port 8080 > outputs/logs/test_phase1_mode.log 2>&1 &
sleep 5

# Test
curl -f http://localhost:8080/
echo "✅ Server started in Phase 1 mode"

# Send test message in browser
# Verify: Works exactly like rico-phase1-complete branch

pkill -f uvicorn
```

**Test 2: Phase 2 Mode (Opt-in)**
```bash
# Start server WITH Phase 2
ENABLE_RICO_PHASE2=true python -m uvicorn src.chat_server:app --host 0.0.0.0 --port 8080 > outputs/logs/test_phase2_mode.log 2>&1 &
sleep 5

# Check logs for Phase 2 initialization
grep -i "phase 2" outputs/logs/test_phase2_mode.log

# Test
curl -f http://localhost:8080/
echo "✅ Server started with Phase 2 enabled"

pkill -f uvicorn
```

**Evidence Required:**
- Screenshot: Phase 1 mode server logs
- Screenshot: Phase 2 mode server logs
- Screenshot: Browser test in Phase 1 mode working
- Log files: test_phase1_mode.log, test_phase2_mode.log

## Validation Gate: GATE_2B.1

**Assertions:**

- [ ] Feature flag added to chat_server.py
- [ ] Default is Phase 1 only (ENABLE_RICO_PHASE2=false)
- [ ] Phase 1 mode: Server starts and works exactly like before
- [ ] Phase 2 mode: Server starts without crashing (even if RICo not used yet)
- [ ] Import errors handled gracefully (falls back to Phase 1)

**Criticality:** CRITICAL - Phase 1 MUST NOT break

**Evidence Package:**
- Modified: `src/chat_server.py` (git diff)
- Logs: test_phase1_mode.log, test_phase2_mode.log
- Screenshot: Browser test in Phase 1 mode
- Screenshot: Server logs showing Phase 2 status

## On Failure

**If Phase 1 mode breaks:**

1. **IMMEDIATE ROLLBACK:**
   ```bash
   git checkout src/chat_server.py
   ```

2. Capture error:
   ```bash
   cp outputs/logs/test_phase1_mode.log outputs/logs/failure_2b1_phase1_broken.log
   ```

3. Update TROUBLESHOOTING.md:
   ```markdown
   ## Feature Flag Broke Phase 1
   
   **Context**: TASK 2B.1 - Adding Phase 2 feature flag
   **Symptom**: Phase 1 mode no longer works after adding feature flag
   **Error Snippet**: [paste error from logs]
   **Probable Cause**: Import error / syntax error / logic error in flag code
   **Quick Fix**: git checkout src/chat_server.py
   **Permanent Fix**: Fix syntax, test imports before adding to server
   **Prevention**: NEVER modify chat_server.py without testing immediately
   ```

4. Create ISSUE-2B1.md

5. **HALT** - Phase 1 integrity is CRITICAL

**If Phase 2 mode crashes:**

This is acceptable IF Phase 1 still works.
- Document issue
- Fix RicoPipeline import/init
- Re-test

## On Success

**Actions:**
```bash
# Test Phase 1 one more time
python -m uvicorn src.chat_server:app --port 8080 &
sleep 3
curl http://localhost:8080/ && echo "✅ Phase 1 confirmed working"
pkill -f uvicorn

# Commit
git add src/chat_server.py
git commit -m "Phase 2B.1: Feature flag added (default: Phase 1 only)

- ENABLE_RICO_PHASE2 environment variable
- Default: false (Phase 1 only)
- Graceful fallback on import errors
- Phase 1 mode: Verified working
- Phase 2 mode: Server starts without crash
- Evidence: outputs/logs/test_phase1_mode.log"

git tag v2b.1-feature-flag-safe
```

**Proceed to:** TASK 2B.2 (Add RICo processing)
```

---

### TASK 2B.2: RICo Integration with Fallback

**File:** `TASK-2B2-RICO-INTEGRATION.md`

```yaml
---
task_id: "2B.2"
name: "Integrate RICo with Explicit Fallback"
priority: "CRITICAL"
dependencies: ["2B.1"]
phase: "BUILD"
---

## Objective

Add Phase 2 mouth sync processing to WebSocket handler.
GUARANTEE fallback to Phase 1 on ANY Phase 2 failure.

## Steps

### Step 2B.2.1: Add RICo Processing (Optional Path)

**Action:** Modify `src/chat_server.py` WebSocket handler

**Find function:**
```python
async def process_user_message(message: str, websocket: WebSocket):
```

**Add AFTER emotion detection and TTS generation:**
```python
# ... existing Phase 1 code ...
ai_response = get_llm_response(message)
emotion_state = detect_emotion(ai_response)
audio_path = generate_tts_audio(ai_response)
base_video_clip = get_emotion_video_path(emotion_state)

# ============================================================================
# PHASE 2: OPTIONAL MOUTH SYNC PREPROCESSING
# ============================================================================
video_path = None  # Will be set by Phase 2 or Phase 1

if ENABLE_RICO_PHASE2 and rico_pipeline:
    try:
        logger.info(f"🎭 Attempting Phase 2 mouth sync on {base_video_clip}")
        
        # Try to add mouth synchronization
        synced_video_path = rico_pipeline.process_video_with_audio(
            video_path=base_video_clip,
            audio_path=audio_path,
            text=ai_response
        )
        
        # Verify file was created
        if os.path.exists(synced_video_path):
            logger.info(f"✅ Phase 2 success: {synced_video_path}")
            video_path = synced_video_path
        else:
            raise FileNotFoundError(f"RICo output not found: {synced_video_path}")
        
    except Exception as e:
        # Phase 2 failed - fall back to Phase 1
        logger.warning(f"⚠️  Phase 2 failed: {e}")
        logger.info("Falling back to Phase 1 duration matching")
        video_path = None  # Signal fallback needed

# ============================================================================
# PHASE 1: DURATION MATCHING (ALWAYS RUNS AS FALLBACK)
# ============================================================================
if video_path is None:
    # Phase 2 disabled, failed, or skipped
    logger.info("Using Phase 1 duration matching")
    video_path = video_duration_matcher.create_duration_matched_clip(
        base_video_clip, 
        audio_path
    )

# ... rest of existing code to send response ...
```

**Validation:**
```python
# Verify both code paths exist
grep -A 20 "PHASE 2:" src/chat_server.py
grep -A 10 "PHASE 1:" src/chat_server.py
```

### Step 2B.2.2: Test Fallback Path

**Test 1: Force Phase 2 to Fail**

Temporarily modify `src/rico_pipeline.py`:
```python
def process_video_with_audio(self, ...):
    raise RuntimeError("FORCED FAILURE FOR TESTING")
```

Start server:
```bash
ENABLE_RICO_PHASE2=true python -m uvicorn src.chat_server:app --port 8080
```

Send message in browser.

**Expected:**
- See warning in logs: "⚠️ Phase 2 failed"
- See info in logs: "Falling back to Phase 1"
- Video STILL plays (using Phase 1)
- No crash

Restore rico_pipeline.py after test.

**Test 2: Phase 1 Only Mode**

```bash
# Default mode (Phase 2 disabled)
python -m uvicorn src.chat_server:app --port 8080
```

Send message.

**Expected:**
- No Phase 2 attempts
- Phase 1 works exactly like before
- Video plays normally

**Test 3: Phase 2 Success (If Components Working)**

```bash
ENABLE_RICO_PHASE2=true python -m uvicorn src.chat_server:app --port 8080
```

Send message using easiest clip (neutral emotion).

**Expected (if RICo working):**
- Phase 2 processes video
- Mouth-synced video plays
- No fallback needed

**Evidence Required:**
- Screenshot: Fallback test (Phase 2 fails, Phase 1 works)
- Screenshot: Phase 1 only mode working
- Screenshot: Phase 2 success (if applicable)
- Logs showing both code paths

## Validation Gate: GATE_2B.2

**Assertions:**

- [ ] RICo integration added to chat_server.py
- [ ] Phase 1 fallback ALWAYS runs if Phase 2 fails
- [ ] Phase 1 only mode: Works identically to rico-phase1-complete
- [ ] Fallback tested: Force Phase 2 error → Phase 1 handles it
- [ ] No crash on ANY Phase 2 failure

**Criticality:** CRITICAL

**Evidence Package:**
- Modified: `src/chat_server.py` (git diff showing try/except)
- Logs: Fallback test showing "⚠️ Phase 2 failed" → "Phase 1 duration matching"
- Screenshot: Video playing after forced Phase 2 failure
- Screenshot: Phase 1 mode unchanged

## On Failure

**If Phase 1 breaks:**

1. **IMMEDIATE ROLLBACK:**
   ```bash
   git checkout src/chat_server.py
   ```

2. Update TROUBLESHOOTING.md

3. Create ISSUE-2B2.md

4. **HALT**

**If Fallback doesn't work:**

This is CRITICAL failure.
- Phase 2 fails AND Phase 1 doesn't activate
- ROLLBACK immediately
- Fix fallback logic
- Re-test extensively

## On Success

**Actions:**
```bash
# Final verification test
python -m uvicorn src.chat_server:app --port 8080 &
sleep 3

# Test in browser
# Send 3 messages, verify all work

pkill -f uvicorn

# Commit
git add src/chat_server.py
git commit -m "Phase 2B.2: RICo integration with guaranteed fallback

- Phase 2 mouth sync added as optional preprocessing
- Explicit try/except with Phase 1 fallback
- Tested: Phase 2 failure → Phase 1 works
- Tested: Phase 1 only mode unchanged
- Tested: Phase 2 success (if components ready)
- Evidence: outputs/logs/test_fallback_path.log"

git tag v2b.2-rico-integrated-safe
```

**Proceed to:** Final validation
```

---

## FINAL VALIDATION

### Manual Integration Test (Human Required)

**File:** `TASK-FINAL-VALIDATION.md`

```yaml
---
task_id: "FINAL"
name: "End-to-End Validation"
priority: "CRITICAL"
dependencies: ["2B.2"]
phase: "VALIDATE"
---

## Objective

Human verification that Phase 2 works AND Phase 1 is still intact.

## Test Procedure

### Test 1: Phase 1 Only (Baseline)

1. Start server:
   ```bash
   python -m uvicorn src.chat_server:app --host 0.0.0.0 --port 8080
   ```

2. Browser: http://localhost:8080

3. Send 3 messages with different emotions

4. Verify:
   - ✅ Video plays after clicking
   - ✅ Audio plays
   - ✅ Duration matching works
   - ✅ Returns to idle
   - ✅ NO errors in console

### Test 2: Phase 2 Enabled

1. Start server:
   ```bash
   ENABLE_RICO_PHASE2=true python -m uvicorn src.chat_server:app --host 0.0.0.0 --port 8080
   ```

2. Send neutral-emotion message

3. Verify:
   - ✅ Video plays (mouth-synced if Phase 2 works, or Phase 1 fallback)
   - ✅ No crash
   - ✅ Logs show Phase 2 attempt

### Test 3: Stress Test

Send 5 consecutive messages rapidly.

Verify:
- ✅ No crashes
- ✅ All responses work
- ✅ Server stable

## Validation Gate: GATE_FINAL

**Assertions:**

- [ ] Phase 1 mode: Identical to rico-phase1-complete branch
- [ ] Phase 2 mode: Server doesn't crash
- [ ] Multiple messages: System stable
- [ ] Logs: Clear Phase 2 status messages

**Evidence Required:**
- Video recording of working system
- Screenshots of console (no errors)
- Server logs showing Phase 2 attempts

## On Success

Project complete! Phase 2 integrated safely.

```bash
git tag v2.0-phase2-complete
```

## On Failure

If Phase 1 broken:
- ROLLBACK to rico-phase1-complete
- Review all changes
- Identify what broke Phase 1
- Fix and re-test
```

---

## LIVING DOCUMENTS

### TROUBLESHOOTING.md (Template)

```markdown
# Troubleshooting Guide - RICo Phase 2

Last Updated: [auto-generated]

---

## Dependency Installation Issues

**Context**: Installing MediaPipe, OpenCV for Phase 2
**Symptom**: pip install fails
**Error Snippet**: [actual error]
**Probable Cause**: Python version incompatibility / binary build issues
**Quick Fix**: pip install --no-binary mediapipe mediapipe
**Permanent Fix**: Use Python 3.10 (not 3.12+), document working environment
**Prevention**: Test in clean venv before production install

---

## Mouth Tracker Low Detection Rate

**Context**: test_mouth_tracker_standalone.py fails
**Symptom**: Detection rate <50%
**Error Snippet**: AssertionError: Detection rate too low: 35.0%
**Probable Cause**: Video quality / MediaPipe confidence threshold too high
**Quick Fix**: Lower min_detection_confidence to 0.3
**Permanent Fix**: Tune thresholds per clip, handle occlusion gracefully
**Prevention**: Test on multiple clips before claiming success

---

## Phase 2 Integration Breaks Phase 1

**Context**: After adding RICo to chat_server.py
**Symptom**: Phase 1 mode no longer works
**Error Snippet**: [actual error from server logs]
**Probable Cause**: Import error / syntax error / removed Phase 1 code
**Quick Fix**: git checkout src/chat_server.py (rollback)
**Permanent Fix**: NEVER remove Phase 1 code, only add Phase 2 as optional
**Prevention**: Test Phase 1 mode IMMEDIATELY after any chat_server.py change

---

## Fallback Path Not Working

**Context**: Phase 2 fails but Phase 1 doesn't activate
**Symptom**: Server crashes or returns error to user
**Error Snippet**: [actual exception]
**Probable Cause**: Missing try/except, video_path variable not set
**Quick Fix**: Ensure video_path = None before Phase 2, then check if None for fallback
**Permanent Fix**: Explicit if video_path is None: run Phase 1
**Prevention**: Test fallback explicitly (force Phase 2 to fail, verify Phase 1 runs)
```

### REPLICATION-NOTES.md (Template)

```markdown
# Replication Notes - RICo Phase 2

Last Updated: [auto-generated]

---

## Environment

- **Machine**: Z8 Workstation
- **OS**: [Linux/Windows/Mac]
- **Python**: 3.10.x
- **Working Branch**: rico-phase1-complete (baseline)

---

## Known Pitfalls to Avoid Next Run

1. ❌ **DO NOT** install MediaPipe on Python 3.12+ (incompatible)
2. ❌ **DO NOT** remove Phase 1 code when adding Phase 2
3. ❌ **DO NOT** commit changes to chat_server.py without testing Phase 1 mode first
4. ✅ **DO** test each component in isolation before integration
5. ✅ **DO** verify fallback path explicitly (force errors)
6. ✅ **DO** keep ENABLE_RICO_PHASE2 default as false

---

## Replicable Setup Checklist

- [ ] Git branch: rico-phase1-complete (verified working)
- [ ] Python 3.10 in clean venv
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

None documented yet.
```

---

## AGENT CONSTRAINTS

### Prohibited Behaviors

1. ❌ **NO** claiming success without runtime evidence
2. ❌ **NO** simulated testing (must execute actual commands)
3. ❌ **NO** modifying chat_server.py without testing Phase 1 immediately
4. ❌ **NO** removing Phase 1 code
5. ❌ **NO** committing broken code
6. ❌ **NO** retries without human approval after failure

### Mandatory Behaviors

1. ✅ Screenshot or log output for EVERY assertion
2. ✅ Test fallback path explicitly
3. ✅ Update living docs BEFORE halting on failure
4. ✅ HALT immediately if uncertain
5. ✅ Rollback if Phase 1 breaks

---

## SUCCESS CRITERIA

**Minimum Viable:**
- ✅ Phase 1 mode: Works identically to rico-phase1-complete
- ✅ Phase 2 mode: Server starts without crash
- ✅ Fallback: Tested and working

**Full Success:**
- ✅ Phase 2 mouth sync works on 1+ clip
- ✅ All 7 clips work (either Phase 2 or Phase 1 fallback)
- ✅ System stable over 10+ messages

**CRITICAL:**
- ✅ Phase 1 NEVER breaks at any point

---

**This policy document ensures Phase 2 development follows strict evidence-based validation with guaranteed Phase 1 preservation.**
