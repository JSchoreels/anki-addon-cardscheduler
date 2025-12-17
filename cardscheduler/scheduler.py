"""
Scheduler module - Core scheduling logic for card prioritization.

This module handles:
- Card information data structures (CardInfo, KanjiReadingInfo)
- Score computation based on kanji/reading pairs
- Unlock potential calculation
- Card positioning and sorting
"""

import statistics
from collections import defaultdict

from .dictionary import load_kanji_dictionnary_readings
from .word_parser import get_kanji_reading_pairs, count_kanji_in_text, count_kana_in_text


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
        self.related_words_known = []  # Related words with stability > 0
        self.related_words_unknown = []  # Related words with stability = 0

    def __repr__(self):
        return f"CardInfo(id={self.card_id}, furigana='{self.furigana_text}', interval={self.stability}, score={self.score}, unknowns={self.unknown_kanji_readings}, unlock={self.unlock_potential}, median_increase={self.unlock_median_score_increase}, pos={self.position})"


class KanjiReadingInfo:
    """Information about a specific kanji-reading pair across all cards."""

    def __init__(self):
        self.matched_cards = set()
        self.max_weighted_interval = 0.0
        self.unlock_potential = 0  # Number of cards that would get score > 0 if this pair was learned
        self.unlock_median_score_increase = 0  # Median score increase for unlocked cards

    def __repr__(self):
        return f"KanjiReadingInfo(max_weighted_interval={self.max_weighted_interval}, matched_cards_count={len(self.matched_cards)}, unlock_potential={self.unlock_potential})"


def get_kanji_reading_to_matching_card(cards, kanji_readings):
    """Build a mapping from kanji-reading pairs to cards that contain them."""
    kanji_reading_to_cards = {}
    for card_info in cards:
        if not card_info.furigana_text:
            continue
        kanji_reading_pairs = get_kanji_reading_pairs(card_info.furigana_text, kanji_readings)
        for pair in kanji_reading_pairs:
            if pair not in kanji_reading_to_cards:
                kanji_reading_to_cards[pair] = KanjiReadingInfo()
            kanji_reading_to_cards[pair].matched_cards.add(card_info)
    return kanji_reading_to_cards


def update_kanji_reading_to_cards_with_max_weighted_interval(kanji_reading_to_cards, kanji_readings):
    """Calculate weighted intervals for each kanji-reading pair."""
    for pair, info in kanji_reading_to_cards.items():
        weighted_intervals = []
        for card in info.matched_cards:
            if card.stability > 0:
                pairs = get_kanji_reading_pairs(card.furigana_text, kanji_readings)
                unique_kanji_count = len(set(p.split('[')[0] for p in pairs))
                weighted_interval = card.stability / 2 ** (unique_kanji_count - 1)
                weighted_intervals.append(weighted_interval)

        info.max_weighted_interval = max(weighted_intervals) if weighted_intervals else 0.0


def print_kanji_readings_with_average_interval(kanji_reading_to_cards):
    """Debug output: Show global kanji-reading averages."""
    print("Global kanji-reading averages:")
    for pair, info in kanji_reading_to_cards.items():
        print(
            f"Pair '{pair}': average_interval={info.max_weighted_interval:.2f}, matched_cards_count={len(info.matched_cards)}")


