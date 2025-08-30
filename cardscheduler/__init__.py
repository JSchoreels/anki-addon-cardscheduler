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
    pattern = r'([一-龯ぁ-ゖァ-ヺー々]+)\[([ぁ-ゖァ-ヺー]+)\]([ぁ-ゖァ-ヺー]*)'  # Add 々 to the pattern
    matches = re.findall(pattern, text)

    processed_kanji = set()
    for kanji_word, reading, conjugation in matches:
        kanji_word = kanji_word + conjugation
        reading = reading + conjugation  # Combine reading and conjugation for full reading
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

    # Fallback to original position-based matching
    pairs = []
    reading_index = 0

    for i, (pos, kanji) in enumerate(zip(kanji_positions, kanji_chars)):
        if i == 0:
            # First kanji: reading starts from beginning
            reading_index = 0
        else:
            # Calculate how much kana is between previous kanji and this one
            prev_kanji_pos = kanji_positions[i-1]
            kana_between = pos - prev_kanji_pos - 1
            if kana_between > 0:
                if last_extended_reading_matched[1:] == kanji_word[prev_kanji_pos+1:prev_kanji_pos+1+len(last_extended_reading_matched[1:])]:
                    kana_between -= len(last_extended_reading_matched[1:])
                # for i_kana_matched in range(1, len(last_extended_reading_matched)):
                #     if last_extended_reading_matched[i_kana_matched] == kanji_word[prev_kanji_pos + i_kana_matched]:
                #         kana_between -= 1
            kanji_word_chars_left = len(kanji_word) - pos  # We might have covered some next kanji with longer readings like ゆめ.みる
            reading_index = min(reading_index + max_new_pairs_size, len(reading) - kanji_word_chars_left) + kana_between
        max_new_pairs_size = 0

        # Find the best matching reading for this kanji
        possible_readings = kanji_readings[kanji]

        remaining_reading = reading[reading_index:]

        exact_match_found = False
        for (base_reading, extended_reading) in [(base_reading, extended_reading)
                               for base_reading in possible_readings
                               for extended_reading in possible_readings[base_reading]]:

            if remaining_reading.startswith(extended_reading):
                pairs.append((kanji, base_reading))
                if len(extended_reading) > max_new_pairs_size:
                    max_new_pairs_size = len(extended_reading)
                    last_extended_reading_matched = extended_reading
                exact_match_found = True

        # Try fuzzy matching with length restrictions
        if not exact_match_found:
            for reading_option in possible_readings:
                if (fuzzy := fuzzy_reading_match(reading_option, remaining_reading)):
                    matched_actual, matched_kanjidic = fuzzy
                    pairs.append((kanji, matched_kanjidic))
                    max_new_pairs_size = max(max_new_pairs_size, len(reading_option))


    return pairs

