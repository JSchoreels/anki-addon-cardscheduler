import unittest
from cardscheduler import (
    CardInfo,
    KanjiReadingInfo,
    build_card_to_pairs,
    update_kanji_reading_to_cards_with_max_weighted_interval,
    load_kanji_dictionnary_readings
)


class TestUpdateMaxWeightedInterval(unittest.TestCase):
    """Test update_kanji_reading_to_cards_with_max_weighted_interval with different kanji pair sizes."""

    @classmethod
    def setUpClass(cls):
        """Load kanji dictionary once for all tests."""
        cls.kanji_readings = load_kanji_dictionnary_readings()

    def _build_card_to_pairs(self, cards):
        """Helper to build card_to_pairs for a list of cards."""
        return build_card_to_pairs(cards, self.kanji_readings)

    def test_single_kanji_pair_single_card(self):
        """Test with a single kanji-reading pair and one card."""
        card = CardInfo(card_id=1, furigana_text='本[ほん]', stability=10.0)
        cards = [card]
        card_to_pairs = self._build_card_to_pairs(cards)

        kanji_reading_to_cards = {
            '本[ほん]': KanjiReadingInfo()
        }
        kanji_reading_to_cards['本[ほん]'].matched_cards.add(card)

        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, card_to_pairs
        )

        # For 1 kanji pair, weight = stability / 2^(1-1) = stability / 1 = 10.0
        self.assertAlmostEqual(
            kanji_reading_to_cards['本[ほん]'].max_weighted_interval,
            10.0,
            places=2
        )

    def test_two_kanji_pairs_single_card(self):
        """Test with two kanji-reading pairs from one card."""
        card = CardInfo(card_id=1, furigana_text='学校[がっこう]', stability=20.0)
        cards = [card]
        card_to_pairs = self._build_card_to_pairs(cards)

        kanji_reading_to_cards = {
            '学[がく]': KanjiReadingInfo(),
            '校[こう]': KanjiReadingInfo()
        }
        kanji_reading_to_cards['学[がく]'].matched_cards.add(card)
        kanji_reading_to_cards['校[こう]'].matched_cards.add(card)

        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, card_to_pairs
        )

        # For 2 kanji pairs, weight = stability / 2^(2-1) = 20.0 / 2 = 10.0
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
        card = CardInfo(card_id=1, furigana_text='女学校[じょがっこう]', stability=16.0)
        cards = [card]
        card_to_pairs = self._build_card_to_pairs(cards)

        kanji_reading_to_cards = {
            '女[じょ]': KanjiReadingInfo(),
            '学[がく]': KanjiReadingInfo(),
            '校[こう]': KanjiReadingInfo()
        }
        kanji_reading_to_cards['女[じょ]'].matched_cards.add(card)
        kanji_reading_to_cards['学[がく]'].matched_cards.add(card)
        kanji_reading_to_cards['校[こう]'].matched_cards.add(card)

        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, card_to_pairs
        )

        # For 3 kanji pairs, weight = stability / 2^(3-1) = 16.0 / 4 = 4.0
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
        card = CardInfo(card_id=1, furigana_text='東京駅前[とうきょうえきまえ]', stability=80.0)
        cards = [card]
        card_to_pairs = self._build_card_to_pairs(cards)

        kanji_reading_to_cards = {
            '東[とう]': KanjiReadingInfo(),
            '京[きょう]': KanjiReadingInfo(),
            '駅[えき]': KanjiReadingInfo(),
            '前[まえ]': KanjiReadingInfo()
        }
        for pair in kanji_reading_to_cards:
            kanji_reading_to_cards[pair].matched_cards.add(card)

        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, card_to_pairs
        )

        # For 4 kanji pairs, weight = stability / 2^(4-1) = 80.0 / 8 = 10.0
        for pair in kanji_reading_to_cards:
            self.assertAlmostEqual(
                kanji_reading_to_cards[pair].max_weighted_interval,
                10.0,
                places=2
            )

    def test_multiple_cards_different_sizes(self):
        """Test with multiple cards having different numbers of kanji pairs."""
        card1 = CardInfo(card_id=1, furigana_text='本[ほん]', stability=10.0)
        card2 = CardInfo(card_id=2, furigana_text='学校[がっこう]', stability=20.0)
        card3 = CardInfo(card_id=3, furigana_text='学[がく]', stability=30.0)
        cards = [card1, card2, card3]
        card_to_pairs = self._build_card_to_pairs(cards)

        kanji_reading_to_cards = {
            '本[ほん]': KanjiReadingInfo(),
            '学[がく]': KanjiReadingInfo(),
            '校[こう]': KanjiReadingInfo()
        }
        kanji_reading_to_cards['本[ほん]'].matched_cards.add(card1)
        kanji_reading_to_cards['学[がく]'].matched_cards.add(card2)
        kanji_reading_to_cards['学[がく]'].matched_cards.add(card3)
        kanji_reading_to_cards['校[こう]'].matched_cards.add(card2)

        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, card_to_pairs
        )

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
        card1 = CardInfo(card_id=1, furigana_text='本[ほん]', stability=0.0)
        card2 = CardInfo(card_id=2, furigana_text='本[ほん]', stability=15.0)
        cards = [card1, card2]
        card_to_pairs = self._build_card_to_pairs(cards)

        kanji_reading_to_cards = {
            '本[ほん]': KanjiReadingInfo()
        }
        kanji_reading_to_cards['本[ほん]'].matched_cards.add(card1)
        kanji_reading_to_cards['本[ほん]'].matched_cards.add(card2)

        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, card_to_pairs
        )

        # Only card2 should be considered (stability=15.0, 1 pair -> 15.0)
        self.assertAlmostEqual(
            kanji_reading_to_cards['本[ほん]'].max_weighted_interval,
            15.0,
            places=2
        )

    def test_all_zero_stability_defaults_to_zero(self):
        """Test that all zero stability cards result in 0.0 interval."""
        card1 = CardInfo(card_id=1, furigana_text='本[ほん]', stability=0.0)
        card2 = CardInfo(card_id=2, furigana_text='本[ほん]', stability=0.0)
        cards = [card1, card2]
        card_to_pairs = self._build_card_to_pairs(cards)

        kanji_reading_to_cards = {
            '本[ほん]': KanjiReadingInfo()
        }
        kanji_reading_to_cards['本[ほん]'].matched_cards.add(card1)
        kanji_reading_to_cards['本[ほん]'].matched_cards.add(card2)

        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, card_to_pairs
        )

        # Should default to 0.0
        self.assertAlmostEqual(
            kanji_reading_to_cards['本[ほん]'].max_weighted_interval,
            0.0,
            places=2
        )

    def test_five_kanji_pairs_exponential_decay(self):
        """Test with five kanji pairs to verify exponential decay."""
        card = CardInfo(card_id=1, furigana_text='一二三四五[いちにさんしご]', stability=160.0)
        cards = [card]
        card_to_pairs = self._build_card_to_pairs(cards)

        kanji_reading_to_cards = {
            '一[いち]': KanjiReadingInfo(),
            '二[に]': KanjiReadingInfo(),
            '三[さん]': KanjiReadingInfo(),
            '四[し]': KanjiReadingInfo(),
            '五[ご]': KanjiReadingInfo()
        }
        for pair in kanji_reading_to_cards:
            kanji_reading_to_cards[pair].matched_cards.add(card)

        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, card_to_pairs
        )

        # For 5 kanji pairs, weight = stability / 2^(5-1) = 160.0 / 16 = 10.0
        for pair in kanji_reading_to_cards:
            self.assertAlmostEqual(
                kanji_reading_to_cards[pair].max_weighted_interval,
                10.0,
                places=2
            )

    def test_mixed_pair_sizes_max_selection(self):
        """Test that max is correctly selected when same pair appears in cards of different sizes."""
        card1 = CardInfo(card_id=1, furigana_text='本[ほん]', stability=8.0)  # 1 pair: 8.0/1 = 8.0
        card2 = CardInfo(card_id=2, furigana_text='本屋[ほんや]', stability=12.0)  # 2 pairs: 12.0/2 = 6.0
        card3 = CardInfo(card_id=3, furigana_text='本当[ほんとう]', stability=20.0)  # 2 pairs: 20.0/2 = 10.0
        cards = [card1, card2, card3]
        card_to_pairs = self._build_card_to_pairs(cards)

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

        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards, card_to_pairs
        )

        # max should pick the highest weighted interval
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
