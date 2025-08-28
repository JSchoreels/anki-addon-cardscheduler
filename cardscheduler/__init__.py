from aqt import mw
from aqt.utils import showInfo
import re
import xml.etree.ElementTree as ET
import os


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
    # Updated pattern to allow mixed kanji and kana in the first group
    pattern = r'([一-龯ぁ-ゖァ-ヺー々]+)\[([ぁ-ゖァ-ヺー]+)\]'  # Add 々 to the pattern
    matches = re.findall(pattern, text)

    processed_kanji = set()
    for kanji_word, reading in matches:
        if len(kanji_word) == 1:
            kanji_pairs.add(f"{kanji_word}[{reading}]")
            processed_kanji.add(kanji_word)
        else:
            # Handle 々 (iteration mark) by expanding it to repeat the previous kanji
            expanded_kanji_word = expand_iteration_marks(kanji_word)

            # Extract only kanji characters from compound word (after expansion)
            kanji_chars = extract_kanji_only(expanded_kanji_word)

            if len(kanji_chars) > 1:
                # Always add the compound word itself (with original form including 々)
                kanji_pairs.add(f"{kanji_word}[{reading}]")

                # For mixed kanji-kana words, use position-aware splitting
                reading_parts = split_reading_with_positions(expanded_kanji_word, reading, kanji_readings)
                if reading_parts:
                    # For repeated kanji (when 々 is used), only add unique kanji-reading pairs
                    unique_pairs = set()
                    for kanji, reading_part in reading_parts:
                        unique_pairs.add((kanji, reading_part))

                    for kanji, reading_part in unique_pairs:
                        kanji_pairs.add(f"{kanji}[{reading_part}]")
                        processed_kanji.add(kanji)
                else:
                    # If splitting fails, add individual kanji with empty readings
                    unique_kanji = set(kanji_chars)  # Remove duplicates
                    for kanji in unique_kanji:
                        kanji_pairs.add(f"{kanji}[]")
                        processed_kanji.add(kanji)
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


def split_reading_with_positions(kanji_word, reading, kanji_readings):
    """Split reading by mapping kanji positions to reading segments."""
    # Find positions of kanji in the original word
    kanji_positions = []
    kanji_chars = []

    for i, char in enumerate(kanji_word):
        if '\u4e00' <= char <= '\u9fff':  # Is kanji
            kanji_positions.append(i)
            kanji_chars.append(char)

    if len(kanji_chars) <= 1:
        return None

    # Try to map reading segments to kanji based on their positions
    pairs = []
    reading_index = 0

    for i, (pos, kanji) in enumerate(zip(kanji_positions, kanji_chars)):
        if i == 0:
            # First kanji: reading starts from beginning
            start_reading_pos = 0
        else:
            # Calculate how much kana is between previous kanji and this one
            prev_kanji_pos = kanji_positions[i-1]
            kana_between = pos - prev_kanji_pos - 1
            reading_index += kana_between
            start_reading_pos = reading_index

        # Find the best matching reading for this kanji
        possible_readings = kanji_readings.get(kanji, [])
        possible_readings = sorted(possible_readings, key=len, reverse=True)

        found_match = False
        remaining_reading = reading[start_reading_pos:]

        for reading_option in possible_readings:
            if remaining_reading.startswith(reading_option):
                # Check if this is a rendaku form and if so, find the base reading
                base_reading = get_base_reading_for_rendaku(reading_option, possible_readings)
                pairs.append((kanji, base_reading if base_reading else reading_option))
                reading_index = start_reading_pos + len(reading_option)
                found_match = True
                break

        if not found_match:
            # Try fuzzy matching
            for reading_option in possible_readings:
                max_check_length = min(len(reading_option) + 2, len(remaining_reading))
                if (fuzzy := fuzzy_reading_match(reading_option, remaining_reading[:max_check_length])):
                    matched_actual, matched_kanjidic = fuzzy
                    pairs.append((kanji, matched_kanjidic))
                    reading_index = start_reading_pos + len(matched_actual)
                    found_match = True
                    break

        if not found_match:
            # If no match found, fall back to original split_reading approach
            return split_reading(kanji_chars, reading, kanji_readings)

    return pairs if len(pairs) == len(kanji_chars) else None

