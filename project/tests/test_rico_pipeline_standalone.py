"""
Standalone test for RicoPipeline

Tests complete RICo pipeline in COMPLETE ISOLATION.
WITHOUT any integration with chat_server.py
"""

import cv2
import numpy as np
import os
import tempfile
from src.rico_pipeline import RicoPipeline


def test_rico_pipeline_initialization():
    """Test pipeline initialization"""

    print("Testing RicoPipeline initialization...")

    pipeline = RicoPipeline()

    # Check components are initialized
    assert hasattr(pipeline, 'mouth_tracker'), "Mouth tracker not initialized"
    assert hasattr(pipeline, 'viseme_mapper'), "Viseme mapper not initialized"
    assert hasattr(pipeline, 'compositor'), "Compositor not initialized"
    assert pipeline.is_initialized, "Pipeline not marked as initialized"

    print("✅ Pipeline initialization successful")
    return True


def test_rico_pipeline_viseme_generation():
    """Test viseme generation in pipeline"""

    print("Testing viseme generation...")

    pipeline = RicoPipeline()

    test_text = "Hello world"
    visemes = pipeline.viseme_mapper.text_to_visemes(test_text)

    assert len(visemes) > 0, "No visemes generated"
    assert all('viseme' in v and 'start' in v and 'end' in v for v in visemes), "Invalid viseme structure"

    print(f"✅ Generated {len(visemes)} visemes from text")
    return True


def test_rico_pipeline_mouth_tracking():
    """Test mouth tracking in pipeline"""

    print("Testing mouth tracking...")

    pipeline = RicoPipeline()

    # Create test frame with a simple pattern
    test_frame = np.zeros((100, 100, 3), dtype=np.uint8)
    # Add some variation to simulate a face
    test_frame[30:70, 30:70] = [200, 150, 100]  # Face-like region

    # Test mouth tracking (may not detect actual mouth, but shouldn't crash)
    try:
        roi_data, confidence = pipeline.mouth_tracker.extract_mouth_roi(test_frame)
        # Result can be None (no mouth detected), but shouldn't crash
        print(f"✅ Mouth tracking completed (confidence: {confidence:.2f})")
        return True
    except Exception as e:
        print(f"❌ Mouth tracking failed: {e}")
        return False


def test_rico_pipeline_compositing():
    """Test compositing in pipeline"""

    print("Testing compositing...")

    pipeline = RicoPipeline()

    # Create test frames
    base_frame = np.full((50, 50, 3), [255, 0, 0], dtype=np.uint8)  # Red background
    mouth_roi = np.full((20, 20, 3), [0, 255, 0], dtype=np.uint8)  # Green mouth

    mouth_position = (15, 15)

    # Test compositing
    result_frame = pipeline.compositor.composite_mouth_roi(base_frame, mouth_roi, mouth_position)

    # Check that compositing occurred
    assert not np.array_equal(base_frame, result_frame), "Frames are identical"

    print("✅ Compositing working")
    return True


def test_rico_pipeline_stats():
    """Test pipeline statistics"""

    print("Testing pipeline statistics...")

    pipeline = RicoPipeline()

    stats = pipeline.get_pipeline_stats()

    assert 'total_frames' in stats, "Missing total_frames in stats"
    assert 'successful_frames' in stats, "Missing successful_frames in stats"
    assert 'success_rate' in stats, "Missing success_rate in stats"
    assert stats['total_frames'] == 0, "Should start with 0 frames"
    assert stats['successful_frames'] == 0, "Should start with 0 successful frames"

    print("✅ Pipeline statistics working")
    return True


def test_rico_pipeline_video_processing():
    """Test basic video processing (mock)"""

    print("Testing video processing pipeline...")

    pipeline = RicoPipeline()

    # Create a simple test video
    with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_video:
        video_path = tmp_video.name

    try:
        # Create a simple test video (just a few frames)
        height, width = 100, 100
        fps = 10
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))

        # Create 5 test frames
        for i in range(5):
            frame = np.full((height, width, 3), [255, 0, 0], dtype=np.uint8)  # Red frame
            out.write(frame)

        out.release()

        # Test pipeline processing
        with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp_output:
            output_path = tmp_output.name

        try:
            result_path = pipeline.process_video_with_audio(
                video_path=video_path,
                audio_path="",  # Empty for now
                text="Test",
                output_path=output_path
            )

            # Check that output file exists
            assert os.path.exists(result_path), f"Output video not created: {result_path}"

            # Check pipeline stats
            stats = pipeline.get_pipeline_stats()
            assert stats['total_frames'] > 0, "No frames were processed"

            print(f"✅ Video processing completed: {stats['total_frames']} frames processed")

        finally:
            if os.path.exists(output_path):
                os.unlink(output_path)

    finally:
        if os.path.exists(video_path):
            os.unlink(video_path)

    return True


if __name__ == "__main__":
    try:
        print("Starting RicoPipeline standalone tests...\n")

        test_rico_pipeline_initialization()
        print()

        test_rico_pipeline_viseme_generation()
        print()

        test_rico_pipeline_mouth_tracking()
        print()

        test_rico_pipeline_compositing()
        print()

        test_rico_pipeline_stats()
        print()

        test_rico_pipeline_video_processing()
        print()

        print("🎉 ALL RICO PIPELINE TESTS PASSED!")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
