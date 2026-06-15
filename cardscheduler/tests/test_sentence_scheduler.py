import unittest

from cardscheduler.scheduler import CardInfo
from cardscheduler.sentence_morphology import SentenceToken
from cardscheduler.sentence_scheduler import (
    SentenceCardInfo,
    assign_sentence_positions_and_priority,
    build_vocabulary_word_index,
    compute_sentence_scores,
)


class FakeAnalyzer:
    def __init__(self, tokens_by_text):
        self.tokens_by_text = tokens_by_text

    def extract_tokens(self, text):
        return self.tokens_by_text.get(text, [])

    def extract_tokens_many(self, texts):
        return {
            text: self.extract_tokens(text)
            for text in texts
        }


class TestSentenceScheduler(unittest.TestCase):
    def test_predicted_score_uses_component_score_for_missing_words(self):
        yesterday = SentenceToken("昨日", "昨日", "きのう", "名詞")
        school = SentenceToken("学校", "学校", "がっこう", "名詞")
        go = SentenceToken("行き", "行く", "いき", "動詞")
        analyzer = FakeAnalyzer(
            {
                "昨日": [yesterday],
                "行く": [SentenceToken("行く", "行く", "いく", "動詞")],
            }
        )
        vocabulary_cards = [
            CardInfo(
                1,
                "昨日[きのう]",
                40,
                word_surface="昨日",
                word_readings=("きのう",),
            ),
            CardInfo(
                2,
                "行く[いく]",
                20,
                word_surface="行く",
                word_readings=("いく",),
            ),
        ]
        sentence = SentenceCardInfo(
            note_id=1,
            card_ids=[1],
            sentence_text="昨日学校に行きました。",
            tokens=[yesterday, school, go],
        )

        compute_sentence_scores(
            [sentence],
            build_vocabulary_word_index(vocabulary_cards, analyzer),
            {
                "学": {"がく": ["がっ", "がく"]},
                "校": {"こう": ["こう"]},
            },
            {
                "学[がく]": 80,
                "校[こう]": 80,
            },
        )

        self.assertEqual(sentence.strict_score, 0)
        self.assertEqual(sentence.predicted_score, 20)
        self.assertEqual(sentence.missing_words, 1)
        self.assertEqual(sentence.inferred_words, 1)
        self.assertEqual(sentence.kanji_word_count, 3)

    def test_ambiguous_lemma_requires_reading_match(self):
        wind = SentenceToken("風", "風", "かぜ", "名詞")
        manner = SentenceToken("風", "風", "ふう", "名詞")
        analyzer = FakeAnalyzer(
            {
                "風": [wind],
            }
        )
        vocabulary_cards = [
            CardInfo(
                1,
                "風[かぜ]",
                30,
                word_surface="風",
                word_readings=("かぜ",),
            ),
            CardInfo(
                2,
                "風[ふう]",
                0,
                word_surface="風",
                word_readings=("ふう",),
            ),
        ]
        sentence = SentenceCardInfo(
            note_id=1,
            card_ids=[1],
            sentence_text="そんな風に考える。",
            tokens=[manner],
        )

        compute_sentence_scores(
            [sentence],
            build_vocabulary_word_index(vocabulary_cards, analyzer),
            {"風": {"かぜ": ["かぜ"], "ふう": ["ふう"]}},
            {},
        )

        self.assertEqual(sentence.strict_score, 0)
        self.assertEqual(sentence.predicted_score, 0)
        self.assertEqual(sentence.missing_words, 1)
        self.assertEqual(sentence.inferred_words, 0)

    def test_priority_score_preserves_sentence_sort_order(self):
        best = SentenceCardInfo(1, [1], "")
        best.strict_score = 40
        zero_with_prediction = SentenceCardInfo(2, [2], "")
        zero_with_prediction.predicted_score = 20
        zero_with_prediction.missing_words = 1
        zero_with_prediction.inferred_words = 1
        zero_without_prediction = SentenceCardInfo(3, [3], "")
        zero_without_prediction.missing_words = 1

        cards = [zero_without_prediction, zero_with_prediction, best]
        assign_sentence_positions_and_priority(cards, new_card_ids={1, 2, 3})

        self.assertEqual(best.position, 1)
        self.assertEqual(zero_with_prediction.position, 2)
        self.assertEqual(zero_without_prediction.position, 3)
        self.assertGreater(best.priority_score, zero_with_prediction.priority_score)
        self.assertGreater(
            zero_with_prediction.priority_score,
            zero_without_prediction.priority_score,
        )

    def test_shorter_sentence_wins_final_tie_breaker(self):
        shorter = SentenceCardInfo(1, [1], "")
        shorter.strict_score = 10
        shorter.predicted_score = 10
        shorter.kanji_word_count = 2
        longer = SentenceCardInfo(2, [2], "")
        longer.strict_score = 10
        longer.predicted_score = 10
        longer.kanji_word_count = 4

        assign_sentence_positions_and_priority([longer, shorter], new_card_ids={1, 2})

        self.assertEqual(shorter.position, 1)
        self.assertEqual(longer.position, 2)
        self.assertGreater(shorter.priority_score, longer.priority_score)

    def test_positions_are_assigned_to_reviewed_sentence_cards_too(self):
        reviewed = SentenceCardInfo(1, [1], "")
        reviewed.strict_score = 20
        new = SentenceCardInfo(2, [2], "")
        new.strict_score = 10

        assign_sentence_positions_and_priority([new, reviewed], new_card_ids={2})

        self.assertEqual(reviewed.position, 1)
        self.assertEqual(new.position, 2)


if __name__ == "__main__":
    unittest.main()