def split_reading(kanji_chars, reading, kanji_readings):
    # Simple case: if number of kanji equals number of kana units, try 1:1 mapping with validation
    if len(kanji_chars) == count_kana_units(reading):
        pairs = []
        kana_units = extract_kana_units(reading)

        # Validate that each kanji actually has the assigned kana unit as an EXACT reading (no fuzzy matching)
        valid_mapping = True
        for i, kanji in enumerate(kanji_chars):
            kana_unit = kana_units[i]
            possible_readings = kanji_readings.get(kanji, [])

            # Only allow exact matches for simple 1:1 mapping
            if kana_unit not in possible_readings:
                valid_mapping = False
                break

        # If all mappings are exact matches, use the 1:1 mapping
        if valid_mapping:
            for i, kanji in enumerate(kanji_chars):
                pairs.append((kanji, kana_units[i]))
            return pairs

    # Complex case: try to match against dictionary readings (handles sokuon transformations)
    remaining_reading = reading
    pairs = []

    for kanji in kanji_chars:
        found_match = False
        possible_readings = kanji_readings.get(kanji, [])
        possible_readings = sorted(possible_readings, key=len, reverse=True)

        # First, try fuzzy matching (which includes sokuon transformations)
        for reading_option in possible_readings:
            max_check_length = min(len(reading_option) + 2, len(remaining_reading))
            if (fuzzy := fuzzy_reading_match(reading_option, remaining_reading[:max_check_length])):
                matched_actual, matched_kanjidic = fuzzy
                pairs.append((kanji, matched_kanjidic))
                remaining_reading = remaining_reading[len(matched_actual):]
                found_match = True
                break

        # If no fuzzy match found, try exact matching
        if not found_match:
            for reading_option in possible_readings:
                if remaining_reading.startswith(reading_option):
                    # Check if this is a rendaku form and if so, find the base reading
                    base_reading = get_base_reading_for_rendaku(reading_option, possible_readings)
                    pairs.append((kanji, base_reading if base_reading else reading_option))
                    remaining_reading = remaining_reading[len(reading_option):]
                    found_match = True
                    break

        # If still no match found, try partial matching (shortened versions)
        if not found_match:
            for reading_option in possible_readings:
                # Try to find if the remaining reading starts with a shortened version of this reading
                # Check prefixes of length 1 and 2 (most common shortened versions)
                for prefix_len in [2, 1]:  # Try 2-kana first, then 1-kana
                    if len(reading_option) > prefix_len:
                        prefix = reading_option[:prefix_len]
                        if remaining_reading.startswith(prefix):
                            pairs.append((kanji, reading_option))  # Keep the full reading in the result
                            remaining_reading = remaining_reading[len(prefix):]
                            found_match = True
                            break
                if found_match:
                    break

        if not found_match:
            # Complex matching failed, fall back to normalization approach
            break
    else:
        # All kanji matched successfully - leftover reading is OK (okurigana/inflections)
        return pairs

    # Fallback case: Try removing "stylistic" small tsu and see if it becomes 1:1
    normalized_reading = normalize_reading_for_splitting(reading)
    if len(kanji_chars) == count_kana_units(normalized_reading):
        pairs = []
        kana_units = extract_kana_units(normalized_reading)
        for i, kanji in enumerate(kanji_chars):
            pairs.append((kanji, kana_units[i]))
        return pairs

    # If everything fails, return None
    return None

def normalize_reading_for_splitting(reading):
    """Remove 'noise' characters like small tsu for splitting purposes."""
    # Remove small tsu (っ) which is often just phonetic emphasis
    normalized = reading.replace('っ', '')

    # Could add other normalizations here if needed
    # For example: remove long vowel marks, etc.

    return normalized

def count_kana_units(text):
    """Count kana units properly, treating combinations like ちゃ, きゅ, etc. as single units."""
    # Small kana that combine with preceding kana to form single phonetic units
    small_kana = {'ゃ', 'ゅ', 'ょ', 'ぁ', 'ぃ', 'ぅ', 'ぇ', 'ぉ', 'っ', 'ァ', 'ィ', 'ゥ', 'ェ', 'ォ', 'ャ', 'ュ', 'ョ', 'ッ'}

    count = 0
    i = 0
    while i < len(text):
        count += 1
        # Skip the next character if it's a small kana (part of current unit)
        if i + 1 < len(text) and text[i + 1] in small_kana:
            i += 2  # Skip both the main kana and the small kana
        else:
            i += 1  # Just move to next character

    return count

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

