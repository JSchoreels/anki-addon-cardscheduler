"""
Tests for learning order calculation based on score and unlock potential.
"""

import unittest

from cardscheduler.__init__ import (
    CardInfo,
    compute_scores,
    assign_positions_to_new_cards,
    load_kanji_dictionnary_readings,
)


class TestLearningOrder(unittest.TestCase):
    """Test cases for learning order position calculation."""

    def setUp(self):
        """Set up test fixtures."""
        self.kanji_readings = load_kanji_dictionnary_readings()

    def test_position_assigned_to_all_cards(self):
        """Test that all cards get a position assigned."""
        cards = [
            CardInfo(1, "学校[がっこう]", 10),
            CardInfo(2, "学生[がくせい]", 0),
            CardInfo(3, "校長[こうちょう]", 5),
        ]

        compute_scores(cards)

        # Assign positions to all cards (simulate all cards are new)
        new_card_ids = {card.card_id for card in cards}
        assign_positions_to_new_cards(cards, new_card_ids)

        # All cards should have a position > 0
        for card in cards:
            self.assertGreater(card.position, 0)

        # Positions should be unique
        positions = [card.position for card in cards]
        self.assertEqual(len(positions), len(set(positions)))

    def test_higher_score_gets_position_1(self):
        """Cards with higher scores should get lower position numbers (position 1 = highest score)."""
        cards = [
            CardInfo(1, "学校[がっこう]", 10),    # Known: high score -> position 1
            CardInfo(2, "学生[がくせい]", 0),     # Unknown: low score -> position 3
            CardInfo(3, "校長[こうちょう]", 5),   # Partially known: medium score -> position 2
        ]

        compute_scores(cards)

        # Assign positions to all cards (simulate all cards are new)
        new_card_ids = {card.card_id for card in cards}
        assign_positions_to_new_cards(cards, new_card_ids)

        # Card 1 (highest score) should have position 1
        # Card 3 (medium score) should have position 2
        # Card 2 (lowest score) should have position 3
        card1 = [c for c in cards if c.card_id == 1][0]
        card2 = [c for c in cards if c.card_id == 2][0]
        card3 = [c for c in cards if c.card_id == 3][0]

        self.assertLess(card1.position, card3.position)
        self.assertLess(card3.position, card2.position)

    def test_same_score_higher_unlock_potential_wins(self):
        """For cards with same score, higher unlock potential gets lower position (higher priority)."""
        cards = [
            CardInfo(1, "学校[がっこう]", 0),     # Unknown: 学 unknown, 校 known
            CardInfo(2, "学園[がくえん]", 0),     # Unknown: 学 unknown, 園 unknown
            CardInfo(3, "校長[こうちょう]", 10),  # Known: provides 校
            CardInfo(4, "園芸[えんげい]", 0),     # Unknown: 園 unknown, 芸 unknown
        ]

        compute_scores(cards)

        # Assign positions to all cards (simulate all cards are new)
        new_card_ids = {card.card_id for card in cards}
        assign_positions_to_new_cards(cards, new_card_ids)

        # Cards 1, 2, 4 all have score = 0
        card1 = [c for c in cards if c.card_id == 1][0]
        card2 = [c for c in cards if c.card_id == 2][0]
        card4 = [c for c in cards if c.card_id == 4][0]

        self.assertEqual(card1.score, 0)
        self.assertEqual(card2.score, 0)
        self.assertEqual(card4.score, 0)

        # Among cards with score=0, the one with higher unlock potential
        # should get a lower position number (higher priority)
        # Card 1 has unlock potential >= 1 (can unlock itself since 校 is known)
        # The card with higher unlock_potential should have lower position
        if card1.unlock_potential > card2.unlock_potential:
            self.assertLess(card1.position, card2.position)

    def test_position_numbers_sequential(self):
        """Position numbers should be sequential starting from 1."""
        cards = [
            CardInfo(1, "一年[いちねん]", 20),
            CardInfo(2, "二年[にねん]", 15),
            CardInfo(3, "三年[さんねん]", 0),
            CardInfo(4, "四年[よねん]", 0),
            CardInfo(5, "五年[ごねん]", 0),
        ]

        compute_scores(cards)

        # Assign positions to all cards (simulate all cards are new)
        new_card_ids = {card.card_id for card in cards}
        assign_positions_to_new_cards(cards, new_card_ids)

        positions = sorted([card.position for card in cards])
        expected_positions = list(range(1, len(cards) + 1))

        self.assertEqual(positions, expected_positions)

    def test_integration_ordering_example(self):
        """Integration test with realistic scenario."""
        cards = [
            # Known cards (high score, high priority - low position numbers)
            CardInfo(1, "一年[いちねん]", 50),    # Score will be high -> position 1
            CardInfo(2, "二年[にねん]", 40),      # Score will be high -> position 2

            # Unknown cards (score = 0, low priority - high position numbers)
            CardInfo(3, "三年[さんねん]", 0),     # 三 unknown, 年 known
            CardInfo(4, "四年[よねん]", 0),       # 四 unknown, 年 known
            CardInfo(5, "五年[ごねん]", 0),       # 五 unknown, 年 known

            # Provides known kanji
            CardInfo(6, "年月[ねんげつ]", 30),    # Provides 年
        ]

        compute_scores(cards)

        # Assign positions to all cards (simulate all cards are new)
        new_card_ids = {card.card_id for card in cards}
        assign_positions_to_new_cards(cards, new_card_ids)

        # Known cards (1, 2, 6) should have lower positions (higher priority) than unknown cards (3, 4, 5)
        unknown_cards = [c for c in cards if c.card_id in [3, 4, 5]]
        known_cards = [c for c in cards if c.card_id in [1, 2, 6]]

        max_known_position = max(c.position for c in known_cards)
        min_unknown_position = min(c.position for c in unknown_cards)

        self.assertLess(max_known_position, min_unknown_position,
                       "Known cards should have lower positions (higher priority) than unknown cards")


if __name__ == "__main__":
    unittest.main()
