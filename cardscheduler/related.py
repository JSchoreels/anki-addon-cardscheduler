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


def _extract_kanji_set_from_pairs(pairs):
    """Extract the set of kanji characters from a collection of pair strings.

    Args:
        pairs: Collection of strings in format 'kanji[reading]'

    Returns:
        Set of kanji characters.

    Example:
        >>> _extract_kanji_set_from_pairs({'大[だい]', '学[がく]'})
        {'大', '学'}
    """
    result = set()
    for pair in pairs:
        parsed = _parse_pair(pair)
        if parsed:
            result.add(parsed[0])
    return result


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
        for pair in card_to_pairs[card.card_id]:
            parsed = _parse_pair(pair)
            if parsed:
                kanji, reading = parsed
                index[kanji][reading].append(card)
    return index


def _find_shared_kanji(related_pairs, current_kanji):
    """Find kanji characters shared between a card's pairs and a reference set.

    Args:
        related_pairs: Set of kanji[reading] pairs from another card
        current_kanji: Set of kanji characters to match against

    Returns:
        Set of kanji characters that appear in both.
    """
    return _extract_kanji_set_from_pairs(related_pairs) & current_kanji


def _get_kanji_reading_map(pairs, kanji_filter=None):
    """Build a mapping from kanji to reading for the given pairs.

    Args:
        pairs: Collection of kanji[reading] pair strings
        kanji_filter: Optional set of kanji to include. If None, includes all.

    Returns:
        Dict mapping kanji character to its reading.

    Example:
        >>> _get_kanji_reading_map({'大[だい]', '学[がく]'}, kanji_filter={'大'})
        {'大': 'だい'}
    """
    result = {}
    for pair in pairs:
        parsed = _parse_pair(pair)
        if parsed:
            kanji, reading = parsed
            if kanji_filter is None or kanji in kanji_filter:
                result[kanji] = reading
    return result


def _can_add_related_card(kanji_reading_map, counts, limit):
    """Check if a related card can be added without exceeding per-reading limits.

    A card can be added if ANY of its kanji-reading combinations is below the limit.

    Args:
        kanji_reading_map: Dict mapping kanji to reading for the card
        counts: Nested dict tracking current counts per kanji per reading
        limit: Maximum number of cards per kanji-reading combination

    Returns:
        True if the card can be added, False otherwise.
    """
    for kanji, reading in kanji_reading_map.items():
        if counts.get(kanji, {}).get(reading, 0) < limit:
            return True
    return False


def _increment_counts(kanji_reading_map, counts):
    """Increment the count for each kanji-reading pair in a card.

    Args:
        kanji_reading_map: Dict mapping kanji to reading for the card being added
        counts: Nested dict to update (kanji -> reading -> count)
    """
    for kanji, reading in kanji_reading_map.items():
        if kanji not in counts:
            counts[kanji] = {}
        if reading not in counts[kanji]:
            counts[kanji][reading] = 0
        counts[kanji][reading] += 1


def compute_related_words(cards, card_to_pairs):
    """Find all cards that share at least one kanji, split by known/unknown.

    Stores related cards as data structures (not HTML).
    Limits to RELATED_CARDS_LIMIT_PER_KANJI_READING examples per kanji-reading combination.

    Args:
        cards: List of CardInfo objects
        card_to_pairs: Pre-computed mapping from card_id to set of kanji[reading] pairs
    """
    kanji_index = _build_pair_index(cards, card_to_pairs)

    for card_info in cards:
        if not card_info.furigana_text:
            card_info.related_cards_known = []
            card_info.related_cards_unknown = []
            continue

        current_pairs = card_to_pairs[card_info.card_id]
        current_kanji = _extract_kanji_set_from_pairs(current_pairs)

        # Collect all related cards that share any kanji
        related_cards_map = {}
        for kanji in current_kanji:
            for reading_cards in kanji_index[kanji].values():
                for related_card in reading_cards:
                    if related_card.card_id == card_info.card_id:
                        continue
                    if related_card.card_id in related_cards_map:
                        continue
                    shared = _find_shared_kanji(card_to_pairs[related_card.card_id], current_kanji)
                    if shared:
                        related_cards_map[related_card.card_id] = (related_card, shared)

        # Sort by: 1) shared kanji count (fewer first), 2) stability (higher first)
        related_cards_sorted = sorted(
            related_cards_map.values(),
            key=lambda item: (len(item[1]), -item[0].stability)
        )

        # Separate into known/unknown with per-kanji-reading limits
        counts_known = {}
        counts_unknown = {}
        known_words = []
        unknown_words = []

        for related_card, shared_kanji in related_cards_sorted:
            is_known = related_card.stability > 0
            counts = counts_known if is_known else counts_unknown
            target_list = known_words if is_known else unknown_words

            # Get kanji->reading mapping for shared kanji only
            kanji_reading_map = _get_kanji_reading_map(
                card_to_pairs[related_card.card_id],
                kanji_filter=shared_kanji
            )

            if _can_add_related_card(kanji_reading_map, counts, RELATED_CARDS_LIMIT_PER_KANJI_READING):
                _increment_counts(kanji_reading_map, counts)
                target_list.append((related_card, shared_kanji))

        card_info.related_cards_known = known_words
        card_info.related_cards_unknown = unknown_words
