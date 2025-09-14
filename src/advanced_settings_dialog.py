from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout, QLineEdit,
    QSpinBox, QCheckBox, QComboBox, QDialogButtonBox, QHBoxLayout, QToolButton,
    QGroupBox
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QAbstractSpinBox, QStyle


class AdvancedSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Download Options")
        self.setMinimumWidth(600)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.tabs = QTabWidget()
        self.general_tab = self._create_general_tab()
        self.filters_naming_tab = self._create_filters_naming_tab()

        self.tabs.addTab(self.general_tab, "General")
        self.tabs.addTab(self.filters_naming_tab, "Filters & Naming")

        layout.addWidget(self.tabs)

        # OK and Cancel buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _create_general_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 10, 5, 5)

        col1_layout = QVBoxLayout()
        concurrency_group = QGroupBox("Concurrency")
        concurrency_form = QFormLayout(concurrency_group)
        tasks_widget, self.concurrent_tasks_spinbox = self._create_spinbox_with_arrows(1, 16, 2)
        self.concurrent_tasks_spinbox.setToolTip("Set the maximum number of files to download at the same time.")
        threads_widget, self.threads_per_task_spinbox = self._create_spinbox_with_arrows(1, 16, 4)
        self.threads_per_task_spinbox.setToolTip("Set the maximum number of parallel connections for a single file.")
        concurrency_form.addRow("Concurrent Tasks:", tasks_widget)
        concurrency_form.addRow("Threads per Task:", threads_widget)
        col1_layout.addWidget(concurrency_group)

        pool_group = QGroupBox("Connection")
        pool_form = QFormLayout(pool_group)
        pool_widget, self.pool_spinbox = self._create_spinbox_with_arrows(0, 100, 8)
        self.pool_spinbox.setToolTip("Advanced: The size of the DC pool for the Telegram client.\nLeave at 8 unless you have connection issues.")
        pool_form.addRow("DC Pool Size:", pool_widget)
        col1_layout.addWidget(pool_group)

        delay_group = QGroupBox("Rate Limiting")
        delay_form = QFormLayout(delay_group)
        delay_layout = QHBoxLayout()
        delay_widget, self.delay_spinbox = self._create_spinbox_with_arrows(0, 99999, 0)
        self.delay_spinbox.setToolTip("Wait a specified amount of time between download tasks to avoid API rate limits.")
        self.delay_unit_combo = QComboBox()
        self.delay_unit_combo.addItems(["ms", "s", "m"])
        delay_layout.addWidget(delay_widget, 1)
        delay_layout.addWidget(self.delay_unit_combo)
        delay_form.addRow("Delay per Task:", delay_layout)
        col1_layout.addWidget(delay_group)
        col1_layout.addStretch()

        col2_layout = QVBoxLayout()
        flags_group = QGroupBox("Behavioral Flags")
        flags_layout = QVBoxLayout(flags_group)
        self.desc_checkbox = QCheckBox("Download in descending order")
        self.desc_checkbox.setToolTip("Download files from newest to oldest instead of the default (oldest to newest).")
        self.skip_same_checkbox = QCheckBox("Skip identical files")
        self.skip_same_checkbox.setToolTip("If a file with the same name and size already exists in the destination, skip it.")
        self.skip_same_checkbox.setChecked(True)
        self.rewrite_ext_checkbox = QCheckBox("Rewrite file extension")
        self.rewrite_ext_checkbox.setToolTip("Renames the file extension based on its actual content type (MIME type).")
        self.group_checkbox = QCheckBox("Auto-download albums/groups")
        self.group_checkbox.setToolTip("If a message link points to a file in an album, download all other files in that album automatically.")
        self.takeout_checkbox = QCheckBox("Use takeout session (lowers limits)")
        self.takeout_checkbox.setToolTip("Use a special session type that is less prone to API rate limits.\nUseful for very large downloads.")
        flags = [self.desc_checkbox, self.skip_same_checkbox, self.rewrite_ext_checkbox, self.group_checkbox, self.takeout_checkbox]
        for flag in flags:
            flags_layout.addWidget(flag)
        flags_layout.addStretch()
        col2_layout.addWidget(flags_group)

        layout.addLayout(col1_layout, 1)
        layout.addLayout(col2_layout, 1)
        return widget

    def _create_filters_naming_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 10, 5, 5)

        filters_group = QGroupBox("File Filters")
        filters_form = QFormLayout(filters_group)
        self.include_ext_input = QLineEdit()
        self.include_ext_input.setPlaceholderText("e.g., mp4,mkv,zip")
        self.include_ext_input.setToolTip("Only download files with these extensions. Cannot be used with Exclude.")
        self.exclude_ext_input = QLineEdit()
        self.exclude_ext_input.setPlaceholderText("e.g., jpg,png,gif")
        self.exclude_ext_input.setToolTip("Do not download files with these extensions. Cannot be used with Include.")
        filters_form.addRow("Include Exts:", self.include_ext_input)
        filters_form.addRow("Exclude Exts:", self.exclude_ext_input)
        layout.addWidget(filters_group)

        template_group = QGroupBox("Filename Template")
        template_v_layout = QVBoxLayout(template_group)
        template_h_layout = QHBoxLayout()
        self.template_combo = QComboBox()
        self.template_combo.addItems(["Default: {{ .DialogID }}_{{ .MessageID }}_{{ filenamify .FileName }}", "{{ .DialogID }}/{{ .FileName }}", "{{ .MessageID }}-{{ .FileName }}", "{{ .FileName }}", "Custom..."])
        self.template_input = QLineEdit()
        self.template_input.setPlaceholderText("Enter custom template...")
        self.template_input.setVisible(False)
        template_help_button = QToolButton()
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MessageBoxQuestion)
        template_help_button.setIcon(icon)
        template_help_button.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://docs.iyear.me/tdl/guide/template/")))
        template_h_layout.addWidget(self.template_combo, 1)
        template_h_layout.addWidget(self.template_input, 1)
        template_h_layout.addWidget(template_help_button)
        template_v_layout.addLayout(template_h_layout)

        self.placeholder_widget = self._create_template_placeholders()
        self.placeholder_widget.setVisible(False)
        template_v_layout.addWidget(self.placeholder_widget)

        layout.addWidget(template_group)
        layout.addStretch()
        return widget

    def _create_template_placeholders(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 0)
        placeholders = ["FileName", "MessageID", "DialogID", "FileSize", "Ext", "Date", "Time"]
        for placeholder in placeholders:
            button = QToolButton()
            button.setText(f"{{{placeholder}}}")
            button.clicked.connect(partial(self.insert_template_placeholder, placeholder))
            layout.addWidget(button)
        layout.addStretch()
        return widget

    def get_settings(self):
        # This method will be used to retrieve the settings from the dialog
        return {
            'concurrent_tasks': self.concurrent_tasks_spinbox.value(),
            'threads_per_task': self.threads_per_task_spinbox.value(),
            'pool_size': self.pool_spinbox.value(),
            'delay': self.delay_spinbox.value(),
            'delay_unit': self.delay_unit_combo.currentText(),
            'desc_order': self.desc_checkbox.isChecked(),
            'skip_same': self.skip_same_checkbox.isChecked(),
            'rewrite_ext': self.rewrite_ext_checkbox.isChecked(),
            'group_albums': self.group_checkbox.isChecked(),
            'use_takeout': self.takeout_checkbox.isChecked(),
            'include_exts': self.include_ext_input.text(),
            'exclude_exts': self.exclude_ext_input.text(),
            'template': self.template_input.text() if self.template_combo.currentText() == "Custom..." else self.template_combo.currentText(),
        }

    def _create_spinbox_with_arrows(self, min_val, max_val, default_val):
        # This is a helper method copied from main_window.py
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        spinbox = QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setValue(default_val)
        spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        up_button = QToolButton(arrowType=Qt.ArrowType.UpArrow, clicked=spinbox.stepUp)
        down_button = QToolButton(arrowType=Qt.ArrowType.DownArrow, clicked=spinbox.stepDown)

        layout.addWidget(spinbox, 1)
        layout.addWidget(down_button)
        layout.addWidget(up_button)
        return container, spinbox

    def insert_template_placeholder(self, placeholder):
        self.template_combo.setCurrentText("Custom...")
        self.template_input.setFocus()
        cursor_pos = self.template_input.cursorPosition()
        current_text = self.template_input.text()
        new_text = f"{current_text[:cursor_pos]}{{{{ .{placeholder} }}}}{current_text[cursor_pos:]}"
        self.template_input.setText(new_text)
        self.template_input.setCursorPosition(cursor_pos + len(f"{{{{ .{placeholder} }}}}"))

    def _create_spinbox_with_arrows(self, min_val, max_val, default_val):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        spinbox = QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setValue(default_val)
        spinbox.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

        up_button = QToolButton(arrowType=Qt.ArrowType.UpArrow, clicked=spinbox.stepUp)
        down_button = QToolButton(arrowType=Qt.ArrowType.DownArrow, clicked=spinbox.stepDown)

        layout.addWidget(spinbox, 1)
        layout.addWidget(down_button)
        layout.addWidget(up_button)
        return container, spinbox
