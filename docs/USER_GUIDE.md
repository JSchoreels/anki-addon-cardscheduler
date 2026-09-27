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

**Settings**
- Opens a native UI for every CardScheduler option
- Also available from Add-ons → CardScheduler → Config
- Requires a full Anki restart after saving

**Compute Scores**
- Updates all score fields
- Does NOT change card order

**Compute and Reposition Cards**
- Updates all score fields
- Reorders NEW cards by optimal learning order

### Automatic Processing

By default, opening an Anki profile and entering a new scheduler day each
schedule one background refresh after a short delay. The triggers can be enabled
independently. Reviews and note additions do not run the processor. The automatic
refresh updates scores, related words, kanji meanings, and the new-card order
according to the checkboxes in **CardScheduler: Settings**. It is skipped when
nothing in the vocabulary deck, the settings, or the add-on changed since the
last refresh.

Reading→Kanji generation and sentence scoring remain manual.

**Compute Sentence Scores**
- Updates sentence score fields and global sentence positions
- Does NOT change card order

**Compute and Reposition Sentence Cards**
- Updates sentence score fields
- Reorders NEW sentence cards by sentence priority

### Recommended Workflow

1. Add required fields to your note type
2. Open **CardScheduler: Settings** and verify the deck and input fields
3. Fully quit and reopen Anki after saving settings
4. Let the startup refresh complete
5. Use the manual actions whenever you want an extra refresh during the day

## How Scoring Works

```
Base score = min(weighted_interval of each canonical kanji-reading family)
Card score = base score × contextual reading-ambiguity factor
```

- Rendaku and sokuon forms share evidence with their canonical reading instead
  of being treated as completely unrelated readings.
- A family used almost evenly across multiple forms receives a larger handicap
  than a family dominated by one form.
- Visible syntax and phonology can lift the handicap. For example, a separate
  noun after an adjective blocks rendaku, and a word-final reading cannot end in
  a lexical sokuon.
- Sokuon receives partial relief when the following voiceless K/S/T/P onset and
  the observed same-token examples make the realization predictable. Voiced
  G/Z/D/B onsets are kept separate.
- Unknown kanji still leave the persisted score at `0`. For ordering only, those
  cards receive a positive shadow priority derived from their existing fallback
  metrics and multiplied by the same ambiguity factor. They remain below every
  card with genuine positive familiarity evidence.

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
