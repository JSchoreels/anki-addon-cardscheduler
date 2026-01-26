"""
Scheduler module - Core scheduling logic for card prioritization.

This module handles:
- Card information data structures (CardInfo, KanjiReadingInfo)
- Score computation based on kanji/reading pairs
- Unlock potential calculation
- Card positioning and sorting
"""

from collections import defaultdict

from .dictionary import load_kanji_dictionnary_readings, extract_kanji_only
from .word_parser import get_kanji_reading_pairs, count_kanji_in_text, count_kana_in_text
from .related import compute_related_words


def build_card_to_pairs(cards, kanji_readings):
    """Build mapping from card_id to set of kanji[reading] pairs.

    This is computed once and passed to functions that need it to avoid
    redundant calls to get_kanji_reading_pairs.

    Args:
        cards: List of CardInfo objects
        kanji_readings: Dictionary of kanji readings from kanjidic

    Returns:
        Dict mapping card_id to set of pair strings like {'大[だい]', '学[がく]'}
    """
    return {
        card.card_id: get_kanji_reading_pairs(card.furigana_text, kanji_readings) if card.furigana_text else set()
        for card in cards
    }

class CardInfo:
    """Information about a single card including computed scores and metrics."""

    def __init__(self, card_id, furigana_text, stability):
        self.card_id = card_id
        self.furigana_text = furigana_text
        self.stability = stability
        self.score = 0  # Initialize score
        self.unknown_kanji_readings = 0
        self.unlock_potential = 0  # Max unlock potential of any unknown kanji/reading pair in this card
        self.unlock_median_score_increase = 0  # Median score increase for cards this would unlock
        self.score_without_missing = 0  # Score this card would have if missing kanji were known
        self.missing_kanji_count = 0  # Number of unknown kanji/readings in this card
        self.position = 0  # Learning order position (1 = highest priority)
        self.related_cards_known = []  # List of (CardInfo, shared_kanji_set) tuples with stability > 0
        self.related_cards_unknown = []  # List of (CardInfo, shared_kanji_set) tuples with stability = 0
        self.cards_with_kanji = 0  # Total cards sharing any kanji (visual familiarity)
        self.cards_with_kanji_known = 0  # Known cards sharing any kanji
        self.cards_with_kanji_unknown = 0  # Unknown cards sharing any kanji
        self.percentile_rank = 0.0  # Combined percentile rank (product of all metric percentiles)

    def __repr__(self):
        return f"CardInfo(id={self.card_id}, furigana='{self.furigana_text}', interval={self.stability}, score={self.score}, unknowns={self.unknown_kanji_readings}, unlock={self.unlock_potential}, median_increase={self.unlock_median_score_increase}, pos={self.position})"

    def __hash__(self):
        """Hash based on card_id for proper set deduplication."""
        return hash(self.card_id)

    def __eq__(self, other):
        """Equality based on card_id for proper set deduplication."""
        if not isinstance(other, CardInfo):
            return False
        return self.card_id == other.card_id


class KanjiReadingInfo:
    """Information about a specific kanji-reading pair across all cards."""

    def __init__(self):
        self.matched_cards = set()
        self.max_weighted_interval = 0.0
        self.unlock_potential = 0  # Number of cards that would get score > 0 if this pair was learned
        self.unlock_median_score_increase = 0  # Median score increase for unlocked cards

    def __repr__(self):
        return f"KanjiReadingInfo(max_weighted_interval={self.max_weighted_interval}, matched_cards_count={len(self.matched_cards)}, unlock_potential={self.unlock_potential})"


def get_kanji_reading_to_matching_card(cards, card_to_pairs):
    """Build a mapping from kanji-reading pairs to cards that contain them.

    Args:
        cards: List of CardInfo objects
        card_to_pairs: Pre-computed mapping from card_id to set of pairs

    Returns:
        Dict mapping pair string to KanjiReadingInfo
    """
    kanji_reading_to_cards = {}
    for card_info in cards:
        for pair in card_to_pairs[card_info.card_id]:
            if pair not in kanji_reading_to_cards:
                kanji_reading_to_cards[pair] = KanjiReadingInfo()
            kanji_reading_to_cards[pair].matched_cards.add(card_info)
    return kanji_reading_to_cards


def build_kanji_to_cards_mapping(cards):
    """Build mapping from kanji characters to cards containing them.

    Returns:
        Dict[str, Set[CardInfo]]: Mapping from kanji char to cards
    """
    kanji_to_cards = defaultdict(set)
    for card in cards:
        kanji_chars = extract_kanji_only(card.furigana_text)
        for kanji in kanji_chars:
            kanji_to_cards[kanji].add(card)
    return kanji_to_cards


