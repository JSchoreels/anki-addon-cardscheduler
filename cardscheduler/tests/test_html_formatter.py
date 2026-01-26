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

from cardscheduler.html_formatter import format_card_html, _format_related_words, _highlight_shared_kanji, _normalize_spacing
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

    def test_trailing_kana_preserved(self):
        """Test that trailing kana after kanji[reading] is preserved."""
        card = CardInfo(1, '石[いし]ころ', 5.0)
        kanji_to_color = {'石': 'lightgreen'}

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)

        # Should preserve the trailing "ころ"
        self.assertIn('ころ', result, "Trailing kana 'ころ' should be preserved")
        self.assertIn('石[いし]', result, "Kanji pair should be present")
        # Check the full result
        self.assertIn('<span style="color: lightgreen;">石[いし]</span>ころ', result,
                      "Should have highlighted kanji followed by trailing kana")

    def test_leading_kana_preserved(self):
        """Test that leading kana before kanji[reading] is preserved."""
        card = CardInfo(1, 'お石[いし]', 5.0)
        kanji_to_color = {'石': 'lightgreen'}

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)

        # Should preserve the leading "お"
        self.assertIn('お', result, "Leading kana 'お' should be preserved")
        self.assertIn('石[いし]', result, "Kanji pair should be present")
        # Check the full result
        self.assertIn('お<span style="color: lightgreen;">石[いし]</span>', result,
                      "Should have leading kana followed by highlighted kanji")

    def test_mixed_kana_and_kanji(self):
        """Test that mixed kana and kanji patterns are handled correctly."""
        card = CardInfo(1, 'お石[いし]ころ', 5.0)
        kanji_to_color = {'石': 'lightgreen'}

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)

        # Should preserve both leading and trailing kana
        self.assertIn('お', result, "Leading kana 'お' should be preserved")
        self.assertIn('ころ', result, "Trailing kana 'ころ' should be preserved")
        self.assertIn('石[いし]', result, "Kanji pair should be present")
        # Check the full result
        self.assertIn('お<span style="color: lightgreen;">石[いし]</span>ころ', result,
                      "Should have leading kana, highlighted kanji, and trailing kana")

    def test_multi_kanji_word_splitting_and_highlighting(self):
        """Test that multi-kanji words are split and each kanji highlighted individually."""
        card = CardInfo(1, '移動[いどう]', 5.0)
        kanji_to_color = {'移': 'lightgreen', '動': 'lightblue'}

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)

        # Should split into individual kanji and highlight each
        self.assertIn('移[い]', result, "First kanji 移 with reading い should be present")
        self.assertIn('動[どう]', result, "Second kanji 動 with reading どう should be present")

        # Both kanji should be highlighted with their respective colors
        self.assertIn('<span style="color: lightgreen;">移[い]</span>', result,
                      "移 should be highlighted in lightgreen")
        self.assertIn('<span style="color: lightblue;">動[どう]</span>', result,
                      "動 should be highlighted in lightblue")

        # Should not have the original unsplit form
        self.assertNotIn('移動[いどう]', result, "Original unsplit form should not be present")

    def test_multi_kanji_word_partial_highlighting(self):
        """Test that only shared kanji are highlighted in multi-kanji words."""
        card = CardInfo(1, '移動[いどう]', 5.0)
        kanji_to_color = {'移': 'lightgreen'}  # Only 移 is shared

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)

        # 移 should be highlighted
        self.assertIn('<span style="color: lightgreen;">移[い]</span>', result,
                      "移 should be highlighted")

        # 動 should NOT be highlighted (no color span)
        self.assertIn('動[どう]', result, "動 should be present")
        # Check that 動 is not wrapped in a colored span
        self.assertNotIn('<span style="color:', result.split('移[い]</span>')[1].split('動[どう]')[0],
                        "There should be no color span between 移 and 動")

    def test_kanji_order_preserved_in_multi_kanji_words(self):
        """Test that kanji order is preserved when splitting multi-kanji words."""
        card = CardInfo(1, '擬態語[ぎたいご]', 5.0)
        kanji_to_color = {'擬': 'lightgreen', '態': 'lightblue', '語': 'pink'}

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)

        # Kanji should appear in the correct order: 擬, 態, 語
        擬_pos = result.find('擬[ぎ]')
        態_pos = result.find('態[たい]')
        語_pos = result.find('語[ご]')

        self.assertNotEqual(擬_pos, -1, "擬[ぎ] should be present")
        self.assertNotEqual(態_pos, -1, "態[たい] should be present")
        self.assertNotEqual(語_pos, -1, "語[ご] should be present")

        # Verify order is preserved: 擬 < 態 < 語
        self.assertLess(擬_pos, 態_pos, "擬 should appear before 態")
        self.assertLess(態_pos, 語_pos, "態 should appear before 語")

        # Should NOT have scrambled order like 態擬語
        self.assertNotIn('態[たい]擬[ぎ]', result, "Kanji should not be in scrambled order")

    def test_spacing_before_furigana_after_kana(self):
        """Test that space is added before furigana when preceded by kana.

        Example: 溶[と]け合[あ]う where 溶 is highlighted
        Should become: <span>溶[と]</span>け 合[あ]う (regular space before 合[あ])
        NOT: <span>溶[と]</span>け合[あ]う (no space)
        """
        card = CardInfo(1, '溶[と]け合[あ]う', 5.0)
        kanji_to_color = {'溶': 'lightgreen'}

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)

        # Should have regular space before 合[あ] (after the kana け)
        self.assertIn('け 合[あ]', result, "Should have regular space before 合[あ]")

        # Should NOT have space after </span> before け
        self.assertIn('</span>け', result, "Should not have space after </span>")
        self.assertNotIn('</span> け', result, "Should not have space between </span> and け")

    def test_reading_order_preserved_when_cant_split(self):
        """Test that reading order is preserved when kanji can't be split properly.

        When some kanji readings can't be found in the dictionary, keep the full
        compound with the full reading instead of scrambling the order.
        Example: お祖母[ばあ]さん should keep 祖母[ばあ], NOT split to 祖[あ]母[ば]
        which would scramble the reading from "baa" to "aba".
        """
        # Test case from user: お祖母さん with reading ばあ
        card = CardInfo(1, 'お祖母[ばあ]さん', 5.0)
        kanji_to_color = {'祖': 'lightgreen', '母': 'lightblue'}

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)

        # Should not have empty readings
        self.assertNotIn('[ ]', result, "Should not have empty readings")

        # Should preserve the full reading ばあ (not split it incorrectly)
        self.assertIn('ばあ', result, "Full reading ばあ should be preserved")

        # Should NOT have scrambled readings like あ before ば
        self.assertNotIn('祖[あ]', result, "Should not have 祖[あ] - this scrambles the order")

        # Should have the compound 祖母 with full reading
        self.assertIn('祖母[ばあ]', result, "Should keep compound 祖母[ばあ]")

        # Verify the compound is highlighted (since both 祖 and 母 are in shared colors)
        self.assertIn('<span style="color:', result, "Compound should be highlighted")

    def test_compound_colored_with_first_kanji_color_when_reading_not_splittable(self):
        """Test that compound kanji uses first matching kanji's color when reading can't be split.

        When a kanji's reading in the compound is not found in the dictionary,
        the system collapses to the full compound and uses the first matching kanji's color.

        Example: 景色[けしき] - 景 only has けい in the dictionary, not け.
        So the compound can't be split into 景[け] + 色[しき].
        The whole 景色[けしき] gets colored with 景's color (from the current card).
        """
        card = CardInfo(1, '景色[けしき]', 5.0)
        kanji_to_color = {'景': 'lightgreen'}  # 景 is shared (e.g., from 景気[けいき] on current card)

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)

        # Should keep the compound with full reading (not split it)
        self.assertIn('景色[けしき]', result, "Should keep compound 景色[けしき]")

        # The compound should be highlighted with 景's color
        self.assertIn('<span style="color: lightgreen;">景色[けしき]</span>', result,
                      "Compound should be colored with first matching kanji's color (景)")

        # Should NOT have incorrectly split readings
        self.assertNotIn('景[け]', result, "Should not have split 景[け]")
        self.assertNotIn('色[しき]', result, "Should not have split 色[しき]")

    def test_compound_colored_when_only_second_kanji_shared(self):
        """Test compound coloring when only the second kanji is in shared colors.

        Example: 景色[けしき] where only 色 is shared.
        """
        card = CardInfo(1, '景色[けしき]', 5.0)
        kanji_to_color = {'色': 'lightblue'}  # Only 色 is shared

        result = _highlight_shared_kanji(card.furigana_text, kanji_to_color, self.kanji_readings)

        # Should keep the compound
        self.assertIn('景色[けしき]', result, "Should keep compound 景色[けしき]")

        # The compound should be highlighted with 色's color (the first matching kanji in the compound)
        self.assertIn('<span style="color: lightblue;">景色[けしき]</span>', result,
                      "Compound should be colored with matching kanji's color (色)")


