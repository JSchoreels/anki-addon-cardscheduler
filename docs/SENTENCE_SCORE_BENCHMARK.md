# Sentence Score Benchmark

The sentence score benchmark measures the current sentence scoring workflow
against a copied Anki collection. It reads vocabulary and sentence card data,
computes scores in memory, and does not update note fields or reposition cards.

## Collection Copy

Run the benchmark from the add-on repository:

```bash
rtk python3 benchmark_sentence_scores.py --sentence-limit 300
```

By default, the script reads Anki's `prefs21.db`, selects the last loaded
profile, copies that profile's `collection.anki2` into a temporary directory,
and opens the copy. If the source collection has SQLite `-wal` or `-shm`
sidecars, those files are copied too.
The temporary copy is removed after the run unless `--keep-copy` is used.

Use an explicit profile or collection path when needed:

```bash
rtk python3 benchmark_sentence_scores.py --profile "Main Profile" --sentence-limit 300
rtk python3 benchmark_sentence_scores.py --collection "/path/to/collection.anki2" --sentence-limit 300
```

`--sentence-limit` limits the number of unique sentence notes that are tokenized
and scored. Use `--sentence-limit 0` to score all configured sentence notes.

`--vocab-limit` can restrict the number of vocabulary cards used to build the
word index. Omitting it uses all vocabulary cards, which is closer to the real
workflow.

## Reported Stages

The benchmark reports timings for:

- copying and opening the collection snapshot
- MeCab setup
- loading vocabulary cards
- computing vocabulary scores
- loading KANJIDIC readings
- building kanji-reading interval data
- building the vocabulary word index
- loading/tokenizing sentence cards
- computing sentence scores
- assigning sentence order

It also reports MeCab extraction calls, cache hits, and cache misses. A high
miss count usually means the benchmark is paying for many separate MeCab
subprocess calls. `MeCab subprocess calls` shows the number of actual MeCab
process executions after batching.

Sentence scoring batches MeCab tokenization by workflow stage: vocabulary
surfaces are tokenized together while building the vocabulary word index, and
loaded sentence texts are tokenized together while loading sentence cards.

When `--sentence-limit` is used, loaded new sentence cards are counted only for
the loaded note subset. The report also includes the total number of new cards
matching the configured sentence decks.
