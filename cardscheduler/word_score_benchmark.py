"""Benchmark vocabulary word score computation on a copied Anki collection."""

import argparse
import json
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from anki.collection import Collection

from .anki_interface import (
    detect_available_fields,
    load_cards,
    update_cards_score,
)
from .config import (
    DECK_NAME,
    FIELD_NAME_CARDS_WITH_KANJI,
    FIELD_NAME_CARDS_WITH_KANJI_KNOWN,
    FIELD_NAME_CARDS_WITH_KANJI_UNKNOWN,
    FIELD_NAME_MISSING_KANJI_COUNT,
    FIELD_NAME_POSITION,
    FIELD_NAME_SCORE,
    FIELD_NAME_SCORE_WITHOUT_MISSING,
    FIELD_NAME_UNLOCK_MEDIAN_SCORE_INCREASE,
    FIELD_NAME_UNLOCK_POTENTIAL,
    SIMULATE_ZERO_STABILITY,
)
from .dictionary import load_kanji_dictionnary_readings
from .scheduler import (
    apply_reading_ambiguity,
    assign_positions_to_new_cards,
    build_card_to_pairs,
    build_kanji_to_cards_mapping,
    compute_card_scores,
    compute_kanji_familiarity,
    compute_unlock_potential,
    get_kanji_reading_to_matching_card,
    update_card_unlock_metrics,
    update_kanji_reading_to_cards_with_max_weighted_interval,
)
from .sentence_benchmark import (
    BenchmarkStage,
    DEFAULT_ANKI_BASE,
    StageTimer,
    copy_collection_snapshot,
    resolve_source_collection_path,
)


@dataclass
class WordScoreStats:
    kanji_reading_pairs: int
    unique_kanji: int
    cards_with_pairs: int
    reviewed_cards: int


@dataclass
class WordScoreBenchmarkResult:
    source_collection: str
    copied_collection: str
    card_limit: Optional[int]
    vocabulary_cards: int
    loaded_new_cards: int
    all_new_cards: int
    update_fields: bool
    updated_cards: int
    stats: WordScoreStats
    stages: list[BenchmarkStage] = field(default_factory=list)

    @property
    def total_seconds(self):
        return sum(stage.seconds for stage in self.stages)

    def to_dict(self):
        result = asdict(self)
        result["total_seconds"] = self.total_seconds
        return result


def compute_word_scores_for_benchmark(cards, timer=None):
    """Compute word scores with benchmark timing around each production stage."""
    if timer is None:
        timer = StageTimer()

    with timer.measure("load_kanji_readings"):
        kanji_readings = load_kanji_dictionnary_readings()

    with timer.measure("build_card_to_pairs"):
        card_to_pairs = build_card_to_pairs(cards, kanji_readings)

    with timer.measure("build_kanji_reading_to_cards"):
        kanji_reading_to_cards = get_kanji_reading_to_matching_card(
            cards,
            card_to_pairs,
        )

    with timer.measure("update_max_weighted_intervals"):
        update_kanji_reading_to_cards_with_max_weighted_interval(
            kanji_reading_to_cards,
            card_to_pairs,
        )

    with timer.measure("build_kanji_to_cards"):
        kanji_to_cards = build_kanji_to_cards_mapping(cards)

    with timer.measure("compute_kanji_familiarity"):
        compute_kanji_familiarity(cards, kanji_to_cards)

    with timer.measure("compute_card_scores"):
        compute_card_scores(cards, card_to_pairs, kanji_reading_to_cards)

    with timer.measure("compute_unlock_potential"):
        compute_unlock_potential(kanji_reading_to_cards, card_to_pairs)

    with timer.measure("update_card_unlock_metrics"):
        update_card_unlock_metrics(cards, card_to_pairs, kanji_reading_to_cards)

    with timer.measure("apply_reading_ambiguity"):
        apply_reading_ambiguity(cards, kanji_readings)

    return WordScoreStats(
        kanji_reading_pairs=len(kanji_reading_to_cards),
        unique_kanji=len(kanji_to_cards),
        cards_with_pairs=sum(1 for pairs in card_to_pairs.values() if pairs),
        reviewed_cards=sum(1 for card in cards if card.stability > 0),
    )


