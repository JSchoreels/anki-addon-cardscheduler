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


def format_card_html(card_info, kanji_meanings, kanji_readings):
    """Generate all HTML for a card's display fields.

    Args:
        card_info: CardInfo object with related_cards_known/unknown lists
        kanji_meanings: Dict {kanji: [meanings]}
        kanji_readings: Dict {kanji: {reading: [variations]}}

    Returns:
        Tuple of (related_known_html, related_unknown_html, meanings_html)
    """
    current_kanji = set(c for c in card_info.furigana_text if '\u4e00' <= c <= '\u9fff')

    kanji_to_color = {
        kanji: HIGHLIGHT_COLORS[i % len(HIGHLIGHT_COLORS)]
        for i, kanji in enumerate(current_kanji)
    }

    related_known_html = _format_related_words(
        card_info.related_cards_known,
        kanji_to_color,
        kanji_readings
    )

    related_unknown_html = _format_related_words(
        card_info.related_cards_unknown,
        kanji_to_color,
        kanji_readings
    )

    meanings_html = _format_kanji_meanings(
        card_info.furigana_text,
        kanji_to_color,
        kanji_meanings
    )

    return (related_known_html, related_unknown_html, meanings_html)


def _format_related_words(related_cards_list, kanji_to_color, kanji_readings):
    """Format list of (CardInfo, shared_kanji) tuples into HTML.

    Args:
        related_cards_list: List of (CardInfo, shared_kanji_set) tuples
        kanji_to_color: Dict mapping kanji to colors
        kanji_readings: Dict for highlighting

    Returns:
        HTML string with color-coded related words
    """
    if not related_cards_list:
        return ""

    html_parts = []
    for related_card, shared_kanji in related_cards_list:
        shared_colors = {
            kanji: kanji_to_color.get(kanji)
            for kanji in shared_kanji
            if kanji in kanji_to_color
        }

        highlighted = _highlight_shared_kanji(
            related_card.furigana_text,
            shared_colors,
            kanji_readings
        )

        html_parts.append(highlighted)

    return ',　 '.join(html_parts)


def _highlight_shared_kanji(furigana_text, shared_kanji_colors, kanji_readings):
    """Highlight kanji in furigana text that are in shared_kanji_colors.

    Preserves the full furigana text including trailing kana.
    """
    if not furigana_text or not shared_kanji_colors:
        return furigana_text

    # Parse the furigana text to extract all parts (kanji[reading] and plain kana)
    # Pattern matches: kanji (or kanji+iteration marks) followed by [reading]
    # Only matches kanji characters (not kana) before the bracket
    pattern = r'([一-龯々]+)\[([ぁ-ゖァ-ヺー]+)\]'

    result = []
    last_end = 0

    for match in re.finditer(pattern, furigana_text):
        # Add any plain text before this match (trailing kana, etc.)
        if match.start() > last_end:
            result.append(furigana_text[last_end:match.start()])

        kanji_part = match.group(1)
        reading_part = match.group(2)

        # Extract individual kanji from kanji_part
        kanji_chars = [c for c in kanji_part if '\u4e00' <= c <= '\u9fff']

        if len(kanji_chars) == 1 and kanji_chars[0] in shared_kanji_colors:
            # Single kanji that should be highlighted
            color = shared_kanji_colors[kanji_chars[0]]
            result.append(f'<span style="color: {color};">{kanji_part}[{reading_part}]</span>')
        else:
            # Multiple kanji or not in shared colors - keep as is
            result.append(f'{kanji_part}[{reading_part}]')

        last_end = match.end()

    # Add any remaining text after the last match
    if last_end < len(furigana_text):
        result.append(furigana_text[last_end:])

    return ''.join(result)


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
            meanings_text = ', '.join(meanings[:3])
            html_parts.append(
                f'<span style="color: {color};">{kanji}</span>: {meanings_text}'
            )

    return '  |  '.join(html_parts)
