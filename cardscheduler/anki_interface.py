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

import math
import re

try:
    from aqt import mw
    from aqt.utils import showInfo
except ImportError:
    # Fallback for non-Anki environments (testing)
    mw = None
    def showInfo(msg):
        print(msg)

from .scheduler import (
    CardInfo,
    assign_positions_to_new_cards,
    build_card_to_pairs,
    compute_scores,
)
from .related import compute_related_words
from .html_formatter import HighlightCache
from .sentence_morphology import MecabTokenAnalyzer
from .sentence_scheduler import (
    SentenceCardInfo,
    assign_sentence_positions_and_priority,
    build_kanji_reading_interval_map,
    build_vocabulary_word_index,
    compute_sentence_scores,
)
from .word_parser import convert_two_fields_to_furigana, extract_kana_readings
from .config import (
    DECK_NAME,
    FIELD_NAME_POSITION,
    FIELD_NAME_SCORE,
    FIELD_NAME_UNLOCK_POTENTIAL,
    FIELD_NAME_UNLOCK_MEDIAN_SCORE_INCREASE,
    FIELD_NAME_SCORE_WITHOUT_MISSING,
    FIELD_NAME_MISSING_KANJI_COUNT,
    FIELD_NAME_RELATED_KNOWN,
    FIELD_NAME_RELATED_UNKNOWN,
    FIELD_NAME_KANJI_MEANINGS,
    FIELD_NAME_CARDS_WITH_KANJI,
    FIELD_NAME_CARDS_WITH_KANJI_KNOWN,
    FIELD_NAME_CARDS_WITH_KANJI_UNKNOWN,
    SIMULATE_ZERO_STABILITY,
    INPUT_MODE,
    INPUT_MODE_SINGLE_FIELD,
    INPUT_MODE_TWO_FIELDS,
    INPUT_FIELD_SINGLE,
    INPUT_FIELD_KANJI,
    INPUT_FIELD_READING,
    NO_KANJI_FREQUENCY_FIELD,
    SENTENCE_DECK_NAMES,
    SENTENCE_NOTE_TYPE,
    SENTENCE_FIELD,
    FIELD_NAME_SENTENCE_STRICT_SCORE,
    FIELD_NAME_SENTENCE_PREDICTED_SCORE,
    FIELD_NAME_SENTENCE_MISSING_WORDS,
    FIELD_NAME_SENTENCE_INFERRED_WORDS,
    FIELD_NAME_SENTENCE_KANJI_WORD_COUNT,
    FIELD_NAME_SENTENCE_PRIORITY_SCORE,
)
from .html_formatter import format_card_html


def format_score_for_note(score):
    """Format score for Anki note display with 3 decimals for non-zero values."""
    if score == 0:
        return "0.000"

    # Keep tiny non-zero values visible (e.g., 0.0001 -> 0.001)
    rounded_up = math.ceil(score * 1000) / 1000
    if rounded_up == 0:
        rounded_up = 0.001
    return f"{rounded_up:.3f}"


def get_field_value(note, field_name):
    """Get field value from note by field name."""
    note_type = note.note_type()
    if not note_type:
        return ""
    for i, fld in enumerate(note_type['flds']):
        if fld['name'] == field_name:
            return note.fields[i]
    return ""


def parse_frequency_value(value):
    """Parse frequency/rank field value into a float."""
    if value is None:
        return None

    cleaned = str(value).strip().replace(",", "")
    if not cleaned:
        return None

    try:
        return float(cleaned)
    except ValueError:
        return None