def benchmark_word_scores(
    source_collection_path,
    card_limit=None,
    update_fields=False,
    copy_dir=None,
    keep_copy=False,
):
    timer = StageTimer()
    copied_collection_path = None
    collection = None

    try:
        with timer.measure("copy_collection"):
            copied_collection_path = copy_collection_snapshot(
                source_collection_path,
                copy_dir,
                temp_prefix="cardscheduler_word_benchmark_",
            )

        with timer.measure("open_collection"):
            collection = Collection(str(copied_collection_path))

        with timer.measure("load_vocabulary_cards"):
            cards = load_cards(collection)
            if card_limit is not None:
                cards = cards[:card_limit]

        stats = compute_word_scores_for_benchmark(cards, timer)

        with timer.measure("find_new_cards"):
            all_new_card_ids = set(collection.find_cards(f'"deck:{DECK_NAME}" is:new'))
            if SIMULATE_ZERO_STABILITY:
                loaded_new_card_ids = set(card.card_id for card in cards)
            else:
                loaded_new_card_ids = {
                    card.card_id for card in cards if card.card_id in all_new_card_ids
                }

        with timer.measure("assign_positions"):
            assign_positions_to_new_cards(cards, loaded_new_card_ids)

        updated_cards = 0
        if update_fields:
            score_field_names = [
                FIELD_NAME_POSITION,
                FIELD_NAME_SCORE,
                FIELD_NAME_UNLOCK_POTENTIAL,
                FIELD_NAME_UNLOCK_MEDIAN_SCORE_INCREASE,
                FIELD_NAME_SCORE_WITHOUT_MISSING,
                FIELD_NAME_MISSING_KANJI_COUNT,
                FIELD_NAME_CARDS_WITH_KANJI,
                FIELD_NAME_CARDS_WITH_KANJI_KNOWN,
                FIELD_NAME_CARDS_WITH_KANJI_UNKNOWN,
            ]
            with timer.measure("detect_score_fields"):
                available_fields = detect_available_fields(collection, score_field_names)

            with timer.measure("update_score_fields"):
                updated_cards = update_cards_score(
                    cards,
                    collection,
                    kanji_meanings={},
                    kanji_readings={},
                    new_card_ids=loaded_new_card_ids,
                    dry_run=False,
                    available_fields=available_fields,
                    update_related_fields=False,
                    update_kanji_meanings_field=False,
                )

        return WordScoreBenchmarkResult(
            source_collection=str(Path(source_collection_path).expanduser()),
            copied_collection=str(copied_collection_path),
            card_limit=card_limit,
            vocabulary_cards=len(cards),
            loaded_new_cards=len(loaded_new_card_ids),
            all_new_cards=len(all_new_card_ids),
            update_fields=update_fields,
            updated_cards=updated_cards,
            stats=stats,
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
    print("Word score benchmark")
    print(f"  Source collection: {result.source_collection}")
    print(f"  Copied collection: {result.copied_collection}")
    print(f"  Vocabulary cards: {result.vocabulary_cards}")
    print(f"  Loaded new cards: {result.loaded_new_cards}")
    print(f"  All matching new cards: {result.all_new_cards}")
    print(f"  Update copied fields: {result.update_fields}")
    print(f"  Updated copied cards: {result.updated_cards}")
    print(f"  Cards with kanji-reading pairs: {result.stats.cards_with_pairs}")
    print(f"  Unique kanji-reading pairs: {result.stats.kanji_reading_pairs}")
    print(f"  Unique kanji: {result.stats.unique_kanji}")
    print(f"  Reviewed cards: {result.stats.reviewed_cards}")
    print()
    for stage in result.stages:
        print(f"{stage.name:32s} {stage.seconds:8.3f}s")
    print(f"{'total':32s} {result.total_seconds:8.3f}s")


def build_arg_parser():
    parser = argparse.ArgumentParser(
        description="Benchmark vocabulary word score computation against a copied Anki collection."
    )
    parser.add_argument("--collection", help="Path to a source collection.anki2 file")
    parser.add_argument("--profile", help="Anki profile name under the Anki2 directory")
    parser.add_argument(
        "--anki-base",
        default=str(DEFAULT_ANKI_BASE),
        help="Anki2 base directory used with --profile",
    )
    parser.add_argument(
        "--card-limit",
        type=int,
        help="Maximum loaded vocabulary cards to score; omitted means all",
    )
    parser.add_argument(
        "--update-fields",
        action="store_true",
        help="Also update score fields in the copied collection",
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
    result = benchmark_word_scores(
        source_collection_path,
        card_limit=args.card_limit,
        update_fields=args.update_fields,
        copy_dir=args.copy_dir,
        keep_copy=args.keep_copy,
    )
    print_result(result)


if __name__ == "__main__":
    main()
