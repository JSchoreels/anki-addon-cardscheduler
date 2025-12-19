"""
Anki Interface module - All Anki-specific operations.

This module handles:
- Card and note field operations
- Card stability/interval retrieval
- Loading cards from collection
- Field detection and validation
- Updating card fields in Anki
- Card repositioning
- Main processing entry point
"""

try:
    from aqt import mw
    from aqt.utils import showInfo
except ImportError:
    # Fallback for non-Anki environments (testing)
    mw = None
    def showInfo(msg):
        print(msg)

from .scheduler import CardInfo, compute_scores, assign_positions_to_new_cards
from .word_parser import convert_two_fields_to_furigana
from .config import (
    FIELD_NAME_POSITION,
    FIELD_NAME_SCORE,
    FIELD_NAME_UNLOCK_POTENTIAL,
    FIELD_NAME_UNLOCK_MEDIAN_SCORE_INCREASE,
    FIELD_NAME_SCORE_WITHOUT_MISSING,
    FIELD_NAME_MISSING_KANJI_COUNT,
    FIELD_NAME_RELATED_KNOWN,
    FIELD_NAME_RELATED_UNKNOWN,
    SIMULATE_ZERO_STABILITY,
    INPUT_MODE,
    INPUT_MODE_SINGLE_FIELD,
    INPUT_MODE_TWO_FIELDS,
    INPUT_FIELD_SINGLE,
    INPUT_FIELD_KANJI,
    INPUT_FIELD_READING
)


def get_field_value(note, field_name):
    """Get field value from note by field name."""
    note_type = note.note_type()
    if not note_type:
        return ""
    for i, fld in enumerate(note_type['flds']):
        if fld['name'] == field_name:
            return note.fields[i]
    return ""


def get_card_stability(card, simulate_zero=False):
    """
    Get the stability value for a card.
    Falls back to interval if stability is not available (for older Anki versions or non-FSRS decks).

    Args:
        card: Anki card object
        simulate_zero: If True, return 0 (simulates starting from scratch)

    Returns:
        Stability value (0 if simulate_zero is True or card has no stability/interval)
    """
    if simulate_zero:
        return 0

    # Try to get stability from FSRS memory state (newer Anki with FSRS enabled)
    if card.memory_state and hasattr(card.memory_state, 'stability'):
        return card.memory_state.stability

    # Fall back to interval (works with SM-2 and older schedulers)
    # Interval is in days, which can be used as a proxy for stability
    if hasattr(card, 'ivl'):
        return max(0, card.ivl)  # ivl can be negative for learning cards, use 0 in that case

    return 0


def load_cards(collection,
               input_mode=INPUT_MODE,
               single_field_name=INPUT_FIELD_SINGLE,
               kanji_field_name=INPUT_FIELD_KANJI,
               reading_field_name=INPUT_FIELD_READING,
               simulate_zero_stability=SIMULATE_ZERO_STABILITY):
    """
    Load cards from collection and extract furigana text.

    Args:
        collection: Anki collection
        input_mode: Either INPUT_MODE_SINGLE_FIELD or INPUT_MODE_TWO_FIELDS
        single_field_name: Field name for single-field mode
        kanji_field_name: Field name for kanji in two-field mode
        reading_field_name: Field name for reading in two-field mode
        simulate_zero_stability: If True, treat all cards as having zero stability

    Returns:
        List of CardInfo objects
    """
    # Extract card information
    all_cids = collection.find_cards('"deck:Japan::1. Vocabulary"')
    cards = []
    for cid in all_cids:
        card = collection.get_card(cid)
        note = card.note()

        # Get furigana text based on input mode
        if input_mode == INPUT_MODE_SINGLE_FIELD:
            furigana_text = get_field_value(note, single_field_name)
        elif input_mode == INPUT_MODE_TWO_FIELDS:
            kanji_text = get_field_value(note, kanji_field_name)
            reading_text = get_field_value(note, reading_field_name)
            furigana_text = convert_two_fields_to_furigana(kanji_text, reading_text)
        else:
            furigana_text = ""

        stability = get_card_stability(card, simulate_zero=simulate_zero_stability)
        cards.append(CardInfo(card.id, furigana_text, stability))
    return cards


