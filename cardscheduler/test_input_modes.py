"""
Test input mode configurations (single-field vs two-field).
"""

import unittest
from cardscheduler.__init__ import (
    convert_two_fields_to_furigana,
    get_kanji_reading_pairs,
    load_kanji_dictionnary_readings,
    INPUT_MODE_SINGLE_FIELD,
    INPUT_MODE_TWO_FIELDS,
)


class TestInputModes(unittest.TestCase):
    """Test cases for different input field configurations."""

    def setUp(self):
        """Set up test fixtures."""
        self.kanji_readings = load_kanji_dictionnary_readings()

    def test_convert_two_fields_to_furigana(self):
        """Test converting two fields to furigana format."""
        # Test basic conversion with kanji
        result = convert_two_fields_to_furigana('頭が痛い', 'あたまがいたい')
        self.assertEqual(result, '頭が痛い[あたまがいたい]')

        # Test with no kanji (pure hiragana) - should NOT add brackets
        result = convert_two_fields_to_furigana('もの', 'もの')
        self.assertEqual(result, 'もの')

        # Test with no kanji (pure hiragana, different text)
        result = convert_two_fields_to_furigana('は', 'は')
        self.assertEqual(result, 'は')

        # Test with katakana only - should NOT add brackets
        result = convert_two_fields_to_furigana('カタカナ', 'カタカナ')
        self.assertEqual(result, 'カタカナ')

        # Test with empty reading
        result = convert_two_fields_to_furigana('頭が痛い', '')
        self.assertEqual(result, '頭が痛い')

        # Test with empty kanji
        result = convert_two_fields_to_furigana('', 'あたまがいたい')
        self.assertEqual(result, '')

        # Test with both empty
        result = convert_two_fields_to_furigana('', '')
        self.assertEqual(result, '')

    def test_single_field_format_parsing(self):
        """Test that single-field format is parsed correctly."""
        # Format: 頭[あたま]が 痛[いた]い
        text = '頭[あたま]が 痛[いた]い'
        pairs = get_kanji_reading_pairs(text, self.kanji_readings)

        # Should extract: 頭[あたま], 痛[いた.む], 痛[いた.い]
        self.assertIn('頭[あたま]', pairs)
        self.assertIn('痛[いた.む]', pairs)
        self.assertIn('痛[いた.い]', pairs)

    def test_two_field_format_parsing(self):
        """Test that two-field format is parsed correctly."""
        # Format: 頭が痛い[あたまがいたい]
        kanji_text = '頭が痛い'
        reading_text = 'あたまがいたい'

        # Convert to furigana format
        furigana_text = convert_two_fields_to_furigana(kanji_text, reading_text)

        # Parse the converted text
        pairs = get_kanji_reading_pairs(furigana_text, self.kanji_readings)

        # Should extract the same pairs as single-field format
        self.assertIn('頭[あたま]', pairs)
        self.assertIn('痛[いた.む]', pairs)
        self.assertIn('痛[いた.い]', pairs)

    def test_both_formats_produce_same_result(self):
        """Test that both formats produce identical kanji-reading pairs."""
        # Single-field format
        single_field_text = '頭[あたま]が 痛[いた]い'
        pairs_single = get_kanji_reading_pairs(single_field_text, self.kanji_readings)

        # Two-field format converted
        kanji_text = '頭が痛い'
        reading_text = 'あたまがいたい'
        two_field_text = convert_two_fields_to_furigana(kanji_text, reading_text)
        pairs_two = get_kanji_reading_pairs(two_field_text, self.kanji_readings)

        # Both should produce the same pairs
        self.assertEqual(pairs_single, pairs_two)

    def test_two_field_format_complex_word(self):
        """Test two-field format with more complex vocabulary."""
        # Example: 学校 (school)
        kanji_text = '学校'
        reading_text = 'がっこう'

        furigana_text = convert_two_fields_to_furigana(kanji_text, reading_text)
        self.assertEqual(furigana_text, '学校[がっこう]')

        pairs = get_kanji_reading_pairs(furigana_text, self.kanji_readings)

        # Should extract individual kanji readings
        self.assertIn('学[がく]', pairs)
        self.assertIn('校[こう]', pairs)


if __name__ == "__main__":
    unittest.main()
