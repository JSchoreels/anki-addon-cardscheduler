"""
CardScheduler - Intelligent vocabulary card scheduling for Anki.

This addon helps you learn Japanese vocabulary by prioritizing cards based on:
- Unlock potential (how many cards would be unlocked by learning this)
- Card familiarity (stability/interval of kanji/readings)
- Card complexity (number of kanji, length)

The addon computes optimal learning positions for new cards and updates
card fields with computed scores and metrics.
"""

# Import main entry point
from .anki_interface import process_collection, load_cards

# Import scheduler classes and functions
from .scheduler import (
    CardInfo,
    KanjiReadingInfo,
    compute_scores,
    assign_positions_to_new_cards,
    get_kanji_reading_to_matching_card,
    update_kanji_reading_to_cards_with_max_weighted_interval,
    compute_unlock_potential,
)

# Import dictionary functions
from .dictionary import load_kanji_dictionnary_readings

# Import word parser functions
from .word_parser import (
    get_kanji_reading_pairs,
    convert_two_fields_to_furigana,
)

# Import configuration
from .config import *

# Expose main function and key classes/functions
__all__ = [
    'process_collection',
    'load_cards',
    'CardInfo',
    'KanjiReadingInfo',
    'compute_scores',
    'assign_positions_to_new_cards',
    'get_kanji_reading_to_matching_card',
    'update_kanji_reading_to_cards_with_max_weighted_interval',
    'compute_unlock_potential',
    'load_kanji_dictionnary_readings',
    'get_kanji_reading_pairs',
    'convert_two_fields_to_furigana',
]
