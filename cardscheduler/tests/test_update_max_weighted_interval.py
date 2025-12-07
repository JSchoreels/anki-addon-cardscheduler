import unittest
from cardscheduler import (
    CardInfo,
    KanjiReadingInfo,
    update_kanji_reading_to_cards_with_max_weighted_interval,
    load_kanji_dictionnary_readings
)


class TestUpdateMaxWeightedInterval(unittest.TestCase):
    """Test update_kanji_reading_to_cards_with_max_weighted_interval with different kanji pair sizes."""

    @classmethod
    def setUpClass(cls):
        """Load kanji dictionary once for all tests."""
        cls.kanji_readings = load_kanji_dictionnary_readings()

    def test_single_kanji_pair_single_card(self):
        """Test with a single kanji-reading pair and one card."""
        # Setup: Card with single kanji: 本[ほん]
        card = CardInfo(card_id=1, furigana_text='本[ほん]', stability=10.0)

        kanji_reading_to_cards = {
            '本[ほん]': KanjiReadingInfo()
        }
        kanji_reading_to_cards['本[ほん]'].matched_cards.add(card)

        # Execute
        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, self.kanji_readings
        )

        # Verify: For 1 kanji pair, weight = stability / 2^(1-1) = stability / 1 = 10.0
        self.assertAlmostEqual(
            kanji_reading_to_cards['本[ほん]'].max_weighted_interval,
            10.0,
            places=2
        )

    def test_two_kanji_pairs_single_card(self):
        """Test with two kanji-reading pairs from one card."""
        # Setup: Card with two kanji: 学校[がっこう] -> 学[がく], 校[こう]
        card = CardInfo(card_id=1, furigana_text='学校[がっこう]', stability=20.0)

        kanji_reading_to_cards = {
            '学[がく]': KanjiReadingInfo(),
            '校[こう]': KanjiReadingInfo()
        }
        kanji_reading_to_cards['学[がく]'].matched_cards.add(card)
        kanji_reading_to_cards['校[こう]'].matched_cards.add(card)

        # Execute
        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, self.kanji_readings
        )

        # Verify: For 2 kanji pairs, weight = stability / 2^(2-1) = 20.0 / 2 = 10.0
        self.assertAlmostEqual(
            kanji_reading_to_cards['学[がく]'].max_weighted_interval,
            10.0,
            places=2
        )
        self.assertAlmostEqual(
            kanji_reading_to_cards['校[こう]'].max_weighted_interval,
            10.0,
            places=2
        )

    def test_three_kanji_pairs_single_card(self):
        """Test with three kanji-reading pairs from one card."""
        # Setup: Card with three kanji: 女学校[じょがっこう] -> 女[じょ], 学[がく], 校[こう]
        card = CardInfo(card_id=1, furigana_text='女学校[じょがっこう]', stability=16.0)

        kanji_reading_to_cards = {
            '女[じょ]': KanjiReadingInfo(),
            '学[がく]': KanjiReadingInfo(),
            '校[こう]': KanjiReadingInfo()
        }
        kanji_reading_to_cards['女[じょ]'].matched_cards.add(card)
        kanji_reading_to_cards['学[がく]'].matched_cards.add(card)
        kanji_reading_to_cards['校[こう]'].matched_cards.add(card)

        # Execute
        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, self.kanji_readings
        )

        # Verify: For 3 kanji pairs, weight = stability / 2^(3-1) = 16.0 / 4 = 4.0
        self.assertAlmostEqual(
            kanji_reading_to_cards['女[じょ]'].max_weighted_interval,
            4.0,
            places=2
        )
        self.assertAlmostEqual(
            kanji_reading_to_cards['学[がく]'].max_weighted_interval,
            4.0,
            places=2
        )
        self.assertAlmostEqual(
            kanji_reading_to_cards['校[こう]'].max_weighted_interval,
            4.0,
            places=2
        )

    def test_four_kanji_pairs_single_card(self):
        """Test with four kanji-reading pairs from one card."""
        # Setup: Card with four kanji
        card = CardInfo(card_id=1, furigana_text='東京駅前[とうきょうえきまえ]', stability=80.0)

        kanji_reading_to_cards = {
            '東[とう]': KanjiReadingInfo(),
            '京[きょう]': KanjiReadingInfo(),
            '駅[えき]': KanjiReadingInfo(),
            '前[まえ]': KanjiReadingInfo()
        }
        for pair in kanji_reading_to_cards:
            kanji_reading_to_cards[pair].matched_cards.add(card)

        # Execute
        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, self.kanji_readings
        )

        # Verify: For 4 kanji pairs, weight = stability / 2^(4-1) = 80.0 / 8 = 10.0
        for pair in kanji_reading_to_cards:
            self.assertAlmostEqual(
                kanji_reading_to_cards[pair].max_weighted_interval,
                10.0,
                places=2
            )

    def test_multiple_cards_different_sizes(self):
        """Test with multiple cards having different numbers of kanji pairs."""
        # Setup:
        # Card 1: 本[ほん] (1 kanji, stability=10)
        # Card 2: 学校[がっこう] (2 kanji, stability=20)
        # Both share nothing, but we test 学 appears in both contexts

        card1 = CardInfo(card_id=1, furigana_text='本[ほん]', stability=10.0)
        card2 = CardInfo(card_id=2, furigana_text='学校[がっこう]', stability=20.0)
        card3 = CardInfo(card_id=3, furigana_text='学[がく]', stability=30.0)

        kanji_reading_to_cards = {
            '本[ほん]': KanjiReadingInfo(),
            '学[がく]': KanjiReadingInfo(),
            '校[こう]': KanjiReadingInfo()
        }
        kanji_reading_to_cards['本[ほん]'].matched_cards.add(card1)
        kanji_reading_to_cards['学[がく]'].matched_cards.add(card2)
        kanji_reading_to_cards['学[がく]'].matched_cards.add(card3)
        kanji_reading_to_cards['校[こう]'].matched_cards.add(card2)

        # Execute
        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, self.kanji_readings
        )

        # Verify:
        # 本[ほん]: card1 only, 1 pair -> 10.0 / 2^0 = 10.0
        self.assertAlmostEqual(
            kanji_reading_to_cards['本[ほん]'].max_weighted_interval,
            10.0,
            places=2
        )
        # 学[がく]: max(card2: 20.0/2^1=10.0, card3: 30.0/2^0=30.0) = 30.0
        self.assertAlmostEqual(
            kanji_reading_to_cards['学[がく]'].max_weighted_interval,
            30.0,
            places=2
        )
        # 校[こう]: card2 only, 2 pairs -> 20.0 / 2^1 = 10.0
        self.assertAlmostEqual(
            kanji_reading_to_cards['校[こう]'].max_weighted_interval,
            10.0,
            places=2
        )

    def test_zero_stability_ignored(self):
        """Test that cards with zero stability are ignored."""
        # Setup: Mix of cards with zero and non-zero stability
        card1 = CardInfo(card_id=1, furigana_text='本[ほん]', stability=0.0)
        card2 = CardInfo(card_id=2, furigana_text='本[ほん]', stability=15.0)

        kanji_reading_to_cards = {
            '本[ほん]': KanjiReadingInfo()
        }
        kanji_reading_to_cards['本[ほん]'].matched_cards.add(card1)
        kanji_reading_to_cards['本[ほん]'].matched_cards.add(card2)

        # Execute
        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, self.kanji_readings
        )

        # Verify: Only card2 should be considered (stability=15.0, 1 pair -> 15.0)
        self.assertAlmostEqual(
            kanji_reading_to_cards['本[ほん]'].max_weighted_interval,
            15.0,
            places=2
        )

    def test_all_zero_stability_defaults_to_zero(self):
        """Test that all zero stability cards result in 0.0 interval."""
        # Setup: All cards have zero stability
        card1 = CardInfo(card_id=1, furigana_text='本[ほん]', stability=0.0)
        card2 = CardInfo(card_id=2, furigana_text='本[ほん]', stability=0.0)

        kanji_reading_to_cards = {
            '本[ほん]': KanjiReadingInfo()
        }
        kanji_reading_to_cards['本[ほん]'].matched_cards.add(card1)
        kanji_reading_to_cards['本[ほん]'].matched_cards.add(card2)

        # Execute
        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, self.kanji_readings
        )

        # Verify: Should default to 0.0
        self.assertAlmostEqual(
            kanji_reading_to_cards['本[ほん]'].max_weighted_interval,
            0.0,
            places=2
        )

    def test_five_kanji_pairs_exponential_decay(self):
        """Test with five kanji pairs to verify exponential decay."""
        # Setup: Card with five kanji
        card = CardInfo(card_id=1, furigana_text='一二三四五[いちにさんしご]', stability=160.0)

        kanji_reading_to_cards = {
            '一[いち]': KanjiReadingInfo(),
            '二[に]': KanjiReadingInfo(),
            '三[さん]': KanjiReadingInfo(),
            '四[し]': KanjiReadingInfo(),
            '五[ご]': KanjiReadingInfo()
        }
        for pair in kanji_reading_to_cards:
            kanji_reading_to_cards[pair].matched_cards.add(card)

        # Execute
        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, self.kanji_readings
        )

        # Verify: For 5 kanji pairs, weight = stability / 2^(5-1) = 160.0 / 16 = 10.0
        for pair in kanji_reading_to_cards:
            self.assertAlmostEqual(
                kanji_reading_to_cards[pair].max_weighted_interval,
                10.0,
                places=2
            )

    def test_mixed_pair_sizes_max_selection(self):
        """Test that max is correctly selected when same pair appears in cards of different sizes."""
        # Setup: Same kanji appears in 1-kanji, 2-kanji, and 3-kanji cards
        card1 = CardInfo(card_id=1, furigana_text='本[ほん]', stability=8.0)  # 1 pair: 8.0/1 = 8.0
        card2 = CardInfo(card_id=2, furigana_text='本屋[ほんや]', stability=12.0)  # 2 pairs: 12.0/2 = 6.0
        card3 = CardInfo(card_id=3, furigana_text='本当[ほんとう]', stability=20.0)  # 2 pairs: 20.0/2 = 10.0

        kanji_reading_to_cards = {
            '本[ほん]': KanjiReadingInfo(),
            '屋[や]': KanjiReadingInfo(),
            '当[とう]': KanjiReadingInfo()
        }
        kanji_reading_to_cards['本[ほん]'].matched_cards.add(card1)
        kanji_reading_to_cards['本[ほん]'].matched_cards.add(card2)
        kanji_reading_to_cards['本[ほん]'].matched_cards.add(card3)
        kanji_reading_to_cards['屋[や]'].matched_cards.add(card2)
        kanji_reading_to_cards['当[とう]'].matched_cards.add(card3)

        # Execute
        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, self.kanji_readings
        )

        # Verify: max should pick the highest weighted interval
        # 本[ほん]: max(8.0, 6.0, 10.0) = 10.0
        self.assertAlmostEqual(
            kanji_reading_to_cards['本[ほん]'].max_weighted_interval,
            10.0,
            places=2
        )
        # 屋[や]: only from card2 = 6.0
        self.assertAlmostEqual(
            kanji_reading_to_cards['屋[や]'].max_weighted_interval,
            6.0,
            places=2
        )
        # 当[とう]: only from card3 = 10.0
        self.assertAlmostEqual(
            kanji_reading_to_cards['当[とう]'].max_weighted_interval,
            10.0,
            places=2
        )


if __name__ == '__main__':
    unittest.main()
