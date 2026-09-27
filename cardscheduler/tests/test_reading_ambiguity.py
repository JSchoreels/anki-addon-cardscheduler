import unittest
from unittest.mock import patch

from cardscheduler.reading_ambiguity import (
    compute_reading_ambiguity_factors,
    entropy_factor,
    onset_row,
)
from cardscheduler.scheduler import CardInfo, assign_positions_to_new_cards, compute_scores
from cardscheduler.sentence_morphology import SurfaceToken


class FakeSurfaceAnalyzer:
    available = True

    def __init__(self, tokens_by_surface):
        self.tokens_by_surface = tokens_by_surface

    def extract_surface_tokens_many(self, texts):
        return {
            text: list(self.tokens_by_surface.get(text, ()))
            for text in texts
        }


def card(card_id, surface, reading, furigana):
    return CardInfo(
        card_id,
        furigana,
        0,
        word_surface=surface,
        word_readings=(reading,),
    )


class TestReadingAmbiguity(unittest.TestCase):
    def test_balanced_variant_distribution_is_penalized_more(self):
        balanced = entropy_factor({"こえ": 5, "ごえ": 5})
        dominant = entropy_factor({"こえ": 9, "ごえ": 1})

        self.assertLess(balanced, dominant)
        self.assertLess(dominant, 1.0)

    def test_adjective_noun_boundary_resolves_rendaku(self):
        cards = [
            card(1, "優しい声", "やさしいこえ", "優[やさ]しい 声[こえ]"),
            card(2, "大声", "おおごえ", "大声[おおごえ]"),
        ]
        analyzer = FakeSurfaceAnalyzer(
            {
                "優しい声": [
                    SurfaceToken("優しい", "形容詞"),
                    SurfaceToken("声", "名詞"),
                ],
                "大声": [SurfaceToken("大声", "名詞")],
            }
        )

        factors = compute_reading_ambiguity_factors(cards, analyzer=analyzer)

        self.assertEqual(factors[1], 1.0)
        self.assertLess(factors[2], 1.0)

    def test_word_final_component_resolves_sokuon(self):
        cards = [
            card(1, "参列", "さんれつ", "参列[さんれつ]"),
            card(2, "列島", "れっとう", "列島[れっとう]"),
        ]
        analyzer = FakeSurfaceAnalyzer(
            {
                "参列": [SurfaceToken("参列", "名詞")],
                "列島": [SurfaceToken("列島", "名詞")],
            }
        )

        factors = compute_reading_ambiguity_factors(cards, analyzer=analyzer)

        self.assertEqual(factors[1], 1.0)
        self.assertLess(factors[2], 1.0)

    def test_predictable_sokuon_gets_partial_relief(self):
        cards = [
            card(1, "積極", "せっきょく", "積極[せっきょく]"),
            card(2, "積極的", "せっきょくてき", "積極的[せっきょくてき]"),
            card(3, "積乱雲", "せきらんうん", "積乱雲[せきらんうん]"),
            card(4, "堆積", "たいせき", "堆積[たいせき]"),
        ]
        analyzer = FakeSurfaceAnalyzer(
            {
                "積極": [SurfaceToken("積極", "名詞")],
                "積極的": [SurfaceToken("積極", "名詞"), SurfaceToken("的", "名詞")],
                "積乱雲": [SurfaceToken("積乱雲", "名詞")],
                "堆積": [SurfaceToken("堆積", "名詞")],
            }
        )

        factors = compute_reading_ambiguity_factors(cards, analyzer=analyzer)

        self.assertGreater(factors[1], entropy_factor({"せっ": 2, "せき": 2}))
        self.assertLess(factors[1], 1.0)
        self.assertEqual(factors[1], factors[2])

    def test_voiced_onset_is_not_grouped_with_sokuon_k_onset(self):
        self.assertEqual(onset_row("こう"), "K")
        self.assertEqual(onset_row("げん"), "other")


class TestAmbiguityRanking(unittest.TestCase):
    def test_compute_scores_keeps_base_score_and_applies_factor(self):
        known = CardInfo(1, "大会[たいかい]", 100)

        with patch(
            "cardscheduler.scheduler.compute_reading_ambiguity_factors",
            return_value={1: 0.8},
        ):
            compute_scores([known])

        self.assertEqual(known.base_score, 50)
        self.assertEqual(known.score, 40)
        self.assertEqual(known.reading_ambiguity_factor, 0.8)

    def test_zero_score_shadow_priority_preserves_then_adjusts_order(self):
        first = CardInfo(1, "学校[がっこう]", 0)
        second = CardInfo(2, "学生[がくせい]", 0)
        cards = [first, second]
        percentiles = {1: [0.9], 2: [0.85]}

        with patch("cardscheduler.scheduler.compute_percentile_ranks", return_value=percentiles):
            assign_positions_to_new_cards(cards, {1, 2})

        self.assertLess(first.position, second.position)
        self.assertGreater(first.ranking_score, 0)
        self.assertGreater(second.ranking_score, 0)

        first.reading_ambiguity_factor = 0.4
        with patch("cardscheduler.scheduler.compute_percentile_ranks", return_value=percentiles):
            assign_positions_to_new_cards(cards, {1, 2})

        self.assertGreater(first.position, second.position)
        self.assertEqual(first.score, 0)

    def test_zero_score_band_stays_below_positive_score(self):
        positive = CardInfo(1, "既知[きち]", 0)
        positive.base_score = 0.1
        positive.score = 0.06
        zero = CardInfo(2, "未知[みち]", 0)
        cards = [positive, zero]
        percentiles = {1: [0.1], 2: [1.0]}

        with patch("cardscheduler.scheduler.compute_percentile_ranks", return_value=percentiles):
            assign_positions_to_new_cards(cards, {1, 2})

        self.assertLess(positive.position, zero.position)
        self.assertLess(zero.ranking_score, positive.ranking_score)

    def test_directly_assigned_positive_score_remains_in_positive_tier(self):
        positive = CardInfo(1, "既知[きち]", 0)
        positive.score = 0.1
        zero = CardInfo(2, "未知[みち]", 0)
        percentiles = {1: [0.1], 2: [1.0]}

        with patch("cardscheduler.scheduler.compute_percentile_ranks", return_value=percentiles):
            assign_positions_to_new_cards([positive, zero], {1, 2})

        self.assertLess(positive.position, zero.position)


if __name__ == "__main__":
    unittest.main()
