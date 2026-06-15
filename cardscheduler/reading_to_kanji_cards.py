"""Generate Reading -> Kanji cards from known vocabulary evidence."""

from collections import defaultdict
from dataclasses import dataclass
from html import escape
from typing import Optional

try:
    from aqt import mw
    from aqt.utils import showInfo
except ImportError:
    mw = None

    def showInfo(msg):
        print(msg)

from .anki_interface import load_cards
from .config import (
    DECK_NAME,
    READING_TO_KANJI_DECK_NAME,
    READING_TO_KANJI_FIELD_NAMES,
    READING_TO_KANJI_MAX_GRADE,
    READING_TO_KANJI_NOTE_TYPE,
)
from .dictionary import (
    get_sokuon_form,
    load_kanji_dictionnary_readings,
    load_kanji_meanings,
)
from .reading_kanji_map import (
    load_kanji_frequencies,
    load_kanji_grades,
    load_onyomi_readings,
)
from .scheduler import build_card_to_pairs

KNOWN_WORD_SEPARATOR = ",　 "
UNKNOWN_GRADE_SORT_VALUE = 99
UNKNOWN_FREQUENCY_SORT_VALUE = 999999

@dataclass
class ReadingToKanjiEntry:
    kanji: str
    meanings: list
    grade: Optional[int]
    frequency: Optional[int]
    known_words: list

    @property
    def known_word_count(self):
        return len(self.known_words)


@dataclass
class ReadingToKanjiCandidate:
    reading: str
    entries: list

    @property
    def kanji_count(self):
        return len(self.entries)

    @property
    def known_word_count(self):
        return sum(entry.known_word_count for entry in self.entries)

    @property
    def min_grade(self):
        grades = [entry.grade for entry in self.entries if entry.grade is not None]
        return min(grades) if grades else UNKNOWN_GRADE_SORT_VALUE

    @property
    def best_frequency(self):
        frequencies = [
            entry.frequency for entry in self.entries if entry.frequency is not None
        ]
        return min(frequencies) if frequencies else UNKNOWN_FREQUENCY_SORT_VALUE


@dataclass
class ReadingToKanjiUpsertResult:
    candidates: list
    created: int = 0
    updated: int = 0
    skipped_duplicates: int = 0
    repositioned: int = 0


def _parse_pair(pair):
    if "[" not in pair or not pair.endswith("]"):
        return None

    kanji, reading = pair[:-1].split("[", 1)
    return kanji, reading


def _generated_readings_for_base(base_reading, variations):
    readings = {base_reading}
    readings.update(variation for variation in variations if variation)
    return {
        reading
        for reading in readings
        if not _is_sokuon_variation(reading, readings)
    }


def _is_sokuon_variation(reading, readings):
    return any(reading == get_sokuon_form(source) for source in readings)


def _supported_readings_for_known_pair(kanji, reading, onyomi_readings):
    readings_map = onyomi_readings.get(kanji, {})
    matching = []

    for base_reading, variations in readings_map.items():
        for generated_reading in _generated_readings_for_base(base_reading, variations):
            accepted_readings = {generated_reading}
            sokuon = get_sokuon_form(generated_reading)
            if sokuon:
                accepted_readings.add(sokuon)

            if reading in accepted_readings:
                matching.append(generated_reading)

    return matching


def _build_possible_kanji_by_reading(onyomi_readings, kanji_grades, max_grade):
    possible_kanji_by_reading = defaultdict(set)

    for kanji, readings_map in onyomi_readings.items():
        grade = kanji_grades.get(kanji)
        if grade is None or grade > max_grade:
            continue

        for base_reading, variations in readings_map.items():
            for reading in _generated_readings_for_base(base_reading, variations):
                possible_kanji_by_reading[reading].add(kanji)

    return possible_kanji_by_reading


