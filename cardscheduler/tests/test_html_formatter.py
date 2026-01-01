"""
Unit tests for html_formatter module.

Tests HTML generation for related words and kanji meanings, with focus on:
- Correct spacing between and within words
- Color coordination
- HTML structure
"""

import unittest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cardscheduler.html_formatter import format_card_html, _format_related_words, _highlight_shared_kanji
from cardscheduler.scheduler import CardInfo
from cardscheduler.dictionary import load_kanji_meanings, load_kanji_dictionnary_readings


class TestHTMLFormatter(unittest.TestCase):
    """Test HTML generation for card display fields."""

    @classmethod
    def setUpClass(cls):
        """Load dictionaries once for all tests."""
        cls.kanji_meanings = load_kanji_meanings()
        cls.kanji_readings = load_kanji_dictionnary_readings()

    def test_no_spaces_within_single_word(self):
        """Test that kanji pairs within a single word have no spaces between them."""
        card = CardInfo(1, '物[もの]忘[わす]', 5.0)
        kanji_to_color = {'物': 'lightgreen', '忘': 'lightblue'}

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)

        # Should not have Japanese space (　) between pairs
        self.assertNotIn('物[もの]　忘[わす]', result)
        self.assertNotIn(']　[', result)
        # Should have pairs directly concatenated or with span tags
        self.assertIn('物[もの]', result)
        self.assertIn('忘[わす]', result)

    def test_separator_between_different_words(self):
        """Test that different related words are separated by comma + Japanese space + regular space."""
        card1 = CardInfo(1, '物[もの]忘[わす]', 8.0)
        card2 = CardInfo(2, '置[お]去[さ]', 6.0)

        related_cards_list = [
            (card1, {'忘'}),
            (card2, {'去'}),
        ]

        kanji_to_color = {'忘': 'lightgreen', '去': 'lightblue'}

        result = _format_related_words(related_cards_list, kanji_to_color, self.kanji_readings)

        # Should have separator between words
        self.assertIn(',　 ', result)
        # Should appear exactly once (between two words)
        self.assertEqual(result.count(',　 '), 1)

    def test_no_extra_japanese_spaces(self):
        """Test that there are no unwanted Japanese spaces (　) between kanji pairs."""
        card = CardInfo(1, '現[げん]在[ざい]地[ち]', 5.0)
        kanji_to_color = {'現': 'lightgreen', '在': 'lightblue', '地': 'pink'}

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)

        # Should not have Japanese space between any pairs
        self.assertNotIn('現[げん]　在[ざい]', result)
        self.assertNotIn('在[ざい]　地[ち]', result)
        self.assertNotIn(']　', result)  # No Japanese space after any closing bracket

    def test_color_highlighting_for_shared_kanji(self):
        """Test that shared kanji are wrapped in colored span tags."""
        card = CardInfo(1, '大[だい]学[がく]', 5.0)
        kanji_to_color = {'大': 'lightgreen', '学': 'lightblue'}

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)

        # Should have span tags with colors
        self.assertIn('<span style="color: lightgreen;">大[だい]</span>', result)
        self.assertIn('<span style="color: lightblue;">学[がく]</span>', result)

    def test_non_shared_kanji_not_highlighted(self):
        """Test that kanji not in shared_kanji_colors are not highlighted."""
        card = CardInfo(1, '大[だい]学[がく]生[せい]', 5.0)
        kanji_to_color = {'大': 'lightgreen'}  # Only 大 is shared

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)

        # 大 should be highlighted
        self.assertIn('<span style="color: lightgreen;">大[だい]</span>', result)
        # 学 and 生 should NOT be highlighted (no span tags)
        self.assertIn('学[がく]', result)
        self.assertNotIn('<span style="color:', result.split('大[だい]</span>')[1].split(',')[0])

    def test_multiple_related_words_spacing(self):
        """Test spacing with multiple related words."""
        card1 = CardInfo(1, '物[もの]忘[わす]', 8.0)
        card2 = CardInfo(2, '置[お]去[さ]', 7.0)
        card3 = CardInfo(3, '現[げん]在[ざい]地[ち]', 6.0)

        related_cards_list = [
            (card1, {'忘'}),
            (card2, {'去'}),
            (card3, {'在'}),
        ]

        kanji_to_color = {'忘': 'lightgreen', '去': 'lightblue', '在': 'pink'}

        result = _format_related_words(related_cards_list, kanji_to_color, self.kanji_readings)

        # Should have exactly 2 separators (between 3 words)
        self.assertEqual(result.count(',　 '), 2)
        # Should not have Japanese spaces within words
        self.assertNotIn('物[もの]　忘[わす]', result)
        self.assertNotIn('置[お]　去[さ]', result)
        self.assertNotIn('現[げん]　在[ざい]', result)
        self.assertNotIn('在[ざい]　地[ち]', result)

    def test_kanji_meanings_html_generation(self):
        """Test that kanji meanings HTML is generated correctly."""
        card = CardInfo(1, '大[だい]学[がく]', 5.0)
        card.related_cards_known = []
        card.related_cards_unknown = []

        _, _, meanings_html = format_card_html(card, self.kanji_meanings, self.kanji_readings)

        # Should have meanings for both kanji
        self.assertIn('大', meanings_html)
        self.assertIn('学', meanings_html)
        # Should have colored spans
        self.assertIn('<span style="color:', meanings_html)
        # Should have meaning text
        self.assertTrue(
            'large' in meanings_html or 'big' in meanings_html,
            "Should contain meaning for 大"
        )
        self.assertTrue(
            'study' in meanings_html or 'learning' in meanings_html,
            "Should contain meaning for 学"
        )

    def test_color_coordination_across_fields(self):
        """Test that colors are consistent between related words and meanings."""
        main_card = CardInfo(1, '大[だい]学[がく]', 10.0)
        related_card = CardInfo(2, '大[だい]人[じん]', 8.0)

        main_card.related_cards_known = [(related_card, {'大'})]
        main_card.related_cards_unknown = []

        known_html, _, meanings_html = format_card_html(
            main_card, self.kanji_meanings, self.kanji_readings
        )

        # Extract color used for 大 in related words
        if '<span style="color: lightgreen;">大' in known_html:
            color = 'lightgreen'
        elif '<span style="color: lightblue;">大' in known_html:
            color = 'lightblue'
        else:
            # Find any color used for 大
            import re
            match = re.search(r'<span style="color: (\w+);">大', known_html)
            self.assertIsNotNone(match, "大 should be colored in related words")
            color = match.group(1)

        # Same color should be used in meanings
        self.assertIn(f'<span style="color: {color};">大</span>', meanings_html)

    def test_empty_related_cards(self):
        """Test that empty related cards list returns empty string."""
        result = _format_related_words([], {}, self.kanji_readings)
        self.assertEqual(result, "")

    def test_empty_furigana_text(self):
        """Test handling of cards with no furigana text."""
        card = CardInfo(1, '', 5.0)
        kanji_to_color = {}

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)
        self.assertEqual(result, "")

    def test_three_kanji_word_no_internal_spaces(self):
        """Test that a three-kanji word has no spaces between any pairs."""
        card = CardInfo(1, '持[じ]命[めい]装[そう]置[ち]', 5.0)
        kanji_to_color = {'持': 'lightgreen', '命': 'lightblue', '装': 'pink', '置': 'lightyellow'}

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)

        # Should not have any Japanese spaces
        self.assertNotIn('　', result)
        # Should have all four kanji
        self.assertIn('持[じ]', result)
        self.assertIn('命[めい]', result)
        self.assertIn('装[そう]', result)
        self.assertIn('置[ち]', result)


if __name__ == '__main__':
    unittest.main()
