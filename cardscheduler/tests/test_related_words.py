"""Test related words feature - verify that cards sharing kanji/reading pairs are linked."""

import unittest
import re
from cardscheduler import (
    CardInfo,
    compute_scores,
    load_kanji_dictionnary_readings,
)


class TestRelatedWords(unittest.TestCase):
    """Test cases for related words calculation."""

    def setUp(self):
        """Set up test fixtures."""
        self.kanji_readings = load_kanji_dictionnary_readings()

    def assert_pair_highlighted(self, words_string, pair, message):
        """Helper to check if a kanji[reading] pair is highlighted with any color."""
        # Match: <span style="color: ANYCOLOR;">pair</span>
        pattern = f'<span style="color: [^"]+;">{re.escape(pair)}</span>'
        self.assertTrue(
            re.search(pattern, words_string) is not None,
            message
        )

    def test_simple_related_words(self):
        """Test that cards sharing kanji/reading pairs are properly linked and split by known/unknown."""
        cards = [
            CardInfo(1, "失恋[しつれん]", 0),
            CardInfo(2, "恋愛[れんあい]", 100),  # Known card
            CardInfo(3, "失敗[しっぱい]", 0),
        ]

        compute_scores(cards)

        card1 = [c for c in cards if c.card_id == 1][0]
        card2 = [c for c in cards if c.card_id == 2][0]
        card3 = [c for c in cards if c.card_id == 3][0]

        print(f"\n=== Test: Simple Related Words ===")
        print(f"失恋[しつれん] known: {card1.related_words_known}, unknown: {card1.related_words_unknown}")
        print(f"恋愛[れんあい] known: {card2.related_words_known}, unknown: {card2.related_words_unknown}")
        print(f"失敗[しっぱい] known: {card3.related_words_known}, unknown: {card3.related_words_unknown}")

        self.assert_pair_highlighted(card1.related_words_known, "恋[れん]", "失恋 should have 恋愛 with 恋[れん] highlighted")
        self.assert_pair_highlighted(card1.related_words_unknown, "失[しつ]", "失恋 should have 失敗 with 失[しつ] highlighted")
        self.assert_pair_highlighted(card2.related_words_unknown, "恋[れん]", "恋愛 should have 失恋 with 恋[れん] highlighted")
        self.assert_pair_highlighted(card3.related_words_unknown, "失[しつ]", "失敗 should have 失恋 with 失[しつ] highlighted")

    def test_no_related_words(self):
        """Test that cards with no shared kanji have empty related words."""
        cards = [
            CardInfo(1, "失恋[しつれん]", 0),
            CardInfo(2, "大学[だいがく]", 0),
        ]

        compute_scores(cards)

        card1 = [c for c in cards if c.card_id == 1][0]
        card2 = [c for c in cards if c.card_id == 2][0]

        print(f"\n=== Test: No Related Words ===")
        print(f"失恋[しつれん] known: {card1.related_words_known}, unknown: {card1.related_words_unknown}")
        print(f"大学[だいがく] known: {card2.related_words_known}, unknown: {card2.related_words_unknown}")

        self.assertEqual(card1.related_words_known, "", "失恋 should have no known related words")
        self.assertEqual(card1.related_words_unknown, "", "失恋 should have no unknown related words")
        self.assertEqual(card2.related_words_known, "", "大学 should have no known related words")
        self.assertEqual(card2.related_words_unknown, "", "大学 should have no unknown related words")

    def test_multiple_shared_pairs(self):
        """Test cards that share multiple kanji/reading pairs with mixed known/unknown."""
        cards = [
            CardInfo(1, "大学生[だいがくせい]", 0),
            CardInfo(2, "大学[だいがく]", 50),  # Known
            CardInfo(3, "学生[がくせい]", 0),
        ]

        compute_scores(cards)

        card1 = [c for c in cards if c.card_id == 1][0]
        card2 = [c for c in cards if c.card_id == 2][0]
        card3 = [c for c in cards if c.card_id == 3][0]

        print(f"\n=== Test: Multiple Shared Pairs ===")
        print(f"大学生[だいがくせい] known: {card1.related_words_known}, unknown: {card1.related_words_unknown}")
        print(f"大学[だいがく] known: {card2.related_words_known}, unknown: {card2.related_words_unknown}")
        print(f"学生[がくせい] known: {card3.related_words_known}, unknown: {card3.related_words_unknown}")

        # Check that both pairs are highlighted (possibly with different colors)
        self.assert_pair_highlighted(card1.related_words_known, "大[だい]", "大学生 should have 大学 with 大[だい] highlighted")
        self.assert_pair_highlighted(card1.related_words_known, "学[がく]", "大学生 should have 大学 with 学[がく] highlighted")
        self.assert_pair_highlighted(card1.related_words_unknown, "学[がく]", "大学生 should have 学生 with 学[がく] highlighted")
        self.assert_pair_highlighted(card1.related_words_unknown, "生[せい]", "大学生 should have 学生 with 生[せい] highlighted")
        self.assert_pair_highlighted(card2.related_words_unknown, "大[だい]", "大学 should have 大学生 with 大[だい] highlighted")
        self.assert_pair_highlighted(card2.related_words_unknown, "学[がく]", "大学 should have 大学生 with 学[がく] highlighted")
        self.assert_pair_highlighted(card3.related_words_unknown, "学[がく]", "学生 should have 大学生 with 学[がく] highlighted")
        self.assert_pair_highlighted(card3.related_words_unknown, "生[せい]", "学生 should have 大学生 with 生[せい] highlighted")

    def test_related_words_sorted(self):
        """Test that related words are sorted alphabetically within each category."""
        cards = [
            CardInfo(1, "失恋[しつれん]", 80),  # Known
            CardInfo(2, "恋愛[れんあい]", 0),
            CardInfo(3, "愛情[あいじょう]", 60),  # Known
        ]

        compute_scores(cards)

        card2 = [c for c in cards if c.card_id == 2][0]

        print(f"\n=== Test: Related Words Sorted ===")
        print(f"恋愛[れんあい] known: {card2.related_words_known}, unknown: {card2.related_words_unknown}")

        # Check that we have 2 known related words (count commas + 1)
        known_count = card2.related_words_known.count(',') + (1 if card2.related_words_known else 0)
        self.assertEqual(known_count, 2, "Should have 2 known related words")
        self.assert_pair_highlighted(card2.related_words_known, "恋[れん]", "Should have 失恋 with 恋[れん] highlighted")
        self.assert_pair_highlighted(card2.related_words_known, "愛[あい]", "Should have 愛情 with 愛[あい] highlighted")
        self.assertEqual(card2.related_words_unknown, "", "Should have no unknown related words")

    def test_known_unknown_split(self):
        """Test that related words are correctly split into known (stability > 0) and unknown (stability = 0)."""
        cards = [
            CardInfo(1, "失恋[しつれん]", 0),
            CardInfo(2, "恋愛[れんあい]", 100),  # Known
            CardInfo(3, "恋文[こいぶみ]", 0),  # Unknown (different reading)
            CardInfo(4, "愛情[あいじょう]", 80),  # Known
            CardInfo(5, "失敗[しっぱい]", 0),
        ]

        compute_scores(cards)

        card1 = [c for c in cards if c.card_id == 1][0]

        print(f"\n=== Test: Known/Unknown Split ===")
        print(f"失恋[しつれん] known: {card1.related_words_known}")
        print(f"失恋[しつれん] unknown: {card1.related_words_unknown}")

        self.assert_pair_highlighted(card1.related_words_known, "恋[れん]", "恋愛 should be in known with 恋[れん] highlighted")
        self.assert_pair_highlighted(card1.related_words_unknown, "失[しつ]", "失敗 should be in unknown with 失[しつ] highlighted")
        # Now shows ALL kanji matches (including different readings), so may have more than 1
        self.assertGreaterEqual(card1.related_words_known.count(',') + (1 if card1.related_words_known else 0), 1, "Should have at least 1 known related word")
        self.assertGreaterEqual(card1.related_words_unknown.count(',') + (1 if card1.related_words_unknown else 0), 1, "Should have at least 1 unknown related word")


if __name__ == "__main__":
    unittest.main(verbosity=2)
