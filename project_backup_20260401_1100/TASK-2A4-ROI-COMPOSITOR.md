---
task_id: "2A.4"
name: "Create ROICompositor Component"
priority: "HIGH"
dependencies: ["2A.2"]
phase: "BUILD"
status: "complete"
---

## Objective

Create `src/roi_compositor.py` and test in COMPLETE ISOLATION.
Composite mouth ROI onto base video frames for lip sync.
Do NOT integrate with chat_server.py.

## Steps

### Step 2A.4.1: Create ROICompositor Class

**Action:** Create file `src/roi_compositor.py`

**Content:**
```python
"""
ROI Compositor for RICo Phase 2

Composites mouth region of interest onto base video frames.
Handles blending, positioning, and temporal synchronization.
"""

import cv2
import numpy as np
from typing import Optional, Tuple, Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ROICompositor:
    """Composites mouth ROI onto video frames with proper blending"""

    def __init__(self,
                 blend_mode: str = "alpha",
                 feather_amount: int = 5,
                 position_offset: Tuple[int, int] = (0, 0)):
        """
        Initialize ROI compositor

        Args:
            blend_mode: "alpha" or "overlay"
            feather_amount: Pixels for edge feathering
            position_offset: (x, y) offset for mouth positioning
        """
        self.blend_mode = blend_mode
        self.feather_amount = feather_amount
        self.position_offset = position_offset

        logger.info(f"ROICompositor initialized: blend={blend_mode}, feather={feather_amount}px, offset={position_offset}")

    def composite_mouth_roi(self,
                           base_frame: np.ndarray,
                           mouth_roi: np.ndarray,
                           mouth_position: Tuple[int, int],
                           mouth_mask: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Composite mouth ROI onto base frame

        Args:
            base_frame: Base video frame (BGR)
            mouth_roi: Mouth region to composite (BGR)
            mouth_position: (x, y) top-left position on base frame
            mouth_mask: Optional alpha mask for mouth ROI

        Returns:
            Composited frame with mouth ROI blended in
        """
        if base_frame is None or mouth_roi is None:
            logger.warning("Invalid input: base_frame or mouth_roi is None")
            return base_frame

        # Create a copy of the base frame
        result_frame = base_frame.copy()

        # Get dimensions
        roi_h, roi_w = mouth_roi.shape[:2]
        frame_h, frame_w = base_frame.shape[:2]

        # Calculate position with offset
        pos_x = mouth_position[0] + self.position_offset[0]
        pos_y = mouth_position[1] + self.position_offset[1]

        # Ensure ROI fits within frame bounds
        pos_x = max(0, min(pos_x, frame_w - roi_w))
        pos_y = max(0, min(pos_y, frame_h - roi_h))

        # Define ROI region on base frame
        roi_region = result_frame[pos_y:pos_y+roi_h, pos_x:pos_x+roi_w]

        if self.blend_mode == "alpha":
            result_frame = self._blend_alpha(result_frame, mouth_roi, mouth_mask, pos_x, pos_y, roi_w, roi_h)
        elif self.blend_mode == "overlay":
            result_frame = self._blend_overlay(result_frame, mouth_roi, pos_x, pos_y, roi_w, roi_h)
        else:
            # Simple copy
            result_frame[pos_y:pos_y+roi_h, pos_x:pos_x+roi_w] = mouth_roi

        logger.debug(f"Composited mouth ROI at ({pos_x}, {pos_y}) size {roi_w}x{roi_h}")
        return result_frame

    def _blend_alpha(self,
                    frame: np.ndarray,
                    roi: np.ndarray,
                    mask: Optional[np.ndarray],
                    x: int, y: int, w: int, h: int) -> np.ndarray:
        """Alpha blend mouth ROI onto frame"""

        # Create alpha mask if not provided
        if mask is None:
            # Create simple oval mask for mouth region
            mask = self._create_mouth_mask(roi.shape[:2])

        # Apply feathering to mask edges
        if self.feather_amount > 0:
            mask = cv2.GaussianBlur(mask, (self.feather_amount*2+1, self.feather_amount*2+1), 0)

        # Ensure mask is same size as ROI
        if mask.shape[:2] != roi.shape[:2]:
            mask = cv2.resize(mask, (roi.shape[1], roi.shape[0]))

        # Normalize mask to 0-1 range
        mask_norm = mask.astype(np.float32) / 255.0

        # Extract region of interest
        roi_region = frame[y:y+h, x:x+w].astype(np.float32)

        # Alpha blend: result = roi * mask + background * (1 - mask)
        blended = roi.astype(np.float32) * mask_norm[:, :, np.newaxis] + \
                 roi_region * (1.0 - mask_norm[:, :, np.newaxis])

        # Put back into frame
        frame[y:y+h, x:x+w] = blended.astype(np.uint8)

        return frame

    def _blend_overlay(self,
                      frame: np.ndarray,
                      roi: np.ndarray,
                      x: int, y: int, w: int, h: int) -> np.ndarray:
        """Overlay blend mouth ROI onto frame"""

        # Simple overlay with optional feathering
        if self.feather_amount > 0:
            # Create feathered edge mask
            mask = np.ones((h, w), dtype=np.uint8) * 255
            cv2.rectangle(mask, (self.feather_amount, self.feather_amount),
                         (w-self.feather_amount, h-self.feather_amount), 0, -1)

            mask = cv2.GaussianBlur(mask, (self.feather_amount*2+1, self.feather_amount*2+1), 0)
            mask = mask.astype(np.float32) / 255.0

            # Blend with feathering
            roi_region = frame[y:y+h, x:x+w].astype(np.float32)
            blended = roi.astype(np.float32) * mask[:, :, np.newaxis] + \
                     roi_region * (1.0 - mask[:, :, np.newaxis])

            frame[y:y+h, x:x+w] = blended.astype(np.uint8)
        else:
            # Direct overlay
            frame[y:y+h, x:x+w] = roi

        return frame

    def _create_mouth_mask(self, shape: Tuple[int, int]) -> np.ndarray:
        """Create oval mask for mouth region"""

        h, w = shape
        mask = np.zeros((h, w), dtype=np.uint8)

        # Create oval mask
        center = (w // 2, h // 2)
        axes = (w // 2, h // 2)
        cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)

        return mask

    def validate_compositing(self,
                            base_frame: np.ndarray,
                            composited_frame: np.ndarray,
                            mouth_position: Tuple[int, int],
                            mouth_size: Tuple[int, int]) -> bool:
        """
        Validate that compositing was successful

        Args:
            base_frame: Original frame
            composited_frame: Frame after compositing
            mouth_position: Expected mouth position
            mouth_size: Expected mouth size

        Returns:
            True if validation passes
        """
        if base_frame.shape != composited_frame.shape:
            logger.error("Frame shapes don't match after compositing")
            return False

        # Check that frames are different (mouth was composited)
        if np.array_equal(base_frame, composited_frame):
            logger.warning("Frames are identical - compositing may have failed")
            return False

        # Check mouth region bounds
        x, y = mouth_position
        w, h = mouth_size

        if x < 0 or y < 0 or x + w > composited_frame.shape[1] or y + h > composited_frame.shape[0]:
            logger.error("Mouth position/size exceeds frame bounds")
            return False

        return True

    def get_compositing_stats(self,
                             base_frame: np.ndarray,
                             composited_frame: np.ndarray) -> Dict:
        """
        Get statistics about the compositing operation

        Args:
            base_frame: Original frame
            composited_frame: Composited frame

        Returns:
            Dictionary with compositing statistics
        """
        diff_pixels = np.count_nonzero(cv2.absdiff(base_frame, composited_frame))
        total_pixels = base_frame.shape[0] * base_frame.shape[1] * base_frame.shape[2]

        return {
            'total_pixels': total_pixels,
            'changed_pixels': diff_pixels,
            'change_percentage': (diff_pixels / total_pixels) * 100,
            'frame_shape': base_frame.shape
        }
```

