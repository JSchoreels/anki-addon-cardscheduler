import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from unittest.mock import patch

from cardscheduler.reading_kanji_map import (
    build_reading_to_kanji_map,
    load_kanji_frequencies,
    load_kanji_grades,
    load_onyomi_readings,
    main,
    write_reading_to_kanji_map,
)


class TestReadingKanjiMap(unittest.TestCase):
    def test_loads_grade_metadata_from_light_kanjidic(self):
        kanji_grades = load_kanji_grades()

        self.assertEqual(kanji_grades["亜"], 8)

    def test_loads_frequency_metadata_from_light_kanjidic(self):
        kanji_frequencies = load_kanji_frequencies()

        self.assertEqual(kanji_frequencies["亜"], 1509)

    @patch("cardscheduler.reading_kanji_map._load_kanjidic_xml", return_value=None)
    def test_metadata_loader_handles_missing_xml(self, _load_xml_mock):
        self.assertEqual(load_kanji_grades(), {})

    @patch("cardscheduler.reading_kanji_map._load_kanjidic_xml", return_value=None)
    def test_load_onyomi_readings_handles_missing_xml(self, _load_xml_mock):
        self.assertEqual(load_onyomi_readings(), {})

    @patch("cardscheduler.reading_kanji_map._load_kanjidic_xml")
    def test_load_onyomi_readings_includes_processed_variations(self, load_xml_mock):
        load_xml_mock.return_value = ET.fromstring(
            """
            <kanjidic2>
              <character>
                <literal>学</literal>
                <ja_on>かく</ja_on>
              </character>
              <character>
                <literal>人</literal>
              </character>
            </kanjidic2>
            """
        )

        readings = load_onyomi_readings()

        self.assertEqual(readings["学"]["かく"], ["かく", "がく", "かっ", "がっ"])
        self.assertNotIn("人", readings)

    def test_orders_readings_by_number_of_kanji(self):
        kanji_readings = {
            "日": {
                "にち": ["にち"],
                "ひ": ["ひ", "び"],
            },
            "人": {
                "にん": ["にん"],
                "ひと": ["ひと", "びと"],
            },
            "任": {
                "にん": ["にん"],
            },
        }

        reading_to_kanji = build_reading_to_kanji_map(kanji_readings)
        readings = list(reading_to_kanji.keys())

        self.assertEqual(reading_to_kanji["にん"], ["人", "任"])
        self.assertLess(readings.index("ひ"), readings.index("にん"))
        self.assertLess(readings.index("ひと"), readings.index("にん"))

    def test_filters_by_max_grade(self):
        kanji_readings = {
            "校": {
                "こう": ["こう"],
            },
            "巧": {
                "こう": ["こう"],
            },
        }
        kanji_grades = {
            "校": 1,
            "巧": 9,
        }

        reading_to_kanji = build_reading_to_kanji_map(
            kanji_readings,
            kanji_grades=kanji_grades,
            max_grade=8,
        )

        self.assertEqual(reading_to_kanji["こう"], ["校"])

    def test_sorts_kanji_array_by_grade(self):
        kanji_readings = {
            "巧": {
                "こう": ["こう"],
            },
            "校": {
                "こう": ["こう"],
            },
        }
        kanji_grades = {
            "巧": 8,
            "校": 1,
        }

        reading_to_kanji = build_reading_to_kanji_map(
            kanji_readings,
            kanji_grades=kanji_grades,
            max_grade=8,
        )

        self.assertEqual(reading_to_kanji["こう"], ["校", "巧"])

    def test_deduplicates_base_reading_and_variations_for_same_kanji(self):
        kanji_readings = {
            "一": {
                "いち": ["いち", "いっ", "いち"],
            },
        }

        reading_to_kanji = build_reading_to_kanji_map(kanji_readings)

        self.assertEqual(reading_to_kanji["いち"], ["一"])
        self.assertEqual(reading_to_kanji["いっ"], ["一"])

    @patch("cardscheduler.reading_kanji_map.load_kanji_grades")
    @patch("cardscheduler.reading_kanji_map.load_kanji_dictionnary_readings")
    @patch("cardscheduler.reading_kanji_map.load_onyomi_readings")
    @patch("builtins.print")
    def test_write_uses_onyomi_only_by_default(
        self,
        print_mock,
        load_onyomi_readings_mock,
        load_kanji_dictionnary_readings_mock,
        load_kanji_grades_mock,
    ):
        load_onyomi_readings_mock.return_value = {
            "学": {
                "がく": ["がく"],
            },
        }
        load_kanji_grades_mock.return_value = {
            "学": 1,
        }

        reading_to_kanji = write_reading_to_kanji_map()

        self.assertEqual(reading_to_kanji, {"がく": ["学"]})
        print_mock.assert_called_once()
        load_onyomi_readings_mock.assert_called_once_with()
        load_kanji_dictionnary_readings_mock.assert_not_called()
        load_kanji_grades_mock.assert_called_once_with()

    @patch("cardscheduler.reading_kanji_map.load_kanji_grades")
    @patch("cardscheduler.reading_kanji_map.load_kanji_dictionnary_readings")
    @patch("cardscheduler.reading_kanji_map.load_onyomi_readings")
    @patch("builtins.print")
    def test_write_can_include_kunyomi(
        self,
        print_mock,
        load_onyomi_readings_mock,
        load_kanji_dictionnary_readings_mock,
        load_kanji_grades_mock,
    ):
        load_kanji_dictionnary_readings_mock.return_value = {
            "学": {
                "がく": ["がく"],
                "まな.ぶ": ["まなぶ"],
            },
        }
        load_kanji_grades_mock.return_value = {
            "学": 1,
        }

        reading_to_kanji = write_reading_to_kanji_map(onyomi_only=False)

        self.assertEqual(reading_to_kanji["がく"], ["学"])
        self.assertEqual(reading_to_kanji["まなぶ"], ["学"])
        print_mock.assert_called_once()
        load_onyomi_readings_mock.assert_not_called()
        load_kanji_dictionnary_readings_mock.assert_called_once_with()
        load_kanji_grades_mock.assert_called_once_with()

    @patch("cardscheduler.reading_kanji_map.load_kanji_grades")
    @patch("cardscheduler.reading_kanji_map.load_onyomi_readings")
    @patch("builtins.print")
    def test_write_uses_max_grade_8_by_default(
        self,
        print_mock,
        load_onyomi_readings_mock,
        load_kanji_grades_mock,
    ):
        load_onyomi_readings_mock.return_value = {
            "校": {
                "こう": ["こう"],
            },
            "巧": {
                "こう": ["こう"],
            },
        }
        load_kanji_grades_mock.return_value = {
            "校": 1,
            "巧": 9,
        }

        reading_to_kanji = write_reading_to_kanji_map()

        self.assertEqual(reading_to_kanji["こう"], ["校"])
        print_mock.assert_called_once()

    @patch("cardscheduler.reading_kanji_map.load_kanji_grades")
    @patch("cardscheduler.reading_kanji_map.load_onyomi_readings")
    def test_write_can_write_json_to_file(
        self,
        load_onyomi_readings_mock,
        load_kanji_grades_mock,
    ):
        load_onyomi_readings_mock.return_value = {
            "学": {
                "がく": ["がく"],
            },
        }
        load_kanji_grades_mock.return_value = {
            "学": 1,
        }

        with tempfile.NamedTemporaryFile() as output_file:
            result = write_reading_to_kanji_map(output_file.name)
            output_file.seek(0)
            written = json.loads(output_file.read().decode("utf-8"))

        self.assertIsNone(result)
        self.assertEqual(written, {"がく": ["学"]})

    @patch("cardscheduler.reading_kanji_map.write_reading_to_kanji_map")
    def test_main_passes_cli_options_to_writer(self, write_mock):
        with patch(
            "sys.argv",
            [
                "reading_kanji_map",
                "--include-kunyomi",
                "--max-grade",
                "6",
                "--output",
                "reading.json",
            ],
        ):
            main()

        write_mock.assert_called_once_with(
            "reading.json",
            onyomi_only=False,
            max_grade=6,
        )


if __name__ == "__main__":
    unittest.main()
