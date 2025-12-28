"""
Word Parser module - Parsing kanji and readings from text.

This module handles:
- Extracting kanji from text
- Converting between field formats (single vs. two-field)
- Parsing kanji-reading pairs from furigana text
- Splitting compound words into individual kanji-reading pairs
- Counting kanji and kana characters
"""

import re
from .dictionary import expand_iteration_marks, extract_kanji_only


def get_kanji_set(text):
    """Extract kanji from text (Unicode range for CJK Unified Ideographs)."""
    return set([char for char in text if '\u4e00' <= char <= '\u9fff'])


def count_kanji_in_text(text):
    """Count the number of kanji characters in text (excluding furigana)."""
    # Extract text without furigana brackets
    text_no_furigana = re.sub(r'\[.*?\]', '', text)
    kanji_count = sum(1 for char in text_no_furigana if '\u4e00' <= char <= '\u9fff')
    return kanji_count


def count_kana_in_text(text):
    """Count the number of kana characters (hiragana + katakana) in text (excluding furigana)."""
    text_no_furigana = re.sub(r'\[.*?\]', '', text)
    kana_count = sum(1 for char in text_no_furigana
                     if ('\u3040' <= char <= '\u309f') or  # Hiragana
                        ('\u30a0' <= char <= '\u30ff'))    # Katakana
    return kana_count


def is_kana(char):
    """Check if character is hiragana or katakana."""
    return ('\u3040' <= char <= '\u309f') or ('\u30a0' <= char <= '\u30ff')

def is_kanji(char):
    """Check if character is kanji."""
    return '\u4e00' <= char <= '\u9fff'

def convert_two_fields_to_furigana(kanji_text, reading_text):
    """
    Convert two-field format to furigana format, aligning kana and adding furigana only for kanji.

    Args:
        kanji_text: Text with kanji (e.g., "とけ込む")
        reading_text: Full reading (e.g., "とけこむ")

    Returns:
        Text in furigana format (e.g., "とけ 込[こ]む")
        If kanji_text has no kanji, returns just the kanji_text without brackets
    """
    if not kanji_text or not reading_text:
        return kanji_text or ""

    if not any(is_kanji(c) for c in kanji_text):
        return kanji_text

    result = []
    k_idx = 0
    r_idx = 0

    while k_idx < len(kanji_text):
        if is_kana(kanji_text[k_idx]):
            kana_segment = []
            while k_idx < len(kanji_text) and is_kana(kanji_text[k_idx]):
                kana_segment.append(kanji_text[k_idx])
                k_idx += 1

            kana_str = ''.join(kana_segment)
            if r_idx < len(reading_text) and reading_text[r_idx:r_idx+len(kana_str)] == kana_str:
                if result and not result[-1].endswith(']'):
                    result.append(' ')
                result.append(kana_str)
                r_idx += len(kana_str)
            else:
                result.append(kanji_text[k_idx-len(kana_segment):k_idx])

        elif is_kanji(kanji_text[k_idx]):
            kanji_segment = []
            while k_idx < len(kanji_text) and is_kanji(kanji_text[k_idx]):
                kanji_segment.append(kanji_text[k_idx])
                k_idx += 1

            next_kana_in_kanji = []
            temp_idx = k_idx
            while temp_idx < len(kanji_text) and is_kana(kanji_text[temp_idx]):
                next_kana_in_kanji.append(kanji_text[temp_idx])
                temp_idx += 1

            next_kana_str = ''.join(next_kana_in_kanji)

            if next_kana_str:
                next_kana_pos = reading_text.find(next_kana_str, r_idx + 1)
                if next_kana_pos != -1:
                    kanji_reading = reading_text[r_idx:next_kana_pos]
                    r_idx = next_kana_pos + len(next_kana_str)
                else:
                    kanji_reading = reading_text[r_idx:-len(next_kana_str)] if len(reading_text) - r_idx > len(next_kana_str) else reading_text[r_idx:]
                    r_idx = len(reading_text)
            else:
                kanji_reading = reading_text[r_idx:]
                r_idx = len(reading_text)

            kanji_str = ''.join(kanji_segment)
            if result and not result[-1].endswith(' '):
                result.append(' ')
            result.append(f"{kanji_str}[{kanji_reading}]")

            if next_kana_str:
                result.append(next_kana_str)
                k_idx = temp_idx
        else:
            result.append(kanji_text[k_idx])
            k_idx += 1

    return ''.join(result)


