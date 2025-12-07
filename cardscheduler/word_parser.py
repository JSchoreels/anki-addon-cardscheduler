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


def convert_two_fields_to_furigana(kanji_text, reading_text):
    """
    Convert two-field format (separate kanji and reading) to single-field furigana format.

    Args:
        kanji_text: Text with kanji (e.g., "頭が痛い")
        reading_text: Full reading (e.g., "あたまがいたい")

    Returns:
        Text in furigana format (e.g., "頭が痛い[あたまがいたい]")
        If kanji_text has no kanji, returns just the kanji_text without brackets
    """
    if not kanji_text or not reading_text:
        return kanji_text or ""

    # Check if kanji_text contains any kanji characters
    has_kanji = any('\u4e00' <= c <= '\u9fff' for c in kanji_text)

    if not has_kanji:
        # No kanji in the text, just return the text without brackets
        return kanji_text
    else:
        # Has kanji, append the reading in brackets
        return f"{kanji_text}[{reading_text}]"


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

    # Handle standalone kanji without readings
    for char in text:
        if '\u4e00' <= char <= '\u9fff' and char not in processed_kanji:
            kanji_pairs.add(f"{char}[]")

    return kanji_pairs
