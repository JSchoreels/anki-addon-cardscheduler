from aqt import mw
from anki.notes import Note
from anki.cards import Card
from aqt.utils import showInfo
import re
import xml.etree.ElementTree as ET


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

def extract_kanji_only(text):
    """Extract only kanji characters from text, filtering out kana."""
    return re.findall(r'[\u4e00-\u9fff]', text)

def get_kanji_reading_pairs(text, kanji_readings):
    """Extract kanji-reading pairs using Kanjidic, falling back to kanji-only."""
    kanji_pairs = set()
    pattern = r'([一-龯]+)\[([ぁ-ゖァ-ヺー]+)\]'
    matches = re.findall(pattern, text)

    processed_kanji = set()
    for kanji_word, reading in matches:
        if len(kanji_word) == 1:
            kanji_pairs.add(f"{kanji_word}[{reading}]")
            processed_kanji.add(kanji_word)
        else:
            # Extract only kanji characters from compound word
            kanji_chars = extract_kanji_only(kanji_word)

            if len(kanji_chars) > 1:
                # Attempt to split readings for compound words (kanji only)
                reading_parts = split_reading(kanji_chars, reading, kanji_readings)
                if reading_parts:
                    for kanji, reading_part in reading_parts:
                        kanji_pairs.add(f"{kanji}[{reading_part}]")
                        processed_kanji.add(kanji)
                else:
                    # If splitting fails, add individual kanji with empty readings
                    for kanji in kanji_chars:
                        kanji_pairs.add(f"{kanji}[]")
                        processed_kanji.add(kanji)
                    # Also keep the compound as a unit
                    kanji_pairs.add(f"{kanji_word}[{reading}]")
            else:
                # Single kanji after filtering
                if kanji_chars:
                    kanji_pairs.add(f"{kanji_chars[0]}[{reading}]")
                    processed_kanji.add(kanji_chars[0])

    # Handle standalone kanji without readings
    for char in text:
        if '\u4e00' <= char <= '\u9fff' and char not in processed_kanji:
            kanji_pairs.add(f"{char}[]")

    return kanji_pairs


def split_reading(kanji_chars, reading, kanji_readings):
    """Split compound reading into individual kanji readings using Kanjidic."""
    remaining_reading = reading
    pairs = []

    for kanji in kanji_chars:
        found_match = False

        # Try all possible readings for this kanji, starting with longest
        possible_readings = kanji_readings.get(kanji, [])
        # Sort by length (longest first) to prefer longer matches
        possible_readings = sorted(possible_readings, key=len, reverse=True)

        for reading_option in possible_readings:
            if remaining_reading.startswith(reading_option):
                pairs.append((kanji, reading_option))
                remaining_reading = remaining_reading[len(reading_option):]
                found_match = True
                break

        if not found_match:
            # If no match found for this kanji, the split fails
            return None

    # Only return pairs if the entire reading is consumed
    if not remaining_reading:
        return pairs
    else:
        return None

def katakana_to_hiragana(text):
    """Convert katakana to hiragana"""
    result = ""
    for char in text:
        if 'ァ' <= char <= 'ヶ':
            # Convert katakana to hiragana
            result += chr(ord(char) - ord('ァ') + ord('ぁ'))
        else:
            result += char
    return result


def load_kanji_readings(xml_file):
    """Load kanji readings from kanjidic2.xml into a dictionary."""
    kanji_readings = {}
    tree = ET.parse(xml_file)
    root = tree.getroot()

    for character in root.findall('character'):
        kanji = character.find('literal').text
        readings = []
        for reading_group in character.findall('reading_meaning/rmgroup'):
            for reading in reading_group.findall("reading[@r_type='ja_kun']"):
                reading.text = reading.text.split('.')[0]
                readings.append(reading.text)
            for reading in reading_group.findall("reading[@r_type='ja_on']"):
                # Convert katakana on'yomi to hiragana
                readings.append(katakana_to_hiragana(reading.text))
        kanji_readings[kanji] = readings
    return kanji_readings

def get_kanji_reading_pairs_simple(text):
    """Fallback: treat compound words as single units"""
    pattern = r'([一-龯]+)\[([ぁ-ゖァ-ヺー]+)\]'
    matches = re.findall(pattern, text)
    return set([f"{kanji}[{reading}]" for kanji, reading in matches])

# Load Kanji readings at the beginning of compute_order
def compute_order():
    xml_file = 'cardscheduler/kanjidic2.xml'
    kanji_readings = load_kanji_readings(xml_file)
    field_name = "ID"
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
        kanji_reading_pairs = get_kanji_reading_pairs(field_value, kanji_readings)
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
            pair_count = len(get_kanji_reading_pairs(field_value, kanji_readings))
            if pair_count > 0:
                weight = 1.0# / pair_count
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
        kanji_reading_pairs = get_kanji_reading_pairs(field_value, kanji_readings)

        pair_scores = []

        for pair in kanji_reading_pairs:
            if pair in kanji_reading_to_cards:
                pair_total_weighted_ivl = 0
                pair_total_weight = 0

                for other_card in kanji_reading_to_cards[pair]:
                    if other_card.id != card.id:
                        other_note = other_card.note()
                        other_field_value = get_field_value(other_note, field_name)
                        other_pair_count = len(get_kanji_reading_pairs(other_field_value, kanji_readings))

                        if other_pair_count > 0:
                            weight = 1.0 #/ other_pair_count
                            pair_total_weighted_ivl += other_card.ivl * weight
                            pair_total_weight += weight

                if pair_total_weight > 0:
                    pair_weighted_avg = pair_total_weighted_ivl / pair_total_weight
                    pair_scores.append(pair_weighted_avg)
                    print(f"Pair '{pair}' in '{field_value}': avg={pair_weighted_avg:.2f}, total_weight={pair_total_weight:.2f}")

        # Simple average: each kanji-reading pair contributes equally to the final score
        if card.id == 1755191995946:
            print(f"Card ID {card.id} ({field_value}) pair scores: {pair_scores}")
            print(f"kanji_reading_pairs : {kanji_reading_pairs}")
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