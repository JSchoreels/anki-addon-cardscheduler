from aqt import mw
from anki.notes import Note
from anki.cards import Card

def get_field_value(note, field_name):
    # Find the index of the field by its name
    note_type = note.note_type()
    if not note_type:
        return ""
    for i, fld in enumerate(note_type['flds']):
        if fld['name'] == field_name:
            return note.fields[i]
    return ""

def get_kanji_set(text):
    # Extract kanji from text (Unicode range for CJK Unified Ideographs)
    return set([char for char in text if '\u4e00' <= char <= '\u9fff'])


def get_kanji_reading_pairs(text):
    """Extract kanji-reading pairs, falling back to kanji-only for standalone kanji"""
    import re

    kanji_pairs = set()

    # Extract explicit kanji[reading] pairs
    pattern = r'([一-龯]+)\[([ぁ-ゖァ-ヺー]+)\]'
    matches = re.findall(pattern, text)

    processed_kanji = set()
    for kanji_word, reading in matches:
        # For compound words, you might want to handle differently
        if len(kanji_word) == 1:
            kanji_pairs.add(f"{kanji_word}[{reading}]")
            processed_kanji.add(kanji_word)
        else:
            # For compounds, still track individual kanji
            for kanji in kanji_word:
                if '\u4e00' <= kanji <= '\u9fff':
                    kanji_pairs.add(f"{kanji}[]")  # No specific reading for individual kanji
                    processed_kanji.add(kanji)

    # Handle standalone kanji without readings
    for char in text:
        if '\u4e00' <= char <= '\u9fff' and char not in processed_kanji:
            kanji_pairs.add(f"{char}[]")

    return kanji_pairs


def get_kanji_reading_pairs_simple(text):
    """Fallback: treat compound words as single units"""
    import re
    pattern = r'([一-龯]+)\[([ぁ-ゖァ-ヺー]+)\]'
    matches = re.findall(pattern, text)
    return set([f"{kanji}[{reading}]" for kanji, reading in matches])

def compute_order():
    field_name = "ID"  # Changed from "Front" to "ID"
    kanji_reading_to_cards = {}
    card_scores = {}

    # Step 1: Build kanji-reading pairs to cards mapping
    all_cids = mw.col.find_cards('"deck:Japan::1. Vocabulary"')
    new_cids = mw.col.find_cards('"deck:Japan::1. Vocabulary" is:new')

    for cid in all_cids:
        card = mw.col.get_card(cid)
        note = card.note()
        field_value = get_field_value(note, field_name)
        if not field_value:
            continue
        kanji_reading_pairs = get_kanji_reading_pairs(field_value)
        for pair in kanji_reading_pairs:
            kanji_reading_to_cards.setdefault(pair, set()).add(card)

    # Debug: Show global kanji-reading averages
    print("Global kanji-reading averages:")
    for pair, cards in kanji_reading_to_cards.items():
        total_weighted_ivl = 0
        total_weight = 0
        for card in cards:
            note = card.note()
            field_value = get_field_value(note, field_name)
            pair_count = len(get_kanji_reading_pairs(field_value))
            if pair_count > 0:
                weight = 1.0 / pair_count
                total_weighted_ivl += card.ivl * weight
                total_weight += weight

        if total_weight > 0:
            global_avg = total_weighted_ivl / total_weight
            print(f"Pair '{pair}': global_avg={global_avg:.2f}, total_weight={total_weight:.2f}")

    # Step 2: Compute score for each card
    for cid in all_cids:
        card = mw.col.get_card(cid)
        note = card.note()
        field_value = get_field_value(note, field_name)
        if not field_value:
            card_scores[card.id] = 0
            continue
        kanji_reading_pairs = get_kanji_reading_pairs(field_value)

        pair_scores = []

        for pair in kanji_reading_pairs:
            if pair in kanji_reading_to_cards:
                pair_total_weighted_ivl = 0
                pair_total_weight = 0

                for other_card in kanji_reading_to_cards[pair]:
                    if other_card.id != card.id:
                        other_note = other_card.note()
                        other_field_value = get_field_value(other_note, field_name)
                        other_pair_count = len(get_kanji_reading_pairs(other_field_value))

                        if other_pair_count > 0:
                            weight = 1.0 / other_pair_count
                            pair_total_weighted_ivl += other_card.ivl * weight
                            pair_total_weight += weight

                if pair_total_weight > 0:
                    pair_weighted_avg = pair_total_weighted_ivl / pair_total_weight
                    pair_scores.append(pair_weighted_avg)
                    print(f"Pair '{pair}' in '{field_value}': avg={pair_weighted_avg:.2f}, total_weight={pair_total_weight:.2f}")

        # Simple average: each kanji-reading pair contributes equally to the final score
        card_scores[card.id] = sum(pair_scores) / len(pair_scores) if pair_scores else 0

    # Sort cards by score in ascending order (lowest scores first - least familiar)
    sorted_cards = sorted(card_scores.items(), key=lambda x: x[1], reverse=False)

    print("Cards sorted by familiarity score (least known first):")
    print("=" * 60)

    # Update MyPosition field for all cards
    update_count = 0
    for card_id, score in sorted_cards:
        # Only process new cards
        if card_id in new_cids:
            card = mw.col.get_card(card_id)
            note = card.note()
            id_field = get_field_value(note, field_name)

            print(f"Score: {score:8.1f} | ID: {id_field}")

            if update_my_position_field(card, score):
                update_count += 1

    print("=" * 60)
    print(f"Total cards processed: {len([cid for cid, _ in sorted_cards if cid in new_cids])}")
    print(f"MyPosition field updated for {update_count} cards")

    # Show a message to the user
    from aqt.utils import showInfo
    showInfo(f"Updated MyPosition field for {update_count} cards")


def update_my_position_field(card, score):
    """Update the MyPosition field with the computed score"""
    note = card.note()
    note_type = note.note_type()

    # Find the MyPosition field index
    my_position_field_index = None
    for i, fld in enumerate(note_type['flds']):
        if fld['name'] == 'MyPosition':
            my_position_field_index = i
            break

    if my_position_field_index is not None:
        # Update the field with the score (rounded to 1 decimal place)
        note.fields[my_position_field_index] = str(round(score, 1))
        mw.col.update_note(note)  # Use the modern API instead of flush()
        return True
    else:
        print(f"MyPosition field not found in note type: {note_type['name']}")
        return False