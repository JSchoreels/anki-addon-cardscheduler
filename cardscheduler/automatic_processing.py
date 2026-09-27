"""Scheduled vocabulary refreshes for Anki startup and day rollover."""

import logging

from .anki_interface import (
    compute_vocabulary_refresh,
    load_vocabulary_refresh,
    save_vocabulary_refresh,
)
from .config import AUTOMATIC_PROCESSING_CONFIG
from .refresh_state import (
    load_stored_fingerprint,
    refresh_fingerprint,
    store_fingerprint,
)

logger = logging.getLogger(__name__)

STARTUP_TRIGGER = "startup"
NEW_DAY_TRIGGER = "new_day"


def should_run_automatic_processing(
    trigger,
    config=AUTOMATIC_PROCESSING_CONFIG,
):
    """Return whether the configured actions should run for a lifecycle trigger."""
    if not config["enabled"]:
        return False
    if not (
        config["update_scores"]
        or config["update_related_words"]
        or config["reposition_new_cards"]
    ):
        return False

    trigger_setting = {
        STARTUP_TRIGGER: "run_on_startup",
        NEW_DAY_TRIGGER: "run_on_new_day",
    }.get(trigger)
    return bool(trigger_setting and config[trigger_setting])


class PreparedRefresh:
    """A loaded refresh and the fingerprint of the collection it was loaded from."""

    def __init__(self, collection_path, fingerprint, refresh):
        self.collection_path = collection_path
        self.fingerprint = fingerprint
        self.refresh = refresh


def prepare_automatic_refresh(collection, config=AUTOMATIC_PROCESSING_CONFIG):
    """Load the refresh inputs, or return None when nothing changed since the last one.

    Needs the collection; keep it short so other collection operations can run.
    """
    fingerprint = refresh_fingerprint(collection)
    if fingerprint == load_stored_fingerprint(collection.path):
        logger.info("CardScheduler automatic refresh skipped: vocabulary unchanged")
        return None

    refresh = load_vocabulary_refresh(
        collection,
        update_score_fields=config["update_scores"] or config["reposition_new_cards"],
        include_related_words=config["update_related_words"],
    )
    return PreparedRefresh(collection.path, fingerprint, refresh)


def compute_automatic_refresh(prepared):
    """Compute the new field values. Does not use the collection."""
    compute_vocabulary_refresh(prepared.refresh)
    return prepared


def finish_automatic_refresh(collection, prepared, config=AUTOMATIC_PROCESSING_CONFIG):
    """Save the computed fields and remember the resulting collection state."""
    unchanged_since_load = refresh_fingerprint(collection) == prepared.fingerprint
    save_vocabulary_refresh(
        collection,
        prepared.refresh,
        reposition=config["reposition_new_cards"],
        # Notes edited while computing must keep their other fields.
        reload_notes=not unchanged_since_load,
    )
    # Reviews or edits made while computing are not reflected in the saved
    # values, so only skip the next refresh if there were none.
    store_fingerprint(
        collection.path,
        refresh_fingerprint(collection) if unchanged_since_load else None,
    )


def run_configured_automatic_processing(
    collection,
    config=AUTOMATIC_PROCESSING_CONFIG,
):
    """Run all refresh phases synchronously. Returns False if it was skipped."""
    prepared = prepare_automatic_refresh(collection, config)
    if prepared is None:
        return False
    compute_automatic_refresh(prepared)
    finish_automatic_refresh(collection, prepared, config)
    return True


class AutomaticProcessingController:
    """Run configured processing after selected Anki lifecycle events."""

    def __init__(
        self,
        mw_instance,
        config=AUTOMATIC_PROCESSING_CONFIG,
        query_op_factory=None,
        timer=None,
    ):
        from aqt.operations import QueryOp
        from aqt.qt import QTimer, qconnect

        self._mw = mw_instance
        self._config = config
        self._query_op_factory = query_op_factory or QueryOp
        self._timer = timer or QTimer(mw_instance)
        self._timer.setSingleShot(True)
        qconnect(self._timer.timeout, self._start_refresh)
        self._running = False
        self._rerun_requested = False

    def on_profile_did_open(self):
        """Schedule one refresh after an Anki profile opens."""
        self._handle_trigger(STARTUP_TRIGGER)

    def on_day_did_change(self):
        """Schedule one refresh when Anki advances to a new scheduler day."""
        self._handle_trigger(NEW_DAY_TRIGGER)

    def _handle_trigger(self, trigger):
        try:
            if not should_run_automatic_processing(trigger, self._config):
                return
            self._mw.taskman.run_on_main(self._schedule_refresh)
        except Exception:
            logger.exception("Could not schedule CardScheduler automatic processing")

    def _schedule_refresh(self):
        if self._running:
            self._rerun_requested = True
            return
        self._timer.start(max(0, int(self._config["delay_ms"])))

    def _start_refresh(self):
        if self._running:
            self._rerun_requested = True
            return

        # Anki runs collection operations one at a time, so only loading and
        # saving use the collection; computing runs on a separate thread and
        # does not hold up other add-ons or Anki's own startup work.
        self._running = True
        operation = self._query_op_factory(
            parent=self._mw,
            op=lambda collection: prepare_automatic_refresh(collection, self._config),
            success=self._on_prepared,
        )
        operation.failure(self._refresh_failed)
        operation.run_in_background()

    def _on_prepared(self, prepared):
        if prepared is None:
            self._running = False
            self._schedule_requested_rerun()
            return

        self._mw.taskman.run_in_background(
            lambda: compute_automatic_refresh(prepared),
            self._on_computed,
            uses_collection=False,
        )

    def _on_computed(self, future):
        try:
            prepared = future.result()
        except Exception as exception:
            self._refresh_failed(exception)
            return

        collection = self._mw.col
        if collection is None or collection.path != prepared.collection_path:
            # The profile was closed or switched while computing.
            self._running = False
            self._schedule_requested_rerun()
            return

        operation = self._query_op_factory(
            parent=self._mw,
            op=lambda collection: finish_automatic_refresh(
                collection,
                prepared,
                self._config,
            ),
            success=self._refresh_succeeded,
        )
        operation.failure(self._refresh_failed)
        operation.run_in_background()

    def _refresh_succeeded(self, _result):
        from aqt.utils import tooltip

        self._running = False
        tooltip("CardScheduler automatic refresh complete.", parent=self._mw)
        self._schedule_requested_rerun()

    def _refresh_failed(self, exception):
        from aqt.utils import tooltip

        self._running = False
        logger.exception(
            "CardScheduler automatic refresh failed",
            exc_info=(type(exception), exception, exception.__traceback__),
        )
        tooltip(
            "CardScheduler automatic refresh failed; see the console for details.",
            parent=self._mw,
        )
        self._schedule_requested_rerun()

    def _schedule_requested_rerun(self):
        if self._rerun_requested:
            self._rerun_requested = False
            self._schedule_refresh()


def register_automatic_processing(
    mw_instance,
    profile_did_open_hook,
    day_did_change_hook,
):
    """Register and retain the automatic processing controller for this session."""
    controller = AutomaticProcessingController(mw_instance)
    profile_did_open_hook.append(controller.on_profile_did_open)
    day_did_change_hook.append(controller.on_day_did_change)
    return controller