def try_balanced_split(kanji_chars, reading, kanji_readings):
    """Try to create a balanced split of the reading among kanji characters."""
    if len(kanji_chars) == 2:
        # For 2-kanji compounds, try various split points
        for split_point in range(1, len(reading)):
            first_part = reading[:split_point]
            second_part = reading[split_point:]

            # Skip very unbalanced splits (one part much longer than the other)
            if len(first_part) > len(second_part) * 3 or len(second_part) > len(first_part) * 3:
                continue

            # Check if both parts are valid readings for their respective kanji
            first_kanji_readings = []
            second_kanji_readings = []
            if kanji_chars[0] in kanji_readings:
                for v in kanji_readings[kanji_chars[0]].values():
                    first_kanji_readings.extend(v)
            if kanji_chars[1] in kanji_readings:
                for v in kanji_readings[kanji_chars[1]].values():
                    second_kanji_readings.extend(v)

            # Try exact matches first
            first_exact_reading = None
            second_exact_reading = None

            # Find the base dictionary reading for first part
            if first_part in first_kanji_readings:
                # If the segment is directly in dictionary, check if there's a shorter base form
                shorter_readings = [r for r in first_kanji_readings if len(r) < len(first_part) and first_part.startswith(r)]
                if shorter_readings:
                    first_exact_reading = min(shorter_readings, key=len)
                else:
                    first_exact_reading = first_part
            else:
                # Check for rendaku form - find base reading
                base_reading = get_base_reading_for_rendaku(first_part, first_kanji_readings)
                if base_reading:
                    first_exact_reading = base_reading

            # Find the base dictionary reading for second part
            if second_part in second_kanji_readings:
                # If the segment is directly in dictionary, check if there's a shorter base form
                shorter_readings = [r for r in second_kanji_readings if len(r) < len(second_part) and second_part.startswith(r)]
                if shorter_readings:
                    second_exact_reading = min(shorter_readings, key=len)
                else:
                    # Check if it's a rendaku form and find the base reading
                    base_reading = get_base_reading_for_rendaku(second_part, second_kanji_readings)
                    second_exact_reading = base_reading if base_reading else second_part
            else:
                # Check for rendaku form - find base reading
                base_reading = get_base_reading_for_rendaku(second_part, second_kanji_readings)
                if base_reading:
                    second_exact_reading = base_reading

            if first_exact_reading and second_exact_reading:
                return [(kanji_chars[0], first_exact_reading), (kanji_chars[1], second_exact_reading)]

            # Try fuzzy matches
            first_fuzzy = None
            second_fuzzy = None

            for reading_option in first_kanji_readings:
                if (fuzzy := fuzzy_reading_match(reading_option, first_part)):
                    if fuzzy[0] == first_part:  # Exact length match
                        first_fuzzy = reading_option
                        break

            for reading_option in second_kanji_readings:
                if (fuzzy := fuzzy_reading_match(reading_option, second_part)):
                    if fuzzy[0] == second_part:  # Exact length match
                        second_fuzzy = reading_option
                        break

            # Accept fuzzy match only if at least one is exact
            if (first_exact_reading and second_fuzzy) or (first_fuzzy and second_exact_reading):
                return [(kanji_chars[0], first_fuzzy or first_exact_reading), (kanji_chars[1], second_fuzzy or second_exact_reading)]

    elif len(kanji_chars) == 3:
        # For 3-kanji compounds, try balanced splits
        total_length = len(reading)

        # Try splits that give each kanji roughly equal portions (1-3 kana each)
        for first_len in range(1, min(4, total_length - 1)):
            for second_len in range(1, min(4, total_length - first_len)):
                third_len = total_length - first_len - second_len
                if third_len < 1 or third_len > 4:
                    continue

                # Skip very unbalanced splits
                lengths = [first_len, second_len, third_len]
                if max(lengths) > min(lengths) * 3:
                    continue

                first_part = reading[:first_len]
                second_part = reading[first_len:first_len + second_len]
                third_part = reading[first_len + second_len:]

                # Find base dictionary readings for each part
                first_dict_reading = None
                second_dict_reading = None
                third_dict_reading = None

                # Check first part
                first_kanji_readings = []
                second_kanji_readings = []
                third_kanji_readings = []
                if kanji_chars[0] in kanji_readings:
                    for v in kanji_readings[kanji_chars[0]].values():
                        first_kanji_readings.extend(v)
                if kanji_chars[1] in kanji_readings:
                    for v in kanji_readings[kanji_chars[1]].values():
                        second_kanji_readings.extend(v)
                if kanji_chars[2] in kanji_readings:
                    for v in kanji_readings[kanji_chars[2]].values():
                        third_kanji_readings.extend(v)
                if first_part in first_kanji_readings:
                    first_dict_reading = first_part
                else:
                    base_reading = get_base_reading_for_rendaku(first_part, kanji_readings.get(kanji_chars[0], []))
                    if base_reading:
                        first_dict_reading = base_reading

                # Check second part
                if second_part in second_kanji_readings:
                    second_dict_reading = second_part
                else:
                    base_reading = get_base_reading_for_rendaku(second_part, kanji_readings.get(kanji_chars[1], []))
                    if base_reading:
                        second_dict_reading = base_reading

                # Check third part
                if third_part in third_kanji_readings:
                    third_dict_reading = third_part
                else:
                    base_reading = get_base_reading_for_rendaku(third_part, kanji_readings.get(kanji_chars[2], []))
                    if base_reading:
                        third_dict_reading = base_reading

                if first_dict_reading and second_dict_reading and third_dict_reading:
                    return [(kanji_chars[0], first_dict_reading), (kanji_chars[1], second_dict_reading), (kanji_chars[2], third_dict_reading)]

    return None

