#!/bin/bash
# quick_setup_rico.sh - Prepares environment for RICo Phase 1

echo "🚀 RICo Phase 1 Quick Setup"

# Task 1.2: Install dependencies
echo "📦 Installing dependencies..."
pip install librosa==0.10.1 ffmpeg-python==0.2.0 pyyaml==6.0.1

# Task 1.3: Verify FFmpeg
echo "🔧 Checking FFmpeg..."
if ! command -v ffmpeg &> /dev/null; then
    echo "❌ FFmpeg not found. Installing..."
    # Auto-detect OS and install
    if [[ "$OSTYPE" == "darwin"* ]]; then
        brew install ffmpeg
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get install -y ffmpeg
    fi
fi

# Verify FFmpeg
ffmpeg -version | head -1
if [ $? -ne 0 ]; then
    echo "❌ FFmpeg installation failed"
    exit 1
fi

# Create output directories
echo "📁 Creating output directories..."
mkdir -p outputs/video outputs/logs

# Task 2.1: Create emotion config (automated)
echo "⚙️ Creating emotion configuration..."
cat > data/emotion_config.yaml << 'EOF'
# Emotion-to-Video Clip Mapping
# Maps emotion_detector output states to video clip filenames

emotion_mapping:
  idle:
    clip: "idle-loop.mp4"
    should_loop: true
    description: "Default rest state, continuous subtle movement"

  listening:
    clip: "reading-the-computer-screen.mp4"
    should_loop: true
    description: "User is typing or AI is thinking"

  greeting:
    clip: "it-is-great-to-see-you-again.mp4"
    should_loop: false
    description: "Welcome message, warm smile"

  neutral_speaking:
    clip: "speaking-nuetral.mp4"
    should_loop: false
    description: "Standard response delivery"

  friendly_speaking:
    clip: "thats-wonderful-to-hear.mp4"
    should_loop: false
    description: "Positive, enthusiastic response"

  empathetic:
    clip: "concerned-deep-breath.mp4"
    should_loop: false
    description: "Reflective, supportive response"

  farewell:
    clip: "see-you-later.mp4"
    should_loop: false
    description: "Gentle closing gesture"

# Fallback clip if emotion detection fails
default_clip: "speaking-nuetral.mp4"

# Base path for video clips
clips_directory: "data/video_clips"
EOF

echo "✅ Setup complete! Ready for Task 3."
echo ""
echo "🧪 Next: python src/video_duration_matcher.py  # Test the module"
echo "🎯 Then integrate with existing Alice chat system"
