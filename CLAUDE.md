# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An Anki addon for Japanese vocabulary learning that intelligently schedules cards based on unlock potential, familiarity, and complexity. The system analyzes kanji-reading relationships across cards to determine optimal learning order.

## Development Commands

### Testing
```bash
# Run all tests
python -m unittest discover cardscheduler/tests

# Run specific test module
python -m unittest cardscheduler.tests.test_html_formatter

# Run specific test class
python -m unittest cardscheduler.tests.test_html_formatter.TestHTMLFormatter

# Run single test
python -m unittest cardscheduler.tests.test_html_formatter.TestHTMLFormatter.test_no_spaces_within_single_word
```

**Note:** Use `unittest` framework, not pytest. Tests are in `cardscheduler/tests/test_*.py`.

### Dictionary Processing
```bash
# Regenerate kanjidic2_light.xml after modifying kanjidic_filter.py
python cardscheduler/kanjidic_filter.py
```

This extracts kanji readings, meanings, and irregular forms from the full kanjidic2.xml into a lightweight version used by the addon.

## Architecture: Separation of Concerns

The codebase follows a strict layered architecture:

### Data Layer → Presentation Layer → Storage Layer

```
scheduler.py (Data)
    ↓ produces CardInfo objects with data structures
html_formatter.py (Presentation)
    ↓ generates HTML strings
anki_interface.py (Storage)
    ↓ writes to Anki database
```

**Key Principle:** Data collection and HTML generation are separated. Never mix them.

### Module Responsibilities

- **`scheduler.py`**: Scheduling algorithms, scoring, unlock potential calculation
  - Stores data structures (lists of tuples), NOT HTML strings
  - Example: `CardInfo.related_cards_known = [(CardInfo, shared_kanji_set), ...]`

- **`html_formatter.py`**: HTML generation, color assignment, styling
  - Takes data structures from scheduler
  - Returns formatted HTML strings
  - Handles color coordination across all fields

- **`dictionary.py`**: Dictionary loading and data access
  - Loads kanjidic2_light.xml (kanji meanings and readings)
  - Loads irregular_readings.txt for special cases
  - Handles rendaku variations and verb conjugations

- **`word_parser.py`**: Text parsing, kanji/reading extraction
  - Parses furigana format: `kanji[reading]`
  - Handles two-field format conversion (Kanji field + Reading field)
  - Counts kanji/kana in text

- **`anki_interface.py`**: All Anki-specific operations
  - Loading cards from collection
  - Updating note fields
  - Repositioning cards in deck
  - Field detection and validation

- **`config.py`**: Configuration constants
  - Field names (e.g., `FIELD_NAME_KANJI_MEANINGS`)
  - Simulation mode and input mode settings

## Data Flow for Card Processing

```
1. anki_interface.load_cards()
   → Extracts furigana_text from Anki notes
   → Creates CardInfo objects with stability/interval

2. scheduler.compute_scores(cards, kanji_readings)
   → Builds kanji_reading_to_cards mapping
   → Computes familiarity scores based on known readings
   → Calls compute_related_words() to find related cards
   → Stores related cards as data: [(CardInfo, shared_kanji_set), ...]

3. html_formatter.format_card_html(card_info, kanji_meanings, kanji_readings)
   → Assigns colors to card's kanji
   → Generates HTML for related words (with color highlighting)
   → Generates HTML for kanji meanings (with matching colors)
   → Returns (related_known_html, related_unknown_html, meanings_html)

4. anki_interface.update_card_fields()
   → Calls formatter to generate HTML
   → Updates Anki note fields with HTML strings
```

## Key Data Structures

### CardInfo
```python
class CardInfo:
    note_id: int
    furigana_text: str          # "大[だい]学[がく]"
    stability: float

    # Data structures (NOT HTML strings)
    related_cards_known: List[Tuple[CardInfo, Set[str]]]
    related_cards_unknown: List[Tuple[CardInfo, Set[str]]]

    # Computed metrics
    score: float
    unlock_potential: int
    unlock_median_score_increase: float
```

