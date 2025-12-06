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

# Configuration: Input field format
# Mode 1: Single field containing kanji with furigana (e.g., "頭[あたま]が 痛[いた]い")
INPUT_MODE_SINGLE_FIELD = "single"
INPUT_FIELD_SINGLE = "ID"  # Field name for single-field mode

# Mode 2: Two fields - one with kanji, one with reading (e.g., "頭が痛い" + "あたまがいたい")
INPUT_MODE_TWO_FIELDS = "two"
INPUT_FIELD_KANJI = "Kanji"  # Field name for kanji
INPUT_FIELD_READING = "Reading"  # Field name for reading

# Active mode: Set to INPUT_MODE_SINGLE_FIELD or INPUT_MODE_TWO_FIELDS
INPUT_MODE = INPUT_MODE_SINGLE_FIELD


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

def convert_two_fields_to_furigana(kanji_text, reading_text):
    """
    Convert two-field format (separate kanji and reading) to single-field furigana format.

    Args:
        kanji_text: Text with kanji (e.g., "頭が痛い")
        reading_text: Full reading (e.g., "あたまがいたい")

    Returns:
        Text in furigana format (e.g., "頭が痛い[あたまがいたい]")
    """
    if not kanji_text or not reading_text:
        return kanji_text or ""

    # Simply append the reading in brackets at the end
    return f"{kanji_text}[{reading_text}]"


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


def assign_positions_to_new_cards(cards, new_card_ids):
    """
    Assign learning order positions only to new cards.

    Args:
        cards: List of all CardInfo objects with scores computed
        new_card_ids: Set of card IDs that are in 'new' state
    """
    # Filter only new cards
    new_cards = [c for c in cards if c.card_id in new_card_ids]

    # Sort new cards by score (descending), then by unlock_potential (descending)
    # Position 1 = highest score (most familiar) = learn first
    sorted_new_cards = sorted(new_cards, key=lambda c: (-c.score, -c.unlock_potential))

    # Assign positions only to new cards
    for position, card in enumerate(sorted_new_cards, start=1):
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


def reposition_new_cards(cards, collection):
    """
    Reposition new cards based on their computed position field.

    Only repositions cards that are in the 'new' state and have a position assigned.

    Args:
        cards: List of CardInfo objects with position field set (for new cards)
        collection: Anki collection

    Returns:
        Number of cards repositioned
    """
    # Get all new cards in the deck
    new_cids = set(collection.find_cards('"deck:Japan::1. Vocabulary" is:new'))

    # Build a mapping of card_id to position for new cards that have positions
    reposition_map = {}
    for card in cards:
        if card.card_id in new_cids and card.position > 0:
            reposition_map[card.card_id] = card.position

    if not reposition_map:
        return 0

    # Sort cards by their computed position
    sorted_card_ids = sorted(reposition_map.keys(), key=lambda cid: reposition_map[cid])

    # Reposition using Anki's scheduler
    # The due value for new cards represents their queue position
    # Modern Anki API (v2.1.50+)
    collection.sched.reposition_new_cards(
        card_ids=sorted_card_ids,
        starting_from=1,
        step_size=1,
        randomize=False,
        shift_existing=True
    )
    return len(sorted_card_ids)


