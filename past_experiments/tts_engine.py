#!/usr/bin/env python3
"""
Alice in Cyberland - TTS Engine Module
Uses pyttsx3 for offline speech synthesis compatible with Python 3.13
"""

import os
import pyttsx3
import yaml
from pathlib import Path
import uuid

class AliceTTSEngine:
    """TTS engine using pyttsx3 for Alice's voice synthesis"""

    def __init__(self, manifest_path='/home/mr-snow/alice_cyberland/project/data/video_manifest.yaml'):
        """Initialize TTS engine with video manifest configuration"""
        self.manifest_path = manifest_path
        self.manifest = self._load_manifest()
        self.voice_settings = self.manifest.get('voice_settings', {})
        self.engine = None
        self._initialize_engine()
        if self.engine is None:
            raise ValueError("Failed to initialize TTS engine")

    def _load_manifest(self):
        """Load video manifest YAML configuration"""
        try:
            with open(self.manifest_path, 'r') as f:
                return yaml.safe_load(f)
        except Exception as e:
            print(f"Error loading manifest: {e}")
            return {}

    def _initialize_engine(self):
        """Initialize pyttsx3 engine with Alice's voice characteristics"""
        try:
            print("🔊 Initializing pyttsx3 TTS engine...")
            self.engine = pyttsx3.init()

            if self.engine is None:
                print("❌ CRITICAL: pyttsx3.init() returned None")
                print("   This usually means pyttsx3 failed to find a TTS engine")
                print("   Possible causes:")
                print("   - No TTS system installed (eSpeak, NSSpeechSynthesizer, SAPI5)")
                print("   - Missing system TTS dependencies")
                print("   - Python environment issues")
                return

            print("✅ pyttsx3 engine initialized successfully")

            # Configure voice settings from manifest
            # Note: pyttsx3 'rate' is speech speed (words per minute), not sample rate
            # Typical range: 120-200 WPM. Default 200 is often too fast for clarity
            speech_rate = 180  # Use reasonable speech rate for clear audio
            self.engine.setProperty('rate', speech_rate)

            # Set volume to maximum (0.0 to 1.0)
            self.engine.setProperty('volume', 1.0)

            # Select female voice if available
            self._select_female_voice()

            print(f"✅ TTS engine fully configured (rate: {speech_rate} WPM)")

        except Exception as e:
            print(f"❌ CRITICAL: pyttsx3 initialization failed with exception: {e}")
            self.engine = None

    def _select_female_voice(self):
        """Select female voice from available voices"""
        if self.engine is None:
            return
        voices = self.engine.getProperty('voices')
        if voices:
            # Find female voice
            for voice in voices:  # type: ignore
                if 'female' in voice.name.lower() or 'woman' in voice.name.lower() or 'girl' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    print(f"Selected voice: {voice.name}")
                    return

            # Fallback to first female or just use default
            for voice in voices:  # type: ignore
                if voice.name and 'voice' in voice.name.lower():
                    self.engine.setProperty('voice', voice.id)
                    print(f"Fallback voice: {voice.name}")
                    return

        print("Using default voice")

    def synthesize(self, text, output_dir="outputs/audio", filename=None):
        """
        Generate speech audio from text

        Args:
            text: Text to synthesize
            output_dir: Directory to save audio file
            filename: Optional filename (auto-generated if None)

        Returns:
            Path to generated audio file
        """
        if self.engine is None:
            print("Error: TTS engine not initialized")
            return None

        # Create output directory if needed
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate unique filename if not provided
        if filename is None:
            filename = f"alice_response_{uuid.uuid4().hex[:8]}.wav"

        audio_path = os.path.join(output_dir, filename)

        try:
            # Save to file directly
            self.engine.save_to_file(text, audio_path)
            self.engine.runAndWait()

            # pyttsx3.runAndWait() is asynchronous for file I/O - wait for file creation
            import time
            timeout = 10  # 10 second timeout
            start_time = time.time()

            while not os.path.exists(audio_path) and (time.time() - start_time) < timeout:
                time.sleep(0.1)  # Short wait

            if os.path.exists(audio_path):
                size = os.path.getsize(audio_path)
                print(f"✅ Audio generated: {audio_path} ({size} bytes)")
                return audio_path
            else:
                print(f"❌ Audio file timeout: {audio_path} not created after {timeout}s")
                return None

        except Exception as e:
            print(f"Error generating audio: {e}")
            return None

    def get_audio_duration(self, audio_path):
        """
        Estimate audio duration for synchronization
        Basic implementation - returns estimated seconds
        """
        # pyttsx3 doesn't provide direct duration, so estimate
        # Rough estimate: 150 words per minute = 2.5 words per second
        word_count = len(audio_path.split('_')[-1].split('.')[0])  # rough text length
        return max(2, word_count / 2.5)  # minimum 2 seconds

    def list_voice_properties(self):
        """Debug: List current voice properties"""
        if self.engine is None:
            print("TTS engine not initialized")
            return
        voices = self.engine.getProperty('voices')
        for voice in voices:  # type: ignore
            print(f"Voice: {voice.name}, ID: {voice.id}, Age: {voice.age}")

        rate = self.engine.getProperty('rate')
        print(f"Current rate: {rate}")

    def test_engine(self, test_text="Hello, I am Alice. Welcome to Cyberland."):
        """Test TTS engine with sample text"""
        print(f"Testing TTS with: '{test_text}'")
        audio_path = self.synthesize(test_text, output_dir="outputs/test")
        if audio_path:
            duration = self.get_audio_duration(audio_path)
            print(".1f")
            return audio_path
        return None


# Test if run directly
if __name__ == "__main__":
    engine = AliceTTSEngine()
    engine.list_voice_properties()
    test_path = engine.test_engine()
    if test_path:
        print(f"Test audio saved to: {test_path}")
