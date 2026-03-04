"""
Configuration for the CardScheduler addon.

Loads settings from config.json if present, otherwise uses defaults.
Place config.json in the addon folder to customize settings.
"""

import json
import os

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
}


def _load_config():
    """Load config from config.json, falling back to defaults."""
    config_path = os.path.join(os.path.dirname(__file__), "config.json")

    config = _DEFAULTS.copy()

    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                user_config = json.load(f)
            # Merge user config into defaults (shallow merge for nested dicts)
            for key, value in user_config.items():
                if key in config and isinstance(config[key], dict) and isinstance(value, dict):
                    config[key] = {**config[key], **value}
                else:
                    config[key] = value
        except (json.JSONDecodeError, IOError) as e:
            print(f"CardScheduler: Error loading config.json: {e}")

    return config


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
