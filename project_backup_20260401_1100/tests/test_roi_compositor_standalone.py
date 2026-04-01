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
    # Look for blended pixels (not pure black [0,0,0] or white [255,255,255])
    blended_pixels = np.sum(np.logical_and(
        np.any(mouth_region != [0, 0, 0], axis=2),
        np.any(mouth_region != [255, 255, 255], axis=2)
    ))
    assert blended_pixels > 0, "Alpha blending not working"

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