def compute_kanji_familiarity(cards, kanji_to_cards):
    """Compute visual kanji familiarity metrics for each card.

    For each card, count how many OTHER cards share any kanji character,
    split by whether those cards are known (stability > 0) or unknown.
    """
    for card in cards:
        kanji_chars = set(extract_kanji_only(card.furigana_text))
        if not kanji_chars:
            continue

        # Collect all OTHER cards that share any kanji
        related_cards = set()
        for kanji in kanji_chars:
            related_cards.update(kanji_to_cards.get(kanji, set()))
        related_cards.discard(card)  # Exclude self

        # Split by known/unknown (stability > 0 means known)
        known_count = sum(1 for c in related_cards if c.stability > 0)
        unknown_count = len(related_cards) - known_count

        card.cards_with_kanji_known = known_count
        card.cards_with_kanji_unknown = unknown_count
        card.cards_with_kanji = known_count + unknown_count


def update_kanji_reading_to_cards_with_max_weighted_interval(kanji_reading_to_cards, card_to_pairs):
    """Calculate weighted intervals for each kanji-reading pair.

    Args:
        kanji_reading_to_cards: Mapping from pair to KanjiReadingInfo
        card_to_pairs: Pre-computed mapping from card_id to set of pairs
    """
    for pair, info in kanji_reading_to_cards.items():
        weighted_intervals = []
        for card in info.matched_cards:
            if card.stability > 0:
                pairs = card_to_pairs[card.card_id]
                unique_kanji_count = len(set(p.split('[')[0] for p in pairs))
                weighted_interval = card.stability / 2 ** (unique_kanji_count - 1)
                weighted_intervals.append(weighted_interval)

        info.max_weighted_interval = max(weighted_intervals) if weighted_intervals else 0.0


