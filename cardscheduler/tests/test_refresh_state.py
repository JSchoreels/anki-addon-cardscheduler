import os
import tempfile
import unittest
from unittest.mock import Mock

from cardscheduler.refresh_state import (
    load_stored_fingerprint,
    refresh_fingerprint,
    store_fingerprint,
)


def fake_collection(card_state, notetype_state=100):
    collection = Mock()
    collection.decks.id_for_name.return_value = 1
    collection.decks.deck_and_child_ids.return_value = [1, 2]
    collection.db.first.return_value = card_state
    collection.db.scalar.return_value = notetype_state
    return collection


class TestRefreshState(unittest.TestCase):
    def test_fingerprint_changes_with_card_state_and_config(self):
        base = refresh_fingerprint(fake_collection([10, 5, 7, 9, 3]), config={"a": 1})

        self.assertEqual(
            base,
            refresh_fingerprint(fake_collection([10, 5, 7, 9, 3]), config={"a": 1}),
        )
        self.assertNotEqual(
            base,
            refresh_fingerprint(fake_collection([10, 5, 8, 9, 3]), config={"a": 1}),
        )
        self.assertNotEqual(
            base,
            refresh_fingerprint(fake_collection([10, 5, 7, 9, 3], 101), config={"a": 1}),
        )
        self.assertNotEqual(
            base,
            refresh_fingerprint(fake_collection([10, 5, 7, 9, 3]), config={"a": 2}),
        )

    def test_fingerprint_queries_deck_and_child_decks(self):
        collection = fake_collection([0, 0, 0, 0, 0])

        refresh_fingerprint(collection, deck_name="Japan::Vocab")

        collection.decks.id_for_name.assert_called_once_with("Japan::Vocab")
        query = collection.db.first.call_args.args[0]
        self.assertIn("c.did in (1,2) or c.odid in (1,2)", query)

    def test_store_and_load_are_per_collection(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = os.path.join(directory, "user_files", "state.json")

            store_fingerprint("/a", "one", state_path=state_path)
            store_fingerprint("/b", "two", state_path=state_path)
            store_fingerprint("/a", None, state_path=state_path)

            self.assertIsNone(load_stored_fingerprint("/a", state_path=state_path))
            self.assertEqual(load_stored_fingerprint("/b", state_path=state_path), "two")

    def test_missing_or_corrupt_state_reads_as_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            state_path = os.path.join(directory, "state.json")
            self.assertIsNone(load_stored_fingerprint("/a", state_path=state_path))

            with open(state_path, "w", encoding="utf-8") as f:
                f.write("not json")
            self.assertIsNone(load_stored_fingerprint("/a", state_path=state_path))


if __name__ == "__main__":
    unittest.main()