def build_reading_to_kanji_candidates(
    cards,
    kanji_readings,
    onyomi_readings,
    kanji_meanings,
    kanji_grades,
    kanji_frequencies,
    max_grade=READING_TO_KANJI_MAX_GRADE,
):
    """Build Reading -> Kanji candidates from known vocabulary cards.

    A reading is generated when at least one known card supports that dictionary
    reading. The generated answer still includes all possible grade-filtered
    kanji for that reading.
    """
    card_to_pairs = build_card_to_pairs(cards, kanji_readings)
    possible_kanji_by_reading = _build_possible_kanji_by_reading(
        onyomi_readings,
        kanji_grades,
        max_grade,
    )
    support = _collect_known_word_support(
        cards,
        card_to_pairs,
        onyomi_readings,
        possible_kanji_by_reading,
    )

    candidates = []
    for reading, possible_kanji in possible_kanji_by_reading.items():
        if not _reading_has_known_support(support, reading, possible_kanji):
            continue

        entries = _build_candidate_entries(
            reading,
            possible_kanji,
            support,
            kanji_meanings,
            kanji_grades,
            kanji_frequencies,
        )
        candidates.append(ReadingToKanjiCandidate(reading=reading, entries=entries))

    candidates.sort(key=candidate_sort_key)
    return candidates


def _collect_known_word_support(
    cards,
    card_to_pairs,
    onyomi_readings,
    possible_kanji_by_reading,
):
    support = defaultdict(lambda: defaultdict(dict))

    for card in cards:
        if card.stability <= 0:
            continue

        for pair in card_to_pairs[card.card_id]:
            parsed = _parse_pair(pair)
            if not parsed:
                continue

            kanji, observed_reading = parsed
            for supported_reading in _supported_readings_for_known_pair(
                kanji,
                observed_reading,
                onyomi_readings,
            ):
                possible_kanji = possible_kanji_by_reading.get(
                    supported_reading,
                    set(),
                )
                if kanji in possible_kanji:
                    _record_best_known_word_support(
                        support,
                        supported_reading,
                        kanji,
                        card.furigana_text,
                        card.stability,
                    )

    return support


def _record_best_known_word_support(support, reading, kanji, known_word, stability):
    previous_stability = support[reading][kanji].get(known_word, -1)
    if stability > previous_stability:
        support[reading][kanji][known_word] = stability


def _reading_has_known_support(support, reading, possible_kanji):
    reading_support = support.get(reading, {})
    return any(reading_support.get(kanji) for kanji in possible_kanji)


def _build_candidate_entries(
    reading,
    possible_kanji,
    support,
    kanji_meanings,
    kanji_grades,
    kanji_frequencies,
):
    entries = [
        ReadingToKanjiEntry(
            kanji=kanji,
            meanings=kanji_meanings.get(kanji, []),
            grade=kanji_grades.get(kanji),
            frequency=kanji_frequencies.get(kanji),
            known_words=_known_words_for_kanji(support, reading, kanji),
        )
        for kanji in possible_kanji
    ]
    entries.sort(key=_entry_sort_key)
    return entries


def _known_words_for_kanji(support, reading, kanji):
    known_word_stabilities = support.get(reading, {}).get(kanji, {})
    return sorted(
        known_word_stabilities,
        key=lambda word: (-known_word_stabilities[word], word),
    )


def _entry_sort_key(entry):
    return (
        entry.known_word_count == 0,
        -entry.known_word_count,
        entry.grade if entry.grade is not None else UNKNOWN_GRADE_SORT_VALUE,
        entry.frequency
        if entry.frequency is not None
        else UNKNOWN_FREQUENCY_SORT_VALUE,
        entry.kanji,
    )


def candidate_sort_key(candidate):
    return (
        candidate.kanji_count,
        -candidate.known_word_count,
        candidate.min_grade,
        candidate.best_frequency,
        candidate.reading,
    )


def _format_meanings(entry):
    if entry.meanings:
        return "; ".join(escape(meaning) for meaning in entry.meanings)
    return "N/A"


def _format_known_word(known_word):
    return f'<span class="known-word">{escape(known_word)}</span>'


