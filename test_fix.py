#!/usr/bin/env python3

from cardscheduler import load_kanji_dictionnary_readings, get_kanji_reading_pairs
from pathlib import Path

# Load kanji readings from the XML file
xml_file = Path(__file__).parent / 'cardscheduler' / 'kanjidic2_light.xml'
kanji_readings = load_kanji_dictionnary_readings(str(xml_file))

# Test the specific failing cases
test_cases = [
    '青空[あおぞら]',
    '踏切[ふみきり]',
    '死神[しにがみ]'
]

print("Testing get_kanji_reading_pairs for failing cases:")
for text in test_cases:
    pairs = get_kanji_reading_pairs(text, kanji_readings)
    print(f"\n{text}:")
    for pair in sorted(pairs):
        print(f"  {pair}")