def _plain_text(value):
    """Remove simple HTML markup from Anki field text."""
    text = re.sub(r"<br\s*/?>", " ", value or "", flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def _surface_from_furigana(text):
    return re.sub(r"\[[^\]]*\]", "", text or "").replace(" ", "").strip()


def _reading_options_from_furigana(text):
    readings = re.findall(r"\[([^\]]+)\]", text or "")
    options = []
    for reading in readings:
        options.extend(extract_kana_readings(reading))
    return tuple(options)


def save_notes(collection, notes):
    """Write changed notes, in a single transaction when supported.

    Each separate update_note call commits its own transaction, which
    dominates runtime when thousands of notes change.
    """
    if not notes:
        return
    update_notes = getattr(collection, "update_notes", None)
    if update_notes is None:
        for note in notes:
            collection.update_note(note)
    else:
        update_notes(notes)


def save_field_changes(collection, computed_notes, field_names):
    """Copy field_names from computed notes onto freshly loaded notes and save.

    Use when the notes were loaded a while ago: reloading keeps any edits made
    to other fields in the meantime.
    """
    changed_notes = []
    for computed in computed_notes:
        current = collection.get_note(computed.id)
        original_fields = list(current.fields)
        for field_name in field_names:
            if field_name in current and field_name in computed:
                current[field_name] = computed[field_name]
        if current.fields != original_fields:
            changed_notes.append(current)
    save_notes(collection, changed_notes)
    return len(changed_notes)


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
               frequency_field_name=NO_KANJI_FREQUENCY_FIELD,
               simulate_zero_stability=SIMULATE_ZERO_STABILITY,
               notes_by_card_id=None):
    """
    Load cards from collection and extract furigana text.

    Args:
        collection: Anki collection
        input_mode: Either INPUT_MODE_SINGLE_FIELD or INPUT_MODE_TWO_FIELDS
        single_field_name: Field name for single-field mode
        kanji_field_name: Field name for kanji in two-field mode
        reading_field_name: Field name for reading in two-field mode
        frequency_field_name: Field name containing frequency/rank for no-kanji ordering
        simulate_zero_stability: If True, treat all cards as having zero stability
        notes_by_card_id: Optional dict filled with each card's loaded note, so
            later field updates can skip reloading it

    Returns:
        List of CardInfo objects
    """
    # Extract card information
    all_cids = collection.find_cards(f'"deck:{DECK_NAME}"')
    cards = []
    frequency_field_found = False
    for cid in all_cids:
        card = collection.get_card(cid)
        note = card.note()
        if notes_by_card_id is not None:
            notes_by_card_id[card.id] = note
        note_type = note.note_type()
        note_field_names = {fld['name'] for fld in note_type['flds']}

        if frequency_field_name and frequency_field_name in note_field_names:
            frequency_field_found = True

        # Get furigana text based on input mode
        word_surface = ""
        word_readings = ()
        if input_mode == INPUT_MODE_SINGLE_FIELD:
            furigana_text = get_field_value(note, single_field_name)
            word_surface = _surface_from_furigana(furigana_text)
            word_readings = _reading_options_from_furigana(furigana_text)
        elif input_mode == INPUT_MODE_TWO_FIELDS:
            kanji_text = get_field_value(note, kanji_field_name)
            reading_text = get_field_value(note, reading_field_name)
            furigana_text = convert_two_fields_to_furigana(kanji_text, reading_text)
            word_surface = _plain_text(kanji_text)
            word_readings = tuple(extract_kana_readings(_plain_text(reading_text)))
        else:
            furigana_text = ""

        stability = get_card_stability(card, simulate_zero=simulate_zero_stability)

        frequency = None
        if frequency_field_name and frequency_field_name in note_field_names:
            frequency = parse_frequency_value(get_field_value(note, frequency_field_name))

        cards.append(
            CardInfo(
                card.id,
                furigana_text,
                stability,
                frequency=frequency,
                word_surface=word_surface,
                word_readings=word_readings,
            )
        )

    if frequency_field_name and cards and not frequency_field_found:
        raise ValueError(
            f"Configured frequency field '{frequency_field_name}' was not found in deck '{DECK_NAME}'."
        )

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
    all_cids = collection.find_cards(f'"deck:{DECK_NAME}"')
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


def ensure_note_type_fields(collection, note_type_name, field_names):
    """Add missing fields to an existing note type and return all available fields."""
    notetype = collection.models.by_name(note_type_name)
    if notetype is None:
        raise ValueError(f"Note type '{note_type_name}' was not found.")

    existing_fields = {field["name"] for field in notetype["flds"]}
    updated = False
    for field_name in field_names:
        if field_name in existing_fields:
            continue
        collection.models.add_field(notetype, collection.models.new_field(field_name))
        existing_fields.add(field_name)
        updated = True

    if updated:
        collection.models.update_dict(notetype)
        refreshed = collection.models.by_name(note_type_name)
        if refreshed is not None:
            notetype = refreshed
            existing_fields = {field["name"] for field in notetype["flds"]}
        if mw is not None and hasattr(mw, "reset"):
            mw.reset()

    return existing_fields


def load_sentence_cards(collection,
                        sentence_deck_names=SENTENCE_DECK_NAMES,
                        sentence_note_type=SENTENCE_NOTE_TYPE,
                        sentence_field=SENTENCE_FIELD,
                        analyzer=None,
                        sentence_limit=None):
    """Load unique sentence notes from configured sentence/audio decks."""
    card_ids = []
    for deck_name in sentence_deck_names:
        query = f'"deck:{deck_name}" "note:{sentence_note_type}"'
        card_ids.extend(collection.find_cards(query))

    sentence_cards_by_note = {}
    for card_id in card_ids:
        card = collection.get_card(card_id)
        note = card.note()
        note_id = note.id

        sentence_card = sentence_cards_by_note.get(note_id)
        if sentence_card is None:
            if sentence_limit is not None and len(sentence_cards_by_note) >= sentence_limit:
                continue
            sentence_text = _plain_text(get_field_value(note, sentence_field))
            sentence_card = SentenceCardInfo(
                note_id=note_id,
                card_ids=[],
                sentence_text=sentence_text,
            )
            sentence_cards_by_note[note_id] = sentence_card

        if card_id not in sentence_card.card_ids:
            sentence_card.card_ids.append(card_id)

    sentence_cards = list(sentence_cards_by_note.values())
    if analyzer:
        tokens_by_text = analyzer.extract_tokens_many(
            [sentence_card.sentence_text for sentence_card in sentence_cards]
        )
        for sentence_card in sentence_cards:
            sentence_card.tokens = tokens_by_text.get(sentence_card.sentence_text, [])

    return sentence_cards


