import statistics

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

            # Always add the compound word itself (with original form including 々)
            # kanji_pairs.add(f"{kanji_word}[{reading}]")

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

    return None

def load_kanji_dictionnary_readings():
    """Load kanji readings from kanjidic2_light.xml into a dictionary.
    For each kanji, map verb_kanji_part reading to a list of all its variations."""

    current_dir = os.path.dirname(os.path.abspath(__file__))
    xml_file = os.path.join(current_dir, 'kanjidic2_light.xml')

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
    """Generate rendaku (sequential voicing) form of a reading if applicable."""
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

class CardInfo:
    def __init__(self, card_id, furigana_text, interval):
        self.card_id = card_id
        self.furigana_text = furigana_text
        self.interval = interval
        self.score = 0  # Initialize score
        self.unknown_kanji_readings = 0

    def __repr__(self):
        return f"CardInfo(id={self.card_id}, furigana='{self.furigana_text}', interval={self.interval}, score={self.score}, unknowns={self.unknown_kanji_readings})"

class KanjiReadingInfo:
    def __init__(self):
        self.matched_cards = set()
        self.average_interval = 0.0

    def __repr__(self):
        return f"KanjiReadingInfo(average_interval={self.average_interval}, matched_cards_count={len(self.matched_cards)})"

def compute_scores(cards):
    """Compute familiarity scores for a list of CardInfo objects."""

    kanji_readings = load_kanji_dictionnary_readings()

    kanji_reading_to_cards = get_kanji_reading_to_matching_card(cards, kanji_readings)

    update_kanji_reading_to_cards_with_average_interval(kanji_reading_to_cards)

    print_kanji_readings_with_average_interval(kanji_reading_to_cards)

    # Step 2: Compute score for each card (simplified)
    for card_info in cards:
        if not card_info.furigana_text:
            card_info.score = 0
            continue
        kanji_reading_pairs = get_kanji_reading_pairs(card_info.furigana_text, kanji_readings)
        intervals = [
            kanji_reading_to_cards[pair].average_interval
            for pair in kanji_reading_pairs
            if pair in kanji_reading_to_cards
        ]
        card_info.score = sum(intervals) / len(intervals) if intervals else 0
        card_info.unknown_kanji_readings = intervals.count(0.0)


def print_kanji_readings_with_average_interval(kanji_reading_to_cards):
    # Debug: Show global kanji-reading averages
    print("Global kanji-reading averages:")
    for pair, info in kanji_reading_to_cards.items():
        print(
            f"Pair '{pair}': average_interval={info.average_interval:.2f}, matched_cards_count={len(info.matched_cards)}")


def update_kanji_reading_to_cards_with_average_interval(kanji_reading_to_cards):
    # Calculate average intervals for each kanji-reading pair
    for pair, info in kanji_reading_to_cards.items():
        info.average_interval = statistics.fmean(
            [card.interval for card in info.matched_cards if card.interval > 0]
            or [0.0]
        )


def get_kanji_reading_to_matching_card(cards, kanji_readings):
    kanji_reading_to_cards = {}
    for card_info in cards:
        if not card_info.furigana_text:
            continue
        kanji_reading_pairs = get_kanji_reading_pairs(card_info.furigana_text, kanji_readings)
        for pair in kanji_reading_pairs:
            if pair not in kanji_reading_to_cards:
                kanji_reading_to_cards[pair] = KanjiReadingInfo()
            kanji_reading_to_cards[pair].matched_cards.add(card_info)
    return kanji_reading_to_cards


def process_collection(collection=None, dry_run=False):
    if not collection:
        collection = mw.col
    else:
        collection = collection

    """Process the entire collection: extract cards, compute scores, and update fields."""
    cards = load_cards(collection)

    # Compute scores
    compute_scores(cards)

    print("Cards sorted by familiarity score (least known first):")
    print("=" * 60)

    update_only_new_cards = True
    if update_only_new_cards:
        new_cids = collection.find_cards('"deck:Japan::1. Vocabulary" is:new')
        card_id_filter = lambda card_id: card_id in new_cids
    else:
        card_id_filter = lambda card_id: True

    print_scores(cards, filter=card_id_filter)
    update_count = update_cards_score(cards, collection, filter=card_id_filter, dry_run=dry_run)

    print("=" * 60)
    print(f"Total cards processed: {len([card for card in cards if card_id_filter(card.card_id)])}")
    print(f"MyPosition field updated for {update_count} cards")

    # Show a message to the user
    try:
        showInfo(f"Updated MyPosition field for {update_count} cards")
    except Exception as e:
        print(f"Updated MyPosition field for {update_count} cards")


def load_cards(collection, furigana_plain_field="ID"):
    # Extract card information
    all_cids = collection.find_cards('"deck:Japan::1. Vocabulary"')
    cards = []
    for cid in all_cids:
        card = collection.get_card(cid)
        note = card.note()
        field_value = get_field_value(note, furigana_plain_field)
        cards.append(CardInfo(card.id, field_value, card.ivl))
    return cards


def print_scores(cards, filter=lambda card: True):
    # Sort cards by score in ascending order (lowest scores first - least familiar)
    sorted_cards = sorted(cards, key=lambda c: c.score, reverse=False)
    for card in sorted_cards:
        if filter(card.card_id):
            print(f"Score: {card.score:8.1f} | ID: {card.furigana_text:24s} | Unknown readings: {card.unknown_kanji_readings}")


def update_cards_score(cards_score, collection, score_field="MyPosition", filter=lambda card: True, dry_run=False):
    update_count = 0
    for card_id, score in [(card.card_id, card.score) for card in cards_score]:
        if filter(card_id):
            if dry_run:
                #print(f"Dry run: would update card ID {card_id} with score {score:.1f}")
                update_count += 1
            elif update_card_score(card_id, score, collection, score_field=score_field):
                update_count += 1
    return update_count


def update_card_score(card_id, score, collection, score_field="MyPosition"):
    card = collection.get_card(card_id)
    note = card.note()
    note_type = note.note_type()

    # Find the MyPosition field index
    my_position_field_index = None
    for i, fld in enumerate(note_type['flds']):
        if fld['name'] == score_field:
            my_position_field_index = i
            break

    if my_position_field_index is not None:
        # Update the field with the score (rounded to 1 decimal place)
        note.fields[my_position_field_index] = str(round(score, 1))
        collection.update_note(note)  # Use the modern API instead of flush()
        return True
    else:
        print(f"MyPosition field not found in note type: {note_type['name']}")
        return False
