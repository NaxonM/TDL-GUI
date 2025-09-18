import webbrowser
import json
import tempfile
import os
from PyQt6.QtCore import QUrl, QStringListModel, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QDialogButtonBox,
    QPlainTextEdit,
    QCheckBox,
    QGroupBox,
    QPushButton,
    QMenu,
    QLabel,
    QComboBox,
    QTabWidget,
    QWidget,
    QLineEdit,
    QCompleter,
    QInputDialog,
    QWidgetAction,
    QMessageBox,
    QStyle,
)
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtGui import QAction, QTextCursor
from src.expr_syntax_highlighter import ExprSyntaxHighlighter


class PresetMenuItem(QWidget):
    """A custom widget for an item in the preset menu."""
    clicked = pyqtSignal()

    def __init__(self, name, parent=None):
        super().__init__(parent)
        self.name = name

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 5, 5)

        self.name_label = QLabel(name)
        self.name_label.setToolTip(f"Load preset '{name}'")

        self.delete_button = QPushButton()
        self.delete_button.setObjectName("PresetDeleteButton")
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton)
        self.delete_button.setIcon(icon)
        self.delete_button.setFixedSize(20, 20)
        self.delete_button.setFlat(True)
        self.delete_button.setToolTip(f"Delete preset '{name}'")

        layout.addWidget(self.name_label)
        layout.addStretch()
        layout.addWidget(self.delete_button)
        self.setLayout(layout)

    def mouseReleaseEvent(self, event):
        # Emit the clicked signal only if the click was not on the delete button
        if not self.delete_button.geometry().contains(event.pos()):
            self.clicked.emit()
        # Let the delete button handle its own click event, which is processed before this
        super().mouseReleaseEvent(event)