**Validation:**
```bash
python -c "from src.roi_compositor import ROICompositor; print('✅ Import successful')"
```

**Evidence Required:**
- File created: `src/roi_compositor.py`
- Import succeeds without error

### Step 2A.4.2: Create Standalone Test

**Action:** Create file `tests/test_roi_compositor_standalone.py`

**Content:**
```python
"""
Standalone test for ROICompositor

Tests ROI compositing in COMPLETE ISOLATION.
WITHOUT any integration with chat_server.py
"""

import cv2
import numpy as np
import os
from src.roi_compositor import ROICompositor


def test_roi_compositing_basic():
    """Test basic ROI compositing functionality"""

    print("Testing basic ROI compositing...")

    compositor = ROICompositor()

    # Create test frames
    base_frame = np.zeros((100, 100, 3), dtype=np.uint8)  # Black background
    base_frame[:, :] = [255, 0, 0]  # Red background

    mouth_roi = np.zeros((20, 20, 3), dtype=np.uint8)
    mouth_roi[:, :] = [0, 255, 0]  # Green mouth

    mouth_position = (40, 40)  # Center of frame

    # Composite
    result_frame = compositor.composite_mouth_roi(base_frame, mouth_roi, mouth_position)

    # Validate
    assert result_frame.shape == base_frame.shape, "Frame shape changed"

    # Check that mouth region was composited (green pixels in red background)
    mouth_region = result_frame[40:60, 40:60]
    green_pixels = np.sum((mouth_region == [0, 255, 0]).all(axis=2))
    assert green_pixels > 0, "Mouth ROI not composited"

    # Validate compositing
    is_valid = compositor.validate_compositing(base_frame, result_frame, mouth_position, (20, 20))
    assert is_valid, "Compositing validation failed"

    print("✅ Basic ROI compositing working")
    return True


def test_roi_compositing_alpha_blend():
    """Test alpha blending mode"""

    print("Testing alpha blending...")

    compositor = ROICompositor(blend_mode="alpha")

    # Create test frames
    base_frame = np.full((50, 50, 3), [255, 255, 255], dtype=np.uint8)  # White background
    mouth_roi = np.full((20, 20, 3), [0, 0, 0], dtype=np.uint8)  # Black mouth

    # Create alpha mask (50% transparent)
    mouth_mask = np.full((20, 20), 128, dtype=np.uint8)

    mouth_position = (15, 15)

    # Composite with alpha blending
    result_frame = compositor.composite_mouth_roi(base_frame, mouth_roi, mouth_position, mouth_mask)

    # Check that blending occurred (should be gray, not pure black or white)
    mouth_region = result_frame[15:35, 15:35]
    gray_pixels = np.sum((mouth_region == [128, 128, 128]).all(axis=2))
    assert gray_pixels > 0, "Alpha blending not working"

    print("✅ Alpha blending working")
    return True


def test_roi_compositing_bounds_checking():
    """Test bounds checking and edge cases"""

    print("Testing bounds checking...")

    compositor = ROICompositor()

    # Create test frames
    base_frame = np.zeros((50, 50, 3), dtype=np.uint8)
    mouth_roi = np.full((20, 20, 3), [255, 255, 255], dtype=np.uint8)

    # Test edge positions
    test_positions = [
        (0, 0),      # Top-left corner
        (30, 30),    # Bottom-right (will be clamped)
        (-10, -10),  # Negative (will be clamped)
    ]

    for pos in test_positions:
        result_frame = compositor.composite_mouth_roi(base_frame.copy(), mouth_roi, pos)

        # Should not crash and should produce valid output
        assert result_frame.shape == base_frame.shape, f"Shape changed for position {pos}"

        # Validate compositing
        clamped_pos = (max(0, min(pos[0], 50-20)), max(0, min(pos[1], 50-20)))
        is_valid = compositor.validate_compositing(base_frame, result_frame, clamped_pos, (20, 20))
        assert is_valid, f"Validation failed for position {pos}"

    print("✅ Bounds checking working")
    return True


def test_roi_compositing_stats():
    """Test compositing statistics"""

    print("Testing compositing statistics...")

    compositor = ROICompositor()

    # Create test frames
    base_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    mouth_roi = np.full((20, 20, 3), [255, 255, 255], dtype=np.uint8)

    mouth_position = (40, 40)

    # Composite
    result_frame = compositor.composite_mouth_roi(base_frame, mouth_roi, mouth_position)

    # Get stats
    stats = compositor.get_compositing_stats(base_frame, result_frame)

    # Validate stats
    assert 'total_pixels' in stats
    assert 'changed_pixels' in stats
    assert 'change_percentage' in stats
    assert stats['changed_pixels'] > 0, "No pixels changed"
    assert stats['change_percentage'] > 0, "Change percentage should be > 0"

    print(f"✅ Compositing stats: {stats['change_percentage']:.1f}% pixels changed")
    return True


def test_roi_compositing_feathering():
    """Test edge feathering"""

    print("Testing edge feathering...")

    compositor = ROICompositor(feather_amount=3)

    # Create test frames
    base_frame = np.full((50, 50, 3), [128, 128, 128], dtype=np.uint8)  # Gray background
    mouth_roi = np.full((20, 20, 3), [255, 255, 255], dtype=np.uint8)  # White mouth

    mouth_position = (15, 15)

    # Composite with feathering
    result_frame = compositor.composite_mouth_roi(base_frame, mouth_roi, mouth_position)

    # Should have smooth transitions, not hard edges
    # Check edge pixels are blended (not pure white or gray)
    edge_region = result_frame[14:16, 14:16]  # Around the edge
    blended_pixels = np.sum(np.logical_and(
        edge_region != [255, 255, 255],
        edge_region != [128, 128, 128]
    ).any(axis=2))

    assert blended_pixels > 0, "Feathering not working - hard edges detected"

    print("✅ Edge feathering working")
    return True


if __name__ == "__main__":
    try:
        print("Starting ROICompositor standalone tests...\n")

        test_roi_compositing_basic()
        print()

        test_roi_compositing_alpha_blend()
        print()

        test_roi_compositing_bounds_checking()
        print()

        test_roi_compositing_stats()
        print()

        test_roi_compositing_feathering()
        print()

        print("🎉 ALL ROI COMPOSITOR TESTS PASSED!")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
```