def split_reading(kanji_chars, reading, kanji_readings):
    # Simple case: if number of kanji equals number of kana units, try 1:1 mapping with validation
    if len(kanji_chars) == count_kana_units(reading):
        pairs = []
        kana_units = extract_kana_units(reading)

        # Check if we can map each segment to a base dictionary reading
        valid_mapping = True
        base_readings = []

        for i, kanji in enumerate(kanji_chars):
            kana_unit = kana_units[i]
            possible_readings = []
            if kanji in kanji_readings:
                for v in kanji_readings[kanji].values():
                    possible_readings.extend(v)

            base_reading = None

            # First check if it's directly in the dictionary
            if kana_unit in possible_readings:
                # If the segment is directly in dictionary, check if there's a shorter base form
                # This handles cases like ふみ -> ふ, しに -> し, きり -> き
                shorter_readings = [r for r in possible_readings if len(r) < len(kana_unit) and kana_unit.startswith(r)]
                if shorter_readings:
                    # Use the shortest matching base reading
                    base_reading = min(shorter_readings, key=len)
                else:
                    base_reading = kana_unit
            else:
                # Check if it's a rendaku form and find the base reading
                rendaku_base = get_base_reading_for_rendaku(kana_unit, possible_readings)
                if rendaku_base:
                    base_reading = rendaku_base
                else:
                    # Try fuzzy matching to find the dictionary reading
                    for reading_option in possible_readings:
                        if (fuzzy := fuzzy_reading_match(reading_option, kana_unit)):
                            if fuzzy[0] == kana_unit:  # Exact length match
                                base_reading = reading_option
                                break

            if base_reading:
                base_readings.append(base_reading)
            else:
                valid_mapping = False
                break

        # If we found base readings for all segments, use them
        if valid_mapping:
            for i, kanji in enumerate(kanji_chars):
                pairs.append((kanji, base_readings[i]))
            return pairs

    # Complex case: try to match against dictionary readings (handles sokuon transformations)
    remaining_reading = reading
    pairs = []

    for kanji in kanji_chars:
        found_match = False
        possible_readings = []
        if kanji in kanji_readings:
            for v in kanji_readings[kanji].values():
                possible_readings.extend(v)
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
            kana_unit = kana_units[i]
            possible_readings = []
            if kanji in kanji_readings:
                for v in kanji_readings[kanji].values():
                    possible_readings.extend(v)

            # Try to find the base dictionary reading that corresponds to this segment
            base_reading = None

            # First check if it's directly in the dictionary
            if kana_unit in possible_readings:
                base_reading = kana_unit
            else:
                # Check if it's a rendaku form and find the base reading
                base_reading = get_base_reading_for_rendaku(kana_unit, possible_readings)
                if not base_reading:
                    # Try fuzzy matching to find the dictionary reading
                    for reading_option in possible_readings:
                        if (fuzzy := fuzzy_reading_match(reading_option, kana_unit)):
                            if fuzzy[0] == kana_unit:  # Exact length match
                                base_reading = reading_option
                                break

            # Use the base reading if found, otherwise fall back to the segment
            pairs.append((kanji, base_reading if base_reading else kana_unit))
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
    # Handle leading sokuon: っちゃ should match ちゃ
    # But only if the lengths are reasonable (within 1-2 characters difference)
    while actual_reading.startswith('っ'):
        actual_reading = actual_reading[1:]

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
        h_to_p_single = {
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
            if first_kanjidic in h_to_p_single and first_actual == h_to_p_single[first_kanjidic]:
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
    """Load kanji readings from kanjidic2_light.xml into a dictionary.
    For each kanji, map verb_kanji_part reading to a list of all its variations."""
    kanji_readings = {}
    tree = ET.parse(xml_file)
    root = tree.getroot()

    for character in root.findall('character'):
        kanji = character.find('literal').text
        readings_map = {}

        # Get kun'yomi readings (Japanese readings)
        for reading in character.findall('ja_kun'):
            reading_text = reading.text
            if reading_text:
                variations = []
                # For readings with dots, generate verb forms
                if not '.' in reading_text:
                    variations.append(reading_text)
                else:
                    cleaned_text = reading_text.replace('-', '')
                    verb_kanji_part, verb_kana_part = cleaned_text.split('.', 1)
                    full_verb = verb_kanji_part + verb_kana_part
                    if verb_kana_part:
                        if verb_kana_part.endswith(('う', 'く', 'む', 'ぬ', 'る', 'つ', 'す', 'ぐ', 'ぶ')):
                            # -i form (masu-stem)
                            i_stem = verb_kanji_part + get_i_stem_ending(verb_kana_part)
                            if i_stem != verb_kanji_part:
                                variations.append(i_stem)
                            # Intermediate form (remove final る)
                            intermediate = verb_kanji_part + verb_kana_part[:-1]
                            if intermediate not in variations:
                                variations.append(intermediate)
                        if verb_kana_part.endswith(('い')):
                            # Intermediate form (remove final い)
                            intermediate = verb_kanji_part + verb_kana_part[:-1]
                            if intermediate not in variations:
                                variations.append(intermediate)
                        if full_verb != verb_kanji_part:
                            variations.append(full_verb)

                # Add rendaku variations
                rendaku_variations = []
                for variation in variations:
                    rendaku_form = get_rendaku_form(variation)
                    if rendaku_form:
                        rendaku_variations.append(rendaku_form)
                    rendaku_form_p = get_rendaku_form_p(variation)
                    if rendaku_form_p:
                        rendaku_variations.append(rendaku_form_p)
                variations.extend(rendaku_variations)

                readings_map[reading_text] = variations

        # Get on'yomi readings (Chinese readings)
        for reading in character.findall('ja_on'):
            reading_text = reading.text
            if reading_text:
                hiragana = katakana_to_hiragana(reading_text)
                variations = [hiragana]
                rendaku_form = get_rendaku_form(hiragana)
                if rendaku_form:
                    variations.append(rendaku_form)
                rendaku_form_p = get_rendaku_form_p(hiragana)
                if rendaku_form_p:
                    variations.append(rendaku_form_p)
                readings_map[reading_text] = variations

        kanji_readings[kanji] = readings_map
    return kanji_readings

def get_i_stem_ending(verb_ending):
    """Convert u-ending verb form to i-stem form for compound words."""
    # Map common verb endings to their i-stem forms
    u_to_i_map = {
        'む': 'み',  # ふ.む -> ふみ
        'ぬ': 'に',  # し.ぬ -> しに
        'く': 'き',  # い.く -> いき, 行く -> 行き
        'ぐ': 'ぎ',  # およ.ぐ -> およぎ
        'ぶ': 'び',  # よ.ぶ -> よび
        'す': 'し',  # はな.す -> はなし
        'つ': 'ち',  # た.つ -> たち
        'う': 'い',  # か.う -> かい
        'る': 'り',  # あ.る -> あり (though this is irregular)
    }

    if verb_ending and verb_ending[-1] in u_to_i_map:
        return verb_ending[:-1] + u_to_i_map[verb_ending[-1]]
    return verb_ending

def get_rendaku_form(reading):
    """Generate rendaku (sequential voicing) form of a reading if applicable."""
    if not reading:
        return None

    # Basic rendaku transformations
    rendaku_map = {
        'か': 'が', 'き': 'ぎ', 'く': 'ぐ', 'け': 'げ', 'こ': 'ご',
        'さ': 'ざ', 'し': 'じ', 'す': 'ず', 'せ': 'ぜ', 'そ': 'ぞ',
        'た': 'だ', 'ち': 'ぢ', 'つ': 'づ', 'て': 'で', 'と': 'ど',
        'は': 'ば', 'ひ': 'び', 'ふ': 'ぶ', 'へ': 'べ', 'ほ': 'ぼ',
    }

    first_char = reading[0]
    if first_char in rendaku_map:
        return rendaku_map[first_char] + reading[1:]

    return None

def get_rendaku_form_p(reading):
    """Generate rendaku (sequential voicing) form of a reading if applicable."""
    if not reading:
        return None

    # Basic rendaku transformations
    rendaku_map = {
        'は': 'ぱ', 'ひ': 'ぴ', 'ふ': 'ぷ', 'へ': 'ぺ', 'ほ': '',
    }

    first_char = reading[0]
    if first_char in rendaku_map:
        return rendaku_map[first_char] + reading[1:]

    return None

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
    # possible_readings may be a list of lists, flatten if needed
    if isinstance(possible_readings, dict):
        all_readings = []
        for v in possible_readings.values():
            all_readings.extend(v)
        possible_readings = all_readings

    # Common rendaku transformations (voiced -> unvoiced)
    reverse_rendaku_map = {
        'が': 'か', 'ぎ': 'き', 'ぐ': 'く', 'げ': 'け', 'ご': 'こ',
        'ざ': 'さ', 'じ': 'し', 'ず': 'す', 'ぜ': 'せ', 'ぞ': 'そ',
        'だ': 'た', 'ぢ': 'ち', 'づ': 'つ', 'で': 'て', 'ど': 'と',
        'ば': 'は', 'び': 'ひ', 'ぶ': 'ふ', 'べ': 'へ', 'ぼ': 'ほ',
        # p→h reverse transformations
        'ぱ': 'は', 'ぴ': 'ひ', 'ぷ': 'ふ', 'ぺ': 'へ', 'ぽ': 'ほ'
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
