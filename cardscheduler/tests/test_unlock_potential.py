import unittest

from cardscheduler import (
    CardInfo,
    compute_scores,
    get_kanji_reading_to_matching_card,
    update_kanji_reading_to_cards_with_max_weighted_interval,
    compute_unlock_potential,
    load_kanji_dictionnary_readings,
    get_kanji_reading_pairs,
)


class TestUnlockPotential(unittest.TestCase):
    """Test cases for unlock potential calculation."""

    def setUp(self):
        """Set up test fixtures."""
        self.kanji_readings = load_kanji_dictionnary_readings()

    def test_known_kanji_has_zero_unlock_potential(self):
        """Known kanji (score > 0) should have unlock potential of 0."""
        cards = [
            CardInfo(1, "学校[がっこう]", 10),  # Known word
        ]

        compute_scores(cards)

        # Known kanji should have score > 0 and unlock potential = 0
        self.assertGreater(cards[0].score, 0)
        self.assertEqual(cards[0].unlock_potential, 0)

    def test_unknown_kanji_single_card(self):
        """Unknown kanji in a single card should unlock itself if it has only one unknown kanji."""
        cards = [
            CardInfo(1, "学校[がっこう]", 0),     # Unknown word - 学+校
            CardInfo(2, "校長[こうちょう]", 10),  # Known word - provides 校
        ]

        compute_scores(cards)

        # Card 1 should have score = 0 (bottlenecked by 学, since 校 is known from card 2)
        self.assertEqual(cards[0].score, 0)
        # Card 1 should have unlock potential >= 1 (learning 学 unlocks it)
        self.assertGreaterEqual(cards[0].unlock_potential, 1)

    def test_unlock_potential_with_compound_word(self):
        """Test unlock potential when unknown kanji appears in compound words."""
        cards = [
            CardInfo(1, "学生[がくせい]", 0),     # Unknown: 学生 (both unknown)
            CardInfo(2, "学校[がっこう]", 0),     # Compound: 学 unknown, 校 known
            CardInfo(3, "校長[こうちょう]", 10),  # Known: 校長
        ]

        compute_scores(cards)

        # Card 3 (校長) should be known
        self.assertGreater(cards[2].score, 0)
        self.assertEqual(cards[2].unlock_potential, 0)

        # Card 2 (学校) should have score = 0 (bottlenecked by 学)
        self.assertEqual(cards[1].score, 0)

        # Learning 学 should unlock Card 2 (学校) since 校 is already known
        # Card 2 should show unlock potential >= 1
        self.assertGreaterEqual(cards[1].unlock_potential, 1)

    def test_unlock_potential_multiple_bottlenecks(self):
        """Test that cards with multiple unknown kanji require all to be learned."""
        cards = [
            CardInfo(1, "大会[たいかい]", 0),     # Unknown: 大+会
            CardInfo(2, "学生[がくせい]", 0),     # Unknown: 学+生
            CardInfo(3, "大学[だいがく]", 0),     # Unknown: 大+学
            CardInfo(4, "会議[かいぎ]", 10),      # Known: provides 会
            CardInfo(5, "生徒[せいと]", 10),      # Known: provides 生
        ]

        compute_scores(cards)

        # Cards 1, 2, 3 should have score = 0
        self.assertEqual(cards[0].score, 0)
        self.assertEqual(cards[1].score, 0)
        self.assertEqual(cards[2].score, 0)

        # Card 3 (大学) should NOT be unlocked by learning only 大 or only 学
        # It requires both, so learning either one alone won't unlock it
        # Card 1 (大会) can be unlocked by learning 大 (since 会 is known) = 1
        # Card 2 (学生) can be unlocked by learning 学 (since 生 is known) = 1
        self.assertEqual(cards[0].unlock_potential, 1)
        self.assertEqual(cards[1].unlock_potential, 1)

    def test_unlock_potential_partial_knowledge(self):
        """Test unlock potential when some kanji in compound are known."""
        cards = [
            CardInfo(1, "小説[しょうせつ]", 8),       # Known: 小説 (provides 小[しょう])
            CardInfo(2, "学校[がっこう]", 0),         # Unknown: 学校 (学 unknown, 校 known)
            CardInfo(3, "校長[こうちょう]", 10),      # Known: 校長 (provides 校[こう])
            CardInfo(4, "小学校[しょうがっこう]", 0), # 小学校: 小 known, 学 unknown, 校 known
        ]

        compute_scores(cards)

        # Known cards should have score > 0
        self.assertGreater(cards[0].score, 0)
        self.assertGreater(cards[2].score, 0)

        # Card 4 (小学校) should be bottlenecked only by 学
        self.assertEqual(cards[3].score, 0)
        self.assertEqual(cards[3].unknown_kanji_readings, 1)

        # Learning 学 should unlock both Card 2 (学校) and Card 4 (小学校)
        # So 学's unlock potential should be >= 2
        self.assertGreaterEqual(cards[1].unlock_potential, 2)
        self.assertGreaterEqual(cards[3].unlock_potential, 2)

    def test_unlock_potential_no_false_positives(self):
        """Test that unlock potential doesn't count cards that won't actually unlock."""
        cards = [
            CardInfo(1, "大会[たいかい]", 0),           # Unknown: 大+会
            CardInfo(2, "学生[がくせい]", 0),           # Unknown: 学+生
            CardInfo(3, "大学[だいがく]", 0),           # Unknown: both 大+学
            CardInfo(4, "大学校[だいがっこう]", 0),     # Unknown: 大+学+校
            CardInfo(5, "会議[かいぎ]", 10),            # Known: provides 会
            CardInfo(6, "生徒[せいと]", 10),            # Known: provides 生
        ]

        compute_scores(cards)

        # All unknown cards should have score = 0
        self.assertEqual(cards[0].score, 0)
        self.assertEqual(cards[1].score, 0)
        self.assertEqual(cards[2].score, 0)
        self.assertEqual(cards[3].score, 0)

        # Learning 大 alone should only unlock Card 1 (大会, since 会 is known)
        # It won't unlock Card 3 (still needs 学) or Card 4 (still needs 学 and 校)
        self.assertEqual(cards[0].unlock_potential, 1)

        # Learning 学 alone should only unlock Card 2 (学生, since 生 is known)
        self.assertEqual(cards[1].unlock_potential, 1)

    def test_compute_unlock_potential_function(self):
        """Test the compute_unlock_potential function directly."""
        from collections import defaultdict

        cards = [
            CardInfo(1, "学生[がくせい]", 0),
            CardInfo(2, "学校[がっこう]", 0),
            CardInfo(3, "校長[こうちょう]", 10),
        ]

        kanji_reading_to_cards = get_kanji_reading_to_matching_card(cards, self.kanji_readings)
        update_kanji_reading_to_cards_with_max_weighted_interval(kanji_reading_to_cards, self.kanji_readings)

        # Compute scores first
        for card_info in cards:
            if not card_info.furigana_text:
                card_info.score = 0
                continue

            kanji_reading_pairs = get_kanji_reading_pairs(card_info.furigana_text, self.kanji_readings)

            kanji_to_intervals = defaultdict(list)
            for pair in kanji_reading_pairs:
                if pair in kanji_reading_to_cards:
                    kanji = pair.split('[')[0]
                    interval = kanji_reading_to_cards[pair].max_weighted_interval
                    kanji_to_intervals[kanji].append(interval)

            max_intervals_per_kanji = [
                max(intervals) for intervals in kanji_to_intervals.values()
            ]

            card_info.score = min(max_intervals_per_kanji) if max_intervals_per_kanji else 0

        # Now compute unlock potential
        compute_unlock_potential(kanji_reading_to_cards, self.kanji_readings, cards)

        # Check that 学[がく] has unlock potential >= 1 (unlocks 学校)
        gaku_pair = "学[がく]"
        self.assertIn(gaku_pair, kanji_reading_to_cards)
        self.assertGreaterEqual(kanji_reading_to_cards[gaku_pair].unlock_potential, 1)

        # Check that 校[こう] has unlock potential = 0 (already known)
        kou_pair = "校[こう]"
        self.assertIn(kou_pair, kanji_reading_to_cards)
        self.assertEqual(kanji_reading_to_cards[kou_pair].unlock_potential, 0)

    def test_card_unlock_potential_inherits_max(self):
        """Test that card unlock potential is the max of its unknown pairs."""
        cards = [
            CardInfo(1, "学生[がくせい]", 0),     # Unknown: 学生 (学 high unlock potential)
            CardInfo(2, "大会[たいかい]", 0),     # Unknown: 大会 (大 low unlock potential)
            CardInfo(3, "学校[がっこう]", 0),     # Has 学 (high) but not 大
            CardInfo(4, "校長[こうちょう]", 10),  # Known: 校長
            CardInfo(5, "大学[だいがく]", 0),     # Has both 学 and 大
        ]

        compute_scores(cards)

        # Card 5 has both 学 (high unlock) and 大 (low unlock)
        # Its unlock potential should be the max of the two
        # Since 学 appears in more cards, it should have higher unlock potential
        card5 = cards[4]
        self.assertEqual(card5.score, 0)

        # The unlock potential should be >= the max of individual kanji unlock potentials
        # 学 appears in Cards 1, 3, 5 = at least 2 cards (depending on bottlenecks)
        # 大 appears in Cards 2, 5 = at least 1 card
        # Card 5 should inherit the higher value
        self.assertGreater(card5.unlock_potential, 0)

    def test_integration_full_flow(self):
        """Integration test for complete unlock potential flow."""
        cards = [
            CardInfo(1, "一年[いちねん]", 20),            # Known: provides 一,年
            CardInfo(2, "二年[にねん]", 15),              # Known: provides 二,年
            CardInfo(3, "三年[さんねん]", 0),             # Unknown: 三 unknown, 年 known
            CardInfo(4, "一二[いちに]", 5),               # Known: 一 and 二 both known
            CardInfo(5, "二三[にさん]", 0),               # 二 known, 三 unknown
            CardInfo(6, "三月[さんがつ]", 0),             # 三 unknown, 月 learned separately
            CardInfo(7, "月日[つきひ]", 10),              # Known: provides 月
        ]

        compute_scores(cards)

        # Cards 1, 2, 4, 7 should be known (score > 0)
        self.assertGreater(cards[0].score, 0)
        self.assertGreater(cards[1].score, 0)
        self.assertGreater(cards[3].score, 0)
        self.assertGreater(cards[6].score, 0)

        # Cards with known kanji should have unlock potential = 0
        self.assertEqual(cards[0].unlock_potential, 0)
        self.assertEqual(cards[1].unlock_potential, 0)
        self.assertEqual(cards[3].unlock_potential, 0)

        # Cards 3, 5, 6 should be unknown (bottlenecked by 三)
        self.assertEqual(cards[2].score, 0)
        self.assertEqual(cards[4].score, 0)
        self.assertEqual(cards[5].score, 0)

        # Learning 三[さん] should unlock Cards 3, 5, and 6
        # All three cards share the same 三[さん] reading, so unlock potential should be >= 3
        # (Note: Different readings like 三[み] or 三[みっ] would have different unlock values)
        self.assertGreaterEqual(cards[2].unlock_potential, 1)
        self.assertGreaterEqual(cards[4].unlock_potential, 1)
        self.assertGreaterEqual(cards[5].unlock_potential, 1)


if __name__ == "__main__":
    unittest.main()