### KanjiReadingInfo
```python
class KanjiReadingInfo:
    kanji: str
    reading: str
    weighted_interval: float    # Stability of this kanji-reading pair
```

### Dictionary Data
```python
# From dictionary.py
kanji_readings: Dict[str, Dict[str, List[str]]]
# Example: {'大': {'だい': ['だい'], 'たい': ['たい'], ...}}

kanji_meanings: Dict[str, List[str]]
# Example: {'大': ['large', 'big', 'great']}
```

## Furigana Format

The addon uses bracket notation for furigana:
- Format: `kanji[reading]`
- Example: `大[だい]学[がく]` (university)
- Multiple kanji: `物[もの]忘[わす]れ` (forgetfulness)

**Spacing rules:**
- No spaces within a single word: `物[もの]忘[わす]` ✓
- Separator between words: `,　 ` (comma + Japanese space + regular space)

## Color Coordination

Colors are assigned once per card in `html_formatter.format_card_html()`:

```python
# Assign colors to current card's kanji
current_kanji = {'大', '学'}
kanji_to_color = {
    '大': 'lightgreen',
    '学': 'lightblue',
}

# Same colors used for:
# 1. Related words highlighting
# 2. Kanji meanings highlighting
```

**Available colors:** lightgreen, lightblue, pink, lightyellow, lightcoral, lightseagreen, plum, peachpuff

## Code Style Guidelines (from CODE_GUIDELINES.md)

### Python Best Practices

1. **Use list comprehensions:**
   ```python
   # Good
   meanings = [m.text for m in character.findall('meaning') if m.text]

   # Avoid
   meanings = []
   for m in character.findall('meaning'):
       if m.text:
           meanings.append(m.text)
   ```

2. **Avoid obvious comments:**
   ```python
   # Good
   meanings = [m.text for m in character.findall('meaning') if m.text]

   # Avoid - comment is obvious
   # Get meanings
   meanings = [m.text for m in character.findall('meaning') if m.text]
   ```

3. **Extract common code patterns:**
   - Use helper functions for repeated exception handling
   - Example: `_load_kanjidic_xml()` used by both `load_kanji_meanings()` and `load_kanji_dictionnary_readings()`

4. **Don't limit data at source:**
   ```python
   # Good - keep all meanings in XML
   for meaning in meanings:
       m_elem.text = meaning

   # Later, limit when displaying
   meanings_text = ', '.join(meanings[:3])

   # Avoid - limiting too early
   for meaning in meanings[:3]:  # Don't limit here!
   ```

### Architecture Principles

- Keep logic in the right module (see "Module Responsibilities" above)
- Store structured data, convert to HTML only when needed
- Never mix data collection with presentation logic

## Testing Strategy

- Use `unittest` framework (not pytest)
- Test files follow pattern: `test_*.py`
- Integration tests may require setting PYTHONPATH:
  ```bash
  PYTHONPATH=/Users/jschoreels/workspace/anki-addon-cardscheduler:$PYTHONPATH python -m unittest
  ```

### Key Test Modules

- `test_html_formatter.py`: HTML generation, spacing, color coordination
- `test_get_kanji_readings_pairs.py`: Furigana parsing
- `test_related_words.py`: Related card computation
- `test_unlock_potential.py`: Unlock potential algorithm
- `test_input_modes.py`: Single-field vs two-field format handling

## Important Files

- **`CODE_GUIDELINES.md`**: Detailed code style guidelines
- **`TODO.md`**: Feature roadmap
- **`cardscheduler/resources/kanjidic2_light.xml`**: Lightweight kanji dictionary (generated)
- **`cardscheduler/resources/irregular_readings.txt`**: Special readings for irregular verbs/adjectives
- **`docs/*.md`**: Feature documentation (INPUT_MODES, SIMULATION_MODE, etc.)
