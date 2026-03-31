"""
Viseme Mapper for RICo Phase 2

Maps phonemes to visemes for mouth shape synchronization.
Based on standard phoneme-to-viseme mapping for English.
"""

import re
from typing import Dict, List, Optional, Tuple
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class VisemeMapper:
    """Maps phonemes to visemes for lip sync"""

    # Standard phoneme to viseme mapping
    # Visemes represent distinct mouth shapes
    PHONEME_TO_VISEME = {
        # Vowels
        'AA': 'AA',  # father
        'AE': 'AE',  # cat
        'AH': 'AH',  # hut
        'AO': 'AO',  # lot
        'AW': 'AW',  # cow
        'AY': 'AY',  # hide
        'EH': 'EH',  # bed
        'ER': 'ER',  # bird
        'EY': 'EY',  # bait
        'IH': 'IH',  # bit
        'IY': 'IY',  # beat
        'OW': 'OW',  # boat
        'OY': 'OY',  # boy
        'UH': 'UH',  # book
        'UW': 'UW',  # boot

        # Consonants - mapped to nearest vowel viseme
        'B': 'UH',   # book
        'CH': 'UH',  # book
        'D': 'UH',   # book
        'DH': 'AH',  # hut
        'F': 'UH',   # book
        'G': 'UH',   # book
        'HH': 'UH',  # book
        'JH': 'AH',  # hut
        'K': 'UH',   # book
        'L': 'IH',   # bit
        'M': 'UH',   # book
        'N': 'AH',   # hut
        'NG': 'AH',  # hut
        'P': 'UH',   # book
        'R': 'ER',   # bird
        'S': 'IH',   # bit
        'SH': 'IH',  # bit
        'T': 'UH',   # book
        'TH': 'IH',   # bit
        'V': 'UH',   # book
        'W': 'UW',   # boot
        'Y': 'IY',   # beat
        'Z': 'IH',   # bit
        'ZH': 'AH',  # hut
    }

    # Viseme durations (relative, will be scaled by phoneme duration)
    VISEME_DURATIONS = {
        'AA': 1.0, 'AE': 1.0, 'AH': 1.0, 'AO': 1.0, 'AW': 1.2,
        'AY': 1.2, 'EH': 1.0, 'ER': 1.0, 'EY': 1.2, 'IH': 1.0,
        'IY': 1.0, 'OW': 1.2, 'OY': 1.2, 'UH': 1.0, 'UW': 1.0
    }

    def __init__(self):
        """Initialize viseme mapper"""
        logger.info(f"VisemeMapper initialized with {len(self.PHONEME_TO_VISEME)} phoneme mappings")

    def phonemes_to_visemes(self, phoneme_data: List[Dict]) -> List[Dict]:
        """
        Convert phoneme sequence to viseme sequence

        Args:
            phoneme_data: List of phoneme dictionaries with keys:
                - 'phoneme': str (phoneme symbol)
                - 'start': float (start time in seconds)
                - 'end': float (end time in seconds)

        Returns:
            List of viseme dictionaries with keys:
                - 'viseme': str (viseme symbol)
                - 'start': float (start time in seconds)
                - 'end': float (end time in seconds)
                - 'duration': float (duration in seconds)
        """
        if not phoneme_data:
            logger.warning("Empty phoneme data provided")
            return []

        visemes = []

        for phoneme in phoneme_data:
            phoneme_symbol = phoneme.get('phoneme', '').strip()
            start_time = phoneme.get('start', 0.0)
            end_time = phoneme.get('end', 0.0)

            # Map phoneme to viseme
            viseme = self.PHONEME_TO_VISEME.get(phoneme_symbol, 'AH')  # Default to 'AH'

            duration = end_time - start_time
            if duration <= 0:
                logger.warning(f"Invalid phoneme duration: {duration} for {phoneme_symbol}")
                duration = 0.1  # Minimum duration

            viseme_data = {
                'viseme': viseme,
                'start': start_time,
                'end': end_time,
                'duration': duration
            }

            visemes.append(viseme_data)

        logger.info(f"Mapped {len(phoneme_data)} phonemes to {len(visemes)} visemes")
        return visemes

    def text_to_visemes(self, text: str, phoneme_timing: Optional[List[Dict]] = None) -> List[Dict]:
        """
        Convert text directly to visemes (simplified approach)

        Args:
            text: Input text string
            phoneme_timing: Optional phoneme timing data

        Returns:
            List of viseme dictionaries
        """
        if not text.strip():
            return []

        # Simple text-to-viseme mapping (fallback when no phoneme data available)
        # This is a basic approximation - real implementation would use phoneme analysis

        words = re.findall(r'\b\w+\b', text.lower())
        visemes = []

        current_time = 0.0
        word_duration = 0.3  # seconds per word (approximate)

        for word in words:
            # Map word to representative viseme based on vowels
            if any(vowel in word for vowel in 'aeiou'):
                # Find first vowel and map to viseme
                for char in word:
                    if char in 'aeiou':
                        viseme = self.PHONEME_TO_VISEME.get(char.upper() + 'H', 'AH')
                        break
                else:
                    viseme = 'AH'  # Default
            else:
                viseme = 'AH'  # Default for consonant-only words

            viseme_data = {
                'viseme': viseme,
                'start': current_time,
                'end': current_time + word_duration,
                'duration': word_duration
            }

            visemes.append(viseme_data)
            current_time += word_duration

        logger.info(f"Converted text '{text[:50]}...' to {len(visemes)} visemes")
        return visemes

    def get_viseme_duration(self, viseme: str) -> float:
        """
        Get the relative duration for a viseme

        Args:
            viseme: Viseme symbol

        Returns:
            Relative duration multiplier
        """
        return self.VISEME_DURATIONS.get(viseme, 1.0)

    def validate_viseme_sequence(self, visemes: List[Dict]) -> bool:
        """
        Validate viseme sequence for consistency

        Args:
            visemes: List of viseme dictionaries

        Returns:
            True if valid, False otherwise
        """
        if not visemes:
            return True

        prev_end = 0.0

        for viseme in visemes:
            start = viseme.get('start', 0)
            end = viseme.get('end', 0)
            duration = viseme.get('duration', 0)
            viseme_symbol = viseme.get('viseme', '')

            # Check timing consistency
            if start < prev_end - 0.01:  # Small tolerance for floating point
                logger.warning(f"Viseme timing overlap: start {start} < prev_end {prev_end}")
                return False

            if abs((end - start) - duration) > 0.01:
                logger.warning(f"Viseme duration mismatch: calculated {end-start}, stored {duration}")
                return False

            # Check viseme symbol validity
            if viseme_symbol not in self.VISEME_DURATIONS:
                logger.warning(f"Invalid viseme symbol: {viseme_symbol}")
                return False

            prev_end = end

        return True