def compute_unlock_potential(kanji_reading_to_cards, kanji_readings, cards):
    """
    For each kanji/reading pair, compute:
    1. How many cards would get score > 0 if that pair was learned (unlock_potential)
    2. The median score increase for unlocked cards (unlock_median_score_increase)

    The score increase is calculated as the "score without missing kanji" - the minimum
    score across only the KNOWN kanji in the card (excluding unknown ones).
    """
    SIMULATED_LEARNED_INTERVAL = 100.0  # High interval to simulate "learned" state

    # For each kanji/reading pair with interval 0
    for pair, pair_info in kanji_reading_to_cards.items():
        if pair_info.max_weighted_interval > 0:
            # Already learned, no unlock potential
            pair_info.unlock_potential = 0
            pair_info.unlock_median_score_increase = 0
            continue

        unlock_count = 0
        score_increases = []  # Track score increases for unlocked cards

        # Check each card containing this pair
        for card in pair_info.matched_cards:
            # Only consider cards with current score <= 0
            if card.score > 0:
                continue

            # Get all kanji/reading pairs for this card
            kanji_reading_pairs = get_kanji_reading_pairs(card.furigana_text, kanji_readings)

            # Group by kanji, collect intervals for each reading
            kanji_to_intervals = defaultdict(list)
            for p in kanji_reading_pairs:
                if p in kanji_reading_to_cards:
                    kanji = p.split('[')[0]
                    interval = kanji_reading_to_cards[p].max_weighted_interval
                    kanji_to_intervals[kanji].append(interval)

            # Calculate "score without missing" - minimum across only KNOWN kanji (interval > 0)
            known_kanji_scores = []
            for kanji, intervals in kanji_to_intervals.items():
                max_interval = max(intervals)
                if max_interval > 0:  # Only include known kanji
                    known_kanji_scores.append(max_interval)

            score_without_missing = min(known_kanji_scores) if known_kanji_scores else 0

            # Now simulate learning this specific pair
            kanji_to_intervals_simulated = defaultdict(list)
            for p in kanji_reading_pairs:
                if p in kanji_reading_to_cards:
                    kanji = p.split('[')[0]
                    # Use simulated interval if this is the pair we're testing
                    interval = SIMULATED_LEARNED_INTERVAL if p == pair else kanji_reading_to_cards[p].max_weighted_interval
                    kanji_to_intervals_simulated[kanji].append(interval)

            # Calculate new score with simulated learning
            max_intervals_per_kanji = [
                max(intervals) for intervals in kanji_to_intervals_simulated.values()
            ]
            new_score = min(max_intervals_per_kanji) if max_intervals_per_kanji else 0

            # Count if this card would be unlocked
            if new_score > 0:
                unlock_count += 1
                # The score increase is the score without missing kanji
                score_increases.append(score_without_missing)

        pair_info.unlock_potential = unlock_count

        # Calculate median score increase
        if score_increases:
            score_increases.sort()
            n = len(score_increases)
            if n % 2 == 0:
                pair_info.unlock_median_score_increase = (score_increases[n//2-1] + score_increases[n//2]) / 2
            else:
                pair_info.unlock_median_score_increase = score_increases[n//2]
        else:
            pair_info.unlock_median_score_increase = 0


def compute_related_words(cards, kanji_reading_to_cards, kanji_readings):
    """Find all cards that share at least one kanji/reading pair, split by known/unknown."""
    for card_info in cards:
        if not card_info.furigana_text:
            card_info.related_words_known = []
            card_info.related_words_unknown = []
            continue

        kanji_reading_pairs = get_kanji_reading_pairs(card_info.furigana_text, kanji_readings)

        related_cards_set = set()
        for pair in kanji_reading_pairs:
            if pair in kanji_reading_to_cards:
                for related_card in kanji_reading_to_cards[pair].matched_cards:
                    if related_card.card_id != card_info.card_id:
                        related_cards_set.add(related_card)

        related_cards_list = sorted(list(related_cards_set), key=lambda c: c.furigana_text)

        card_info.related_words_known = [c.furigana_text for c in related_cards_list if c.stability > 0]
        card_info.related_words_unknown = [c.furigana_text for c in related_cards_list if c.stability == 0]


def compute_scores(cards):
    """Compute familiarity scores for a list of CardInfo objects."""

    kanji_readings = load_kanji_dictionnary_readings()

    kanji_reading_to_cards = get_kanji_reading_to_matching_card(cards, kanji_readings)

    update_kanji_reading_to_cards_with_max_weighted_interval(kanji_reading_to_cards, kanji_readings)

    print_kanji_readings_with_average_interval(kanji_reading_to_cards)

    # Step 2: Compute score for each card (simplified)
    for card_info in cards:
        if not card_info.furigana_text:
            card_info.score = 0
            continue
        kanji_reading_pairs = get_kanji_reading_pairs(card_info.furigana_text, kanji_readings)

        # Group by kanji, collect intervals for each reading
        kanji_to_intervals = defaultdict(list)
        for pair in kanji_reading_pairs:
            if pair in kanji_reading_to_cards:
                kanji = pair.split('[')[0]  # Extract kanji from '当[あ.たる]'
                interval = kanji_reading_to_cards[pair].max_weighted_interval
                kanji_to_intervals[kanji].append(interval)

        # Take max interval for each kanji, then min across all kanji
        max_intervals_per_kanji = [
            max(intervals) for intervals in kanji_to_intervals.values()
        ]

        card_info.score = min(max_intervals_per_kanji) if max_intervals_per_kanji else 0
        card_info.unknown_kanji_readings = sum(
            1 for intervals in kanji_to_intervals.values() if max(intervals) == 0.0
        )

    # Step 3: Compute unlock potential for each kanji/reading pair
    compute_unlock_potential(kanji_reading_to_cards, kanji_readings, cards)

    # Step 4: Update each card's unlock potential, median score increase, score without missing, and missing count
    for card_info in cards:
        if not card_info.furigana_text:
            card_info.unlock_potential = 0
            card_info.unlock_median_score_increase = 0
            card_info.score_without_missing = 0
            card_info.missing_kanji_count = 0
            continue

        kanji_reading_pairs = get_kanji_reading_pairs(card_info.furigana_text, kanji_readings)

        if card_info.score > 0:
            # Card already has positive score - no missing kanji
            card_info.unlock_potential = 0
            card_info.unlock_median_score_increase = 0
            card_info.score_without_missing = card_info.score
            card_info.missing_kanji_count = 0
            continue

        # Group by kanji, collect intervals for each reading
        kanji_to_intervals = defaultdict(list)
        for pair in kanji_reading_pairs:
            if pair in kanji_reading_to_cards:
                kanji = pair.split('[')[0]
                interval = kanji_reading_to_cards[pair].max_weighted_interval
                kanji_to_intervals[kanji].append(interval)

        # Calculate score without missing kanji (min of only known kanji)
        known_kanji_scores = []
        missing_kanji_count = 0
        for kanji, intervals in kanji_to_intervals.items():
            max_interval = max(intervals)
            if max_interval > 0:
                known_kanji_scores.append(max_interval)
            else:
                missing_kanji_count += 1

        card_info.score_without_missing = min(known_kanji_scores) if known_kanji_scores else 0
        card_info.missing_kanji_count = missing_kanji_count

        # Find the unknown pair with max unlock potential and its median score increase
        max_unlock = 0
        max_median_increase = 0

        for pair in kanji_reading_pairs:
            if pair in kanji_reading_to_cards:
                pair_info = kanji_reading_to_cards[pair]
                # Only consider pairs that are unknown (interval = 0)
                if pair_info.max_weighted_interval == 0:
                    if pair_info.unlock_potential > max_unlock:
                        max_unlock = pair_info.unlock_potential
                        max_median_increase = pair_info.unlock_median_score_increase
                    elif pair_info.unlock_potential == max_unlock:
                        # If same unlock potential, take the higher median score increase
                        max_median_increase = max(max_median_increase, pair_info.unlock_median_score_increase)

        card_info.unlock_potential = max_unlock
        card_info.unlock_median_score_increase = max_median_increase

    # Step 5: Compute related words for each card
    compute_related_words(cards, kanji_reading_to_cards, kanji_readings)


def assign_positions_to_new_cards(cards, new_card_ids):
    """
    Assign learning order positions only to new cards.

    Sorting priority for cards with score = 0 (have unknown kanji):
    1. Score (descending) - always 0 for these cards
    2. Unlock potential (descending) - more cards would be fully unlocked by learning this
    3. Unlock median score increase (descending) - unlocked cards would have higher scores
    4. Missing kanji count (ascending) - fewer missing kanji
    5. Kanji count (ascending) - fewer kanji = simpler word
    6. Kana count (ascending) - fewer kana = shorter word
    7. Score without missing (ascending) - lower score = needs more help (final tiebreaker)

    Sorting priority for cards with score > 0 (all kanji known):
    1. Score (descending) - higher score = more familiar = learn first
    2. Kanji count (ascending) - fewer kanji = simpler word
    3. Kana count (ascending) - fewer kana = shorter word (final tiebreaker)

    Note: unlock_potential counts only cards that would be FULLY unlocked (score > 0)
    by learning this single kanji, not cards that still have other missing kanji.

    Args:
        cards: List of all CardInfo objects with scores computed
        new_card_ids: Set of card IDs that are in 'new' state
    """
    # Filter only new cards
    new_cards = [c for c in cards if c.card_id in new_card_ids]

    # Sort new cards with multi-level priority
    # Position 1 = highest priority (best to learn first)
    sorted_new_cards = sorted(new_cards, key=lambda c: (
        -c.score,                              # 1. Higher score first (more familiar)
        -c.unlock_potential,                   # 2. More cards fully unlocked (only matters when score=0)
        -c.unlock_median_score_increase,       # 3. Higher value unlocks (only matters when score=0)
        c.missing_kanji_count,                 # 4. Fewer missing kanji (only matters when score=0)
        count_kanji_in_text(c.furigana_text),  # 5. Fewer kanji (simpler) - applies to all cards
        count_kana_in_text(c.furigana_text),   # 6. Fewer kana (shorter) - applies to all cards
        c.score_without_missing                # 7. Lower score needs more help (only matters when score=0)
    ))

    # Assign positions only to new cards
    for position, card in enumerate(sorted_new_cards, start=1):
        card.position = position
