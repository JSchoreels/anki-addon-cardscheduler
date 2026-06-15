# Word Score Benchmark

The word score benchmark measures vocabulary score computation against a copied
Anki collection. It reads vocabulary card data, computes score and ordering data
in memory, and does not update note fields or reposition cards.

## Collection Copy

Run the benchmark from the add-on repository:

```bash
rtk python3 benchmark_word_scores.py
```

By default, the script reads Anki's `prefs21.db`, selects the last loaded
profile, copies that profile's `collection.anki2` into a temporary directory,
and opens the copy. If the source collection has SQLite `-wal` or `-shm`
sidecars, those files are copied too. The temporary copy is removed after the
run unless `--keep-copy` is used.

Use an explicit profile or collection path when needed:

```bash
rtk python3 benchmark_word_scores.py --profile "Main Profile"
rtk python3 benchmark_word_scores.py --collection "/path/to/collection.anki2"
```

`--card-limit` can restrict the number of loaded vocabulary cards that are
scored after the collection read stage.

Use `--update-fields` to also write computed score fields into the copied
collection:

```bash
rtk python3 benchmark_word_scores.py --update-fields
```

This still does not write to the live Anki collection. It updates only the
temporary copied collection and removes that copy after the run unless
`--keep-copy` is used.

## Reported Stages

The benchmark reports timings for:

- copying and opening the collection snapshot
- loading vocabulary cards
- loading KANJIDIC readings
- building card-to-kanji-reading pairs
- grouping cards by kanji-reading pair
- calculating max weighted intervals
- building visual kanji-to-card mappings
- computing visual kanji familiarity
- computing per-card scores
- computing unlock potential
- updating per-card unlock metrics
- finding new cards
- assigning positions
- detecting score fields, when `--update-fields` is used
- updating score fields in the copied collection, when `--update-fields` is used

It also reports the number of loaded vocabulary cards, new cards, unique
kanji-reading pairs, unique kanji, and reviewed cards.