def process_collection(collection=None, dry_run=False, reposition=False):
    """
    Process cards to compute scores, unlock potential, and positions.

    Args:
        collection: Anki collection (defaults to mw.col)
        dry_run: If True, don't actually update cards
        reposition: If True, also reposition new cards based on computed positions
    """
    if not collection:
        collection = mw.col
    else:
        collection = collection

    cards = load_cards(collection)

    # Compute scores for ALL cards
    compute_scores(cards)

    # Get new card IDs for position assignment
    new_cids = set(collection.find_cards('"deck:Japan::1. Vocabulary" is:new'))

    # Assign positions only to new cards
    assign_positions_to_new_cards(cards, new_cids)

    print("Cards sorted by learning order position:")
    print("=" * 60)

    # Show all cards in output
    print_scores(cards, new_card_ids=new_cids)

    # Update fields for ALL cards (score/unlock for all, position only for new)
    update_count = update_cards_score(cards, collection, new_card_ids=new_cids, dry_run=dry_run)

    print("=" * 60)
    print(f"Total cards processed: {len(cards)}")
    print(f"  - New cards: {len(new_cids)}")
    print(f"  - Non-new cards: {len(cards) - len(new_cids)}")
    print(f"Card fields updated for {update_count} cards")
    print(f"  - {FIELD_NAME_SCORE}: Familiarity score (all cards)")
    print(f"  - {FIELD_NAME_UNLOCK_POTENTIAL}: Unlock potential (all cards)")
    print(f"  - {FIELD_NAME_POSITION}: Learning order position (new cards only)")

    # Reposition cards if requested (only new cards)
    reposition_count = 0
    if reposition and not dry_run:
        reposition_count = reposition_new_cards(cards, collection)
        print(f"\nRepositioned {reposition_count} new cards based on computed positions")

    try:
        message = f"Updated card fields for {update_count} cards:\n"
        message += f"  - {FIELD_NAME_SCORE} (all cards)\n"
        message += f"  - {FIELD_NAME_UNLOCK_POTENTIAL} (all cards)\n"
        message += f"  - {FIELD_NAME_POSITION} ({len(new_cids)} new cards only)"
        if reposition and reposition_count > 0:
            message += f"\n\nRepositioned {reposition_count} new cards"
        showInfo(message)
    except Exception as e:
        print(f"Updated card fields for {update_count} cards")


def load_cards(collection,
               input_mode=INPUT_MODE,
               single_field_name=INPUT_FIELD_SINGLE,
               kanji_field_name=INPUT_FIELD_KANJI,
               reading_field_name=INPUT_FIELD_READING):
    """
    Load cards from collection and extract furigana text.

    Args:
        collection: Anki collection
        input_mode: Either INPUT_MODE_SINGLE_FIELD or INPUT_MODE_TWO_FIELDS
        single_field_name: Field name for single-field mode
        kanji_field_name: Field name for kanji in two-field mode
        reading_field_name: Field name for reading in two-field mode

    Returns:
        List of CardInfo objects
    """
    # Extract card information
    all_cids = collection.find_cards('"deck:Japan::1. Vocabulary"')
    cards = []
    for cid in all_cids:
        card = collection.get_card(cid)
        note = card.note()

        # Get furigana text based on input mode
        if input_mode == INPUT_MODE_SINGLE_FIELD:
            furigana_text = get_field_value(note, single_field_name)
        elif input_mode == INPUT_MODE_TWO_FIELDS:
            kanji_text = get_field_value(note, kanji_field_name)
            reading_text = get_field_value(note, reading_field_name)
            furigana_text = convert_two_fields_to_furigana(kanji_text, reading_text)
        else:
            furigana_text = ""

        cards.append(CardInfo(card.id, furigana_text, card.memory_state.stability if card.memory_state else 0))
    return cards


