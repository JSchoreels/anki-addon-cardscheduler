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
        self.collection = object()

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

    def test_runs_enabled_score_related_and_reposition_actions(self):
        process_scores = Mock()
        process_related = Mock()

        run_configured_automatic_processing(
            collection=self.collection,
            config=self.config,
            process_collection_fn=process_scores,
            process_related_words_fn=process_related,
        )

        process_scores.assert_called_once_with(
            collection=self.collection,
            reposition=True,
            show_summary=False,
        )
        process_related.assert_called_once_with(
            collection=self.collection,
            show_summary=False,
        )

    def test_reposition_still_runs_score_pipeline_when_score_toggle_is_off(self):
        self.config["update_scores"] = False
        process_scores = Mock()

        run_configured_automatic_processing(
            collection=self.collection,
            config=self.config,
            process_collection_fn=process_scores,
            process_related_words_fn=Mock(),
        )

        process_scores.assert_called_once_with(
            collection=self.collection,
            reposition=True,
            show_summary=False,
        )

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
