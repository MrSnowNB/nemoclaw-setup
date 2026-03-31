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
        cv2.ellipse(mask, center, axes, 0, 0, 360, (255,), -1)

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

    def composite_mouth_with_viseme(self,
                                   base_frame: np.ndarray,
                                   mouth_roi: np.ndarray,
                                   mouth_position: Tuple[int, int],
                                   viseme: str,
                                   mouth_mask: Optional[np.ndarray] = None) -> np.ndarray:
        """
        Composite mouth ROI with viseme-specific modifications

        Args:
            base_frame: Base video frame (BGR)
            mouth_roi: Mouth region to composite (BGR)
            mouth_position: (x, y) top-left position on base frame
            viseme: Viseme symbol (e.g., 'AA', 'IH', 'OW')
            mouth_mask: Optional alpha mask for mouth ROI

        Returns:
            Composited frame with viseme-modified mouth
        """
        if base_frame is None or mouth_roi is None:
            logger.warning("Invalid input: base_frame or mouth_roi is None")
            return base_frame

        # Apply viseme-specific transformation to mouth ROI
        modified_mouth_roi = self._apply_viseme_transformation(mouth_roi, viseme)

        # Composite the modified mouth
        return self.composite_mouth_roi(
            base_frame=base_frame,
            mouth_roi=modified_mouth_roi,
            mouth_position=mouth_position,
            mouth_mask=mouth_mask
        )

    def _apply_viseme_transformation(self, mouth_roi: np.ndarray, viseme: str) -> np.ndarray:
        """
        Apply viseme-specific transformation to mouth ROI

        Args:
            mouth_roi: Original mouth ROI
            viseme: Viseme symbol

        Returns:
            Transformed mouth ROI
        """
        # Create a copy to modify
        transformed_roi = mouth_roi.copy()

        # Define viseme-specific transformations
        viseme_transforms = {
            # Wide open mouth vowels
            'AA': {'scale_x': 1.2, 'scale_y': 1.3, 'brightness': 1.1},  # father
            'AO': {'scale_x': 1.1, 'scale_y': 1.2, 'brightness': 1.0},  # lot

            # Rounded vowels
            'OW': {'scale_x': 0.9, 'scale_y': 1.1, 'brightness': 0.9},  # boat
            'UW': {'scale_x': 0.8, 'scale_y': 1.0, 'brightness': 0.8},  # boot

            # Narrow vowels
            'IH': {'scale_x': 0.7, 'scale_y': 0.8, 'brightness': 0.9},  # bit
            'IY': {'scale_x': 0.6, 'scale_y': 0.7, 'brightness': 1.0},  # beat

            # Mid vowels
            'EH': {'scale_x': 0.9, 'scale_y': 0.9, 'brightness': 1.0},  # bed
            'AH': {'scale_x': 1.0, 'scale_y': 1.0, 'brightness': 1.0},  # hut

            # Default for consonants and unknown
            'DEFAULT': {'scale_x': 0.8, 'scale_y': 0.6, 'brightness': 0.7}
        }

        # Get transformation parameters
        transform = viseme_transforms.get(viseme, viseme_transforms['DEFAULT'])

        scale_x = transform['scale_x']
        scale_y = transform['scale_y']
        brightness = transform['brightness']

        # Apply scaling transformation
        h, w = transformed_roi.shape[:2]
        new_w = int(w * scale_x)
        new_h = int(h * scale_y)

        # Resize the mouth ROI
        if new_w > 0 and new_h > 0:
            transformed_roi = cv2.resize(transformed_roi, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

            # Pad back to original size if needed
            if new_h < h or new_w < w:
                pad_top = (h - new_h) // 2
                pad_bottom = h - new_h - pad_top
                pad_left = (w - new_w) // 2
                pad_right = w - new_w - pad_left

                transformed_roi = cv2.copyMakeBorder(
                    transformed_roi,
                    pad_top, pad_bottom, pad_left, pad_right,
                    cv2.BORDER_CONSTANT, value=[0, 0, 0]
                )

        # Apply brightness modification
        if brightness != 1.0:
            transformed_roi = cv2.convertScaleAbs(transformed_roi, alpha=brightness, beta=0)

        return transformed_roi

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
