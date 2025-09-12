# main_window.py

import sys
import os
import glob
import json
import tempfile
import urllib.request
import subprocess
from PyQt6.QtCore import pyqtSignal, QDir, QUrl, QDate, QDateTime, Qt, QSize
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QFormLayout, QMenu, QPlainTextEdit, QGroupBox, QPushButton,
    QLineEdit, QToolButton, QSpinBox, QCheckBox, QRadioButton, QProgressBar,
    QFileDialog, QMessageBox, QDateEdit, QLabel, QComboBox, QScrollArea, QStackedWidget,
    QAbstractSpinBox, QStyle
)
from PyQt6.QtGui import QAction, QDesktopServices, QColor, QTextCursor, QTextCharFormat, QPalette

from functools import partial
from worker import Worker
from settings_dialog import SettingsDialog
from utility_dialog import UtilityDialog
from progress_widget import DownloadProgressWidget

class MainWindow(QMainWindow):
    log_message = pyqtSignal(str)

    # Configuration for utility commands
    UTILITY_CONFIGS = {
        'list_chats': {
            'title': 'List Chats',
            'base_cmd': ['tdl', 'chat', 'ls'],
            'fields': [{'name': 'filter', 'label': 'Filter Expression:', 'arg': '--filter'}]
        },
        'export_members': {
            'title': 'Export Members',
            'base_cmd': ['tdl', 'chat', 'users'],
            'fields': [
                {'name': 'chat_id', 'label': 'Chat ID or Username:', 'arg': '-c'},
                {'name': 'output_file', 'label': 'Output JSON File:', 'arg': '-o', 'type': 'save_file'}
            ]
        },
        'backup_data': {
            'title': 'Backup Data',
            'base_cmd': ['tdl', 'backup'],
            'fields': [{'name': 'output_file', 'label': 'Backup File Path:', 'arg': '-d', 'type': 'save_file'}]
        },
        'recover_data': {
            'title': 'Recover Data',
            'base_cmd': ['tdl', 'recover'],
            'fields': [{'name': 'input_file', 'label': 'Backup File to Restore:', 'arg': '-f', 'type': 'open_file'}]
        },
        'migrate_data': {
            'title': 'Migrate Data',
            'base_cmd': ['tdl', 'migrate'],
            'fields': [
                {'name': 'destination', 'label': 'Destination Storage (e.g., type=file,path=...):', 'arg': '--to'}
            ]
        },
    }

    def __init__(self, tdl_path, theme='light'):
        super().__init__()
        self.tdl_path = tdl_path
        self.theme = theme
        self.worker = None
        self.progress_widgets = {}
        self.download_controls = []
        self.export_controls = []
        self.has_started_download = False

        self._init_settings()
        self._init_ui()
        self._setup_connections()
        self.log_message.emit("Application initialized.")

    def _init_settings(self):
        """Initializes settings and theme-dependent variables."""
        self.settings = {
            'debug_mode': False, 'storage_path': '', 'auto_proxy': True,
            'manual_proxy': '', 'storage_driver': 'bolt', 'namespace': 'default',
            'command_timeout': 300, 'ntp_server': '', 'reconnect_timeout': '5m'
        }
        if self.theme == 'dark':
            self.error_color = QColor("#BF616A")
        else:
            self.error_color = QColor("#D32F2F")

    def _init_ui(self):
        """Initializes the main UI components."""
        self.setWindowTitle("tdl GUI")
        self.setGeometry(100, 100, 750, 650)

        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        self.download_tab = self._create_download_tab()
        self.export_tab = self._create_export_tab()
        self.log_tab = self._create_log_tab()

        self.tabs.addTab(self.download_tab, "Download")
        self.tabs.addTab(self.export_tab, "Export")
        self.tabs.addTab(self.log_tab, "Log")

        self._create_menu_bar()
        self._create_status_bar()

    def _setup_connections(self):
        """Connects all signals to slots."""
        self.log_message.connect(self.append_log)
        # Download Tab Connections
        self.start_download_button.clicked.connect(self.handle_download_button)
        self.resume_download_button.clicked.connect(self.handle_resume_button)
        self.load_from_file_button.clicked.connect(self.load_source_from_file)
        self.browse_dest_button.clicked.connect(self.select_destination_directory)
        self.clear_source_button.clicked.connect(self.source_input.clear)
        self.template_combo.currentTextChanged.connect(self._on_template_change)
        self.include_ext_input.textChanged.connect(self.on_include_text_changed)
        self.exclude_ext_input.textChanged.connect(self.on_exclude_text_changed)
        self.advanced_group.toggled.connect(lambda checked: self.advanced_tabs.setVisible(checked))
        # Export Tab Connections
        self.run_export_button.clicked.connect(self.handle_export_button)
        self.export_type_combo.currentIndexChanged.connect(self.filter_stack.setCurrentIndex)

    def _create_download_tab(self):
        """Creates the main 'Download' tab widget."""
        widget = QWidget()
        grid_layout = QGridLayout(widget)
        grid_layout.setSpacing(10)

        # Create widgets
        source_group = self._create_download_source_group()
        dest_group = self._create_download_destination_group()
        self.advanced_group = self._create_download_advanced_group()
        progress_group = self._create_download_progress_group()

        self.start_download_button = QPushButton("Start Download")
        self.start_download_button.setObjectName("ActionButton")
        self.resume_download_button = QPushButton("Resume Last Download")
        self.resume_download_button.setObjectName("ActionButton")
        self.resume_download_button.setEnabled(False)

        action_button_layout = QHBoxLayout()
        action_button_layout.addStretch()
        action_button_layout.addWidget(self.start_download_button)
        action_button_layout.addWidget(self.resume_download_button)
        action_button_layout.addStretch()

        # Arrange widgets on the grid
        grid_layout.addWidget(source_group, 0, 0, 1, 2)
        grid_layout.addWidget(dest_group, 1, 0)
        grid_layout.addWidget(self.advanced_group, 1, 1)
        grid_layout.addLayout(action_button_layout, 2, 0, 1, 2)
        grid_layout.addWidget(progress_group, 3, 0, 1, 2)

        grid_layout.setColumnStretch(0, 1)
        grid_layout.setColumnStretch(1, 1)

        self.download_controls.extend([
            self.source_input, self.load_from_file_button, self.clear_source_button,
            self.dest_path_input, self.browse_dest_button, self.advanced_group
        ])
        return widget

    def _create_download_source_group(self):
        group = QGroupBox("Source Input")
        layout = QVBoxLayout(group)
        self.source_input = QPlainTextEdit()
        self.source_input.setPlaceholderText("Paste message links or file paths here, one per line.")
        
        button_layout = QHBoxLayout()
        self.load_from_file_button = QPushButton("Load from File...")
        self.clear_source_button = QPushButton("Clear")
        button_layout.addWidget(self.load_from_file_button)
        button_layout.addWidget(self.clear_source_button)
        button_layout.addStretch()
        
        layout.addWidget(self.source_input)
        layout.addLayout(button_layout)
        return group

    def _create_download_destination_group(self):
        group = QGroupBox("Destination Directory")
        layout = QHBoxLayout(group)
        self.dest_path_input = QLineEdit()
        default_dest = QDir.home().filePath("Downloads")
        self.dest_path_input.setPlaceholderText(f"Default: {default_dest}")
        
        self.browse_dest_button = QToolButton()
        icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        self.browse_dest_button.setIcon(icon)
        
        layout.addWidget(self.dest_path_input)
        layout.addWidget(self.browse_dest_button)
        return group

    def _create_download_advanced_group(self):
        group = QGroupBox("Advanced Options")
        group.setCheckable(True)
        group.setChecked(False)
        group_layout = QVBoxLayout(group)
        
        self.advanced_tabs = QTabWidget()
        general_tab = self._create_adv_general_tab()
        filters_naming_tab = self._create_adv_filters_naming_tab()
        
        self.advanced_tabs.addTab(general_tab, "General")
        self.advanced_tabs.addTab(filters_naming_tab, "Filters & Naming")
        self.advanced_tabs.setVisible(False)
        
        group_layout.addWidget(self.advanced_tabs)
        return group

    def _create_adv_general_tab(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(5, 10, 5, 5)

        col1_layout = QVBoxLayout()
        concurrency_group = QGroupBox("Concurrency")
        concurrency_form = QFormLayout(concurrency_group)
        tasks_widget, self.concurrent_tasks_spinbox = self._create_spinbox_with_arrows(1, 16, 2)
        threads_widget, self.threads_per_task_spinbox = self._create_spinbox_with_arrows(1, 16, 4)
        concurrency_form.addRow("Concurrent Tasks:", tasks_widget)
        concurrency_form.addRow("Threads per Task:", threads_widget)
        col1_layout.addWidget(concurrency_group)
        
        pool_group = QGroupBox("Connection")
        pool_form = QFormLayout(pool_group)
        pool_widget, self.pool_spinbox = self._create_spinbox_with_arrows(0, 100, 8)
        pool_form.addRow("DC Pool Size:", pool_widget)
        col1_layout.addWidget(pool_group)

        delay_group = QGroupBox("Rate Limiting")
        delay_form = QFormLayout(delay_group)
        delay_layout = QHBoxLayout()
        delay_widget, self.delay_spinbox = self._create_spinbox_with_arrows(0, 99999, 0)
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
        self.skip_same_checkbox = QCheckBox("Skip identical files")
        self.skip_same_checkbox.setChecked(True)
        self.rewrite_ext_checkbox = QCheckBox("Rewrite file extension")
        self.group_checkbox = QCheckBox("Auto-download albums/groups")
        self.takeout_checkbox = QCheckBox("Use takeout session (lowers limits)")
        flags = [self.desc_checkbox, self.skip_same_checkbox, self.rewrite_ext_checkbox, self.group_checkbox, self.takeout_checkbox]
        for flag in flags:
            flags_layout.addWidget(flag)
        flags_layout.addStretch()
        col2_layout.addWidget(flags_group)

        layout.addLayout(col1_layout, 1)
        layout.addLayout(col2_layout, 1)
        return widget

    def _create_adv_filters_naming_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 10, 5, 5)

        filters_group = QGroupBox("File Filters")
        filters_form = QFormLayout(filters_group)
        self.include_ext_input = QLineEdit()
        self.include_ext_input.setPlaceholderText("e.g., mp4,mkv,zip")
        self.exclude_ext_input = QLineEdit()
        self.exclude_ext_input.setPlaceholderText("e.g., jpg,png,gif")
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

    def _create_download_progress_group(self):
        group = QGroupBox("Live Downloads")
        layout = QVBoxLayout(group)
        progress_area = QScrollArea()
        progress_area.setWidgetResizable(True)
        progress_area.setMinimumHeight(150)
        
        progress_widget_container = QWidget()
        self.progress_layout = QVBoxLayout(progress_widget_container)
        self.progress_layout.addStretch()
        progress_area.setWidget(progress_widget_container)
        
        layout.addWidget(progress_area)
        return group

    def _create_export_tab(self):
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setSpacing(10)

        source_group = self._create_export_source_group()
        options_group = self._create_export_options_group()
        content_group = self._create_export_content_group()
        
        self.run_export_button = QPushButton("Export to JSON...")
        self.run_export_button.setObjectName("ActionButton")

        self.export_advanced_group = self._create_export_advanced_group()

        action_button_layout = QHBoxLayout()
        action_button_layout.addStretch()
        action_button_layout.addWidget(self.run_export_button)
        action_button_layout.addStretch()

        main_layout.addWidget(source_group)
        main_layout.addWidget(options_group)
        main_layout.addWidget(content_group)
        main_layout.addWidget(self.export_advanced_group)
        main_layout.addLayout(action_button_layout)
        main_layout.addStretch()

        self.export_controls.extend([
            self.export_source_input, self.export_type_combo, self.filter_stack,
            self.export_with_content_checkbox, self.export_all_types_checkbox,
            self.export_advanced_group
        ])
        return widget
        
    def _create_export_source_group(self):
        group = QGroupBox("Export Source")
        layout = QFormLayout(group)
        self.export_source_input = QLineEdit()
        self.export_source_input.setPlaceholderText("Enter Channel/Chat ID or Username")
        layout.addRow("Channel/Chat Source:", self.export_source_input)
        return group

    def _create_export_options_group(self):
        group = QGroupBox("Export Options")
        layout = QFormLayout(group)
        
        self.export_type_combo = QComboBox()
        self.export_type_combo.addItems(["All Messages", "By Time Range", "By ID Range", "Last N Messages"])
        
        self.filter_stack = QStackedWidget()
        self.filter_stack.addWidget(QWidget())
        
        time_range_widget = QWidget()
        time_range_layout = QHBoxLayout(time_range_widget)
        self.from_date_edit = QDateEdit(calendarPopup=True, displayFormat="yyyy-MM-dd")
        self.to_date_edit = QDateEdit(calendarPopup=True, displayFormat="yyyy-MM-dd", date=QDate.currentDate())
        time_range_layout.addWidget(QLabel("From:"))
        time_range_layout.addWidget(self.from_date_edit)
        time_range_layout.addWidget(QLabel("To:"))
        time_range_layout.addWidget(self.to_date_edit)
        self.filter_stack.addWidget(time_range_widget)
        
        id_range_widget = QWidget()
        id_range_layout = QHBoxLayout(id_range_widget)
        self.from_id_input = QLineEdit(placeholderText="e.g., 1")
        self.to_id_input = QLineEdit(placeholderText="e.g., 1000")
        id_range_layout.addWidget(QLabel("From ID:"))
        id_range_layout.addWidget(self.from_id_input)
        id_range_layout.addWidget(QLabel("To ID:"))
        id_range_layout.addWidget(self.to_id_input)
        self.filter_stack.addWidget(id_range_widget)
        
        last_n_widget = QWidget()
        last_n_layout = QHBoxLayout(last_n_widget)
        self.last_n_spinbox = QSpinBox(minimum=1, maximum=1_000_000, value=100)
        last_n_layout.addWidget(QLabel("Number of messages:"))
        last_n_layout.addWidget(self.last_n_spinbox)
        last_n_layout.addStretch()
        self.filter_stack.addWidget(last_n_widget)
        
        layout.addRow("Export Type:", self.export_type_combo)
        layout.addRow(self.filter_stack)
        return group

    def _create_export_content_group(self):
        group = QGroupBox("Additional Content")
        layout = QHBoxLayout(group)
        self.export_with_content_checkbox = QCheckBox("Include message text/captions")
        self.export_with_content_checkbox.setChecked(True)
        self.export_all_types_checkbox = QCheckBox("Include non-media messages")
        layout.addWidget(self.export_with_content_checkbox)
        layout.addWidget(self.export_all_types_checkbox)
        return group
    
    def _create_export_advanced_group(self):
        group = QGroupBox("Advanced Filtering")
        group.setCheckable(True)
        group.setChecked(False)

        form_layout = QFormLayout()
        self.export_filter_input = QLineEdit()
        self.export_filter_input.setPlaceholderText("e.g., 'IsPhoto && HasViews'")
        self.export_reply_input = QLineEdit()
        self.export_reply_input.setPlaceholderText("Export replies to a specific message ID")
        self.export_topic_input = QLineEdit()
        self.export_topic_input.setPlaceholderText("Export from a specific topic/forum ID")

        form_layout.addRow("Filter Expression:", self.export_filter_input)
        form_layout.addRow("Replies to Message ID:", self.export_reply_input)
        form_layout.addRow("Topic ID:", self.export_topic_input)

        container_widget = QWidget()
        container_widget.setLayout(form_layout)
        container_widget.setVisible(False)

        group_layout = QVBoxLayout(group)
        group_layout.addWidget(container_widget)

        group.toggled.connect(container_widget.setVisible)

        return group

    def _create_log_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("LogOutput")
        layout.addWidget(self.log_output)
        return widget

    def _create_status_bar(self):
        self.status_label = QLabel("Ready")
        self.status_progress = QProgressBar()
        self.status_progress.setRange(0, 100)
        self.status_progress.setFixedSize(150, 16)
        self.status_progress.setTextVisible(False)
        self.status_progress.hide()

        self.cpu_label = QLabel("CPU: N/A")
        self.mem_label = QLabel("Mem: N/A")
        self.cpu_label.setObjectName("StatsLabel")
        self.mem_label.setObjectName("StatsLabel")

        self.statusBar().addPermanentWidget(self.status_label)
        self.statusBar().addPermanentWidget(self.status_progress)
        self.statusBar().addPermanentWidget(self.cpu_label)
        self.statusBar().addPermanentWidget(self.mem_label)
        self.statusBar().showMessage("Ready")

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

    def set_task_running_ui_state(self, is_running):
        """Enables or disables UI controls based on the state of a running task."""
        if self.tools_menu not in self.download_controls:
            self.download_controls.append(self.tools_menu)

        all_controls = self.download_controls + self.export_controls
        for widget in all_controls:
            widget.setEnabled(not is_running)
        
        # Explicitly handle the main action buttons
        self.start_download_button.setText("Stop Download" if is_running else "Start Download")
        self.run_export_button.setEnabled(not is_running)
        
        if is_running:
            self.resume_download_button.setEnabled(False)
            self.start_download_button.setProperty("class", "stop-button")
            self.status_progress.show()
            self.status_label.setText("Starting...")
            self.cpu_label.setText("CPU: ...")
            self.mem_label.setText("Mem: ...")
        else:
            if self.has_started_download:
                self.resume_download_button.setEnabled(True)
            self.start_download_button.setProperty("class", "")
            self.status_progress.hide()
            self.cpu_label.setText("CPU: N/A")
            self.mem_label.setText("Mem: N/A")

        self.start_download_button.style().unpolish(self.start_download_button)
        self.start_download_button.style().polish(self.start_download_button)
        
    def _on_template_change(self, text):
        is_custom = (text == "Custom...")
        self.template_input.setVisible(is_custom)
        self.placeholder_widget.setVisible(is_custom)

    def insert_template_placeholder(self, placeholder):
        self.template_combo.setCurrentText("Custom...")
        self.template_input.setFocus()
        cursor_pos = self.template_input.cursorPosition()
        current_text = self.template_input.text()
        new_text = f"{current_text[:cursor_pos]}{{{{ .{placeholder} }}}}{current_text[cursor_pos:]}"
        self.template_input.setText(new_text)
        self.template_input.setCursorPosition(cursor_pos + len(f"{{{{ .{placeholder} }}}}"))

    def append_log(self, message):
        cursor = self.log_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        char_format = QTextCharFormat()
        default_color = self.palette().color(QPalette.ColorRole.Text)
        char_format.setForeground(default_color)
        if "[ERROR]" in message or "Traceback" in message or "failed" in message.lower():
            char_format.setForeground(self.error_color)
        cursor.setCharFormat(char_format)
        cursor.insertText(message + '\n')
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.setCharFormat(QTextCharFormat())
        self.log_output.setTextCursor(cursor)
        self.statusBar().showMessage(message, 5000)

    def _create_menu_bar(self):
        menu_bar = self.menuBar()
        file_menu = menu_bar.addMenu("&File")
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        self.tools_menu = menu_bar.addMenu("&Tools")
        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self.open_settings_dialog)
        self.tools_menu.addAction(settings_action)
        self.tools_menu.addSeparator()
        utility_actions = [
            ('List Chats', self.UTILITY_CONFIGS['list_chats']),
            ('Export Members', self.UTILITY_CONFIGS['export_members']),
            'separator',
            ('Backup Data', self.UTILITY_CONFIGS['backup_data']),
            ('Recover Data', self.UTILITY_CONFIGS['recover_data']),
            ('Migrate Data', self.UTILITY_CONFIGS['migrate_data']),
        ]
        for item in utility_actions:
            if item == 'separator':
                self.tools_menu.addSeparator()
                continue
            label, config = item
            action = QAction(label, self)
            action.triggered.connect(partial(self._run_utility_command, config))
            self.tools_menu.addAction(action)
        help_menu = menu_bar.addMenu("&Help")
        doc_action = QAction("Documentation", self)
        doc_action.triggered.connect(self.show_documentation)
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(doc_action)
        help_menu.addAction(about_action)

    def show_documentation(self):
        QDesktopServices.openUrl(QUrl("https://docs.iyear.me/tdl/"))

    def show_about_dialog(self):
        QMessageBox.about(self, "About tdl GUI", "<h3>tdl GUI</h3><p>A graphical user interface for the tdl command-line tool.</p><p>Built with PyQt6.</p>")

    def open_settings_dialog(self):
        dialog = SettingsDialog(self.tdl_path, self.settings, self)
        dialog.desktop_login_requested.connect(self.handle_desktop_login)
        if dialog.exec():
            self.settings.update(dialog.settings)
            self.log_message.emit(f"Settings updated. Active account is now '{self.settings['namespace']}'.")
        else:
            self.log_message.emit("Settings dialog cancelled.")

    def handle_desktop_login(self, path, passcode):
        self.log_message.emit("Desktop login requested. See log for details.")
        if self.worker is not None and self.worker.isRunning():
            self.log_message.emit("A task is already running. Please wait.")
            return

        self.log_message.emit(f"Attempting to log in from desktop client at: {path}")
        command = [self.tdl_path, 'login', '-d', path]
        if passcode:
            command.extend(['-p', passcode])

        timeout = self.settings.get('command_timeout', 300)
        self.worker = Worker(command, self.tdl_path, timeout=timeout)
        self.worker.logMessage.connect(self.append_log)
        self.worker.taskFinished.connect(self._task_finished)
        self.worker.taskFailedWithLog.connect(self._task_failed)
        self.worker.start()
        self.set_task_running_ui_state(is_running=True)

    def select_destination_directory(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Destination Directory", QDir.homePath())
        if directory:
            self.dest_path_input.setText(directory)

    def load_source_from_file(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Load Source File", QDir.homePath(), "Text Files (*.txt)")
        if filepath:
            try:
                with open(filepath, 'r') as f:
                    self.source_input.setPlainText(f.read())
                self.log_message.emit(f"Loaded sources from {filepath}")
            except Exception as e:
                self.log_message.emit(f"Error reading file {filepath}: {e}")

    def handle_download_button(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            return
        source_text = self.source_input.toPlainText().strip()
        if not source_text:
            self.log_message.emit("Error: Source input cannot be empty.")
            return

        command = [self.tdl_path, 'download']
        lines = source_text.splitlines()
        for line in lines:
            clean_line = line.strip()
            if not clean_line: continue
            if clean_line.endswith('.json') and os.path.exists(clean_line):
                command.extend(['-f', clean_line])
            else:
                command.extend(['-u', clean_line])

        dest_path = self.dest_path_input.text().strip() or QDir.home().filePath("Downloads")
        os.makedirs(dest_path, exist_ok=True)
        command.extend(['-d', dest_path])
        if self.advanced_group.isChecked():
            command.extend(['-l', str(self.concurrent_tasks_spinbox.value())])
            command.extend(['-t', str(self.threads_per_task_spinbox.value())])
            if self.include_ext_input.text(): command.extend(['-i', self.include_ext_input.text()])
            if self.exclude_ext_input.text(): command.extend(['-e', self.exclude_ext_input.text()])
            if self.desc_checkbox.isChecked(): command.append('--desc')
            if self.skip_same_checkbox.isChecked(): command.append('--skip-same')
            if self.rewrite_ext_checkbox.isChecked(): command.append('--rewrite-ext')
            if self.group_checkbox.isChecked(): command.append('--group')
            if self.takeout_checkbox.isChecked(): command.append('--takeout')
            command.extend(['--pool', str(self.pool_spinbox.value())])
            template_text = ""
            current_template = self.template_combo.currentText()
            if current_template == "Custom...":
                template_text = self.template_input.text()
            elif ':' in current_template:
                template_text = current_template.split(':', 1)[1].strip()
            if template_text:
                command.extend(['--template', template_text])
        if self.settings.get('debug_mode', False): command.append('--debug')
        delay_value = self.delay_spinbox.value()
        if delay_value > 0:
            delay_unit = self.delay_unit_combo.currentText()
            command.extend(['--delay', f"{delay_value}{delay_unit}"])
        command.extend(self._get_proxy_args())
        command.extend(self._get_storage_args())
        command.extend(self._get_namespace_args())
        command.extend(self._get_ntp_args())
        command.extend(self._get_reconnect_timeout_args())
        self.log_message.emit(f"Starting download with command: {' '.join(command)}")
        timeout = self.settings.get('command_timeout', 300)
        self.worker = Worker(command, self.tdl_path, timeout=timeout)
        self.worker.logMessage.connect(self.append_log)
        self.worker.taskFinished.connect(self._task_finished)
        self.worker.taskFailedWithLog.connect(self._task_failed)
        self.worker.downloadStarted.connect(self.add_download_progress_widget)
        self.worker.downloadProgress.connect(self.update_download_progress)
        self.worker.downloadFinished.connect(self.remove_download_progress_widget)
        self.worker.overallProgress.connect(self.update_overall_progress)
        self.worker.statsUpdated.connect(self.update_system_stats)
        self.has_started_download = True
        self.worker.start()
        self.set_task_running_ui_state(is_running=True)

    def handle_resume_button(self):
        if self.worker is not None and self.worker.isRunning():
            self.log_message.emit("A task is already running. Please wait.")
            return

        self.log_message.emit("Attempting to resume the last download...")
        command = [self.tdl_path, 'download', '--continue']

        if self.settings.get('debug_mode', False): command.append('--debug')
        command.extend(self._get_proxy_args())
        command.extend(self._get_storage_args())
        command.extend(self._get_namespace_args())
        command.extend(self._get_ntp_args())
        command.extend(self._get_reconnect_timeout_args())

        self.log_message.emit(f"Starting resume with command: {' '.join(command)}")
        timeout = self.settings.get('command_timeout', 300)
        self.worker = Worker(command, self.tdl_path, timeout=timeout)
        self.worker.logMessage.connect(self.append_log)
        self.worker.taskFinished.connect(self._task_finished)
        self.worker.taskFailedWithLog.connect(self._task_failed)
        self.worker.downloadStarted.connect(self.add_download_progress_widget)
        self.worker.downloadProgress.connect(self.update_download_progress)
        self.worker.downloadFinished.connect(self.remove_download_progress_widget)
        self.worker.overallProgress.connect(self.update_overall_progress)
        self.worker.statsUpdated.connect(self.update_system_stats)
        self.has_started_download = True
        self.worker.start()
        self.set_task_running_ui_state(is_running=True)

    def add_download_progress_widget(self, file_id):
        if file_id not in self.progress_widgets:
            progress_widget = DownloadProgressWidget(file_id)
            self.progress_layout.insertWidget(0, progress_widget)
            self.progress_widgets[file_id] = progress_widget

    def update_download_progress(self, progress_data):
        file_id = progress_data['id']
        if file_id in self.progress_widgets:
            self.progress_widgets[file_id].update_progress(progress_data)
        else:
            self.add_download_progress_widget(file_id)
            self.progress_widgets[file_id].update_progress(progress_data)

    def remove_download_progress_widget(self, file_id):
        if file_id in self.progress_widgets:
            widget = self.progress_widgets.pop(file_id)
            widget.deleteLater()

    def update_overall_progress(self, data):
        self.status_progress.setValue(data['percent'])
        self.status_label.setText(f"Overall Speed: {data['speed']}")

    def update_system_stats(self, data):
        self.cpu_label.setText(f"CPU: {data['cpu']}")
        self.mem_label.setText(f"Mem: {data['mem']}")

    def _task_finished(self, exit_code):
        if exit_code == 0:
            self.log_message.emit("All tasks completed successfully.")
            self.status_label.setText("Finished")
        else:
            self.log_message.emit(f"A task failed or was terminated (Exit Code: {exit_code}).")
            self.status_label.setText("Error / Stopped")
        self.set_task_running_ui_state(is_running=False)
        self.worker = None
        for i in reversed(range(self.progress_layout.count())):
            item = self.progress_layout.itemAt(i)
            widget = item.widget()
            if widget and not isinstance(widget, QLabel):
                widget.setParent(None)
                widget.deleteLater()
        self.progress_widgets.clear()
        self.progress_layout.addStretch()

    def on_include_text_changed(self, text):
        self.exclude_ext_input.setEnabled(not bool(text))

    def on_exclude_text_changed(self, text):
        self.include_ext_input.setEnabled(not bool(text))

    def _run_utility_command(self, config):
        if self.worker is not None and self.worker.isRunning():
            self.log_message.emit("A task is already running. Please wait for it to complete.")
            return
        dialog = UtilityDialog(config['title'], config['fields'], self)
        if not dialog.exec():
            self.log_message.emit(f"'{config['title']}' was cancelled.")
            return
        values = dialog.get_values()
        command = [self.tdl_path] + config['base_cmd']
        for field in config['fields']:
            value = values.get(field['name'])
            if value:
                command.extend([field['arg'], value])
        if self.settings.get('debug_mode', False): command.append('--debug')
        command.extend(self._get_proxy_args())
        command.extend(self._get_storage_args())
        command.extend(self._get_namespace_args())
        command.extend(self._get_ntp_args())
        command.extend(self._get_reconnect_timeout_args())
        self.log_message.emit(f"Running utility: {' '.join(command)}")
        timeout = self.settings.get('command_timeout', 300)
        self.worker = Worker(command, self.tdl_path, timeout=timeout)
        self.worker.logMessage.connect(self.append_log)
        self.worker.taskFinished.connect(self._task_finished)
        self.worker.taskFailedWithLog.connect(self._task_failed)
        self.worker.start()
        self.set_task_running_ui_state(is_running=True)

    def handle_export_button(self):
        if self.worker is not None and self.worker.isRunning():
            self.log_message.emit("A task is already running. Please wait.")
            return
        source = self.export_source_input.text().strip()
        if not source:
            QMessageBox.warning(self, "Input Error", "Export source cannot be empty.")
            return
        output_path, _ = QFileDialog.getSaveFileName(self, "Save Exported JSON", QDir.homePath(), "JSON Files (*.json)")
        if not output_path:
            self.log_message.emit("Export cancelled by user.")
            return
        command = [self.tdl_path, 'chat', 'export', '-c', source, '-o', output_path]
        export_type_index = self.export_type_combo.currentIndex()
        if export_type_index == 1:
            from_dt = QDateTime(self.from_date_edit.date())
            to_dt = QDateTime(self.to_date_edit.date()).addDays(1).addSecs(-1)
            command.extend(['-T', 'time', '-i', f"{int(from_dt.toSecsSinceEpoch())},{int(to_dt.toSecsSinceEpoch())}"])
        elif export_type_index == 2:
            from_id = self.from_id_input.text().strip() or "0"
            to_id = self.to_id_input.text().strip() or "0"
            command.extend(['-T', 'id', '-i', f"{from_id},{to_id}"])
        elif export_type_index == 3:
            n_messages = self.last_n_spinbox.value()
            command.extend(['-T', 'last', '-i', str(n_messages)])
        if self.export_with_content_checkbox.isChecked(): command.append('--with-content')
        if self.export_all_types_checkbox.isChecked(): command.append('--all')

        if self.export_advanced_group.isChecked():
            if self.export_filter_input.text():
                command.extend(['--filter', self.export_filter_input.text()])
            if self.export_reply_input.text():
                command.extend(['--reply', self.export_reply_input.text()])
            if self.export_topic_input.text():
                command.extend(['--topic', self.export_topic_input.text()])
        if self.settings.get('debug_mode', False): command.append('--debug')
        command.extend(self._get_proxy_args())
        command.extend(self._get_storage_args())
        command.extend(self._get_namespace_args())
        command.extend(self._get_ntp_args())
        command.extend(self._get_reconnect_timeout_args())
        self.log_message.emit(f"Starting export with command: {' '.join(command)}")
        timeout = self.settings.get('command_timeout', 300)
        self.worker = Worker(command, self.tdl_path, timeout=timeout)
        self.worker.logMessage.connect(self.append_log)
        self.worker.taskFinished.connect(self._task_finished)
        self.worker.taskFailedWithLog.connect(self._task_failed)
        self.worker.start()
        self.set_task_running_ui_state(is_running=True)

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.log_message.emit("A task is running. Stopping it before exit...")
            self.worker.stop()
            self.worker.wait()
        event.accept()

    def _get_proxy_args(self):
        if self.settings.get('auto_proxy', True):
            proxies = urllib.request.getproxies()
            proxy = proxies.get('https', proxies.get('http'))
            if proxy:
                self.log_message.emit(f"Using system proxy: {proxy}")
                return ['--proxy', proxy]
        elif self.settings.get('manual_proxy', ''):
            proxy = self.settings['manual_proxy']
            self.log_message.emit(f"Using manual proxy: {proxy}")
            return ['--proxy', proxy]
        return []

    def _get_storage_args(self):
        driver = self.settings.get('storage_driver', 'bolt')
        path = self.settings.get('storage_path', '').strip()
        if not path:
            return []
        storage_str = f"type={driver},path={path}"
        return ['--storage', storage_str]

    def _get_namespace_args(self):
        namespace = self.settings.get('namespace', 'default')
        if namespace and namespace != 'default':
            return ['--ns', namespace]
        return []

    def _get_ntp_args(self):
        ntp_server = self.settings.get('ntp_server', '').strip()
        if ntp_server:
            return ['--ntp', ntp_server]
        return []

    def _get_reconnect_timeout_args(self):
        reconnect_timeout = self.settings.get('reconnect_timeout', '5m').strip()
        if reconnect_timeout and reconnect_timeout != '5m' and reconnect_timeout != '0s':
            return ['--reconnect-timeout', reconnect_timeout]
        return []

    def _task_failed(self, exit_code, log_output):
        if "not authorized" in log_output:
            QMessageBox.warning(
                self,
                "Authentication Required",
                "The operation failed because you are not logged in.\n\n"
                "Please go to Tools > Settings and use the 'Login to New Account' button to log in."
            )