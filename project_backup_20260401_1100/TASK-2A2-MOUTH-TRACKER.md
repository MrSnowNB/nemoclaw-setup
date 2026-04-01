---
task_id: "2A.2"
name: "Create Standalone Mouth Tracker"
priority: "HIGH"
dependencies: ["2A.1"]
phase: "BUILD"
status: "complete"
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
    video_path = "static/video_clips/speaking-neutral.mp4"

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
