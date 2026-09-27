import unittest

from cardscheduler.scheduler import CardInfo
from cardscheduler.sentence_benchmark import BenchmarkStage
from cardscheduler.word_score_benchmark import (
    WordScoreBenchmarkResult,
    WordScoreStats,
    compute_word_scores_for_benchmark,
)


class TestWordScoreBenchmark(unittest.TestCase):
    def test_compute_word_scores_for_benchmark_records_stages(self):
        cards = [
            CardInfo(1, "学校[がっこう]", 10),
            CardInfo(2, "学生[がくせい]", 0),
            CardInfo(3, "校長[こうちょう]", 5),
        ]

        stats = compute_word_scores_for_benchmark(cards)

        self.assertGreater(stats.kanji_reading_pairs, 0)
        self.assertGreater(stats.unique_kanji, 0)
        self.assertEqual(stats.reviewed_cards, 2)
        self.assertGreater(cards[0].score, 0)
        self.assertIsNotNone(cards[0].base_score)
        self.assertLessEqual(cards[0].score, cards[0].base_score)
        self.assertGreaterEqual(cards[1].unlock_potential, 0)

    def test_result_reports_total_seconds(self):
        result = WordScoreBenchmarkResult(
            source_collection="/source/collection.anki2",
            copied_collection="/copy/collection.anki2",
            card_limit=None,
            vocabulary_cards=10,
            loaded_new_cards=2,
            all_new_cards=5,
            update_fields=False,
            updated_cards=0,
            stats=WordScoreStats(
                kanji_reading_pairs=3,
                unique_kanji=2,
                cards_with_pairs=2,
                reviewed_cards=1,
            ),
            stages=[
                BenchmarkStage("first", 1.25),
                BenchmarkStage("second", 2.5),
            ],
        )

        self.assertEqual(result.total_seconds, 3.75)
        self.assertEqual(result.to_dict()["total_seconds"], 3.75)


if __name__ == "__main__":
    unittest.main()