def compute_unlock_potential(kanji_reading_to_cards, card_to_pairs):
    """Compute unlock potential for each kanji/reading pair.

    For each pair, computes:
    1. How many cards would get score > 0 if that pair was learned (unlock_potential)
    2. The median score increase for unlocked cards (unlock_median_score_increase)

    Args:
        kanji_reading_to_cards: Mapping from pair to KanjiReadingInfo
        card_to_pairs: Pre-computed mapping from card_id to set of pairs
    """
    SIMULATED_LEARNED_INTERVAL = 100.0

    for pair, pair_info in kanji_reading_to_cards.items():
        if pair_info.max_weighted_interval > 0:
            pair_info.unlock_potential = 0
            pair_info.unlock_median_score_increase = 0
            continue

        unlock_count = 0
        score_increases = []

        for card in pair_info.matched_cards:
            if card.score > 0:
                continue

            kanji_reading_pairs = card_to_pairs[card.card_id]

            kanji_to_intervals = defaultdict(list)
            for p in kanji_reading_pairs:
                if p in kanji_reading_to_cards:
                    kanji = p.split('[')[0]
                    interval = kanji_reading_to_cards[p].max_weighted_interval
                    kanji_to_intervals[kanji].append(interval)

            known_kanji_scores = [
                max(intervals) for intervals in kanji_to_intervals.values()
                if max(intervals) > 0
            ]
            score_without_missing = min(known_kanji_scores) if known_kanji_scores else 0

            kanji_to_intervals_simulated = defaultdict(list)
            for p in kanji_reading_pairs:
                if p in kanji_reading_to_cards:
                    kanji = p.split('[')[0]
                    interval = SIMULATED_LEARNED_INTERVAL if p == pair else kanji_reading_to_cards[p].max_weighted_interval
                    kanji_to_intervals_simulated[kanji].append(interval)

            max_intervals_per_kanji = [
                max(intervals) for intervals in kanji_to_intervals_simulated.values()
            ]
            new_score = min(max_intervals_per_kanji) if max_intervals_per_kanji else 0

            if new_score > 0:
                unlock_count += 1
                score_increases.append(score_without_missing)

        pair_info.unlock_potential = unlock_count

        if score_increases:
            score_increases.sort()
            n = len(score_increases)
            if n % 2 == 0:
                pair_info.unlock_median_score_increase = (score_increases[n//2-1] + score_increases[n//2]) / 2
            else:
                pair_info.unlock_median_score_increase = score_increases[n//2]
        else:
            pair_info.unlock_median_score_increase = 0


def compute_scores(cards):
    """Compute familiarity scores for a list of CardInfo objects."""
    kanji_readings = load_kanji_dictionnary_readings()

    # Build card_to_pairs once, used by all subsequent functions
    card_to_pairs = build_card_to_pairs(cards, kanji_readings)

    kanji_reading_to_cards = get_kanji_reading_to_matching_card(cards, card_to_pairs)
    update_kanji_reading_to_cards_with_max_weighted_interval(kanji_reading_to_cards, card_to_pairs)

    # Compute visual kanji familiarity metrics
    kanji_to_cards = build_kanji_to_cards_mapping(cards)
    compute_kanji_familiarity(cards, kanji_to_cards)

    # Compute score for each card
    for card_info in cards:
        pairs = card_to_pairs[card_info.card_id]
        if not pairs:
            card_info.score = 0
            continue

        kanji_to_intervals = defaultdict(list)
        for pair in pairs:
            if pair in kanji_reading_to_cards:
                kanji = pair.split('[')[0]
                interval = kanji_reading_to_cards[pair].max_weighted_interval
                kanji_to_intervals[kanji].append(interval)

        max_intervals_per_kanji = [
            max(intervals) for intervals in kanji_to_intervals.values()
        ]

        card_info.score = min(max_intervals_per_kanji) if max_intervals_per_kanji else 0
        card_info.unknown_kanji_readings = sum(
            1 for intervals in kanji_to_intervals.values() if max(intervals) == 0.0
        )

    # Compute unlock potential for each kanji/reading pair
    compute_unlock_potential(kanji_reading_to_cards, card_to_pairs)

    # Update each card's unlock potential and related metrics
    for card_info in cards:
        pairs = card_to_pairs[card_info.card_id]
        if not pairs:
            card_info.unlock_potential = 0
            card_info.unlock_median_score_increase = 0
            card_info.score_without_missing = 0
            card_info.missing_kanji_count = 0
            continue

        if card_info.score > 0:
            card_info.unlock_potential = 0
            card_info.unlock_median_score_increase = 0
            card_info.score_without_missing = card_info.score
            card_info.missing_kanji_count = 0
            continue

        kanji_to_intervals = defaultdict(list)
        for pair in pairs:
            if pair in kanji_reading_to_cards:
                kanji = pair.split('[')[0]
                interval = kanji_reading_to_cards[pair].max_weighted_interval
                kanji_to_intervals[kanji].append(interval)

        known_kanji_scores = []
        missing_kanji_count = 0
        for intervals in kanji_to_intervals.values():
            max_interval = max(intervals)
            if max_interval > 0:
                known_kanji_scores.append(max_interval)
            else:
                missing_kanji_count += 1

        card_info.score_without_missing = min(known_kanji_scores) if known_kanji_scores else 0
        card_info.missing_kanji_count = missing_kanji_count

        max_unlock = 0
        max_median_increase = 0
        for pair in pairs:
            if pair in kanji_reading_to_cards:
                pair_info = kanji_reading_to_cards[pair]
                if pair_info.max_weighted_interval == 0:
                    if pair_info.unlock_potential > max_unlock:
                        max_unlock = pair_info.unlock_potential
                        max_median_increase = pair_info.unlock_median_score_increase
                    elif pair_info.unlock_potential == max_unlock:
                        max_median_increase = max(max_median_increase, pair_info.unlock_median_score_increase)

        card_info.unlock_potential = max_unlock
        card_info.unlock_median_score_increase = max_median_increase

    # Compute related words for each card
    compute_related_words(cards, card_to_pairs)


def compute_percentile_ranks(cards, metric_getters):
    """Compute percentile ranks for multiple metrics across a set of cards.

    For each metric, cards are ranked and assigned a percentile from 1/n to 1.0,
    where n is the number of cards. Ties receive the average percentile of their
    tied positions.

    Args:
        cards: List of CardInfo objects
        metric_getters: List of (get_value_func, higher_is_better) tuples
            - get_value_func: Function that takes a card and returns the metric value
            - higher_is_better: If True, higher values get higher percentiles

    Returns:
        Dict mapping card_id to list of percentiles (one per metric, in order)
    """
    if not cards:
        return {}

    n = len(cards)
    result = {card.card_id: [] for card in cards}

    for get_value, higher_is_better in metric_getters:
        # Get values for all cards
        card_values = [(card, get_value(card)) for card in cards]

        # Sort: ascending for higher_is_better (so higher values get higher ranks)
        # descending for lower_is_better (so lower values get higher ranks)
        card_values.sort(key=lambda x: x[1], reverse=not higher_is_better)

        # Assign percentiles with tie handling
        i = 0
        while i < n:
            current_value = card_values[i][1]
            j = i
            while j < n and card_values[j][1] == current_value:
                j += 1

            # Average rank for ties (1-indexed ranks from i+1 to j)
            avg_rank = (i + 1 + j) / 2
            percentile = avg_rank / n

            for k in range(i, j):
                result[card_values[k][0].card_id].append(percentile)

            i = j

    return result


def assign_positions_to_new_cards(cards, new_card_ids):
    """
    Assign learning order positions only to new cards using percentile-based ranking.

    Cards are ranked by the product of their percentiles across multiple metrics.
    This gives a balanced ranking where being good across all dimensions matters
    more than being excellent in just one dimension.

    Example: A card at 50th percentile for two metrics gets 0.5 * 0.5 = 0.25 (25%)
             A card at 90th percentile for two metrics gets 0.9 * 0.9 = 0.81 (81%)

    Metrics included (higher percentile = better):
    - Unlock potential (higher is better) - more cards unlocked by learning this
    - Cards with kanji known (higher is better) - visual familiarity
    - Cards with kanji total (higher is better) - kanji prevalence
    - Unlock median score increase (higher is better) - unlocked cards have higher scores
    - Missing kanji count (lower is better) - fewer missing kanji
    - Kanji count (lower is better) - simpler words preferred
    - Kana count (lower is better) - shorter words preferred
    - Score without missing (lower is better) - lower score needs more help

    Cards with score > 0 are sorted by score first (more familiar = learn first),
    then by percentile product for tiebreaking.

    Args:
        cards: List of all CardInfo objects with scores computed
        new_card_ids: Set of card IDs that are in 'new' state
    """
    # Filter only new cards
    new_cards = [c for c in cards if c.card_id in new_card_ids]

    if not new_cards:
        return

    # Define metrics: (getter function, higher_is_better)
    # Using explicit functions to avoid lambda capture issues
    def get_unlock_potential(c):
        return c.unlock_potential

    def get_cards_with_kanji_known(c):
        return c.cards_with_kanji_known

    def get_cards_with_kanji(c):
        return c.cards_with_kanji

    def get_unlock_median_score_increase(c):
        return c.unlock_median_score_increase

    def get_missing_kanji_count(c):
        return c.missing_kanji_count

    def get_kanji_count(c):
        return count_kanji_in_text(c.furigana_text)

    def get_kana_count(c):
        return count_kana_in_text(c.furigana_text)

    def get_score_without_missing(c):
        return c.score_without_missing

    metric_getters = [
        (get_unlock_potential, True),              # Higher unlock potential = better
        (get_cards_with_kanji_known, True),        # More known cards with same kanji = better
        (get_cards_with_kanji, True),              # More total cards with same kanji = better
        (get_unlock_median_score_increase, True),  # Higher median score increase = better
        (get_missing_kanji_count, False),          # Fewer missing kanji = better
        (get_kanji_count, False),                  # Fewer kanji (simpler) = better
        (get_kana_count, False),                   # Fewer kana (shorter) = better
        (get_score_without_missing, False),        # Lower score = needs more help = better
    ]

    # Compute percentile ranks for each metric
    percentile_ranks = compute_percentile_ranks(new_cards, metric_getters)

    # Compute product of percentiles for each card
    products = {}
    for card in new_cards:
        percentiles = percentile_ranks[card.card_id]
        product = 1.0
        for p in percentiles:
            product *= p
        products[card.card_id] = product

    # Normalize products to 0-100 scale (P0 = worst, P100 = best)
    # Sort cards by product to determine ranking
    n = len(new_cards)
    if n > 1:
        sorted_by_product = sorted(new_cards, key=lambda c: products[c.card_id])
        i = 0
        while i < n:
            current_product = products[sorted_by_product[i].card_id]
            j = i
            while j < n and products[sorted_by_product[j].card_id] == current_product:
                j += 1
            # Average rank for ties (0-indexed), then scale to 0-100
            avg_rank = (i + j - 1) / 2  # Average of positions i to j-1
            normalized = (avg_rank / (n - 1)) * 100 if n > 1 else 100
            for k in range(i, j):
                sorted_by_product[k].percentile_rank = normalized
            i = j
    else:
        # Single card gets 100%
        for card in new_cards:
            card.percentile_rank = 100.0

    # Sort by score (descending) first, then by percentile product (descending)
    sorted_new_cards = sorted(new_cards, key=lambda c: (
        -c.score,
        -c.percentile_rank
    ))

    # Assign positions only to new cards
    for position, card in enumerate(sorted_new_cards, start=1):
        card.position = position
