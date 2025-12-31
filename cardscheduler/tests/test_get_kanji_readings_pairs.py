import unittest
import os
import csv
from pathlib import Path
from collections import defaultdict

from cardscheduler import get_kanji_reading_pairs, load_kanji_dictionnary_readings

def analyze_empty_brackets(kanji_pairs):
    """Analyze and report the percentage of empty brackets in kanji pairs."""
    total_pairs = len(kanji_pairs)
    empty_bracket_pairs = [pair for pair in kanji_pairs if pair.endswith('[ ]')]
    empty_count = len(empty_bracket_pairs)

    if total_pairs == 0:
        return 0.0, [ ], [ ]

    percentage = (empty_count / total_pairs) * 100
    return percentage, empty_bracket_pairs, list(kanji_pairs - set(empty_bracket_pairs))

class TestKanjiReadingPairs(unittest.TestCase):

    @classmethod
    def setUp(cls):
        cls.kanji_readings = load_kanji_dictionnary_readings()

    def test_daigakuseikai(self):
        text = '大学生会[だいがくせいかい]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'学[がく]', '大[たい]', '生[せい]', '会[かい]'})

    def test_yubiwa(self):
        text = '指輪[ゆびわ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'指[ゆび]', '輪[わ]'})

    def test_ikiru(self):
        text = '生[い]きる'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'生[い]'})

    def test_jogakkou(self):
        text = '女学校[じょがっこう]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'女[じょ]', '学[がく]', '校[こう]'})

    def test_ikkyo(self):
        text = '一挙[いっきょ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'一[いつ]', '挙[きょ]'})

    def test_aozora(self):
        text = '青空[あおぞら]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'空[そら]', '青[あお]'})

    def test_naze(self):
        text = '何故[なぜ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'何[ ]', '故[ ]'})

    def test_muccha(self):
        text = '無茶[むっちゃ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'無[む]', '茶[ちゃ]'})

    def test_michiyuku(self):
        text = '道行く[みちゆく]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'行[ゆ]', '道[みち]'})

    def test_ningenkankei(self):
        text = '人間関係[にんげんかんけい]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'人[にん]', '係[けい]', '間[けん]', '関[かん]'})

    def test_kotoshi(self):
        text = '今年[ことし]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        # Irregular reading loaded from irregular_readings.txt
        self.assertSetEqual(pairs, {'今[こ]', '年[とし]'})

    def test_tokei(self):
        text = '時計[とけい]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        # Irregular reading loaded from irregular_readings.txt
        self.assertSetEqual(pairs, {'時[と]', '計[けい]'})

    def test_hikiageru(self):
        text = '引き上げる[ひきあげる]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'上[あ]', '引[ひ]'})

    def test_gunpuku(self):
        text = '軍服[ぐんぷく]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'服[ふく]', '軍[ぐん]'})

    def test_ippou(self):
        text = '一方[いっぽう]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        # Only actual reading: いっ→いち (sokuon normalized)
        self.assertSetEqual(pairs, {'一[いつ]', '方[ほう]'})

    def test_tokidoki(self):
        text = '時々[ときどき]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'時[とき]'})

    def test_happyoukai(self):
        text = '発表会[はっぴょうかい]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'会[かい]', '発[はつ]', '表[ひょう]'})

    def test_chouinshiki(self):
        text = '調印式[ちょういんしき]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'印[いん]', '式[しき]', '調[ちょう]'})

    def test_shinigami(self):
        text = '死神[しにがみ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'死[し]', '神[かみ]'})

    def test_fumikiri(self):
        text = '踏切[ふみきり]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'切[き]', '踏[ふ]'})

    def test_yukue(self):
        text = '行方[ゆくえ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'行[ゆ]', '方[ ]'})

    def test_yukuefumei(self):
        text = '行方不明[ゆくえふめい]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'不[ ]', '明[ ]', '行[ゆ]', '方[ ]'})

    def test_amagumo(self):
        text = '雨雲[あまぐも]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'雨[あま]', '雲[くも]'})

    def test_tsutsumotase(self):
        text = '美人局[つつもたせ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'人[ ]', '局[ ]', '美[ ]'})

    def test_obidame(self):
        text = '帯止め[おびどめ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'帯[お]', '止[ど]'})

    def test_yumemiru(self):
        text = '夢見[ゆめみ]る'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'見[み]', '夢[ゆめ]'})

    def test_machigai(self):
        text = '間違[まちが]い'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'違[ちが]', '間[ま]'})

    def test_toonori(self):
        text = '遠乗[とおの]り'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'乗[の]', '遠[とお]'})

    def test_mezameru(self):
        text = '目覚[めざ]める'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'覚[さ]', '目[め]'})

    def test_inochinoonjin(self):
        text = '命の恩人[いのちのおんじん]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'命[いのち]', '恩[おん]', '人[じん]'})

    def test_naku(self):
        text = '泣[な]き 声[ごえ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'声[ごえ]', '泣[な]'})

    def test_atamagaitai_one_field(self):
        text = '頭[あたま]が 痛[いた]い'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'痛[いた]', '頭[あたま]'})

    def test_atamagaitai_two_fields(self):
        text = '頭が痛い[あたまがいたい]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'痛[いた]', '頭[あたま]'})

    def test_gouka(self):
        text = '豪華[ごうか]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'華[か]', '豪[ごう]'})

    def test_iwayuru(self):
        text = '所謂[いわゆる]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'謂[いわゆる]', '所[ ]'})

    def test_shimekiri(self):
        text = '締[し]め 切[き]り'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'締[し]', '切[き]'})

    def test_ataru(self):
        text = '当[あ]たる'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'当[あ]'})

    def test_atarimae(self):
        text = '当[あ]たり 前[まえ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'前[まえ]', '当[あ]'})

    def test_kago(self):
        text = 'といっても過言ではない[といってもかごんではない]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'過[ ]', '言[ ]'})

    def test_onsha(self):
        text = '御社[おんしゃ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'社[しゃ]', '御[おん]'})

    def test_budoushu(self):
        text = 'ブドウ酒[ブドウしゅ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'酒[ ]'})

    def test_shitsuren(self):
        text = '失恋[しつれん]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'失[しつ]', '恋[れん]'})

    def test_katamaru(self):
        text = '固まる[かたまる]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'固[かた]'})

    def test_katai(self):
        text = '固い[かたい]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'固[かた]'})

    def test_shippai(self):
        text = '失敗[しっぱい]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'失[しつ]', '敗[はい]'})

    def test_kakusu(self):
        text = '画数[かくすう]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'画[かく]', '数[すう]'})

    def test_tsure(self):
        text = '連[つ]れ'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'連[つ]'})

    def test_kueru(self):
        text = '食[く]える'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'食[く]'})

    def test_suukagetsu(self):
        text = '数ヶ月[すうかげつ]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {})

    def test_uwaki(self):
        text = '浮気[うわき]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(f"Actual pairs for {text}: {pairs}")
        self.assertSetEqual(pairs, {'浮[うわ]', '気[き]'})


    def test_csv_analysis_and_output(self):
        """Analyze all CSV entries and write kanji pairs to file."""
        # Load CSV data
        csv_path = Path(__file__).parent / 'test.mapping.csv'

        # Write output to test_output directory
        test_output_dir = Path(__file__).parent / 'test_output'
        test_output_dir.mkdir(exist_ok=True)
        output_path = test_output_dir / 'all_kanji_pairs.txt'

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

            kanji_count = len(pairs) # - 1  # Exclude the full word pair
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
                f.write(f"# Empty brackets: {len([p for p in all_pairs if p.endswith('[ ]')])}\n\n")

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
        print(f"Unique pairs with empty readings: {len([p for p in all_pairs if p.endswith('[ ]')])}")

        # Test assertion - ensure we have reasonable success rate
        success_rate = ((total_kanji - empty_kanji) / total_kanji * 100)
        print(f"Success rate: {success_rate:.2f}%")
        self.assertGreaterEqual(success_rate, 98.75, f"Success rate {success_rate:.2f}% is too low")

if __name__ == '__main__':
    unittest.main()