def fuzzy_reading_match(kanjidic_reading, actual_reading):
    # Exact match
    if kanjidic_reading == actual_reading:
        return (actual_reading, kanjidic_reading)

    # Generic sokuon transformation: XYZ → XYっ
    # This handles cases where a kana ending gets converted to sokuon in compound words
    # Examples: じつ → じっ, がく → がっ, いち → いっ, はつ → はっ, etc.
    sokuon_endings = ['つ', 'ち', 'く', 'き', 'さ', 'し', 'そ', 'こ', 'て', 'と', 'け']

    for ending in sokuon_endings:
        if kanjidic_reading.endswith(ending):
            # Create the sokuon version: replace ending with っ
            sokuon_version = kanjidic_reading[:-len(ending)] + 'っ'
            if actual_reading.startswith(sokuon_version):
                return (sokuon_version, kanjidic_reading)

    # Handle leading sokuon: っちゃ should match ちゃ
    # But only if the lengths are reasonable (within 1-2 characters difference)
    if (actual_reading.startswith('っ') and
        kanjidic_reading == actual_reading[1:] and
        len(actual_reading) <= len(kanjidic_reading) + 2):
        return (actual_reading, kanjidic_reading)

    # Multi-character rendaku transformations (exact matches)
    multi_char_rendaku = {
        # h→b rendaku (more common)
        'ひょう': 'びょう', 'ひゃ': 'びゃ', 'ひゅ': 'びゅ',
        'ほう': 'ぼう', 'は': 'ば', 'ひ': 'び', 'ふ': 'ぶ', 'へ': 'べ', 'ほ': 'ぼ',
        # f→p rendaku
        'ふょう': 'ぷょう', 'ふゃ': 'ぷゃ', 'ふゅ': 'ぷゅ',
    }

    # Try h→p rendaku as a separate check since some words use p instead of b
    h_to_p_rendaku = {
        'ひょう': 'ぴょう', 'ひゃ': 'ぴゃ', 'ひゅ': 'ぴゅ',
        'ほう': 'ぽう', 'は': 'ぱ', 'ひ': 'ぴ', 'ふ': 'ぷ', 'へ': 'ぺ', 'ほ': 'ぽ',
    }

    if kanjidic_reading in multi_char_rendaku:
        expected_rendaku = multi_char_rendaku[kanjidic_reading]
        if actual_reading.startswith(expected_rendaku):
            return (expected_rendaku, kanjidic_reading)

    # Also try h→p rendaku transformations
    if kanjidic_reading in h_to_p_rendaku:
        expected_rendaku = h_to_p_rendaku[kanjidic_reading]
        if actual_reading.startswith(expected_rendaku):
            return (expected_rendaku, kanjidic_reading)

    # Single character rendaku transformations
    if len(kanjidic_reading) == len(actual_reading) and len(kanjidic_reading) > 0:
        first_kanjidic = kanjidic_reading[0]
        first_actual = actual_reading[0]
        rest_matches = kanjidic_reading[1:] == actual_reading[1:]

        # Basic rendaku pairs (avoiding duplicates)
        single_char_rendaku = {
            'か': 'が', 'き': 'ぎ', 'く': 'ぐ', 'け': 'げ', 'こ': 'ご',
            'さ': 'ざ', 'し': 'じ', 'す': 'ず', 'せ': 'ぜ', 'そ': 'ぞ',
            'た': 'だ', 'ち': 'ぢ', 'つ': 'づ', 'て': 'で', 'と': 'ど',
            'は': 'ば', 'ひ': 'び', 'ふ': 'ぶ', 'へ': 'べ', 'ほ': 'ぼ',
        }

        # Check h→p transformations separately
        h_to_p_rendaku = {
            'は': 'ぱ', 'ひ': 'ぴ', 'ふ': 'ぷ', 'へ': 'ぺ', 'ほ': 'ぽ',
        }

        # f→p transformations
        f_to_p_rendaku = {
            'ふぁ': 'ぱ', 'ふぃ': 'ぴ', 'ふぇ': 'ぺ', 'ふぉ': 'ぽ',
        }

        if rest_matches:
            # Try basic rendaku first
            if first_kanjidic in single_char_rendaku and first_actual == single_char_rendaku[first_kanjidic]:
                return (actual_reading, kanjidic_reading)

            # Try h→p rendaku
            if first_kanjidic in h_to_p_rendaku and first_actual == h_to_p_rendaku[first_kanjidic]:
                return (actual_reading, kanjidic_reading)

        # Check f→p for multi-character sequences
        for base, rendaku in f_to_p_rendaku.items():
            if kanjidic_reading.startswith(base) and actual_reading.startswith(rendaku):
                if kanjidic_reading[len(base):] == actual_reading[len(rendaku):]:
                    return (actual_reading, kanjidic_reading)

    # Sokuon: がく → がっ (length difference) - original logic
    if kanjidic_reading.endswith('く') and actual_reading.endswith('っ'):
        if kanjidic_reading[:-1] == actual_reading[:-1]:
            return (actual_reading, kanjidic_reading)

    return None

def load_kanji_readings(xml_file):
    """Load kanji readings from kanjidic2_light.xml into a dictionary."""
    kanji_readings = {}
    tree = ET.parse(xml_file)
    root = tree.getroot()

    for character in root.findall('character'):
        kanji = character.find('literal').text
        readings = []

        # Get kun'yomi readings (Japanese readings)
        for reading in character.findall('ja_kun'):
            reading_text = reading.text
            if reading_text:
                # Clean kun'yomi readings (remove okurigana indicators)
                reading_text = reading_text.split('.')[0]
                reading_text = reading_text.replace('-', '')
                readings.append(reading_text)

        # Get on'yomi readings (Chinese readings)
        for reading in character.findall('ja_on'):
            reading_text = reading.text
            if reading_text:
                # Convert katakana on'yomi to hiragana for consistency
                readings.append(katakana_to_hiragana(reading_text))

        # Add rendaku (sequential voicing) variations for common readings
        # These are needed for exact matching in compound words
        rendaku_readings = []
        for reading in readings:
            rendaku_form = get_rendaku_form(reading)
            if rendaku_form and rendaku_form not in readings:
                rendaku_readings.append(rendaku_form)

        readings.extend(rendaku_readings)
        kanji_readings[kanji] = readings
    return kanji_readings

