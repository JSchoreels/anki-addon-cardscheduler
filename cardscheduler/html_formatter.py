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

    Adapted from scheduler.py's highlight_shared_kanji function.
    """
    from .word_parser import get_kanji_reading_pairs

    pairs = get_kanji_reading_pairs(furigana_text, kanji_readings)
    highlighted_pairs = []

    for pair in pairs:
        match = re.match(r'([^[]+)\[([^]]*)\]', pair)
        if match:
            kanji, reading = match.groups()
            if kanji in shared_kanji_colors:
                color = shared_kanji_colors[kanji]
                highlighted_pairs.append(
                    f'<span style="color: {color};">{kanji}[{reading}]</span>'
                )
            else:
                highlighted_pairs.append(pair)
        else:
            highlighted_pairs.append(pair)

    return ''.join(highlighted_pairs)


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