def print_scores(cards, new_card_ids=None):
    """
    Print card scores. Only new cards have positions assigned.

    Args:
        cards: List of CardInfo objects
        new_card_ids: Set of card IDs that are new (have positions)
    """
    # Sort cards: new cards by position, non-new cards by score
    new_cards = [c for c in cards if new_card_ids and c.card_id in new_card_ids]
    non_new_cards = [c for c in cards if not new_card_ids or c.card_id not in new_card_ids]

    # Sort new cards by position
    sorted_new_cards = sorted(new_cards, key=lambda c: c.position)

    # Sort non-new cards by score (descending)
    sorted_non_new_cards = sorted(non_new_cards, key=lambda c: -c.score)

    # Print new cards first
    for card in sorted_new_cards:
        if card.score > 0:
            print(f"Pos: {card.position:5d} | Score: {card.score:8.1f} | ID: {card.furigana_text:24s} | Unknown: {card.unknown_kanji_readings} | Unlock: {card.unlock_potential:3d} | Stability: {card.stability:.1f} (Score/Stability: {card.score / card.stability * 100 if card.stability > 0 else 0:.1f}%)")
        else:
            print(f"Pos: {card.position:5d} | Score: {card.score:8.1f} | ID: {card.furigana_text:24s} | Unknown: {card.unknown_kanji_readings} | Unlock: {card.unlock_potential:3d}")

    # Print non-new cards (no position)
    if sorted_non_new_cards:
        print("\nNon-new cards (no position assigned):")
        for card in sorted_non_new_cards[:20]:  # Limit to first 20 for brevity
            if card.score > 0:
                print(f"Pos: {'N/A':>5s} | Score: {card.score:8.1f} | ID: {card.furigana_text:24s} | Unknown: {card.unknown_kanji_readings} | Unlock: {card.unlock_potential:3d} | Stability: {card.stability:.1f}")
            else:
                print(f"Pos: {'N/A':>5s} | Score: {card.score:8.1f} | ID: {card.furigana_text:24s} | Unknown: {card.unknown_kanji_readings} | Unlock: {card.unlock_potential:3d}")


def update_cards_score(cards_score, collection,
                       position_field=FIELD_NAME_POSITION,
                       score_field=FIELD_NAME_SCORE,
                       unlock_potential_field=FIELD_NAME_UNLOCK_POTENTIAL,
                       new_card_ids=None, dry_run=False):
    """
    Update card fields with position, score, and unlock potential.

    Args:
        cards_score: List of CardInfo objects
        collection: Anki collection
        position_field: Name of position field
        score_field: Name of score field
        unlock_potential_field: Name of unlock potential field
        new_card_ids: Set of card IDs that are new (only these get position updated)
        dry_run: If True, don't actually update
    """
    update_count = 0
    for card in cards_score:
        is_new = new_card_ids and card.card_id in new_card_ids
        if dry_run:
            update_count += 1
        elif update_card_fields(card, collection,
                               position_field=position_field,
                               score_field=score_field,
                               unlock_potential_field=unlock_potential_field,
                               update_position=is_new):
            update_count += 1
    return update_count


def update_card_fields(card_info, collection,
                       position_field=FIELD_NAME_POSITION,
                       score_field=FIELD_NAME_SCORE,
                       unlock_potential_field=FIELD_NAME_UNLOCK_POTENTIAL,
                       update_position=True):
    """
    Update card note with position, score, and unlock potential fields.

    Args:
        card_info: CardInfo object
        collection: Anki collection
        position_field: Name of position field
        score_field: Name of score field
        unlock_potential_field: Name of unlock potential field
        update_position: If True, update position field; if False, clear position field
    """
    card = collection.get_card(card_info.card_id)
    note = card.note()
    note_type = note.note_type()

    # Build a map of field names to indices
    field_indices = {}
    for i, fld in enumerate(note_type['flds']):
        field_indices[fld['name']] = i

    # Track if any field was updated
    updated = False

    # Update position field (only for new cards) or clear it (for non-new cards)
    if position_field in field_indices:
        if update_position:
            note.fields[field_indices[position_field]] = str(card_info.position)
        else:
            # Clear position field for non-new cards
            note.fields[field_indices[position_field]] = ""
        updated = True
    else:
        if update_position:
            print(f"Warning: Field '{position_field}' not found in note type: {note_type['name']}")

    # Update score field (for all cards)
    if score_field in field_indices:
        note.fields[field_indices[score_field]] = str(round(card_info.score, 1))
        updated = True
    else:
        print(f"Warning: Field '{score_field}' not found in note type: {note_type['name']}")

    # Update unlock potential field (for all cards)
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
