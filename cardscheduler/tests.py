import unittest
import os
import csv
from pathlib import Path
from collections import defaultdict

from cardscheduler.__init__ import get_kanji_reading_pairs, load_kanji_readings

def analyze_empty_brackets(kanji_pairs):
    """Analyze and report the percentage of empty brackets in kanji pairs."""
    total_pairs = len(kanji_pairs)
    empty_bracket_pairs = [pair for pair in kanji_pairs if pair.endswith('[]')]
    empty_count = len(empty_bracket_pairs)

    if total_pairs == 0:
        return 0.0, [], []

    percentage = (empty_count / total_pairs) * 100
    return percentage, empty_bracket_pairs, list(kanji_pairs - set(empty_bracket_pairs))

class TestKanjiReadingPairs(unittest.TestCase):
    def setUp(self):
        # kanjidic2_light.xml is in the same directory as this test file
        kanjidic_path = Path(__file__).parent / 'kanjidic2_light.xml'
        self.kanji_readings = load_kanji_readings(str(kanjidic_path))

    def test_jogakkou(self):
        text = '女学校[じょがっこう]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'学[がく]', '校[こう]', '女[じょ]', '女学校[じょがっこう]'})

    def test_ikkyo(self):
        text = '一挙[いっきょ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'一[いち]', '一[いつ]', '一挙[いっきょ]', '挙[きょ]'})

    def test_rendaku(self):
        text = '青空[あおぞら]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'青[あお]', '空[そら]', '青空[あおぞら]'})

    def test_naze(self):
        text = '何故[なぜ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'何故[なぜ]', '何[な]', '故[ぜ]'})

    def test_muccha(self):
        text = '無茶[むっちゃ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'無[む]', '無茶[むっちゃ]', '茶[ちゃ]'})

    def test_michiyuku(self):
        text = '道行く[みちゆく]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'行[ゆ]', '行[ゆく]', '道[みち]', '道行く[みちゆく]'})

    def test_ningenkankei(self):
        text = '人間関係[にんげんかんけい]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'人間関係[にんげんかんけい]', '人[にん]', '間[けん]', '関[かん]', '係[けい]'})

    def test_kotoshi(self):
        text = '今年[ことし]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'今[こ]', '年[とし]', '今年[ことし]'})

    def test_tokei(self):
        text = '時計[とけい]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'時計[とけい]', '時[とき]', '計[けい]'})

    def test_hikiageru(self):
        text = '引き上げる[ひきあげる]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'上[あ]', '上[あげる]', '引[ひ]', '引[ひき]', '引き上げる[ひきあげる]'})

    def test_gunpuku(self):
        text = '軍服[ぐんぷく]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'軍服[ぐんぷく]', '軍[ぐん]', '服[ふく]'})

    def test_ippou(self):
        text = '一方[いっぽう]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'一[いち]', '一[いつ]', '一方[いっぽう]', '方[ほう]'})

    def test_tokidoki(self):
        text = '時々[ときどき]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'時々[ときどき]', '時[とき]'})

    def test_happyoukai(self):
        text = '発表会[はっぴょうかい]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'発表会[はっぴょうかい]', '発[はつ]', '表[ひょう]', '会[かい]'})

    def test_chouinshiki(self):
        text = '調印式[ちょういんしき]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'調[ちょう]', '印[いん]', '式[しき]', '調印式[ちょういんしき]'})

    def test_shinigami(self):
        text = '死神[しにがみ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'死[し]', '死[しに]', '死神[しにがみ]', '神[かみ]'})

    def test_fumikiri(self):
        text = '踏切[ふみきり]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'切[き]', '切[きり]', '踏[ふ]', '踏[ふみ]', '踏切[ふみきり]'})

    def test_yukue(self):
        text = '行方[ゆくえ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'行方[ゆくえ]', '行[ゆ]', '行[ゆく]', '方[]'})

    def test_yukuefumei(self):
        text = '行方不明[ゆくえふめい]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'行方不明[ゆくえふめい]', '行[ゆ]', '方[]', '不[ふ]', '明[めい]'})

    def test_amagumo(self):
        text = '雨雲[あまぐも]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {sorted(pairs)}")
        self.assertSetEqual(pairs, {'雨[あめ]', '雲[くも]', '雨雲[あまぐも]'})


    def test_csv_analysis_and_output(self):
        """Analyze all CSV entries and write kanji pairs to file."""
        # Load CSV data
        csv_path = Path(__file__).parent / 'test.mapping.csv'
        output_path = Path(__file__).parent / 'all_kanji_pairs.txt'

        # Check if CSV file exists
        if not csv_path.exists():
            self.fail(f"CSV file not found: {csv_path}")

        # Collect all unique source texts from CSV
        source_texts = set()
        try:
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row_num, row in enumerate(reader, 1):
                    if len(row) >= 2:
                        source_text = row[1].strip()
                        if source_text:  # Only add non-empty texts
                            source_texts.add(source_text)
                    elif len(row) == 1:
                        # Single column rows - treat as individual kanji pairs, extract source text from them
                        kanji_pair = row[0].strip()
                        if '[' in kanji_pair and ']' in kanji_pair:
                            # Extract the source text from the kanji pair format
                            source_text = kanji_pair
                            source_texts.add(source_text)
                    else:
                        print(f"Warning: Row {row_num} is empty or malformed: {row}")
        except Exception as e:
            self.fail(f"Error reading CSV file: {e}")

        if not source_texts:
            self.fail(f"No valid source texts found in CSV file: {csv_path}")

        print(f"\nAnalyzing {len(source_texts)} unique texts from CSV...")

        all_pairs = set()
        total_kanji = 0
        empty_kanji = 0
        texts_with_empty = 0

        # Analyze each text
        for source_text in sorted(source_texts):
            pairs = get_kanji_reading_pairs(source_text, self.kanji_readings)
            all_pairs.update(pairs)

            # Count kanji and empty brackets
            empty_percentage, empty_pairs, non_empty_pairs = analyze_empty_brackets(pairs)

            kanji_count = len(pairs)
            empty_count = len(empty_pairs)

            total_kanji += kanji_count
            empty_kanji += empty_count

            if empty_count > 0:
                texts_with_empty += 1
                print(f"❌ {source_text}: {empty_count}/{kanji_count} empty ({empty_percentage:.1f}%) - {sorted(empty_pairs)}")

        # Ensure we actually processed some kanji
        if total_kanji == 0:
            self.fail("No kanji pairs were generated from any source text")

        # Write all pairs to file
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(f"# All Kanji-Reading Pairs from test.mapping.csv\n")
                f.write(f"# Generated from {len(source_texts)} unique texts\n")
                f.write(f"# Total pairs: {len(all_pairs)}\n")
                f.write(f"# Empty brackets: {len([p for p in all_pairs if p.endswith('[]')])}\n\n")

                for pair in sorted(all_pairs):
                    f.write(f"{pair}\n")
            print(f"Output written to: {output_path}")
        except Exception as e:
            print(f"Warning: Could not write output file: {e}")

        # Summary report
        print("\n" + "="*60)
        print("KANJI READING ANALYSIS SUMMARY")
        print("="*60)
        print(f"Total unique texts analyzed: {len(source_texts)}")
        print(f"Total kanji pairs generated: {total_kanji}")
        print(f"Kanji with empty readings: {empty_kanji}")
        print(f"Empty reading percentage: {(empty_kanji/total_kanji*100):.1f}%")
        print(f"Texts with empty readings: {texts_with_empty}/{len(source_texts)} ({texts_with_empty/len(source_texts)*100:.1f}%)")
        print(f"Unique pairs written to: {output_path}")
        print(f"Total unique pairs: {len(all_pairs)}")
        print(f"Unique pairs with empty readings: {len([p for p in all_pairs if p.endswith('[]')])}")

        # Test assertion - ensure we have reasonable success rate
        success_rate = ((total_kanji - empty_kanji) / total_kanji * 100)
        self.assertGreaterEqual(success_rate, 99.1, f"Success rate {success_rate:.1f}% is too low")

if __name__ == '__main__':
    unittest.main()
