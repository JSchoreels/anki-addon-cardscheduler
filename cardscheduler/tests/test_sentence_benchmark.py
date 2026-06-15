import tempfile
import unittest
from pathlib import Path

from cardscheduler.sentence_benchmark import (
    BenchmarkStage,
    SentenceBenchmarkResult,
    copy_collection_snapshot,
    resolve_source_collection_path,
)


class TestSentenceBenchmark(unittest.TestCase):
    def test_resolve_source_collection_path_uses_profile(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            collection_path = base / "Main Profile" / "collection.anki2"
            collection_path.parent.mkdir()
            collection_path.write_text("collection", encoding="utf-8")

            resolved = resolve_source_collection_path(
                profile="Main Profile",
                anki_base=base,
            )

        self.assertEqual(resolved, collection_path)

    def test_copy_collection_snapshot_copies_sqlite_sidecars(self):
        with tempfile.TemporaryDirectory() as source_dir:
            source = Path(source_dir) / "collection.anki2"
            source.write_text("main", encoding="utf-8")
            Path(str(source) + "-wal").write_text("wal", encoding="utf-8")
            Path(str(source) + "-shm").write_text("shm", encoding="utf-8")

            with tempfile.TemporaryDirectory() as copy_dir:
                copied = copy_collection_snapshot(source, copy_dir=copy_dir)

                self.assertEqual(copied.read_text(encoding="utf-8"), "main")
                self.assertEqual(
                    Path(str(copied) + "-wal").read_text(encoding="utf-8"),
                    "wal",
                )
                self.assertEqual(
                    Path(str(copied) + "-shm").read_text(encoding="utf-8"),
                    "shm",
                )

    def test_result_reports_total_seconds(self):
        result = SentenceBenchmarkResult(
            source_collection="/source/collection.anki2",
            copied_collection="/copy/collection.anki2",
            sentence_limit=300,
            vocab_limit=None,
            vocab_cards=10,
            sentence_cards=2,
            loaded_new_sentence_cards=1,
            all_new_sentence_cards=5,
            mecab_extract_calls=3,
            mecab_cache_hits=1,
            mecab_cache_misses=2,
            mecab_subprocess_calls=1,
            stages=[
                BenchmarkStage("first", 1.25),
                BenchmarkStage("second", 2.5),
            ],
        )

        self.assertEqual(result.total_seconds, 3.75)
        self.assertEqual(result.to_dict()["total_seconds"], 3.75)


if __name__ == "__main__":
    unittest.main()