def sentence_new_card_ids(collection,
                          sentence_deck_names=SENTENCE_DECK_NAMES,
                          sentence_note_type=SENTENCE_NOTE_TYPE):
    new_card_ids = set()
    for deck_name in sentence_deck_names:
        query = f'"deck:{deck_name}" "note:{sentence_note_type}" is:new'
        new_card_ids.update(collection.find_cards(query))
    return new_card_ids


def update_sentence_fields(sentence_cards, collection, dry_run=False, available_fields=None):
    if available_fields is None:
        available_fields = set()

    update_count = 0
    for sentence_card in sentence_cards:
        if dry_run:
            update_count += 1
        elif update_sentence_note_fields(
            sentence_card,
            collection,
            available_fields=available_fields,
        ):
            update_count += 1
    return update_count


def update_sentence_note_fields(sentence_card, collection, available_fields=None):
    if available_fields is None:
        available_fields = set()
    if not sentence_card.card_ids:
        return False

    note = collection.get_card(sentence_card.card_ids[0]).note()
    note_type = note.note_type()
    field_indices = {
        field["name"]: index
        for index, field in enumerate(note_type["flds"])
    }

    field_values = {
        FIELD_NAME_POSITION: str(sentence_card.position) if sentence_card.position else "",
        FIELD_NAME_SENTENCE_STRICT_SCORE: format_score_for_note(sentence_card.strict_score),
        FIELD_NAME_SENTENCE_PREDICTED_SCORE: format_score_for_note(sentence_card.predicted_score),
        FIELD_NAME_SENTENCE_MISSING_WORDS: str(sentence_card.missing_words),
        FIELD_NAME_SENTENCE_INFERRED_WORDS: str(sentence_card.inferred_words),
        FIELD_NAME_SENTENCE_KANJI_WORD_COUNT: str(sentence_card.kanji_word_count),
        FIELD_NAME_SENTENCE_PRIORITY_SCORE: format_score_for_note(sentence_card.priority_score),
    }

    updated = False
    for field_name, value in field_values.items():
        if field_name in available_fields and field_name in field_indices:
            note.fields[field_indices[field_name]] = value
            updated = True

    if updated:
        collection.update_note(note)
    return updated


def reposition_new_sentence_cards(collection, sentence_cards, new_card_ids):
    sorted_new_card_ids = []
    for sentence_card in sorted(
        (card for card in sentence_cards if card.position > 0),
        key=lambda card: card.position,
    ):
        sorted_new_card_ids.extend(
            card_id for card_id in sentence_card.card_ids if card_id in new_card_ids
        )

    if not sorted_new_card_ids:
        return 0

    collection.sched.reposition_new_cards(
        card_ids=sorted_new_card_ids,
        starting_from=1,
        step_size=1,
        randomize=False,
        shift_existing=True,
    )
    return len(sorted_new_card_ids)


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
            print(f"Pos: {card.position:5d} | Score: {card.score:8.1f} | ID: {card.furigana_text:24s} | "
                  f"Pctl: {card.percentile_rank:5.1f}%")
        else:
            print(f"Pos: {card.position:5d} | Score: {card.score:8.1f} | ID: {card.furigana_text:24s} | "
                  f"Pctl: {card.percentile_rank:5.1f}% | Unlock: {card.unlock_potential:3d} | "
                  f"UnlockMedian: {card.unlock_median_score_increase:6.1f} | "
                  f"ScoreNoMissing: {card.score_without_missing:6.1f} | Missing: {card.missing_kanji_count}")


