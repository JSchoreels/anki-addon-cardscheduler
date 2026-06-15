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
from .anki_interface import (
    load_cards,
    process_all_features,
    process_collection,
    process_related_words,
    process_sentence_scores,
)
from .reading_to_kanji_cards import process_reading_to_kanji_cards

# Import scheduler classes and functions
from .scheduler import (
    CardInfo,
    KanjiReadingInfo,
    build_card_to_pairs,
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
    'process_related_words',
    'process_sentence_scores',
    'process_all_features',
    'process_reading_to_kanji_cards',
    'load_cards',
    'CardInfo',
    'KanjiReadingInfo',
    'build_card_to_pairs',
    'compute_scores',
    'assign_positions_to_new_cards',
    'get_kanji_reading_to_matching_card',
    'update_kanji_reading_to_cards_with_max_weighted_interval',
    'compute_unlock_potential',
    'load_kanji_dictionnary_readings',
    'get_kanji_reading_pairs',
    'convert_two_fields_to_furigana',
    'NO_KANJI_BEFORE',
    'NO_KANJI_AFTER',
    'NO_KANJI_ZIPPED',
    'NO_KANJI_MERGE_MODE',
    'NO_KANJI_FREQUENCY_FIELD',
    'NO_KANJI_FREQUENCY_TYPE',
    'NO_KANJI_FREQUENCY_TYPE_RANK',
    'NO_KANJI_FREQUENCY_TYPE_FREQUENCY',
    'SENTENCE_DECK_NAMES',
    'SENTENCE_NOTE_TYPE',
    'SENTENCE_FIELD',
    'FIELD_NAME_SENTENCE_STRICT_SCORE',
    'FIELD_NAME_SENTENCE_PREDICTED_SCORE',
    'FIELD_NAME_SENTENCE_MISSING_WORDS',
    'FIELD_NAME_SENTENCE_INFERRED_WORDS',
    'FIELD_NAME_SENTENCE_KANJI_WORD_COUNT',
    'FIELD_NAME_SENTENCE_PRIORITY_SCORE',
]
