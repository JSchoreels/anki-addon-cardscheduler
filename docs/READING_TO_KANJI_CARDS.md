# Reading to Kanji Cards

The Reading to Kanji generator creates one note per KANJIDIC onyomi dictionary
reading. Each note asks for the reading and shows the possible kanji, meanings,
grade, frequency, and known vocabulary evidence.

## Source Data

The generator reads vocabulary cards from the configured vocabulary deck. A
vocabulary card is considered known when its stability is greater than `0`.

Known vocabulary is used only as evidence for creating and ordering generated
notes. The answer side still includes all possible KANJIDIC kanji for the
reading after grade filtering, including kanji that do not yet have known
vocabulary examples.

KANJIDIC metadata comes from `kanjidic2_light.xml`:

- `ja_on` readings define the generated Reading field.
- `meaning` values populate the Kanji Meaning field.
- `grade` is used for filtering and ordering.
- `freq` is used for ordering and the Frequency field.

## Reading Matching

Generated cards use dictionary readings and their rendaku variants. Sokuon-final
variants can support a dictionary or rendaku reading, but they do not create
their own Reading card.

For example, a known vocabulary pair `学[がっ]` supports the generated reading
`がく`, but it does not create a generated `がっ` note.

For example, the `実` dictionary onyomi `しつ` also participates in the generated
`じつ` note because `じつ` is the rendaku form of `しつ`.

Known Words are restricted to words where the kanji uses the generated reading
or that reading's sokuon form. Words with different readings for the same kanji
are not included.

Known Words are grouped by kanji and separated with the same comma/full-width
spacing used by the related-word display fields. The generated card template uses
Anki's `furigana:` filter on fields that can contain bracket furigana notation.

## Default Target

By default, generated notes are written to:

```text
<deck_name>::Reading->Kanji
```

The default note type is:

```text
CardScheduler Reading->Kanji
```

If the deck does not exist, it is created. If the note type does not exist, it is
created with these fields:

```text
Reading
Kanji Meaning
Matching Kanji Count
Grade
Frequency
Known Words
```

If the configured note type already exists, missing generated fields are added
without overwriting existing card templates or CSS. The default card template is
added only when the note type is created or when an existing configured note type
has no templates.

The default back template is:

```text
{{FrontSide}}
<hr>
Kanji Count : {{Matching Kanji Count}}
<hr>
Matching Kanjis : {{furigana:Kanji Meaning}}
<hr>
Grade : {{Grade}}
<hr>
Frequency : {{Frequency}}
<hr>
Known Words : {{furigana:Known Words}}
```

## Updates

Generated notes are upserted by their `Reading` field in the target deck and note
type. Each run recomputes:

- possible kanji
- matching kanji count
- meanings
- grade
- frequency
- known words
- card ordering

If duplicate generated notes already exist for the same Reading, that reading is
skipped and reported.

## Ordering

Generated cards are repositioned every run.

Cards are ordered by:

1. Fewer possible kanji for the reading
2. More known supporting words
3. Lower minimum grade
4. Lower best frequency rank
5. Reading text

Kanji inside one note are ordered by:

1. Kanji with known words first
2. More known words
3. Lower grade
4. Lower frequency rank
5. Kanji text

## Configuration

Example Anki add-on config block:

```json
{
  "reading_to_kanji_cards": {
    "deck_name": null,
    "note_type": "CardScheduler Reading->Kanji",
    "max_grade": 8,
    "field_names": {
      "reading": "Reading",
      "kanji_meaning": "Kanji Meaning",
      "matching_kanji_count": "Matching Kanji Count",
      "grade": "Grade",
      "frequency": "Frequency",
      "known_words": "Known Words"
    }
  }
}
```

When `deck_name` is `null`, the add-on uses `<deck_name>::Reading->Kanji`.
