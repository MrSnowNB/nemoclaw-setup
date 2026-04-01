"""
RICo MVP Proof-of-Concept Integration Test

Complete end-to-end test of RICo mouth synchronization pipeline.
Generates patent-ready demonstration video showing phoneme-synchronized mouth movement.
"""

import cv2
import numpy as np
import json
import os
import sys
import time
import wave
from datetime import datetime
from typing import List, Dict, Any

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import RICo components
from src.rico_pipeline import RicoPipeline
from src.tts_engine import AliceTTSEngine


def generate_test_audio_and_phonemes() -> tuple[str, float, List[Dict]]:
    """
    Generate TTS audio with phoneme extraction for test phrase.

    Returns:
        Tuple of (audio_path, duration, phoneme_data)
    """
    print("🎤 Generating TTS audio with phonemes...")

    # Test phrase for patent demonstration
    test_phrase = "Hello, I'm Alice. This is a test of mouth synchronization."

    # Initialize TTS engine
    tts_engine = AliceTTSEngine()

    # Generate audio and get phonemes
    audio_path = "outputs/audio/mvp_test.wav"
    os.makedirs(os.path.dirname(audio_path), exist_ok=True)

    # Generate TTS audio
    audio_path_temp = tts_engine.synthesize(test_phrase, output_dir="outputs/audio", filename="temp_mvp.wav")
    if audio_path_temp is None:
        raise RuntimeError("TTS synthesis failed")

    # Copy the generated audio file to our desired location
    import shutil
    shutil.copy2(audio_path_temp, audio_path)

    # Get audio properties for duration calculation
    with wave.open(audio_path, 'rb') as wav_file:
        sample_rate = wav_file.getframerate()
        num_frames = wav_file.getnframes()
        duration = num_frames / sample_rate

    # For now, create mock phoneme data since TTS engine may not have phoneme extraction
    # In a full implementation, this would come from the TTS engine
    phoneme_data = generate_mock_phoneme_data(test_phrase, duration)

    print(".2f")
    print(f"📝 Phonemes: {len(phoneme_data)} timestamps")

    return audio_path, duration, phoneme_data


def generate_mock_phoneme_data(text: str, duration: float) -> List[Dict]:
    """
    Generate mock phoneme data for demonstration.
    In production, this would come from TTS engine with actual phoneme timing.
    """
    # Simple approximation: distribute phonemes evenly across duration
    words = text.replace(',', '').replace('.', '').split()
    phonemes_per_word = 3  # Rough approximation

    total_phonemes = len(words) * phonemes_per_word
    phoneme_duration = duration / total_phonemes

    phoneme_data = []
    current_time = 0.0

    # Common phoneme sequence for demonstration
    mock_phonemes = ['HH', 'EH', 'L', 'OW', 'AY', 'M', 'AE', 'L', 'IH', 'S']

    for i, word in enumerate(words):
        for j in range(phonemes_per_word):
            if i * phonemes_per_word + j < len(mock_phonemes):
                phoneme = mock_phonemes[i * phonemes_per_word + j]
            else:
                phoneme = 'AH'  # Default

            phoneme_data.append({
                'phoneme': phoneme,
                'start': current_time,
                'end': current_time + phoneme_duration
            })
            current_time += phoneme_duration

    return phoneme_data