def get_rendaku_form(reading):
    """Generate rendaku (sequential voicing) form of a reading."""
    if not reading:
        return None

    # Generate all possible rendaku forms for the first character
    first_char = reading[0]
    rest_of_reading = reading[1:]

    # Common rendaku transformations - return the first applicable one
    # Priority: more common transformations first
    if first_char == 'か': return 'が' + rest_of_reading
    elif first_char == 'き': return 'ぎ' + rest_of_reading
    elif first_char == 'く': return 'ぐ' + rest_of_reading
    elif first_char == 'け': return 'げ' + rest_of_reading
    elif first_char == 'こ': return 'ご' + rest_of_reading
    elif first_char == 'さ': return 'ざ' + rest_of_reading
    elif first_char == 'し': return 'じ' + rest_of_reading
    elif first_char == 'す': return 'ず' + rest_of_reading
    elif first_char == 'せ': return 'ぜ' + rest_of_reading
    elif first_char == 'そ': return 'ぞ' + rest_of_reading
    elif first_char == 'た': return 'だ' + rest_of_reading
    elif first_char == 'ち': return 'ぢ' + rest_of_reading
    elif first_char == 'つ': return 'づ' + rest_of_reading
    elif first_char == 'て': return 'で' + rest_of_reading
    elif first_char == 'と': return 'ど' + rest_of_reading
    elif first_char == 'は': return 'ば' + rest_of_reading  # h→b more common
    elif first_char == 'ひ': return 'び' + rest_of_reading
    elif first_char == 'ふ': return 'ぶ' + rest_of_reading  # f→b more common than f→p
    elif first_char == 'へ': return 'べ' + rest_of_reading
    elif first_char == 'ほ': return 'ぼ' + rest_of_reading
    # f-row to p transformations
    elif first_char == 'ふぁ': return 'ぱ' + rest_of_reading
    elif first_char == 'ふぃ': return 'ぴ' + rest_of_reading
    elif first_char == 'ふぇ': return 'ぺ' + rest_of_reading
    elif first_char == 'ふぉ': return 'ぽ' + rest_of_reading

    return None

def get_kanji_reading_pairs_simple(text):
    """Fallback: treat compound words as single units"""
    pattern = r'([一-龯]+)\[([ぁ-ゖァ-ヺー]+)\]'
    matches = re.findall(pattern, text)
    return set([f"{kanji}[{reading}]" for kanji, reading in matches])

# Load Kanji readings at the beginning of compute_order
def compute_order():
    # Get the absolute path to the XML file relative to this module
    current_dir = os.path.dirname(os.path.abspath(__file__))
    xml_file = os.path.join(current_dir, 'kanjidic2_light.xml')

    try:
        kanji_readings = load_kanji_readings(xml_file)
        print(f"Successfully loaded {len(kanji_readings)} kanji from {xml_file}")
    except FileNotFoundError:
        print(f"Error: Could not find kanjidic2_light.xml at {xml_file}")
        showInfo(f"Error: kanjidic2_light.xml not found. Please ensure the file is in the cardscheduler directory.")
        return
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        showInfo(f"Error: Invalid XML format in kanjidic2_light.xml")
        return
    except Exception as e:
        print(f"Unexpected error loading kanji readings: {e}")
        showInfo(f"Error loading kanji data: {str(e)}")
        return

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

def extract_kana_units(text):
    """Extract individual kana units, treating combinations like ちゃ, きゅ as single units."""
    small_kana = {'ゃ', 'ゅ', 'ょ', 'ぁ', 'ぃ', 'ぅ', 'ぇ', 'ぉ', 'っ', 'ァ', 'ィ', 'ゥ', 'ェ', 'ォ', 'ャ', 'ュ', 'ョ', 'ッ'}

    units = []
    i = 0
    while i < len(text):
        # Check if next character is a small kana (part of current unit)
        if i + 1 < len(text) and text[i + 1] in small_kana:
            units.append(text[i:i+2])  # Include both characters as one unit
            i += 2
        else:
            units.append(text[i])  # Single character unit
            i += 1

    return units

def get_base_reading_for_rendaku(reading, possible_readings):
    """Find the base reading for a rendaku form, if applicable."""
    # Common rendaku transformations (voiced -> unvoiced)
    reverse_rendaku_map = {
        'が': 'か', 'ぎ': 'き', 'ぐ': 'く', 'げ': 'け', 'ご': 'こ',
        'ざ': 'さ', 'じ': 'し', 'ず': 'す', 'ぜ': 'せ', 'ぞ': 'そ',
        'だ': 'た', 'ぢ': 'ち', 'づ': 'つ', 'で': 'て', 'ど': 'と',
        'ば': 'は', 'び': 'ひ', 'ぶ': 'ふ', 'べ': 'へ', 'ぼ': 'ほ',
        # Add complete p→f reverse transformations for all p-sounds
        'ぷ': 'ふ', 'ぱ': 'ふぁ', 'ぴ': 'ふぃ', 'ぺ': 'ふぇ', 'ぽ': 'ふぉ',
        # Add p→h reverse transformations (alternative to b→h)
        # Note: ぱ is handled above as ふぁ, but we also need direct p→h for cases like ぽう→ほう
        'ぱ': 'は', 'ぴ': 'ひ', 'ぽ': 'ほ', 'ぺ': 'へ'
    }

    # Check if the reading is a rendaku form
    first_char = reading[0]
    if first_char in reverse_rendaku_map:
        # Get the base reading by replacing the first character with its unvoiced counterpart
        base_reading = reverse_rendaku_map[first_char] + reading[1:]

        # Ensure the base reading is a valid reading for this kanji
        if base_reading in possible_readings:
            return base_reading

    return None

def expand_iteration_marks(kanji_word):
    """Expand 々 iteration marks in a kanji word."""
    # Split the word by 々 and keep track of positions
    parts = []
    start = 0

    for i, char in enumerate(kanji_word):
        if char == '々':
            # Add the segment before 々 as a new part
            if start < i:
                parts.append(kanji_word[start:i])
            # Repeat the last part (after expansion) for 々
            if parts:
                parts.append(parts[-1])
            start = i + 1

    # Add the final segment after the last 々
    if start < len(kanji_word):
        parts.append(kanji_word[start:])

    # Join the parts back together
    return ''.join(parts)