def detect_available_fields(collection, field_names):
    """
    Detect which fields are available in the note types used by cards in the deck.
    Print warnings for missing fields (only once per field).

    Args:
        collection: Anki collection
        field_names: List of field names to check

    Returns:
        Set of field names that exist in at least one note type
    """
    all_cids = collection.find_cards('"deck:Japan::1. Vocabulary"')
    note_types_checked = set()
    available_fields = set()
    missing_fields_by_note_type = {}  # Track which fields are missing for which note types

    # Check a sample of cards to find which fields exist
    for cid in all_cids[:100]:  # Check first 100 cards to get representative note types
        card = collection.get_card(cid)
        note = card.note()
        note_type = note.note_type()
        note_type_name = note_type['name']

        if note_type_name in note_types_checked:
            continue

        note_types_checked.add(note_type_name)

        # Check which fields exist in this note type
        field_names_in_note = {fld['name'] for fld in note_type['flds']}

        for field_name in field_names:
            if field_name in field_names_in_note:
                available_fields.add(field_name)
            else:
                if note_type_name not in missing_fields_by_note_type:
                    missing_fields_by_note_type[note_type_name] = []
                missing_fields_by_note_type[note_type_name].append(field_name)

    # Print warnings for missing fields (grouped by note type)
    if missing_fields_by_note_type:
        print("\nWarning: Some fields not found in note types:")
        for note_type_name, missing_fields in missing_fields_by_note_type.items():
            print(f"  Note type '{note_type_name}': {', '.join(missing_fields)}")
        print()

    return available_fields


def print_scores(cards, new_card_ids=None):
    """
    Print card scores. Only new cards have positions assigned.

    Args:
        cards: List of CardInfo objects
        new_card_ids: Set of card IDs that are new (have positions)
    """
    # Sort cards: new cards by position, non-new cards by score
    new_cards = [c for c in cards if new_card_ids and c.card_id in new_card_ids]
    non_new_cards = [c for c in cards if not new_card_ids or c.card_id not in new_card_ids]

    # Sort new cards by position
    sorted_new_cards = sorted(new_cards, key=lambda c: -c.position)

    # Sort non-new cards by score (descending)
    sorted_non_new_cards = sorted(non_new_cards, key=lambda c: -c.score)

    # Print non-new cards (no position)
    if sorted_non_new_cards:
        print("\nNon-new cards (no position assigned):")
        for card in sorted_non_new_cards[:20]:  # Limit to first 20 for brevity
            if card.score > 0:
                print(f"Pos: {'N/A':>5s} | Score: {card.score:8.1f} | ID: {card.furigana_text:24s} | Unknown: {card.unknown_kanji_readings} | Unlock: {card.unlock_potential:3d} | Stability: {card.stability:.1f}")
            else:
                print(f"Pos: {'N/A':>5s} | Score: {card.score:8.1f} | ID: {card.furigana_text:24s} | Unknown: {card.unknown_kanji_readings} | Unlock: {card.unlock_potential:3d}")


    # Print new cards
    for card in sorted_new_cards:
        if card.score > 0:
            print(f"Pos: {card.position:5d} | Score: {card.score:8.1f} | ID: {card.furigana_text:24s}")
        else:
            print(f"Pos: {card.position:5d} | Score: {card.score:8.1f} | ID: {card.furigana_text:24s} | "
                  f"Unknown: {card.unknown_kanji_readings} | Unlock: {card.unlock_potential:3d} | "
                  f"UnlockMedian: {card.unlock_median_score_increase:6.1f} | "
                  f"ScoreNoMissing: {card.score_without_missing:6.1f} | Missing: {card.missing_kanji_count}")


def update_cards_score(cards_score, collection,
                       position_field=FIELD_NAME_POSITION,
                       score_field=FIELD_NAME_SCORE,
                       unlock_potential_field=FIELD_NAME_UNLOCK_POTENTIAL,
                       new_card_ids=None, dry_run=False, available_fields=None):
    """
    Update card fields with position, score, and unlock potential.

    Args:
        cards_score: List of CardInfo objects
        collection: Anki collection
        position_field: Name of position field
        score_field: Name of score field
        unlock_potential_field: Name of unlock potential field
        new_card_ids: Set of card IDs that are new (only these get position updated)
        dry_run: If True, don't actually update
        available_fields: Set of field names that are available (to skip missing fields)
    """
    if available_fields is None:
        available_fields = set()  # Empty set means all fields will be skipped with warnings

    update_count = 0
    for card in cards_score:
        is_new = new_card_ids and card.card_id in new_card_ids
        if dry_run:
            update_count += 1
        elif update_card_fields(card, collection,
                               position_field=position_field,
                               score_field=score_field,
                               unlock_potential_field=unlock_potential_field,
                               update_position=is_new,
                               available_fields=available_fields):
            update_count += 1
    return update_count


