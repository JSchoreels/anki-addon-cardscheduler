# Unlock Score Impact Feature

## Overview

This feature enhances the card scheduling algorithm by considering not just HOW MANY cards would be unlocked by learning a kanji, but also THE QUALITY (score) of those unlocked cards.

## New Fields

Three new fields are now computed and stored for each card:

### 1. CardScheduler.UnlockMedianScoreIncrease
**Description**: The median score that unlocked cards would achieve

**Purpose**: Helps prioritize learning kanji that unlock high-value cards (cards with many already-known kanji)

**Example**:
- Card A unlocks 5 cards that would get scores of [10, 20, 30, 40, 50] → median = 30
- Card B unlocks 5 cards that would get scores of [1, 2, 3, 4, 5] → median = 3
- Card A is prioritized because it unlocks higher-value cards

### 2. CardScheduler.ScoreWithoutMissing
**Description**: The score this card would have if we only consider its KNOWN kanji (excluding unknown ones)

**Purpose**: Predicts how valuable this card will be once its missing kanji are learned

**Calculation**: `min(scores of known kanji only)`

**Example**:
- Card contains kanji: 学(unknown), 校(score=50), 生(score=30)
- ScoreWithoutMissing = min(50, 30) = 30
- Once 学 is learned, the card's actual score would be min(simulated, 50, 30)

### 3. CardScheduler.MissingKanjiCount
**Description**: Number of unknown kanji/readings in this card

**Purpose**: Indicates how "close" a card is to being unlockable

**Example**:
- Card "学校" with 学(unknown) and 校(known) → MissingKanjiCount = 1
- Card "学生" with both unknown → MissingKanjiCount = 2
- The first card is closer to being unlocked (needs only 1 kanji learned)

## How It Works

### Step 1: Compute Unlock Potential (Enhanced)

For each unknown kanji/reading pair, we now compute:

1. **unlock_potential**: Count of cards that would be FULLY unlocked (get score > 0)
2. **unlock_median_score_increase**: Median of the "score without missing" for unlocked cards

Example:
```
Unknown kanji: 学[がく]

Cards containing 学:
- 学校 (校 is known with score 50) → would unlock with score=50
- 学生 (生 is known with score 30) → would unlock with score=30
- 大学 (大 is known with score 40) → would unlock with score=40

Result for 学[がく]:
- unlock_potential = 3 cards
- unlock_median_score_increase = median(30, 40, 50) = 40
```

### Step 2: Assign to Cards

For each card, we find the unknown kanji/reading pair with:
- Highest unlock_potential
- If tied, highest unlock_median_score_increase

And assign these values to the card.

### Step 3: Calculate Score Without Missing

For each card with score = 0 (has unknown kanji):
- Find all its kanji
- Take only the KNOWN kanji (interval > 0)
- Calculate score_without_missing = min(known kanji scores)
- Count missing_kanji_count = number of unknown kanji

## New Sorting Priority

Cards are now sorted with the following priority:

1. **Score** (descending) - Higher score = more familiar = learn first
2. **Unlock Potential** (descending) - More cards fully unlocked
3. **Unlock Median Score Increase** (descending) - Higher value unlocks
4. **Missing Kanji Count** (ascending) - Fewer missing kanji (tiebreaker)

### Why This Order?

**Score first**: Always prioritize familiar content

**Unlock Potential second**: Learn kanji that unlock the most cards

**Unlock Median Score Increase third**: Among cards with same unlock potential, prioritize those that unlock higher-value cards

**Missing Kanji Count last**: Final tiebreaker - prefer cards closer to being unlockable

## Example Scenario

Consider two cards with score = 0:

**Card A**: "学校"
- Contains: 学(unknown), 校(score=100)
- ScoreWithoutMissing = 100
- MissingKanjiCount = 1
- Learning 学 unlocks 10 cards with median score 80

**Card B**: "学生会"
- Contains: 学(unknown), 生(score=50), 会(score=60)
- ScoreWithoutMissing = 50
- MissingKanjiCount = 1
- Learning 学 unlocks 10 cards with median score 20

**Result**: Card A is prioritized because:
- Same unlock_potential (10 cards)
- Higher unlock_median_score_increase (80 vs 20)
- This means Card A unlocks higher-value cards

## Benefits

1. **Smarter Prioritization**: Not just quantity of unlocks, but quality matters
2. **Better Learning Path**: Learn kanji that unlock cards you're already familiar with
3. **Visible Progress**: See which cards are close to being unlocked (low MissingKanjiCount)
4. **Strategic Planning**: Understand the value of learning specific kanji

## Configuration

All field names are customizable at the top of `cardscheduler/__init__.py`:

```python
FIELD_NAME_UNLOCK_MEDIAN_SCORE_INCREASE = "CardScheduler.UnlockMedianScoreIncrease"
FIELD_NAME_SCORE_WITHOUT_MISSING = "CardScheduler.ScoreWithoutMissing"
FIELD_NAME_MISSING_KANJI_COUNT = "CardScheduler.MissingKanjiCount"
```

## Technical Implementation

- **Median calculation**: Uses standard median (middle value for odd count, average of two middle for even count)
- **Score without missing**: Only considers kanji with interval > 0 (known)
- **Unlock counting**: Only counts cards where ALL other kanji are known (new_score > 0 after simulation)
