#!/bin/bash
echo "🔍 RICo Phase 1 Readiness Check"

# Check video clips
echo "\n📹 Video Clips:"
ls -1 data/video_clips/*.mp4 2>/dev/null || echo "❌ No video clips found"

# Check Python files
echo "\n🐍 Python Modules:"
test -f src/chat_server.py && echo "✅ chat_server.py" || echo "❌ Missing chat_server.py"
test -f src/emotion_detector.py && echo "✅ emotion_detector.py" || echo "❌ Missing emotion_detector.py"

# Check dependencies
echo "\n📦 Dependencies:"
python -c "import librosa" 2>/dev/null && echo "✅ librosa installed" || echo "❌ librosa MISSING"
python -c "import ffmpeg" 2>/dev/null && echo "✅ ffmpeg-python installed" || echo "❌ ffmpeg-python MISSING"
ffmpeg -version >/dev/null 2>&1 && echo "✅ FFmpeg binary installed" || echo "❌ FFmpeg MISSING"

# Check configuration
echo "\n⚙️ Configuration:"
test -f data/emotion_config.yaml && echo "✅ emotion_config.yaml exists" || echo "❌ emotion_config.yaml MISSING"

# Check directories
echo "\n📂 Directories:"
test -d outputs/video && echo "✅ outputs/video/" || echo "⚠️  outputs/video/ will be created"
test -d outputs/logs && echo "✅ outputs/logs/" || echo "⚠️  outputs/logs/ will be created"

# Check Module integration
echo "\n🔗 Module Integration:"
python -c "from src.video_duration_matcher import VideoDurationMatcher; print('✅ VideoDurationMatcher imports')" 2>/dev/null || echo "❌ VideoDurationMatcher import failed"

echo "\n✅ Diagnostic complete"
