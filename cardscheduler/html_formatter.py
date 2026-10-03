"""
HTML formatting module - Generate color-coded HTML for card display fields.

Handles:
- Color assignment for kanji
- Related words HTML generation
- Kanji meanings HTML generation
"""

import re

HIGHLIGHT_COLORS = [
    'lightgreen', 'lightblue', 'pink', 'lightyellow',
    'lightcoral', 'lightseagreen', 'plum', 'peachpuff'
]

# Furigana element: kanji (not kana) followed by [reading]
_FURIGANA_PATTERN = re.compile(r'([一-龯々]+)\[([ぁ-ゖァ-ヺー]+)\]')

# Kanji[reading] optionally followed by trailing kana, e.g. "同[おな]じ" or "同[おな]"
_KANJI_WITH_KANA = r'[一-龯々]+\[[ぁ-ゖァ-ヺー]+\][ぁ-ゖァ-ヺー]*'
# Plain kana (hiragana/katakana)
_KANA = r'[ぁ-ゖァ-ヺー]+'
_KANA_SPACE_KANJI_PATTERN = re.compile(rf'({_KANA})\s+({_KANJI_WITH_KANA})')
_KANJI_SPACE_KANA_PATTERN = re.compile(rf'({_KANJI_WITH_KANA})\s+({_KANA})')


class HighlightCache:
    """Memoized highlighting results, valid for a single kanji_readings dict.

    Related words repeat heavily across cards, so sharing one cache while
    formatting a whole collection avoids re-highlighting the same text.
    """

    def __init__(self):
        self.highlighted = {}
        self.reading_parts = {}
        self.normalized = {}


def format_card_html(card_info, kanji_meanings, kanji_readings, cache=None):
    """Generate all HTML for a card's display fields.

    Args:
        card_info: CardInfo object with related_cards_known/unknown lists
        kanji_meanings: Dict {kanji: [meanings]}
        kanji_readings: Dict {kanji: {reading: [variations]}}
        cache: Optional HighlightCache shared across cards using the same kanji_readings

    Returns:
        Tuple of (related_known_html, related_unknown_html, meanings_html)
    """
    # Order of first appearance keeps colors stable between runs; set order
    # varies with Python's per-process string hashing.
    current_kanji = dict.fromkeys(
        c for c in card_info.furigana_text if '\u4e00' <= c <= '\u9fff'
    )

    kanji_to_color = {
        kanji: HIGHLIGHT_COLORS[i % len(HIGHLIGHT_COLORS)]
        for i, kanji in enumerate(current_kanji)
    }

    if cache is None:
        cache = HighlightCache()

    related_known_html = _format_related_words(
        card_info.related_cards_known,
        kanji_to_color,
        kanji_readings,
        cache,
    )

    related_unknown_html = _format_related_words(
        card_info.related_cards_unknown,
        kanji_to_color,
        kanji_readings,
        cache,
    )

    meanings_html = _format_kanji_meanings(
        card_info.furigana_text,
        kanji_to_color,
        kanji_meanings
    )

    return (related_known_html, related_unknown_html, meanings_html)


def _format_related_words(related_cards_list, kanji_to_color, kanji_readings, cache=None):
    """Format list of (CardInfo, shared_kanji) tuples into HTML.

    Args:
        related_cards_list: List of (CardInfo, shared_kanji_set) tuples
        kanji_to_color: Dict mapping kanji to colors
        kanji_readings: Dict for highlighting
        cache: Optional HighlightCache shared across calls

    Returns:
        HTML string with color-coded related words
    """
    if not related_cards_list:
        return ""

    if cache is None:
        cache = HighlightCache()

    html_parts = []
    for related_card, shared_kanji in related_cards_list:
        if len(shared_kanji) == 1:
            # Most related cards share a single kanji; skip building a frozenset key
            for kanji in shared_kanji:
                color = kanji_to_color.get(kanji)
            if color is None:
                shared_colors = {}
                cache_key = (related_card.furigana_text, frozenset())
            else:
                shared_colors = {kanji: color}
                cache_key = (related_card.furigana_text, kanji, color)
        else:
            shared_colors = {
                kanji: kanji_to_color.get(kanji)
                for kanji in shared_kanji
                if kanji in kanji_to_color
            }
            cache_key = (related_card.furigana_text, frozenset(shared_colors.items()))

        highlighted = cache.highlighted.get(cache_key)
        if highlighted is None:
            # Normalize spacing before highlighting
            normalized_text = cache.normalized.get(related_card.furigana_text)
            if normalized_text is None:
                normalized_text = _normalize_spacing(related_card.furigana_text)
                cache.normalized[related_card.furigana_text] = normalized_text

            highlighted = _highlight_shared_kanji(
                normalized_text,
                shared_colors,
                kanji_readings,
                cache,
            )
            cache.highlighted[cache_key] = highlighted

        html_parts.append(highlighted)

    return ',　 '.join(html_parts)


