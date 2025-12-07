"""
Dictionary module - Loading and manipulating kanji dictionary data.

This module handles:
- Loading kanji readings from kanjidic2_light.xml
- Verb conjugation helpers (i-stem endings)
- Rendaku (sequential voicing) transformations
- Iteration mark expansion (々)
- Kanji extraction from text
"""

import os
import re
import xml.etree.ElementTree as ET

try:
    from aqt.utils import showInfo
except ImportError:
    # Fallback for non-Anki environments (testing)
    def showInfo(msg):
        print(msg)


def extract_kanji_only(text):
    """Extract only kanji characters from text, filtering out kana."""
    return re.findall(r'[\u4e00-\u9fff]', text)


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
    return verb_ending[:-1] + u_to_i_map[verb_ending[-1]]


def get_rendaku_form(reading):
    """Generate rendaku (sequential voicing) form of a reading if applicable."""
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
    """Generate rendaku (sequential voicing) form of a reading if applicable (p-transformation)."""
    rendaku_map = {
        'は': 'ぱ', 'ひ': 'ぴ', 'ふ': 'ぷ', 'へ': 'ぺ', 'ほ': 'ぽ',
    }

    first_char = reading[0]
    if first_char in rendaku_map:
        return rendaku_map[first_char] + reading[1:]

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


def load_kanji_dictionnary_readings():
    """Load kanji readings from kanjidic2_light.xml into a dictionary.
    For each kanji, map verb_kanji_part reading to a list of all its variations."""

    current_dir = os.path.dirname(os.path.abspath(__file__))
    xml_file = os.path.join(current_dir, 'resources', 'kanjidic2_light.xml')

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()
    except Exception as e:
        print(f"Unexpected error loading kanji readings: {e}")
        showInfo(f"Error loading kanji data: {str(e)}")
        return {}

    kanji_readings = {}

    for character in root.findall('character'):
        kanji = character.find('literal').text
        readings_map = {}

        # Get kun'yomi readings (Japanese readings)
        for reading in character.findall('ja_kun'):
            reading_text = reading.text
            if reading_text:
                variations = []
                # For readings with dots, generate verb forms
                if '.' not in reading_text:
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
                        if verb_kana_part.endswith('い'):
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
                variations = [reading_text]
                rendaku_form = get_rendaku_form(reading_text)
                if rendaku_form:
                    variations.append(rendaku_form)
                rendaku_form_p = get_rendaku_form_p(reading_text)
                if rendaku_form_p:
                    variations.append(rendaku_form_p)
                readings_map[reading_text] = variations

        kanji_readings[kanji] = readings_map
    return kanji_readings
