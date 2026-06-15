"""Build a reading-to-kanji map from the processed KANJIDIC readings."""

import argparse
import json
from collections import defaultdict

from .dictionary import (
    _load_kanjidic_xml,
    get_rendaku_form,
    get_rendaku_form_p,
    get_sokuon_form,
    load_kanji_dictionnary_readings,
)

DEFAULT_MAX_GRADE = 8


def load_kanji_grades():
    """Load KANJIDIC grade metadata from kanjidic2_light.xml."""
    return _load_kanji_int_metadata("grade")


def load_kanji_frequencies():
    """Load KANJIDIC frequency metadata from kanjidic2_light.xml."""
    return _load_kanji_int_metadata("freq")


def _load_kanji_int_metadata(element_name):
    root = _load_kanjidic_xml()
    if root is None:
        return {}

    values = {}

    for character in root.findall("character"):
        literal = character.find("literal")
        value = character.find(element_name)
        if literal is not None and literal.text and value is not None and value.text:
            values[literal.text] = int(value.text)

    return values


def load_onyomi_readings():
    """Load only onyomi readings from kanjidic2_light.xml."""
    root = _load_kanjidic_xml()
    if root is None:
        return {}

    kanji_readings = {}

    for character in root.findall("character"):
        kanji = character.find("literal").text
        readings_map = {}

        for reading in character.findall("ja_on"):
            reading_text = reading.text
            if reading_text:
                readings_map[reading_text] = _reading_variations(reading_text)

        if readings_map:
            kanji_readings[kanji] = dict(sorted(readings_map.items()))

    return kanji_readings


def _reading_variations(reading_text):
    variations = [reading_text]
    _extend_with_variation(variations, get_rendaku_form)
    _extend_with_variation(variations, get_rendaku_form_p)
    _extend_with_variation(variations, get_sokuon_form)
    return variations


def _extend_with_variation(variations, variation_function):
    for variation in list(variations):
        new_variation = variation_function(variation)
        if new_variation:
            variations.append(new_variation)


def build_reading_to_kanji_map(kanji_readings, kanji_grades=None, max_grade=None):
    """Return {reading: [kanji, ...]} ordered by number of matching kanji.

    The input is the processed dictionary shape returned by
    load_kanji_dictionnary_readings(): {kanji: {base_reading: [variations]}}.
    Both base readings and their processed variations are indexed.
    """
    reading_to_kanji = defaultdict(set)
    kanji_grades = kanji_grades or {}

    for kanji, readings_map in kanji_readings.items():
        grade = kanji_grades.get(kanji)
        if max_grade is not None and (grade is None or grade > max_grade):
            continue

        for base_reading, variations in readings_map.items():
            readings = {base_reading}
            readings.update(variation for variation in variations if variation)

            for reading in readings:
                if reading:
                    reading_to_kanji[reading].add(kanji)

    sorted_items = sorted(
        reading_to_kanji.items(),
        key=lambda item: (len(item[1]), item[0]),
    )

    return {
        reading: sorted(
            kanji_set,
            key=lambda kanji: (kanji_grades.get(kanji, 99), kanji),
        )
        for reading, kanji_set in sorted_items
    }


def write_reading_to_kanji_map(
    output_path=None,
    onyomi_only=True,
    max_grade=DEFAULT_MAX_GRADE,
):
    """Load KANJIDIC readings and write the ordered reading-to-kanji JSON map."""
    if onyomi_only:
        kanji_readings = load_onyomi_readings()
    else:
        kanji_readings = load_kanji_dictionnary_readings()

    kanji_grades = load_kanji_grades()
    reading_to_kanji = build_reading_to_kanji_map(
        kanji_readings,
        kanji_grades=kanji_grades,
        max_grade=max_grade,
    )
    json_text = json.dumps(reading_to_kanji, ensure_ascii=False, indent=2)

    if output_path:
        with open(output_path, "w", encoding="utf-8") as output_file:
            output_file.write(json_text)
            output_file.write("\n")
        return None

    print(json_text)
    return reading_to_kanji


def main():
    parser = argparse.ArgumentParser(
        description="Create a reading-to-kanji JSON map ordered by kanji count."
    )
    parser.add_argument(
        "--output",
        help="Optional output JSON file. Prints to stdout when omitted.",
    )
    parser.add_argument(
        "--max-grade",
        type=int,
        default=DEFAULT_MAX_GRADE,
        help="Only include kanji with this KANJIDIC grade or lower. Default: 8.",
    )
    reading_scope = parser.add_mutually_exclusive_group()
    reading_scope.add_argument(
        "--onyomi-only",
        dest="onyomi_only",
        action="store_true",
        default=True,
        help="Only include onyomi readings. This is the default.",
    )
    reading_scope.add_argument(
        "--include-kunyomi",
        dest="onyomi_only",
        action="store_false",
        help="Include kunyomi and irregular readings.",
    )
    args = parser.parse_args()

    write_reading_to_kanji_map(
        args.output,
        onyomi_only=args.onyomi_only,
        max_grade=args.max_grade,
    )


if __name__ == "__main__":
    main()
