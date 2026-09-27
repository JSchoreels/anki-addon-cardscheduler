import unittest
from unittest.mock import Mock, patch

from cardscheduler.sentence_morphology import (
    MecabTokenAnalyzer,
    SentenceToken,
    SurfaceToken,
)


def analyzer_with_base_cmd():
    analyzer = object.__new__(MecabTokenAnalyzer)
    analyzer._commands = ["mecab"]
    analyzer.base_cmd = ["mecab"]
    analyzer.encoding = "utf-8"
    analyzer._token_cache = {}
    analyzer._surface_token_cache = {}
    return analyzer


class TestSentenceMorphology(unittest.TestCase):
    def test_extract_tokens_returns_kanji_tokens_with_normalized_reading(self):
        completed_process = Mock(
            returncode=0,
            stdout="学校\t名詞\t学校\tガッコウ\nに\t助詞\tに\tニ\n",
        )

        with patch("cardscheduler.sentence_morphology.subprocess.run", return_value=completed_process):
            tokens = analyzer_with_base_cmd().extract_tokens("学校に")

        self.assertEqual(
            tokens,
            [SentenceToken(surface="学校", lemma="学校", reading="がっこう", pos="名詞")],
        )

    def test_extract_tokens_caches_repeated_text(self):
        completed_process = Mock(
            returncode=0,
            stdout="学校\t名詞\t学校\tガッコウ\n",
        )

        with patch("cardscheduler.sentence_morphology.subprocess.run", return_value=completed_process) as run_mock:
            analyzer = analyzer_with_base_cmd()
            self.assertEqual(len(analyzer.extract_tokens("学校")), 1)
            self.assertEqual(len(analyzer.extract_tokens("学校")), 1)

        run_mock.assert_called_once()

    def test_extract_tokens_many_uses_single_mecab_call(self):
        completed_process = Mock(
            returncode=0,
            stdout=(
                "学校\t名詞\t学校\tガッコウ\n"
                "EOS\n"
                "本\t名詞\t本\tホン\n"
                "読む\t動詞\t読む\tヨム\n"
                "EOS\n"
            ),
        )

        with patch("cardscheduler.sentence_morphology.subprocess.run", return_value=completed_process) as run_mock:
            analyzer = analyzer_with_base_cmd()
            tokens_by_text = analyzer.extract_tokens_many(["学校に", "本を読む"])

        self.assertEqual(
            tokens_by_text["学校に"],
            [SentenceToken(surface="学校", lemma="学校", reading="がっこう", pos="名詞")],
        )
        self.assertEqual(
            tokens_by_text["本を読む"],
            [
                SentenceToken(surface="本", lemma="本", reading="ほん", pos="名詞"),
                SentenceToken(surface="読む", lemma="読む", reading="よむ", pos="動詞"),
            ],
        )
        run_mock.assert_called_once()

    def test_extract_surface_tokens_many_keeps_non_kanji_boundaries(self):
        completed_process = Mock(
            returncode=0,
            stdout=(
                "優しい\t形容詞\t優しい\tヤサシイ\n"
                "声\t名詞\t声\tコエ\n"
                "EOS\n"
            ),
        )

        with patch("cardscheduler.sentence_morphology.subprocess.run", return_value=completed_process):
            tokens = analyzer_with_base_cmd().extract_surface_tokens_many(["優しい声"])

        self.assertEqual(
            tokens["優しい声"],
            [SurfaceToken("優しい", "形容詞"), SurfaceToken("声", "名詞")],
        )


if __name__ == "__main__":
    unittest.main()
