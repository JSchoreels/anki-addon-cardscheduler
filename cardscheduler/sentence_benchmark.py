"""Benchmark sentence score computation on a copied Anki collection."""

import argparse
import json
import pickle
import shutil
import tempfile
import time
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from anki.collection import Collection

from .anki_interface import (
    load_cards,
    load_sentence_cards,
    sentence_new_card_ids,
)
from .config import (
    SENTENCE_DECK_NAMES,
    SENTENCE_NOTE_TYPE,
)
from .dictionary import load_kanji_dictionnary_readings
from .scheduler import compute_scores
from .sentence_morphology import MecabTokenAnalyzer
from .sentence_scheduler import (
    assign_sentence_positions_and_priority,
    build_kanji_reading_interval_map,
    build_vocabulary_word_index,
    compute_sentence_scores,
)


DEFAULT_ANKI_BASE = Path.home() / "Library/Application Support/Anki2"
DEFAULT_SENTENCE_LIMIT = 300


@dataclass
class BenchmarkStage:
    name: str
    seconds: float


@dataclass
class SentenceBenchmarkResult:
    source_collection: str
    copied_collection: str
    sentence_limit: Optional[int]
    vocab_limit: Optional[int]
    vocab_cards: int
    sentence_cards: int
    loaded_new_sentence_cards: int
    all_new_sentence_cards: int
    mecab_extract_calls: int
    mecab_cache_hits: int
    mecab_cache_misses: int
    mecab_subprocess_calls: int
    stages: list[BenchmarkStage] = field(default_factory=list)

    @property
    def total_seconds(self):
        return sum(stage.seconds for stage in self.stages)

    def to_dict(self):
        result = asdict(self)
        result["total_seconds"] = self.total_seconds
        return result


class StageTimer:
    def __init__(self):
        self.stages = []

    @contextmanager
    def measure(self, name):
        start = time.perf_counter()
        try:
            yield
        finally:
            self.stages.append(BenchmarkStage(name, time.perf_counter() - start))


class CountingMecabTokenAnalyzer(MecabTokenAnalyzer):
    """MeCab analyzer wrapper that records cache effectiveness."""

    def __init__(self):
        self.extract_calls = 0
        self.cache_hits = 0
        self.cache_misses = 0
        self.subprocess_calls = 0
        super().__init__()

    def extract_tokens(self, text):
        return super().extract_tokens(text)

    def extract_tokens_many(self, texts):
        cache_keys = [self._cache_key(text) for text in texts]
        self.extract_calls += len(cache_keys)
        seen_misses = set()
        for text in cache_keys:
            if text in self._token_cache:
                self.cache_hits += 1
            elif text not in seen_misses:
                self.cache_misses += 1
                seen_misses.add(text)
        return super().extract_tokens_many(texts)

    def _run_mecab(self, texts):
        self.subprocess_calls += 1
        return super()._run_mecab(texts)


def last_loaded_profile_name(anki_base=DEFAULT_ANKI_BASE):
    prefs_path = Path(anki_base) / "prefs21.db"
    if not prefs_path.exists():
        return None

    import sqlite3

    connection = sqlite3.connect(str(prefs_path))
    try:
        row = connection.execute(
            "select data from profiles where name = '_global'"
        ).fetchone()
    finally:
        connection.close()

    if not row:
        return None

    data = pickle.loads(row[0])
    return data.get("last_loaded_profile_name")


def resolve_source_collection_path(collection_path=None, profile=None, anki_base=DEFAULT_ANKI_BASE):
    if collection_path:
        return Path(collection_path).expanduser()

    base = Path(anki_base).expanduser()
    profile_name = profile or last_loaded_profile_name(base)
    if profile_name:
        return base / profile_name / "collection.anki2"

    candidates = sorted(base.glob("*/collection.anki2"))
    if not candidates:
        raise FileNotFoundError(f"No collection.anki2 files found under {base}")
    return candidates[0]


def copy_collection_snapshot(
    source_collection_path,
    copy_dir=None,
    temp_prefix="cardscheduler_sentence_benchmark_",
):
    """Copy collection.anki2 and SQLite sidecars into an isolated directory."""
    source = Path(source_collection_path).expanduser()
    if not source.exists():
        raise FileNotFoundError(f"Collection not found: {source}")

    if copy_dir:
        snapshot_dir = Path(copy_dir).expanduser()
        snapshot_dir.mkdir(parents=True, exist_ok=True)
    else:
        snapshot_dir = Path(tempfile.mkdtemp(prefix=temp_prefix))

    copied = snapshot_dir / "collection.anki2"
    shutil.copy2(source, copied)
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(source) + suffix)
        if sidecar.exists():
            shutil.copy2(sidecar, Path(str(copied) + suffix))
    return copied


