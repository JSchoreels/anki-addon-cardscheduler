"""
Configuration for the CardScheduler addon.

Loads settings from Anki's add-on config when running inside Anki.
Outside Anki, loads settings from cardscheduler/config.json if present.
"""

import json
import os
from copy import deepcopy

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

    # Automatically refresh vocabulary data at selected lifecycle events.
    "automatic_processing": {
        "enabled": True,
        "run_on_startup": True,
        "run_on_new_day": True,
        "update_scores": True,
        "update_related_words": True,
        "reposition_new_cards": True,
        "delay_ms": 1500,
    },

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


def get_default_config():
    """Return an independent copy of the complete default configuration."""
    return deepcopy(_DEFAULTS)


def normalize_config(config):
    """Merge a partial configuration over all current defaults."""
    return _merge_config(get_default_config(), config or {})


def validate_config(config):
    """Return user-facing validation errors for a complete configuration."""
    config = normalize_config(config)
    errors = []

    def require_text(value, label):
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{label} cannot be empty.")

    require_text(config["deck_name"], "Vocabulary deck")

    if config["input_mode"] not in {"single", "two"}:
        errors.append("Input mode must be 'single' or 'two'.")
    if config["input_mode"] == "single":
        require_text(config["input_fields"]["single"], "Single input field")
    else:
        require_text(config["input_fields"]["kanji"], "Kanji input field")
        require_text(config["input_fields"]["reading"], "Reading input field")

    for key, value in config["field_names"].items():
        require_text(value, f"Vocabulary output field '{key}'")

    if config["no_kanji_merge_mode"] not in {
        "NO_KANJI_BEFORE",
        "NO_KANJI_AFTER",
        "NO_KANJI_ZIPPED",
    }:
        errors.append("Kana-only merge mode is invalid.")
    if str(config["no_kanji_frequency_type"]).upper() not in {
        "RANK",
        "FREQUENCY",
    }:
        errors.append("Kana-only frequency type must be RANK or FREQUENCY.")

    automatic = config["automatic_processing"]
    if not isinstance(automatic["delay_ms"], int) or not (
        0 <= automatic["delay_ms"] <= 60000
    ):
        errors.append("Automatic processing delay must be between 0 and 60000 ms.")

    reading = config["reading_to_kanji_cards"]
    require_text(reading["note_type"], "Reading→Kanji note type")
    if not isinstance(reading["max_grade"], int) or not (
        1 <= reading["max_grade"] <= 99
    ):
        errors.append("Reading→Kanji maximum grade must be between 1 and 99.")
    for key, value in reading["field_names"].items():
        require_text(value, f"Reading→Kanji field '{key}'")

    sentence = config["sentence_scoring"]
    if not sentence["deck_names"] or not all(
        isinstance(deck, str) and deck.strip() for deck in sentence["deck_names"]
    ):
        errors.append("At least one non-empty sentence deck is required.")
    require_text(sentence["note_type"], "Sentence note type")
    require_text(sentence["sentence_field"], "Sentence text field")
    for key, value in sentence["field_names"].items():
        require_text(value, f"Sentence output field '{key}'")

    return errors


def _load_config(
    config_path=LOCAL_CONFIG_PATH,
    anki_config_loader=load_anki_addon_config,
):
    """Load config from Anki or local JSON, falling back to defaults."""
    config = get_default_config()
    anki_config = anki_config_loader(__name__)

    if anki_config is not None:
        return normalize_config(anki_config)

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            config = normalize_config(user_config)
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

AUTOMATIC_PROCESSING_CONFIG = _config["automatic_processing"]
AUTOMATIC_PROCESSING_ENABLED = AUTOMATIC_PROCESSING_CONFIG["enabled"]
AUTOMATIC_UPDATE_SCORES = AUTOMATIC_PROCESSING_CONFIG["update_scores"]
AUTOMATIC_UPDATE_RELATED_WORDS = AUTOMATIC_PROCESSING_CONFIG["update_related_words"]
AUTOMATIC_REPOSITION_NEW_CARDS = AUTOMATIC_PROCESSING_CONFIG["reposition_new_cards"]
AUTOMATIC_PROCESSING_DELAY_MS = AUTOMATIC_PROCESSING_CONFIG["delay_ms"]

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
