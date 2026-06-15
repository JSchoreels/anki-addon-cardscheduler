"""Sentence scoring based on reviewed vocabulary and kanji-reading familiarity."""

from collections import defaultdict
from dataclasses import dataclass, field

from .dictionary import extract_kanji_only
from .scheduler import (
    build_card_to_pairs,
    get_kanji_reading_to_matching_card,
    update_kanji_reading_to_cards_with_max_weighted_interval,
)
from .sentence_morphology import SentenceToken, contains_kanji
from .word_parser import get_kanji_reading_pairs


@dataclass
class VocabularyWordEntry:
    surface: str
    lemma: str
    readings: tuple
    known_interval: float


@dataclass
class VocabularyWordIndex:
    by_surface: dict = field(default_factory=lambda: defaultdict(list))
    by_lemma: dict = field(default_factory=lambda: defaultdict(list))
    readings_by_surface: dict = field(default_factory=lambda: defaultdict(set))
    readings_by_lemma: dict = field(default_factory=lambda: defaultdict(set))


@dataclass
class SentenceCardInfo:
    note_id: int
    card_ids: list
    sentence_text: str
    tokens: list = field(default_factory=list)
    strict_score: float = 0.0
    predicted_score: float = 0.0
    missing_words: int = 0
    inferred_words: int = 0
    kanji_word_count: int = 0
    priority_score: float = 0.0
    position: int = 0


def build_kanji_reading_interval_map(cards, kanji_readings):
    """Return max weighted interval by kanji-reading pair for known vocabulary."""
    card_to_pairs = build_card_to_pairs(cards, kanji_readings)
    kanji_reading_to_cards = get_kanji_reading_to_matching_card(cards, card_to_pairs)
    update_kanji_reading_to_cards_with_max_weighted_interval(
        kanji_reading_to_cards,
        card_to_pairs,
    )
    return {
        pair: info.max_weighted_interval
        for pair, info in kanji_reading_to_cards.items()
    }


def build_vocabulary_word_index(vocabulary_cards, analyzer):
    """Index vocabulary cards by surface and lemma for sentence token matching."""
    index = VocabularyWordIndex()
    cards_with_surfaces = []

    for card in vocabulary_cards:
        surface = getattr(card, "word_surface", "") or ""
        readings = tuple(getattr(card, "word_readings", ()) or ())
        if not surface or not contains_kanji(surface):
            continue
        cards_with_surfaces.append((card, surface, readings))

    tokens_by_surface = (
        analyzer.extract_tokens_many([surface for _, surface, _ in cards_with_surfaces])
        if analyzer
        else {}
    )

    for card, surface, readings in cards_with_surfaces:
        tokens = tokens_by_surface.get(surface, [])
        if len(tokens) != 1:
            continue

        token = tokens[0]
        entry = VocabularyWordEntry(
            surface=surface,
            lemma=token.lemma,
            readings=readings or ((token.reading,) if token.reading else ()),
            known_interval=card.stability if card.stability > 0 else 0.0,
        )
        _add_entry(index, entry)

    return index


def _add_entry(index, entry):
    index.by_surface[entry.surface].append(entry)
    index.by_lemma[entry.lemma].append(entry)

    for reading in entry.readings:
        if reading:
            index.readings_by_surface[entry.surface].add(reading)
            index.readings_by_lemma[entry.lemma].add(reading)


def compute_sentence_scores(sentence_cards, vocabulary_index, kanji_readings, pair_intervals):
    """Compute strict and predicted scores for all sentence cards."""
    for sentence_card in sentence_cards:
        _compute_sentence_score(
            sentence_card,
            vocabulary_index,
            kanji_readings,
            pair_intervals,
        )


