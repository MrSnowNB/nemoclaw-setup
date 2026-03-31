"""
Video Duration Matcher for RICo Phase 1

Extends 6-second emotional video clips to match TTS audio duration
via FFmpeg-based controlled looping for precise synchronization.
"""

import subprocess
import json
import os
import uuid
from pathlib import Path
import yaml
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VideoDurationMatcher:
    """Matches video clip duration to audio duration via FFmpeg looping"""

    def __init__(self, config_path='/home/mr-snow/alice_cyberland/project/data/emotion_config.yaml'):
        """Initialize with emotion configuration"""
        self.config = self._load_config(config_path)
        self.clips_dir = Path(self.config['clips_directory'])
        self.clip_durations = self._measure_all_clip_durations()

        # Create output directory
        self.output_dir = Path("outputs/video")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"📹 VideoDurationMatcher initialized with {len(self.clip_durations)} clips")

    def _load_config(self, config_path):
        """Load emotion-to-clip mapping config"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _measure_all_clip_durations(self):
        """Measure duration of all video clips using FFprobe"""
        durations = {}

        for clip_file in self.clips_dir.glob("*.mp4"):
            try:
                duration = self._get_video_duration(clip_file)
                durations[clip_file.name] = duration
                logger.info(".2f")
            except Exception as e:
                logger.error(f"  ✗ Failed to measure {clip_file.name}: {e}")

        return durations

    def _get_video_duration(self, video_path):
        """Get duration of a video file using FFprobe"""
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json",
            str(video_path)
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(result.stdout)
        return float(data['format']['duration'])

    def create_duration_matched_clip(self, emotion_state, target_duration):
        """
        Create a video clip that matches target audio duration

        Args:
            emotion_state: Emotion key from emotion_config.yaml
            target_duration: Duration in seconds to match

        Returns:
            Path to generated video file
        """
        # Get clip info from config
        emotion_data = self.config['emotion_mapping'].get(
            emotion_state,
            {'clip': self.config['default_clip'], 'should_loop': False}
        )

        clip_name = emotion_data['clip']
        clip_path = self.clips_dir / clip_name

        if not clip_path.exists():
            raise FileNotFoundError(f"Video clip not found: {clip_path}")

        # Get original clip duration
        original_duration = self.clip_durations.get(clip_name)
        if not original_duration:
            original_duration = self._get_video_duration(clip_path)

        # Generate output filename
        output_filename = f"{emotion_state}_{uuid.uuid4().hex[:8]}.mp4"
        output_path = self.output_dir / output_filename

        # Calculate how many loops needed (simplified - may be fractional)
        if target_duration <= original_duration:
            # Audio is shorter than clip - just trim the clip
            loop_count = 0
        else:
            # Audio is longer - need to loop (will get fractional loops)
            loop_count = target_duration / original_duration

        logger.info(f"🎬 Creating {emotion_state} clip: {original_duration:.1f}s → {target_duration:.1f}s (loops: {loop_count:.2f})")

        # Build FFmpeg command
        if loop_count <= 1.0:
            # Audio is shorter than clip - just trim
            cmd = [
                "ffmpeg", "-y",
                "-i", str(clip_path),
                "-t", str(target_duration),
                "-c", "copy",
                "-avoid_negative_ts", "make_zero",
                str(output_path)
            ]
        else:
            # Audio is longer - stream copy with controlled loop count
            cmd = [
                "ffmpeg", "-y",
                "-stream_loop", str(int(loop_count)),  # Only integer loops
                "-i", str(clip_path),
                "-t", str(target_duration),  # Trim exactly to target duration
                "-c", "copy",  # No re-encoding for speed
                "-avoid_negative_ts", "make_zero",
                str(output_path)
            ]

        # Execute FFmpeg
        try:
            subprocess.run(
                cmd,
                check=True,
                capture_output=True,
                text=True
            )

            # Verify output
            actual_duration = self._get_video_duration(output_path)
            drift = abs(actual_duration - target_duration)

            if drift > 0.1:  # Allow 100ms tolerance
                logger.warning(f"⚠️  Duration drift: {drift:.3f}s (target: {target_duration:.1f}s, actual: {actual_duration:.1f}s)")
            else:
                logger.info(f"✅ Duration match: {actual_duration:.1f}s (drift: {drift*1000:.0f}ms)")

            return output_path

        except subprocess.CalledProcessError as e:
            logger.error(f"❌ FFmpeg error: {e.stderr}")
            raise

    def get_clip_for_emotion(self, emotion_state):
        """Get the clip filename for a given emotion state"""
        emotion_data = self.config['emotion_mapping'].get(
            emotion_state,
            {'clip': self.config['default_clip']}
        )
        return emotion_data['clip']


# Test function
if __name__ == "__main__":
    matcher = VideoDurationMatcher()

    # Test creating a 12-second happy clip (double 6-second clip)
    test_output = matcher.create_duration_matched_clip('friendly_speaking', 12.0)
    print(f"✅ Test output: {test_output}")

    # Test duration measurement
    if test_output and os.path.exists(test_output):
        measured = matcher._get_video_duration(test_output)
        print(f"✅ Measured duration: {measured:.2f}s (target: 12.0s)")