def format_candidate_fields(candidate, field_names=READING_TO_KANJI_FIELD_NAMES):
    """Format one generated candidate into Anki note field values."""
    kanji_meaning = []
    grades = []
    frequencies = []
    known_words = []

    for entry in candidate.entries:
        kanji = escape(entry.kanji)
        kanji_meaning.append(
            f"<div><b>{kanji}</b> - {_format_meanings(entry)}</div>"
        )
        grades.append(
            f"<div><b>{kanji}</b>: {entry.grade if entry.grade is not None else 'N/A'}</div>"
        )
        frequencies.append(
            f"<div><b>{kanji}</b>: {entry.frequency if entry.frequency is not None else 'N/A'}</div>"
        )
        words = KNOWN_WORD_SEPARATOR.join(
            _format_known_word(word) for word in entry.known_words
        )
        known_words.append(f"<div><b>{kanji}</b>: {words if words else 'N/A'}</div>")

    return {
        field_names["reading"]: candidate.reading,
        field_names["kanji_meaning"]: "\n".join(kanji_meaning),
        field_names["matching_kanji_count"]: str(candidate.kanji_count),
        field_names["grade"]: "\n".join(grades),
        field_names["frequency"]: "\n".join(frequencies),
        field_names["known_words"]: "\n".join(known_words),
    }


def resolve_reading_to_kanji_deck_name(deck_name=READING_TO_KANJI_DECK_NAME):
    return deck_name or f"{DECK_NAME}::Reading->Kanji"


def ensure_reading_to_kanji_deck_and_notetype(
    collection,
    deck_name,
    note_type_name=READING_TO_KANJI_NOTE_TYPE,
    field_names=READING_TO_KANJI_FIELD_NAMES,
):
    """Ensure target deck and note type exist, returning (deck_id, notetype)."""
    deck_existed = _deck_exists(collection, deck_name)
    deck_id = collection.decks.add_normal_deck_with_name(deck_name).id
    notetype = collection.models.by_name(note_type_name)
    notetype_created = notetype is None
    notetype_updated = False

    if notetype_created:
        notetype = _create_reading_to_kanji_notetype(
            collection,
            note_type_name,
            field_names,
        )
    else:
        notetype_updated, notetype = _ensure_reading_to_kanji_notetype_schema(
            collection,
            notetype,
            field_names,
        )

    _refresh_ui_after_creation(
        deck_created=not deck_existed,
        notetype_created=notetype_created or notetype_updated,
    )
    return deck_id, notetype


def _deck_exists(collection, deck_name):
    id_for_name = getattr(collection.decks, "id_for_name", None)
    if id_for_name is None:
        return False
    return id_for_name(deck_name) is not None


def _refresh_ui_after_creation(deck_created=False, notetype_created=False):
    if not deck_created and not notetype_created:
        return
    if mw is not None and hasattr(mw, "reset"):
        mw.reset()


def _create_reading_to_kanji_notetype(collection, note_type_name, field_names):
    notetype = collection.models.new(note_type_name)

    for field_name in field_names.values():
        collection.models.add_field(notetype, collection.models.new_field(field_name))

    template = _new_reading_to_kanji_template(collection, field_names)
    collection.models.add_template(notetype, template)
    collection.models.add_dict(notetype)

    created = collection.models.by_name(note_type_name)
    if created is None:
        raise ValueError(f"Failed to create note type '{note_type_name}'.")
    return created


def _ensure_reading_to_kanji_notetype_schema(collection, notetype, field_names):
    existing_fields = {field["name"] for field in notetype["flds"]}
    updated = False

    for field_name in field_names.values():
        if field_name not in existing_fields:
            collection.models.add_field(
                notetype,
                collection.models.new_field(field_name),
            )
            existing_fields.add(field_name)
            updated = True

    if not notetype["tmpls"]:
        collection.models.add_template(
            notetype,
            _new_reading_to_kanji_template(collection, field_names),
        )
        updated = True

    if updated:
        collection.models.update_dict(notetype)
        refreshed = collection.models.by_name(notetype["name"])
        if refreshed is not None:
            notetype = refreshed

    return updated, notetype


def _new_reading_to_kanji_template(collection, field_names):
    template = collection.models.new_template("Reading -> Kanji")
    template["qfmt"] = _anki_field(field_names["reading"])
    template["afmt"] = "\n".join(
        [
            "{{FrontSide}}",
            "<hr>",
            "Kanji Count : " + _anki_field(field_names["matching_kanji_count"]),
            "<hr>",
            "Matching Kanjis : " + _anki_furigana_field(field_names["kanji_meaning"]),
            "<hr>",
            "Grade : " + _anki_field(field_names["grade"]),
            "<hr>",
            "Frequency : " + _anki_field(field_names["frequency"]),
            "<hr>",
            "Known Words : " + _anki_furigana_field(field_names["known_words"]),
        ]
    )
    return template