def _compute_sentence_score(sentence_card, vocabulary_index, kanji_readings, pair_intervals):
    strict_token_scores = []
    predicted_token_scores = []
    missing_words = 0
    inferred_words = 0

    for token in sentence_card.tokens:
        known_interval = _known_word_interval(token, vocabulary_index)
        if known_interval > 0:
            strict_token_scores.append(known_interval)
            predicted_token_scores.append(known_interval)
            continue

        missing_words += 1
        component_score = _component_score_for_token(token, kanji_readings, pair_intervals)
        if component_score > 0:
            inferred_words += 1
        predicted_token_scores.append(component_score)

    sentence_card.missing_words = missing_words
    sentence_card.inferred_words = inferred_words
    sentence_card.kanji_word_count = len(sentence_card.tokens)
    sentence_card.strict_score = (
        min(strict_token_scores)
        if strict_token_scores and missing_words == 0
        else 0.0
    )
    sentence_card.predicted_score = (
        min(predicted_token_scores)
        if predicted_token_scores
        else 0.0
    )


def _known_word_interval(token, vocabulary_index):
    intervals = []
    intervals.extend(
        _matching_known_intervals(
            token,
            vocabulary_index.by_surface.get(token.surface, []),
            vocabulary_index.readings_by_surface.get(token.surface, set()),
        )
    )
    intervals.extend(
        _matching_known_intervals(
            token,
            vocabulary_index.by_lemma.get(token.lemma, []),
            vocabulary_index.readings_by_lemma.get(token.lemma, set()),
        )
    )
    return max(intervals) if intervals else 0.0


def _matching_known_intervals(token, entries, key_readings):
    known_entries = [entry for entry in entries if entry.known_interval > 0]
    if not known_entries:
        return []

    matching = [
        entry.known_interval
        for entry in known_entries
        if _entry_matches_reading(entry, token.reading)
    ]
    if matching:
        return matching

    if len(key_readings) <= 1:
        return [entry.known_interval for entry in known_entries]

    return []


def _entry_matches_reading(entry, token_reading):
    if not token_reading:
        return False
    for reading in entry.readings:
        if reading == token_reading:
            return True
        if reading.startswith(token_reading) or token_reading.startswith(reading):
            return True
    return False


def _component_score_for_token(token, kanji_readings, pair_intervals):
    if not token.reading:
        return 0.0

    scores = [
        _component_score_for_text(token.surface, token.reading, kanji_readings, pair_intervals),
    ]
    if token.lemma != token.surface:
        scores.append(
            _component_score_for_text(token.lemma, token.reading, kanji_readings, pair_intervals)
        )
    return max(scores)


def _component_score_for_text(text, reading, kanji_readings, pair_intervals):
    if not text or not extract_kanji_only(text):
        return 0.0

    pairs = get_kanji_reading_pairs(f"{text}[{reading}]", kanji_readings)
    if not pairs:
        return 0.0

    kanji_to_intervals = defaultdict(list)
    for pair in pairs:
        kanji = pair.split("[", 1)[0]
        kanji_to_intervals[kanji].append(pair_intervals.get(pair, 0.0))

    max_intervals = [
        max(intervals)
        for intervals in kanji_to_intervals.values()
    ]
    return min(max_intervals) if max_intervals else 0.0


def assign_sentence_positions_and_priority(sentence_cards, new_card_ids):
    """Assign position and 0-100 priority to all sentence cards."""
    sorted_cards = sorted(sentence_cards, key=_sentence_sort_key)
    _assign_priority_scores(sorted_cards)
    for position, card in enumerate(sorted_cards, start=1):
        card.position = position


def _assign_priority_scores(sorted_cards):
    if not sorted_cards:
        return
    if len(sorted_cards) == 1:
        sorted_cards[0].priority_score = 100.0
        return

    denominator = len(sorted_cards) - 1
    for index, card in enumerate(sorted_cards):
        card.priority_score = 100.0 - (index / denominator * 100.0)


def _sentence_sort_key(sentence_card):
    return (
        -sentence_card.strict_score,
        -sentence_card.predicted_score,
        sentence_card.missing_words,
        sentence_card.inferred_words,
        sentence_card.kanji_word_count,
        min(sentence_card.card_ids) if sentence_card.card_ids else 0,
    )