def _normalize_spacing(furigana_text):
    """Remove unnecessary spaces in furigana text.

    Rules:
    - Remove space between kana and kanji[reading] (e.g., "と 同[おな]じ" → "と同[おな]じ")
    - Remove space between kanji[reading]+kana and kana (e.g., "同[おな]じ ように" → "同[おな]じように")
    - Keep spaces between kanji[reading] and kanji[reading] (different words)

    Args:
        furigana_text: Text with potential unnecessary spaces

    Returns:
        Text with normalized spacing
    """
    if not furigana_text:
        return furigana_text

    # Remove space between kana and kanji[reading]
    # Example: "と 同[おな]じ" → "と同[おな]じ"
    result = _KANA_SPACE_KANJI_PATTERN.sub(r'\1\2', furigana_text)

    # Remove space between kanji[reading](+kana) and kana
    # Example: "同[おな]じ ように" → "同[おな]じように"
    result = _KANJI_SPACE_KANA_PATTERN.sub(r'\1\2', result)

    return result


def _add_spacing_before_furigana(text):
    """Add regular space before furigana elements when needed.

    Rule: Add space ( ) before kanji[reading] pattern if the previous character is:
    - Japanese (kana or kanji)
    - NOT a delimiter (<, >, space, etc.)
    - NOT a non-Japanese character (Latin letters, numbers, etc.)

    Example: '</span>け合[あ]う' → '</span>け 合[あ]う'
    """
    if not text:
        return text

    result = []
    last_end = 0

    for match in _FURIGANA_PATTERN.finditer(text):
        # Get text before this furigana element
        before_text = text[last_end:match.start()]
        result.append(before_text)

        # Check the character immediately before this furigana element
        if before_text:
            last_char = before_text[-1]

            # Check if we need to add a space
            # Add space if last char is Japanese (kana/kanji) and not a delimiter
            is_kana = '\u3040' <= last_char <= '\u30ff'  # Hiragana or Katakana
            is_kanji = '\u4e00' <= last_char <= '\u9fff'  # Kanji
            is_delimiter = last_char in '<>　 '  # Common delimiters
            is_japanese = is_kana or is_kanji

            if is_japanese and not is_delimiter:
                result.append(' ')  # Add regular space

        # Add the furigana element itself
        result.append(match.group(0))
        last_end = match.end()

    # Add any remaining text
    if last_end < len(text):
        result.append(text[last_end:])

    return ''.join(result)


def _collapse_empty_readings_to_compound(reading_parts, full_reading):
    """Collapse kanji groups with empty readings into compound with full reading.

    When some kanji readings can't be found, instead of showing [ ] or scrambling
    the reading order, keep the full kanji compound with the full reading.
    This preserves the correct reading order.

    Example: 祖母[ばあ] where 祖 can't be matched → keep as 祖母[ばあ]
    instead of trying to split into 祖[?]母[ば] which would scramble the order.

    Args:
        reading_parts: List of (kanji, actual_reading, dictionary_form) tuples
        full_reading: The complete reading for the word

    Returns:
        If any empty readings: single tuple (all_kanji, full_reading, None)
        Otherwise: original reading_parts list
    """
    if not reading_parts:
        return reading_parts

    # Check if any readings are empty (space or empty string)
    has_empty = any(actual_reading.strip() == ""
                    for kanji, actual_reading, dictionary_form in reading_parts)

    if has_empty:
        # Collapse all kanji into a single compound with full reading
        all_kanji = ''.join(kanji for kanji, _, _ in reading_parts)
        return [(all_kanji, full_reading, None)]

    return reading_parts


