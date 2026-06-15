# Sentence Scoring

Sentence scoring assigns familiarity fields to sentence notes using reviewed
vocabulary evidence first, then kanji-reading evidence as a fallback.

For local performance measurements, see
[Sentence Score Benchmark](SENTENCE_SCORE_BENCHMARK.md).

## Data Read

- Vocabulary cards are read from `deck_name`, using the configured input mode and
  input fields.
- Sentence cards are read from `sentence_scoring.deck_names`.
- Sentence notes are restricted to `sentence_scoring.note_type`.
- Sentence text is read from `sentence_scoring.sentence_field`.
- MeCab tokenizes sentence text and vocabulary fronts. Only tokens containing
  kanji are scored.

Default sentence configuration:

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

## Fields Updated

Missing fields are added to the sentence note type before writing scores.

- `CardScheduler.Position`
- `CardScheduler.SentenceStrictScore`
- `CardScheduler.SentencePredictedScore`
- `CardScheduler.SentenceMissingWords`
- `CardScheduler.SentenceInferredWords`
- `CardScheduler.SentenceKanjiWordCount`
- `CardScheduler.SentencePriorityScore`

Because Anki fields belong to notes, a sentence note with multiple cards receives
one shared set of sentence fields.

`CardScheduler.Position` is the global sentence rank for every sentence note.
Repositioning still only moves Anki cards that are currently new.

## Score Rules

`SentenceStrictScore` uses reviewed vocabulary cards only.

```text
SentenceStrictScore = min(reviewed word interval per kanji word)
```

If any kanji word has no reviewed vocabulary evidence, strict score is `0`.

`SentencePredictedScore` uses reviewed vocabulary cards first. Missing reviewed
word evidence falls back to the current kanji-reading component score for that
sentence token.

```text
SentencePredictedScore = min(reviewed word interval or component score per kanji word)
```

`SentenceMissingWords` counts kanji words without reviewed vocabulary evidence.

`SentenceInferredWords` counts missing words that still received a non-zero
component score.

`SentenceKanjiWordCount` counts MeCab tokens containing kanji. It is used as a
final tie-breaker so shorter or less dense sentences come first when the
readiness scores are otherwise equal.

`SentencePriorityScore` is a rank score from `0` to `100`, where `100` is the
highest priority sentence after sorting by:

1. `SentenceStrictScore` descending
2. `SentencePredictedScore` descending
3. `SentenceMissingWords` ascending
4. `SentenceInferredWords` ascending
5. `SentenceKanjiWordCount` ascending

## Reading Ambiguity

Vocabulary matching uses surface, lemma, and reading. Lemma-only matching is only
accepted when that lemma has one reading in the vocabulary index. If the lemma has
multiple readings, the sentence token reading must match a vocabulary reading.

For example, `風` can be `かぜ` or `ふう`. Knowing `風[かぜ]` does not give reviewed
word credit for a `ふう` sentence token.

## MeCab

Sentence scoring requires a working `mecab` command. The add-on checks:

- `mecab`
- `/usr/local/bin/mecab`
- `/opt/homebrew/bin/mecab`

If MeCab is unavailable or tokenization fails, sentence scores are not updated
and a warning is logged/shown.