def update_cards_score(cards_score, collection, kanji_meanings, kanji_readings,
                       position_field=FIELD_NAME_POSITION,
                       score_field=FIELD_NAME_SCORE,
                       unlock_potential_field=FIELD_NAME_UNLOCK_POTENTIAL,
                       new_card_ids=None, dry_run=False, available_fields=None,
                       update_related_fields=True,
                       update_kanji_meanings_field=True,
                       notes_by_card_id=None,
                       highlight_cache=None,
                       update_score_fields=True,
                       pending_notes=None):
    """
    Update card fields with position, score, and unlock potential.

    Changed notes are saved together once all cards have been processed,
    unless pending_notes is given, in which case the caller saves them.

    Args:
        cards_score: List of CardInfo objects
        collection: Anki collection
        kanji_meanings: Dict mapping kanji to meanings
        kanji_readings: Dict mapping kanji to readings
        position_field: Name of position field
        score_field: Name of score field
        unlock_potential_field: Name of unlock potential field
        new_card_ids: Set of card IDs that are new (only these get position updated)
        dry_run: If True, don't actually update
        available_fields: Set of field names that are available (to skip missing fields)
        update_related_fields: If True, update related-word fields
        update_kanji_meanings_field: If True, update kanji meanings field
        notes_by_card_id: Optional notes already loaded by load_cards
        highlight_cache: Optional HighlightCache shared across cards
        update_score_fields: If True, update score and position fields
        pending_notes: If given, changed notes are appended here instead of saved
    """
    if available_fields is None:
        available_fields = set()
    if notes_by_card_id is None:
        notes_by_card_id = {}
    if highlight_cache is None:
        highlight_cache = HighlightCache()
    save_changes = pending_notes is None
    if save_changes:
        pending_notes = []

    update_count = 0
    for card in cards_score:
        is_new = new_card_ids and card.card_id in new_card_ids
        if dry_run:
            update_count += 1
        elif update_card_fields(card, collection, kanji_meanings, kanji_readings,
                               position_field=position_field,
                               score_field=score_field,
                               unlock_potential_field=unlock_potential_field,
                               update_position=is_new,
                               available_fields=available_fields,
                               update_score_fields=update_score_fields,
                               update_related_fields=update_related_fields,
                               update_kanji_meanings_field=update_kanji_meanings_field,
                               note=notes_by_card_id.get(card.card_id),
                               highlight_cache=highlight_cache,
                               pending_notes=pending_notes):
            update_count += 1
    if save_changes:
        save_notes(collection, pending_notes)
    return update_count


