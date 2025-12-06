# CardScheduler Menu Actions

The CardScheduler add-on adds two menu items to Anki's **Tools** menu:

## 1. CardScheduler: Compute Scores

**What it does:**
- Computes familiarity scores for **all cards** based on kanji knowledge
- Calculates unlock potential (how many other cards each word would unlock)
- Assigns learning order positions (1 = highest priority) **only to NEW cards**
- Updates three custom fields in your notes:
  - `CardScheduler.Position` - Learning order (1, 2, 3...) **[NEW cards only, cleared for non-new cards]**
  - `CardScheduler.Score` - Familiarity score **[All cards]**
  - `CardScheduler.UnlockPotential` - Number of cards this would unlock **[All cards]**

**What it does NOT do:**
- Does NOT change the due dates or order of cards in Anki
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

**Use this when:**
- You want new cards presented in the optimal learning order
- You want to learn high-priority cards (known words) first
- You want cards with high unlock potential prioritized

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

## Required Note Fields

Your note type must have these three fields:
- `CardScheduler.Position`
- `CardScheduler.Score`
- `CardScheduler.UnlockPotential`

**To customize field names**, edit the configuration at the top of `cardscheduler/__init__.py`:
```python
FIELD_NAME_POSITION = "CardScheduler.Position"
FIELD_NAME_SCORE = "CardScheduler.Score"
FIELD_NAME_UNLOCK_POTENTIAL = "CardScheduler.UnlockPotential"
```

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
1. Add the three required fields to your note type
2. Run **"Compute Scores"** to verify fields populate correctly
3. Check the browser to see the computed values

**Regular use:**
1. Run **"Compute and Reposition Cards"** when you:
   - Add new cards to the deck
   - Want to refresh the learning order
   - Complete some reviews (scores will have changed)

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
- `reposition_new_cards()` - Handles Anki repositioning
- `update_card_fields()` - Writes to note fields
- `process_collection()` - Orchestrates everything

**Configuration:**
- Deck name: Hardcoded as `"Japan::1. Vocabulary"` in `load_cards()`
- Field names: Configurable via constants at top of file
- Furigana field: Defaults to `"ID"` in `load_cards()`