def fuzzy_reading_match(kanjidic_reading, actual_reading):
    """
    Match readings with fuzzy logic to handle sokuon and other variations.

    Returns:
        Tuple of (matched_actual, matched_kanjidic) if match found, None otherwise
    """
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

    return None


def is_rendaku_of(reading, base_reading):
    """Check if reading is the rendaku form of base_reading."""
    if not reading or not base_reading:
        return False

    # Rendaku mappings (inverse of the normal map)
    rendaku_inverse = {
        'が': 'か', 'ぎ': 'き', 'ぐ': 'く', 'げ': 'け', 'ご': 'こ',
        'ざ': 'さ', 'じ': 'し', 'ず': 'す', 'ぜ': 'せ', 'ぞ': 'そ',
        'だ': 'た', 'ぢ': 'ち', 'づ': 'つ', 'で': 'て', 'ど': 'と',
        'ば': 'は', 'び': 'ひ', 'ぶ': 'ふ', 'べ': 'へ', 'ぼ': 'ほ',
    }

    first_char = reading[0]
    if first_char in rendaku_inverse:
        unvoiced = rendaku_inverse[first_char] + reading[1:]
        return unvoiced == base_reading

    return False


def is_handakuon_of(reading, base_reading):
    """Check if reading is the handakuon (p-sound) form of base_reading.

    Handakuon: は/ひ/ふ/へ/ほ → ぱ/ぴ/ぷ/ぺ/ぽ
    Example: ぴょう is handakuon of ひょう
    """
    if not reading or not base_reading:
        return False

    # Handakuon mappings (inverse: p-sound → h-sound)
    handakuon_inverse = {
        'ぱ': 'は', 'ぴ': 'ひ', 'ぷ': 'ふ', 'ぺ': 'へ', 'ぽ': 'ほ',
    }

    first_char = reading[0]
    if first_char in handakuon_inverse:
        h_version = handakuon_inverse[first_char] + reading[1:]
        return h_version == base_reading

    return False


def extract_actual_readings(kanji_word, reading, kanji_readings):
    """Extract actual readings for each kanji from the furigana text.

    For "当[あ]たり", returns [('当', 'あ')] - the actual reading, not dictionary base readings.
    For "時々[ときどき]", returns [('時', 'とき'), ('時', 'とき')] - normalizes どき to とき.
    Uses the dictionary to find valid matches but returns normalized base readings.
    """
    # Find positions of kanji in the word
    kanji_positions = []
    for i, char in enumerate(kanji_word):
        if '\u4e00' <= char <= '\u9fff':
            kanji_positions.append((i, char))

    if not kanji_positions:
        return []

    pairs = []
    reading_index = 0

    for pos_idx, (kanji_pos, kanji) in enumerate(kanji_positions):
        if kanji not in kanji_readings:
            # Unknown kanji, skip
            continue

        # Skip any kana in the reading that corresponds to kana in the kanji_word
        if pos_idx > 0:
            prev_kanji_pos = kanji_positions[pos_idx - 1][0]
            # Check for kana between previous kanji and current kanji
            kana_between_start = prev_kanji_pos + 1
            kana_between_end = kanji_pos
            if kana_between_end > kana_between_start:
                # There's kana between the kanji
                kana_text = kanji_word[kana_between_start:kana_between_end]
                # Skip this kana in the reading
                if reading[reading_index:reading_index + len(kana_text)] == kana_text:
                    reading_index += len(kana_text)

        possible_readings = kanji_readings[kanji]
        remaining_reading = reading[reading_index:]

        if not remaining_reading:
            break

        # Find the longest matching reading from the dictionary
        best_match_extended = None
        best_match_base = None
        best_match_length = 0

        for base_reading in possible_readings:
            for extended_reading in possible_readings[base_reading]:
                if remaining_reading.startswith(extended_reading):
                    if len(extended_reading) > best_match_length:
                        best_match_extended = extended_reading
                        best_match_base = base_reading
                        best_match_length = len(extended_reading)

        if best_match_base:
            # Extract the kanji reading part (without okurigana)
            if '.' in best_match_base:
                kanji_reading_part = best_match_base.split('.')[0]
                actual_reading = remaining_reading[:len(kanji_reading_part)]
            else:
                # No okurigana, use the full reading
                kanji_reading_part = best_match_base
                actual_reading = remaining_reading[:len(best_match_base)]

            # Normalize rendaku and handakuon: convert to base form
            # BUT only if the actual_reading is NOT a valid base reading itself
            # Examples:
            #   - どき→とき (rendaku, どき not in dictionary)
            #   - ぴょう→ひょう (handakuon, ぴょう not in dictionary)
            #   - だい stays だい (だい is valid on-yomi)
            normalized_reading = actual_reading

            # Check rendaku normalization
            if is_rendaku_of(actual_reading, kanji_reading_part):
                if actual_reading not in possible_readings:
                    normalized_reading = kanji_reading_part
            # Check handakuon normalization
            elif is_handakuon_of(actual_reading, kanji_reading_part):
                if actual_reading not in possible_readings:
                    normalized_reading = kanji_reading_part

            pairs.append((kanji, normalized_reading))
            reading_index += best_match_length
        else:
            # Try fuzzy matching
            for base_reading in possible_readings:
                if fuzzy := fuzzy_reading_match(base_reading, remaining_reading):
                    matched_actual, matched_kanjidic = fuzzy
                    pairs.append((kanji, matched_kanjidic))  # Use base form from dictionary
                    reading_index += len(matched_actual)
                    break

    return pairs