class AdvancedForwardDialog(QDialog):
    def __init__(self, tdl_runner, settings_manager, logger, parent=None):
        super().__init__(parent)
        self.tdl_runner = tdl_runner
        self.settings_manager = settings_manager
        self.logger = logger
        self.setWindowTitle("Advanced Forward Options")
        self.setObjectName("AdvancedForwardDialog")
        self.setMinimumWidth(600)

        layout = QVBoxLayout(self)

        # Edit Message Tabs
        self.tabs = QTabWidget()
        self.simple_editor_tab = QWidget()
        self.advanced_editor_tab = QWidget()

        self.tabs.addTab(self.simple_editor_tab, "Simple Editor")
        self.tabs.addTab(self.advanced_editor_tab, "Advanced Editor")

        self._setup_simple_editor_tab()
        self._setup_advanced_editor_tab()

        # Other options
        options_group = QGroupBox("Options")
        options_layout = QFormLayout(options_group)

        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["direct", "clone"])
        self.mode_selector.setToolTip(
            "Direct: Official forward with header.\nClone: Copy content without header (may not work for all message types)."
        )
        options_layout.addRow("Forwarding Mode:", self.mode_selector)

        self.dry_run_checkbox = QCheckBox("Dry run (don't actually forward, just log)")
        self.dry_run_checkbox.setToolTip("Activates the --dry-run flag.")
        options_layout.addRow(self.dry_run_checkbox)

        self.silent_checkbox = QCheckBox("Silent forward (no notification)")
        self.silent_checkbox.setToolTip("Activates the --silent flag.")
        options_layout.addRow(self.silent_checkbox)

        self.no_group_checkbox = QCheckBox(
            "Disable grouped detection (forward album as single messages)"
        )
        self.no_group_checkbox.setToolTip("Activates the --single flag.")
        options_layout.addRow(self.no_group_checkbox)

        self.desc_order_checkbox = QCheckBox("Forward in descending order")
        self.desc_order_checkbox.setToolTip("Activates the --desc flag.")
        options_layout.addRow(self.desc_order_checkbox)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(self.tabs)
        layout.addWidget(options_group)
        layout.addWidget(button_box)

    def _setup_simple_editor_tab(self):
        layout = QFormLayout(self.simple_editor_tab)
        self.prepend_text_input = QPlainTextEdit()
        self.prepend_text_input.setFixedHeight(80)
        self.append_text_input = QPlainTextEdit()
        self.append_text_input.setFixedHeight(80)
        self.include_original_msg_checkbox = QCheckBox("Include original message text")
        self.include_original_msg_checkbox.setChecked(True)
        self.include_sender_checkbox = QCheckBox("Include sender's name")

        layout.addRow("Text to Prepend:", self.prepend_text_input)
        layout.addRow("Text to Append:", self.append_text_input)
        layout.addRow(self.include_original_msg_checkbox)
        layout.addRow(self.include_sender_checkbox)

    def _setup_advanced_editor_tab(self):
        layout = QVBoxLayout(self.advanced_editor_tab)
        group = QGroupBox("Edit Message Expression")
        main_edit_layout = QVBoxLayout(group)

        # Top part with text area and buttons
        top_layout = QHBoxLayout()
        self.edit_input = QPlainTextEdit()
        self.edit_input.setPlaceholderText(
            '# Example: Prepend sender name and append a signature\n`Forwarded from: ${From.VisibleName}\n\n${Message.Message}\n\n--\nSent via TDL-GUI`'
        )
        self.edit_input.setToolTip("Write your `expr` expression here. Press Ctrl+Space for autocompletion.")
        self.highlighter = ExprSyntaxHighlighter(self.edit_input.document())

        # Setup completer
        self.completer = QCompleter(self)
        self.completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.completer.setWidget(self.edit_input)
        self.completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)

        self._update_completer_model("")
        self.edit_input.textChanged.connect(self._update_completer_model_on_text_change)

        top_layout.addWidget(self.edit_input)

        # Vertical layout for helper buttons
        button_v_layout = QVBoxLayout()

        self.placeholder_combo = QComboBox()
        self.placeholder_combo.addItems([
            "Message.Message",
            "From.VisibleName",
            "From.ID",
            "Message.Date",
            "Message.Views",
        ])
        insert_placeholder_button = QPushButton("Insert Placeholder")
        insert_placeholder_button.clicked.connect(self._insert_placeholder_from_combo)

        example_button = QPushButton("Show Examples")
        example_button.setMenu(self._create_example_menu())

        clear_button = QPushButton("Clear")
        clear_button.clicked.connect(self.edit_input.clear)

        button_v_layout.addWidget(self.placeholder_combo)
        button_v_layout.addWidget(insert_placeholder_button)
        button_v_layout.addWidget(example_button)
        button_v_layout.addWidget(clear_button)
        button_v_layout.addStretch()
        top_layout.addLayout(button_v_layout)

        # Bottom part with buttons
        self.load_preset_button = QPushButton("Load Preset")
        self.load_preset_button.setToolTip("Load a previously saved expression preset.")
        self.load_preset_button.clicked.connect(self._on_load_preset)
        self.save_preset_button = QPushButton("Save Preset")
        self.save_preset_button.setToolTip("Save the current expression as a preset for later use.")
        self.save_preset_button.clicked.connect(self._on_save_preset)

        bottom_button_layout = QHBoxLayout()
        bottom_button_layout.addStretch()
        bottom_button_layout.addWidget(self.load_preset_button)
        bottom_button_layout.addWidget(self.save_preset_button)

        doc_label = QLabel(
            '<a href="https://docs.iyear.me/tdl/guide/forward/#edit">Read the expression guide for more details.</a>'
        )
        doc_label.setOpenExternalLinks(True)

        main_edit_layout.addLayout(top_layout)
        main_edit_layout.addLayout(bottom_button_layout)
        main_edit_layout.addWidget(doc_label)
        layout.addWidget(group)

    def _insert_placeholder_from_combo(self):
        self.edit_input.insertPlainText(self.placeholder_combo.currentText())

    def _create_example_menu(self):
        menu = QMenu(self)
        examples = {
            "Append Text": 'Message.Message + "\n-- Appended Text"',
            "Prepend Text": '"Prepended Text --\n" + Message.Message',
            "Add Sender Name": '`Forwarded from: ${From.VisibleName}\n\n${Message.Message}`',
            "Convert to Uppercase": "upper(Message.Message)",
            "Replace Words": 'replace(Message.Message, "old", "new")',
        }
        for text, expr in examples.items():
            action = QAction(text, self)
            action.triggered.connect(lambda checked, content=expr: self._insert_example(content))
            menu.addAction(action)
        return menu

    def _insert_example(self, text):
        self.edit_input.setPlainText(text)

    def _generate_simple_expression(self):
        parts = []
        prepend_text = self.prepend_text_input.toPlainText().strip()
        append_text = self.append_text_input.toPlainText().strip()

        if self.include_sender_checkbox.isChecked():
            parts.append('From.VisibleName + ":\\n"')

        if prepend_text:
            parts.append(f'"{prepend_text}\\n"')

        if self.include_original_msg_checkbox.isChecked():
            parts.append("Message.Message")

        if append_text:
            parts.append(f'"\\n{append_text}"')

        return " + ".join(parts) if parts else ""

    def _update_completer_model_on_text_change(self):
        cursor = self.edit_input.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        word = cursor.selectedText()

        if '.' in word:
            base = word.split('.')[0]
            self._update_completer_model(base)
        else:
            self._update_completer_model("")

    def _update_completer_model(self, prefix):
        if prefix.lower() == "message":
            word_list = ["Message", "Date", "Views", "ID"]
        elif prefix.lower() == "from":
            word_list = ["VisibleName", "ID"]
        else:
            word_list = [
                "let", "in", "and", "or", "not", "matches", "true", "false", "nil",
                "trim", "trimPrefix", "trimSuffix", "upper", "lower", "split",
                "splitAfter", "replace", "repeat", "indexOf", "lastIndexOf",
                "hasPrefix", "hasSuffix", "now", "duration", "date", "timezone",
                "max", "min", "abs", "ceil", "floor", "round", "all", "any", "one",
                "none", "map", "filter", "find", "findIndex", "findLast",
                "findLastIndex", "groupBy", "count", "concat", "flatten", "uniq",
                "join", "reduce", "sum", "mean", "median", "first", "last", "take",
                "reverse", "sort", "sortBy", "keys", "values", "type", "int",
                "float", "string", "toJSON", "fromJSON", "toBase64", "fromBase64",
                "toPairs", "fromPairs", "len", "get", "bitand", "bitor", "bitxor",
                "bitnand", "bitnot", "bitshl", "bitshr", "bitushr",
                "Message", "From"
            ]

        model = QStringListModel(word_list, self)
        self.completer.setModel(model)

    def _on_save_preset(self):
        expression = self.edit_input.toPlainText().strip()
        if not expression:
            self.logger.warning("Preset is empty, not saving.")
            return

        preset_name, ok = QInputDialog.getText(
            self, "Save Preset", "Enter a name for the preset:"
        )

        if ok and preset_name:
            presets = self.settings_manager.get("presets", {})
            presets[preset_name] = expression
            self.settings_manager.set("presets", presets)
            self.settings_manager.save_settings()
            self.logger.info(f"Saved preset '{preset_name}'.")

    def _on_load_preset(self):
        presets = self.settings_manager.get("presets", {})
        if not presets:
            self.logger.info("No saved presets found.")
            # Optionally, show a disabled menu item
            menu = QMenu(self)
            action = QAction("No Saved Presets", self)
            action.setEnabled(False)
            menu.addAction(action)
            menu.exec(self.load_preset_button.mapToGlobal(self.load_preset_button.rect().bottomLeft()))
            return

        menu = QMenu(self)
        for name, expression in presets.items():
            widget_action = self._create_preset_widget(name, expression, menu)
            menu.addAction(widget_action)

        menu.exec(self.load_preset_button.mapToGlobal(self.load_preset_button.rect().bottomLeft()))

    def _create_preset_widget(self, name, expression, menu):
        menu_item = PresetMenuItem(name)

        # Connect the custom signals to the desired actions
        menu_item.clicked.connect(lambda: (self.edit_input.setPlainText(expression), menu.close()))
        menu_item.delete_button.clicked.connect(lambda: self._on_delete_preset(name, menu))

        widget_action = QWidgetAction(self)
        widget_action.setDefaultWidget(menu_item)
        return widget_action

    def _on_delete_preset(self, name, menu):
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            presets = self.settings_manager.get("presets", {})
            if name in presets:
                del presets[name]
                self.settings_manager.set("presets", presets)
                self.settings_manager.save_settings()
                self.logger.info(f"Deleted preset '{name}'.")
            menu.close()

    def get_settings(self):
        """Returns a dictionary of the selected settings."""
        edit_expression = ""
        if self.tabs.currentWidget() == self.simple_editor_tab:
            edit_expression = self._generate_simple_expression()
        else:
            edit_expression = self.edit_input.toPlainText().strip()

        return {
            "mode": self.mode_selector.currentText(),
            "edit_expression": edit_expression,
            "dry_run": self.dry_run_checkbox.isChecked(),
            "silent": self.silent_checkbox.isChecked(),
            "no_group": self.no_group_checkbox.isChecked(),
            "desc_order": self.desc_order_checkbox.isChecked(),
        }
