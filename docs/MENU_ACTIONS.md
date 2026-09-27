# CardScheduler Menu Actions

The CardScheduler add-on adds these menu items to Anki's **Tools** menu:

## CardScheduler: Settings

Opens the native tabbed settings dialog. It covers the vocabulary deck and
input mode, automatic processing, every output field, Reading→Kanji generation,
and sentence scoring. The same dialog opens from **Add-ons → CardScheduler →
Config**. Fully quit and reopen Anki after saving.

## Scheduled Automatic Processing

When enabled, opening an Anki profile or entering a new scheduler day can start
one background refresh. Each lifecycle trigger is independently configurable.
Reviews and note additions do not start processing. The enabled automation
options can refresh score fields, related words and kanji meanings, and the exact
new-card order.

Reading→Kanji generation and sentence scoring remain manual because they update
separate decks and note types.

## 1. CardScheduler: Compute Scores

**What it does:**
- Computes familiarity scores for **all cards** from canonical kanji-reading
  knowledge and context-sensitive rendaku/sokuon ambiguity
- Calculates unlock potential (how many other cards each word would unlock)
- Assigns learning order positions (1 = highest priority) **only to NEW cards**
- Applies ambiguity to the fallback priority of score-zero kanji cards without
  promoting them above cards with positive familiarity evidence
- Updates three custom fields in your notes:
  - `CardScheduler.Position` - Learning order (1, 2, 3...) **[NEW cards only, cleared for non-new cards]**
  - `CardScheduler.Score` - Familiarity score **[All cards]**
  - `CardScheduler.UnlockPotential` - Number of cards this would unlock **[All cards]**
  - score-supporting metric fields such as missing kanji count, score without
    missing kanji, unlock median score increase, and cards sharing kanji

**What it does NOT do:**
- Does NOT change the due dates or order of cards in Anki
- Does NOT update related-word display fields
- Does NOT generate Reading -> Kanji cards
- Only updates the note fields for reference
- Does NOT assign positions to cards that are already being reviewed or learned (clears their Position field instead)

**Use this when:**
- You want to see the computed metrics without affecting your review queue
- You want to update the fields for filtering/sorting in the browser

---

## 2. CardScheduler: Compute and Reposition Cards

**What it does:**
- Everything from "Compute Scores" (above)
- **PLUS**: Repositions NEW cards based on the computed learning order
- Sets the due queue position of new cards to match `CardScheduler.Position`
- Shifts existing new cards to make room for repositioned cards

**What it affects:**
- **Only affects cards in the "new" state**
- Does NOT affect cards you're currently reviewing or already learned
- Changes the order in which new cards will be introduced
- May shift other new cards in the queue to maintain sequential order
- Does NOT update related-word display fields
- Does NOT generate Reading -> Kanji cards

**Use this when:**
- You want new cards presented in the optimal learning order
- You want to learn high-priority cards (known words) first
- You want cards with high unlock potential prioritized

---

## 3. CardScheduler: Compute Related Words

**What it does:**
- Computes cards that share kanji with each vocabulary card
- Splits related cards into known and unknown groups
- Updates related display fields:
  - `CardScheduler.Related.Known`
  - `CardScheduler.Related.Unknown`
  - `CardScheduler.KanjiMeanings`

**What it does NOT do:**
- Does NOT update score or position fields
- Does NOT reposition cards
- Does NOT generate Reading -> Kanji cards

**Use this when:**
- You want to refresh related-word examples after adding or reviewing cards
- You changed related-word or kanji-meaning display fields

---

## 4. CardScheduler: Update Reading->Kanji Cards

**What it does:**
- Scans known vocabulary cards in the configured vocabulary deck
- Creates or updates one generated note per KANJIDIC onyomi dictionary reading
- Writes possible kanji, meanings, grade, frequency, and known vocabulary examples
- Creates the target deck and note type when they do not exist
- Repositions generated cards every run by reading ambiguity

**Default target:**
- Deck: `<deck_name>::Reading->Kanji`
- Note type: `CardScheduler Reading->Kanji`

**Ordering:**
- Readings with fewer possible kanji come first
- Ties prefer more known vocabulary evidence, lower grade, and lower frequency rank

See [Reading to Kanji Cards](READING_TO_KANJI_CARDS.md) for the full data rules.

---

## 5. CardScheduler: Compute Sentence Scores

**What it does:**
- Tokenizes configured sentence notes with MeCab
- Scores sentence notes from reviewed vocabulary evidence
- Writes strict score, predicted score, missing words, inferred words, and
  kanji word count, and priority score
- Adds missing sentence score fields to the configured sentence note type
- Updates `CardScheduler.Position` for all sentence notes

**What it does NOT do:**
- Does NOT reposition cards
- Does NOT change vocabulary scores
- Does NOT generate Reading -> Kanji cards

See [Sentence Scoring](SENTENCE_SCORING.md) for the full data rules.

---

## 6. CardScheduler: Compute and Reposition Sentence Cards

**What it does:**
- Everything from "Compute Sentence Scores"
- **PLUS**: Repositions NEW sentence cards by sentence priority

