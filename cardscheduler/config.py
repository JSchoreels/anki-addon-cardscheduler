"""
Configuration for the CardScheduler addon.

Loads settings from Anki's add-on config when running inside Anki.
Outside Anki, loads settings from cardscheduler/config.json if present.
"""

import json
import os

from .anki_config_adapter import load_anki_addon_config

LOCAL_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

# Default configuration
_DEFAULTS = {
    # Deck to process
    "deck_name": "Japan::1. Vocabulary",

    # Output field names
    "field_names": {
        "position": "CardScheduler.Position",
        "score": "CardScheduler.Score",
        "unlock_potential": "CardScheduler.UnlockPotential",
        "unlock_median_score_increase": "CardScheduler.UnlockMedianScoreIncrease",
        "score_without_missing": "CardScheduler.ScoreWithoutMissing",
        "missing_kanji_count": "CardScheduler.MissingKanjiCount",
        "related_known": "CardScheduler.Related.Known",
        "related_unknown": "CardScheduler.Related.Unknown",
        "kanji_meanings": "CardScheduler.KanjiMeanings",
        "cards_with_kanji": "CardScheduler.CardsWithKanji",
        "cards_with_kanji_known": "CardScheduler.CardsWithKanjiKnown",
        "cards_with_kanji_unknown": "CardScheduler.CardsWithKanjiUnknown",
    },

    # Input mode: "single" or "two"
    "input_mode": "two",

    # Input field names
    "input_fields": {
        "single": "ID",
        "kanji": "Front",
        "reading": "Reading",
    },

    # Simulation mode (treat all cards as new)
    "simulate_zero_stability": False,

    # How kana-only cards are merged into the learning order
    # Options: "NO_KANJI_BEFORE", "NO_KANJI_AFTER", "NO_KANJI_ZIPPED"
    "no_kanji_merge_mode": "NO_KANJI_ZIPPED",

    # No-kanji card ordering by frequency field
    # no_kanji_frequency_type options: "RANK" (lower is better), "FREQUENCY" (higher is better)
    "no_kanji_frequency_field": "Frequency",
    "no_kanji_frequency_type": "RANK",

    # Generated Reading -> Kanji cards
    "reading_to_kanji_cards": {
        "deck_name": "Japan::4. Recall::Reading->Kanji",
        "note_type": "CardScheduler Reading->Kanji",
        "max_grade": 8,
        "field_names": {
            "reading": "Reading",
            "kanji_meaning": "Kanji Meaning",
            "matching_kanji_count": "Matching Kanji Count",
            "grade": "Grade",
            "frequency": "Frequency",
            "known_words": "Known Words",
        },
    },

    # Sentence scoring from reviewed vocabulary and kanji-reading familiarity
    "sentence_scoring": {
        "deck_names": [
            "Japan::2. Sentences",
            "Japan::3. Audio",
        ],
        "note_type": "Japanese Sentence Card",
        "sentence_field": "Sentence",
        "field_names": {
            "strict_score": "CardScheduler.SentenceStrictScore",
            "predicted_score": "CardScheduler.SentencePredictedScore",
            "missing_words": "CardScheduler.SentenceMissingWords",
            "inferred_words": "CardScheduler.SentenceInferredWords",
            "kanji_word_count": "CardScheduler.SentenceKanjiWordCount",
            "priority_score": "CardScheduler.SentencePriorityScore",
        },
    },
}


def _load_config(
    config_path=LOCAL_CONFIG_PATH,
    anki_config_loader=load_anki_addon_config,
):
    """Load config from Anki or local JSON, falling back to defaults."""
    config = _merge_config({}, _DEFAULTS)
    anki_config = anki_config_loader(__name__)

    if anki_config is not None:
        return _merge_config(config, anki_config)

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            config = _merge_config(config, user_config)
        except (json.JSONDecodeError, IOError) as e:
            print(f"CardScheduler: Error loading config.json: {e}")

    return config


def _merge_config(base, override):
    merged = base.copy()
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _merge_config(merged[key], value)
        else:
            merged[key] = value
    return merged


_config = _load_config()

# Expose config values as module-level constants for backwards compatibility
DECK_NAME = _config["deck_name"]

