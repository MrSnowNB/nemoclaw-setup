"""
RICo Pipeline for Phase 2

Orchestrates mouth tracking, viseme mapping, and ROI compositing
for complete lip synchronization pipeline.
"""

import cv2
import numpy as np
from typing import Optional, Dict, List, Tuple, Any
import logging
import os

from src.mouth_tracker import MouthROITracker
from src.viseme_mapper import VisemeMapper
from src.roi_compositor import ROICompositor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class RicoPipeline:
    """Complete lip sync pipeline orchestrating all components"""

    def __init__(self,
                 mouth_tracker_config: Optional[Dict] = None,
                 viseme_mapper_config: Optional[Dict] = None,
                 compositor_config: Optional[Dict] = None):
        """
        Initialize RICo pipeline with all components

        Args:
            mouth_tracker_config: Config for MouthROITracker
            viseme_mapper_config: Config for VisemeMapper (unused for now)
            compositor_config: Config for ROICompositor
        """
        # Initialize components
        self.mouth_tracker = MouthROITracker(
            min_detection_confidence=mouth_tracker_config.get('min_detection_confidence', 0.5) if mouth_tracker_config else 0.5,
            min_tracking_confidence=mouth_tracker_config.get('min_tracking_confidence', 0.5) if mouth_tracker_config else 0.5
        )

        self.viseme_mapper = VisemeMapper()

        self.compositor = ROICompositor(
            blend_mode=compositor_config.get('blend_mode', 'alpha') if compositor_config else 'alpha',
            feather_amount=compositor_config.get('feather_amount', 5) if compositor_config else 5,
            position_offset=compositor_config.get('position_offset', (0, 0)) if compositor_config else (0, 0)
        )

        # Pipeline state
        self.is_initialized = True
        self.frame_count = 0
        self.success_count = 0

        logger.info("RICo Pipeline initialized with all components")

    def process_video_with_audio(self,
                                video_path: str,
                                audio_path: str,
                                text: str,
                                output_path: Optional[str] = None) -> str:
        """
        Process video with audio for lip sync

        Args:
            video_path: Path to input video
            audio_path: Path to audio file
            text: Text content for viseme generation
            output_path: Optional output path

        Returns:
            Path to processed video
        """
        if not self.is_initialized:
            raise RuntimeError("RICo Pipeline not properly initialized")

        logger.info(f"Starting RICo processing: video={video_path}, audio={audio_path}")

        # Generate output path if not provided
        if output_path is None:
            base_name = os.path.splitext(os.path.basename(video_path))[0]
            output_path = f"outputs/video/rico_{base_name}_{int(cv2.getTickCount())}.mp4"

        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Step 1: Extract visemes from text
        logger.info("Step 1: Generating visemes from text")
        visemes = self.viseme_mapper.text_to_visemes(text)

        if not visemes:
            logger.warning("No visemes generated from text, falling back to basic processing")
            # For now, just copy the original video
            self._copy_video(video_path, output_path)
            return output_path

        logger.info(f"Generated {len(visemes)} visemes")

        # Step 2: Process video frames
        logger.info("Step 2: Processing video frames")
        processed_frames = self._process_video_frames(video_path, visemes)

        if not processed_frames:
            logger.warning("No frames processed successfully, falling back to original")
            self._copy_video(video_path, output_path)
            return output_path

        # Step 3: Create output video
        logger.info("Step 3: Creating output video")
        self._create_output_video(video_path, processed_frames, output_path)

        success_rate = (self.success_count / self.frame_count) * 100 if self.frame_count > 0 else 0
        logger.info(".1f")

        return output_path

    def _process_video_frames(self, video_path: str, visemes: List[Dict]) -> List[np.ndarray]:
        """
        Process individual video frames with mouth tracking and compositing

        Args:
            video_path: Input video path
            visemes: Viseme sequence

        Returns:
            List of processed frames
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.error(f"Failed to open video: {video_path}")
            return []

        processed_frames = []
        frame_idx = 0

        # Get video properties
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        logger.info(f"Processing {total_frames} frames at {fps} FPS")

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            self.frame_count += 1

            # Get current viseme for this frame
            current_viseme = self._get_viseme_for_frame(frame_idx, fps, visemes)

            # Process frame
            processed_frame = self._process_single_frame(frame, current_viseme)
            processed_frames.append(processed_frame)

            frame_idx += 1

            # Progress logging
            if frame_idx % 100 == 0:
                logger.info(f"Processed {frame_idx}/{total_frames} frames")

        cap.release()
        logger.info(f"Frame processing complete: {len(processed_frames)} frames processed")
        return processed_frames

    def _get_viseme_for_frame(self, frame_idx: int, fps: float, visemes: List[Dict]) -> Optional[Dict]:
        """
        Get the appropriate viseme for the current frame

        Args:
            frame_idx: Current frame index
            fps: Frames per second
            visemes: Viseme sequence

        Returns:
            Current viseme dict or None
        """
        if not visemes:
            return None

        # Convert frame index to time
        current_time = frame_idx / fps

        # Find the viseme that covers this time
        for viseme in visemes:
            start_time = viseme.get('start', 0)
            end_time = viseme.get('end', 0)

            if start_time <= current_time < end_time:
                return viseme

        # If no viseme covers this time, return the last one
        return visemes[-1] if visemes else None

    def _process_single_frame(self, frame: np.ndarray, viseme: Optional[Dict]) -> np.ndarray:
        """
        Process a single frame with mouth tracking and compositing

        Args:
            frame: Input frame
            viseme: Current viseme (can be None)

        Returns:
            Processed frame
        """
        try:
            # Track mouth in the frame
            roi_data, confidence = self.mouth_tracker.extract_mouth_roi(frame)

            if roi_data is None:
                # No mouth detected, return original frame
                logger.debug("No mouth detected in frame")
                return frame

            # Extract mouth ROI and position
            mouth_roi = roi_data['roi']
            mouth_position = (roi_data['bbox'][0], roi_data['bbox'][1])

            # Get viseme symbol for this frame
            viseme_symbol = viseme.get('viseme', 'AH') if viseme else 'AH'

            # Composite mouth with viseme-specific transformation
            result_frame = self.compositor.composite_mouth_with_viseme(
                base_frame=frame,
                mouth_roi=mouth_roi,
                mouth_position=mouth_position,
                viseme=viseme_symbol
            )

            self.success_count += 1
            return result_frame

        except Exception as e:
            logger.warning(f"Frame processing failed: {e}")
            return frame

    def _create_output_video(self, input_video_path: str, frames: List[np.ndarray], output_path: str):
        """
        Create output video from processed frames

        Args:
            input_video_path: Original video path (for properties)
            frames: Processed frames
            output_path: Output video path
        """
        if not frames:
            logger.error("No frames to write")
            return

        # Get input video properties
        cap = cv2.VideoCapture(input_video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        # Create video writer
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        if not out.isOpened():
            logger.error(f"Failed to create output video: {output_path}")
            return

        # Write frames
        for frame in frames:
            out.write(frame)

        out.release()
        logger.info(f"Output video created: {output_path}")

    def _copy_video(self, input_path: str, output_path: str):
        """
        Copy video when processing fails

        Args:
            input_path: Source video
            output_path: Destination video
        """
        try:
            # Simple copy for fallback
            import shutil
            shutil.copy2(input_path, output_path)
            logger.info(f"Video copied as fallback: {output_path}")
        except Exception as e:
            logger.error(f"Video copy failed: {e}")

    def get_pipeline_stats(self) -> Dict[str, Any]:
        """
        Get pipeline processing statistics

        Returns:
            Dictionary with pipeline stats
        """
        success_rate = (self.success_count / self.frame_count) * 100 if self.frame_count > 0 else 0

        return {
            'total_frames': self.frame_count,
            'successful_frames': self.success_count,
            'success_rate': success_rate,
            'components_initialized': self.is_initialized
        }

    def reset_stats(self):
        """Reset pipeline statistics"""
        self.frame_count = 0
        self.success_count = 0
        logger.info("Pipeline statistics reset")