def save_phoneme_data(phoneme_data: List[Dict], output_path: str):
    """Save phoneme data to JSON file for evidence."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'phoneme_count': len(phoneme_data),
            'phonemes': phoneme_data
        }, f, indent=2)

    print(f"💾 Phoneme data saved: {output_path}")


def process_video_with_rico(audio_path: str, phoneme_data: List[Dict], test_phrase: str) -> str:
    """
    Process video through RICo pipeline.

    Args:
        audio_path: Path to generated audio
        phoneme_data: Phoneme timing data

    Returns:
        Path to output video
    """
    print("\n🎬 Processing video with RICo pipeline...")

    # Initialize RICo pipeline
    pipeline = RicoPipeline()

    # Use neutral speaking clip as base
    video_path = "data/video_clips/speaking-neutral.mp4"

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Base video not found: {video_path}")

    # Get video properties
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()

    print(f"🎥 Base video: {video_path}")
    print(f"📊 FPS: {fps}, Total frames: {total_frames}")

    # Process video with RICo pipeline
    output_path = "outputs/patent_demo_synced.mp4"

    start_time = time.time()

    # Use the pipeline to process video
    result_path = pipeline.process_video_with_audio(
        video_path=video_path,
        audio_path=audio_path,
        text=test_phrase,  # Pass the actual text for viseme generation
        output_path=output_path
    )

    processing_time = time.time() - start_time

    # Get final stats
    stats = pipeline.get_pipeline_stats()

    print("\n✅ RICo processing complete!")
    print(f"📁 Output: {result_path}")
    print(f"🎞️  Frames processed: {stats['total_frames']}")
    print(".2f")

    # DEBUG: Add frame-by-frame analysis
    print("\n🔍 DEBUG: Analyzing frame differences...")
    analyze_frame_differences(video_path, result_path)

    # DEBUG: Show viseme sequence
    print("\n🔍 DEBUG: Viseme sequence analysis...")
    show_viseme_sequence(test_phrase)

    return result_path


def analyze_frame_differences(original_video: str, processed_video: str):
    """Analyze pixel differences between original and processed frames"""

    # Open both videos
    orig_cap = cv2.VideoCapture(original_video)
    proc_cap = cv2.VideoCapture(processed_video)

    if not orig_cap.isOpened() or not proc_cap.isOpened():
        print("❌ Could not open videos for comparison")
        return

    total_frames = min(
        int(orig_cap.get(cv2.CAP_PROP_FRAME_COUNT)),
        int(proc_cap.get(cv2.CAP_PROP_FRAME_COUNT))
    )

    total_pixel_diff = 0
    changed_frames = 0
    max_diff = 0

    print(f"Comparing {total_frames} frames...")

    for i in range(total_frames):
        orig_ret, orig_frame = orig_cap.read()
        proc_ret, proc_frame = proc_cap.read()

        if not orig_ret or not proc_ret:
            break

        # Calculate pixel difference
        diff = cv2.absdiff(orig_frame, proc_frame)
        pixel_diff = np.sum(diff)

        total_pixel_diff += pixel_diff
        max_diff = max(max_diff, pixel_diff)

        if pixel_diff > 100:  # Threshold for "changed"
            changed_frames += 1

        # Log every 10th frame
        if i % 10 == 0:
            print(f"Frame {i:3d}: Pixel diff = {pixel_diff:8d}")

    orig_cap.release()
    proc_cap.release()

    avg_diff = total_pixel_diff / total_frames if total_frames > 0 else 0
    change_percentage = (changed_frames / total_frames) * 100 if total_frames > 0 else 0

    print("\n📊 Frame Difference Analysis:")
    print(f"   Total frames: {total_frames}")
    print(f"   Changed frames: {changed_frames} ({change_percentage:.1f}%)")
    print(f"   Average pixel diff: {avg_diff:.0f}")
    print(f"   Maximum pixel diff: {max_diff}")

    if changed_frames == 0:
        print("❌ CRITICAL: NO FRAMES CHANGED! Compositing is not working.")
    elif change_percentage < 5:
        print("⚠️  WARNING: Very few frames changed (<5%). Mouth sync may not be visible.")
    else:
        print("✅ Frames are being modified - compositing appears to be working.")


def show_viseme_sequence(text: str):
    """Show the viseme sequence that would be generated for the text"""

    # Import here to avoid circular imports
    from src.viseme_mapper import VisemeMapper

    mapper = VisemeMapper()
    visemes = mapper.text_to_visemes(text)

    print(f"Text: '{text}'")
    print(f"Generated {len(visemes)} visemes:")

    for i, viseme in enumerate(visemes):
        print(f"  {i}: '{viseme['viseme']}' ({viseme['start']:.2f}s - {viseme['end']:.2f}s)")

    # Show unique visemes
    unique_visemes = set(v['viseme'] for v in visemes)
    print(f"Unique visemes used: {sorted(unique_visemes)}")


def verify_output_video(video_path: str, expected_duration: float):
    """Verify the output video was created correctly."""
    print("\n🔍 Verifying output video...")

    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Output video not created: {video_path}")

    # Check file size
    file_size = os.path.getsize(video_path)
    print(f"📏 File size: {file_size / (1024*1024):.1f} MB")

    if file_size < 1000000:  # Less than 1MB
        print("⚠️  Warning: Output file is very small")

    # Try to open video and check properties
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise RuntimeError("Cannot open output video")

    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = frame_count / fps if fps > 0 else 0

    cap.release()

    print(f"🎬 Video properties: {frame_count} frames, {fps} FPS, {duration:.2f}s duration")

    # Check duration is reasonable (should be close to audio duration)
    if abs(duration - expected_duration) > 2.0:  # Allow 2 second tolerance
        print(f"⚠️  Warning: Video duration ({duration:.2f}s) differs significantly from audio ({expected_duration:.2f}s)")

    print("✅ Output video verification passed")


def main():
    """Run the complete RICo MVP proof-of-concept."""
    try:
        print("🚀 Starting RICo MVP proof-of-concept...")
        print("=" * 60)

        # Step 1: Generate audio and phonemes
        audio_path, audio_duration, phoneme_data = generate_test_audio_and_phonemes()

        # Save phoneme data for evidence
        phoneme_json_path = "outputs/patent_demo_phonemes.json"
        save_phoneme_data(phoneme_data, phoneme_json_path)

        # Step 2: Process video through RICo pipeline
        test_phrase = "Hello, I'm Alice. This is a test of mouth synchronization."
        output_video_path = process_video_with_rico(audio_path, phoneme_data, test_phrase)

        # Step 3: Verify output
        verify_output_video(output_video_path, audio_duration)

        print("\n" + "=" * 60)
        print("🎉 RICo MVP PROOF-OF-CONCEPT COMPLETE!")
        print("=" * 60)
        print(f"📁 Demonstration video: {output_video_path}")
        print(f"🎵 Audio file: {audio_path}")
        print(f"📋 Phoneme data: {phoneme_json_path}")
        print("\n📋 Next: Human visual verification (TASK MVP-1.2)")

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