def update_card_fields(card_info, collection,
                       position_field=FIELD_NAME_POSITION,
                       score_field=FIELD_NAME_SCORE,
                       unlock_potential_field=FIELD_NAME_UNLOCK_POTENTIAL,
                       unlock_median_score_increase_field=FIELD_NAME_UNLOCK_MEDIAN_SCORE_INCREASE,
                       score_without_missing_field=FIELD_NAME_SCORE_WITHOUT_MISSING,
                       missing_kanji_count_field=FIELD_NAME_MISSING_KANJI_COUNT,
                       related_known_field=FIELD_NAME_RELATED_KNOWN,
                       related_unknown_field=FIELD_NAME_RELATED_UNKNOWN,
                       update_position=True,
                       available_fields=None):
    """
    Update card note with all computed fields.

    Args:
        card_info: CardInfo object
        collection: Anki collection
        position_field: Name of position field
        score_field: Name of score field
        unlock_potential_field: Name of unlock potential field
        unlock_median_score_increase_field: Name of unlock median score increase field
        score_without_missing_field: Name of score without missing field
        missing_kanji_count_field: Name of missing kanji count field
        update_position: If True, update position field; if False, clear position field
        available_fields: Set of field names that are available (to skip missing fields)
    """
    if available_fields is None:
        available_fields = set()

    card = collection.get_card(card_info.card_id)
    note = card.note()
    note_type = note.note_type()

    # Build a map of field names to indices
    field_indices = {}
    for i, fld in enumerate(note_type['flds']):
        field_indices[fld['name']] = i

    # Track if any field was updated
    updated = False

    # Update position field (only for new cards) or clear it (for non-new cards)
    if position_field in available_fields and position_field in field_indices:
        if update_position:
            note.fields[field_indices[position_field]] = str(card_info.position)
        else:
            # Clear position field for non-new cards
            note.fields[field_indices[position_field]] = ""
        updated = True

    # Update score field (for all cards)
    if score_field in available_fields and score_field in field_indices:
        note.fields[field_indices[score_field]] = str(round(card_info.score, 1))
        updated = True

    # Update unlock potential field (for all cards)
    if unlock_potential_field in available_fields and unlock_potential_field in field_indices:
        note.fields[field_indices[unlock_potential_field]] = str(card_info.unlock_potential)
        updated = True

    # Update unlock median score increase field (for all cards)
    if unlock_median_score_increase_field in available_fields and unlock_median_score_increase_field in field_indices:
        note.fields[field_indices[unlock_median_score_increase_field]] = str(round(card_info.unlock_median_score_increase, 1))
        updated = True

    # Update score without missing field (for all cards)
    if score_without_missing_field in available_fields and score_without_missing_field in field_indices:
        note.fields[field_indices[score_without_missing_field]] = str(round(card_info.score_without_missing, 1))
        updated = True

    # Update missing kanji count field (for all cards)
    if missing_kanji_count_field in available_fields and missing_kanji_count_field in field_indices:
        note.fields[field_indices[missing_kanji_count_field]] = str(card_info.missing_kanji_count)
        updated = True

    # Update related known words field (for all cards)
    if related_known_field in available_fields and related_known_field in field_indices:
        note.fields[field_indices[related_known_field]] = card_info.related_words_known
        updated = True

    # Update related unknown words field (for all cards)
    if related_unknown_field in available_fields and related_unknown_field in field_indices:
        note.fields[field_indices[related_unknown_field]] = card_info.related_words_unknown
        updated = True

    if updated:
        collection.update_note(note)
        return True
    else:
        return False


def update_card_score(card_id, score, collection, score_field="MyPosition"):
    """Legacy function - kept for backwards compatibility."""
    card = collection.get_card(card_id)
    note = card.note()
    note_type = note.note_type()

    # Find the field index
    field_index = None
    for i, fld in enumerate(note_type['flds']):
        if fld['name'] == score_field:
            field_index = i
            break

    if field_index is not None:
        # Update the field with the score (rounded to 1 decimal place)
        note.fields[field_index] = str(round(score, 1))
        collection.update_note(note)
        return True
    else:
        print(f"Field '{score_field}' not found in note type: {note_type['name']}")
        return False


def reposition_new_cards(cards, collection):
    """
    Reposition new cards based on computed positions.

    Args:
        cards: List of CardInfo objects with positions assigned
        collection: Anki collection

    Returns:
        Number of cards repositioned
    """
    # Filter only cards with positions > 0
    cards_with_positions = [c for c in cards if c.position > 0]

    # Sort by position
    sorted_cards = sorted(cards_with_positions, key=lambda c: c.position)

    # Extract card IDs in order
    sorted_card_ids = [c.card_id for c in sorted_cards]

    if not sorted_card_ids:
        return 0

    # Modern Anki API (v2.1.50+)
    collection.sched.reposition_new_cards(
        card_ids=sorted_card_ids,
        starting_from=1,
        step_size=1,
        randomize=False,
        shift_existing=True
    )
    return len(sorted_card_ids)