def _anki_field(field_name):
    return "{{" + field_name + "}}"


def _anki_furigana_field(field_name):
    return "{{furigana:" + field_name + "}}"


def _index_existing_notes(collection, deck_name, note_type_name, reading_field):
    query = f'"deck:{deck_name}" "note:{note_type_name}"'
    notes_by_reading = {}
    duplicates = set()

    for note_id in collection.find_notes(query):
        note = collection.get_note(note_id)
        reading = note[reading_field].strip()
        if not reading:
            continue
        if reading in notes_by_reading:
            duplicates.add(reading)
            continue
        notes_by_reading[reading] = note

    return notes_by_reading, duplicates


def _note_card_ids(collection, note):
    if hasattr(note, "card_ids"):
        return list(note.card_ids())
    if hasattr(collection, "card_ids_of_note"):
        return list(collection.card_ids_of_note(note.id))
    return []


def upsert_reading_to_kanji_notes(
    collection,
    candidates,
    deck_id,
    deck_name,
    notetype,
    field_names=READING_TO_KANJI_FIELD_NAMES,
):
    """Create/update generated notes and reposition their cards by candidate order."""
    notes_by_reading, duplicates = _index_existing_notes(
        collection,
        deck_name,
        notetype["name"],
        field_names["reading"],
    )
    created = 0
    updated = 0
    skipped_duplicates = 0
    sorted_card_ids = []

    for candidate in candidates:
        if candidate.reading in duplicates:
            skipped_duplicates += 1
            continue

        field_values = format_candidate_fields(candidate, field_names)
        note = notes_by_reading.get(candidate.reading)

        if note is None:
            note = collection.new_note(notetype)
            _set_note_fields(note, field_values)
            collection.add_note(note, deck_id)
            created += 1
        else:
            _set_note_fields(note, field_values)
            collection.update_note(note)
            updated += 1

        sorted_card_ids.extend(_note_card_ids(collection, note))

    repositioned = reposition_generated_cards(collection, sorted_card_ids)
    return ReadingToKanjiUpsertResult(
        candidates=candidates,
        created=created,
        updated=updated,
        skipped_duplicates=skipped_duplicates,
        repositioned=repositioned,
    )


def _set_note_fields(note, field_values):
    for field_name, value in field_values.items():
        note[field_name] = value


def reposition_generated_cards(collection, sorted_card_ids):
    if not sorted_card_ids:
        return 0

    collection.sched.reposition_new_cards(
        card_ids=sorted_card_ids,
        starting_from=1,
        step_size=1,
        randomize=False,
        shift_existing=True,
    )
    return len(sorted_card_ids)


def build_candidates_from_collection(collection):
    cards = load_cards(collection, frequency_field_name=None)
    kanji_readings = load_kanji_dictionnary_readings()
    return build_reading_to_kanji_candidates(
        cards=cards,
        kanji_readings=kanji_readings,
        onyomi_readings=load_onyomi_readings(),
        kanji_meanings=load_kanji_meanings(),
        kanji_grades=load_kanji_grades(),
        kanji_frequencies=load_kanji_frequencies(),
        max_grade=READING_TO_KANJI_MAX_GRADE,
    )


def process_reading_to_kanji_cards(collection=None, dry_run=False):
    if collection is None:
        collection = mw.col

    candidates = build_candidates_from_collection(collection)
    deck_name = resolve_reading_to_kanji_deck_name()

    if dry_run:
        result = ReadingToKanjiUpsertResult(candidates=candidates)
    else:
        deck_id, notetype = ensure_reading_to_kanji_deck_and_notetype(
            collection,
            deck_name,
        )
        result = upsert_reading_to_kanji_notes(
            collection,
            candidates,
            deck_id,
            deck_name,
            notetype,
        )

    message = (
        f"Reading->Kanji cards: {len(candidates)} candidates\n"
        f"Created: {result.created}\n"
        f"Updated: {result.updated}\n"
        f"Skipped duplicate readings: {result.skipped_duplicates}\n"
        f"Repositioned cards: {result.repositioned}"
    )
    print(message)
    showInfo(message)
    return result
