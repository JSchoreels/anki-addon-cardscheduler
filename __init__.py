from aqt import gui_hooks, mw
from aqt.qt import QAction
from anki.notes import Note
from anki.cards import Card
import sys

from .cardscheduler import (
    process_all_features,
    process_collection,
    process_reading_to_kanji_cards,
    process_related_words,
    process_sentence_scores,
)
from .cardscheduler.automatic_processing import register_automatic_processing
from .cardscheduler.settings_dialog import open_settings_dialog


_automatic_processing_controller = None

if 'pytest' not in sys.modules:
    # Create menu items in the Tools menu
    # Only run when loaded by Anki (mw is not None)
    if mw is not None:
        action_settings = QAction("CardScheduler: Settings", mw)
        action_settings.triggered.connect(lambda: open_settings_dialog(__name__))
        mw.form.menuTools.addAction(action_settings)
        mw.addonManager.setConfigAction(
            __name__,
            lambda: open_settings_dialog(__name__),
        )

        # Action 1: Compute only (update fields but don't reposition)
        action_compute = QAction("CardScheduler: Compute Scores", mw)
        action_compute.triggered.connect(lambda: process_collection(reposition=False))
        mw.form.menuTools.addAction(action_compute)

        # Action 2: Compute and reposition new cards
        action_reposition = QAction("CardScheduler: Compute and Reposition Cards", mw)
        action_reposition.triggered.connect(lambda: process_collection(reposition=True))
        mw.form.menuTools.addAction(action_reposition)

        # Action 3: Compute related-word display fields
        action_related = QAction("CardScheduler: Compute Related Words", mw)
        action_related.triggered.connect(lambda: process_related_words())
        mw.form.menuTools.addAction(action_related)

        # Action 4: Generate/update Reading -> Kanji cards from known vocabulary
        action_reading_to_kanji = QAction(
            "CardScheduler: Update Reading->Kanji Cards",
            mw,
        )
        action_reading_to_kanji.triggered.connect(
            lambda: process_reading_to_kanji_cards()
        )
        mw.form.menuTools.addAction(action_reading_to_kanji)

        # Action 5: Compute sentence scores
        action_sentence_scores = QAction(
            "CardScheduler: Compute Sentence Scores",
            mw,
        )
        action_sentence_scores.triggered.connect(
            lambda: process_sentence_scores(reposition=False)
        )
        mw.form.menuTools.addAction(action_sentence_scores)

        # Action 6: Compute sentence scores and reposition new sentence cards
        action_sentence_reposition = QAction(
            "CardScheduler: Compute and Reposition Sentence Cards",
            mw,
        )
        action_sentence_reposition.triggered.connect(
            lambda: process_sentence_scores(reposition=True)
        )
        mw.form.menuTools.addAction(action_sentence_reposition)

        # Action 7: Run the complete workflow
        action_all = QAction(
            "CardScheduler: Compute Scores, Related Words, Reposition Cards, "
            "Generate Reading Cards, Sentence Scores",
            mw,
        )
        action_all.triggered.connect(lambda: process_all_features())
        mw.form.menuTools.addAction(action_all)

        _automatic_processing_controller = register_automatic_processing(
            mw,
            gui_hooks.profile_did_open,
            gui_hooks.day_did_change,
        )
