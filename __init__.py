from aqt import mw
from aqt.qt import QAction
from anki.notes import Note
from anki.cards import Card

from .cardscheduler import process_collection

# Create menu items in the Tools menu

# Action 1: Compute only (update fields but don't reposition)
action_compute = QAction("CardScheduler: Compute Scores", mw)
action_compute.triggered.connect(lambda: process_collection(reposition=False))
mw.form.menuTools.addAction(action_compute)

# Action 2: Compute and reposition new cards
action_reposition = QAction("CardScheduler: Compute and Reposition Cards", mw)
action_reposition.triggered.connect(lambda: process_collection(reposition=True))
mw.form.menuTools.addAction(action_reposition)