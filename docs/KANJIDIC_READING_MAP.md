# KANJIDIC Reading Map

`cardscheduler.reading_kanji_map` creates a JSON map from processed readings to
the kanji that can use each reading.

By default the script reads only `ja_on` entries from `kanjidic2_light.xml`.
Those onyomi readings use the same generated reading variations as the scheduler.
Passing `--include-kunyomi` reads data through `load_kanji_dictionnary_readings()`
instead, so the output also includes kunyomi and irregular readings.

By default the script keeps only kanji with KANJIDIC grade `8` or lower. Grades
`1` through `6` are elementary school kanji, and grade `8` covers other joyo
kanji. Grade `9`, grade `10`, and entries without a grade are excluded unless a
higher `--max-grade` is passed.

The light KANJIDIC resource also preserves KANJIDIC `freq` metadata. The reading
map script does not currently include frequency in its JSON output, but generated
Reading to Kanji cards use it for display and ordering.

## Output

The JSON shape is:

```json
{
  "reading": ["kanji"]
}
```

Entries are ordered by the number of kanji for each reading after grade
filtering, ascending. Readings that map to one kanji are emitted before readings
shared by multiple kanji. When two readings have the same kanji count, they are
ordered by the reading text.

Kanji lists are deduplicated and sorted by grade first, then by kanji text for
deterministic output.

## Usage

Print the map:

```bash
python3 -m cardscheduler.reading_kanji_map
```

The default is equivalent to:

```bash
python3 -m cardscheduler.reading_kanji_map --onyomi-only
```

Write the map to a file:

```bash
python3 -m cardscheduler.reading_kanji_map --output reading_to_kanji.json
```

Change the grade cutoff:

```bash
python3 -m cardscheduler.reading_kanji_map --max-grade 6
```

Include kunyomi and irregular readings:

```bash
python3 -m cardscheduler.reading_kanji_map --include-kunyomi
```