def get_kanji_reading_pairs(text, kanji_readings):
    """Extract kanji-reading pairs using Kanjidic, falling back to kanji-only."""
    kanji_pairs = set()
    # Updated pattern to allow mixed kanji and kana in the first group
    pattern = r'([一-龯ぁ-ゖァ-ヺー々]+)\[([ぁ-ゖァ-ヺー]+)\]'  # Add 々 to the pattern
    matches = re.findall(pattern, text)

    processed_kanji = set()
    for kanji_word, reading in matches:
        if len(kanji_word) == 1:
            kanji_pairs.add(f"{kanji_word}[{reading}]")
            processed_kanji.add(kanji_word)
        else:
            # Handle 々 (iteration mark) by expanding it to repeat the previous kanji
            expanded_kanji_word = expand_iteration_marks(kanji_word)

            # Extract only kanji characters from compound word (after expansion)
            kanji_chars = extract_kanji_only(expanded_kanji_word)

            if len(kanji_chars) > 1:
                # Always add the compound word itself (with original form including 々)
                kanji_pairs.add(f"{kanji_word}[{reading}]")

                # For mixed kanji-kana words, use position-aware splitting
                reading_parts = split_reading_with_positions(expanded_kanji_word, reading, kanji_readings)
                if reading_parts:
                    # For repeated kanji (when 々 is used), only add unique kanji-reading pairs
                    unique_pairs = set()
                    for kanji, reading_part in reading_parts:
                        unique_pairs.add((kanji, reading_part))

                    for kanji, reading_part in unique_pairs:
                        kanji_pairs.add(f"{kanji}[{reading_part}]")
                        processed_kanji.add(kanji)
                else:
                    # If splitting fails, add individual kanji with empty readings
                    unique_kanji = set(kanji_chars)  # Remove duplicates
                    for kanji in unique_kanji:
                        kanji_pairs.add(f"{kanji}[]")
                        processed_kanji.add(kanji)
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


def split_reading_with_positions(kanji_word, reading, kanji_readings):
    """Split reading by mapping kanji positions to reading segments."""
    # Find positions of kanji in the original word
    kanji_positions = []
    kanji_chars = []

    for i, char in enumerate(kanji_word):
        if '\u4e00' <= char <= '\u9fff':  # Is kanji
            kanji_positions.append(i)
            kanji_chars.append(char)

    if len(kanji_chars) <= 1:
        return None

    # Try to map reading segments to kanji based on their positions
    pairs = []
    reading_index = 0

    for i, (pos, kanji) in enumerate(zip(kanji_positions, kanji_chars)):
        if i == 0:
            # First kanji: reading starts from beginning
            start_reading_pos = 0
        else:
            # Calculate how much kana is between previous kanji and this one
            prev_kanji_pos = kanji_positions[i-1]
            kana_between = pos - prev_kanji_pos - 1
            reading_index += kana_between
            start_reading_pos = reading_index

        # Find the best matching reading for this kanji
        possible_readings = kanji_readings.get(kanji, [])
        possible_readings = sorted(possible_readings, key=len, reverse=True)

        found_match = False
        remaining_reading = reading[start_reading_pos:]

        for reading_option in possible_readings:
            if remaining_reading.startswith(reading_option):
                # Check if this is a rendaku form and if so, find the base reading
                base_reading = get_base_reading_for_rendaku(reading_option, possible_readings)
                pairs.append((kanji, base_reading if base_reading else reading_option))
                reading_index = start_reading_pos + len(reading_option)
                found_match = True
                break

        if not found_match:
            # Try fuzzy matching
            for reading_option in possible_readings:
                max_check_length = min(len(reading_option) + 2, len(remaining_reading))
                if (fuzzy := fuzzy_reading_match(reading_option, remaining_reading[:max_check_length])):
                    matched_actual, matched_kanjidic = fuzzy
                    pairs.append((kanji, matched_kanjidic))
                    reading_index = start_reading_pos + len(matched_actual)
                    found_match = True
                    break

        if not found_match:
            # If no match found, fall back to original split_reading approach
            return split_reading(kanji_chars, reading, kanji_readings)

    return pairs if len(pairs) == len(kanji_chars) else None

