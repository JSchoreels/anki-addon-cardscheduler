import unittest

from cardscheduler.__init__ import get_kanji_reading_pairs, load_kanji_readings

class TestKanjiReadingPairs(unittest.TestCase):
    def setUp(self):
        # Load kanji readings from your kanjidic2.xml
        self.kanji_readings = load_kanji_readings('kanjidic2.xml')

    def test_jogakkou(self):
        text = '女学校[じょがっこう]'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)
        print(pairs)
        # You can assert expected pairs if you know them, e.g.:
        # self.assertIn('学[がっ]', pairs)
        # self.assertIn('女[じょ]', pairs)
        # self.assertIn('校[こう]', pairs)

if __name__ == '__main__':
    unittest.main()