import unittest
from unittest.mock import patch

from cardscheduler.anki_interface import (
    process_collection,
    process_related_words,
    update_card_fields,
)
from cardscheduler.scheduler import CardInfo


class FakeNote:
    def __init__(self, field_names):
        self._note_type = {"flds": [{"name": name} for name in field_names]}
        self.fields = [""] * len(field_names)

    def note_type(self):
        return self._note_type


class FakeCard:
    def __init__(self, note):
        self._note = note

    def note(self):
        return self._note


class FakeCollection:
    def __init__(self, card):
        self._card = card
        self.updated_notes = []
        self.searches = []

    def get_card(self, _card_id):
        return self._card

    def update_note(self, note):
        self.updated_notes.append(note)

    def find_cards(self, _query):
        self.searches.append(_query)
        return []


class TestScoreFieldFormatting(unittest.TestCase):
    def _build_card_info(self, score=0.0, unlock_median_score_increase=0.0, score_without_missing=0.0):
        card_info = CardInfo(1, "学校[がっこう]", 0)
        card_info.score = score
        card_info.unlock_median_score_increase = unlock_median_score_increase
        card_info.score_without_missing = score_without_missing
        return card_info

    @patch("cardscheduler.anki_interface.format_card_html", return_value=("", "", ""))
    def test_score_zero_displays_three_decimals(self, _mock_html):
        field_name = "CardScheduler.Score"
        note = FakeNote([field_name])
        collection = FakeCollection(FakeCard(note))

        update_card_fields(
            self._build_card_info(0.0),
            collection,
            kanji_meanings={},
            kanji_readings={},
            score_field=field_name,
            available_fields={field_name},
        )

        self.assertEqual(note.fields[0], "0.000")

    @patch("cardscheduler.anki_interface.format_card_html", return_value=("", "", ""))
    def test_tiny_non_zero_score_is_visible(self, _mock_html):
        field_name = "CardScheduler.Score"
        note = FakeNote([field_name])
        collection = FakeCollection(FakeCard(note))

        update_card_fields(
            self._build_card_info(0.0001),
            collection,
            kanji_meanings={},
            kanji_readings={},
            score_field=field_name,
            available_fields={field_name},
        )

        self.assertEqual(note.fields[0], "0.001")

    @patch("cardscheduler.anki_interface.format_card_html", return_value=("", "", ""))
    def test_non_zero_score_uses_three_decimals_rounded_up(self, _mock_html):
        field_name = "CardScheduler.Score"
        note = FakeNote([field_name])
        collection = FakeCollection(FakeCard(note))

        update_card_fields(
            self._build_card_info(1.2341),
            collection,
            kanji_meanings={},
            kanji_readings={},
            score_field=field_name,
            available_fields={field_name},
        )

        self.assertEqual(note.fields[0], "1.235")

    @patch("cardscheduler.anki_interface.format_card_html", return_value=("", "", ""))
    def test_unlock_median_score_increase_tiny_non_zero_is_visible(self, _mock_html):
        field_name = "CardScheduler.UnlockMedianScoreIncrease"
        note = FakeNote([field_name])
        collection = FakeCollection(FakeCard(note))

        update_card_fields(
            self._build_card_info(unlock_median_score_increase=0.0001),
            collection,
            kanji_meanings={},
            kanji_readings={},
            unlock_median_score_increase_field=field_name,
            available_fields={field_name},
        )

        self.assertEqual(note.fields[0], "0.001")

    @patch("cardscheduler.anki_interface.format_card_html", return_value=("", "", ""))
    def test_score_without_missing_non_zero_uses_three_decimals_rounded_up(self, _mock_html):
        field_name = "CardScheduler.ScoreWithoutMissing"
        note = FakeNote([field_name])
        collection = FakeCollection(FakeCard(note))

        update_card_fields(
            self._build_card_info(score_without_missing=2.3001),
            collection,
            kanji_meanings={},
            kanji_readings={},
            score_without_missing_field=field_name,
            available_fields={field_name},
        )

        self.assertEqual(note.fields[0], "2.301")

    @patch("cardscheduler.anki_interface.format_card_html", return_value=("", "", ""))
    def test_zero_values_keep_three_decimals_for_all_score_fields(self, _mock_html):
        field_names = [
            "CardScheduler.Score",
            "CardScheduler.UnlockMedianScoreIncrease",
            "CardScheduler.ScoreWithoutMissing",
        ]
        note = FakeNote(field_names)
        collection = FakeCollection(FakeCard(note))

        update_card_fields(
            self._build_card_info(score=0.0, unlock_median_score_increase=0.0, score_without_missing=0.0),
            collection,
            kanji_meanings={},
            kanji_readings={},
            score_field=field_names[0],
            unlock_median_score_increase_field=field_names[1],
            score_without_missing_field=field_names[2],
            available_fields=set(field_names),
        )

        self.assertEqual(note.fields[0], "0.000")
        self.assertEqual(note.fields[1], "0.000")
        self.assertEqual(note.fields[2], "0.000")

    @patch("cardscheduler.anki_interface.format_card_html")
    def test_score_update_can_skip_related_display_fields(self, mock_html):
        field_names = [
            "CardScheduler.Score",
            "CardScheduler.Related.Known",
            "CardScheduler.Related.Unknown",
            "CardScheduler.KanjiMeanings",
        ]
        note = FakeNote(field_names)
        collection = FakeCollection(FakeCard(note))

        update_card_fields(
            self._build_card_info(score=1.0),
            collection,
            kanji_meanings={},
            kanji_readings={},
            score_field=field_names[0],
            available_fields=set(field_names),
            update_related_fields=False,
            update_kanji_meanings_field=False,
        )

        self.assertEqual(note.fields[0], "1.000")
        self.assertEqual(note.fields[1], "")
        self.assertEqual(note.fields[2], "")
        self.assertEqual(note.fields[3], "")
        mock_html.assert_not_called()

    @patch(
        "cardscheduler.anki_interface.format_card_html",
        return_value=("known html", "unknown html", "meaning html"),
    )
    def test_related_update_can_skip_score_fields(self, _mock_html):
        field_names = [
            "CardScheduler.Score",
            "CardScheduler.Related.Known",
            "CardScheduler.Related.Unknown",
            "CardScheduler.KanjiMeanings",
        ]
        note = FakeNote(field_names)
        collection = FakeCollection(FakeCard(note))

        update_card_fields(
            self._build_card_info(score=1.0),
            collection,
            kanji_meanings={},
            kanji_readings={},
            score_field=field_names[0],
            available_fields=set(field_names),
            update_score_fields=False,
            update_related_fields=True,
            update_kanji_meanings_field=True,
        )

        self.assertEqual(note.fields[0], "")
        self.assertEqual(note.fields[1], "known html")
        self.assertEqual(note.fields[2], "unknown html")
        self.assertEqual(note.fields[3], "meaning html")


