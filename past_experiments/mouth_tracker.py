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

        if avg_confidence < 0.0:  # Allow animated avatars with 0.0 visibility
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