**What it affects:**
- Only affects cards in the "new" state
- Updates sentence fields on the note, so audio cards sharing the same note see
  the same sentence score fields

---

## 7. CardScheduler: Compute Scores, Related Words, Reposition Cards, Generate Reading Cards, Sentence Scores

**What it does:**
- Runs **Compute Scores**
- Runs **Compute Related Words**
- Repositions new vocabulary cards
- Computes sentence scores and repositions new sentence cards
- Generates or updates Reading -> Kanji cards

**Use this when:**
- You want the complete CardScheduler refresh in one action
- You added cards or completed reviews and want every generated field/deck updated

---

## How the Learning Order Works

**Position Assignment:**
1. **Position 1-N (High Scores)**: Well-known cards come first
2. **For cards with same score**: Higher unlock potential = lower position (higher priority)
3. **Sequential numbering**: 1, 2, 3, 4... (no gaps)

**Example:**
```
Position 1:  一年[いちねん]      Score: 50.0  (very familiar)
Position 2:  二年[にねん]        Score: 40.0  (familiar)
Position 3:  年月[ねんげつ]      Score: 30.0  (somewhat familiar)
Position 4:  三年[さんねん]      Score: 0.0   Unlock: 5 (unlocks 5 other cards)
Position 5:  四年[よねん]        Score: 0.0   Unlock: 3 (unlocks 3 other cards)
Position 6:  五年[ごねん]        Score: 0.0   Unlock: 1 (unlocks 1 card)
```

---

## Note Fields

Score actions update these fields when they exist:
- `CardScheduler.Position`
- `CardScheduler.Score`
- `CardScheduler.UnlockPotential`
- `CardScheduler.UnlockMedianScoreIncrease`
- `CardScheduler.ScoreWithoutMissing`
- `CardScheduler.MissingKanjiCount`
- `CardScheduler.CardsWithKanji`
- `CardScheduler.CardsWithKanjiKnown`
- `CardScheduler.CardsWithKanjiUnknown`

Related-word actions update these fields when they exist:
- `CardScheduler.Related.Known`
- `CardScheduler.Related.Unknown`
- `CardScheduler.KanjiMeanings`

Sentence score actions add missing fields to the sentence note type, then update:
- `CardScheduler.Position`
- `CardScheduler.SentenceStrictScore`
- `CardScheduler.SentencePredictedScore`
- `CardScheduler.SentenceMissingWords`
- `CardScheduler.SentenceInferredWords`
- `CardScheduler.SentenceKanjiWordCount`
- `CardScheduler.SentencePriorityScore`

To customize field names, update the add-on configuration described in
[Configuration](CONFIGURATION.md).

---

## How Repositioning Works

When you use **"Compute and Reposition Cards"**:

1. Computes optimal learning order (position 1, 2, 3...)
2. Identifies all NEW cards in the deck `"Japan::1. Vocabulary"`
3. Sets each new card's due position to match its computed position
4. Cards are now queued in optimal order for learning

**Technical details:**
- Uses Anki's scheduler `reposition_new_cards()` method (requires Anki v2.1.50+)
- Only affects cards in "new" state (not reviewing, not learned)
- Uses `shift_existing=True` to maintain queue integrity

---

## Workflow Recommendation

**First time setup:**
1. Add the fields you want CardScheduler to update to your note type
2. Run **"Compute Scores"** to verify fields populate correctly
3. Check the browser to see the computed values

**Regular use:**
1. Leave the desired startup and new-day triggers enabled to refresh vocabulary
   fields at predictable boundaries.
2. Run **"Compute and Reposition Cards"** manually when you:
   - Add new cards to the deck
   - Want to refresh the learning order
   - Complete some reviews (scores will have changed)
3. Run **"Compute Related Words"** when you want a manual related-field refresh.
4. Run the full workflow action when you want score fields, related fields, card
   ordering, and Reading -> Kanji cards refreshed together.

**Frequency:**
- Weekly: Good balance between freshness and stability
- After adding 50+ new cards: Ensures new content is optimally ordered
- When changing study focus: Recompute to adjust priorities

---

## Troubleshooting

**Fields not updating:**
- Check that your note type has the exact field names
- Check console output for "Field not found" warnings
- Verify you're using the correct deck name in `load_cards()`

**Repositioning not working:**
- Only affects NEW cards (check card state)
- Check that cards are in the target deck
- Verify Anki has write permissions

**Unexpected order:**
- Position 1 = highest score (most familiar)
- Check unlock potential values for tie-breaking
- Review console output showing positions

---

## Developer Notes

**Key functions:**
- `compute_scores()` - Main computation logic
- `process_related_words()` - Computes and writes related display fields
- `reposition_new_cards()` - Handles Anki repositioning
- `update_card_fields()` - Writes to note fields
- `process_collection()` - Orchestrates score computation and optional repositioning
- `process_all_features()` - Runs the full menu workflow

**Configuration:**
- Deck name: configured by `deck_name`
- Field names: configured by `field_names`
- Input fields: configured by `input_fields`
