import unittest

from cardscheduler.anki_interface import load_cards
from cardscheduler.config import INPUT_MODE_SINGLE_FIELD


class FakeNote:
    def __init__(self, field_names, values_by_name):
        self._note_type = {"flds": [{"name": name} for name in field_names]}
        self.fields = [values_by_name.get(name, "") for name in field_names]

    def note_type(self):
        return self._note_type


class FakeCard:
    def __init__(self, card_id, note):
        self.id = card_id
        self._note = note
        self.memory_state = None
        self.ivl = 0

    def note(self):
        return self._note


class FakeCollection:
    def __init__(self, cards):
        self._cards = {card.id: card for card in cards}

    def find_cards(self, _query):
        return list(self._cards.keys())

    def get_card(self, card_id):
        return self._cards[card_id]


class TestFrequencyFieldLoading(unittest.TestCase):
    def test_raises_if_frequency_field_missing(self):
        note = FakeNote(["ID"], {"ID": "ありがとう"})
        collection = FakeCollection([FakeCard(1, note)])

        with self.assertRaises(ValueError):
            load_cards(
                collection,
                input_mode=INPUT_MODE_SINGLE_FIELD,
                single_field_name="ID",
                frequency_field_name="Frequency",
            )

    def test_supports_custom_frequency_field_and_parses_value(self):
        note = FakeNote(["ID", "FreqRank"], {"ID": "ありがとう", "FreqRank": "1,234"})
        collection = FakeCollection([FakeCard(1, note)])

        cards = load_cards(
            collection,
            input_mode=INPUT_MODE_SINGLE_FIELD,
            single_field_name="ID",
            frequency_field_name="FreqRank",
        )

        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].frequency, 1234.0)


if __name__ == "__main__":
    unittest.main()
