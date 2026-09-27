# CardScheduler - Intelligent Vocabulary Card Scheduling for Anki

An Anki addon that helps you learn Japanese vocabulary by prioritizing cards based on unlock potential, familiarity, and complexity.

## Features

- ✅ Score word cards from canonical kanji-reading familiarity, with observed
  rendaku/sokuon ambiguity and linguistic context factored into difficulty
- ✅ Flag how many unknown readings a word has
- ✅ Score sentence cards from reviewed vocabulary and kanji-reading familiarity
- ✅ Smart sorting algorithm that considers:
  - **Unlock potential**: How many cards would be unlocked by learning this kanji
  - **Unlock score impact**: The quality/score of cards that would be unlocked
  - **Card familiarity**: Stability/interval of kanji/readings
  - **Card complexity**: Number of kanji, word length

## Installation

1. Copy the entire addon directory to your Anki addons folder
2. Restart Anki
3. The addon will add menu items under **Tools**:
   - "CardScheduler: Settings" - Configure the complete add-on through a native UI
   - "CardScheduler: Compute Scores" - Update card fields with scores
   - "CardScheduler: Compute and Reposition Cards" - Update scores and reposition new cards

CardScheduler can automatically refresh scores, related words, kanji meanings,
and new-card positions once when an Anki profile opens and once when Anki enters
a new scheduler day. Configure either trigger independently from **Tools →
CardScheduler: Settings**.

## Documentation

- **[Input Modes](docs/INPUT_MODES.md)** - Configure single-field vs. two-field input formats
- **[Configuration](docs/CONFIGURATION.md)** - Configure the add-on from Anki
- **[Simulation Mode](docs/SIMULATION_MODE.md)** - See optimal learning order from scratch
- **[Unlock Score Impact](docs/UNLOCK_SCORE_IMPACT.md)** - Understanding the unlock potential algorithm
- **[Menu Actions](docs/MENU_ACTIONS.md)** - Available menu commands
- **[Reading to Kanji Cards](docs/READING_TO_KANJI_CARDS.md)** - Generate Reading → Kanji cards from known vocabulary
- **[Sentence Scoring](docs/SENTENCE_SCORING.md)** - Score sentence cards from known vocabulary
- **[Word Score Benchmark](docs/WORD_SCORE_BENCHMARK.md)** - Measure vocabulary scoring performance on a copied collection
- **[Sentence Score Benchmark](docs/SENTENCE_SCORE_BENCHMARK.md)** - Measure sentence scoring performance on a copied collection
- **[Input Modes Test Report](docs/INPUT_MODES_TEST_REPORT.md)** - Test coverage for input modes

## Project Structure

```
.
├── cardscheduler/           # Main package
│   ├── __init__.py          # Public API
│   ├── config.py            # Configuration constants
│   ├── dictionary.py        # Dictionary loading and manipulation
│   ├── word_parser.py       # Kanji/reading parsing
│   ├── scheduler.py         # Core scheduling logic
│   ├── anki_interface.py    # Anki-specific operations
│   └── tests/               # Test suite
├── docs/                    # Documentation
├── resources/               # Data files (kanjidic2.xml)
└── test_output/             # Test output files (gitignored)
```

## Configuration

Open **Tools → CardScheduler: Settings** or **Tools → Add-ons → CardScheduler →
Config** to customize deck names, every field name, automatic processing, input
mode, frequency handling, Reading → Kanji generation, and sentence scoring. See
[Configuration](docs/CONFIGURATION.md) for the complete options.

## Testing

Run the test suite:

```bash
python3 -m pytest cardscheduler/tests/
```

Test outputs are written to the `test_output/` directory.

## How It Works

1. **Score Computation**: Each card gets a familiarity score based on the
   stability/interval of its canonical kanji-reading families. Observed reading
   variants add an entropy-based handicap unless the word context resolves them.
2. **Unlock Potential**: Calculates how many other cards would become learnable by studying this card
3. **Position Assignment**: New cards are sorted by:
   - Score (higher = more familiar)
   - Reading ambiguity, including score-zero cards through a separate shadow priority
   - Unlock potential (more cards unlocked)
   - Unlock median score increase (higher quality unlocks)
   - Missing kanji count (fewer missing)
   - Kanji count (fewer = simpler)
   - Kana count (fewer = shorter)

## Module Overview

- **`config.py`**: All configuration constants (field names, modes, flags)
- **`dictionary.py`**: Loads kanjidic2_light.xml, handles rendaku, verb conjugations, iteration marks
- **`word_parser.py`**: Parses kanji-reading pairs from furigana text, counts kanji/kana
- **`scheduler.py`**: Core algorithm - score computation, unlock potential, card positioning
- **`anki_interface.py`**: All Anki-specific operations - loading cards, updating fields, repositioning

## License

[Add your license here]

## Contributing

Contributions welcome! Please add tests for new features.