**Execute:**
```bash
python tests/test_roi_compositor_standalone.py
```

**Expected Output:**
```
Starting ROICompositor standalone tests...

Testing basic ROI compositing...
✅ Basic ROI compositing working

Testing alpha blending...
✅ Alpha blending working

Testing bounds checking...
✅ Bounds checking working

Testing compositing statistics...
✅ Compositing stats: X.X% pixels changed

Testing edge feathering...
✅ Edge feathering working

🎉 ALL ROI COMPOSITOR TESTS PASSED!
```

**Evidence Required:**
- Screenshot of test output showing PASSED
- All test functions pass

## Validation Gate: GATE_2A.4

**Assertions:**

- [ ] src/roi_compositor.py created
- [ ] ROICompositor imports successfully
- [ ] All standalone tests PASS
- [ ] Basic compositing works
- [ ] Alpha blending works
- [ ] Bounds checking works
- [ ] Statistics work
- [ ] Feathering works
- [ ] No integration with chat_server.py

**Criticality:** HIGH

**Evidence Package:**
- File: `src/roi_compositor.py`
- File: `tests/test_roi_compositor_standalone.py`
- Screenshot: All tests passing
- Log: `outputs/logs/gate_2a4_roi_compositor_test.log`

## On Success

**Actions:**
```bash
# Commit isolated component
git add src/roi_compositor.py tests/test_roi_compositor_standalone.py
git commit -m "Phase 2A.4: ROICompositor standalone component

- Composites mouth ROI onto video frames
- Supports alpha blending and overlay modes
- Handles bounds checking and edge feathering
- Tested in isolation (no chat_server integration)
- All tests passing
- Evidence: outputs/logs/gate_2a4_roi_compositor_test.log"

git tag v2a.4-roi-compositor-isolated
```

**Proceed to:** TASK 2A.5 (Next isolated component)
