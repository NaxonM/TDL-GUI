# main_window.py

import json
import urllib.request
import subprocess
import re
import os
import sys
from PyQt6.QtCore import (
    QUrl,
)
from PyQt6.QtWidgets import (
    QMainWindow,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QPushButton,
    QProgressBar,
    QMessageBox,
    QLabel,
)
from PyQt6.QtGui import (
    QAction,
    QDesktopServices,
    QColor,
    QTextCursor,
    QTextCharFormat,
    QPalette,
)

from functools import partial
from src.settings_dialog import SettingsDialog
from src.utility_dialog import UtilityDialog
from src.update_manager import UpdateDialog, UpdateManager
from src.config import UTILITY_CONFIGS
from src.tdl_runner import TdlRunner
from src.download_tab import DownloadTab
from src.export_tab import ExportTab
from src.chats_tab import ChatsTab
from src.upload_tab import UploadTab
from src.forward_tab import ForwardTab


class MainWindow(QMainWindow):
    def __init__(self, app, tdl_path, settings_manager, logger, theme="light"):
        super().__init__()
        self.app = app
        self.tdl_path = tdl_path
        self.settings_manager = settings_manager
        self.logger = logger
        self.theme = theme
        self.tdl_runner = TdlRunner(tdl_path, settings_manager, logger)
        self.worker = None
        self.tdl_version = self._get_tdl_version()
        self.update_manager = None
        self.global_controls = []
        self.has_started_download = False
        self.active_task_tab_index = -1
        self.original_tab_text = ""
        self.advanced_settings = {}

        if self.theme == "dark":
            self.error_color = QColor("#FF5555")
            self.warn_color = QColor("#FFC107")
        elif self.theme == "nord":
            self.error_color = QColor("#BF616A")  # nord11
            self.warn_color = QColor("#EBCB8B")  # nord13
        elif self.theme == "solarized-dark":
            self.error_color = QColor("#dc322f")  # red
            self.warn_color = QColor("#b58900")  # yellow
        elif self.theme == "solarized-light":
            self.error_color = QColor("#dc322f")  # red
            self.warn_color = QColor("#b58900")  # yellow
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
        self.download_tab = DownloadTab(
            self.tdl_runner, self.settings_manager, self.logger
        )
        self.upload_tab = UploadTab(self.tdl_runner, self.settings_manager, self.logger)
        self.forward_tab = ForwardTab(
            self.tdl_runner, self.settings_manager, self.logger
        )
        self.export_tab = ExportTab(self.tdl_runner, self.settings_manager, self.logger)
        self.chats_tab = ChatsTab(self.tdl_runner, self.settings_manager, self.logger)
        self.log_tab = self._create_log_tab()

        self.tabs.addTab(self.download_tab, "Download")
        self.tabs.addTab(self.upload_tab, "Upload")
        self.tabs.addTab(self.forward_tab, "Forward")
        self.tabs.addTab(self.export_tab, "Export")
        self.tabs.addTab(self.chats_tab, "Chats")
        self.tabs.addTab(self.log_tab, "Log")

    def _collect_global_controls(self):
        """Collects all controls that should be disabled when a task is running."""
        self.global_controls.extend(
            [
                self.tools_menu,
            ]
        )

    def _setup_connections(self):
        """Connects all signals to slots."""
        self.logger.log_signal.connect(self.append_log)

        # Download Tab Connections
        self.download_tab.task_started.connect(self.on_task_started)
        self.download_tab.task_finished.connect(self._task_finished)
        self.download_tab.overall_progress_updated.connect(self.update_overall_progress)
        self.download_tab.system_stats_updated.connect(self.update_system_stats)

        # Upload Tab Connections
        self.upload_tab.task_started.connect(self.on_task_started)
        self.upload_tab.task_finished.connect(self._task_finished)
        self.upload_tab.system_stats_updated.connect(self.update_system_stats)

        # Forward Tab Connections
        self.forward_tab.task_started.connect(self.on_task_started)
        self.forward_tab.task_finished.connect(self._task_finished)
        self.forward_tab.task_failed.connect(self._on_forward_task_failed)

        # Export Tab Connections
        self.export_tab.task_started.connect(self.on_task_started)
        self.export_tab.task_finished.connect(self._task_finished)

        # Chats Tab Connections
        self.chats_tab.task_started.connect(self.on_task_started)
        self.chats_tab.task_finished.connect(self._task_finished)
        self.chats_tab.export_chat_messages.connect(self.on_export_chat_messages)
        self.chats_tab.export_chat_members.connect(self.on_export_chat_members)

    def on_export_chat_messages(self, chat_id):
        self.tabs.setCurrentWidget(self.export_tab)
        self.export_tab.set_export_source(chat_id)

    def on_export_chat_members(self, chat_id):
        config = UTILITY_CONFIGS["export_members_by_id"]
        prefilled_values = {"chat_id": chat_id}
        self._run_utility_command(config, prefilled_values)

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
        namespace = self.settings_manager.get("namespace", "default")
        self.namespace_label.setText(f"NS: {namespace}")

    def on_task_started(self, worker):
        self.worker = worker
        self.set_task_running_ui_state(True, self.tabs.currentIndex())

    def set_task_running_ui_state(self, is_running, tab_index=-1):
        """Enables or disables UI controls based on the state of a running task."""
        self.download_tab.set_running_state(is_running)
        self.upload_tab.set_running_state(is_running)
        self.forward_tab.set_running_state(is_running)
        self.export_tab.set_running_state(is_running)
        self.chats_tab.set_running_state(is_running)
        for widget in self.global_controls:
            widget.setEnabled(not is_running)

        if is_running:
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
            self.status_progress.hide()
            self.cpu_label.setText("CPU: N/A")
            self.mem_label.setText("Mem: N/A")

            # Restore original tab text
            if self.active_task_tab_index != -1:
                self.tabs.setTabText(self.active_task_tab_index, self.original_tab_text)
                self.active_task_tab_index = -1
                self.original_tab_text = ""

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
        cursor.insertText(message + "\n")

        # Reset format for next entries
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.setCharFormat(QTextCharFormat())
        self.log_output.setTextCursor(cursor)

        # Show important messages in the status bar
        if level in ["INFO", "WARNING", "ERROR", "CRITICAL"]:
            # Strip the timestamp and level for a cleaner status bar message
            status_message = " - ".join(message.split(" - ")[2:])
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
            ("Export Members by ID...", UTILITY_CONFIGS["export_members_by_id"]),
            "separator",
            ("Backup Data", UTILITY_CONFIGS["backup_data"]),
            ("Recover Data", UTILITY_CONFIGS["recover_data"]),
            ("Migrate Data", UTILITY_CONFIGS["migrate_data"]),
        ]
        for item in utility_actions:
            if item == "separator":
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
            result = subprocess.run(
                [self.tdl_path, "version"], capture_output=True, text=True, check=True
            )
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
            active_ns = self.settings_manager.get("namespace")
            self.logger.info(f"Settings saved. Active account is now '{active_ns}'.")
            self._update_namespace_display()
        else:
            self.logger.info("Settings dialog cancelled.")

    def check_for_updates(self):
        self.logger.info("Checking for tdl updates...")
        try:
            local_version_str = self.tdl_version
            match = re.search(r"(\d+\.\d+\.\d+)", local_version_str)
            if not match:
                QMessageBox.warning(
                    self,
                    "Update Check Failed",
                    f"Could not parse local version: {local_version_str}",
                )
                return
            local_version = match.group(1)

            url = "https://api.github.com/repos/iyear/tdl/releases/latest"
            with urllib.request.urlopen(url) as response:
                data = json.loads(response.read().decode())
                latest_version = data["tag_name"].lstrip("v")
                release_notes = data["body"]
                download_url = None
                for asset in data["assets"]:
                    if (
                        "Windows" in asset["name"]
                        and "64bit" in asset["name"]
                        and asset["name"].endswith(".zip")
                    ):
                        download_url = asset["browser_download_url"]
                        break

            self.logger.info(
                f"Local version: {local_version}, Latest version: {latest_version}"
            )

            if local_version < latest_version:
                if not download_url:
                    QMessageBox.warning(
                        self,
                        "Update Check Failed",
                        "Could not find a compatible update file for Windows 64-bit.",
                    )
                    return

                reply = QMessageBox.information(
                    self,
                    "Update Available",
                    f"A new version of tdl is available: <b>{latest_version}</b><br><br>"
                    f"<b>Release Notes:</b><br>{release_notes}<br><br>"
                    "Would you like to download and install it now?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    self.start_update_process(download_url, latest_version)
            else:
                QMessageBox.information(
                    self, "No Updates", "You are using the latest version of tdl."
                )

        except Exception as e:
            self.logger.error(f"Failed to check for updates: {e}")
            QMessageBox.warning(
                self,
                "Update Check Failed",
                "Could not check for updates. See logs for details.",
            )

    def start_update_process(self, url, version):
        self.logger.info(f"Starting update to version {version} from {url}")
        update_dialog = UpdateDialog(version, self)

        self.update_manager = UpdateManager(url, version, self.tdl_path)
        self.update_manager.progress.connect(update_dialog.update_progress)
        self.update_manager.error.connect(self.on_update_error)
        self.update_manager.finished.connect(self.on_update_finished)

        self.update_manager.start_download()
        update_dialog.exec()

    def on_update_error(self, error_message):
        self.logger.error(f"Update failed: {error_message}")
        QMessageBox.critical(self, "Update Failed", error_message)

    def on_update_finished(self, updater_script_path, version):
        self.logger.info(f"Update to {version} downloaded. Restarting...")
        QMessageBox.information(
            self,
            "Update Ready",
            "The update is ready. The application will now restart to complete the installation.",
        )
        # Use DETACHED_PROCESS to run the updater independently
        subprocess.Popen(
            [updater_script_path], creationflags=subprocess.DETACHED_PROCESS
        )
        self.app.quit()

    def handle_desktop_login(self, path, passcode):
        self.logger.info("Desktop login requested. See log for details.")
        if self.tdl_runner.is_running():
            self.logger.warning("A task is already running. Please wait.")
            return

        self.logger.info(f"Attempting to log in from desktop client at: {path}")
        command = ["login", "-d", path]
        if passcode:
            command.extend(["-p", passcode])

        self.worker = self.tdl_runner.run(command)
        if not self.worker:
            return

        self.worker.taskFinished.connect(self._task_finished)
        self.worker.taskFailedWithLog.connect(self._task_failed)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()
        self.set_task_running_ui_state(is_running=True, tab_index=-1)

    def update_overall_progress(self, data):
        self.status_progress.setValue(data["percent"])
        self.status_label.setText(f"Overall Speed: {data['speed']}")

    def update_system_stats(self, data):
        self.cpu_label.setText(f"CPU: {data['cpu']}")
        self.mem_label.setText(f"Mem: {data['mem']}")

    def _task_finished(self, exit_code):
        if exit_code == 0:
            self.logger.info("All tasks completed successfully.")
            self.status_label.setText("Finished")
        else:
            self.logger.warning(
                f"A task failed or was terminated (Exit Code: {exit_code})."
            )
            self.status_label.setText("Error / Stopped")

        # Reset UI state
        self.set_task_running_ui_state(is_running=False)

        # If the finished task was a download, clear the progress widgets
        if self.tabs.currentIndex() == 0:  # Download Tab
            self.download_tab.clear_progress_widgets()

    def _on_worker_finished(self):
        """Slot for when the worker thread has completely finished."""
        self.logger.debug("Worker thread finished.")
        self.worker = None

    def on_include_text_changed(self, text):
        self.exclude_ext_input.setEnabled(not bool(text))

    def on_exclude_text_changed(self, text):
        self.include_ext_input.setEnabled(not bool(text))

    def _run_utility_command(self, config, prefilled_values=None):
        if self.tdl_runner.is_running():
            self.logger.warning(
                "A task is already running. Please wait for it to complete."
            )
            return

        values = {}
        if prefilled_values:
            values.update(prefilled_values)

        # Determine which fields still need to be asked from the user
        fields_to_ask = [
            field for field in config["fields"] if field["name"] not in values
        ]

        if fields_to_ask:
            dialog = UtilityDialog(config["title"], fields_to_ask, self)
            if not dialog.exec():
                self.logger.info(f"'{config['title']}' was cancelled.")
                return
            values.update(dialog.get_values())

        command = config["base_cmd"][:]
        for field in config["fields"]:
            value = values.get(field["name"])
            if value:
                command.extend([field["arg"], value])

        self.worker = self.tdl_runner.run(command)
        if not self.worker:
            return

        self.worker.taskFinished.connect(self._task_finished)
        self.worker.taskFailedWithLog.connect(self._task_failed)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()
        self.set_task_running_ui_state(is_running=True, tab_index=-1)

    def closeEvent(self, event):
        if self.tdl_runner.is_running():
            self.logger.info("A task is running. Stopping it before exit...")
            self.tdl_runner.stop()
            if self.worker:
                self.worker.wait()
        event.accept()

    def _on_forward_task_failed(self, log_output):
        """Handles a failed task from the forward tab, showing a detailed dialog."""
        self.logger.error("Forwarding task failed.")

        error_title = "Forwarding Task Failed"
        error_message = "An error occurred during the forwarding task."

        # Try to parse a more specific error from the tdl output
        # Go panics are a good indicator of a fatal, specific error.
        panic_match = re.search(r"panic:\s*(.*)", log_output, re.IGNORECASE)
        if panic_match:
            error_details = panic_match.group(1).strip()
            # Further clean up common Go error prefixes
            if "invalid expression" in error_details:
                error_title = "Invalid Expression"
                error_message = "The expression you provided is invalid. Please correct it and try again."
                # Extract just the core error message if possible
                expr_err_match = re.search(r"invalid expression:\s*(.*)", error_details, re.IGNORECASE)
                if expr_err_match:
                    error_details = expr_err_match.group(1).strip()

            else:
                 error_message = "A critical error occurred in the `tdl` tool."
        else:
            # Fallback for non-panic errors
            error_details = "See the full log below for details."


        msg_box = QMessageBox(self)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.setWindowTitle(error_title)
        msg_box.setText(f"<b>{error_message}</b>")
        msg_box.setInformativeText("Please check the details below and consult the logs if the issue persists.")
        msg_box.setDetailedText(log_output)
        msg_box.exec()

    def _task_failed(self, log_output):
        self.logger.error("A task failed. See full log in the Log tab or app.log file.")
        # Check if log_output is a string before performing string operations
        if isinstance(log_output, str) and "not authorized" in log_output:
            QMessageBox.warning(
                self,
                "Authentication Required",
                "The operation failed because you are not logged in.\n\n"
                "Please go to Tools > Settings and use the 'Login to New Account' button to log in.",
            )
