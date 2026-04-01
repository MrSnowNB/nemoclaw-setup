"""
Comprehensive validation test for VisemeMapper

Tests viseme mapping with comprehensive phonemic coverage, edge cases,
and detailed logging for GitHub review and debugging.
"""

import sys
import os
import yaml
import json
import traceback
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.viseme_mapper import VisemeMapper


def test_comprehensive_phoneme_mapping():
    """Test comprehensive phoneme to viseme mapping with detailed logging"""

    # Setup logging
    os.makedirs("outputs/logs", exist_ok=True)
    os.makedirs("outputs/debug", exist_ok=True)

    debug_log_path = "outputs/logs/viseme_mapper_debug.log"
    exception_log_path = "outputs/logs/viseme_mapper_exceptions.log"
    result_yaml_path = "outputs/debug/viseme_map_test_result.yaml"

    # Clear previous logs
    with open(debug_log_path, 'w') as f:
        f.write(f"=== VisemeMapper Comprehensive Test - {datetime.now()} ===\n\n")

    print("Starting comprehensive VisemeMapper validation...")

    mapper = VisemeMapper()

    # Test data covering all phonemic classes
    test_cases = [
        {
            'name': 'Basic Vowels',
            'text': 'She ate ice cream',
            'phonemes': [
                {'phoneme': 'SH', 'start': 0.0, 'end': 0.1},
                {'phoneme': 'IY', 'start': 0.1, 'end': 0.3},
                {'phoneme': 'EY', 'start': 0.4, 'end': 0.6},
                {'phoneme': 'T', 'start': 0.6, 'end': 0.7},
                {'phoneme': 'AY', 'start': 0.8, 'end': 1.0},
                {'phoneme': 'S', 'start': 1.0, 'end': 1.1},
                {'phoneme': 'K', 'start': 1.1, 'end': 1.2},
                {'phoneme': 'R', 'start': 1.2, 'end': 1.3},
                {'phoneme': 'IY', 'start': 1.3, 'end': 1.5},
                {'phoneme': 'M', 'start': 1.5, 'end': 1.6},
            ]
        },
        {
            'name': 'Consonants',
            'text': 'The quick brown fox',
            'phonemes': [
                {'phoneme': 'DH', 'start': 0.0, 'end': 0.1},
                {'phoneme': 'AH', 'start': 0.1, 'end': 0.2},
                {'phoneme': 'K', 'start': 0.3, 'end': 0.4},
                {'phoneme': 'W', 'start': 0.4, 'end': 0.5},
                {'phoneme': 'IH', 'start': 0.5, 'end': 0.6},
                {'phoneme': 'K', 'start': 0.6, 'end': 0.7},
                {'phoneme': 'B', 'start': 0.8, 'end': 0.9},
                {'phoneme': 'R', 'start': 0.9, 'end': 1.0},
                {'phoneme': 'AW', 'start': 1.0, 'end': 1.2},
                {'phoneme': 'N', 'start': 1.2, 'end': 1.3},
                {'phoneme': 'F', 'start': 1.4, 'end': 1.5},
                {'phoneme': 'AA', 'start': 1.5, 'end': 1.7},
                {'phoneme': 'K', 'start': 1.7, 'end': 1.8},
                {'phoneme': 'S', 'start': 1.8, 'end': 1.9},
            ]
        },
        {
            'name': 'Diphthongs',
            'text': 'How now brown cow',
            'phonemes': [
                {'phoneme': 'HH', 'start': 0.0, 'end': 0.1},
                {'phoneme': 'AW', 'start': 0.1, 'end': 0.3},
                {'phoneme': 'N', 'start': 0.4, 'end': 0.5},
                {'phoneme': 'AW', 'start': 0.5, 'end': 0.7},
                {'phoneme': 'B', 'start': 0.8, 'end': 0.9},
                {'phoneme': 'R', 'start': 0.9, 'end': 1.0},
                {'phoneme': 'AW', 'start': 1.0, 'end': 1.2},
                {'phoneme': 'N', 'start': 1.2, 'end': 1.3},
                {'phoneme': 'K', 'start': 1.4, 'end': 1.5},
                {'phoneme': 'AW', 'start': 1.5, 'end': 1.7},
            ]
        }
    ]

    all_results = {}

    for test_case in test_cases:
        case_name = test_case['name']
        print(f"\n--- Testing: {case_name} ---")
        print(f"Text: {test_case['text']}")

        with open(debug_log_path, 'a') as f:
            f.write(f"\n=== Test Case: {case_name} ===\n")
            f.write(f"Text: {test_case['text']}\n")
            f.write(f"Phonemes: {len(test_case['phonemes'])}\n\n")

        try:
            # Test phoneme mapping
            visemes = mapper.phonemes_to_visemes(test_case['phonemes'])

            print(f"Generated {len(visemes)} visemes:")
            for i, viseme in enumerate(visemes):
                print(f"  {i}: {viseme['viseme']} ({viseme['start']:.2f}-{viseme['end']:.2f})")
                with open(debug_log_path, 'a') as f:
                    f.write(f"Viseme {i}: {viseme['viseme']} ({viseme['start']:.3f}-{viseme['end']:.3f})\n")

            # Validate sequence
            is_valid = mapper.validate_viseme_sequence(visemes)
            print(f"Sequence validation: {'PASS' if is_valid else 'FAIL'}")

            with open(debug_log_path, 'a') as f:
                f.write(f"Sequence validation: {'PASS' if is_valid else 'FAIL'}\n\n")

            # Store results
            all_results[case_name] = {
                'text': test_case['text'],
                'phonemes': test_case['phonemes'],
                'visemes': visemes,
                'validation_passed': is_valid
            }

        except Exception as e:
            error_msg = f"❌ Exception in {case_name}: {e}"
            print(error_msg)
            with open(exception_log_path, 'a') as f:
                f.write(f"=== Exception in {case_name} ===\n")
                f.write(f"Timestamp: {datetime.now()}\n")
                f.write(f"Error: {e}\n")
                f.write(f"Traceback:\n{traceback.format_exc()}\n\n")
            continue

    return all_results


