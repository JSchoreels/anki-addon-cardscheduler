"""Fingerprint of the automatic refresh inputs.

A refresh only depends on the vocabulary deck's cards and notes, the note
types, the add-on configuration and the add-on code. When none of these
changed since the last completed refresh, running it again would write
exactly the same field values, so it can be skipped.
"""

import hashlib
import json
import os

from .config import DECK_NAME, _config

PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
# user_files is preserved by Anki on add-on updates and by copy_to_anki.sh.
STATE_PATH = os.path.join(
    os.path.dirname(PACKAGE_DIR), "user_files", "refresh_state.json"
)
_CODE_EXTENSIONS = (".py", ".xml", ".txt", ".json")


def refresh_fingerprint(collection, deck_name=DECK_NAME, config=_config):
    """Return a digest that changes whenever a refresh could produce new values."""
    deck_ids = _deck_and_child_ids(collection, deck_name)
    ids = "(" + ",".join(str(deck_id) for deck_id in deck_ids) + ")" if deck_ids else "(0)"
    # Card mtimes change with reviews, rescheduling, deck moves and FSRS
    # memory-state updates; note mtimes with field edits (including ours).
    # The data length also catches memory states filled in without an mtime bump.
    card_state = collection.db.first(
        "select count(), coalesce(sum(c.id), 0), coalesce(sum(c.mod), 0), "
        "coalesce(sum(n.mod), 0), coalesce(sum(length(c.data)), 0) "
        "from cards c join notes n on n.id = c.nid "
        f"where c.did in {ids} or c.odid in {ids}"
    )
    notetype_state = collection.db.scalar(
        "select coalesce(sum(mtime_secs), 0) from notetypes"
    )
    payload = {
        "cards": list(card_state or ()),
        "notetypes": notetype_state,
        "config": config,
        "code": _code_signature(),
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def load_stored_fingerprint(collection_path, state_path=None):
    return _read_state(state_path or STATE_PATH).get(collection_path)


def store_fingerprint(collection_path, fingerprint, state_path=None):
    state_path = state_path or STATE_PATH
    state = _read_state(state_path)
    if fingerprint is None:
        state.pop(collection_path, None)
    else:
        state[collection_path] = fingerprint
    os.makedirs(os.path.dirname(state_path), exist_ok=True)
    temp_path = f"{state_path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, sort_keys=True)
    os.replace(temp_path, state_path)


def _read_state(state_path):
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            state = json.load(f)
    except (OSError, ValueError):
        return {}
    return state if isinstance(state, dict) else {}


def _deck_and_child_ids(collection, deck_name):
    deck_id = collection.decks.id_for_name(deck_name)
    if not deck_id:
        return []
    return list(collection.decks.deck_and_child_ids(deck_id))


def _code_signature():
    signature = []
    for root, dirs, files in os.walk(PACKAGE_DIR):
        dirs[:] = sorted(d for d in dirs if d not in {"tests", "__pycache__"})
        for name in sorted(files):
            if not name.endswith(_CODE_EXTENSIONS):
                continue
            path = os.path.join(root, name)
            stat = os.stat(path)
            signature.append(
                (os.path.relpath(path, PACKAGE_DIR), stat.st_size, stat.st_mtime_ns)
            )
    return signature
