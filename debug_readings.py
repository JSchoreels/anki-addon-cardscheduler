#!/usr/bin/env python3

from cardscheduler import load_kanji_readings
from pathlib import Path

# Load kanji readings from the XML file
xml_file = Path(__file__).parent / 'cardscheduler' / 'kanjidic2_light.xml'
kanji_readings = load_kanji_readings(str(xml_file))

# Check the readings for problematic kanji
problematic_kanji = ['空', '踏', '切', '死', '神']

for kanji in problematic_kanji:
    readings = kanji_readings.get(kanji, [])
    print(f"Kanji '{kanji}' has readings: {readings}")

# Test specific failing cases
print("\nTesting specific failing cases:")

test_cases = [
    ('青空[あおぞら]', ['青', '空'], ['あお', 'ぞら']),
    ('踏切[ふみきり]', ['踏', '切'], ['ふみ', 'きり']),
    ('死神[しにがみ]', ['死', '神'], ['しに', 'がみ']),
]

for word, kanji_chars, segments in test_cases:
    print(f"\n{word}:")
    for i, (kanji, segment) in enumerate(zip(kanji_chars, segments)):
        possible_readings = kanji_readings.get(kanji, [])
        print(f"  {kanji}[{segment}] - dictionary has: {possible_readings}")
        print(f"    Segment '{segment}' in dictionary? {segment in possible_readings}")

        # Check if it's a rendaku form
        from cardscheduler import get_base_reading_for_rendaku
        base = get_base_reading_for_rendaku(segment, possible_readings)
        print(f"    Base reading for '{segment}': {base}")

        # Check fuzzy matching
        from cardscheduler import fuzzy_reading_match
        for reading_option in possible_readings:
            fuzzy = fuzzy_reading_match(reading_option, segment)
            if fuzzy and fuzzy[0] == segment:
                print(f"    Fuzzy match: '{reading_option}' -> '{segment}'")
