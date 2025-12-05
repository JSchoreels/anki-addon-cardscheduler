import statistics
from collections import defaultdict

from aqt import mw
from aqt.utils import showInfo
import re
import xml.etree.ElementTree as ET
import os

# Configuration: Customizable field names
FIELD_NAME_POSITION = "CardScheduler.Position"
FIELD_NAME_SCORE = "CardScheduler.Score"
FIELD_NAME_UNLOCK_POTENTIAL = "CardScheduler.UnlockPotential"


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
                if  last_extended_reading_matched[1:] == kanji_word[prev_kanji_pos+1:prev_kanji_pos+1+len(last_extended_reading_matched[1:])]:
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
    def __init__(self, card_id, furigana_text, stability):
        self.card_id = card_id
        self.furigana_text = furigana_text
        self.stability = stability
        self.score = 0  # Initialize score
        self.unknown_kanji_readings = 0
        self.unlock_potential = 0  # Max unlock potential of any unknown kanji/reading pair in this card
        self.position = 0  # Learning order position (1 = highest priority)

    def __repr__(self):
        return f"CardInfo(id={self.card_id}, furigana='{self.furigana_text}', interval={self.stability}, score={self.score}, unknowns={self.unknown_kanji_readings}, unlock={self.unlock_potential}, pos={self.position})"

class KanjiReadingInfo:
    def __init__(self):
        self.matched_cards = set()
        self.average_interval = 0.0
        self.unlock_potential = 0  # Number of cards that would get score > 0 if this pair was learned

    def __repr__(self):
        return f"KanjiReadingInfo(average_interval={self.average_interval}, matched_cards_count={len(self.matched_cards)}, unlock_potential={self.unlock_potential})"

def compute_scores(cards):
    """Compute familiarity scores for a list of CardInfo objects."""

    kanji_readings = load_kanji_dictionnary_readings()

    kanji_reading_to_cards = get_kanji_reading_to_matching_card(cards, kanji_readings)

    update_kanji_reading_to_cards_with_max_weighted_interval(kanji_reading_to_cards, kanji_readings)

    print_kanji_readings_with_average_interval(kanji_reading_to_cards)

    # Step 2: Compute score for each card (simplified)
    for card_info in cards:
        if not card_info.furigana_text:
            card_info.score = 0
            continue
        kanji_reading_pairs = get_kanji_reading_pairs(card_info.furigana_text, kanji_readings)

        # Group by kanji, collect intervals for each reading
        kanji_to_intervals = defaultdict(list)
        for pair in kanji_reading_pairs:
            if pair in kanji_reading_to_cards:
                kanji = pair.split('[')[0]  # Extract kanji from '当[あ.たる]'
                interval = kanji_reading_to_cards[pair].max_weighted_interval
                kanji_to_intervals[kanji].append(interval)

        # Take max interval for each kanji, then min across all kanji
        max_intervals_per_kanji = [
            max(intervals) for intervals in kanji_to_intervals.values()
        ]

        card_info.score = min(max_intervals_per_kanji) if max_intervals_per_kanji else 0
        card_info.unknown_kanji_readings = sum(
            1 for intervals in kanji_to_intervals.values() if max(intervals) == 0.0
        )

    # Step 3: Compute unlock potential for each kanji/reading pair
    compute_unlock_potential(kanji_reading_to_cards, kanji_readings, cards)

    # Step 4: Update each card's unlock potential (max of all its unknown pairs)
    for card_info in cards:
        if not card_info.furigana_text or card_info.score > 0:
            card_info.unlock_potential = 0
            continue

        kanji_reading_pairs = get_kanji_reading_pairs(card_info.furigana_text, kanji_readings)
        max_unlock = 0

        for pair in kanji_reading_pairs:
            if pair in kanji_reading_to_cards:
                pair_info = kanji_reading_to_cards[pair]
                # Only consider pairs that are unknown (interval = 0)
                if pair_info.max_weighted_interval == 0:
                    max_unlock = max(max_unlock, pair_info.unlock_potential)

        card_info.unlock_potential = max_unlock

    # Step 5: Calculate learning order positions
    # Sort by score (descending), then by unlock_potential (descending)
    # Position 1 = highest score (most familiar) = learn first
    # For cards with same score, higher unlock potential = higher priority
    sorted_cards = sorted(cards, key=lambda c: (-c.score, -c.unlock_potential))
    for position, card in enumerate(sorted_cards, start=1):
        card.position = position

