from aqt import mw
from aqt.qt import QAction
from anki.notes import Note
from anki.cards import Card

from .cardscheduler import process_collection

# Create a new menu item in the Tools menu
action = QAction("Compute Card Order", mw)
# Set it to call compute_order when clicked
action.triggered.connect(process_collection)
# Add the menu item
mw.form.menuTools.addAction(action)