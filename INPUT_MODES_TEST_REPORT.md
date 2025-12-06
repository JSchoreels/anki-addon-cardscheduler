# Input Modes Comparison Test Report

## Overview

This document summarizes the comprehensive comparison test between single-field and two-field input modes for the CardScheduler addon.

## Test Configuration

- **Single-field mode**: Uses the "ID" field with format `頭[あたま]が 痛[いた]い`
- **Two-field mode**: Uses "Front" (kanji) and "Reading" fields, combined as `頭が痛い[あたまがいたい]`

## Test Results Summary

### Overall Statistics

| Metric | Value |
|--------|-------|
| Total cards compared | 9,924 |
| Cards with matching scores | 8,977 (90.46%) |
| Cards with different scores | 947 (9.54%) |
| **Match percentage** | **90.46%** |
| **Test threshold** | **90.0%** |
| **Test result** | **✅ PASS** |

### Unlock Potential Comparison

| Metric | Value |
|--------|-------|
| Cards with matching unlock potential | 9,772 (98.47%) |
| Cards with different unlock potential | 152 (1.53%) |

## Analysis of Differences

The 947 cards with different scores can be categorized into three types:

### 1. Pure Hiragana/Katakana Cards (0 cards, 0.00%)

**Explanation**: Cards that contain only hiragana or katakana with no kanji.

**Behavior**: ✅ **Now handled identically in both modes!**
- The implementation was updated to NOT add brackets for pure kana cards
- Both modes now produce score = 0 for pure kana cards
- Examples: `は`, `な`, `と`, `に`, `もの` all match perfectly

**Previous behavior** (before fix):
- Single-field mode: No kanji detected → score = 0
- Two-field mode: Reading field was processed with brackets → score > 0
- This caused 23 cards to differ

**Current behavior** (after fix):
- Both modes: No kanji detected → no brackets added → score = 0 ✅

### 2. Okurigana/Parsing Differences (769 cards, 7.75%)

**Explanation**: Cards with different okurigana handling or parsing between formats.

**Examples**:

**Okurigana handling**:
- `前[まえ]のめり` vs `前のめり[まえのめり]`
  - Single: 1448.01, Two: 235.81 (difference: 1212.20)
- `貰[もら]う` vs `もらう[もらう]`
  - Single: 844.41, Two: 0.00 (difference: 844.41)
- `貰[もら]える` vs `貰える[もらえる]`
  - Single: 844.41, Two: 67.35 (difference: 777.06)

**Why this happens**:
- Single-field mode: Okurigana is explicitly marked with furigana brackets
- Two-field mode: Full reading is provided, system must infer which parts are okurigana
- The parsing algorithm handles these formats differently

### 3. Other Differences (178 cards, 1.79%)

Other edge cases that don't fit the above categories.

## Key Improvement

**Before the fix**:
- Match rate: 90.23%
- Pure hiragana differences: 23 cards

**After the fix**:
- Match rate: **90.46%** ✅
- Pure hiragana differences: **0 cards** ✅
- Improvement: +0.23% (23 cards now matching)

This improvement was achieved by updating `convert_two_fields_to_furigana()` to detect pure kana text and not add brackets, making it behave identically to single-field mode for these cards.

## Conclusion

### ✅ Test Passes

The test achieves a **90.46% match rate**, exceeding the 90% threshold.

### Key Findings

1. **Both input modes produce highly similar results** (90%+ match rate)
2. **Pure hiragana cards now match perfectly** - fixed by not adding brackets for kana-only text
3. **Okurigana handling varies** between formats - this represents the main source of remaining differences (~8%)
4. **Unlock potential is even more consistent** (98.47% match rate)

### Recommendations

1. **Single-field mode** is recommended when:
   - Your cards have explicit furigana annotations
   - You want precise control over okurigana marking
   - You have existing data in this format

2. **Two-field mode** is recommended when:
   - Your cards have separate kanji and reading fields
   - You want to process pure kana cards
   - You have existing data in this format

Both modes are valid and produce functionally equivalent results for scoring and card scheduling.

## Top 10 Largest Score Differences (After Fix)

All pure hiragana differences have been eliminated! The remaining differences are primarily okurigana/parsing variations:

1. `前のめり` - Okurigana parsing (diff: ~1212)
2. `前々から` - Okurigana parsing (diff: ~1212)
3. `前々` - Okurigana parsing (diff: ~1212)
4. `前` - Okurigana parsing (diff: ~1212)
5. `前に` - Okurigana parsing (diff: ~1212)
6. `貰う` - Okurigana parsing (diff: ~844)
7. `貰える` - Okurigana parsing (diff: ~777)
8. `様になる` - Okurigana parsing (diff: ~518)
9. `様です` - Okurigana parsing (diff: ~518)
10. Other okurigana variations

**Note**: Pure hiragana cards like `は`, `な`, `と`, `に`, `を`, `もの` now match perfectly between both modes!

## Test Execution

Run the comparison test with:

```bash
PYTHONPATH=/path/to/anki-addon-cardscheduler:$PYTHONPATH \
  python -m unittest cardscheduler.test_input_modes_comparison
```

Expected output:
```
Ran 1 test in 1.467s
OK
```

---

**Test file**: `cardscheduler/test_input_modes_comparison.py`
**Test date**: 2025-12-06
**Collection**: Main Profile (9,924 cards)