def print_kanji_readings_with_average_interval(kanji_reading_to_cards):
    # Debug: Show global kanji-reading averages
    print("Global kanji-reading averages:")
    for pair, info in kanji_reading_to_cards.items():
        print(
            f"Pair '{pair}': average_interval={info.max_weighted_interval:.2f}, matched_cards_count={len(info.matched_cards)}")


def update_kanji_reading_to_cards_with_max_weighted_interval(kanji_reading_to_cards, kanji_readings):
    # Calculate average intervals for each kanji-reading pair

    for pair, info in kanji_reading_to_cards.items():
        weighted_intervals = []
        for card in info.matched_cards:
            if card.stability > 0:
                pairs = get_kanji_reading_pairs(card.furigana_text, kanji_readings)
                unique_kanji_count = len(set(p.split('[')[0] for p in pairs))
                weighted_interval = card.stability / 2 ** (unique_kanji_count - 1)
                weighted_intervals.append(weighted_interval)

        info.max_weighted_interval = max(weighted_intervals) if weighted_intervals else 0.0


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


def compute_unlock_potential(kanji_reading_to_cards, kanji_readings, cards):
    """
    For each kanji/reading pair, compute how many cards would get score > 0
    if that pair was learned (simulated with high interval value).
    """
    SIMULATED_LEARNED_INTERVAL = 100.0  # High interval to simulate "learned" state

    # For each kanji/reading pair with interval 0
    for pair, pair_info in kanji_reading_to_cards.items():
        if pair_info.max_weighted_interval > 0:
            # Already learned, no unlock potential
            pair_info.unlock_potential = 0
            continue

        unlock_count = 0

        # Check each card containing this pair
        for card in pair_info.matched_cards:
            # Only consider cards with current score <= 0
            if card.score > 0:
                continue

            # Simulate learning this pair and recalculate card score
            kanji_reading_pairs = get_kanji_reading_pairs(card.furigana_text, kanji_readings)

            # Group by kanji, collect intervals for each reading
            kanji_to_intervals = defaultdict(list)
            for p in kanji_reading_pairs:
                if p in kanji_reading_to_cards:
                    kanji = p.split('[')[0]
                    # Use simulated interval if this is the pair we're testing
                    interval = SIMULATED_LEARNED_INTERVAL if p == pair else kanji_reading_to_cards[p].max_weighted_interval
                    kanji_to_intervals[kanji].append(interval)

            # Calculate new score with simulated learning
            max_intervals_per_kanji = [
                max(intervals) for intervals in kanji_to_intervals.values()
            ]
            new_score = min(max_intervals_per_kanji) if max_intervals_per_kanji else 0

            # Count if this card would be unlocked
            if new_score > 0:
                unlock_count += 1

        pair_info.unlock_potential = unlock_count


def process_collection(collection=None, dry_run=False):
    if not collection:
        collection = mw.col
    else:
        collection = collection

    cards = load_cards(collection)

    compute_scores(cards)

    print("Cards sorted by familiarity score (least known first):")
    print("=" * 60)

    update_only_new_cards = False
    if update_only_new_cards:
        new_cids = collection.find_cards('"deck:Japan::1. Vocabulary" is:new')
        card_id_filter = lambda card_id: card_id in new_cids
    else:
        card_id_filter = lambda card_id: True

    print_scores(cards, filter=card_id_filter)
    update_count = update_cards_score(cards, collection, filter=card_id_filter, dry_run=dry_run)

    print("=" * 60)
    print(f"Total cards processed: {len([card for card in cards if card_id_filter(card.card_id)])}")
    print(f"Card fields updated for {update_count} cards")
    print(f"  - {FIELD_NAME_POSITION}: Learning order position")
    print(f"  - {FIELD_NAME_SCORE}: Familiarity score")
    print(f"  - {FIELD_NAME_UNLOCK_POTENTIAL}: Unlock potential")

    try:
        showInfo(f"Updated card fields for {update_count} cards:\n"
                f"  - {FIELD_NAME_POSITION}\n"
                f"  - {FIELD_NAME_SCORE}\n"
                f"  - {FIELD_NAME_UNLOCK_POTENTIAL}")
    except Exception as e:
        print(f"Updated card fields for {update_count} cards")