def process_collection(collection=None, dry_run=False, reposition=False):
    """
    Process cards to compute scores, unlock potential, and positions.

    Args:
        collection: Anki collection (defaults to mw.col)
        dry_run: If True, don't actually update cards
        reposition: If True, also reposition new cards based on computed positions
    """
    if not collection:
        collection = mw.col
    else:
        collection = collection

    # Display simulation mode status
    if SIMULATE_ZERO_STABILITY:
        print("\n" + "=" * 60)
        print("SIMULATION MODE: All cards treated as having ZERO stability")
        print("This shows the optimal learning order starting from scratch")
        print("=" * 60 + "\n")

    cards = load_cards(collection)

    # Compute scores for ALL cards
    compute_scores(cards)

    # Get new card IDs for position assignment
    # In simulation mode, treat ALL cards as new
    if SIMULATE_ZERO_STABILITY:
        new_cids = set(c.card_id for c in cards)
    else:
        new_cids = set(collection.find_cards('"deck:Japan::1. Vocabulary" is:new'))

    # Assign positions only to new cards (or all cards in simulation mode)
    assign_positions_to_new_cards(cards, new_cids)

    print("Cards sorted by learning order position:")
    print("=" * 60)

    # Show all cards in output
    print_scores(cards, new_card_ids=new_cids)

    # Detect which fields exist in the note types
    available_fields = detect_available_fields(collection, [
        FIELD_NAME_POSITION,
        FIELD_NAME_SCORE,
        FIELD_NAME_UNLOCK_POTENTIAL,
        FIELD_NAME_UNLOCK_MEDIAN_SCORE_INCREASE,
        FIELD_NAME_SCORE_WITHOUT_MISSING,
        FIELD_NAME_MISSING_KANJI_COUNT,
        FIELD_NAME_RELATED_KNOWN,
        FIELD_NAME_RELATED_UNKNOWN
    ])

    # Update fields for ALL cards (score/unlock for all, position only for new)
    update_count = update_cards_score(cards, collection, new_card_ids=new_cids, dry_run=dry_run, available_fields=available_fields)

    print("=" * 60)
    print(f"Total cards processed: {len(cards)}")
    print(f"  - New cards: {len(new_cids)}")
    print(f"  - Non-new cards: {len(cards) - len(new_cids)}")
    print(f"Card fields updated for {update_count} cards")
    print(f"  - {FIELD_NAME_SCORE}: Familiarity score (all cards)")
    print(f"  - {FIELD_NAME_UNLOCK_POTENTIAL}: Unlock potential (all cards)")
    print(f"  - {FIELD_NAME_UNLOCK_MEDIAN_SCORE_INCREASE}: Unlock median score increase (all cards)")
    print(f"  - {FIELD_NAME_SCORE_WITHOUT_MISSING}: Score without missing kanji (all cards)")
    print(f"  - {FIELD_NAME_MISSING_KANJI_COUNT}: Missing kanji count (all cards)")
    print(f"  - {FIELD_NAME_POSITION}: Learning order position (new cards only)")

    # Reposition cards if requested (only new cards)
    reposition_count = 0
    if reposition and not dry_run:
        reposition_count = reposition_new_cards(cards, collection)
        print(f"\nRepositioned {reposition_count} new cards based on computed positions")

    try:
        message = f"Updated card fields for {update_count} cards:\n"
        message += f"  - {FIELD_NAME_SCORE} (all cards)\n"
        message += f"  - {FIELD_NAME_UNLOCK_POTENTIAL} (all cards)\n"
        message += f"  - {FIELD_NAME_UNLOCK_MEDIAN_SCORE_INCREASE} (all cards)\n"
        message += f"  - {FIELD_NAME_SCORE_WITHOUT_MISSING} (all cards)\n"
        message += f"  - {FIELD_NAME_MISSING_KANJI_COUNT} (all cards)\n"
        message += f"  - {FIELD_NAME_POSITION} ({len(new_cids)} new cards only)"
        if reposition and reposition_count > 0:
            message += f"\n\nRepositioned {reposition_count} new cards"
        showInfo(message)
    except Exception as e:
        print(f"Updated card fields for {update_count} cards")
