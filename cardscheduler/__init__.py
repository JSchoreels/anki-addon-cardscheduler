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


def compute_order():
    field_name = "Front"  # Replace with your field name
    kanji_to_cards = {}
    card_scores = {}


    # Step 1: Build kanji to cards mapping
    all_cids = mw.col.find_cards('"deck:Japan::1. Vocabulary::Yomitan"')
    new_cids = mw.col.find_cards('"deck:Japan::1. Vocabulary" is:new')

    for cid in all_cids:
        card = mw.col.get_card(cid)
        note = card.note()
        field_value = get_field_value(note, field_name)
        if not field_value:
            continue
        kanji_set = get_kanji_set(field_value)
        for kanji in kanji_set:
            kanji_to_cards.setdefault(kanji, set()).add(card)

    # Debug: Show global kanji averages
    print("Global kanji averages:")
    for kanji, cards in kanji_to_cards.items():
        total_weighted_ivl = 0
        total_weight = 0
        for card in cards:
            note = card.note()
            field_value = get_field_value(note, field_name)
            kanji_count = len(get_kanji_set(field_value))
            if kanji_count > 0:
                weight = 1.0 / kanji_count
                total_weighted_ivl += card.ivl * weight
                total_weight += weight

        if total_weight > 0:
            global_avg = total_weighted_ivl / total_weight
            print(f"Kanji '{kanji}': global_avg={global_avg:.2f}, total_weight={total_weight:.2f}")

    # Step 2: Compute score for each card
    for cid in all_cids:
        card = mw.col.get_card(cid)
        note = card.note()
        field_value = get_field_value(note, field_name)
        if not field_value:
            card_scores[card.id] = 0
            continue
        kanji_set = get_kanji_set(field_value)

        kanji_scores = []  # Store individual kanji scores (not weighted by kanji count)

        for kanji in kanji_set:
            if kanji in kanji_to_cards:
                kanji_total_weighted_ivl = 0
                kanji_total_weight = 0

                for other_card in kanji_to_cards[kanji]:
                    if other_card.id != card.id:
                        other_note = other_card.note()
                        other_field_value = get_field_value(other_note, field_name)
                        other_kanji_count = len(get_kanji_set(other_field_value))

                        if other_kanji_count > 0:
                            weight = 1.0 / other_kanji_count  # Weight only affects kanji calculation
                            kanji_total_weighted_ivl += other_card.ivl * weight
                            kanji_total_weight += weight

                if kanji_total_weight > 0:
                    kanji_weighted_avg = kanji_total_weighted_ivl / kanji_total_weight
                    kanji_scores.append(kanji_weighted_avg)  # Each kanji contributes equally
                    print(f"Kanji '{kanji}' in '{field_value}': avg={kanji_weighted_avg:.2f}, total_weight={kanji_total_weight:.2f}")

        # Simple average: each kanji contributes equally to the final score
        card_scores[card.id] = sum(kanji_scores) / len(kanji_scores) if kanji_scores else 0

    # Sort cards by score in ascending order (lowest scores first - least familiar)
    sorted_cards = sorted(card_scores.items(), key=lambda x: x[1], reverse=False)

    print("Cards sorted by familiarity score (least known first):")
    print("=" * 60)

    for card_id, score in sorted_cards:
        if card_id in new_cids:
            card = mw.col.get_card(card_id)
            note = card.note()
            front_field = get_field_value(note, field_name)
            print(f"Score: {score:8.1f} | Front: {front_field}")

    print("=" * 60)
    print(f"Total cards processed: {len([cid for cid, _ in sorted_cards if cid in new_cids])}")

# To run this, you must use Anki's Debug Console (Tools -> Debug Console)
# and then type `from cardscheduler import compute_order; compute_order()` and press Ctrl+Enter.