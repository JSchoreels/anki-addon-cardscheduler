import unittest
from unittest.mock import patch

from cardscheduler.reading_to_kanji_cards import (
    ReadingToKanjiCandidate,
    ReadingToKanjiEntry,
    build_candidates_from_collection,
    build_reading_to_kanji_candidates,
    ensure_reading_to_kanji_deck_and_notetype,
    format_candidate_fields,
    process_reading_to_kanji_cards,
    resolve_reading_to_kanji_deck_name,
    upsert_reading_to_kanji_notes,
)
from cardscheduler.scheduler import CardInfo


class TestReadingToKanjiCards(unittest.TestCase):
    def test_includes_all_possible_kanji_and_orders_supported_first(self):
        known_card = CardInfo(1, "校[こう]", 10)
        unknown_card = CardInfo(2, "工[こう]", 0)

        with patch(
            "cardscheduler.reading_to_kanji_cards.build_card_to_pairs",
            return_value={
                1: {"校[こう]"},
                2: {"工[こう]"},
            },
        ):
            candidates = build_reading_to_kanji_candidates(
                cards=[known_card, unknown_card],
                kanji_readings={},
                onyomi_readings={
                    "校": {"こう": ["こう"]},
                    "工": {"こう": ["こう"]},
                },
                kanji_meanings={
                    "校": ["school"],
                    "工": ["construction"],
                },
                kanji_grades={
                    "校": 1,
                    "工": 2,
                },
                kanji_frequencies={
                    "校": 298,
                    "工": 299,
                },
                max_grade=8,
            )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].reading, "こう")
        self.assertEqual([entry.kanji for entry in candidates[0].entries], ["校", "工"])
        self.assertEqual(candidates[0].entries[0].known_words, ["校[こう]"])
        self.assertEqual(candidates[0].entries[1].known_words, [])

    def test_sokuon_known_word_supports_dictionary_reading_only(self):
        known_card = CardInfo(1, "学[がっ]", 10)

        with patch(
            "cardscheduler.reading_to_kanji_cards.build_card_to_pairs",
            return_value={1: {"学[がっ]"}},
        ):
            candidates = build_reading_to_kanji_candidates(
                cards=[known_card],
                kanji_readings={},
                onyomi_readings={
                    "学": {"がく": ["がく", "がっ"]},
                },
                kanji_meanings={"学": ["study"]},
                kanji_grades={"学": 1},
                kanji_frequencies={"学": 63},
                max_grade=8,
            )

        self.assertEqual([candidate.reading for candidate in candidates], ["がく"])
        self.assertEqual(candidates[0].entries[0].known_words, ["学[がっ]"])

    def test_rendaku_reading_includes_possible_kanji_from_base_onyomi(self):
        known_card = CardInfo(1, "日[じつ]", 10)

        with patch(
            "cardscheduler.reading_to_kanji_cards.build_card_to_pairs",
            return_value={1: {"日[じつ]"}},
        ):
            candidates = build_reading_to_kanji_candidates(
                cards=[known_card],
                kanji_readings={},
                onyomi_readings={
                    "日": {"じつ": ["じつ"]},
                    "実": {"しつ": ["しつ", "じつ", "しっ", "じっ"]},
                },
                kanji_meanings={
                    "日": ["day"],
                    "実": ["truth"],
                },
                kanji_grades={
                    "日": 1,
                    "実": 3,
                },
                kanji_frequencies={
                    "日": 1,
                    "実": 68,
                },
                max_grade=8,
            )

        self.assertIn("じつ", [candidate.reading for candidate in candidates])
        candidate = next(
            candidate for candidate in candidates if candidate.reading == "じつ"
        )
        self.assertEqual([entry.kanji for entry in candidate.entries], ["日", "実"])

    def test_rendaku_known_word_supports_rendaku_reading(self):
        known_card = CardInfo(1, "実[じつ]", 10)

        with patch(
            "cardscheduler.reading_to_kanji_cards.build_card_to_pairs",
            return_value={1: {"実[じつ]"}},
        ):
            candidates = build_reading_to_kanji_candidates(
                cards=[known_card],
                kanji_readings={},
                onyomi_readings={
                    "実": {"しつ": ["しつ", "じつ", "しっ", "じっ"]},
                },
                kanji_meanings={"実": ["truth"]},
                kanji_grades={"実": 3},
                kanji_frequencies={"実": 68},
                max_grade=8,
            )

        self.assertEqual([candidate.reading for candidate in candidates], ["じつ"])
        self.assertEqual(candidates[0].entries[0].known_words, ["実[じつ]"])

    def test_malformed_known_pair_does_not_create_candidate(self):
        known_card = CardInfo(1, "学がく", 10)

        with patch(
            "cardscheduler.reading_to_kanji_cards.build_card_to_pairs",
            return_value={1: {"学がく"}},
        ):
            candidates = build_reading_to_kanji_candidates(
                cards=[known_card],
                kanji_readings={},
                onyomi_readings={
                    "学": {"がく": ["がく"]},
                },
                kanji_meanings={"学": ["study"]},
                kanji_grades={"学": 1},
                kanji_frequencies={"学": 63},
                max_grade=8,
            )

        self.assertEqual(candidates, [])

    def test_grade_filter_removes_possible_kanji_candidates(self):
        known_card = CardInfo(1, "巧[こう]", 10)

        with patch(
            "cardscheduler.reading_to_kanji_cards.build_card_to_pairs",
            return_value={1: {"巧[こう]"}},
        ):
            candidates = build_reading_to_kanji_candidates(
                cards=[known_card],
                kanji_readings={},
                onyomi_readings={
                    "巧": {"こう": ["こう"]},
                },
                kanji_meanings={"巧": ["skill"]},
                kanji_grades={"巧": 9},
                kanji_frequencies={"巧": 1669},
                max_grade=8,
            )

        self.assertEqual(candidates, [])

    def test_candidates_order_by_number_of_possible_kanji_first(self):
        cards = [
            CardInfo(1, "鬱[うつ]", 10),
            CardInfo(2, "校[こう]", 10),
        ]

        with patch(
            "cardscheduler.reading_to_kanji_cards.build_card_to_pairs",
            return_value={
                1: {"鬱[うつ]"},
                2: {"校[こう]"},
            },
        ):
            candidates = build_reading_to_kanji_candidates(
                cards=cards,
                kanji_readings={},
                onyomi_readings={
                    "鬱": {"うつ": ["うつ"]},
                    "校": {"こう": ["こう"]},
                    "工": {"こう": ["こう"]},
                },
                kanji_meanings={},
                kanji_grades={"鬱": 8, "校": 1, "工": 2},
                kanji_frequencies={"鬱": 1800, "校": 298, "工": 299},
                max_grade=8,
            )

        self.assertEqual([candidate.reading for candidate in candidates], ["うつ", "こう"])

    def test_format_candidate_fields(self):
        candidate = ReadingToKanjiCandidate(
            reading="こう",
            entries=[
                ReadingToKanjiEntry(
                    kanji="校",
                    meanings=["school", "exam"],
                    grade=1,
                    frequency=298,
                    known_words=["学校[がっこう]", "校長[こうちょう]"],
                )
            ],
        )

        fields = format_candidate_fields(candidate)

        self.assertEqual(fields["Reading"], "こう")
        self.assertIn("<b>校</b> - school; exam", fields["Kanji Meaning"])
        self.assertEqual(fields["Matching Kanji Count"], "1")
        self.assertIn("<b>校</b>: 1", fields["Grade"])
        self.assertIn("<b>校</b>: 298", fields["Frequency"])
        self.assertIn('<span class="known-word">学校[がっこう]</span>', fields["Known Words"])
        self.assertIn(",　 ", fields["Known Words"])
        self.assertIn("学校[がっこう]", fields["Known Words"])

    def test_format_candidate_fields_uses_na_for_missing_metadata(self):
        candidate = ReadingToKanjiCandidate(
            reading="こう",
            entries=[
                ReadingToKanjiEntry(
                    kanji="工",
                    meanings=[],
                    grade=None,
                    frequency=None,
                    known_words=[],
                )
            ],
        )

        fields = format_candidate_fields(candidate)

        self.assertIn("<b>工</b> - N/A", fields["Kanji Meaning"])
        self.assertIn("<b>工</b>: N/A", fields["Grade"])
        self.assertIn("<b>工</b>: N/A", fields["Frequency"])
        self.assertIn("<b>工</b>: N/A", fields["Known Words"])


