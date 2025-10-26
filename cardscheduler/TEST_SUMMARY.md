# Test Summary for update_kanji_reading_to_cards_with_max_weighted_interval

## Overview
This document describes the test suite for the `update_kanji_reading_to_cards_with_max_weighted_interval` function, which calculates the maximum weighted interval for each kanji-reading pair based on card stability and the number of kanji pairs in each card.

## Test File
`cardscheduler/test_update_max_weighted_interval.py`

## Running the Tests
```bash
cd /Users/jschoreels/workspace/anki-addon-cardscheduler
python -m cardscheduler.test_update_max_weighted_interval
```

## Function Under Test
The function calculates weighted intervals using the formula:
```
weighted_interval = card.stability / 2^(num_kanji_pairs - 1)
```

Then it selects the **maximum** weighted interval among all cards that contain a given kanji-reading pair.

## Test Cases

### 1. test_single_kanji_pair_single_card
Tests the simplest case with one card containing one kanji.
- **Input**: Card with `本[ほん]`, stability=10.0
- **Expected**: max_weighted_interval = 10.0 (10.0 / 2^0)

### 2. test_two_kanji_pairs_single_card
Tests a card with two kanji pairs.
- **Input**: Card with `学校[がっこう]`, stability=20.0
- **Expected**: Both `学[がく]` and `校[こう]` get 10.0 (20.0 / 2^1)

### 3. test_three_kanji_pairs_single_card
Tests a card with three kanji pairs.
- **Input**: Card with `女学校[じょがっこう]`, stability=16.0
- **Expected**: All three kanji pairs get 4.0 (16.0 / 2^2)

### 4. test_four_kanji_pairs_single_card
Tests a card with four kanji pairs.
- **Input**: Card with `東京駅前[とうきょうえきまえ]`, stability=80.0
- **Expected**: All four kanji pairs get 10.0 (80.0 / 2^3)

### 5. test_five_kanji_pairs_exponential_decay
Tests exponential decay with five kanji pairs.
- **Input**: Card with `一二三四五[いちにさんしご]`, stability=160.0
- **Expected**: All five kanji pairs get 10.0 (160.0 / 2^4)

### 6. test_multiple_cards_different_sizes
Tests when the same kanji appears in cards of different sizes.
- **Input**: 
  - `本[ほん]` (1 pair, stability=10.0)
  - `学校[がっこう]` (2 pairs, stability=20.0)
  - `学[がく]` (1 pair, stability=30.0)
- **Expected**: 
  - `本[ほん]`: 10.0
  - `学[がく]`: 30.0 (max of 10.0 and 30.0)
  - `校[こう]`: 10.0

### 7. test_zero_stability_ignored
Tests that cards with zero stability are filtered out.
- **Input**: Two cards both with `本[ほん]`, one with stability=0.0, one with 15.0
- **Expected**: max_weighted_interval = 15.0 (zero stability card ignored)

### 8. test_all_zero_stability_defaults_to_zero
Tests the edge case where all cards have zero stability.
- **Input**: Two cards both with `本[ほん]`, both with stability=0.0
- **Expected**: max_weighted_interval = 0.0

### 9. test_mixed_pair_sizes_max_selection
Tests that the maximum is correctly selected across different card sizes.
- **Input**:
  - `本[ほん]` (1 pair, stability=8.0) → 8.0
  - `本屋[ほんや]` (2 pairs, stability=12.0) → 6.0 per kanji
  - `本当[ほんとう]` (2 pairs, stability=20.0) → 10.0 per kanji
- **Expected**: `本[ほん]` gets max(8.0, 6.0, 10.0) = 10.0

## Key Insights

1. **Exponential Decay**: The weighting decreases exponentially (by powers of 2) as the number of kanji in a card increases.

2. **Max Selection**: When a kanji appears in multiple cards, the function selects the highest weighted interval, favoring simpler contexts.

3. **Zero Stability Handling**: Cards with zero stability are correctly filtered out, with a fallback to 0.0 if all cards have zero stability.

4. **Scalability**: Tests cover 1-5 kanji pairs to verify the algorithm scales correctly.