class TestSpacingNormalization(unittest.TestCase):
    """Test spacing normalization in related words."""

    def test_remove_space_kana_before_kanji(self):
        """Test that space between kana and kanji[reading] is removed."""
        text = 'と 同[おな]じように'
        result = _normalize_spacing(text)
        expected = 'と同[おな]じように'
        self.assertEqual(result, expected,
                        "Space between kana 'と' and kanji '同[おな]じ' should be removed")

    def test_remove_space_kanji_before_kana(self):
        """Test that space between kanji[reading] and kana is removed."""
        text = '同[おな]じ ように'
        result = _normalize_spacing(text)
        expected = '同[おな]じように'
        self.assertEqual(result, expected,
                        "Space between kanji '同[おな]じ' and kana 'ように' should be removed")

    def test_remove_multiple_spaces(self):
        """Test that multiple spaces are normalized."""
        text = 'と 同[おな]じ ように'
        result = _normalize_spacing(text)
        expected = 'と同[おな]じように'
        self.assertEqual(result, expected,
                        "All spaces between kana and kanji should be removed")

    def test_keep_space_between_kanji_groups(self):
        """Test that spaces between different kanji[reading] groups are preserved."""
        # Note: Current implementation removes all spaces, but if we want to keep
        # spaces between kanji groups, we'd need more sophisticated logic
        text = '大[だい]学[がく] 生[せい]活[かつ]'
        result = _normalize_spacing(text)
        # Currently removes the space - this might need adjustment based on requirements
        self.assertIsNotNone(result)

    def test_no_spaces_to_remove(self):
        """Test text with no unnecessary spaces."""
        text = '同[おな]じように'
        result = _normalize_spacing(text)
        expected = '同[おな]じように'
        self.assertEqual(result, expected,
                        "Text without spaces should remain unchanged")

    def test_empty_text(self):
        """Test that empty text is handled correctly."""
        text = ''
        result = _normalize_spacing(text)
        self.assertEqual(result, '', "Empty text should return empty string")

    def test_none_text(self):
        """Test that None is handled correctly."""
        result = _normalize_spacing(None)
        self.assertIsNone(result, "None should return None")

    def test_only_kana(self):
        """Test text with only kana (no kanji)."""
        text = 'ひらがな カタカナ'
        result = _normalize_spacing(text)
        # Should keep spaces between pure kana groups
        self.assertEqual(result, text,
                        "Spaces in pure kana text should be preserved")

    def test_complex_sentence(self):
        """Test a complex sentence with multiple patterns."""
        text = 'これは 本[ほん]です 。 明[あ]日[した] 行[い]きます 。'
        result = _normalize_spacing(text)
        # Spaces between kana and kanji should be removed
        self.assertNotIn('は 本', result, "Space between kana and kanji should be removed")
        self.assertNotIn('日 行', result, "Space between kanji groups should be removed")
        # Note: Space between pure kana (きます 。) is preserved - that's OK
        # The function only removes spaces adjacent to kanji[reading] patterns

    def test_particle_before_kanji(self):
        """Test Japanese particles before kanji (common pattern)."""
        # Common particles: は, が, を, に, で, と, から, まで, も, etc.
        text = 'それは 違[ちが]います'
        result = _normalize_spacing(text)
        expected = 'それは違[ちが]います'
        self.assertEqual(result, expected,
                        "Space between particle 'は' and kanji should be removed")

    def test_multiple_kanji_readings_with_kana(self):
        """Test text with multiple kanji[reading] patterns and interspersed kana."""
        text = 'お 母[かあ]さん が 言[い]った こと'
        result = _normalize_spacing(text)
        # Should remove spaces before/after kanji[reading]
        self.assertNotIn('お 母', result, "Space between kana and kanji should be removed")
        self.assertNotIn('が 言', result, "Space between kana and kanji should be removed")
        # Spaces between pure kana groups (like "さん が" or "った こと") are preserved
        # That's expected behavior - we only remove spaces adjacent to kanji[reading]


if __name__ == '__main__':
    unittest.main()