def split_reading_with_positions(kanji_word, reading, kanji_readings):
    """Split reading by mapping kanji positions to reading segments."""
    # Find positions of kanji in the original word
    kanji_positions = []
    kanji_chars = []

    for i, char in enumerate(kanji_word):
        if '\u4e00' <= char <= '\u9fff':  # Is kanji
            kanji_positions.append(i)
            kanji_chars.append(char)

    # Fallback to original position-based matching
    pairs = []
    reading_index = 0
    last_extended_reading_matched = ""

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
            kanji_word_chars_left = len(kanji_word) - pos  # We might have covered some next kanji with longer readings like ゆめ.みる
            reading_index = min(reading_index + max_new_pairs_size, len(reading) - kanji_word_chars_left) + kana_between
        max_new_pairs_size = 0

        # Find the best matching reading for this kanji
        possible_readings = kanji_readings[kanji]

        remaining_reading = reading[reading_index:]

        # Add ALL matching base readings (not just the longest)
        exact_match_found = False
        for (base_reading, extended_reading) in [(base_reading, extended_reading)
                               for base_reading in possible_readings
                               for extended_reading in possible_readings[base_reading]]:

            if remaining_reading.startswith(extended_reading):
                # Store the base reading
                pairs.append((kanji, base_reading))
                max_new_pairs_size = max(max_new_pairs_size, len(extended_reading))
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
            # For single kanji, use base reading only (original format)
            kanji_pairs.add(f"{kanji_word}[{reading}]")
            processed_kanji.add(kanji_word)
        else:
            # Handle 々 (iteration mark) by expanding it to repeat the previous kanji
            expanded_kanji_word = expand_iteration_marks(kanji_word)

            # Extract only kanji characters from compound word (after expansion)
            kanji_chars = extract_kanji_only(expanded_kanji_word)

            # Extract actual readings from the furigana text (not dictionary readings)
            reading_parts = extract_actual_readings(expanded_kanji_word, reading, kanji_readings)
            if reading_parts:
                # For repeated kanji (when 々 is used), only add unique kanji-reading pairs
                unique_pairs = set()
                for kanji, actual_reading in reading_parts:
                    unique_pairs.add((kanji, actual_reading))

                for kanji, actual_reading in unique_pairs:
                    # Use actual reading from the text
                    kanji_pairs.add(f"{kanji}[{actual_reading}]")
                    processed_kanji.add(kanji)
            else:
                # If splitting fails, add individual kanji with empty readings
                unique_kanji = set(kanji_chars)  # Remove duplicates
                for kanji in unique_kanji:
                    kanji_pairs.add(f"{kanji}[]")
                    processed_kanji.add(kanji)

    # Handle standalone kanji without readings
    for char in text:
        if '\u4e00' <= char <= '\u9fff' and char not in processed_kanji:
            kanji_pairs.add(f"{char}[]")

    return kanji_pairs
