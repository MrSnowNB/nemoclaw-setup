---
task_id: "2A.2-Debug"
name: "Enhanced Testing & Logging for Mouth Tracker"
status: "complete"
priority: "critical"
dependencies: ["2A.2"]
---

## Objective

Add thorough step-by-step diagnostics and persistent logging to `tests/test_mouth_tracker_standalone.py` so every debug output, log, and error is saved and can be committed/backed up to GitHub.

## Steps

### 1. Save First Decoded Frame
- On the first successful read, save as `outputs/debug/first_frame.jpg` using `cv2.imwrite`.
- Print/log the absolute path and `frame.shape` for inspection.

### 2. Log Frame Properties for All Frames
- For each frame processed, log the index, shape, dtype, and basic statistics (min/max, mean pixel value) to `outputs/logs/mouth_tracker_debug.log`.

### 3. Exception Handling
- Wrap the MediaPipe processing code in a try/except.
- If any exception occurs (including hidden MediaPipe errors), log the full exception and traceback to `outputs/logs/mediapipe_exceptions.log` (append mode).

### 4. No Face Detected: Save Frames
- If a frame results in no detected landmarks/faces, save it as an image in `outputs/debug/no_face_detected/frame_{idx:03d}.jpg`.
- Ensure the debug subdirectory exists (use `os.makedirs()` as needed).

### 5. Logging All Metrics
- At test completion, append summary stats (frames processed, # with/without detection, avg confidence, etc.) to `outputs/logs/mouth_tracker_debug.log`.

### 6. Commit All Diagnostics to GitHub
- Add all changed and new files:
  - Script: `tests/test_mouth_tracker_standalone.py`
  - Logs: `outputs/logs/mediapipe_exceptions.log`, `outputs/logs/mouth_tracker_debug.log`
  - Images: Any in `outputs/debug/`
- Commit and push with the message:
  ```
  "[Policy] Enhanced mouth tracker debug: frame dumps, exception logs, full metrics for 0% face detection diagnostics"
  ```
- Do not skip or remove logs/images, even if test run is unsuccessful.

### 7. Notification on Persistent Error
- If no faces are detected after re-running the test with enhanced logging, agent must halt per policy and notify the human, referencing new logs for further analysis.

---

**All outputs and artifacts must be in version control and backed up to GitHub with the next commit for easy review by a human or automated agent.**
