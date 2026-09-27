"""Scheduled vocabulary refreshes for Anki startup and day rollover."""

import logging

from .anki_interface import process_collection, process_related_words
from .config import AUTOMATIC_PROCESSING_CONFIG

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


def run_configured_automatic_processing(
    collection,
    config=AUTOMATIC_PROCESSING_CONFIG,
    process_collection_fn=process_collection,
    process_related_words_fn=process_related_words,
):
    """Run the enabled exact refresh actions without modal summary dialogs."""
    if config["update_scores"] or config["reposition_new_cards"]:
        process_collection_fn(
            collection=collection,
            reposition=config["reposition_new_cards"],
            show_summary=False,
        )

    if config["update_related_words"]:
        process_related_words_fn(
            collection=collection,
            show_summary=False,
        )


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

        self._running = True
        operation = self._query_op_factory(
            parent=self._mw,
            op=lambda collection: run_configured_automatic_processing(
                collection,
                self._config,
            ),
            success=self._refresh_succeeded,
        )
        operation.failure(self._refresh_failed)
        operation.with_progress("CardScheduler: refreshing vocabulary cards…")
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
