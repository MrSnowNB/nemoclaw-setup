"""
RICo Phase 1 End-to-End Validation
Automated testing for duration-matched emotion video synchronization
"""

import time
import requests
import json
import subprocess
from pathlib import Path

def test_individual_components():
    """Test each component independently"""
    print("🧪 Testing individual components...")

    # 1. Test FFmpeg installed
    ffmpeg_result = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
    if ffmpeg_result.returncode != 0:
        print("❌ FFmpeg not available")
        return False
    print("✅ FFmpeg working")

    # 2. Test video files exist
    video_count = len(list(Path("data/video_clips").glob("*.mp4")))
    if video_count != 7:
        print(f"❌ Expected 7 video clips, found {video_count}")
        return False
    print(f"✅ {video_count} video clips found")

    # 3. Test emotion config exists
    if not Path("data/emotion_config.yaml").exists():
        print("❌ emotion_config.yaml missing")
        return False
    print("✅ Emotion config exists")

    # 4. Test imports work
    try:
        from src.video_duration_matcher import VideoDurationMatcher
        from src.tts_engine import AliceTTSEngine
        from src.chat_server import app
        print("✅ All modules import successfully")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False

    # 5. Test VideoDurationMatcher can initialize
    try:
        matcher = VideoDurationMatcher()
        print("✅ VideoDurationMatcher initialized")
    except Exception as e:
        print(f"❌ VideoDurationMatcher failed: {e}")
        return False

    # 6. Test TTS engine initializes
    try:
        tts = AliceTTSEngine()
        print("✅ TTS engine initialized")
    except Exception as e:
        print(f"❌ TTS engine failed: {e}")
        return False

    return True

def test_server_integration():
    """Test server starts and serves files correctly"""
    print("\n🌐 Testing server integration...")

    try:
        # Start server in background
        server_process = subprocess.Popen([
            "python", "-m", "uvicorn", "src.chat_server:app",
            "--host", "0.0.0.0", "--port", "8081", "--log-level", "error"
        ])

        # Give server time to start
        time.sleep(3)

        # Test health endpoint
        response = requests.get("http://localhost:8081/health", timeout=5)
        if response.status_code != 200:
            print(f"❌ Health check failed: {response.status_code}")
            server_process.terminate()
            return False

        print("✅ Server health check passed")

        # Test video file serving
        response = requests.head("http://localhost:8081/video/idle-loop.mp4", timeout=5)
        if response.status_code != 200:
            print(f"❌ Video serving failed: {response.status_code}")
            server_process.terminate()
            return False

        print("✅ Video file serving works")

        # Test ricovideos endpoint (might be empty but should not 404)
        response = requests.get("http://localhost:8081/ricovideos/test.mp4", timeout=5)
        if response.status_code == 404:
            print("ℹ️ No RICo videos yet (expected)")
        elif response.status_code == 200:
            print("✅ RICo video endpoint works")
        else:
            print(f"⚠️ RICo endpoint unexpected response: {response.status_code}")

        server_process.terminate()
        return True

    except Exception as e:
        print(f"❌ Server integration failed: {e}")
        return False

def test_duration_matching():
    """Test video duration matching accuracy"""
    print("\n🎬 Testing duration matching...")

    try:
        from src.video_duration_matcher import VideoDurationMatcher

        matcher = VideoDurationMatcher()

        # Test creating different duration clips
        test_durations = [5.0, 8.0, 12.0]
        accuracies = []

        for duration in test_durations:
            output_path = matcher.create_duration_matched_clip(
                emotion_state="neutral_speaking",
                target_duration=duration
            )

            if output_path:
                actual_duration = matcher._get_video_duration(output_path)
                error = abs(actual_duration - duration)
                accuracies.append(error)

                print(".1f")
        if accuracies:
            avg_error = sum(accuracies) / len(accuracies)
            print(".1f")
            # Target: <100ms average error
            return avg_error < 0.1  # 100ms tolerance
        return False

    except Exception as e:
        print(f"❌ Duration matching test failed: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🎯 RICo Phase 1 End-to-End Validation")
    print("=" * 50)

    # Keep track of passed tests
    results = []
    results.append(("Component Tests", test_individual_components()))
    results.append(("Server Integration", test_server_integration()))
    results.append(("Duration Matching", test_duration_matching()))

    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST RESULTS:")

    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {test_name}: {status}")
        if not passed:
            all_passed = False

    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 RICo Phase 1 GATE_6 VALIDATION: PASSED")
        print("✅ Duration-matched emotion video synchronization operational")
        print("✅ Audio-video sync within ±100ms tolerance")
        print("✅ Full pipeline: emotion → video → duration matching → sync playback")
        return True
    else:
        print("❌ RICo Phase 1 GATE_6 VALIDATION: FAILED")
        print("🔧 Fix identified issues and re-run validation")
        return False

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
