import unittest
from unittest.mock import Mock, patch

from cardscheduler.automatic_processing import (
    NEW_DAY_TRIGGER,
    STARTUP_TRIGGER,
    AutomaticProcessingController,
    register_automatic_processing,
    run_configured_automatic_processing,
    should_run_automatic_processing,
)
from cardscheduler.config import get_default_config


class FakeSignal:
    def __init__(self):
        self.callback = None

    def connect(self, callback):
        self.callback = callback


class FakeTimer:
    def __init__(self):
        self.timeout = FakeSignal()
        self.single_shot = False
        self.started_with = []

    def setSingleShot(self, single_shot):
        self.single_shot = single_shot

    def start(self, delay_ms):
        self.started_with.append(delay_ms)


class ImmediateTaskManager:
    def run_on_main(self, callback):
        callback()


class FakeMainWindow:
    def __init__(self):
        self.taskman = ImmediateTaskManager()


class TestAutomaticProcessing(unittest.TestCase):
    def setUp(self):
        self.config = get_default_config()["automatic_processing"]
        self.collection = Mock(path="/profile/collection.anki2")

    def test_startup_and_new_day_triggers_are_enabled_by_default(self):
        self.assertTrue(
            should_run_automatic_processing(STARTUP_TRIGGER, self.config)
        )
        self.assertTrue(
            should_run_automatic_processing(NEW_DAY_TRIGGER, self.config)
        )

    def test_each_lifecycle_trigger_can_be_disabled_independently(self):
        self.config["run_on_startup"] = False

        self.assertFalse(
            should_run_automatic_processing(STARTUP_TRIGGER, self.config)
        )
        self.assertTrue(
            should_run_automatic_processing(NEW_DAY_TRIGGER, self.config)
        )

    def test_global_disable_prevents_all_automatic_processing(self):
        self.config["enabled"] = False

        self.assertFalse(
            should_run_automatic_processing(STARTUP_TRIGGER, self.config)
        )
        self.assertFalse(
            should_run_automatic_processing(NEW_DAY_TRIGGER, self.config)
        )

    def test_no_refresh_is_scheduled_when_all_actions_are_disabled(self):
        self.config["update_scores"] = False
        self.config["update_related_words"] = False
        self.config["reposition_new_cards"] = False

        self.assertFalse(
            should_run_automatic_processing(STARTUP_TRIGGER, self.config)
        )

    def test_unknown_trigger_does_not_schedule_processing(self):
        self.assertFalse(
            should_run_automatic_processing("unknown", self.config)
        )

    def _patch_refresh(self, stored_fingerprint, fingerprints):
        """Patch the collection-facing refresh helpers; returns the mocks."""
        mocks = {
            "load": patch(
                "cardscheduler.automatic_processing.load_vocabulary_refresh",
                return_value=Mock(),
            ),
            "compute": patch(
                "cardscheduler.automatic_processing.compute_vocabulary_refresh"
            ),
            "save": patch(
                "cardscheduler.automatic_processing.save_vocabulary_refresh"
            ),
            "fingerprint": patch(
                "cardscheduler.automatic_processing.refresh_fingerprint",
                side_effect=fingerprints,
            ),
            "stored": patch(
                "cardscheduler.automatic_processing.load_stored_fingerprint",
                return_value=stored_fingerprint,
            ),
            "store": patch(
                "cardscheduler.automatic_processing.store_fingerprint"
            ),
        }
        started = {name: patcher.start() for name, patcher in mocks.items()}
        for patcher in mocks.values():
            self.addCleanup(patcher.stop)
        return started

    def test_refresh_is_skipped_when_vocabulary_is_unchanged(self):
        mocks = self._patch_refresh("same", ["same"])

        ran = run_configured_automatic_processing(self.collection, self.config)

        self.assertFalse(ran)
        mocks["load"].assert_not_called()
        mocks["save"].assert_not_called()

    def test_refresh_updates_scores_and_related_words_in_one_pass(self):
        mocks = self._patch_refresh("old", ["before", "before", "after"])

        ran = run_configured_automatic_processing(self.collection, self.config)

        self.assertTrue(ran)
        mocks["load"].assert_called_once_with(
            self.collection,
            update_score_fields=True,
            include_related_words=True,
        )
        mocks["compute"].assert_called_once_with(mocks["load"].return_value)
        mocks["save"].assert_called_once_with(
            self.collection,
            mocks["load"].return_value,
            reposition=True,
            reload_notes=False,
        )
        mocks["store"].assert_called_once_with(self.collection.path, "after")

    def test_changes_while_computing_reload_notes_and_force_next_refresh(self):
        mocks = self._patch_refresh("old", ["before", "edited"])

        run_configured_automatic_processing(self.collection, self.config)

        self.assertTrue(mocks["save"].call_args.kwargs["reload_notes"])
        mocks["store"].assert_called_once_with(self.collection.path, None)

    def test_related_words_alone_skip_score_fields(self):
        self.config["update_scores"] = False
        self.config["reposition_new_cards"] = False
        mocks = self._patch_refresh("old", ["before", "before", "after"])

        run_configured_automatic_processing(self.collection, self.config)

        mocks["load"].assert_called_once_with(
            self.collection,
            update_score_fields=False,
            include_related_words=True,
        )

    def test_reposition_still_runs_score_pipeline_when_score_toggle_is_off(self):
        self.config["update_scores"] = False
        self.config["update_related_words"] = False
        mocks = self._patch_refresh("old", ["before", "before", "after"])

        run_configured_automatic_processing(self.collection, self.config)

        mocks["load"].assert_called_once_with(
            self.collection,
            update_score_fields=True,
            include_related_words=False,
        )
        self.assertTrue(mocks["save"].call_args.kwargs["reposition"])

    def test_controller_computes_off_the_collection_thread(self):
        collection = self.collection
        background_calls = []

        class RecordingTaskManager(ImmediateTaskManager):
            def run_in_background(self, task, on_done, uses_collection=True):
                background_calls.append(uses_collection)
                future = Mock()
                future.result.return_value = task()
                on_done(future)

        class ImmediateQueryOp:
            def __init__(self, parent, op, success):
                self._op = op
                self._success = success

            def failure(self, _callback):
                return self

            def run_in_background(self):
                self._success(self._op(collection))

        main_window = FakeMainWindow()
        main_window.taskman = RecordingTaskManager()
        main_window.col = collection
        controller = AutomaticProcessingController(
            main_window,
            config=self.config,
            query_op_factory=ImmediateQueryOp,
            timer=FakeTimer(),
        )
        mocks = self._patch_refresh("old", ["before", "before", "after"])

        with patch("aqt.utils.tooltip", create=True):
            controller._start_refresh()

        self.assertEqual(background_calls, [False])
        mocks["compute"].assert_called_once()
        mocks["save"].assert_called_once()
        self.assertFalse(controller._running)

    def test_controller_debounces_startup_and_new_day_triggers(self):
        timer = FakeTimer()
        controller = AutomaticProcessingController(
            FakeMainWindow(),
            config=self.config,
            query_op_factory=Mock(),
            timer=timer,
        )

        controller.on_profile_did_open()
        controller.on_day_did_change()

        self.assertTrue(timer.single_shot)
        self.assertEqual(timer.started_with, [1500, 1500])

    def test_controller_honors_individual_trigger_settings(self):
        self.config["run_on_startup"] = False
        timer = FakeTimer()
        controller = AutomaticProcessingController(
            FakeMainWindow(),
            config=self.config,
            query_op_factory=Mock(),
            timer=timer,
        )

        controller.on_profile_did_open()
        controller.on_day_did_change()

        self.assertEqual(timer.started_with, [1500])

    def test_registration_connects_both_lifecycle_hooks(self):
        profile_hook = []
        day_hook = []
        controller = Mock()
        with patch(
            "cardscheduler.automatic_processing.AutomaticProcessingController",
            return_value=controller,
        ):
            result = register_automatic_processing(
                FakeMainWindow(),
                profile_hook,
                day_hook,
            )

        self.assertIs(result, controller)
        self.assertEqual(profile_hook, [controller.on_profile_did_open])
        self.assertEqual(day_hook, [controller.on_day_did_change])


if __name__ == "__main__":
    unittest.main()