def benchmark_sentence_scores(
    source_collection_path,
    sentence_limit=DEFAULT_SENTENCE_LIMIT,
    vocab_limit=None,
    copy_dir=None,
    keep_copy=False,
):
    timer = StageTimer()
    copied_collection_path = None
    collection = None

    try:
        with timer.measure("copy_collection"):
            copied_collection_path = copy_collection_snapshot(source_collection_path, copy_dir)

        with timer.measure("open_collection"):
            collection = Collection(str(copied_collection_path))

        with timer.measure("setup_mecab"):
            analyzer = CountingMecabTokenAnalyzer()
            if not analyzer.available:
                raise RuntimeError("MeCab is not available")

        with timer.measure("load_vocabulary_cards"):
            vocab_cards = load_cards(collection)
            if vocab_limit is not None:
                vocab_cards = vocab_cards[:vocab_limit]

        with timer.measure("compute_vocabulary_scores"):
            compute_scores(vocab_cards)

        with timer.measure("load_kanji_readings"):
            kanji_readings = load_kanji_dictionnary_readings()

        with timer.measure("build_pair_intervals"):
            pair_intervals = build_kanji_reading_interval_map(
                vocab_cards,
                kanji_readings,
            )

        with timer.measure("build_vocabulary_word_index"):
            vocabulary_index = build_vocabulary_word_index(vocab_cards, analyzer)

        with timer.measure("load_sentence_cards"):
            sentence_cards = load_sentence_cards(
                collection,
                analyzer=analyzer,
                sentence_limit=sentence_limit,
            )

        with timer.measure("compute_sentence_scores"):
            compute_sentence_scores(
                sentence_cards,
                vocabulary_index,
                kanji_readings,
                pair_intervals,
            )

        with timer.measure("assign_sentence_order"):
            new_card_ids = sentence_new_card_ids(collection)
            assign_sentence_positions_and_priority(sentence_cards, new_card_ids)
            loaded_new_card_count = sum(
                1
                for sentence_card in sentence_cards
                for card_id in sentence_card.card_ids
                if card_id in new_card_ids
            )

        return SentenceBenchmarkResult(
            source_collection=str(Path(source_collection_path).expanduser()),
            copied_collection=str(copied_collection_path),
            sentence_limit=sentence_limit,
            vocab_limit=vocab_limit,
            vocab_cards=len(vocab_cards),
            sentence_cards=len(sentence_cards),
            loaded_new_sentence_cards=loaded_new_card_count,
            all_new_sentence_cards=len(new_card_ids),
            mecab_extract_calls=analyzer.extract_calls,
            mecab_cache_hits=analyzer.cache_hits,
            mecab_cache_misses=analyzer.cache_misses,
            mecab_subprocess_calls=analyzer.subprocess_calls,
            stages=timer.stages,
        )
    finally:
        if collection is not None:
            collection.close(downgrade=False)
        if copied_collection_path and not keep_copy and copy_dir is None:
            shutil.rmtree(copied_collection_path.parent, ignore_errors=True)


def print_result(result):
    print(json.dumps(result.to_dict(), indent=2))
    print()
    print("Sentence score benchmark")
    print(f"  Source collection: {result.source_collection}")
    print(f"  Copied collection: {result.copied_collection}")
    print(f"  Vocab cards: {result.vocab_cards}")
    print(f"  Sentence notes: {result.sentence_cards}")
    print(f"  Loaded new sentence cards: {result.loaded_new_sentence_cards}")
    print(f"  All matching new sentence cards: {result.all_new_sentence_cards}")
    print(f"  MeCab calls: {result.mecab_extract_calls}")
    print(f"  MeCab cache hits: {result.mecab_cache_hits}")
    print(f"  MeCab cache misses: {result.mecab_cache_misses}")
    print(f"  MeCab subprocess calls: {result.mecab_subprocess_calls}")
    print()
    for stage in result.stages:
        print(f"{stage.name:32s} {stage.seconds:8.3f}s")
    print(f"{'total':32s} {result.total_seconds:8.3f}s")


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Benchmark sentence scoring against a copied Anki collection."
    )
    parser.add_argument("--collection", help="Path to a source collection.anki2 file")
    parser.add_argument("--profile", help="Anki profile name under the Anki2 directory")
    parser.add_argument(
        "--anki-base",
        default=str(DEFAULT_ANKI_BASE),
        help="Anki2 base directory used with --profile",
    )
    parser.add_argument(
        "--sentence-limit",
        type=int,
        default=DEFAULT_SENTENCE_LIMIT,
        help="Maximum unique sentence notes to score; use 0 for all",
    )
    parser.add_argument(
        "--vocab-limit",
        type=int,
        help="Maximum vocabulary cards to include; omitted means all",
    )
    parser.add_argument("--copy-dir", help="Directory where the copied collection is written")
    parser.add_argument(
        "--keep-copy",
        action="store_true",
        help="Keep the temporary copied collection after the benchmark",
    )
    return parser


def main(argv=None):
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    source_collection_path = resolve_source_collection_path(
        collection_path=args.collection,
        profile=args.profile,
        anki_base=args.anki_base,
    )
    sentence_limit = args.sentence_limit if args.sentence_limit > 0 else None
    result = benchmark_sentence_scores(
        source_collection_path,
        sentence_limit=sentence_limit,
        vocab_limit=args.vocab_limit,
        copy_dir=args.copy_dir,
        keep_copy=args.keep_copy,
    )
    print_result(result)


if __name__ == "__main__":
    main()
