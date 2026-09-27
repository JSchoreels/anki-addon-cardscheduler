import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from aqt.qt import QApplication

from cardscheduler.config import get_default_config
from cardscheduler.settings_dialog import (
    CardSchedulerSettingsDialog,
    available_deck_names,
    available_field_names,
)


class FakeNameId:
    def __init__(self, name):
        self.name = name


class FakeDeckManager:
    def all_names_and_ids(self, include_filtered=True):
        self.include_filtered = include_filtered
        return [
            FakeNameId("Japanese::Vocabulary"),
            FakeNameId("Default"),
            FakeNameId("Japanese::Vocabulary"),
        ]


class FakeNotetypeManager:
    def all(self):
        return [
            {"flds": [{"name": "Front"}, {"name": "Reading"}]},
            {"flds": [{"name": "Sentence"}, {"name": "Front"}]},
        ]


class FakeCollection:
    def __init__(self):
        self.decks = FakeDeckManager()
        self.models = FakeNotetypeManager()


class TestSettingsDialog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.dialog = CardSchedulerSettingsDialog(get_default_config())

    def tearDown(self):
        self.dialog.close()

    def test_round_trips_all_default_configuration(self):
        self.assertEqual(self.dialog.configured_values(), get_default_config())

    def test_collects_edited_general_automation_and_sentence_values(self):
        self.dialog._editable_combos[("deck_name",)].setCurrentText(
            "Japanese::Vocabulary"
        )
        self.dialog._checks[("automatic_processing", "enabled")].setChecked(False)
        self.dialog._checks[
            ("automatic_processing", "run_on_startup")
        ].setChecked(False)
        self.dialog._spins[("automatic_processing", "delay_ms")].setValue(2500)
        self.dialog._plain_text_edits[
            ("sentence_scoring", "deck_names")
        ].setPlainText("Japanese::Sentences\nJapanese::Audio")

        config = self.dialog.configured_values()

        self.assertEqual(config["deck_name"], "Japanese::Vocabulary")
        self.assertFalse(config["automatic_processing"]["enabled"])
        self.assertFalse(config["automatic_processing"]["run_on_startup"])
        self.assertTrue(config["automatic_processing"]["run_on_new_day"])
        self.assertEqual(config["automatic_processing"]["delay_ms"], 2500)
        self.assertEqual(
            config["sentence_scoring"]["deck_names"],
            ["Japanese::Sentences", "Japanese::Audio"],
        )

    def test_blank_reading_to_kanji_deck_is_saved_as_default_selection(self):
        self.dialog._editable_combos[
            ("reading_to_kanji_cards", "deck_name")
        ].setEditText("")

        config = self.dialog.configured_values()

        self.assertIsNone(config["reading_to_kanji_cards"]["deck_name"])

    def test_reads_sorted_unique_decks_and_fields_from_collection(self):
        collection = FakeCollection()

        self.assertEqual(
            available_deck_names(collection),
            ["Default", "Japanese::Vocabulary"],
        )
        self.assertFalse(collection.decks.include_filtered)
        self.assertEqual(
            available_field_names(collection),
            ["Front", "Reading", "Sentence"],
        )

    def test_deck_and_field_dropdowns_include_collection_choices(self):
        dialog = CardSchedulerSettingsDialog(
            get_default_config(),
            deck_names=["Default", "Japanese::Vocabulary"],
            field_names=["Front", "Reading", "Sentence"],
        )
        self.addCleanup(dialog.close)

        deck_combo = dialog._editable_combos[("deck_name",)]
        field_combo = dialog._editable_combos[("input_fields", "reading")]

        self.assertTrue(deck_combo.isEditable())
        self.assertTrue(field_combo.isEditable())
        self.assertIn(
            "Japanese::Vocabulary",
            [deck_combo.itemText(index) for index in range(deck_combo.count())],
        )
        self.assertIn(
            "Sentence",
            [field_combo.itemText(index) for index in range(field_combo.count())],
        )

    def test_editable_dropdowns_preserve_custom_values(self):
        self.dialog._editable_combos[("deck_name",)].setEditText(
            "Future::Vocabulary"
        )
        self.dialog._editable_combos[("input_fields", "reading")].setEditText(
            "Custom Reading"
        )

        config = self.dialog.configured_values()

        self.assertEqual(config["deck_name"], "Future::Vocabulary")
        self.assertEqual(config["input_fields"]["reading"], "Custom Reading")


if __name__ == "__main__":
    unittest.main()
