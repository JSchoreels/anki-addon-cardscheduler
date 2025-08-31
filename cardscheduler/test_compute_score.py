import unittest
from anki.collection import Collection

from cardscheduler import load_cards, compute_scores, process_collection


class TestComputeScore(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.collection = Collection("/Users/jschoreels/Library/Application Support/Anki2/Main Profile/collection.anki2")

    def test_compute_score(self):
        process_collection(self.collection, dry_run=True)

