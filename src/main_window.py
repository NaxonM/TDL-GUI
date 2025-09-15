# main_window.py

import sys
import os
import glob
import json
import tempfile
import urllib.request
import subprocess
import re
from PyQt6.QtCore import pyqtSignal, QDir, QUrl, QDate, QDateTime, Qt, QSize, QStandardPaths
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QFormLayout, QMenu, QPlainTextEdit, QGroupBox, QPushButton,
    QLineEdit, QToolButton, QSpinBox, QCheckBox, QProgressBar,
    QFileDialog, QMessageBox, QDateEdit, QLabel, QComboBox, QScrollArea, QStackedWidget,
    QAbstractSpinBox, QStyle, QTableWidget, QHeaderView, QTableWidgetItem
)
from PyQt6.QtGui import QAction, QDesktopServices, QColor, QTextCursor, QTextCharFormat, QPalette

from functools import partial
from worker import Worker
from settings_dialog import SettingsDialog
from utility_dialog import UtilityDialog
from progress_widget import DownloadProgressWidget
from settings_manager import SettingsManager
from logger import Logger
from advanced_settings_dialog import AdvancedSettingsDialog
from advanced_export_dialog import AdvancedExportDialog

class MainWindow(QMainWindow):
    # Configuration for utility commands
    UTILITY_CONFIGS = {
        'export_members_by_id': {
            'title': 'Export Members by ID',
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

    CHAT_NAME_COLORS = [
        QColor("#1ABC9C"), QColor("#2ECC71"), QColor("#3498DB"), QColor("#9B59B6"),
        QColor("#34495E"), QColor("#F1C40F"), QColor("#E67E22"), QColor("#E74C3C"),
        QColor("#95A5A6"), QColor("#16A085"), QColor("#27AE60"), QColor("#2980B9"),
        QColor("#8E44AD"), QColor("#2C3E50"), QColor("#F39C12"), QColor("#D35400"),
        QColor("#C0392B"), QColor("#7F8C8D")
    ]

    def __init__(self, app, tdl_path, settings_manager, logger, theme='light'):
        super().__init__()
        self.app = app
        self.tdl_path = tdl_path
        self.settings_manager = settings_manager
        self.logger = logger
        self.theme = theme
        self.worker = None
        self.tdl_version = self._get_tdl_version()
        self.progress_widgets = {}
        self.download_controls = []
        self.export_controls = []
        self.global_controls = []
        self.has_started_download = False
        self.active_task_tab_index = -1
        self.original_tab_text = ""
        self.advanced_settings = {}
        self.advanced_export_settings = {}

        if self.theme == 'dark':
            self.error_color = QColor("#FF5555")
            self.warn_color = QColor("#FFC107")
        elif self.theme == 'nord':
            self.error_color = QColor("#BF616A")  # nord11
            self.warn_color = QColor("#EBCB8B")   # nord13
        elif self.theme == 'solarized-dark':
            self.error_color = QColor("#dc322f")  # red
            self.warn_color = QColor("#b58900")   # yellow
        elif self.theme == 'solarized-light':
            self.error_color = QColor("#dc322f")  # red
            self.warn_color = QColor("#b58900")   # yellow
        else:  # light theme
            self.error_color = QColor("#D32F2F")
            self.warn_color = QColor("#F57F17")


        self._init_ui()
        self._setup_connections()
        self.logger.info("Application initialized.")
        self.logger.info(f"Settings loaded from {self.settings_manager.settings_path}")


    def _init_ui(self):
        """Initializes the main UI components."""
        self._init_window()
        self._create_central_widget()
        self._create_menu_bar()
        self._create_status_bar()
        self._update_namespace_display()
        self._collect_global_controls()

    def _init_window(self):
        """Initializes main window properties."""
        self.setWindowTitle("tdl GUI")
        self.resize(850, 700)  # Set a default size, but allow resizing

    def _create_central_widget(self):
        """Creates and sets up the central tab widget."""
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Create and add tabs
        self.download_tab = self._create_download_tab()
        self.export_tab = self._create_export_tab()
        self.chats_tab = self._create_chats_tab()
        self.log_tab = self._create_log_tab()

        self.tabs.addTab(self.download_tab, "Download")
        self.tabs.addTab(self.export_tab, "Export")
        self.tabs.addTab(self.chats_tab, "Chats")
        self.tabs.addTab(self.log_tab, "Log")

    def _collect_global_controls(self):
        """Collects all controls that should be disabled when a task is running."""
        self.global_controls.extend([
            self.refresh_chats_button,
            self.chats_table,
            self.tools_menu,
            self.start_download_button,
            self.resume_download_button,
            self.run_export_button,
        ])

    def _setup_connections(self):
        """Connects all signals to slots."""
        self.logger.log_signal.connect(self.append_log)
        # Download Tab Connections
        self.start_download_button.clicked.connect(self.handle_download_button)
        self.resume_download_button.clicked.connect(self.handle_resume_button)
        self.load_from_file_button.clicked.connect(self.load_source_from_file)
        self.browse_dest_button.clicked.connect(self.select_destination_directory)
        self.clear_source_button.clicked.connect(self.source_input.clear)
        # Export Tab Connections
        self.run_export_button.clicked.connect(self.handle_export_button)
        self.export_type_combo.currentIndexChanged.connect(self.filter_stack.setCurrentIndex)

    def _create_download_tab(self):
        """Creates the main 'Download' tab widget."""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setSpacing(15)

        source_group = self._create_download_source_group()
        dest_group = self._create_download_destination_group()
        progress_group = self._create_download_progress_group()

        self.start_download_button = QPushButton("Start Download")
        self.start_download_button.setObjectName("ActionButton")
        self.resume_download_button = QPushButton("Resume Last Download")
        self.resume_download_button.setObjectName("ActionButton")
        self.resume_download_button.setEnabled(False)

        self.advanced_settings_button = QPushButton("Advanced Options...")
        self.advanced_settings_button.clicked.connect(self.open_advanced_settings_dialog)

        action_button_layout = QHBoxLayout()
        action_button_layout.addStretch()
        action_button_layout.addWidget(self.advanced_settings_button)
        action_button_layout.addWidget(self.start_download_button)
        action_button_layout.addWidget(self.resume_download_button)
        action_button_layout.addStretch()

        main_layout.addWidget(source_group)
        main_layout.addWidget(dest_group)
        main_layout.addLayout(action_button_layout)
        main_layout.addWidget(progress_group)

        self.download_controls.extend([
            self.source_input, self.load_from_file_button, self.clear_source_button,
            self.dest_path_input, self.browse_dest_button, self.advanced_settings_button
        ])
        return widget

    def _create_download_source_group(self):
        group = QGroupBox("Source Input")
        layout = QVBoxLayout(group)
        self.source_input = QPlainTextEdit()
        self.source_input.setPlaceholderText("Paste message links or file paths here, one per line.")
        self.source_input.setToolTip("Enter one Telegram message link (e.g., https://t.me/channel/123) or one local .json file path per line.")

        button_layout = QHBoxLayout()
        self.load_from_file_button = QPushButton("Load from File...")
        self.load_from_file_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.load_from_file_button.setToolTip("Load a list of sources from a text file.")

        self.clear_source_button = QPushButton("Clear")
        self.clear_source_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))
        self.clear_source_button.setToolTip("Clear all text from the source input box.")

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

    def open_advanced_settings_dialog(self):
        dialog = AdvancedSettingsDialog(self)
        if dialog.exec():
            self.advanced_settings = dialog.get_settings()
            self.logger.info("Advanced settings saved.")
        else:
            self.logger.info("Advanced settings dialog cancelled.")


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
        main_layout.setSpacing(15)

        source_group = self._create_export_source_group()
        options_group = self._create_export_options_group()
        content_group = self._create_export_content_group()
        
        self.run_export_button = QPushButton("Export to JSON...")
        self.run_export_button.setObjectName("ActionButton")

        self.advanced_export_button = QPushButton("Advanced Options...")
        self.advanced_export_button.clicked.connect(self.open_advanced_export_dialog)

        action_button_layout = QHBoxLayout()
        action_button_layout.addStretch()
        action_button_layout.addWidget(self.advanced_export_button)
        action_button_layout.addWidget(self.run_export_button)
        action_button_layout.addStretch()

        main_layout.addWidget(source_group)
        main_layout.addWidget(options_group)
        main_layout.addWidget(content_group)
        main_layout.addLayout(action_button_layout)
        main_layout.addStretch()

        self.export_controls.extend([
            self.export_source_input, self.export_type_combo, self.filter_stack,
            self.export_with_content_checkbox, self.export_all_types_checkbox,
            self.advanced_export_button
        ])
        return widget
        
    def _create_export_source_group(self):
        group = QGroupBox("Export Source")
        layout = QFormLayout(group)
        self.export_source_input = QLineEdit()
        self.export_source_input.setPlaceholderText("Enter Channel/Chat ID or Username")
        self.export_source_input.setToolTip("Enter the source to export from, e.g., 'telegram' or '-100123456789'.")
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
    
    def open_advanced_export_dialog(self):
        dialog = AdvancedExportDialog(self)
        if dialog.exec():
            self.advanced_export_settings = dialog.get_settings()
            self.logger.info("Advanced export settings saved.")
        else:
            self.logger.info("Advanced export settings dialog cancelled.")

    def _create_log_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setObjectName("LogOutput")

        button_layout = QHBoxLayout()
        open_log_button = QPushButton("Open Log File Location")
        open_log_button.clicked.connect(self.open_log_directory)
        button_layout.addStretch()
        button_layout.addWidget(open_log_button)

        layout.addWidget(self.log_output)
        layout.addLayout(button_layout)
        return widget

    def open_log_directory(self):
        log_dir = self.settings_manager.config_dir
        QDesktopServices.openUrl(QUrl.fromLocalFile(log_dir))

    def _create_chats_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        button_layout = QHBoxLayout()
        self.refresh_chats_button = QPushButton("Refresh Chat List")
        self.refresh_chats_button.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.refresh_chats_button.setToolTip("Fetch the latest list of your chats from Telegram.")
        button_layout.addWidget(self.refresh_chats_button)
        button_layout.addStretch()

        self.chats_table = QTableWidget()
        self.chats_table.setColumnCount(4)
        self.chats_table.setHorizontalHeaderLabels(["Name", "Type", "ID", "Username"])
        self.chats_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.chats_table.verticalHeader().setVisible(False)
        self.chats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.chats_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.chats_table.setSortingEnabled(True)
        self.chats_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.chats_table.customContextMenuRequested.connect(self._show_chat_context_menu)


        layout.addLayout(button_layout)
        layout.addWidget(self.chats_table)

        self.refresh_chats_button.clicked.connect(self.handle_refresh_chats)

        return widget

    def handle_refresh_chats(self):
        self.run_list_chats()

    def _create_status_bar(self):
        self.status_label = QLabel("Ready")
        self.status_progress = QProgressBar()
        self.status_progress.setRange(0, 100)
        self.status_progress.setFixedSize(150, 16)
        self.status_progress.setTextVisible(False)
        self.status_progress.hide()

        self.cpu_label = QLabel("CPU: N/A")
        self.mem_label = QLabel("Mem: N/A")
        self.namespace_label = QLabel("NS: default")
        self.cpu_label.setObjectName("StatsLabel")
        self.mem_label.setObjectName("StatsLabel")
        self.namespace_label.setObjectName("StatsLabel")

        self.statusBar().addPermanentWidget(self.namespace_label)
        self.statusBar().addPermanentWidget(self.status_label)
        self.statusBar().addPermanentWidget(self.status_progress)
        self.statusBar().addPermanentWidget(self.cpu_label)
        self.statusBar().addPermanentWidget(self.mem_label)
        self.statusBar().showMessage("Ready")

    def _update_namespace_display(self):
        """Updates the namespace label in the status bar."""
        namespace = self.settings_manager.get('namespace', 'default')
        self.namespace_label.setText(f"NS: {namespace}")


    def set_task_running_ui_state(self, is_running, tab_index=-1):
        """Enables or disables UI controls based on the state of a running task."""
        all_controls = self.download_controls + self.export_controls + self.global_controls
        for widget in all_controls:
            widget.setEnabled(not is_running)

        # Explicitly handle the main action buttons that change text or have special logic
        self.start_download_button.setText("Stop Download" if is_running else "Start Download")

        if is_running:
            self.resume_download_button.setEnabled(False)
            self.start_download_button.setProperty("class", "stop-button")
            self.status_progress.show()
            self.status_label.setText("Starting...")
            self.cpu_label.setText("CPU: ...")
            self.mem_label.setText("Mem: ...")

            # Update tab text to show activity
            if tab_index != -1:
                self.active_task_tab_index = tab_index
                self.original_tab_text = self.tabs.tabText(tab_index)
                self.tabs.setTabText(tab_index, f"{self.original_tab_text} ●")

        else:
            if self.has_started_download:
                self.resume_download_button.setEnabled(True)
            self.start_download_button.setProperty("class", "")
            self.status_progress.hide()
            self.cpu_label.setText("CPU: N/A")
            self.mem_label.setText("Mem: N/A")

            # Restore original tab text
            if self.active_task_tab_index != -1:
                self.tabs.setTabText(self.active_task_tab_index, self.original_tab_text)
                self.active_task_tab_index = -1
                self.original_tab_text = ""

        self.start_download_button.style().unpolish(self.start_download_button)
        self.start_download_button.style().polish(self.start_download_button)
        
    def run_list_chats(self):
        if self.worker is not None and self.worker.isRunning():
            self.logger.warning("A task is already running. Please wait for it to complete.")
            return

        self.logger.info("Fetching chat list...")
        command = [self.tdl_path, 'chat', 'ls', '-o', 'json']

        # Add global flags
        if self.settings_manager.get('debug_mode', False): command.append('--debug')
        command.extend(self._get_proxy_args())
        command.extend(self._get_storage_args())
        command.extend(self._get_namespace_args())

        timeout = self.settings_manager.get('command_timeout', 300)
        self.worker = Worker(command, self.logger, timeout=timeout)
        self.worker.taskFinished.connect(self._task_finished)
        self.worker.taskFailedWithLog.connect(self._task_failed)
        self.worker.taskData.connect(self._populate_chats_table)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()
        self.set_task_running_ui_state(is_running=True, tab_index=2) # 2 is the Chats tab

    def _show_chat_context_menu(self, position):
        selected_items = self.chats_table.selectedItems()
        if not selected_items:
            return

        # Get the chat ID from the selected row (column 2)
        selected_row = selected_items[0].row()
        chat_id_item = self.chats_table.item(selected_row, 2)
        if not chat_id_item:
            return
        chat_id = chat_id_item.text()

        menu = QMenu()
        copy_id_action = menu.addAction("Copy Chat ID")
        export_messages_action = menu.addAction("Export Messages...")
        export_members_action = menu.addAction("Export Members...")

        action = menu.exec(self.chats_table.viewport().mapToGlobal(position))

        if action == copy_id_action:
            self._handle_copy_chat_id(chat_id)
        elif action == export_messages_action:
            self._handle_export_chat_messages(chat_id)
        elif action == export_members_action:
            self._handle_export_chat_members(chat_id)

    def _handle_copy_chat_id(self, chat_id):
        clipboard = QApplication.clipboard()
        clipboard.setText(chat_id)
        self.logger.info(f"Copied Chat ID to clipboard: {chat_id}")

    def _handle_export_chat_messages(self, chat_id):
        self.tabs.setCurrentWidget(self.export_tab)
        self.export_source_input.setText(chat_id)
        self.logger.info(f"Switched to Export tab for Chat ID: {chat_id}")

    def _populate_chats_table(self, json_data):
        try:
            chats = json.loads(json_data)
            self.chats_table.setSortingEnabled(False) # Disable sorting during population
            self.chats_table.setRowCount(0) # Clear existing rows

            for chat in chats:
                row_position = self.chats_table.rowCount()
                self.chats_table.insertRow(row_position)

                name = chat.get('visible_name', '')
                type = chat.get('type', '')
                id_str = str(chat.get('id', ''))
                username = chat.get('username', '')

                # Color the chat name
                name_item = QTableWidgetItem(name)
                if id_str:
                    color_index = hash(id_str) % len(self.CHAT_NAME_COLORS)
                    name_item.setForeground(self.CHAT_NAME_COLORS[color_index])

                self.chats_table.setItem(row_position, 0, name_item)
                self.chats_table.setItem(row_position, 1, QTableWidgetItem(type))
                self.chats_table.setItem(row_position, 2, QTableWidgetItem(id_str))
                self.chats_table.setItem(row_position, 3, QTableWidgetItem(username))

            self.chats_table.setSortingEnabled(True)
            self.logger.info(f"Successfully populated chats table with {len(chats)} chats.")

        except json.JSONDecodeError:
            self.logger.error("Failed to parse JSON data from 'tdl chat ls' command.")
            QMessageBox.critical(self, "Error", "Could not parse the chat list from tdl. See logs for details.")


    def append_log(self, message, level):
        cursor = self.log_output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        char_format = QTextCharFormat()
        default_color = self.palette().color(QPalette.ColorRole.Text)
        char_format.setForeground(default_color)

        if level == "WARNING":
            char_format.setForeground(self.warn_color)
        elif level in ["ERROR", "CRITICAL"]:
            char_format.setForeground(self.error_color)

        cursor.setCharFormat(char_format)
        # We only insert the message, as the logger already formats it with timestamp/level
        cursor.insertText(message + '\n')

        # Reset format for next entries
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.setCharFormat(QTextCharFormat())
        self.log_output.setTextCursor(cursor)

        # Show important messages in the status bar
        if level in ["INFO", "WARNING", "ERROR", "CRITICAL"]:
            # Strip the timestamp and level for a cleaner status bar message
            status_message = ' - '.join(message.split(' - ')[2:])
            self.statusBar().showMessage(status_message, 5000)

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
            ('Export Members by ID...', self.UTILITY_CONFIGS['export_members_by_id']),
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
        update_action = QAction("Check for Updates...", self)
        update_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(doc_action)
        help_menu.addAction(update_action)
        help_menu.addAction(about_action)

    def show_documentation(self):
        QDesktopServices.openUrl(QUrl("https://docs.iyear.me/tdl/"))

    def _get_tdl_version(self):
        try:
            result = subprocess.run([self.tdl_path, 'version'], capture_output=True, text=True, check=True)
            # Example output: "tdl version 0.7.3"
            version_line = result.stdout.strip()
            return version_line
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            self.logger.error(f"Could not get tdl version: {e}")
            return "Unknown"

    def show_about_dialog(self):
        about_text = f"""
            <h3>tdl GUI</h3>
            <p>A graphical user interface for the tdl command-line tool.</p>
            <p><b>tdl version:</b> {self.tdl_version}</p>
            <p>Built with PyQt6.</p>
        """
        QMessageBox.about(self, "About tdl GUI", about_text)

    def open_settings_dialog(self):
        dialog = SettingsDialog(self.tdl_path, self.settings_manager, self)
        dialog.desktop_login_requested.connect(self.handle_desktop_login)
        if dialog.exec():
            # The dialog now directly modifies the settings manager's state
            self.settings_manager.save_settings()
            active_ns = self.settings_manager.get('namespace')
            self.logger.info(f"Settings saved. Active account is now '{active_ns}'.")
            self._update_namespace_display()
        else:
            self.logger.info("Settings dialog cancelled.")

    def check_for_updates(self):
        self.logger.info("Checking for tdl updates...")
        try:
            # Get local version
            local_version_str = self.tdl_version
            match = re.search(r'(\d+\.\d+\.\d+)', local_version_str)
            if not match:
                QMessageBox.warning(self, "Update Check Failed", f"Could not parse local version: {local_version_str}")
                return
            local_version = match.group(1)

            # Get latest version from GitHub
            url = "https://api.github.com/repos/iyear/tdl/releases/latest"
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                latest_version = data['tag_name'].lstrip('v')
                release_notes = data['body']
                download_url = ""
                for asset in data['assets']:
                    if 'linux' in asset['name'] and 'amd64' in asset['name']:
                         download_url = asset['browser_download_url']
                         break

            self.logger.info(f"Local version: {local_version}, Latest version: {latest_version}")

            if local_version < latest_version:
                reply = QMessageBox.information(
                    self, "Update Available",
                    f"A new version of tdl is available: <b>{latest_version}</b><br><br>"
                    f"<b>Release Notes:</b><br>{release_notes}<br><br>"
                    "Would you like to download and install it now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.logger.info(f"User agreed to update to version {latest_version}")
                    # I will implement the download and update logic later
                    QMessageBox.information(self, "Not Implemented", "The automatic update functionality is not yet implemented.")

            else:
                QMessageBox.information(self, "No Updates", "You are using the latest version of tdl.")

        except Exception as e:
            self.logger.error(f"Failed to check for updates: {e}")
            QMessageBox.warning(self, "Update Check Failed", f"Could not check for updates. See logs for details.")

    def handle_desktop_login(self, path, passcode):
        self.logger.info("Desktop login requested. See log for details.")
        if self.worker is not None and self.worker.isRunning():
            self.logger.warning("A task is already running. Please wait.")
            return

        self.logger.info(f"Attempting to log in from desktop client at: {path}")
        command = [self.tdl_path, 'login', '-d', path]
        if passcode:
            command.extend(['-p', passcode])

        timeout = self.settings_manager.get('command_timeout', 300)
        self.worker = Worker(command, self.logger, timeout=timeout)
        self.worker.taskFinished.connect(self._task_finished)
        self.worker.taskFailedWithLog.connect(self._task_failed)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()
        self.set_task_running_ui_state(is_running=True, tab_index=-1)

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
                self.logger.info(f"Loaded sources from {filepath}")
            except Exception as e:
                self.logger.error(f"Error reading file {filepath}: {e}")

    def handle_download_button(self):
        if self.worker is not None and self.worker.isRunning():
            self.worker.stop()
            return
        source_text = self.source_input.toPlainText().strip()
        if not source_text:
            self.logger.error("Source input cannot be empty.")
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

        if self.advanced_settings:
            command.extend(['-l', str(self.advanced_settings['concurrent_tasks'])])
            command.extend(['-t', str(self.advanced_settings['threads_per_task'])])
            if self.advanced_settings['include_exts']:
                command.extend(['-i', self.advanced_settings['include_exts']])
            if self.advanced_settings['exclude_exts']:
                command.extend(['-e', self.advanced_settings['exclude_exts']])
            if self.advanced_settings['desc_order']:
                command.append('--desc')
            if self.advanced_settings['skip_same']:
                command.append('--skip-same')
            if self.advanced_settings['rewrite_ext']:
                command.append('--rewrite-ext')
            if self.advanced_settings['group_albums']:
                command.append('--group')
            if self.advanced_settings['use_takeout']:
                command.append('--takeout')
            command.extend(['--pool', str(self.advanced_settings['pool_size'])])
            if self.advanced_settings['template']:
                command.extend(['--template', self.advanced_settings['template']])
            delay_value = self.advanced_settings['delay']
            if delay_value > 0:
                delay_unit = self.advanced_settings['delay_unit']
                command.extend(['--delay', f"{delay_value}{delay_unit}"])

        if self.settings_manager.get('debug_mode', False): command.append('--debug')
        command.extend(self._get_proxy_args())
        command.extend(self._get_storage_args())
        command.extend(self._get_namespace_args())
        command.extend(self._get_ntp_args())
        command.extend(self._get_reconnect_timeout_args())
        self.logger.info(f"Starting download with command: {' '.join(command)}")
        timeout = self.settings_manager.get('command_timeout', 300)
        self.worker = Worker(command, self.logger, timeout=timeout)
        self.worker.taskFinished.connect(self._task_finished)
        self.worker.taskFailedWithLog.connect(self._task_failed)
        self.worker.downloadStarted.connect(self.add_download_progress_widget)
        self.worker.downloadProgress.connect(self.update_download_progress)
        self.worker.downloadFinished.connect(self.remove_download_progress_widget)
        self.worker.overallProgress.connect(self.update_overall_progress)
        self.worker.statsUpdated.connect(self.update_system_stats)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.has_started_download = True
        self.worker.start()
        self.set_task_running_ui_state(is_running=True, tab_index=0)

    def handle_resume_button(self):
        if self.worker is not None and self.worker.isRunning():
            self.logger.warning("A task is already running. Please wait.")
            return

        self.logger.info("Attempting to resume the last download...")
        command = [self.tdl_path, 'download', '--continue']

        if self.settings_manager.get('debug_mode', False): command.append('--debug')
        command.extend(self._get_proxy_args())
        command.extend(self._get_storage_args())
        command.extend(self._get_namespace_args())
        command.extend(self._get_ntp_args())
        command.extend(self._get_reconnect_timeout_args())

        self.logger.info(f"Starting resume with command: {' '.join(command)}")
        timeout = self.settings_manager.get('command_timeout', 300)
        self.worker = Worker(command, self.logger, timeout=timeout)
        self.worker.taskFinished.connect(self._task_finished)
        self.worker.taskFailedWithLog.connect(self._task_failed)
        self.worker.downloadStarted.connect(self.add_download_progress_widget)
        self.worker.downloadProgress.connect(self.update_download_progress)
        self.worker.downloadFinished.connect(self.remove_download_progress_widget)
        self.worker.overallProgress.connect(self.update_overall_progress)
        self.worker.statsUpdated.connect(self.update_system_stats)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.has_started_download = True
        self.worker.start()
        self.set_task_running_ui_state(is_running=True, tab_index=0)

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
            self.logger.info("All tasks completed successfully.")
            self.status_label.setText("Finished")
        else:
            self.logger.warning(f"A task failed or was terminated (Exit Code: {exit_code}).")
            self.status_label.setText("Error / Stopped")
        self.set_task_running_ui_state(is_running=False)
        # self.worker is set to None in _on_worker_finished to avoid race conditions
        for i in reversed(range(self.progress_layout.count())):
            item = self.progress_layout.itemAt(i)
            widget = item.widget()
            if widget and not isinstance(widget, QLabel):
                widget.setParent(None)
                widget.deleteLater()
        self.progress_widgets.clear()
        self.progress_layout.addStretch()

    def _on_worker_finished(self):
        """Slot for when the worker thread has completely finished."""
        self.logger.debug("Worker thread finished.")
        self.worker = None

    def on_include_text_changed(self, text):
        self.exclude_ext_input.setEnabled(not bool(text))

    def on_exclude_text_changed(self, text):
        self.include_ext_input.setEnabled(not bool(text))

    def _handle_export_chat_members(self, chat_id):
        config = self.UTILITY_CONFIGS['export_members']
        # Pre-fill the chat_id and let the user choose the output file
        prefilled_values = {'chat_id': chat_id}
        self._run_utility_command(config, prefilled_values)

    def _run_utility_command(self, config, prefilled_values=None):
        if self.worker is not None and self.worker.isRunning():
            self.logger.warning("A task is already running. Please wait for it to complete.")
            return

        values = {}
        if prefilled_values:
            values.update(prefilled_values)

        # Determine which fields still need to be asked from the user
        fields_to_ask = [
            field for field in config['fields']
            if field['name'] not in values
        ]

        if fields_to_ask:
            dialog = UtilityDialog(config['title'], fields_to_ask, self)
            if not dialog.exec():
                self.logger.info(f"'{config['title']}' was cancelled.")
                return
            values.update(dialog.get_values())

        command = [self.tdl_path] + config['base_cmd']
        for field in config['fields']:
            value = values.get(field['name'])
            if value:
                command.extend([field['arg'], value])
        if self.settings_manager.get('debug_mode', False): command.append('--debug')
        command.extend(self._get_proxy_args())
        command.extend(self._get_storage_args())
        command.extend(self._get_namespace_args())
        command.extend(self._get_ntp_args())
        command.extend(self._get_reconnect_timeout_args())
        self.logger.info(f"Running utility: {' '.join(command)}")
        timeout = self.settings_manager.get('command_timeout', 300)
        self.worker = Worker(command, self.logger, timeout=timeout)
        self.worker.taskFinished.connect(self._task_finished)
        self.worker.taskFailedWithLog.connect(self._task_failed)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()
        self.set_task_running_ui_state(is_running=True, tab_index=-1)

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
            self.logger.info("Export cancelled by user.")
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

        if self.advanced_export_settings:
            if self.advanced_export_settings['filter']:
                command.extend(['--filter', self.advanced_export_settings['filter']])
            if self.advanced_export_settings['reply']:
                command.extend(['--reply', self.advanced_export_settings['reply']])
            if self.advanced_export_settings['topic']:
                command.extend(['--topic', self.advanced_export_settings['topic']])

        if self.settings_manager.get('debug_mode', False): command.append('--debug')
        command.extend(self._get_proxy_args())
        command.extend(self._get_storage_args())
        command.extend(self._get_namespace_args())
        command.extend(self._get_ntp_args())
        command.extend(self._get_reconnect_timeout_args())
        self.logger.info(f"Starting export with command: {' '.join(command)}")
        timeout = self.settings_manager.get('command_timeout', 300)
        self.worker = Worker(command, self.logger, timeout=timeout)
        self.worker.taskFinished.connect(self._task_finished)
        self.worker.taskFailedWithLog.connect(self._task_failed)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()
        self.set_task_running_ui_state(is_running=True, tab_index=1)

    def closeEvent(self, event):
        if self.worker is not None and self.worker.isRunning():
            self.log_message.emit("A task is running. Stopping it before exit...")
            self.worker.stop()
            self.worker.wait()
        event.accept()

    def _get_proxy_args(self):
        if self.settings_manager.get('auto_proxy', True):
            proxies = urllib.request.getproxies()
            proxy = proxies.get('https', proxies.get('http'))
            if proxy:
                self.logger.debug(f"Using system proxy: {proxy}")
                return ['--proxy', proxy]
        elif self.settings_manager.get('manual_proxy', ''):
            proxy = self.settings_manager.get('manual_proxy')
            self.logger.debug(f"Using manual proxy: {proxy}")
            return ['--proxy', proxy]
        return []

    def _get_storage_args(self):
        driver = self.settings_manager.get('storage_driver', 'bolt')
        path = self.settings_manager.get('storage_path', '').strip()
        if not path:
            return []
        storage_str = f"type={driver},path={path}"
        return ['--storage', storage_str]

    def _get_namespace_args(self):
        namespace = self.settings_manager.get('namespace', 'default')
        if namespace and namespace != 'default':
            return ['--ns', namespace]
        return []

    def _get_ntp_args(self):
        ntp_server = self.settings_manager.get('ntp_server', '').strip()
        if ntp_server:
            return ['--ntp', ntp_server]
        return []

    def _get_reconnect_timeout_args(self):
        reconnect_timeout = self.settings_manager.get('reconnect_timeout', '5m').strip()
        if reconnect_timeout and reconnect_timeout != '5m' and reconnect_timeout != '0s':
            return ['--reconnect-timeout', reconnect_timeout]
        return []

    def _task_failed(self, log_output):
        self.logger.error("A task failed. See full log in the Log tab or app.log file.")
        # Check if log_output is a string before performing string operations
        if isinstance(log_output, str) and "not authorized" in log_output:
            QMessageBox.warning(
                self,
                "Authentication Required",
                "The operation failed because you are not logged in.\n\n"
                "Please go to Tools > Settings and use the 'Login to New Account' button to log in."
            )