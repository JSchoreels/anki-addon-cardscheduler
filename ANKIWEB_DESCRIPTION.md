# CardScheduler

CardScheduler helps order Japanese vocabulary cards so new cards are introduced
when their kanji/readings are already familiar, while still surfacing cards that
unlock many other words.

It works best with vocabulary notes that contain Japanese text with furigana, or
separate kanji and reading fields.

## Features

- Computes a familiarity score for each vocabulary card from known kanji-reading
  pairs.
- Calculates how many other cards each card can help unlock.
- Writes useful browser fields such as score, position, missing kanji count, and
  related known/unknown words.
- Can reposition only new cards according to the computed learning order.
- Can generate Reading -> Kanji cards from readings already supported by known
  vocabulary.

## Menu Actions

After installation, open Anki's **Tools** menu:

- **CardScheduler: Compute Scores**
  Updates CardScheduler fields without changing card due order.

- **CardScheduler: Compute and Reposition Cards**
  Updates fields and reorders new cards. Review and learning cards are not
  repositioned.

- **CardScheduler: Update Reading->Kanji Cards**
  Creates or updates generated Reading -> Kanji cards from known vocabulary.

## Configuration

Open **Tools -> Add-ons**, select **CardScheduler**, then click **Config**.

Common options:

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

- `deck_name`: deck scanned by the add-on.
- `input_mode`: use `two` for separate kanji/reading fields, or `single` for one
  furigana field.
- `input_fields`: field names used by your note type.
- `no_kanji_frequency_type`: `RANK` means lower is better; `FREQUENCY` means
  higher is better.

## Output Fields

Add these fields to your vocabulary note type, or customize their names in the
add-on config:

```text
CardScheduler.Position
CardScheduler.Score
CardScheduler.UnlockPotential
CardScheduler.UnlockMedianScoreIncrease
CardScheduler.ScoreWithoutMissing
CardScheduler.MissingKanjiCount
CardScheduler.Related.Known
CardScheduler.Related.Unknown
CardScheduler.KanjiMeanings
CardScheduler.CardsWithKanji
CardScheduler.CardsWithKanjiKnown
CardScheduler.CardsWithKanjiUnknown
```

If some configured output fields do not exist, the add-on skips those fields and
prints a warning.

## Reading -> Kanji Cards

The generator creates one note per KANJIDIC onyomi dictionary reading when at
least one known vocabulary card supports that reading.

Default config:

```json
{
  "reading_to_kanji_cards": {
    "deck_name": null,
    "note_type": "CardScheduler Reading->Kanji",
    "max_grade": 8
  }
}
```

- `deck_name: null` writes to `<deck_name>::Reading->Kanji`.
- `max_grade` filters KANJIDIC grades; the default includes grades 1-8.
- Generated cards include possible kanji, meanings, grade, frequency, matching
  kanji count, and known vocabulary examples.
- Existing generated note templates and CSS are preserved.

Generated Reading -> Kanji cards are reordered each run so readings with fewer
matching kanji appear first.

## Notes

- Repositioning affects only new cards.
- KANJIDIC grade and frequency metadata come from the bundled light dictionary.
- Known vocabulary means cards with stability greater than zero.
