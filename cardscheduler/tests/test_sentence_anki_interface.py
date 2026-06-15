import unittest

from cardscheduler.anki_interface import (
    ensure_note_type_fields,
    load_sentence_cards,
    update_sentence_note_fields,
)
from cardscheduler.sentence_scheduler import SentenceCardInfo


class FakeModels:
    def __init__(self, notetype):
        self.notetype = notetype
        self.updated = False

    def by_name(self, name):
        if self.notetype["name"] == name:
            return self.notetype
        return None

    def new_field(self, name):
        return {"name": name, "ord": None}

    def add_field(self, notetype, field):
        field["ord"] = len(notetype["flds"])
        notetype["flds"].append(field)

    def update_dict(self, notetype):
        self.notetype = notetype
        self.updated = True


class FakeNote:
    def __init__(self, notetype):
        self.id = 10
        self._notetype = notetype
        self.fields = [""] * len(notetype["flds"])

    def note_type(self):
        return self._notetype


class FakeCard:
    def __init__(self, note):
        self._note = note

    def note(self):
        return self._note


class FakeCollection:
    def __init__(self, note):
        self.models = FakeModels(note.note_type())
        self.note = note
        self.updated_notes = []

    def get_card(self, _card_id):
        return FakeCard(self.note)

    def update_note(self, note):
        self.updated_notes.append(note)


class FakeMappedCollection:
    def __init__(self, cards_by_id):
        self.cards_by_id = cards_by_id

    def find_cards(self, _query):
        return list(self.cards_by_id.keys())

    def get_card(self, card_id):
        return self.cards_by_id[card_id]


class FakeMappedCard:
    def __init__(self, note):
        self._note = note

    def note(self):
        return self._note


class FakeMappedNote:
    def __init__(self, note_id, sentence):
        self.id = note_id
        self.fields = [sentence]
        self._notetype = {
            "name": "Japanese Sentence Card",
            "flds": [{"name": "Sentence"}],
        }

    def note_type(self):
        return self._notetype


class FakeAnalyzer:
    def __init__(self):
        self.texts = []

    def extract_tokens(self, text):
        self.texts.append(text)
        return []

    def extract_tokens_many(self, texts):
        self.texts.extend(texts)
        return {
            text: []
            for text in texts
        }


class TestSentenceAnkiInterface(unittest.TestCase):
    def test_ensure_note_type_fields_adds_missing_fields(self):
        notetype = {
            "name": "Japanese Sentence Card",
            "flds": [{"name": "Sentence"}],
        }
        note = FakeNote(notetype)
        collection = FakeCollection(note)

        fields = ensure_note_type_fields(
            collection,
            "Japanese Sentence Card",
            ["Sentence", "CardScheduler.SentenceStrictScore"],
        )

        self.assertIn("CardScheduler.SentenceStrictScore", fields)
        self.assertTrue(collection.models.updated)
        self.assertEqual(
            [field["name"] for field in collection.models.notetype["flds"]],
            ["Sentence", "CardScheduler.SentenceStrictScore"],
        )

    def test_update_sentence_note_fields_writes_scores_and_counts(self):
        field_names = [
            "CardScheduler.Position",
            "CardScheduler.SentenceStrictScore",
            "CardScheduler.SentencePredictedScore",
            "CardScheduler.SentenceMissingWords",
            "CardScheduler.SentenceInferredWords",
            "CardScheduler.SentenceKanjiWordCount",
            "CardScheduler.SentencePriorityScore",
        ]
        notetype = {
            "name": "Japanese Sentence Card",
            "flds": [{"name": name} for name in field_names],
        }
        note = FakeNote(notetype)
        collection = FakeCollection(note)
        sentence = SentenceCardInfo(note_id=10, card_ids=[1], sentence_text="")
        sentence.position = 3
        sentence.strict_score = 0
        sentence.predicted_score = 20.125
        sentence.missing_words = 2
        sentence.inferred_words = 1
        sentence.kanji_word_count = 5
        sentence.priority_score = 66.6661

        updated = update_sentence_note_fields(
            sentence,
            collection,
            available_fields=set(field_names),
        )

        self.assertTrue(updated)
        self.assertEqual(note.fields[0], "3")
        self.assertEqual(note.fields[1], "0.000")
        self.assertEqual(note.fields[2], "20.125")
        self.assertEqual(note.fields[3], "2")
        self.assertEqual(note.fields[4], "1")
        self.assertEqual(note.fields[5], "5")
        self.assertEqual(note.fields[6], "66.667")
        self.assertEqual(collection.updated_notes, [note])

    def test_load_sentence_cards_can_limit_unique_notes(self):
        note_a = FakeMappedNote(10, "昨日学校に行きました。")
        note_b = FakeMappedNote(20, "本を読みます。")
        note_c = FakeMappedNote(30, "映画を見ます。")
        collection = FakeMappedCollection(
            {
                1: FakeMappedCard(note_a),
                2: FakeMappedCard(note_b),
                3: FakeMappedCard(note_c),
                4: FakeMappedCard(note_a),
            }
        )
        analyzer = FakeAnalyzer()

        sentence_cards = load_sentence_cards(
            collection,
            sentence_deck_names=["Japan::2. Sentences"],
            analyzer=analyzer,
            sentence_limit=2,
        )

        self.assertEqual([card.note_id for card in sentence_cards], [10, 20])
        self.assertEqual(sentence_cards[0].card_ids, [1, 4])
        self.assertEqual(analyzer.texts, ["昨日学校に行きました。", "本を読みます。"])


if __name__ == "__main__":
    unittest.main()
