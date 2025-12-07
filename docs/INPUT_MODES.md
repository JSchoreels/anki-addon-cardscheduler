# Input Mode Configuration

The CardScheduler addon supports two different input field configurations for extracting kanji and readings from your Anki cards.

## Configuration Options

Edit the configuration constants at the top of `cardscheduler/__init__.py`:

```python
# Configuration: Input field format
INPUT_MODE_SINGLE_FIELD = "single"
INPUT_FIELD_SINGLE = "ID"  # Field name for single-field mode

INPUT_MODE_TWO_FIELDS = "two"
INPUT_FIELD_KANJI = "Kanji"  # Field name for kanji
INPUT_FIELD_READING = "Reading"  # Field name for reading

# Active mode: Set to INPUT_MODE_SINGLE_FIELD or INPUT_MODE_TWO_FIELDS
INPUT_MODE = INPUT_MODE_SINGLE_FIELD
```

## Mode 1: Single Field (Default)

**Use this when:** Your Anki cards have kanji with furigana annotations in a single field.

**Configuration:**
```python
INPUT_MODE = INPUT_MODE_SINGLE_FIELD
INPUT_FIELD_SINGLE = "ID"  # Change to your field name
```

**Example card data:**
```
Field "ID": 頭[あたま]が 痛[いた]い
```

**Format:** Each kanji is immediately followed by its reading in brackets `[reading]`.

## Mode 2: Two Fields

**Use this when:** Your Anki cards have separate fields for kanji text and full reading.

**Configuration:**
```python
INPUT_MODE = INPUT_MODE_TWO_FIELDS
INPUT_FIELD_KANJI = "Kanji"      # Change to your kanji field name
INPUT_FIELD_READING = "Reading"   # Change to your reading field name
```

**Example card data:**
```
Field "Kanji": 頭が痛い
Field "Reading": あたまがいたい
```

**Format:** The kanji field contains the full text with kanji, and the reading field contains the complete reading in hiragana/katakana.

## How It Works

Both modes produce the same result:

1. **Single-field mode:** Directly uses the field value as-is
2. **Two-field mode:** Combines the fields intelligently:
   - If kanji field contains kanji: `Kanji[Reading]`
   - If kanji field has no kanji (pure hiragana/katakana): just `Text` (no brackets)

Both formats are then processed by `get_kanji_reading_pairs()` which:
- Extracts individual kanji-reading pairs using the Kanjidic dictionary
- Handles compound words and mixed kanji-kana text
- Returns normalized pairs like `頭[あたま]`, `痛[いた.む]`, `痛[いた.い]`

## Testing

Run the test suite to verify both modes work correctly:

```bash
PYTHONPATH=/path/to/anki-addon-cardscheduler:$PYTHONPATH python -m unittest cardscheduler.test_input_modes
```

Expected output:
```
Ran 5 tests in 0.562s
OK
```

## Switching Between Modes

To switch modes:

1. Edit `cardscheduler/__init__.py`
2. Change the `INPUT_MODE` constant:
   - For single field: `INPUT_MODE = INPUT_MODE_SINGLE_FIELD`
   - For two fields: `INPUT_MODE = INPUT_MODE_TWO_FIELDS`
3. Update field names if needed:
   - Single field: `INPUT_FIELD_SINGLE = "YourFieldName"`
   - Two fields: `INPUT_FIELD_KANJI = "YourKanjiField"` and `INPUT_FIELD_READING = "YourReadingField"`
4. Restart Anki to load the changes

## Examples

### Single Field Examples

```
学校[がっこう]        → 学[がく], 校[こう]
頭[あたま]が 痛[いた]い → 頭[あたま], 痛[いた.む], 痛[いた.い]
大会[たいかい]        → 大[たい], 会[かい]
```

### Two Field Examples

```
Kanji: 学校        Reading: がっこう        → 学校[がっこう] → 学[がく], 校[こう]
Kanji: 頭が痛い    Reading: あたまがいたい   → 頭が痛い[あたまがいたい] → 頭[あたま], 痛[いた.む], 痛[いた.い]
Kanji: 大会        Reading: たいかい        → 大会[たいかい] → 大[たい], 会[かい]
Kanji: もの        Reading: もの            → もの (no brackets) → (no kanji pairs extracted)
Kanji: は          Reading: は              → は (no brackets) → (no kanji pairs extracted)
```

Both produce identical kanji-reading pairs for scoring!

**Note**: Pure hiragana/katakana words (no kanji) are handled identically in both modes - no brackets are added, and no kanji pairs are extracted, resulting in score = 0.