def split_reading(kanji_chars, reading, kanji_readings):
    # Simple case: if number of kanji equals number of kana units, try 1:1 mapping with validation
    if len(kanji_chars) == count_kana_units(reading):
        pairs = []
        kana_units = extract_kana_units(reading)

        # Validate that each kanji actually has the assigned kana unit as an EXACT reading (no fuzzy matching)
        valid_mapping = True
        for i, kanji in enumerate(kanji_chars):
            kana_unit = kana_units[i]
            possible_readings = kanji_readings.get(kanji, [])

            # Only allow exact matches for simple 1:1 mapping
            if kana_unit not in possible_readings:
                valid_mapping = False
                break

        # If all mappings are exact matches, use the 1:1 mapping
        if valid_mapping:
            for i, kanji in enumerate(kanji_chars):
                pairs.append((kanji, kana_units[i]))
            return pairs

    # Complex case: try to match against dictionary readings (handles sokuon transformations)
    remaining_reading = reading
    pairs = []

    for kanji in kanji_chars:
        found_match = False
        possible_readings = kanji_readings.get(kanji, [])
        possible_readings = sorted(possible_readings, key=len, reverse=True)

        # First, try fuzzy matching (which includes sokuon transformations)
        for reading_option in possible_readings:
            max_check_length = min(len(reading_option) + 2, len(remaining_reading))
            if (fuzzy := fuzzy_reading_match(reading_option, remaining_reading[:max_check_length])):
                matched_actual, matched_kanjidic = fuzzy
                pairs.append((kanji, matched_kanjidic))
                remaining_reading = remaining_reading[len(matched_actual):]
                found_match = True
                break

        # If no fuzzy match found, try exact matching
        if not found_match:
            for reading_option in possible_readings:
                if remaining_reading.startswith(reading_option):
                    # Check if this is a rendaku form and if so, find the base reading
                    base_reading = get_base_reading_for_rendaku(reading_option, possible_readings)
                    pairs.append((kanji, base_reading if base_reading else reading_option))
                    remaining_reading = remaining_reading[len(reading_option):]
                    found_match = True
                    break

        # If still no match found, try partial matching (shortened versions)
        if not found_match:
            for reading_option in possible_readings:
                # Try to find if the remaining reading starts with a shortened version of this reading
                # Check prefixes of length 1 and 2 (most common shortened versions)
                for prefix_len in [2, 1]:  # Try 2-kana first, then 1-kana
                    if len(reading_option) > prefix_len:
                        prefix = reading_option[:prefix_len]
                        if remaining_reading.startswith(prefix):
                            pairs.append((kanji, reading_option))  # Keep the full reading in the result
                            remaining_reading = remaining_reading[len(prefix):]
                            found_match = True
                            break
                if found_match:
                    break

        if not found_match:
            # Complex matching failed, fall back to normalization approach
            break
    else:
        # All kanji matched successfully - leftover reading is OK (okurigana/inflections)
        return pairs

    # Fallback case: Try removing "stylistic" small tsu and see if it becomes 1:1
    normalized_reading = normalize_reading_for_splitting(reading)
    if len(kanji_chars) == count_kana_units(normalized_reading):
        pairs = []
        kana_units = extract_kana_units(normalized_reading)
        for i, kanji in enumerate(kanji_chars):
            pairs.append((kanji, kana_units[i]))
        return pairs

    # If everything fails, return None
    return None

def normalize_reading_for_splitting(reading):
    """Remove 'noise' characters like small tsu for splitting purposes."""
    # Remove small tsu (っ) which is often just phonetic emphasis
    normalized = reading.replace('っ', '')

    # Could add other normalizations here if needed
    # For example: remove long vowel marks, etc.

    return normalized

def count_kana_units(text):
    """Count kana units properly, treating combinations like ちゃ, きゅ, etc. as single units."""
    # Small kana that combine with preceding kana to form single phonetic units
    small_kana = {'ゃ', 'ゅ', 'ょ', 'ぁ', 'ぃ', 'ぅ', 'ぇ', 'ぉ', 'っ', 'ァ', 'ィ', 'ゥ', 'ェ', 'ォ', 'ャ', 'ュ', 'ョ', 'ッ'}

    count = 0
    i = 0
    while i < len(text):
        count += 1
        # Skip the next character if it's a small kana (part of current unit)
        if i + 1 < len(text) and text[i + 1] in small_kana:
            i += 2  # Skip both the main kana and the small kana
        else:
            i += 1  # Just move to next character

    return count

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

