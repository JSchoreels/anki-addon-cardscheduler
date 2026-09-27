"""Native Anki configuration dialog for CardScheduler."""

from aqt.qt import QDialog

from .anki_config_adapter import load_anki_addon_config, write_anki_addon_config
from .config import get_default_config, normalize_config, validate_config


VOCABULARY_FIELD_LABELS = {
    "position": "Position",
    "score": "Score",
    "unlock_potential": "Unlock potential",
    "unlock_median_score_increase": "Unlock median score increase",
    "score_without_missing": "Score without missing kanji",
    "missing_kanji_count": "Missing kanji count",
    "related_known": "Related known words",
    "related_unknown": "Related unknown words",
    "kanji_meanings": "Kanji meanings",
    "cards_with_kanji": "Cards sharing kanji",
    "cards_with_kanji_known": "Known cards sharing kanji",
    "cards_with_kanji_unknown": "Unknown cards sharing kanji",
}

READING_TO_KANJI_FIELD_LABELS = {
    "reading": "Reading",
    "kanji_meaning": "Kanji meaning",
    "matching_kanji_count": "Matching kanji count",
    "grade": "Grade",
    "frequency": "Frequency",
    "known_words": "Known words",
}

SENTENCE_FIELD_LABELS = {
    "strict_score": "Strict score",
    "predicted_score": "Predicted score",
    "missing_words": "Missing words",
    "inferred_words": "Inferred words",
    "kanji_word_count": "Kanji word count",
    "priority_score": "Priority score",
}


def _set_nested(config, path, value):
    target = config
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value


def _sorted_unique_names(names):
    return sorted(
        {
            name.strip()
            for name in names
            if isinstance(name, str) and name.strip()
        },
        key=str.casefold,
    )


def available_deck_names(collection):
    """Return sorted normal deck names exposed by the Anki collection."""
    if collection is None:
        return []
    return _sorted_unique_names(
        entry.name
        for entry in collection.decks.all_names_and_ids(
            include_filtered=False,
        )
    )


def available_field_names(collection):
    """Return sorted field names exposed by all Anki note types."""
    if collection is None:
        return []
    return _sorted_unique_names(
        field.get("name", "")
        for note_type in collection.models.all()
        if note_type
        for field in note_type.get("flds", [])
    )