def _highlight_shared_kanji(furigana_text, shared_kanji_colors, kanji_readings, cache=None):
    """Highlight kanji in furigana text that are in shared_kanji_colors.

    Preserves the full furigana text including trailing kana.
    """
    if not furigana_text or not shared_kanji_colors:
        return furigana_text

    # Parse the furigana text to extract all parts (kanji[reading] and plain kana)
    result = []
    last_end = 0

    for match in _FURIGANA_PATTERN.finditer(furigana_text):
        # Add any plain text before this match (trailing kana, etc.)
        if match.start() > last_end:
            result.append(furigana_text[last_end:match.start()])

        kanji_part = match.group(1)
        reading_part = match.group(2)

        # Extract individual kanji from kanji_part
        kanji_chars = [c for c in kanji_part if '\u4e00' <= c <= '\u9fff']

        if len(kanji_chars) == 1:
            # Single kanji - check if it should be highlighted
            if kanji_chars[0] in shared_kanji_colors:
                color = shared_kanji_colors[kanji_chars[0]]
                result.append(f'<span style="color: {color};">{kanji_part}[{reading_part}]</span>')
            else:
                result.append(f'{kanji_part}[{reading_part}]')
        else:
            # Multiple kanji - split into individual pairs and highlight each
            reading_parts = _split_compound_reading(
                kanji_part, reading_part, kanji_readings, cache
            )

            if reading_parts:

                # Highlight each kanji that's in shared colors
                pair_html = []
                for kanji, actual_reading, dictionary_form in reading_parts:
                    # Check if this is a compound (multiple kanji in single entry)
                    if len(kanji) > 1:
                        # Compound - check if any kanji in it are in shared colors
                        compound_kanji = [k for k in kanji if '\u4e00' <= k <= '\u9fff']
                        matching_kanji = [k for k in compound_kanji if k in shared_kanji_colors]

                        if matching_kanji:
                            # Use color of first matching kanji for the compound
                            color = shared_kanji_colors[matching_kanji[0]]
                            pair_html.append(f'<span style="color: {color};">{kanji}[{actual_reading}]</span>')
                        else:
                            pair_html.append(f'{kanji}[{actual_reading}]')
                    else:
                        # Single kanji - use actual reading from the text
                        if kanji in shared_kanji_colors:
                            color = shared_kanji_colors[kanji]
                            pair_html.append(f'<span style="color: {color};">{kanji}[{actual_reading}]</span>')
                        else:
                            pair_html.append(f'{kanji}[{actual_reading}]')
                result.append(''.join(pair_html))
            else:
                # Fallback if splitting failed
                result.append(f'{kanji_part}[{reading_part}]')

        last_end = match.end()

    # Add any remaining text after the last match
    if last_end < len(furigana_text):
        result.append(furigana_text[last_end:])

    # Join and add spacing before furigana elements when needed
    highlighted = ''.join(result)
    highlighted = _add_spacing_before_furigana(highlighted)

    return highlighted


def _restore_iteration_marks(kanji_part, reading_parts):
    """Show 々 as written (時々[ときどき]) instead of the kanji it repeats.

    Splitting runs on the expanded word (時時), so each 々 gets its own
    (kanji, reading) part; merge it back into the part before it.
    """
    if '々' not in kanji_part or len(reading_parts) != len(kanji_part):
        return reading_parts

    restored = []
    for char, part in zip(kanji_part, reading_parts):
        if char == '々' and restored:
            kanji, reading, dictionary_form = restored[-1]
            # Keep an unmatched reading blank so the compound still collapses
            if reading.strip() and part[1].strip():
                reading += part[1]
            else:
                reading = ' '
            restored[-1] = (kanji + char, reading, dictionary_form)
        else:
            restored.append(part)
    return restored


def _split_compound_reading(kanji_part, reading_part, kanji_readings, cache=None):
    """Return the kanji[reading] parts of a compound, collapsed when unmatched."""
    cache_key = (kanji_part, reading_part)
    if cache is not None and cache_key in cache.reading_parts:
        return cache.reading_parts[cache_key]

    from .word_parser import split_reading_with_positions
    from .dictionary import expand_iteration_marks

    # Expand iteration marks (々) before splitting
    expanded_kanji = expand_iteration_marks(kanji_part)

    # Get individual kanji[reading] pairs in order
    reading_parts = split_reading_with_positions(expanded_kanji, reading_part, kanji_readings)

    if reading_parts:
        reading_parts = _restore_iteration_marks(kanji_part, reading_parts)
        # If any readings are empty, collapse to compound to preserve reading order
        reading_parts = _collapse_empty_readings_to_compound(reading_parts, reading_part)

    if cache is not None:
        cache.reading_parts[cache_key] = reading_parts
    return reading_parts


def _format_kanji_meanings(furigana_text, kanji_to_color, kanji_meanings):
    """Generate HTML for kanji meanings with color coordination.

    Args:
        furigana_text: Card's furigana text
        kanji_to_color: Dict mapping kanji to colors
        kanji_meanings: Dict mapping kanji to [meanings]

    Returns:
        HTML string like: <span style="color: lightgreen;">大</span>: large, big  |  ...
    """
    if not furigana_text or not kanji_to_color:
        return ""

    kanji_chars = []
    for char in furigana_text:
        if '\u4e00' <= char <= '\u9fff' and char not in kanji_chars:
            kanji_chars.append(char)

    html_parts = []
    for kanji in kanji_chars:
        if kanji not in kanji_to_color:
            continue

        color = kanji_to_color[kanji]
        meanings = kanji_meanings.get(kanji, [])

        if meanings:
            meanings_text = ', '.join(meanings)
            html_parts.append(
                f'<span style="color: {color};">{kanji}</span>: {meanings_text}'
            )

    return '  |  '.join(html_parts)
