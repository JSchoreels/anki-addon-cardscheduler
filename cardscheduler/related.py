"""
Related words module - Find cards that share kanji characters.

This module handles:
- Finding related cards that share kanji with a given card
- Splitting related cards by known/unknown status
- Limiting results per kanji-reading combination
"""

import re
from collections import defaultdict

RELATED_CARDS_LIMIT_PER_KANJI_READING = 5

# Compiled regex for parsing kanji[reading] pairs
_PAIR_PATTERN = re.compile(r'([^[]+)\[([^]]*)\]')


def _parse_pair(pair):
    """Extract (kanji, reading) tuple from a pair string.

    Args:
        pair: String in format 'kanji[reading]', e.g. '大[だい]'

    Returns:
        Tuple of (kanji, reading) if valid, None otherwise.

    Example:
        >>> _parse_pair('大[だい]')
        ('大', 'だい')
    """
    match = _PAIR_PATTERN.match(pair)
    return match.groups() if match else None


def _build_pair_index(cards, card_to_pairs):
    """Build an index for fast lookup of cards by kanji and reading.

    Args:
        cards: List of CardInfo objects
        card_to_pairs: Dict mapping card_id to set of kanji[reading] pairs

    Returns:
        Nested dict: kanji -> reading -> list of CardInfo objects
    """
    index = defaultdict(lambda: defaultdict(list))
    for card in cards:
        for pair in sorted(card_to_pairs[card.card_id]):
            parsed = _parse_pair(pair)
            if parsed:
                kanji, reading = parsed
                index[kanji][reading].append(card)
    return index


def compute_related_words(cards, card_to_pairs):
    """Find all cards that share at least one kanji, split by known/unknown.

    Stores related cards as data structures (not HTML).
    Limits to RELATED_CARDS_LIMIT_PER_KANJI_READING examples per kanji-reading combination.

    Related cards are ordered by shared kanji count (fewer first), then
    stability (higher first), then order of discovery. Walking that order, a
    card is kept if any of its shared kanji, with that card's reading, is still
    below the limit; known and unknown cards have separate limits.

    Cards sharing a single kanji come first and only use one limit each, so
    they are the first cards (by stability) of their kanji/reading. Those lists
    are sorted once for all cards, and only the few cards sharing several kanji
    need to be looked at one by one.

    Args:
        cards: List of CardInfo objects
        card_to_pairs: Pre-computed mapping from card_id to set of kanji[reading] pairs
    """
    limit = RELATED_CARDS_LIMIT_PER_KANJI_READING
    kanji_index = _build_pair_index(cards, card_to_pairs)

    # Pairs are sorted so results (and thus note fields) are identical between
    # runs, as set order varies with Python's per-process hashing. When a card
    # has several readings for one kanji, the last one in sorted order is used.
    reading_by_card = {}
    for card in cards:
        readings = {}
        for pair in sorted(card_to_pairs[card.card_id]):
            parsed = _parse_pair(pair)
            if parsed:
                readings[parsed[0]] = parsed[1]
        reading_by_card[card.card_id] = readings

    # Per kanji: the discovery position of each card containing it, and its
    # cards grouped by reading and known/unknown, in related-card order.
    position_by_kanji = {}
    ranked_by_kanji = {}
    for kanji, cards_by_reading in kanji_index.items():
        unique = {}
        for reading_cards in cards_by_reading.values():
            for card in reading_cards:
                unique.setdefault(card.card_id, card)
        position_by_kanji[kanji] = {card_id: i for i, card_id in enumerate(unique)}
        ranked = {}
        for card in sorted(unique.values(), key=lambda card: -card.stability):
            reading = reading_by_card[card.card_id][kanji]
            known_cards, unknown_cards = ranked.setdefault(reading, ([], []))
            (known_cards if card.stability > 0 else unknown_cards).append(card)
        ranked_by_kanji[kanji] = [
            (reading, known_cards, unknown_cards)
            for reading, (known_cards, unknown_cards) in ranked.items()
        ]

    # (kanji, kanji) -> cards containing both, to find cards sharing several kanji
    cards_by_kanji_pair = defaultdict(list)
    for card in cards:
        card_kanji = sorted(reading_by_card[card.card_id])
        for i, first in enumerate(card_kanji):
            for second in card_kanji[i + 1:]:
                cards_by_kanji_pair[(first, second)].append(card)

    for card_info in cards:
        if not card_info.furigana_text:
            card_info.related_cards_known = []
            card_info.related_cards_unknown = []
            continue

        own_id = card_info.card_id
        current_kanji = sorted(reading_by_card[own_id])
        kanji_rank = {kanji: i for i, kanji in enumerate(current_kanji)}

        # Cards sharing several kanji
        multi_cards = {}
        for i, first in enumerate(current_kanji):
            for second in current_kanji[i + 1:]:
                for card in cards_by_kanji_pair.get((first, second), ()):
                    if card.card_id != own_id:
                        multi_cards[card.card_id] = card

        # Cards sharing a single kanji: the first ones of each kanji/reading
        counts_known = {}
        counts_unknown = {}
        single_known = []
        single_unknown = []
        for kanji in current_kanji:
            rank = kanji_rank[kanji]
            positions = position_by_kanji[kanji]
            for reading, known_cards, unknown_cards in ranked_by_kanji[kanji]:
                for ranked_cards, counts, target_list in (
                    (known_cards, counts_known, single_known),
                    (unknown_cards, counts_unknown, single_unknown),
                ):
                    count = 0
                    for card in ranked_cards:
                        card_id = card.card_id
                        if card_id == own_id or card_id in multi_cards:
                            continue
                        target_list.append((
                            (-card.stability, rank, positions[card_id]),
                            card,
                            {kanji},
                        ))
                        count += 1
                        if count == limit:
                            break
                    if count:
                        counts[(kanji, reading)] = count

        single_known.sort(key=lambda item: item[0])
        single_unknown.sort(key=lambda item: item[0])
        known_words = [(card, shared) for _, card, shared in single_known]
        unknown_words = [(card, shared) for _, card, shared in single_unknown]

        if multi_cards:
            current_set = set(current_kanji)
            multi_related = []
            for card_id, card in multi_cards.items():
                shared = reading_by_card[card_id].keys() & current_set
                first = min(shared, key=kanji_rank.__getitem__)
                multi_related.append((
                    (len(shared), -card.stability, kanji_rank[first],
                     position_by_kanji[first][card_id]),
                    card,
                    shared,
                ))
            multi_related.sort(key=lambda item: item[0])

            for _, card, shared in multi_related:
                if card.stability > 0:
                    counts = counts_known
                    target_list = known_words
                else:
                    counts = counts_unknown
                    target_list = unknown_words
                readings = reading_by_card[card.card_id]
                keys = [(kanji, readings[kanji]) for kanji in shared]
                if any(counts.get(key, 0) < limit for key in keys):
                    for key in keys:
                        counts[key] = counts.get(key, 0) + 1
                    target_list.append((card, shared))

        card_info.related_cards_known = known_words
        card_info.related_cards_unknown = unknown_words