class FakeChange:
    def __init__(self, id):
        self.id = id


class FakeDecks:
    def __init__(self):
        self.created_names = []
        self.existing_names = set()

    def id_for_name(self, name):
        return 42 if name in self.existing_names else None

    def add_normal_deck_with_name(self, name):
        self.created_names.append(name)
        self.existing_names.add(name)
        return FakeChange(42)


class FakeModels:
    def __init__(self):
        self.notetypes = {}

    def by_name(self, name):
        return self.notetypes.get(name)

    def new(self, name):
        return {"id": 0, "name": name, "flds": [], "tmpls": []}

    def new_field(self, name):
        return {"name": name, "ord": None}

    def add_field(self, notetype, field):
        field["ord"] = len(notetype["flds"])
        notetype["flds"].append(field)

    def new_template(self, name):
        return {"name": name, "qfmt": "", "afmt": "", "ord": None}

    def add_template(self, notetype, template):
        template["ord"] = len(notetype["tmpls"])
        notetype["tmpls"].append(template)

    def add_dict(self, notetype):
        notetype["id"] = len(self.notetypes) + 1
        self.notetypes[notetype["name"]] = notetype
        return FakeChange(notetype["id"])

    def update_dict(self, notetype):
        self.notetypes[notetype["name"]] = notetype