def load_cards(collection, furigana_plain_field="ID"):
    # Extract card information
    all_cids = collection.find_cards('"deck:Japan::1. Vocabulary"')
    cards = []
    for cid in all_cids:
        card = collection.get_card(cid)
        note = card.note()
        field_value = get_field_value(note, furigana_plain_field)
        cards.append(CardInfo(card.id, field_value, card.memory_state.stability if card.memory_state else 0))
    return cards


def print_scores(cards, filter=lambda card: True):
    # Sort cards by position (learning order)
    sorted_cards = sorted(cards, key=lambda c: c.position)
    for card in sorted_cards:
        if filter(card.card_id):
            if card.score > 0:
                print(f"Pos: {card.position:5d} | Score: {card.score:8.1f} | ID: {card.furigana_text:24s} | Unknown: {card.unknown_kanji_readings} | Unlock: {card.unlock_potential:3d} | Stability: {card.stability:.1f} (Score/Stability: {card.score / card.stability * 100 if card.stability > 0 else 0:.1f}%)")
            else:
                print(f"Pos: {card.position:5d} | Score: {card.score:8.1f} | ID: {card.furigana_text:24s} | Unknown: {card.unknown_kanji_readings} | Unlock: {card.unlock_potential:3d}")


def update_cards_score(cards_score, collection,
                       position_field=FIELD_NAME_POSITION,
                       score_field=FIELD_NAME_SCORE,
                       unlock_potential_field=FIELD_NAME_UNLOCK_POTENTIAL,
                       filter=lambda card: True, dry_run=False):
    """Update card fields with position, score, and unlock potential."""
    update_count = 0
    for card in cards_score:
        if filter(card.card_id):
            if dry_run:
                update_count += 1
            elif update_card_fields(card, collection,
                                   position_field=position_field,
                                   score_field=score_field,
                                   unlock_potential_field=unlock_potential_field):
                update_count += 1
    return update_count


def update_card_fields(card_info, collection,
                       position_field=FIELD_NAME_POSITION,
                       score_field=FIELD_NAME_SCORE,
                       unlock_potential_field=FIELD_NAME_UNLOCK_POTENTIAL):
    """Update card note with position, score, and unlock potential fields."""
    card = collection.get_card(card_info.card_id)
    note = card.note()
    note_type = note.note_type()

    # Build a map of field names to indices
    field_indices = {}
    for i, fld in enumerate(note_type['flds']):
        field_indices[fld['name']] = i

    # Track if any field was updated
    updated = False

    # Update position field
    if position_field in field_indices:
        note.fields[field_indices[position_field]] = str(card_info.position)
        updated = True
    else:
        print(f"Warning: Field '{position_field}' not found in note type: {note_type['name']}")

    # Update score field
    if score_field in field_indices:
        note.fields[field_indices[score_field]] = str(round(card_info.score, 1))
        updated = True
    else:
        print(f"Warning: Field '{score_field}' not found in note type: {note_type['name']}")

    # Update unlock potential field
    if unlock_potential_field in field_indices:
        note.fields[field_indices[unlock_potential_field]] = str(card_info.unlock_potential)
        updated = True
    else:
        print(f"Warning: Field '{unlock_potential_field}' not found in note type: {note_type['name']}")

    if updated:
        collection.update_note(note)
        return True
    else:
        return False


def update_card_score(card_id, score, collection, score_field="MyPosition"):
    """Legacy function - kept for backwards compatibility."""
    card = collection.get_card(card_id)
    note = card.note()
    note_type = note.note_type()

    # Find the field index
    field_index = None
    for i, fld in enumerate(note_type['flds']):
        if fld['name'] == score_field:
            field_index = i
            break

    if field_index is not None:
        # Update the field with the score (rounded to 1 decimal place)
        note.fields[field_index] = str(round(score, 1))
        collection.update_note(note)
        return True
    else:
        print(f"Field '{score_field}' not found in note type: {note_type['name']}")
        return False