def fuzzy_reading_match(kanjidic_reading, actual_reading):
    # Exact match
    if kanjidic_reading == actual_reading:
        return (actual_reading, kanjidic_reading)

    # Generic sokuon transformation: XYZ → XYっ
    # This handles cases where a kana ending gets converted to sokuon in compound words
    # Examples: じつ → じっ, がく → がっ, いち → いっ, はつ → はっ, etc.
    sokuon_endings = ['つ', 'ち', 'く', 'き', 'さ', 'し', 'そ', 'こ', 'て', 'と', 'け']

    for ending in sokuon_endings:
        if kanjidic_reading.endswith(ending):
            # Create the sokuon version: replace ending with っ
            sokuon_version = kanjidic_reading[:-len(ending)] + 'っ'
            if actual_reading.startswith(sokuon_version):
                return (sokuon_version, kanjidic_reading)

    # Handle leading sokuon: っちゃ should match ちゃ
    # But only if the lengths are reasonable (within 1-2 characters difference)
    if (actual_reading.startswith('っ') and
        kanjidic_reading == actual_reading[1:] and
        len(actual_reading) <= len(kanjidic_reading) + 2):
        return (actual_reading, kanjidic_reading)

    # Multi-character rendaku transformations (exact matches)
    multi_char_rendaku = {
        # h→b rendaku (more common)
        'ひょう': 'びょう', 'ひゃ': 'びゃ', 'ひゅ': 'びゅ',
        'ほう': 'ぼう', 'は': 'ば', 'ひ': 'び', 'ふ': 'ぶ', 'へ': 'べ', 'ほ': 'ぼ',
        # f→p rendaku
        'ふょう': 'ぷょう', 'ふゃ': 'ぷゃ', 'ふゅ': 'ぷゅ',
    }

    # Try h→p rendaku as a separate check since some words use p instead of b
    h_to_p_rendaku = {
        'ひょう': 'ぴょう', 'ひゃ': 'ぴゃ', 'ひゅ': 'ぴゅ',
        'ほう': 'ぽう', 'は': 'ぱ', 'ひ': 'ぴ', 'ふ': 'ぷ', 'へ': 'ぺ', 'ほ': 'ぽ',
    }

    if kanjidic_reading in multi_char_rendaku:
        expected_rendaku = multi_char_rendaku[kanjidic_reading]
        if actual_reading.startswith(expected_rendaku):
            return (expected_rendaku, kanjidic_reading)

    # Also try h→p rendaku transformations
    if kanjidic_reading in h_to_p_rendaku:
        expected_rendaku = h_to_p_rendaku[kanjidic_reading]
        if actual_reading.startswith(expected_rendaku):
            return (expected_rendaku, kanjidic_reading)

    # Single character rendaku transformations
    if len(kanjidic_reading) == len(actual_reading) and len(kanjidic_reading) > 0:
        first_kanjidic = kanjidic_reading[0]
        first_actual = actual_reading[0]
        rest_matches = kanjidic_reading[1:] == actual_reading[1:]

        # Basic rendaku pairs (avoiding duplicates)
        single_char_rendaku = {
            'か': 'が', 'き': 'ぎ', 'く': 'ぐ', 'け': 'げ', 'こ': 'ご',
            'さ': 'ざ', 'し': 'じ', 'す': 'ず', 'せ': 'ぜ', 'そ': 'ぞ',
            'た': 'だ', 'ち': 'ぢ', 'つ': 'づ', 'て': 'で', 'と': 'ど',
            'は': 'ば', 'ひ': 'び', 'ふ': 'ぶ', 'へ': 'べ', 'ほ': 'ぼ',
        }

        # Check h→p transformations separately
        h_to_p_rendaku = {
            'は': 'ぱ', 'ひ': 'ぴ', 'ふ': 'ぷ', 'へ': 'ぺ', 'ほ': 'ぽ',
        }

        # f→p transformations
        f_to_p_rendaku = {
            'ふぁ': 'ぱ', 'ふぃ': 'ぴ', 'ふぇ': 'ぺ', 'ふぉ': 'ぽ',
        }

        if rest_matches:
            # Try basic rendaku first
            if first_kanjidic in single_char_rendaku and first_actual == single_char_rendaku[first_kanjidic]:
                return (actual_reading, kanjidic_reading)

            # Try h→p rendaku
            if first_kanjidic in h_to_p_rendaku and first_actual == h_to_p_rendaku[first_kanjidic]:
                return (actual_reading, kanjidic_reading)

        # Check f→p for multi-character sequences
        for base, rendaku in f_to_p_rendaku.items():
            if kanjidic_reading.startswith(base) and actual_reading.startswith(rendaku):
                if kanjidic_reading[len(base):] == actual_reading[len(rendaku):]:
                    return (actual_reading, kanjidic_reading)

    # Sokuon: がく → がっ (length difference) - original logic
    if kanjidic_reading.endswith('く') and actual_reading.endswith('っ'):
        if kanjidic_reading[:-1] == actual_reading[:-1]:
            return (actual_reading, kanjidic_reading)

    return None

def load_kanji_readings(xml_file):
    """Load kanji readings from kanjidic2_light.xml into a dictionary."""
    kanji_readings = {}
    tree = ET.parse(xml_file)
    root = tree.getroot()

    for character in root.findall('character'):
        kanji = character.find('literal').text
        readings = []

        # Get kun'yomi readings (Japanese readings)
        for reading in character.findall('ja_kun'):
            reading_text = reading.text
            if reading_text:
                # Clean kun'yomi readings (remove okurigana indicators)
                reading_text = reading_text.split('.')[0]
                reading_text = reading_text.replace('-', '')
                readings.append(reading_text)

        # Get on'yomi readings (Chinese readings)
        for reading in character.findall('ja_on'):
            reading_text = reading.text
            if reading_text:
                # Convert katakana on'yomi to hiragana for consistency
                readings.append(katakana_to_hiragana(reading_text))

        # Add rendaku (sequential voicing) variations for common readings
        # These are needed for exact matching in compound words
        rendaku_readings = []
        for reading in readings:
            rendaku_form = get_rendaku_form(reading)
            if rendaku_form and rendaku_form not in readings:
                rendaku_readings.append(rendaku_form)

        readings.extend(rendaku_readings)
        kanji_readings[kanji] = readings
    return kanji_readings

