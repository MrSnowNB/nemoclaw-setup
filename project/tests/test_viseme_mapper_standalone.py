"""
Standalone test for VisemeMapper

Tests viseme mapping in COMPLETE ISOLATION.
WITHOUT any integration with chat_server.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.viseme_mapper import VisemeMapper


def test_viseme_mapping_phonemes():
    """Test phoneme to viseme mapping"""

    print("Testing phoneme to viseme mapping...")

    mapper = VisemeMapper()

    # Test phoneme data
    phoneme_data = [
        {'phoneme': 'HH', 'start': 0.0, 'end': 0.1},    # H
        {'phoneme': 'EH', 'start': 0.1, 'end': 0.3},    # E
        {'phoneme': 'L', 'start': 0.3, 'end': 0.4},     # L
        {'phoneme': 'OW', 'start': 0.4, 'end': 0.7},    # O
    ]

    visemes = mapper.phonemes_to_visemes(phoneme_data)

    # Validate results
    assert len(visemes) == 4, f"Expected 4 visemes, got {len(visemes)}"

    # Check mappings
    expected_visemes = ['UH', 'EH', 'IH', 'OW']  # H->UH, E->EH, L->IH, O->OW
    for i, viseme in enumerate(visemes):
        assert viseme['viseme'] == expected_visemes[i], f"Viseme {i}: expected {expected_visemes[i]}, got {viseme['viseme']}"
        assert 'start' in viseme and 'end' in viseme and 'duration' in viseme

    # Validate timing
    assert mapper.validate_viseme_sequence(visemes), "Viseme sequence validation failed"

    print(f"✅ Mapped phonemes to visemes: {expected_visemes}")
    return True


def test_viseme_mapping_text():
    """Test text to viseme mapping"""

    print("Testing text to viseme mapping...")

    mapper = VisemeMapper()

    text = "Hello world"
    visemes = mapper.text_to_visemes(text)

    # Should have at least some visemes
    assert len(visemes) > 0, "No visemes generated from text"

    # All visemes should be valid
    for viseme in visemes:
        assert 'viseme' in viseme
        assert 'start' in viseme and 'end' in viseme and 'duration' in viseme
        assert viseme['viseme'] in mapper.VISEME_DURATIONS

    # Validate sequence
    assert mapper.validate_viseme_sequence(visemes), "Text viseme sequence validation failed"

    print(f"✅ Generated {len(visemes)} visemes from text: {[v['viseme'] for v in visemes]}")
    return True


def test_viseme_durations():
    """Test viseme duration lookup"""

    print("Testing viseme duration lookup...")

    mapper = VisemeMapper()

    # Test known visemes
    assert mapper.get_viseme_duration('AA') == 1.0
    assert mapper.get_viseme_duration('AW') == 1.2  # Diphthong
    assert mapper.get_viseme_duration('UNKNOWN') == 1.0  # Default

    print("✅ Viseme durations working correctly")
    return True


def test_viseme_validation():
    """Test viseme sequence validation"""

    print("Testing viseme sequence validation...")

    mapper = VisemeMapper()

    # Valid sequence
    valid_visemes = [
        {'viseme': 'AH', 'start': 0.0, 'end': 0.3, 'duration': 0.3},
        {'viseme': 'EH', 'start': 0.3, 'end': 0.6, 'duration': 0.3},
    ]
    assert mapper.validate_viseme_sequence(valid_visemes), "Valid sequence rejected"

    # Invalid sequence (overlap)
    invalid_visemes = [
        {'viseme': 'AH', 'start': 0.0, 'end': 0.4, 'duration': 0.4},
        {'viseme': 'EH', 'start': 0.3, 'end': 0.6, 'duration': 0.3},  # Overlaps
    ]
    assert not mapper.validate_viseme_sequence(invalid_visemes), "Invalid sequence accepted"

    print("✅ Viseme validation working correctly")
    return True


if __name__ == "__main__":
    try:
        print("Starting VisemeMapper standalone tests...\n")

        test_viseme_mapping_phonemes()
        print()

        test_viseme_mapping_text()
        print()

        test_viseme_durations()
        print()

        test_viseme_validation()
        print()

        print("🎉 ALL VISEME MAPPER TESTS PASSED!")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
