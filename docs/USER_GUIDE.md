# CardScheduler User Guide

## What It Does

Prioritizes Japanese vocabulary cards based on:
- **Kanji familiarity** - Cards with known kanji readings are learned first
- **Unlock potential** - Cards that unlock other cards are prioritized
- **Complexity** - Simpler words (fewer kanji) are preferred
- **Sentence familiarity** - Sentence notes are scored from reviewed vocabulary
  and kanji-reading familiarity

## Prerequisites

### 1. Deck Name

Default: `Japan::1. Vocabulary`

Configure in `config.json` (see Configuration section).

### 2. Input Field (choose one)

**Option A: Single field with furigana** (default)
```
Field "ID": 学校[がっこう]
```

**Option B: Two separate fields**
```
Field "Front": 学校
Field "Reading": がっこう
```

Configure in `config.py`:
```python
INPUT_MODE = INPUT_MODE_SINGLE_FIELD  # or INPUT_MODE_TWO_FIELDS
```

### 3. Output Fields

Add these fields to your note type:

| Field | Description |
|-------|-------------|
| `CardScheduler.Position` | Learning order (1 = highest priority) |
| `CardScheduler.Score` | Familiarity score |
| `CardScheduler.UnlockPotential` | Cards unlocked by learning this |
| `CardScheduler.Related.Known` | Related known words |
| `CardScheduler.Related.Unknown` | Related unknown words |
| `CardScheduler.KanjiMeanings` | Meanings of each kanji |

Optional fields:
- `CardScheduler.UnlockMedianScoreIncrease`
- `CardScheduler.ScoreWithoutMissing`
- `CardScheduler.MissingKanjiCount`
- `CardScheduler.CardsWithKanji`
- `CardScheduler.CardsWithKanjiKnown`
- `CardScheduler.CardsWithKanjiUnknown`
- `CardScheduler.SentenceStrictScore`
- `CardScheduler.SentencePredictedScore`
- `CardScheduler.SentenceMissingWords`
- `CardScheduler.SentenceInferredWords`
- `CardScheduler.SentenceKanjiWordCount`
- `CardScheduler.SentencePriorityScore`

## Usage

### Menu: Tools > CardScheduler

**Compute Scores**
- Updates all score fields
- Does NOT change card order

**Compute and Reposition Cards**
- Updates all score fields
- Reorders NEW cards by optimal learning order

**Compute Sentence Scores**
- Updates sentence score fields and global sentence positions
- Does NOT change card order

**Compute and Reposition Sentence Cards**
- Updates sentence score fields
- Reorders NEW sentence cards by sentence priority

### Recommended Workflow

1. Add required fields to your note type
2. Run "Compute Scores" to verify setup
3. Run "Compute and Reposition Cards" to reorder new cards
4. Re-run periodically after reviews (weekly or after adding cards)

## How Scoring Works

```
Card Score = min(weighted_interval of each kanji-reading pair)
```

- Known kanji → higher score → learn first
- Unknown kanji → score = 0 → sorted by unlock potential

## Configuration

Copy `config.json.example` to `config.json` and edit:

```json
{
  "deck_name": "Your::Deck::Name",
  "input_mode": "single",
  "input_fields": {
    "single": "Expression",
    "kanji": "Front",
    "reading": "Reading"
  },
  "simulate_zero_stability": false
}
```

Only include settings you want to change. Missing values use defaults.

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Fields not updating | Check exact field names match |
| No cards processed | Check `deck_name` in config.json |
| Wrong card order | Run "Compute and Reposition Cards" |
