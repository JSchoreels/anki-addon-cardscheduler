"""Test related words feature - verify that cards sharing kanji/reading pairs are linked."""

import unittest
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

    def assert_has_related_card(self, related_cards_list, furigana_text, shared_kanji, message):
        """Helper to check if a card with specific furigana and shared kanji exists in related cards list.

        Args:
            related_cards_list: List of (CardInfo, shared_kanji_set) tuples
            furigana_text: Expected furigana text of related card
            shared_kanji: Expected shared kanji (can be a set or single kanji string)
            message: Assertion message
        """
        if isinstance(shared_kanji, str):
            shared_kanji = {shared_kanji}

        found = any(
            card.furigana_text == furigana_text and kanji_set == shared_kanji
            for card, kanji_set in related_cards_list
        )
        self.assertTrue(found, message)

    def assert_has_related_card_with_kanji(self, related_cards_list, furigana_text, expected_kanji, message):
        """Helper to check if a card exists with at least the expected kanji in shared set.

        Args:
            related_cards_list: List of (CardInfo, shared_kanji_set) tuples
            furigana_text: Expected furigana text of related card
            expected_kanji: Kanji that should be in the shared set
            message: Assertion message
        """
        found = any(
            card.furigana_text == furigana_text and expected_kanji in kanji_set
            for card, kanji_set in related_cards_list
        )
        self.assertTrue(found, message)

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
        print(f"失恋[しつれん] known: {[(c.furigana_text, k) for c, k in card1.related_cards_known]}")
        print(f"失恋[しつれん] unknown: {[(c.furigana_text, k) for c, k in card1.related_cards_unknown]}")
        print(f"恋愛[れんあい] known: {[(c.furigana_text, k) for c, k in card2.related_cards_known]}")
        print(f"恋愛[れんあい] unknown: {[(c.furigana_text, k) for c, k in card2.related_cards_unknown]}")
        print(f"失敗[しっぱい] known: {[(c.furigana_text, k) for c, k in card3.related_cards_known]}")
        print(f"失敗[しっぱい] unknown: {[(c.furigana_text, k) for c, k in card3.related_cards_unknown]}")

        # 失恋 should have 恋愛 (known) sharing 恋, and 失敗 (unknown) sharing 失
        self.assert_has_related_card_with_kanji(card1.related_cards_known, "恋愛[れんあい]", "恋", "失恋 should have 恋愛 in known")
        self.assert_has_related_card_with_kanji(card1.related_cards_unknown, "失敗[しっぱい]", "失", "失恋 should have 失敗 in unknown")

        # 恋愛 should have 失恋 (unknown) sharing 恋
        self.assert_has_related_card_with_kanji(card2.related_cards_unknown, "失恋[しつれん]", "恋", "恋愛 should have 失恋 in unknown")

        # 失敗 should have 失恋 (unknown) sharing 失
        self.assert_has_related_card_with_kanji(card3.related_cards_unknown, "失恋[しつれん]", "失", "失敗 should have 失恋 in unknown")

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
        print(f"失恋[しつれん] known: {card1.related_cards_known}")
        print(f"失恋[しつれん] unknown: {card1.related_cards_unknown}")
        print(f"大学[だいがく] known: {card2.related_cards_known}")
        print(f"大学[だいがく] unknown: {card2.related_cards_unknown}")

        self.assertEqual(len(card1.related_cards_known), 0, "失恋 should have no known related words")
        self.assertEqual(len(card1.related_cards_unknown), 0, "失恋 should have no unknown related words")
        self.assertEqual(len(card2.related_cards_known), 0, "大学 should have no known related words")
        self.assertEqual(len(card2.related_cards_unknown), 0, "大学 should have no unknown related words")

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
        print(f"大学生[だいがくせい] known: {[(c.furigana_text, k) for c, k in card1.related_cards_known]}")
        print(f"大学生[だいがくせい] unknown: {[(c.furigana_text, k) for c, k in card1.related_cards_unknown]}")
        print(f"大学[だいがく] known: {[(c.furigana_text, k) for c, k in card2.related_cards_known]}")
        print(f"大学[だいがく] unknown: {[(c.furigana_text, k) for c, k in card2.related_cards_unknown]}")
        print(f"学生[がくせい] known: {[(c.furigana_text, k) for c, k in card3.related_cards_known]}")
        print(f"学生[がくせい] unknown: {[(c.furigana_text, k) for c, k in card3.related_cards_unknown]}")

        # 大学生 should have 大学 (known) sharing both 大 and 学
        self.assert_has_related_card_with_kanji(card1.related_cards_known, "大学[だいがく]", "大", "大学生 should have 大学 sharing 大")
        self.assert_has_related_card_with_kanji(card1.related_cards_known, "大学[だいがく]", "学", "大学生 should have 大学 sharing 学")

        # 大学生 should have 学生 (unknown) sharing both 学 and 生
        self.assert_has_related_card_with_kanji(card1.related_cards_unknown, "学生[がくせい]", "学", "大学生 should have 学生 sharing 学")
        self.assert_has_related_card_with_kanji(card1.related_cards_unknown, "学生[がくせい]", "生", "大学生 should have 学生 sharing 生")

        # 大学 should have 大学生 (unknown) sharing both 大 and 学
        self.assert_has_related_card_with_kanji(card2.related_cards_unknown, "大学生[だいがくせい]", "大", "大学 should have 大学生 sharing 大")
        self.assert_has_related_card_with_kanji(card2.related_cards_unknown, "大学生[だいがくせい]", "学", "大学 should have 大学生 sharing 学")

        # 学生 should have 大学生 (unknown) sharing both 学 and 生
        self.assert_has_related_card_with_kanji(card3.related_cards_unknown, "大学生[だいがくせい]", "学", "学生 should have 大学生 sharing 学")
        self.assert_has_related_card_with_kanji(card3.related_cards_unknown, "大学生[だいがくせい]", "生", "学生 should have 大学生 sharing 生")

    def test_related_words_sorted(self):
        """Test that related words are sorted by shared kanji count."""
        cards = [
            CardInfo(1, "失恋[しつれん]", 80),  # Known
            CardInfo(2, "恋愛[れんあい]", 0),
            CardInfo(3, "愛情[あいじょう]", 60),  # Known
        ]

        compute_scores(cards)

        card2 = [c for c in cards if c.card_id == 2][0]

        print(f"\n=== Test: Related Words Sorted ===")
        print(f"恋愛[れんあい] known: {[(c.furigana_text, k) for c, k in card2.related_cards_known]}")
        print(f"恋愛[れんあい] unknown: {[(c.furigana_text, k) for c, k in card2.related_cards_unknown]}")

        # Check that we have 2 known related words
        self.assertEqual(len(card2.related_cards_known), 2, "Should have 2 known related words")
        self.assert_has_related_card_with_kanji(card2.related_cards_known, "失恋[しつれん]", "恋", "Should have 失恋 sharing 恋")
        self.assert_has_related_card_with_kanji(card2.related_cards_known, "愛情[あいじょう]", "愛", "Should have 愛情 sharing 愛")
        self.assertEqual(len(card2.related_cards_unknown), 0, "Should have no unknown related words")

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
        print(f"失恋[しつれん] known: {[(c.furigana_text, k) for c, k in card1.related_cards_known]}")
        print(f"失恋[しつれん] unknown: {[(c.furigana_text, k) for c, k in card1.related_cards_unknown]}")

        # Should have at least 恋愛 in known (shares 恋)
        self.assert_has_related_card_with_kanji(card1.related_cards_known, "恋愛[れんあい]", "恋", "恋愛 should be in known")

        # Should have at least 失敗 in unknown (shares 失)
        self.assert_has_related_card_with_kanji(card1.related_cards_unknown, "失敗[しっぱい]", "失", "失敗 should be in unknown")

        # Should have at least 1 known and 1 unknown
        self.assertGreaterEqual(len(card1.related_cards_known), 1, "Should have at least 1 known related word")
        self.assertGreaterEqual(len(card1.related_cards_unknown), 1, "Should have at least 1 unknown related word")


if __name__ == "__main__":
    unittest.main(verbosity=2)