class FakeSched:
    def __init__(self):
        self.repositioned_card_ids = []

    def reposition_new_cards(self, card_ids, **_kwargs):
        self.repositioned_card_ids = list(card_ids)


class FakeGeneratedNote:
    next_id = 1

    def __init__(self, notetype, card_id):
        self.id = FakeGeneratedNote.next_id
        FakeGeneratedNote.next_id += 1
        self._card_id = card_id
        self._fields = {field["name"]: "" for field in notetype["flds"]}

    def __getitem__(self, key):
        return self._fields[key]

    def __setitem__(self, key, value):
        self._fields[key] = value

    def card_ids(self):
        return [self._card_id]


class FakeNoteWithoutCardIds:
    def __init__(self, notetype, note_id):
        self.id = note_id
        self._fields = {field["name"]: "" for field in notetype["flds"]}

    def __getitem__(self, key):
        return self._fields[key]

    def __setitem__(self, key, value):
        self._fields[key] = value


class FakeGeneratedCollection:
    def __init__(self):
        self.decks = FakeDecks()
        self.models = FakeModels()
        self.sched = FakeSched()
        self.notes = {}
        self.next_card_id = 100
        self.updated_notes = []

    def find_notes(self, _query):
        return list(self.notes.keys())

    def get_note(self, note_id):
        return self.notes[note_id]

    def new_note(self, notetype):
        self.next_card_id += 1
        return FakeGeneratedNote(notetype, self.next_card_id)

    def add_note(self, note, _deck_id):
        self.notes[note.id] = note

    def update_note(self, note):
        self.updated_notes.append(note)


class FakeCollectionWithCardIdLookup(FakeGeneratedCollection):
    def card_ids_of_note(self, note_id):
        return [note_id + 1000]


