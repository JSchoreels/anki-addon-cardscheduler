# Configuration

CardScheduler is configured through Anki's add-on config screen.

Open **Tools → Add-ons**, select **CardScheduler**, then click **Config**. Anki
edits the add-on `config.json` values and keeps your overrides in your Anki
profile.

## Common Settings

```json
{
  "deck_name": "Japan::1. Vocabulary",
  "input_mode": "two",
  "input_fields": {
    "single": "ID",
    "kanji": "Front",
    "reading": "Reading"
  },
  "no_kanji_frequency_field": "Frequency",
  "no_kanji_frequency_type": "RANK"
}
```

- `deck_name`: vocabulary deck scanned by the scheduler.
- `input_mode`: `two` uses separate kanji and reading fields; `single` uses one
  furigana field.
- `input_fields`: field names used by the selected input mode.
- `no_kanji_frequency_type`: `RANK` means lower is better; `FREQUENCY` means
  higher is better.

## Reading to Kanji Cards

```json
{
  "reading_to_kanji_cards": {
    "deck_name": "Japan::4. Recall::Reading->Kanji",
    "note_type": "CardScheduler Reading->Kanji",
    "max_grade": 8
  }
}
```

- `deck_name`: target deck. `null` means `<deck_name>::Reading->Kanji`.
  The shipped default is `Japan::4. Recall::Reading->Kanji`.
- `note_type`: note type for generated Reading → Kanji cards.
- `max_grade`: only include kanji with this KANJIDIC grade or lower.

Existing generated note templates and CSS are preserved. Missing generated fields
are added when needed.

## Sentence Scoring

```json
{
  "sentence_scoring": {
    "deck_names": [
      "Japan::2. Sentences",
      "Japan::3. Audio"
    ],
    "note_type": "Japanese Sentence Card",
    "sentence_field": "Sentence"
  }
}
```

- `deck_names`: decks scanned for sentence/audio cards.
- `note_type`: sentence note type to score.
- `sentence_field`: field tokenized by MeCab.

Sentence scoring adds missing `CardScheduler.Sentence*` fields to the configured
note type before updating values. See [Sentence Scoring](SENTENCE_SCORING.md) for
the field meanings and matching rules.

Outside Anki, development scripts can still use `cardscheduler/config.json`.
