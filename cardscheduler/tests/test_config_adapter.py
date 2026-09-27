import json
import tempfile
import unittest

from cardscheduler.anki_config_adapter import (
    load_anki_addon_config,
    write_anki_addon_config,
)
from cardscheduler.config import _load_config, get_default_config, validate_config


class FakeAddonManager:
    def __init__(self, configs):
        self.configs = configs
        self.requested_module_names = []
        self.written_configs = []

    def getConfig(self, module_name):
        self.requested_module_names.append(module_name)
        return self.configs.get(module_name)

    def writeConfig(self, module_name, config):
        self.written_configs.append((module_name, config))


class FakeMw:
    def __init__(self, addon_manager=None):
        self.addonManager = addon_manager


class TestAnkiConfigAdapter(unittest.TestCase):
    def test_loads_config_for_addon_package_name(self):
        addon_manager = FakeAddonManager(
            {
                "123456": {
                    "deck_name": "Japanese",
                },
            }
        )

        config = load_anki_addon_config(
            "123456.cardscheduler.config",
            mw_instance=FakeMw(addon_manager),
        )

        self.assertEqual(config, {"deck_name": "Japanese"})
        self.assertEqual(addon_manager.requested_module_names, ["123456"])

    def test_returns_none_without_addon_manager(self):
        self.assertIsNone(
            load_anki_addon_config(
                "123456.cardscheduler.config",
                mw_instance=object(),
            )
        )

    def test_returns_none_for_non_dict_config(self):
        addon_manager = FakeAddonManager({"123456": None})

        self.assertIsNone(
            load_anki_addon_config(
                "123456.cardscheduler.config",
                mw_instance=FakeMw(addon_manager),
            )
        )

    def test_writes_config_for_addon_package_name(self):
        addon_manager = FakeAddonManager({})
        config = {"deck_name": "Japanese"}

        write_anki_addon_config(
            "123456.cardscheduler.settings_dialog",
            config,
            mw_instance=FakeMw(addon_manager),
        )

        self.assertEqual(
            addon_manager.written_configs,
            [("123456", config)],
        )

    def test_load_config_prefers_anki_config(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as config_file:
            json.dump({"deck_name": "Local"}, config_file)
            config_file.flush()

            config = _load_config(
                config_path=config_file.name,
                anki_config_loader=lambda _module_name: {"deck_name": "Anki"},
            )

        self.assertEqual(config["deck_name"], "Anki")

    def test_load_config_uses_local_json_without_anki_config(self):
        with tempfile.NamedTemporaryFile("w", encoding="utf-8") as config_file:
            json.dump({"deck_name": "Local"}, config_file)
            config_file.flush()

            config = _load_config(
                config_path=config_file.name,
                anki_config_loader=lambda _module_name: None,
            )

        self.assertEqual(config["deck_name"], "Local")

    def test_load_config_merges_nested_defaults(self):
        config = _load_config(
            config_path="/tmp/card_scheduler_missing_config.json",
            anki_config_loader=lambda _module_name: {
                "reading_to_kanji_cards": {
                    "max_grade": 6,
                },
            },
        )

        self.assertEqual(config["reading_to_kanji_cards"]["max_grade"], 6)
        self.assertEqual(
            config["reading_to_kanji_cards"]["note_type"],
            "CardScheduler Reading->Kanji",
        )

    def test_load_config_merges_sentence_scoring_defaults(self):
        config = _load_config(
            config_path="/tmp/card_scheduler_missing_config.json",
            anki_config_loader=lambda _module_name: {
                "sentence_scoring": {
                    "sentence_field": "Reading",
                },
            },
        )

        self.assertEqual(config["sentence_scoring"]["sentence_field"], "Reading")
        self.assertEqual(
            config["sentence_scoring"]["note_type"],
            "Japanese Sentence Card",
        )
        self.assertIn(
            "Japan::2. Sentences",
            config["sentence_scoring"]["deck_names"],
        )

    def test_legacy_automatic_config_gains_lifecycle_trigger_defaults(self):
        config = _load_config(
            config_path="/tmp/card_scheduler_missing_config.json",
            anki_config_loader=lambda _module_name: {
                "automatic_processing": {
                    "update_scores": False,
                },
            },
        )

        self.assertFalse(config["automatic_processing"]["update_scores"])
        self.assertTrue(config["automatic_processing"]["run_on_startup"])
        self.assertTrue(config["automatic_processing"]["run_on_new_day"])

    def test_default_config_includes_automatic_processing(self):
        config = get_default_config()

        self.assertTrue(config["automatic_processing"]["enabled"])
        self.assertTrue(config["automatic_processing"]["run_on_startup"])
        self.assertTrue(config["automatic_processing"]["run_on_new_day"])
        self.assertTrue(config["automatic_processing"]["update_scores"])
        self.assertTrue(config["automatic_processing"]["update_related_words"])
        self.assertTrue(config["automatic_processing"]["reposition_new_cards"])

    def test_validate_config_accepts_defaults(self):
        self.assertEqual(validate_config(get_default_config()), [])

    def test_validate_config_reports_invalid_user_values(self):
        config = get_default_config()
        config["deck_name"] = ""
        config["automatic_processing"]["delay_ms"] = 60001

        errors = validate_config(config)

        self.assertIn("Vocabulary deck cannot be empty.", errors)
        self.assertIn(
            "Automatic processing delay must be between 0 and 60000 ms.",
            errors,
        )


if __name__ == "__main__":
    unittest.main()