def update_card_fields(card_info, collection,
                       kanji_meanings,
                       kanji_readings,
                       position_field=FIELD_NAME_POSITION,
                       score_field=FIELD_NAME_SCORE,
                       unlock_potential_field=FIELD_NAME_UNLOCK_POTENTIAL,
                       unlock_median_score_increase_field=FIELD_NAME_UNLOCK_MEDIAN_SCORE_INCREASE,
                       score_without_missing_field=FIELD_NAME_SCORE_WITHOUT_MISSING,
                       missing_kanji_count_field=FIELD_NAME_MISSING_KANJI_COUNT,
                       related_known_field=FIELD_NAME_RELATED_KNOWN,
                       related_unknown_field=FIELD_NAME_RELATED_UNKNOWN,
                       cards_with_kanji_field=FIELD_NAME_CARDS_WITH_KANJI,
                       cards_with_kanji_known_field=FIELD_NAME_CARDS_WITH_KANJI_KNOWN,
                       cards_with_kanji_unknown_field=FIELD_NAME_CARDS_WITH_KANJI_UNKNOWN,
                       update_position=True,
                       available_fields=None,
                       update_score_fields=True,
                       update_related_fields=True,
                       update_kanji_meanings_field=True,
                       note=None,
                       highlight_cache=None,
                       pending_notes=None):
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
        update_score_fields: If True, update score and position fields
        update_related_fields: If True, update related-word fields
        update_kanji_meanings_field: If True, update kanji meanings field
        note: The card's note, if already loaded
        highlight_cache: Optional HighlightCache shared across cards
        pending_notes: If given, changed notes are appended here for the caller
            to save with save_notes instead of being saved immediately

    Returns:
        True if any available field was set, even when its value was unchanged
    """
    if available_fields is None:
        available_fields = set()

    if note is None:
        note = collection.get_card(card_info.card_id).note()
    note_type = note.note_type()
    original_fields = list(note.fields)

    # Build a map of field names to indices
    field_indices = {}
    for i, fld in enumerate(note_type['flds']):
        field_indices[fld['name']] = i

    related_known_html = related_unknown_html = meanings_html = ""
    if update_related_fields or update_kanji_meanings_field:
        related_known_html, related_unknown_html, meanings_html = format_card_html(
            card_info,
            kanji_meanings,
            kanji_readings,
            cache=highlight_cache,
        )

    # Track if any field was updated
    updated = False

    # Update position field (only for new cards) or clear it (for non-new cards)
    if update_score_fields and position_field in available_fields and position_field in field_indices:
        if update_position:
            note.fields[field_indices[position_field]] = str(card_info.position)
        else:
            # Clear position field for non-new cards
            note.fields[field_indices[position_field]] = ""
        updated = True

    # Update score field (for all cards)
    if update_score_fields and score_field in available_fields and score_field in field_indices:
        note.fields[field_indices[score_field]] = format_score_for_note(card_info.score)
        updated = True

    # Update unlock potential field (for all cards)
    if update_score_fields and unlock_potential_field in available_fields and unlock_potential_field in field_indices:
        note.fields[field_indices[unlock_potential_field]] = str(card_info.unlock_potential)
        updated = True

    # Update unlock median score increase field (for all cards)
    if update_score_fields and unlock_median_score_increase_field in available_fields and unlock_median_score_increase_field in field_indices:
        note.fields[field_indices[unlock_median_score_increase_field]] = format_score_for_note(
            card_info.unlock_median_score_increase
        )
        updated = True

    # Update score without missing field (for all cards)
    if update_score_fields and score_without_missing_field in available_fields and score_without_missing_field in field_indices:
        note.fields[field_indices[score_without_missing_field]] = format_score_for_note(
            card_info.score_without_missing
        )
        updated = True

    # Update missing kanji count field (for all cards)
    if update_score_fields and missing_kanji_count_field in available_fields and missing_kanji_count_field in field_indices:
        note.fields[field_indices[missing_kanji_count_field]] = str(card_info.missing_kanji_count)
        updated = True

    # Update cards with kanji fields (visual familiarity metrics)
    if update_score_fields and cards_with_kanji_field in available_fields and cards_with_kanji_field in field_indices:
        note.fields[field_indices[cards_with_kanji_field]] = str(card_info.cards_with_kanji)
        updated = True
    if update_score_fields and cards_with_kanji_known_field in available_fields and cards_with_kanji_known_field in field_indices:
        note.fields[field_indices[cards_with_kanji_known_field]] = str(card_info.cards_with_kanji_known)
        updated = True
    if update_score_fields and cards_with_kanji_unknown_field in available_fields and cards_with_kanji_unknown_field in field_indices:
        note.fields[field_indices[cards_with_kanji_unknown_field]] = str(card_info.cards_with_kanji_unknown)
        updated = True

    # Update related known words field (for all cards)
    if update_related_fields and related_known_field in available_fields and related_known_field in field_indices:
        note.fields[field_indices[related_known_field]] = related_known_html
        updated = True

    # Update related unknown words field (for all cards)
    if update_related_fields and related_unknown_field in available_fields and related_unknown_field in field_indices:
        note.fields[field_indices[related_unknown_field]] = related_unknown_html
        updated = True

    # Update kanji meanings field (for all cards)
    kanji_meanings_field = FIELD_NAME_KANJI_MEANINGS
    if update_kanji_meanings_field and kanji_meanings_field in available_fields and kanji_meanings_field in field_indices:
        note.fields[field_indices[kanji_meanings_field]] = meanings_html
        updated = True

    if updated and note.fields != original_fields:
        if pending_notes is None:
            collection.update_note(note)
        else:
            pending_notes.append(note)
    return updated


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


def process_related_words(collection=None, dry_run=False, show_summary=True):
    """
    Process cards to compute and update related-word display fields.

    Args:
        collection: Anki collection (defaults to mw.col)
        dry_run: If True, don't actually update cards
        show_summary: If True, show the completion dialog
    """
    if not collection:
        collection = mw.col

    notes_by_card_id = {}
    cards = load_cards(collection, notes_by_card_id=notes_by_card_id)
    from .dictionary import load_kanji_dictionnary_readings, load_kanji_meanings
    kanji_readings = load_kanji_dictionnary_readings()
    kanji_meanings = load_kanji_meanings()
    card_to_pairs = build_card_to_pairs(cards, kanji_readings)
    compute_related_words(cards, card_to_pairs)

    available_fields = detect_available_fields(collection, [
        FIELD_NAME_RELATED_KNOWN,
        FIELD_NAME_RELATED_UNKNOWN,
        FIELD_NAME_KANJI_MEANINGS,
    ])

    highlight_cache = HighlightCache()
    pending_notes = []
    update_count = 0
    for card in cards:
        if dry_run:
            update_count += 1
        elif update_card_fields(
            card,
            collection,
            kanji_meanings,
            kanji_readings,
            available_fields=available_fields,
            update_score_fields=False,
            update_related_fields=True,
            update_kanji_meanings_field=True,
            note=notes_by_card_id.get(card.card_id),
            highlight_cache=highlight_cache,
            pending_notes=pending_notes,
        ):
            update_count += 1
    save_notes(collection, pending_notes)

    print("=" * 60)
    print(f"Total cards processed for related words: {len(cards)}")
    print(f"Related fields updated for {update_count} cards")
    print(f"  - {FIELD_NAME_RELATED_KNOWN}: Related known words")
    print(f"  - {FIELD_NAME_RELATED_UNKNOWN}: Related unknown words")
    print(f"  - {FIELD_NAME_KANJI_MEANINGS}: Kanji meanings")

    message = f"Updated related-word fields for {update_count} cards:\n"
    message += f"  - {FIELD_NAME_RELATED_KNOWN}\n"
    message += f"  - {FIELD_NAME_RELATED_UNKNOWN}\n"
    message += f"  - {FIELD_NAME_KANJI_MEANINGS}"
    if show_summary:
        showInfo(message)
    return update_count


def process_sentence_scores(collection=None, dry_run=False, reposition=False,
                            vocab_cards=None, kanji_readings=None):
    """
    Compute sentence strict/predicted scores and optionally reposition new cards.

    Args:
        vocab_cards: Vocabulary cards with scores already computed, to reuse
        kanji_readings: Kanji dictionary readings, to reuse
    """
    if not collection:
        collection = mw.col

    analyzer = MecabTokenAnalyzer()
    if not analyzer.available:
        message = "MeCab is not available; sentence scores were not updated."
        print(message)
        showInfo(message)
        return 0

    from .dictionary import load_kanji_dictionnary_readings
    if kanji_readings is None:
        kanji_readings = load_kanji_dictionnary_readings()
    if vocab_cards is None:
        vocab_cards = load_cards(collection)
        compute_scores(vocab_cards, kanji_readings)

    pair_intervals = build_kanji_reading_interval_map(vocab_cards, kanji_readings)
    vocabulary_index = build_vocabulary_word_index(vocab_cards, analyzer)

    sentence_cards = load_sentence_cards(collection, analyzer=analyzer)
    compute_sentence_scores(
        sentence_cards,
        vocabulary_index,
        kanji_readings,
        pair_intervals,
    )

    new_cids = sentence_new_card_ids(collection)
    assign_sentence_positions_and_priority(sentence_cards, new_cids)

    sentence_field_names = [
        FIELD_NAME_POSITION,
        FIELD_NAME_SENTENCE_STRICT_SCORE,
        FIELD_NAME_SENTENCE_PREDICTED_SCORE,
        FIELD_NAME_SENTENCE_MISSING_WORDS,
        FIELD_NAME_SENTENCE_INFERRED_WORDS,
        FIELD_NAME_SENTENCE_KANJI_WORD_COUNT,
        FIELD_NAME_SENTENCE_PRIORITY_SCORE,
    ]
    if dry_run:
        available_fields = set(sentence_field_names)
    else:
        available_fields = ensure_note_type_fields(
            collection,
            SENTENCE_NOTE_TYPE,
            sentence_field_names,
        )

    update_count = update_sentence_fields(
        sentence_cards,
        collection,
        dry_run=dry_run,
        available_fields=available_fields,
    )

    reposition_count = 0
    if reposition and not dry_run:
        reposition_count = reposition_new_sentence_cards(
            collection,
            sentence_cards,
            new_cids,
        )

    print("=" * 60)
    print(f"Sentence cards processed: {len(sentence_cards)}")
    print(f"  - New sentence cards: {len(new_cids)}")
    print(f"Sentence fields updated for {update_count} notes")
    print(f"  - {FIELD_NAME_SENTENCE_STRICT_SCORE}")
    print(f"  - {FIELD_NAME_SENTENCE_PREDICTED_SCORE}")
    print(f"  - {FIELD_NAME_SENTENCE_MISSING_WORDS}")
    print(f"  - {FIELD_NAME_SENTENCE_INFERRED_WORDS}")
    print(f"  - {FIELD_NAME_SENTENCE_KANJI_WORD_COUNT}")
    print(f"  - {FIELD_NAME_SENTENCE_PRIORITY_SCORE}")
    print(f"  - {FIELD_NAME_POSITION} (all sentence notes)")
    if reposition_count:
        print(f"Repositioned {reposition_count} new sentence cards")

    message = f"Updated sentence fields for {update_count} notes:\n"
    message += f"  - {FIELD_NAME_SENTENCE_STRICT_SCORE}\n"
    message += f"  - {FIELD_NAME_SENTENCE_PREDICTED_SCORE}\n"
    message += f"  - {FIELD_NAME_SENTENCE_MISSING_WORDS}\n"
    message += f"  - {FIELD_NAME_SENTENCE_INFERRED_WORDS}\n"
    message += f"  - {FIELD_NAME_SENTENCE_KANJI_WORD_COUNT}\n"
    message += f"  - {FIELD_NAME_SENTENCE_PRIORITY_SCORE}\n"
    message += f"  - {FIELD_NAME_POSITION} (all sentence notes)"
    if reposition_count:
        message += f"\n\nRepositioned {reposition_count} new sentence cards"
    showInfo(message)
    return update_count


def process_all_features(collection=None, dry_run=False):
    """
    Run the full CardScheduler workflow.

    Computes score fields, computes related-word fields, repositions new cards,
    and generates Reading -> Kanji cards.
    """
    if not collection:
        collection = mw.col

    # Later steps reuse the vocabulary cards, scores and dictionary computed
    # here instead of loading and scoring the deck again.
    from .dictionary import load_kanji_dictionnary_readings
    kanji_readings = load_kanji_dictionnary_readings()
    _, refresh = _process_vocabulary(
        collection=collection,
        dry_run=dry_run,
        reposition=True,
        include_related_words=True,
        kanji_readings=kanji_readings,
    )
    process_sentence_scores(
        collection=collection,
        dry_run=dry_run,
        reposition=True,
        vocab_cards=refresh.cards,
        kanji_readings=kanji_readings,
    )

    from .reading_to_kanji_cards import process_reading_to_kanji_cards
    return process_reading_to_kanji_cards(
        collection=collection,
        dry_run=dry_run,
        cards=refresh.cards,
        kanji_readings=kanji_readings,
    )


SCORE_FIELD_NAMES = [
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
RELATED_FIELD_NAMES = [
    FIELD_NAME_RELATED_KNOWN,
    FIELD_NAME_RELATED_UNKNOWN,
    FIELD_NAME_KANJI_MEANINGS,
]


class VocabularyRefresh:
    """State carried from loading the deck, through computing, to saving fields.

    Only load_vocabulary_refresh and save_vocabulary_refresh use the
    collection, so compute_vocabulary_refresh can run off Anki's collection
    thread without blocking other collection operations.
    """

    def __init__(self, cards, notes_by_card_id, new_card_ids, available_fields,
                 update_score_fields, include_related_words):
        self.cards = cards
        self.notes_by_card_id = notes_by_card_id
        self.new_card_ids = new_card_ids
        self.available_fields = available_fields
        self.update_score_fields = update_score_fields
        self.include_related_words = include_related_words
        self.pending_notes = []
        self.update_count = 0


def load_vocabulary_refresh(collection, update_score_fields=True,
                            include_related_words=False):
    """Load the vocabulary cards, their notes, and the output fields to fill."""
    notes_by_card_id = {}
    cards = load_cards(collection, notes_by_card_id=notes_by_card_id)

    # Get new card IDs for position assignment
    # In simulation mode, treat ALL cards as new
    if SIMULATE_ZERO_STABILITY:
        new_cids = set(c.card_id for c in cards)
    else:
        new_cids = set(collection.find_cards(f'"deck:{DECK_NAME}" is:new'))

    # Detect which output fields exist in the note types
    field_names = []
    if update_score_fields:
        field_names += SCORE_FIELD_NAMES
    if include_related_words:
        field_names += RELATED_FIELD_NAMES
    available_fields = detect_available_fields(collection, field_names)

    return VocabularyRefresh(
        cards,
        notes_by_card_id,
        new_cids,
        available_fields,
        update_score_fields,
        include_related_words,
    )


def compute_vocabulary_refresh(refresh, dry_run=False, kanji_readings=None):
    """Compute all fields in memory; changed notes end up in refresh.pending_notes."""
    from .dictionary import load_kanji_dictionnary_readings, load_kanji_meanings
    if kanji_readings is None:
        kanji_readings = load_kanji_dictionnary_readings()

    if refresh.update_score_fields:
        # Compute scores for ALL cards
        card_to_pairs = compute_scores(refresh.cards, kanji_readings)
        # Assign positions only to new cards (or all cards in simulation mode)
        assign_positions_to_new_cards(refresh.cards, refresh.new_card_ids)
    else:
        card_to_pairs = build_card_to_pairs(refresh.cards, kanji_readings)

    kanji_meanings = {}
    if refresh.include_related_words:
        kanji_meanings = load_kanji_meanings()
        compute_related_words(refresh.cards, card_to_pairs)

    # Update fields for ALL cards (score/unlock for all, position only for new)
    refresh.update_count = update_cards_score(
        refresh.cards,
        None,
        kanji_meanings=kanji_meanings,
        kanji_readings=kanji_readings,
        new_card_ids=refresh.new_card_ids,
        dry_run=dry_run,
        available_fields=refresh.available_fields,
        update_score_fields=refresh.update_score_fields,
        update_related_fields=refresh.include_related_words,
        update_kanji_meanings_field=refresh.include_related_words,
        notes_by_card_id=refresh.notes_by_card_id,
        pending_notes=refresh.pending_notes,
    )
    return refresh


def save_vocabulary_refresh(collection, refresh, reposition=False,
                            reload_notes=False):
    """Save computed fields and optionally reposition new cards.

    Args:
        reload_notes: If True, apply only the output fields onto freshly loaded
            notes, for when notes may have been edited since they were loaded

    Returns:
        Number of repositioned cards
    """
    if reload_notes:
        save_field_changes(collection, refresh.pending_notes, refresh.available_fields)
    else:
        save_notes(collection, refresh.pending_notes)
    refresh.pending_notes = []

    if reposition and refresh.update_score_fields:
        return reposition_new_cards(refresh.cards, collection)
    return 0


def process_collection(
    collection=None,
    dry_run=False,
    reposition=False,
    show_summary=True,
    include_related_words=False,
):
    """
    Process cards to compute scores, unlock potential, and positions.

    Args:
        collection: Anki collection (defaults to mw.col)
        dry_run: If True, don't actually update cards
        reposition: If True, also reposition new cards based on computed positions
        show_summary: If True, show the completion dialog
        include_related_words: If True, also update the related-word fields in
            the same pass (same result as a following process_related_words)
    """
    update_count, _ = _process_vocabulary(
        collection=collection,
        dry_run=dry_run,
        reposition=reposition,
        show_summary=show_summary,
        include_related_words=include_related_words,
    )
    return update_count


def _process_vocabulary(
    collection=None,
    dry_run=False,
    reposition=False,
    show_summary=True,
    include_related_words=False,
    kanji_readings=None,
):
    """process_collection, also returning the VocabularyRefresh for reuse."""
    if not collection:
        collection = mw.col

    # Display simulation mode status
    if SIMULATE_ZERO_STABILITY:
        print("\n" + "=" * 60)
        print("SIMULATION MODE: All cards treated as having ZERO stability")
        print("This shows the optimal learning order starting from scratch")
        print("=" * 60 + "\n")

    refresh = load_vocabulary_refresh(
        collection,
        include_related_words=include_related_words,
    )
    compute_vocabulary_refresh(refresh, dry_run=dry_run, kanji_readings=kanji_readings)
    cards = refresh.cards
    new_cids = refresh.new_card_ids
    update_count = refresh.update_count

    print("Cards sorted by learning order position:")
    print("=" * 60)

    # Show all cards in output
    print_scores(cards, new_card_ids=new_cids)

    reposition_count = 0
    if not dry_run:
        reposition_count = save_vocabulary_refresh(
            collection,
            refresh,
            reposition=reposition,
        )

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
    print(f"  - {FIELD_NAME_CARDS_WITH_KANJI}: Cards sharing kanji (all cards)")
    print(f"  - {FIELD_NAME_CARDS_WITH_KANJI_KNOWN}: Known cards sharing kanji (all cards)")
    print(f"  - {FIELD_NAME_CARDS_WITH_KANJI_UNKNOWN}: Unknown cards sharing kanji (all cards)")
    print(f"  - {FIELD_NAME_POSITION}: Learning order position (new cards only)")
    if include_related_words:
        print(f"  - {FIELD_NAME_RELATED_KNOWN}: Related known words")
        print(f"  - {FIELD_NAME_RELATED_UNKNOWN}: Related unknown words")
        print(f"  - {FIELD_NAME_KANJI_MEANINGS}: Kanji meanings")
    if reposition_count:
        print(f"\nRepositioned {reposition_count} new cards based on computed positions")

    if show_summary:
        try:
            message = f"Updated card fields for {update_count} cards:\n"
            message += f"  - {FIELD_NAME_SCORE} (all cards)\n"
            message += f"  - {FIELD_NAME_UNLOCK_POTENTIAL} (all cards)\n"
            message += f"  - {FIELD_NAME_UNLOCK_MEDIAN_SCORE_INCREASE} (all cards)\n"
            message += f"  - {FIELD_NAME_SCORE_WITHOUT_MISSING} (all cards)\n"
            message += f"  - {FIELD_NAME_MISSING_KANJI_COUNT} (all cards)\n"
            message += f"  - {FIELD_NAME_CARDS_WITH_KANJI} (all cards)\n"
            message += f"  - {FIELD_NAME_CARDS_WITH_KANJI_KNOWN} (all cards)\n"
            message += f"  - {FIELD_NAME_CARDS_WITH_KANJI_UNKNOWN} (all cards)\n"
            message += f"  - {FIELD_NAME_POSITION} ({len(new_cids)} new cards only)"
            if include_related_words:
                message += f"\n  - {FIELD_NAME_RELATED_KNOWN}"
                message += f"\n  - {FIELD_NAME_RELATED_UNKNOWN}"
                message += f"\n  - {FIELD_NAME_KANJI_MEANINGS}"
            if reposition and reposition_count > 0:
                message += f"\n\nRepositioned {reposition_count} new cards"
            showInfo(message)
        except Exception:
            print(f"Updated card fields for {update_count} cards")

    return update_count, refresh