class TestRelatedWordsProcessing(unittest.TestCase):
    @patch("cardscheduler.anki_interface.showInfo")
    @patch("cardscheduler.anki_interface.update_cards_score", return_value=0)
    @patch("cardscheduler.anki_interface.detect_available_fields", return_value=set())
    @patch("cardscheduler.anki_interface.print_scores")
    @patch("cardscheduler.anki_interface.assign_positions_to_new_cards")
    @patch("cardscheduler.anki_interface.compute_scores")
    @patch("cardscheduler.anki_interface.load_cards", return_value=[])
    def test_process_collection_skips_related_display_fields(
        self,
        _load_cards_mock,
        _compute_scores_mock,
        _assign_positions_mock,
        _print_scores_mock,
        _detect_fields_mock,
        update_cards_score_mock,
        _show_info_mock,
    ):
        process_collection(collection=FakeCollection(FakeCard(FakeNote([]))))

        update_cards_score_mock.assert_called_once()
        kwargs = update_cards_score_mock.call_args.kwargs
        self.assertFalse(kwargs["update_related_fields"])
        self.assertFalse(kwargs["update_kanji_meanings_field"])

    @patch("cardscheduler.anki_interface.DECK_NAME", "Custom::Vocabulary")
    @patch("cardscheduler.anki_interface.update_cards_score", return_value=0)
    @patch("cardscheduler.anki_interface.detect_available_fields", return_value=set())
    @patch("cardscheduler.anki_interface.print_scores")
    @patch("cardscheduler.anki_interface.assign_positions_to_new_cards")
    @patch("cardscheduler.anki_interface.compute_scores")
    @patch("cardscheduler.anki_interface.load_cards", return_value=[])
    def test_process_collection_uses_configured_deck_for_new_cards(
        self,
        _load_cards_mock,
        _compute_scores_mock,
        _assign_positions_mock,
        _print_scores_mock,
        _detect_fields_mock,
        _update_cards_score_mock,
    ):
        collection = FakeCollection(FakeCard(FakeNote([])))

        process_collection(
            collection=collection,
            show_summary=False,
        )

        self.assertIn('"deck:Custom::Vocabulary" is:new', collection.searches)

    @patch("cardscheduler.anki_interface.showInfo")
    @patch("cardscheduler.anki_interface.update_card_fields", return_value=True)
    @patch(
        "cardscheduler.anki_interface.detect_available_fields",
        return_value={
            "CardScheduler.Related.Known",
            "CardScheduler.Related.Unknown",
            "CardScheduler.KanjiMeanings",
        },
    )
    @patch("cardscheduler.anki_interface.compute_related_words")
    @patch("cardscheduler.anki_interface.build_card_to_pairs", return_value={1: set()})
    @patch("cardscheduler.dictionary.load_kanji_meanings", return_value={})
    @patch("cardscheduler.dictionary.load_kanji_dictionnary_readings", return_value={})
    @patch("cardscheduler.anki_interface.load_cards")
    def test_process_related_words_updates_only_related_display_fields(
        self,
        load_cards_mock,
        _load_readings_mock,
        _load_meanings_mock,
        _build_pairs_mock,
        compute_related_mock,
        _detect_fields_mock,
        update_card_fields_mock,
        _show_info_mock,
    ):
        collection = object()
        card = CardInfo(1, "学校[がっこう]", 0)
        load_cards_mock.return_value = [card]

        update_count = process_related_words(collection=collection)

        self.assertEqual(update_count, 1)
        compute_related_mock.assert_called_once_with([card], {1: set()})
        update_card_fields_mock.assert_called_once()
        kwargs = update_card_fields_mock.call_args.kwargs
        self.assertFalse(kwargs["update_score_fields"])
        self.assertTrue(kwargs["update_related_fields"])
        self.assertTrue(kwargs["update_kanji_meanings_field"])


if __name__ == "__main__":
    unittest.main()
