---
task_id: "2A.1"
name: "Install and Validate Phase 2 Dependencies"
priority: "CRITICAL"
dependencies: []
phase: "BUILD"
status: "complete"
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

- [x] All packages installed (pip list shows versions)
- [x] All imports successful (no ImportError)
- [x] requirements-phase2.txt created with pinned versions

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
