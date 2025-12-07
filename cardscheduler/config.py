"""
Configuration constants for the CardScheduler addon.
"""

# Configuration: Customizable field names
FIELD_NAME_POSITION = "CardScheduler.Position"
FIELD_NAME_SCORE = "CardScheduler.Score"
FIELD_NAME_UNLOCK_POTENTIAL = "CardScheduler.UnlockPotential"
FIELD_NAME_UNLOCK_MEDIAN_SCORE_INCREASE = "CardScheduler.UnlockMedianScoreIncrease"
FIELD_NAME_SCORE_WITHOUT_MISSING = "CardScheduler.ScoreWithoutMissing"
FIELD_NAME_MISSING_KANJI_COUNT = "CardScheduler.MissingKanjiCount"

# Configuration: Simulation mode
# When True, all cards are treated as having zero stability (simulates starting from scratch)
# This shows what the optimal learning order would be if you had no progress
SIMULATE_ZERO_STABILITY = False

# Configuration: Input field format
# Mode 1: Single field containing kanji with furigana (e.g., "頭[あたま]が 痛[いた]い")
INPUT_MODE_SINGLE_FIELD = "single"
INPUT_FIELD_SINGLE = "ID"  # Field name for single-field mode

# Mode 2: Two fields - one with kanji, one with reading (e.g., "頭が痛い" + "あたまがいたい")
INPUT_MODE_TWO_FIELDS = "two"
INPUT_FIELD_KANJI = "Kanji"  # Field name for kanji
INPUT_FIELD_READING = "Reading"  # Field name for reading

# Active mode: Set to INPUT_MODE_SINGLE_FIELD or INPUT_MODE_TWO_FIELDS
INPUT_MODE = INPUT_MODE_SINGLE_FIELD