class TestReadingToKanjiAnkiOperations(unittest.TestCase):
    def test_resolve_reading_to_kanji_deck_name_defaults_under_vocab_deck(self):
        self.assertEqual(
            resolve_reading_to_kanji_deck_name(),
            "Japan::4. Recall::Reading->Kanji",
        )

    def test_resolve_reading_to_kanji_deck_name_uses_configured_deck(self):
        self.assertEqual(
            resolve_reading_to_kanji_deck_name("Generated"),
            "Generated",
        )

    @patch("cardscheduler.reading_to_kanji_cards.mw")
    def test_creates_deck_and_note_type_when_missing(self, mw_mock):
        collection = FakeGeneratedCollection()

        deck_id, notetype = ensure_reading_to_kanji_deck_and_notetype(
            collection,
            "Japan::1. Vocabulary::Reading->Kanji",
        )

        self.assertEqual(deck_id, 42)
        self.assertEqual(notetype["name"], "CardScheduler Reading->Kanji")
        self.assertEqual(
            [field["name"] for field in notetype["flds"]],
            [
                "Reading",
                "Kanji Meaning",
                "Matching Kanji Count",
                "Grade",
                "Frequency",
                "Known Words",
            ],
        )
        self.assertIn("{{Reading}}", notetype["tmpls"][0]["qfmt"])
        self.assertIn(
            "Kanji Count : {{Matching Kanji Count}}",
            notetype["tmpls"][0]["afmt"],
        )
        self.assertIn(
            "Matching Kanjis : {{furigana:Kanji Meaning}}",
            notetype["tmpls"][0]["afmt"],
        )
        self.assertIn(
            "Known Words : {{furigana:Known Words}}",
            notetype["tmpls"][0]["afmt"],
        )
        mw_mock.reset.assert_called_once_with()

    @patch("cardscheduler.reading_to_kanji_cards.mw")
    def test_does_not_refresh_ui_when_deck_and_note_type_exist(self, mw_mock):
        collection = FakeGeneratedCollection()
        deck_name = "Japan::1. Vocabulary::Reading->Kanji"
        ensure_reading_to_kanji_deck_and_notetype(collection, deck_name)
        mw_mock.reset.reset_mock()

        ensure_reading_to_kanji_deck_and_notetype(collection, deck_name)

        mw_mock.reset.assert_not_called()

    @patch("cardscheduler.reading_to_kanji_cards.mw")
    def test_updates_existing_note_type_with_new_field_without_overriding_template(
        self,
        mw_mock,
    ):
        collection = FakeGeneratedCollection()
        deck_name = "Japan::1. Vocabulary::Reading->Kanji"
        collection.decks.existing_names.add(deck_name)
        custom_template = "{{Known Words}}"
        collection.models.notetypes["CardScheduler Reading->Kanji"] = {
            "id": 1,
            "name": "CardScheduler Reading->Kanji",
            "flds": [
                {"name": "Reading"},
                {"name": "Kanji Meaning"},
                {"name": "Grade"},
                {"name": "Frequency"},
                {"name": "Known Words"},
            ],
            "tmpls": [
                {
                    "name": "Reading -> Kanji",
                    "qfmt": "{{Reading}}",
                    "afmt": custom_template,
                }
            ],
        }

        _deck_id, notetype = ensure_reading_to_kanji_deck_and_notetype(
            collection,
            deck_name,
        )

        self.assertIn(
            "Matching Kanji Count",
            [field["name"] for field in notetype["flds"]],
        )
        self.assertEqual(custom_template, notetype["tmpls"][0]["afmt"])
        mw_mock.reset.assert_called_once_with()

    @patch("cardscheduler.reading_to_kanji_cards.mw")
    def test_adds_template_when_existing_note_type_has_no_template(self, mw_mock):
        collection = FakeGeneratedCollection()
        deck_name = "Japan::1. Vocabulary::Reading->Kanji"
        collection.decks.existing_names.add(deck_name)
        collection.models.notetypes["CardScheduler Reading->Kanji"] = {
            "id": 1,
            "name": "CardScheduler Reading->Kanji",
            "flds": [
                {"name": "Reading"},
                {"name": "Kanji Meaning"},
                {"name": "Matching Kanji Count"},
                {"name": "Grade"},
                {"name": "Frequency"},
                {"name": "Known Words"},
            ],
            "tmpls": [],
        }

        _deck_id, notetype = ensure_reading_to_kanji_deck_and_notetype(
            collection,
            deck_name,
        )

        self.assertEqual(len(notetype["tmpls"]), 1)
        self.assertIn(
            "Kanji Count : {{Matching Kanji Count}}",
            notetype["tmpls"][0]["afmt"],
        )
        mw_mock.reset.assert_called_once_with()

    def test_upsert_repositions_generated_cards_in_candidate_order(self):
        collection = FakeGeneratedCollection()
        deck_id, notetype = ensure_reading_to_kanji_deck_and_notetype(
            collection,
            "Japan::1. Vocabulary::Reading->Kanji",
        )
        candidates = [
            ReadingToKanjiCandidate(
                reading="うつ",
                entries=[
                    ReadingToKanjiEntry("鬱", ["gloom"], 8, 1800, ["鬱[うつ]"])
                ],
            ),
            ReadingToKanjiCandidate(
                reading="こう",
                entries=[
                    ReadingToKanjiEntry("校", ["school"], 1, 298, ["校[こう]"]),
                    ReadingToKanjiEntry("工", ["construction"], 2, 299, []),
                ],
            ),
        ]

        result = upsert_reading_to_kanji_notes(
            collection,
            candidates,
            deck_id,
            "Japan::1. Vocabulary::Reading->Kanji",
            notetype,
        )

        self.assertEqual(result.created, 2)
        self.assertEqual(collection.sched.repositioned_card_ids, [101, 102])

    def test_upsert_updates_existing_note(self):
        collection = FakeGeneratedCollection()
        deck_id, notetype = ensure_reading_to_kanji_deck_and_notetype(
            collection,
            "Japan::1. Vocabulary::Reading->Kanji",
        )
        note = collection.new_note(notetype)
        note["Reading"] = "こう"
        collection.add_note(note, deck_id)
        candidates = [
            ReadingToKanjiCandidate(
                reading="こう",
                entries=[
                    ReadingToKanjiEntry("校", ["school"], 1, 298, ["校[こう]"]),
                ],
            ),
        ]

        result = upsert_reading_to_kanji_notes(
            collection,
            candidates,
            deck_id,
            "Japan::1. Vocabulary::Reading->Kanji",
            notetype,
        )

        self.assertEqual(result.updated, 1)
        self.assertEqual(collection.updated_notes, [note])
        self.assertIn("school", note["Kanji Meaning"])

    def test_upsert_ignores_existing_note_without_reading(self):
        collection = FakeGeneratedCollection()
        deck_id, notetype = ensure_reading_to_kanji_deck_and_notetype(
            collection,
            "Japan::1. Vocabulary::Reading->Kanji",
        )
        blank_note = collection.new_note(notetype)
        blank_note["Reading"] = ""
        collection.add_note(blank_note, deck_id)
        candidates = [
            ReadingToKanjiCandidate(
                reading="こう",
                entries=[
                    ReadingToKanjiEntry("校", ["school"], 1, 298, ["校[こう]"]),
                ],
            ),
        ]

        result = upsert_reading_to_kanji_notes(
            collection,
            candidates,
            deck_id,
            "Japan::1. Vocabulary::Reading->Kanji",
            notetype,
        )

        self.assertEqual(result.created, 1)

    def test_upsert_can_use_collection_card_id_lookup(self):
        collection = FakeCollectionWithCardIdLookup()
        deck_id, notetype = ensure_reading_to_kanji_deck_and_notetype(
            collection,
            "Japan::1. Vocabulary::Reading->Kanji",
        )
        note = FakeNoteWithoutCardIds(notetype, 7)
        note["Reading"] = "こう"
        collection.notes[note.id] = note
        candidates = [
            ReadingToKanjiCandidate(
                reading="こう",
                entries=[
                    ReadingToKanjiEntry("校", ["school"], 1, 298, ["校[こう]"]),
                ],
            ),
        ]

        result = upsert_reading_to_kanji_notes(
            collection,
            candidates,
            deck_id,
            "Japan::1. Vocabulary::Reading->Kanji",
            notetype,
        )

        self.assertEqual(result.repositioned, 1)
        self.assertEqual(collection.sched.repositioned_card_ids, [1007])

    def test_upsert_skips_duplicate_existing_reading(self):
        collection = FakeGeneratedCollection()
        deck_id, notetype = ensure_reading_to_kanji_deck_and_notetype(
            collection,
            "Japan::1. Vocabulary::Reading->Kanji",
        )
        first_note = collection.new_note(notetype)
        first_note["Reading"] = "こう"
        collection.add_note(first_note, deck_id)
        second_note = collection.new_note(notetype)
        second_note["Reading"] = "こう"
        collection.add_note(second_note, deck_id)
        candidates = [
            ReadingToKanjiCandidate(
                reading="こう",
                entries=[
                    ReadingToKanjiEntry("校", ["school"], 1, 298, ["校[こう]"]),
                ],
            ),
        ]

        result = upsert_reading_to_kanji_notes(
            collection,
            candidates,
            deck_id,
            "Japan::1. Vocabulary::Reading->Kanji",
            notetype,
        )

        self.assertEqual(result.skipped_duplicates, 1)
        self.assertEqual(result.created, 0)
        self.assertEqual(result.updated, 0)
        self.assertEqual(result.repositioned, 0)

    @patch("cardscheduler.reading_to_kanji_cards.build_reading_to_kanji_candidates")
    @patch("cardscheduler.reading_to_kanji_cards.load_kanji_frequencies")
    @patch("cardscheduler.reading_to_kanji_cards.load_kanji_grades")
    @patch("cardscheduler.reading_to_kanji_cards.load_onyomi_readings")
    @patch("cardscheduler.reading_to_kanji_cards.load_kanji_meanings")
    @patch("cardscheduler.reading_to_kanji_cards.load_kanji_dictionnary_readings")
    @patch("cardscheduler.reading_to_kanji_cards.load_cards")
    def test_build_candidates_from_collection_uses_configured_sources(
        self,
        load_cards_mock,
        load_kanji_readings_mock,
        load_meanings_mock,
        load_onyomi_mock,
        load_grades_mock,
        load_frequencies_mock,
        build_candidates_mock,
    ):
        collection = FakeGeneratedCollection()
        cards = [CardInfo(1, "校[こう]", 10)]
        load_cards_mock.return_value = cards
        load_kanji_readings_mock.return_value = {"校": {"こう": ["こう"]}}
        load_meanings_mock.return_value = {"校": ["school"]}
        load_onyomi_mock.return_value = {"校": {"こう": ["こう"]}}
        load_grades_mock.return_value = {"校": 1}
        load_frequencies_mock.return_value = {"校": 298}
        build_candidates_mock.return_value = []

        self.assertEqual(build_candidates_from_collection(collection), [])

        load_cards_mock.assert_called_once_with(collection, frequency_field_name=None)
        build_candidates_mock.assert_called_once_with(
            cards=cards,
            kanji_readings={"校": {"こう": ["こう"]}},
            onyomi_readings={"校": {"こう": ["こう"]}},
            kanji_meanings={"校": ["school"]},
            kanji_grades={"校": 1},
            kanji_frequencies={"校": 298},
            max_grade=8,
        )

    @patch("cardscheduler.reading_to_kanji_cards.showInfo")
    @patch("builtins.print")
    @patch("cardscheduler.reading_to_kanji_cards.build_candidates_from_collection")
    def test_process_reading_to_kanji_cards_supports_dry_run(
        self,
        build_candidates_mock,
        print_mock,
        show_info_mock,
    ):
        collection = FakeGeneratedCollection()
        build_candidates_mock.return_value = [
            ReadingToKanjiCandidate(
                reading="こう",
                entries=[
                    ReadingToKanjiEntry("校", ["school"], 1, 298, ["校[こう]"]),
                ],
            ),
        ]

        result = process_reading_to_kanji_cards(collection=collection, dry_run=True)

        self.assertEqual(result.created, 0)
        self.assertEqual(result.updated, 0)
        self.assertEqual(len(result.candidates), 1)
        print_mock.assert_called_once()
        show_info_mock.assert_called_once()

    @patch("cardscheduler.reading_to_kanji_cards.showInfo")
    @patch("builtins.print")
    @patch("cardscheduler.reading_to_kanji_cards.upsert_reading_to_kanji_notes")
    @patch("cardscheduler.reading_to_kanji_cards.ensure_reading_to_kanji_deck_and_notetype")
    @patch("cardscheduler.reading_to_kanji_cards.build_candidates_from_collection")
    def test_process_reading_to_kanji_cards_upserts_when_not_dry_run(
        self,
        build_candidates_mock,
        ensure_mock,
        upsert_mock,
        print_mock,
        show_info_mock,
    ):
        collection = FakeGeneratedCollection()
        candidates = [
            ReadingToKanjiCandidate(
                reading="こう",
                entries=[
                    ReadingToKanjiEntry("校", ["school"], 1, 298, ["校[こう]"]),
                ],
            ),
        ]
        notetype = {"name": "CardScheduler Reading->Kanji"}
        build_candidates_mock.return_value = candidates
        ensure_mock.return_value = (42, notetype)
        upsert_mock.return_value = type(
            "Result",
            (),
            {
                "candidates": candidates,
                "created": 1,
                "updated": 0,
                "skipped_duplicates": 0,
                "repositioned": 1,
            },
        )()

        result = process_reading_to_kanji_cards(collection=collection)

        ensure_mock.assert_called_once_with(
            collection,
            "Japan::4. Recall::Reading->Kanji",
        )
        upsert_mock.assert_called_once_with(
            collection,
            candidates,
            42,
            "Japan::4. Recall::Reading->Kanji",
            notetype,
        )
        self.assertEqual(result.created, 1)
        print_mock.assert_called_once()
        show_info_mock.assert_called_once()

    @patch("cardscheduler.reading_to_kanji_cards.showInfo")
    @patch("builtins.print")
    @patch("cardscheduler.reading_to_kanji_cards.mw")
    @patch("cardscheduler.reading_to_kanji_cards.build_candidates_from_collection")
    def test_process_reading_to_kanji_cards_defaults_to_mw_collection(
        self,
        build_candidates_mock,
        mw_mock,
        print_mock,
        show_info_mock,
    ):
        collection = FakeGeneratedCollection()
        mw_mock.col = collection
        build_candidates_mock.return_value = []

        process_reading_to_kanji_cards(dry_run=True)

        build_candidates_mock.assert_called_once_with(collection)
        print_mock.assert_called_once()
        show_info_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
