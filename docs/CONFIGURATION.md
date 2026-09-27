# Configuration

CardScheduler provides a native settings dialog for every supported option.

Open it from either location:

- **Tools → CardScheduler: Settings**
- **Tools → Add-ons → CardScheduler → Config**

Select **Save**, then fully quit and reopen Anki. CardScheduler loads its
configuration when the add-on starts, so a restart is required before new
values are used.

Single-deck settings are editable dropdowns populated from the current Anki
collection. Field settings are editable dropdowns populated from every field
available on the installed note types. You can still type a custom value when a
deck or field has not been created yet. The sentence-deck setting remains a
multi-line list because sentence scoring can target several decks at once.

## General

| Setting | Purpose |
|---|---|
| Vocabulary deck | Root deck scanned for vocabulary cards; child decks are included. |
| Input mode | Use one furigana field or separate surface/reading fields. |
| Single furigana field | Field containing text such as `学校[がっこう]`. |
| Kanji/surface field | Written form used by two-field mode, such as `学校`. |
| Reading field | Kana reading used by two-field mode, such as `がっこう`. |
| Simulation mode | Treat every vocabulary card as new when calculating positions. |
| Kana-only card placement | Put kana-only cards before, after, or interleaved with kanji cards. |
| Kana-only frequency field | Optional rank/frequency field used to order kana-only cards. |
| Kana-only frequency interpretation | Treat the value as a rank (lower is better) or frequency (higher is better). |

## Automatic Processing

Automatic processing uses Anki's profile-open and scheduler-day-change hooks.
Each trigger can be enabled independently. Reviewing cards and adding notes do
not trigger processing.

| Setting | Purpose |
|---|---|
| Enable automatic processing | Turns all scheduled processing on or off. |
| Run after opening a profile | Runs once shortly after Anki opens a profile, including application startup. |
| Run on a new scheduler day | Runs once when an open Anki session advances to its next scheduler day. |
| Refresh scores | Updates score, unlock, familiarity, missing-kanji, and position fields. |
| Refresh related words | Updates known/unknown related words and kanji meanings. |
| Reposition new cards | Recalculates and applies the exact order of all new vocabulary cards. |
| Delay | Time to wait after either lifecycle event before starting the refresh. |

Score and reposition processing use the complete vocabulary deck so new and
existing cards remain consistent. The refresh runs in the background without a
progress window: only loading the deck and saving fields briefly use the
collection, so Anki and other add-ons are not held up while scores are
computed. A tooltip appears once fields have been saved.

The refresh is skipped when nothing it depends on changed since the last
completed one: the vocabulary deck's cards and notes (reviews, edits, FSRS
updates, additions and deletions), note types, the add-on settings, and the
add-on code. The last state is remembered per profile in
`user_files/refresh_state.json`; deleting it forces the next refresh.

Reading→Kanji generation and sentence scoring stay manual because they create
or update separate card collections.

Repositioning inherently refreshes scores, even if the separate score toggle is
off, because the position order is calculated from those scores.

## Vocabulary Output Fields

The **Vocabulary fields** tab controls every field written by score and related
word processing:

- position
- score
- unlock potential
- unlock median score increase
- score without missing kanji
- missing kanji count
- related known words
- related unknown words
- kanji meanings
- cards sharing kanji
- known cards sharing kanji
- unknown cards sharing kanji

The configured fields must exist on a vocabulary note type to receive values.
Different note types in the vocabulary deck may expose different subsets.

## Reading → Kanji

The **Reading → Kanji** tab configures:

- target deck; blank uses `<vocabulary deck>::Reading->Kanji`
- generated note type
- maximum KANJIDIC grade
- Reading field
- Kanji Meaning field
- Matching Kanji Count field
- Grade field
- Frequency field
- Known Words field

Existing generated templates and CSS are preserved. Missing generated fields
are added when required by the manual Reading→Kanji action.

## Sentence Scoring

The **Sentences** tab configures:

- one or more sentence decks, one per line
- sentence note type
- source sentence field
- strict score field
- predicted score field
- missing words field
- inferred words field
- kanji word count field
- priority score field

Sentence processing adds missing output fields to the configured sentence note
type. See [Sentence Scoring](SENTENCE_SCORING.md) for the matching and scoring
rules.

## JSON and Development Fallback

The dialog writes the same configuration that Anki stores for the add-on. The
standard JSON shape remains supported for development and manual inspection; the
complete defaults are in `cardscheduler/config.json.example`.

Outside Anki, scripts load `cardscheduler/config.json` when that file exists and
otherwise use the built-in defaults.
