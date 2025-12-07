# Simulation Mode: Zero Stability

## Overview

Simulation mode allows you to see what the optimal learning order would be if you were starting from scratch with no existing knowledge.

**Compatibility**: Works with both FSRS (stability-based) and SM-2 (interval-based) schedulers. The addon automatically detects which scheduler you're using and uses the appropriate metric (stability or interval).

This is useful for:

1. **Understanding the algorithm** - See how cards would be prioritized based purely on unlock potential and card complexity
2. **Planning a fresh start** - If you want to reset and start learning vocabulary from scratch
3. **Comparing strategies** - See how different the order is compared to your current progress

## How to Enable

Edit the configuration at the top of `cardscheduler/__init__.py`:

```python
# Configuration: Simulation mode
# When True, all cards are treated as having zero stability (simulates starting from scratch)
# This shows what the optimal learning order would be if you had no progress
SIMULATE_ZERO_STABILITY = False  # Change to True to enable
```

## What Changes in Simulation Mode

When `SIMULATE_ZERO_STABILITY = True`:

1. **All cards treated as new**: Every card is treated as if it has zero stability (never been studied) and gets a position assigned
2. **All scores become zero**: Since no kanji are known, all cards start with score = 0
3. **All cards get positions**: Unlike normal mode where only "new" cards get positions, in simulation mode ALL cards receive position numbers (1 through N)
4. **Sorting by unlock potential**: Cards are sorted purely by:
   - Unlock potential (how many other cards learning this kanji would unlock)
   - Unlock median score increase
   - Missing kanji count
   - Kanji count (simpler words first)
   - Kana count (shorter words first)
   - Score without missing (final tiebreaker)

## Example Output

When simulation mode is enabled, you'll see:

```
============================================================
SIMULATION MODE: All cards treated as having ZERO stability
This shows the optimal learning order starting from scratch
============================================================

Cards sorted by learning order position:
============================================================
Pos:     1 | Score:      0.0 | ID: 一[いち]                   | Unknown: 1 | Unlock:  25 | ...
Pos:     2 | Score:      0.0 | ID: 二[に]                    | Unknown: 1 | Unlock:  18 | ...
Pos:     3 | Score:      0.0 | ID: 三[さん]                   | Unknown: 1 | Unlock:  12 | ...
...
```

## How It Works

The simulation mode is implemented by:

1. **`SIMULATE_ZERO_STABILITY` flag**: Global configuration constant
2. **`get_card_stability(card, simulate_zero)` function**: Externalized stability retrieval
   - If `simulate_zero=True`, always returns 0
   - If `simulate_zero=False`, returns actual card stability
3. **`load_cards()` function**: Uses `get_card_stability()` to load cards with the appropriate stability

## Use Cases

### Use Case 1: Understand the Algorithm
Enable simulation mode to see which cards the algorithm considers most foundational:

```python
SIMULATE_ZERO_STABILITY = True
```

Run the addon and observe which cards get the highest priority (position 1, 2, 3...). These are the cards that:
- Unlock the most other cards
- Use common kanji that appear in many words
- Are simpler (fewer kanji, shorter words)

### Use Case 2: Compare with Current Progress
Run the addon twice:

1. First with `SIMULATE_ZERO_STABILITY = False` (normal mode)
   - Save/note the top 20 positions
2. Then with `SIMULATE_ZERO_STABILITY = True` (simulation mode)
   - Compare the top 20 positions

This shows you how your current knowledge has shifted your learning priorities.

### Use Case 3: Fresh Start Planning
If you're considering resetting your deck or starting fresh:

1. Enable simulation mode
2. Export the positions to see the optimal order
3. Use this as a learning roadmap

## Technical Details

### Code Structure

```python
# Configuration
SIMULATE_ZERO_STABILITY = False

# Stability retrieval (externalized with fallback to interval)
def get_card_stability(card, simulate_zero=False):
    if simulate_zero:
        return 0

    # Try stability from FSRS (newer Anki)
    if card.memory_state and hasattr(card.memory_state, 'stability'):
        return card.memory_state.stability

    # Fall back to interval (SM-2 and older schedulers)
    if hasattr(card, 'ivl'):
        return max(0, card.ivl)

    return 0

# Loading cards with simulation support
def load_cards(collection, simulate_zero_stability=SIMULATE_ZERO_STABILITY):
    for cid in all_cids:
        card = collection.get_card(cid)
        stability = get_card_stability(card, simulate_zero=simulate_zero_stability)
        cards.append(CardInfo(card.id, furigana_text, stability))
    return cards

# In process_collection: treat all cards as new in simulation mode
if SIMULATE_ZERO_STABILITY:
    new_cids = set(c.card_id for c in cards)  # All cards
else:
    new_cids = set(collection.find_cards('"deck:Japan::1. Vocabulary" is:new'))  # Only new cards
```

### Impact on Sorting

In simulation mode, since all cards have score = 0, the sorting priority becomes:

1. ~~Score~~ (all tied at 0)
2. **Unlock Potential** - More cards unlocked
3. **Unlock Median Score Increase** - Higher value unlocks
4. **Missing Kanji Count** - Fewer missing
5. **Kanji Count** - Fewer kanji (simpler)
6. **Kana Count** - Fewer kana (shorter)
7. **Score Without Missing** - Lower score needs more help

This creates a pure "unlock potential first" strategy, prioritizing foundational vocabulary.

## Limitations

1. **Does not update Anki cards**: Simulation mode only affects the display and calculated positions. It doesn't modify your actual card scheduling in Anki (unless you run with reposition enabled).

2. **All cards treated equally**: Even cards you've mastered are treated as completely new, which may not reflect your actual knowledge.

3. **No partial knowledge**: The simulation is binary (0 or actual stability), not a gradient.

## Disabling Simulation Mode

Simply set the flag back to `False`:

```python
SIMULATE_ZERO_STABILITY = False
```

And restart Anki or reload the addon.