def get_rendaku_form(reading):
    """Generate rendaku (sequential voicing) form of a reading."""
    if not reading:
        return None

    # Generate all possible rendaku forms for the first character
    first_char = reading[0]
    rest_of_reading = reading[1:]

    # Common rendaku transformations - return the first applicable one
    # Priority: more common transformations first
    if first_char == 'か': return 'が' + rest_of_reading
    elif first_char == 'き': return 'ぎ' + rest_of_reading
    elif first_char == 'く': return 'ぐ' + rest_of_reading
    elif first_char == 'け': return 'げ' + rest_of_reading
    elif first_char == 'こ': return 'ご' + rest_of_reading
    elif first_char == 'さ': return 'ざ' + rest_of_reading
    elif first_char == 'し': return 'じ' + rest_of_reading
    elif first_char == 'す': return 'ず' + rest_of_reading
    elif first_char == 'せ': return 'ぜ' + rest_of_reading
    elif first_char == 'そ': return 'ぞ' + rest_of_reading
    elif first_char == 'た': return 'だ' + rest_of_reading
    elif first_char == 'ち': return 'ぢ' + rest_of_reading
    elif first_char == 'つ': return 'づ' + rest_of_reading
    elif first_char == 'て': return 'で' + rest_of_reading
    elif first_char == 'と': return 'ど' + rest_of_reading
    elif first_char == 'は': return 'ば' + rest_of_reading  # h→b more common
    elif first_char == 'ひ': return 'び' + rest_of_reading
    elif first_char == 'ふ': return 'ぶ' + rest_of_reading  # f→b more common than f→p
    elif first_char == 'へ': return 'べ' + rest_of_reading
    elif first_char == 'ほ': return 'ぼ' + rest_of_reading
    # f-row to p transformations
    elif first_char == 'ふぁ': return 'ぱ' + rest_of_reading
    elif first_char == 'ふぃ': return 'ぴ' + rest_of_reading
    elif first_char == 'ふぇ': return 'ぺ' + rest_of_reading
    elif first_char == 'ふぉ': return 'ぽ' + rest_of_reading

    return None

def get_kanji_reading_pairs_simple(text):
    """Fallback: treat compound words as single units"""
    pattern = r'([一-龯]+)\[([ぁ-ゖァ-ヺー]+)\]'
    matches = re.findall(pattern, text)
    return set([f"{kanji}[{reading}]" for kanji, reading in matches])

# Load Kanji readings at the beginning of compute_order
def compute_order():
    # Get the absolute path to the XML file relative to this module
    current_dir = os.path.dirname(os.path.abspath(__file__))
    xml_file = os.path.join(current_dir, 'kanjidic2_light.xml')

    try:
        kanji_readings = load_kanji_readings(xml_file)
        print(f"Successfully loaded {len(kanji_readings)} kanji from {xml_file}")
    except FileNotFoundError:
        print(f"Error: Could not find kanjidic2_light.xml at {xml_file}")
        showInfo(f"Error: kanjidic2_light.xml not found. Please ensure the file is in the cardscheduler directory.")
        return
    except ET.ParseError as e:
        print(f"Error parsing XML file: {e}")
        showInfo(f"Error: Invalid XML format in kanjidic2_light.xml")
        return
    except Exception as e:
        print(f"Unexpected error loading kanji readings: {e}")
        showInfo(f"Error loading kanji data: {str(e)}")
        return

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

def extract_kana_units(text):
    """Extract individual kana units, treating combinations like ちゃ, きゅ as single units."""
    small_kana = {'ゃ', 'ゅ', 'ょ', 'ぁ', 'ぃ', 'ぅ', 'ぇ', 'ぉ', 'っ', 'ァ', 'ィ', 'ゥ', 'ェ', 'ォ', 'ャ', 'ュ', 'ョ', 'ッ'}

    units = []
    i = 0
    while i < len(text):
        # Check if next character is a small kana (part of current unit)
        if i + 1 < len(text) and text[i + 1] in small_kana:
            units.append(text[i:i+2])  # Include both characters as one unit
            i += 2
        else:
            units.append(text[i])  # Single character unit
            i += 1

    return units

def get_base_reading_for_rendaku(reading, possible_readings):
    """Find the base reading for a rendaku form, if applicable."""
    # Common rendaku transformations (voiced -> unvoiced)
    reverse_rendaku_map = {
        'が': 'か', 'ぎ': 'き', 'ぐ': 'く', 'げ': 'け', 'ご': 'こ',
        'ざ': 'さ', 'じ': 'し', 'ず': 'す', 'ぜ': 'せ', 'ぞ': 'そ',
        'だ': 'た', 'ぢ': 'ち', 'づ': 'つ', 'で': 'て', 'ど': 'と',
        'ば': 'は', 'び': 'ひ', 'ぶ': 'ふ', 'べ': 'へ', 'ぼ': 'ほ',
        # Add complete p→f reverse transformations for all p-sounds
        'ぷ': 'ふ', 'ぱ': 'ふぁ', 'ぴ': 'ふぃ', 'ぺ': 'ふぇ', 'ぽ': 'ふぉ',
        # Add p→h reverse transformations (alternative to b→h)
        # Note: ぱ is handled above as ふぁ, but we also need direct p→h for cases like ぽう→ほう
        'ぱ': 'は', 'ぴ': 'ひ', 'ぽ': 'ほ', 'ぺ': 'へ'
    }

    # Check if the reading is a rendaku form
    first_char = reading[0]
    if first_char in reverse_rendaku_map:
        # Get the base reading by replacing the first character with its unvoiced counterpart
        base_reading = reverse_rendaku_map[first_char] + reading[1:]

        # Ensure the base reading is a valid reading for this kanji
        if base_reading in possible_readings:
            return base_reading

    return None