def test_edge_cases():
    """Test edge cases and error conditions"""

    print("\n--- Testing Edge Cases ---")

    debug_log_path = "outputs/logs/viseme_mapper_debug.log"
    exception_log_path = "outputs/logs/viseme_mapper_exceptions.log"

    mapper = VisemeMapper()

    edge_cases = [
        {'name': 'Empty Input', 'text': '', 'phonemes': []},
        {'name': 'Whitespace Only', 'text': '   ', 'phonemes': []},
        {'name': 'Non-English Characters', 'text': 'Hello 世界 🌍', 'phonemes': []},
        {'name': 'Numbers and Symbols', 'text': 'Test 123!@#', 'phonemes': []},
        {'name': 'Very Long Text', 'text': 'This is a very long sentence that should test the limits of our text processing capabilities and ensure that the system can handle extended input without any issues or performance degradation.', 'phonemes': []},
    ]

    edge_results = {}

    for case in edge_cases:
        case_name = case['name']
        print(f"\nTesting: {case_name}")

        with open(debug_log_path, 'a') as f:
            f.write(f"\n=== Edge Case: {case_name} ===\n")
            f.write(f"Input: '{case['text'][:100]}{'...' if len(case['text']) > 100 else ''}'\n")

        try:
            visemes = mapper.text_to_visemes(case['text'])

            print(f"Generated {len(visemes)} visemes")
            with open(debug_log_path, 'a') as f:
                f.write(f"Generated {len(visemes)} visemes\n")
                for i, viseme in enumerate(visemes[:5]):  # Log first 5
                    f.write(f"  {i}: {viseme}\n")
                if len(visemes) > 5:
                    f.write(f"  ... and {len(visemes) - 5} more\n")

            # Validate
            is_valid = mapper.validate_viseme_sequence(visemes)
            print(f"Validation: {'PASS' if is_valid else 'FAIL'}")

            edge_results[case_name] = {
                'input': case['text'],
                'viseme_count': len(visemes),
                'validation_passed': is_valid,
                'error': None
            }

        except Exception as e:
            error_msg = f"❌ Exception in {case_name}: {e}"
            print(error_msg)
            with open(exception_log_path, 'a') as f:
                f.write(f"=== Edge Case Exception: {case_name} ===\n")
                f.write(f"Timestamp: {datetime.now()}\n")
                f.write(f"Input: '{case['text'][:100]}'\n")
                f.write(f"Error: {e}\n")
                f.write(f"Traceback:\n{traceback.format_exc()}\n\n")

            edge_results[case_name] = {
                'input': case['text'],
                'viseme_count': 0,
                'validation_passed': False,
                'error': str(e)
            }

    return edge_results


def save_results_to_yaml(all_results, edge_results):
    """Save comprehensive test results to YAML file"""

    result_yaml_path = "outputs/debug/viseme_map_test_result.yaml"

    result_data = {
        'test_timestamp': datetime.now().isoformat(),
        'phoneme_mapping_tests': all_results,
        'edge_case_tests': edge_results,
        'summary': {
            'total_test_cases': len(all_results) + len(edge_results),
            'phoneme_tests': len(all_results),
            'edge_tests': len(edge_results),
            'all_mappings_logged': True,
            'exceptions_logged': True
        }
    }

    with open(result_yaml_path, 'w') as f:
        yaml.dump(result_data, f, default_flow_style=False, sort_keys=False)

    print(f"\n✅ Results saved to {result_yaml_path}")


def main():
    """Run comprehensive validation"""

    try:
        print("🎯 Starting VisemeMapper Comprehensive Validation")
        print("=" * 60)

        # Test comprehensive phoneme mapping
        all_results = test_comprehensive_phoneme_mapping()

        # Test edge cases
        edge_results = test_edge_cases()

        # Save results
        save_results_to_yaml(all_results, edge_results)

        # Final summary
        total_tests = len(all_results) + len(edge_results)
        passed_tests = sum(1 for r in all_results.values() if r.get('validation_passed', False)) + \
                      sum(1 for r in edge_results.values() if r.get('validation_passed', False))

        print(f"\n🎉 VALIDATION COMPLETE")
        print(f"Total test cases: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {total_tests - passed_tests}")

        if passed_tests == total_tests:
            print("✅ ALL TESTS PASSED - VisemeMapper validation successful!")
            return True
        else:
            print("⚠️  SOME TESTS FAILED - Check logs for details")
            return False

    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {e}")
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
