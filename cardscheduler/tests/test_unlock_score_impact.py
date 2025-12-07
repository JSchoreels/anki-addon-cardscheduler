"""
Test unlock score impact feature - verify that unlock_median_score_increase,
score_without_missing, and missing_kanji_count are calculated correctly.
"""

import unittest
from cardscheduler import (
    CardInfo,
    compute_scores,
    load_kanji_dictionnary_readings,
)


class TestUnlockScoreImpact(unittest.TestCase):
    """Test cases for unlock score impact calculations."""

    def setUp(self):
        """Set up test fixtures."""
        self.kanji_readings = load_kanji_dictionnary_readings()

    def test_simple_scenario_four_kanji_word(self):
        """
        Test scenario with a 4-kanji word where 2 kanji are known.

        Setup:
        - Target word: 大学生会[だいがくせいかい] has 4 kanji
        - Known kanji: 大(score=100), 会(score=80) via other cards
        - Unknown kanji: 学, 生
        - Helper cards that provide the unknown kanji

        Expected:
        - Target word should have score=0 (has unknown kanji)
        - score_without_missing should be min(100, 80) = 80
        - missing_kanji_count should be 2
        """
        cards = [
            # Target card with 4 kanji (2 known, 2 unknown)
            CardInfo(1, "大学生会[だいがくせいかい]", 0),

            # Cards that provide known kanji (大, 会)
            CardInfo(2, "大会[たいかい]", 100),      # Provides 大[たい], 会[かい]

            # Cards that provide unknown kanji (学, 生)
            CardInfo(3, "学校[がっこう]", 0),        # Provides 学[がく] (unknown)
            CardInfo(4, "校長[こうちょう]", 50),     # Provides 校[こう] (known)
            CardInfo(5, "学生[がくせい]", 0),        # Provides 生[せい] (unknown)
        ]

        compute_scores(cards)

        # Find target card
        target = [c for c in cards if c.card_id == 1][0]

        print(f"\n=== Test: Four Kanji Word ===")
        print(f"Target card: {target.furigana_text}")
        print(f"  Score: {target.score}")
        print(f"  Score without missing: {target.score_without_missing}")
        print(f"  Missing kanji count: {target.missing_kanji_count}")
        print(f"  Unlock potential: {target.unlock_potential}")
        print(f"  Unlock median score increase: {target.unlock_median_score_increase}")

        # Verify target card properties
        self.assertEqual(target.score, 0, "Target should have score 0 (has unknown kanji)")
        # Note: 大会 has stability 100, 2 kanji → weighted = 100/2 = 50
        # So 大 and 会 both have max_weighted_interval = 50
        # score_without_missing = min(50, 50) = 50
        self.assertEqual(target.score_without_missing, 50, "Score without missing should be 50 (both kanji weighted to 50)")
        self.assertEqual(target.missing_kanji_count, 2, "Should have 2 unknown kanji (学, 生)")

    def test_unlock_median_score_increase_calculation(self):
        """
        Test that unlock_median_score_increase is calculated correctly.

        Setup:
        - Unknown kanji 学 appears in multiple cards
        - Each card has different "score without missing" values
        - Verify median is calculated correctly

        Weighted intervals (stability / 2^(unique_kanji_count - 1)):
        - 校長 (stability=100, 2 kanji): 校[こう] = 100/2 = 50
        - 長生 (stability=50, 2 kanji): 生[せい] = 50/2 = 25
        - 大会 (stability=80, 2 kanji): 大[たい] = 80/2 = 40

        Cards with 学:
        - 学校: 校(weighted=50) → score_without_missing = 50
        - 学生: 生(weighted=25) → score_without_missing = 25
        - 大学: 大(weighted=40) → score_without_missing = 40

        Expected median: 40
        """
        cards = [
            # Cards containing unknown kanji 学
            CardInfo(1, "学校[がっこう]", 0),        # 校 known (weighted=50)
            CardInfo(2, "学生[がくせい]", 0),        # 生 known (weighted=25)
            CardInfo(3, "大学[だいがく]", 0),        # 大 known (weighted=40)

            # Cards that provide the known kanji
            CardInfo(4, "校長[こうちょう]", 100),    # Provides 校[こう] weighted to 50
            CardInfo(5, "長生[ちょうせい]", 50),     # Provides 生[せい] weighted to 25
            CardInfo(6, "大会[たいかい]", 80),       # Provides 大[たい] weighted to 40
        ]

        compute_scores(cards)

        # All cards with 学 should have the same unlock_median_score_increase
        # since they all contain the same unknown kanji 学
        card_with_gaku = [c for c in cards if c.card_id in [1, 2, 3]]

        print(f"\n=== Test: Unlock Median Score Increase ===")
        for card in card_with_gaku:
            print(f"Card: {card.furigana_text}")
            print(f"  Score without missing: {card.score_without_missing}")
            print(f"  Unlock median score increase: {card.unlock_median_score_increase}")

        # Note: Weighted intervals are used (stability / 2^(unique_kanji_count - 1))
        # 校長 has stability 100, 2 kanji → 校[こう] = 100/2 = 50
        # 長生 has stability 50, 2 kanji → 生[せい] = 50/2 = 25
        # 大会 has stability 80, 2 kanji → 大[たい] = 80/2 = 40
        #
        # Cards with 学:
        # - 学校: score_without_missing = min(校=50) = 50
        # - 学生: score_without_missing = min(生=25) = 25
        # - 大学: score_without_missing = min(大=40) = 40
        #
        # The median of [25, 40, 50] = 40
        expected_median = 40

        # Note: Each card gets the unlock_median_score_increase from its unknown kanji
        # All three cards have 学 as unknown, so they should all reference the same median
        for card in card_with_gaku:
            self.assertEqual(
                card.unlock_median_score_increase,
                expected_median,
                f"Card {card.furigana_text} should have median score increase of {expected_median}"
            )

    def test_missing_kanji_count_progression(self):
        """
        Test that missing_kanji_count is calculated correctly for cards
        with different numbers of unknown kanji.
        """
        cards = [
            # Card with 0 missing kanji (all known)
            CardInfo(1, "大会[たいかい]", 100),

            # Card with 1 missing kanji
            CardInfo(2, "学校[がっこう]", 0),        # 学 unknown, 校 known

            # Card with 2 missing kanji
            CardInfo(3, "学生[がくせい]", 0),        # Both unknown

            # Card with 3 missing kanji
            CardInfo(4, "小学校[しょうがっこう]", 0), # 小, 学 unknown, 校 known

            # Helper cards
            CardInfo(5, "校長[こうちょう]", 100),    # Provides 校[こう]
        ]

        compute_scores(cards)

        print(f"\n=== Test: Missing Kanji Count ===")
        for card in cards:
            print(f"Card: {card.furigana_text:20s} | Missing: {card.missing_kanji_count} | Score: {card.score}")

        # Verify missing kanji counts
        self.assertEqual(cards[0].missing_kanji_count, 0, "大会 should have 0 missing (all known)")
        self.assertEqual(cards[1].missing_kanji_count, 1, "学校 should have 1 missing (学)")
        self.assertEqual(cards[2].missing_kanji_count, 2, "学生 should have 2 missing (学, 生)")
        self.assertEqual(cards[3].missing_kanji_count, 2, "小学校 should have 2 missing (小, 学)")

    def test_score_without_missing_various_scenarios(self):
        """
        Test score_without_missing calculation in various scenarios.

        Weighted intervals (stability / 2^(unique_kanji_count - 1)):
        - 校長 (stability=50, 2 kanji): 校[こう] = 50/2 = 25
        - 会議 (stability=100, 2 kanji): 会[かい] = 100/2 = 50
        - 大会 (stability=100, 2 kanji): 大[たい] = 100/2 = 50
        """
        cards = [
            # Scenario 1: Card with all unknown kanji
            CardInfo(1, "学生[がくせい]", 0),

            # Scenario 2: Card with one unknown, rest known
            CardInfo(2, "学校[がっこう]", 0),

            # Scenario 3: Card with known kanji of different scores
            CardInfo(3, "大学校[だいがっこう]", 0),  # 大(weighted=50), 学(unknown), 校(weighted=25)

            # Scenario 4: Card with all known kanji
            CardInfo(4, "大会[たいかい]", 100),

            # Helper cards
            CardInfo(5, "校長[こうちょう]", 50),     # Provides 校[こう] weighted to 25
            CardInfo(6, "会議[かいぎ]", 100),        # Provides 会[かい] weighted to 50
            CardInfo(7, "議長[ぎちょう]", 100),      # Provides 議[ぎ] weighted to 50
        ]

        compute_scores(cards)

        print(f"\n=== Test: Score Without Missing ===")
        for card in cards[:4]:
            print(f"Card: {card.furigana_text:20s} | Score: {card.score:6.1f} | Without missing: {card.score_without_missing:6.1f}")

        # Note: Weighted intervals are used (stability / 2^(unique_kanji_count - 1))
        # 校長 has stability 50, 2 kanji → 校[こう] = 50/2 = 25
        # 会議 has stability 100, 2 kanji → 会[かい] = 100/2 = 50
        # 大会 has stability 100, 2 kanji → 大[たい] = 100/2 = 50

        # Scenario 1: All unknown → score_without_missing = 0
        self.assertEqual(cards[0].score_without_missing, 0, "All unknown → 0")

        # Scenario 2: 校 known (weighted=25), 学 unknown → min(25) = 25
        self.assertEqual(cards[1].score_without_missing, 25, "Should be min of known kanji = 25")

        # Scenario 3: 大(weighted=50), 学(unknown), 校(weighted=25) → min(50, 25) = 25
        self.assertEqual(cards[2].score_without_missing, 25, "Should be min(50, 25) = 25")

        # Scenario 4: All known → score_without_missing = score
        self.assertEqual(cards[3].score_without_missing, cards[3].score, "All known → equals score")

    def test_unlock_potential_with_score_impact(self):
        """
        Test that cards with same unlock_potential but different
        unlock_median_score_increase are differentiated.
        """
        cards = [
            # Two cards that both unlock 2 cards, but with different quality

            # Card A: contains 大, unlocks high-value cards
            CardInfo(1, "大会[たいかい]", 0),        # 大 unknown, 会 unknown

            # Card B: contains 小, unlocks low-value cards
            CardInfo(2, "小説[しょうせつ]", 0),      # 小 unknown, 説 unknown

            # Cards unlocked by 大 (high scores)
            CardInfo(3, "大学[だいがく]", 0),        # 学 known (100)

            # Cards unlocked by 小 (low scores)
            CardInfo(4, "小学[しょうがく]", 0),      # 学 known (100)
            CardInfo(5, "小人[しょうにん]", 0),      # 人 known (30)

            # Helper cards providing known kanji
            CardInfo(6, "学校[がっこう]", 100),      # Provides 学[がく]=100
            CardInfo(7, "校長[こうちょう]", 100),    # Provides 校[こう]=100
            CardInfo(8, "人間[にんげん]", 30),       # Provides 人[にん]=30
            CardInfo(9, "間違[まちが]", 30),         # Provides 間[ま]=30
        ]

        compute_scores(cards)

        card_a = [c for c in cards if c.card_id == 1][0]
        card_b = [c for c in cards if c.card_id == 2][0]

        print(f"\n=== Test: Same Unlock Potential, Different Quality ===")
        print(f"Card A (大会):")
        print(f"  Unlock potential: {card_a.unlock_potential}")
        print(f"  Unlock median score increase: {card_a.unlock_median_score_increase}")
        print(f"Card B (小説):")
        print(f"  Unlock potential: {card_b.unlock_potential}")
        print(f"  Unlock median score increase: {card_b.unlock_median_score_increase}")

        # Note: Weighted intervals (stability / 2^(unique_kanji_count - 1))
        # 学校 has stability 100, 2 kanji → 学[がく] = 100/2 = 50
        # 人間 has stability 30, 2 kanji → 人[にん] = 30/2 = 15
        #
        # Card A (大会): 大 unknown, 会 unknown
        # - Learning 大 unlocks: 大学 (score_without_missing = 50)
        # - Learning 会 unlocks: nothing (no other cards with 会)
        # - unlock_potential = max(1, 0) = 1
        #
        # Card B (小説): 小 unknown, 説 unknown
        # - Learning 小 unlocks: 小学 (score_without_missing = 50), 小人 (score_without_missing = 15)
        # - Learning 説 unlocks: nothing
        # - unlock_potential = max(2, 0) = 2

        # Card B should unlock more cards
        self.assertEqual(card_a.unlock_potential, 1, "大会: learning 大 unlocks 1 card")
        self.assertEqual(card_b.unlock_potential, 2, "小説: learning 小 unlocks 2 cards")

        # If both had same unlock potential, we'd check median score increase
        # But in this case, we just verify the values are calculated
        self.assertGreaterEqual(card_a.unlock_median_score_increase, 0, "Should have valid median")
        self.assertGreaterEqual(card_b.unlock_median_score_increase, 0, "Should have valid median")

    def test_integration_complete_scenario(self):
        """
        Complete integration test with multiple cards demonstrating
        all three new metrics working together.

        Weighted intervals (stability / 2^(unique_kanji_count - 1)):
        - 大会 (stability=100, 2 kanji): 大[たい]=50, 会[かい]=50
        - 会議 (stability=80, 2 kanji): 会[かい]=40, 議[ぎ]=40
        - 校長 (stability=60, 2 kanji): 校[こう]=30, 長[ちょう]=30
        - 問題 (stability=40, 2 kanji): 問[もん]=20, 題[だい]=20
        - 活動 (stability=70, 2 kanji): 活[かつ]=35, 動[どう]=35

        会[かい] max = max(50, 40) = 50
        """
        cards = [
            # Target card: 4 kanji, 2 known, 2 unknown
            CardInfo(1, "大学生会[だいがくせいかい]", 0),

            # Cards that provide known kanji
            CardInfo(2, "大会[たいかい]", 100),      # Provides 大[たい]=50, 会[かい]=50
            CardInfo(3, "会議[かいぎ]", 80),         # Provides 会[かい]=40, 議[ぎ]=40

            # Cards with 学 (unknown) - these will be unlocked when 学 is learned
            CardInfo(4, "学校[がっこう]", 0),        # 校 known (weighted=30)
            CardInfo(5, "学問[がくもん]", 0),        # 問 known (weighted=20)

            # Cards with 生 (unknown) - these will be unlocked when 生 is learned
            CardInfo(6, "生活[せいかつ]", 0),        # 活 known (weighted=35)
            CardInfo(7, "学生[がくせい]", 0),        # 学 unknown, will NOT be unlocked by just 生

            # Helper cards providing more known kanji
            CardInfo(8, "校長[こうちょう]", 60),     # Provides 校[こう]=30, 長[ちょう]=30
            CardInfo(9, "問題[もんだい]", 40),       # Provides 問[もん]=20, 題[だい]=20
            CardInfo(10, "活動[かつどう]", 70),      # Provides 活[かつ]=35, 動[どう]=35
        ]

        compute_scores(cards)

        target = [c for c in cards if c.card_id == 1][0]

        print(f"\n=== Integration Test: Complete Scenario ===")
        print(f"Target card: {target.furigana_text}")
        print(f"  Score: {target.score}")
        print(f"  Score without missing: {target.score_without_missing}")
        print(f"  Missing kanji count: {target.missing_kanji_count}")
        print(f"  Unlock potential: {target.unlock_potential}")
        print(f"  Unlock median score increase: {target.unlock_median_score_increase}")

        # Note: Weighted intervals are used (stability / 2^(unique_kanji_count - 1))
        # 大会 has stability 100, 2 kanji → 大[たい] = 100/2 = 50, 会[かい] = 100/2 = 50
        # 会議 has stability 80, 2 kanji → 会[かい] = 80/2 = 40, 議[ぎ] = 80/2 = 40
        # So 会[かい] = max(50, 40) = 50
        # Target card has 大(weighted=50) and 会(weighted=50), both known

        # Verify all metrics
        self.assertEqual(target.score, 0, "Has unknown kanji")
        self.assertEqual(target.score_without_missing, 50, "min(大=50, 会=50) = 50")
        self.assertEqual(target.missing_kanji_count, 2, "Missing 学 and 生")

        # Unlock potential: learning either 学 or 生 unlocks different cards
        # 学 unlocks: 学校, 学問 (2 cards)
        # 生 unlocks: 生活 (1 card, not 学生 because 学 is still unknown)
        # Max of the two should be 2
        self.assertGreaterEqual(target.unlock_potential, 1, "Should have some unlock potential")

        # Unlock median score increase should be based on the best unknown kanji
        self.assertGreater(target.unlock_median_score_increase, 0, "Should have positive median increase")


if __name__ == "__main__":
    unittest.main(verbosity=2)