class CardSchedulerSettingsDialog(QDialog):
    """Tabbed editor for the complete CardScheduler configuration."""

    def __init__(
        self,
        config,
        *,
        deck_names=(),
        field_names=(),
        parent=None,
    ):
        super().__init__(parent)
        self._initial_config = normalize_config(config)
        self._deck_names = _sorted_unique_names(deck_names)
        self._field_names = _sorted_unique_names(field_names)
        self._line_edits = {}
        self._combos = {}
        self._editable_combos = {}
        self._checks = {}
        self._spins = {}
        self._plain_text_edits = {}
        self._result_config = None

        self.setWindowTitle("CardScheduler Settings")
        self.setMinimumSize(760, 640)
        self._build_ui()

    def _build_ui(self):
        from aqt.qt import (
            QDialogButtonBox,
            QLabel,
            QTabWidget,
            QVBoxLayout,
            qconnect,
        )

        layout = QVBoxLayout(self)
        description = QLabel(
            "Configure CardScheduler without editing JSON. Changes take effect "
            "after restarting Anki."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        tabs = QTabWidget()
        tabs.addTab(self._build_general_tab(), "General")
        tabs.addTab(self._build_automation_tab(), "Automation")
        tabs.addTab(self._build_vocabulary_fields_tab(), "Vocabulary fields")
        tabs.addTab(self._build_reading_to_kanji_tab(), "Reading → Kanji")
        tabs.addTab(self._build_sentence_tab(), "Sentences")
        layout.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        qconnect(buttons.accepted, self.accept)
        qconnect(buttons.rejected, self.reject)
        layout.addWidget(buttons)

    def _new_form_tab(self):
        from aqt.qt import QFormLayout, QScrollArea, QVBoxLayout, QWidget

        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        form = QFormLayout(content)
        form.setFieldGrowthPolicy(
            QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow
        )
        scroll.setWidget(content)
        tab_layout.addWidget(scroll)
        return tab, form

    def _add_line_edit(self, form, label, path, value, placeholder=None):
        from aqt.qt import QLineEdit

        widget = QLineEdit()
        widget.setText("" if value is None else str(value))
        if placeholder:
            widget.setPlaceholderText(placeholder)
        form.addRow(label, widget)
        self._line_edits[path] = widget
        return widget

    def _add_combo(self, form, label, path, choices, value):
        from aqt.qt import QComboBox

        widget = QComboBox()
        for display, data in choices:
            widget.addItem(display, data)
        index = widget.findData(value)
        widget.setCurrentIndex(index if index >= 0 else 0)
        form.addRow(label, widget)
        self._combos[path] = widget
        return widget

    def _add_editable_combo(
        self,
        form,
        label,
        path,
        choices,
        value,
        placeholder=None,
    ):
        from aqt.qt import QComboBox

        widget = QComboBox()
        widget.setEditable(True)
        widget.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        current_text = "" if value is None else str(value)
        widget.addItems(_sorted_unique_names([*choices, current_text]))
        if current_text:
            widget.setCurrentText(current_text)
        else:
            widget.setCurrentIndex(-1)
            widget.setEditText("")
        if placeholder and widget.lineEdit():
            widget.lineEdit().setPlaceholderText(placeholder)
        form.addRow(label, widget)
        self._editable_combos[path] = widget
        return widget

    def _add_check(self, form, label, path, value):
        from aqt.qt import QCheckBox

        widget = QCheckBox()
        widget.setChecked(bool(value))
        form.addRow(label, widget)
        self._checks[path] = widget
        return widget

    def _add_spin(self, form, label, path, value, minimum, maximum, suffix=""):
        from aqt.qt import QSpinBox

        widget = QSpinBox()
        widget.setRange(minimum, maximum)
        widget.setValue(int(value))
        if suffix:
            widget.setSuffix(suffix)
        form.addRow(label, widget)
        self._spins[path] = widget
        return widget

    def _build_general_tab(self):
        config = self._initial_config
        tab, form = self._new_form_tab()

        self._add_editable_combo(
            form,
            "Vocabulary deck",
            ("deck_name",),
            self._deck_names,
            config["deck_name"],
        )
        self._add_combo(
            form,
            "Input mode",
            ("input_mode",),
            [
                ("Separate kanji and reading fields", "two"),
                ("Furigana field", "single"),
            ],
            config["input_mode"],
        )
        self._add_editable_combo(
            form,
            "Single furigana field",
            ("input_fields", "single"),
            self._field_names,
            config["input_fields"]["single"],
        )
        self._add_editable_combo(
            form,
            "Kanji/surface field",
            ("input_fields", "kanji"),
            self._field_names,
            config["input_fields"]["kanji"],
        )
        self._add_editable_combo(
            form,
            "Reading field",
            ("input_fields", "reading"),
            self._field_names,
            config["input_fields"]["reading"],
        )
        self._add_check(
            form,
            "Simulation mode (treat every card as new)",
            ("simulate_zero_stability",),
            config["simulate_zero_stability"],
        )
        self._add_combo(
            form,
            "Kana-only card placement",
            ("no_kanji_merge_mode",),
            [
                ("Before kanji cards", "NO_KANJI_BEFORE"),
                ("After kanji cards", "NO_KANJI_AFTER"),
                ("Interleaved by score", "NO_KANJI_ZIPPED"),
            ],
            config["no_kanji_merge_mode"],
        )
        self._add_editable_combo(
            form,
            "Kana-only frequency field",
            ("no_kanji_frequency_field",),
            self._field_names,
            config["no_kanji_frequency_field"],
            placeholder="Leave blank to disable frequency ordering",
        )
        self._add_combo(
            form,
            "Kana-only frequency interpretation",
            ("no_kanji_frequency_type",),
            [
                ("Rank (lower is better)", "RANK"),
                ("Frequency (higher is better)", "FREQUENCY"),
            ],
            str(config["no_kanji_frequency_type"]).upper(),
        )
        return tab

    def _build_automation_tab(self):
        from aqt.qt import QLabel

        automatic = self._initial_config["automatic_processing"]
        tab, form = self._new_form_tab()
        note = QLabel(
            "Selected Anki lifecycle events start one exact background refresh. "
            "Score refreshes process the full vocabulary deck so positions and "
            "unlock metrics remain consistent. Repositioning also refreshes scores "
            "because the order depends on them."
        )
        note.setWordWrap(True)
        form.addRow(note)

        self._add_check(
            form,
            "Enable scheduled automatic processing",
            ("automatic_processing", "enabled"),
            automatic["enabled"],
        )
        self._add_check(
            form,
            "Run once after opening an Anki profile",
            ("automatic_processing", "run_on_startup"),
            automatic["run_on_startup"],
        )
        self._add_check(
            form,
            "Run when Anki enters a new scheduler day",
            ("automatic_processing", "run_on_new_day"),
            automatic["run_on_new_day"],
        )
        self._add_check(
            form,
            "Refresh scores and score-related fields",
            ("automatic_processing", "update_scores"),
            automatic["update_scores"],
        )
        self._add_check(
            form,
            "Refresh related words and kanji meanings",
            ("automatic_processing", "update_related_words"),
            automatic["update_related_words"],
        )
        self._add_check(
            form,
            "Reposition all new vocabulary cards",
            ("automatic_processing", "reposition_new_cards"),
            automatic["reposition_new_cards"],
        )
        self._add_spin(
            form,
            "Wait before starting an automatic refresh",
            ("automatic_processing", "delay_ms"),
            automatic["delay_ms"],
            0,
            60000,
            " ms",
        )
        return tab

    def _build_vocabulary_fields_tab(self):
        tab, form = self._new_form_tab()
        field_names = self._initial_config["field_names"]
        for key, label in VOCABULARY_FIELD_LABELS.items():
            self._add_editable_combo(
                form,
                label,
                ("field_names", key),
                self._field_names,
                field_names[key],
            )
        return tab

    def _build_reading_to_kanji_tab(self):
        config = self._initial_config["reading_to_kanji_cards"]
        tab, form = self._new_form_tab()
        self._add_editable_combo(
            form,
            "Target deck",
            ("reading_to_kanji_cards", "deck_name"),
            self._deck_names,
            config["deck_name"],
            placeholder="Blank: <vocabulary deck>::Reading->Kanji",
        )
        self._add_line_edit(
            form,
            "Note type",
            ("reading_to_kanji_cards", "note_type"),
            config["note_type"],
        )
        self._add_spin(
            form,
            "Maximum KANJIDIC grade",
            ("reading_to_kanji_cards", "max_grade"),
            config["max_grade"],
            1,
            99,
        )
        for key, label in READING_TO_KANJI_FIELD_LABELS.items():
            self._add_editable_combo(
                form,
                f"{label} field",
                ("reading_to_kanji_cards", "field_names", key),
                self._field_names,
                config["field_names"][key],
            )
        return tab

    def _build_sentence_tab(self):
        from aqt.qt import QPlainTextEdit

        config = self._initial_config["sentence_scoring"]
        tab, form = self._new_form_tab()
        decks = QPlainTextEdit()
        decks.setPlainText("\n".join(config["deck_names"]))
        decks.setMaximumHeight(90)
        form.addRow("Sentence decks (one per line)", decks)
        self._plain_text_edits[("sentence_scoring", "deck_names")] = decks

        self._add_line_edit(
            form,
            "Sentence note type",
            ("sentence_scoring", "note_type"),
            config["note_type"],
        )
        self._add_editable_combo(
            form,
            "Sentence text field",
            ("sentence_scoring", "sentence_field"),
            self._field_names,
            config["sentence_field"],
        )
        for key, label in SENTENCE_FIELD_LABELS.items():
            self._add_editable_combo(
                form,
                f"{label} field",
                ("sentence_scoring", "field_names", key),
                self._field_names,
                config["field_names"][key],
            )
        return tab

    def configured_values(self):
        config = normalize_config(self._initial_config)

        for path, widget in self._line_edits.items():
            value = widget.text().strip()
            _set_nested(config, path, value)
        for path, widget in self._editable_combos.items():
            value = widget.currentText().strip()
            if path == ("reading_to_kanji_cards", "deck_name") and not value:
                value = None
            _set_nested(config, path, value)
        for path, widget in self._combos.items():
            _set_nested(config, path, widget.currentData())
        for path, widget in self._checks.items():
            _set_nested(config, path, widget.isChecked())
        for path, widget in self._spins.items():
            _set_nested(config, path, widget.value())
        for path, widget in self._plain_text_edits.items():
            values = [
                line.strip()
                for line in widget.toPlainText().splitlines()
                if line.strip()
            ]
            _set_nested(config, path, values)

        return config

    def accept(self):
        from aqt.utils import showWarning

        config = self.configured_values()
        if errors := validate_config(config):
            showWarning("Please correct these settings:\n\n" + "\n".join(errors))
            return

        self._result_config = config
        super().accept()

    @property
    def result_config(self):
        return self._result_config


def open_settings_dialog(addon_module_name, mw_instance=None):
    """Open, validate, and persist the native CardScheduler settings dialog."""
    from aqt import mw
    from aqt.qt import QDialog
    from aqt.utils import showInfo

    anki_mw = mw if mw_instance is None else mw_instance
    config = load_anki_addon_config(addon_module_name, anki_mw)
    collection = getattr(anki_mw, "col", None)
    dialog = CardSchedulerSettingsDialog(
        normalize_config(config or get_default_config()),
        deck_names=available_deck_names(collection),
        field_names=available_field_names(collection),
        parent=anki_mw,
    )
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return False

    write_anki_addon_config(
        addon_module_name,
        dialog.result_config,
        mw_instance=anki_mw,
    )
    showInfo(
        "CardScheduler settings saved. Fully quit and reopen Anki to apply them."
    )
    return True