FIELD_NAME_POSITION = _config["field_names"]["position"]
FIELD_NAME_SCORE = _config["field_names"]["score"]
FIELD_NAME_UNLOCK_POTENTIAL = _config["field_names"]["unlock_potential"]
FIELD_NAME_UNLOCK_MEDIAN_SCORE_INCREASE = _config["field_names"]["unlock_median_score_increase"]
FIELD_NAME_SCORE_WITHOUT_MISSING = _config["field_names"]["score_without_missing"]
FIELD_NAME_MISSING_KANJI_COUNT = _config["field_names"]["missing_kanji_count"]
FIELD_NAME_RELATED_KNOWN = _config["field_names"]["related_known"]
FIELD_NAME_RELATED_UNKNOWN = _config["field_names"]["related_unknown"]
FIELD_NAME_KANJI_MEANINGS = _config["field_names"]["kanji_meanings"]
FIELD_NAME_CARDS_WITH_KANJI = _config["field_names"]["cards_with_kanji"]
FIELD_NAME_CARDS_WITH_KANJI_KNOWN = _config["field_names"]["cards_with_kanji_known"]
FIELD_NAME_CARDS_WITH_KANJI_UNKNOWN = _config["field_names"]["cards_with_kanji_unknown"]

INPUT_MODE_SINGLE_FIELD = "single"
INPUT_MODE_TWO_FIELDS = "two"
INPUT_MODE = _config["input_mode"]
INPUT_FIELD_SINGLE = _config["input_fields"]["single"]
INPUT_FIELD_KANJI = _config["input_fields"]["kanji"]
INPUT_FIELD_READING = _config["input_fields"]["reading"]

SIMULATE_ZERO_STABILITY = _config["simulate_zero_stability"]

NO_KANJI_BEFORE = "NO_KANJI_BEFORE"
NO_KANJI_AFTER = "NO_KANJI_AFTER"
NO_KANJI_ZIPPED = "NO_KANJI_ZIPPED"
NO_KANJI_MERGE_MODE = _config["no_kanji_merge_mode"]

NO_KANJI_FREQUENCY_TYPE_RANK = "RANK"
NO_KANJI_FREQUENCY_TYPE_FREQUENCY = "FREQUENCY"
NO_KANJI_FREQUENCY_FIELD = _config["no_kanji_frequency_field"]
NO_KANJI_FREQUENCY_TYPE = str(_config["no_kanji_frequency_type"]).upper()

READING_TO_KANJI_CONFIG = _config["reading_to_kanji_cards"]
READING_TO_KANJI_DECK_NAME = READING_TO_KANJI_CONFIG["deck_name"]
READING_TO_KANJI_NOTE_TYPE = READING_TO_KANJI_CONFIG["note_type"]
READING_TO_KANJI_MAX_GRADE = READING_TO_KANJI_CONFIG["max_grade"]
READING_TO_KANJI_FIELD_NAMES = READING_TO_KANJI_CONFIG["field_names"]

SENTENCE_SCORING_CONFIG = _config["sentence_scoring"]
SENTENCE_DECK_NAMES = SENTENCE_SCORING_CONFIG["deck_names"]
SENTENCE_NOTE_TYPE = SENTENCE_SCORING_CONFIG["note_type"]
SENTENCE_FIELD = SENTENCE_SCORING_CONFIG["sentence_field"]
SENTENCE_FIELD_NAMES = SENTENCE_SCORING_CONFIG["field_names"]
FIELD_NAME_SENTENCE_STRICT_SCORE = SENTENCE_FIELD_NAMES["strict_score"]
FIELD_NAME_SENTENCE_PREDICTED_SCORE = SENTENCE_FIELD_NAMES["predicted_score"]
FIELD_NAME_SENTENCE_MISSING_WORDS = SENTENCE_FIELD_NAMES["missing_words"]
FIELD_NAME_SENTENCE_INFERRED_WORDS = SENTENCE_FIELD_NAMES["inferred_words"]
FIELD_NAME_SENTENCE_KANJI_WORD_COUNT = SENTENCE_FIELD_NAMES["kanji_word_count"]
FIELD_NAME_SENTENCE_PRIORITY_SCORE = SENTENCE_FIELD_NAMES["priority_score"]
