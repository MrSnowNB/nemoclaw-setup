#!/usr/bin/env python3
"""Debug TTS engine initialization and synthesis"""

import sys
import os
print(f"Python: {sys.version}")
print(f"Platform: {sys.platform}")

# Test pyttsx3 import
try:
    import pyttsx3
    print("✅ pyttsx3 imported successfully")
except ImportError as e:
    print(f"❌ Failed to import pyttsx3: {e}")
    exit(1)

# Test initialization
print("\n🔧 Testing pyttsx3 initialization...")
try:
    engine = pyttsx3.init()
    if engine is None:
        print("❌ pyttsx3.init() returned None")
        print("🔍 Troubleshooting:")
        print("   - On Linux: sudo apt-get install espeak")
        print("   - On macOS: TTS should work out of box")
        print("   - On Windows: SAPI5 should be available")
        exit(1)
    else:
        print("✅ pyttsx3.init() succeeded")
except Exception as e:
    print(f"❌ pyttsx3.init() failed with exception: {e}")
    if "NoBackendError" in str(e):
        print("🔧 Backend error - try installing espeak (Linux)")
    exit(1)

# Test basic properties
try:
    voices = engine.getProperty('voices')
    voices_list = voices if isinstance(voices, (list, tuple)) else []
    print(f"✅ Found {len(voices_list)} voices")

    rate = engine.getProperty('rate')
    print(f"✅ Current rate: {rate}")

    if voices_list:
        print("🎤 Available voices:")
        for i, voice in enumerate(voices_list[:5]):  # Show first 5
            age = getattr(voice, 'age', 'unknown')
            gender = getattr(voice, 'gender', 'unknown')
            print(f"   {i+1}. {voice.name} (age: {age}, gender: {gender})")
except Exception as e:
    print(f"⚠️ Could not get voice properties: {e}")

# Test audio generation
print("\n🗣️ Testing audio generation...")
test_dir = "outputs/test"
os.makedirs(test_dir, exist_ok=True)
test_file = os.path.join(test_dir, "debug_test.wav")
test_text = "This is Alice testing TTS functionality."

try:
    engine.save_to_file(test_text, test_file)
    engine.runAndWait()

    if os.path.exists(test_file):
        size = os.path.getsize(test_file)
        print(f"✅ Audio file created: {test_file} ({size} bytes)")

        # Try different extension
        test_file_wav = test_file.replace('.wav', '.mp3')
        os.rename(test_file, test_file_wav)
        print(f"✅ Renamed to: {test_file_wav}")
    else:
        print(f"❌ Audio file not created: {test_file}")
        print("💡 Possible issues:")
        print("   - No write permissions to outputs/test")
        print("   - TTS backend not working properly")
        print("   - File extension not supported")

        # Try without file extension
        test_file_noext = os.path.join(test_dir, "debug_test_noext")
        engine.save_to_file(test_text, test_file_noext)
        engine.runAndWait()

        if os.path.exists(test_file_noext):
            print(f"✅ File created without extension: {test_file_noext}")
        else:
            print("❌ Even no-extension file not created")

except Exception as e:
    print(f"❌ Audio generation failed: {e}")
    print("🔧 Try installing TTS backends:")
    if sys.platform.startswith('linux'):
        print("   sudo apt-get install espeak-ng-nss-plugins -y")
        print("   sudo apt-get install mbrola -y")
    elif sys.platform.startswith('darwin'):
        print("   Should work out of box on macOS")
    elif sys.platform.startswith('win'):
        print("   Should work out of box on Windows")

# Test our AliceTTSEngine wrapper
print("\n🎭 Testing AliceTTSEngine wrapper...")
try:
    from src.tts_engine import AliceTTSEngine
    alice_tts = AliceTTSEngine()
    print("✅ AliceTTSEngine initialized")

    # Test synthesis
    test_path = alice_tts.synthesize("Hello! I'm Alice testing the TTS wrapper.", output_dir="outputs/debug")
    if test_path and os.path.exists(test_path):
        print(f"✅ AliceTTSEngine synthesis worked: {test_path}")
    else:
        print(f"❌ AliceTTSEngine synthesis failed: path={test_path}")

except Exception as e:
    print(f"❌ AliceTTSEngine failed: {e}")
    import traceback
    traceback.print_exc()

print("\n🔍 Debugging complete")
print("💡 Share this output for additional troubleshooting help!")
