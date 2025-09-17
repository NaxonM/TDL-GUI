import os
from PyQt6.QtCore import QDir, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QLineEdit,
    QToolButton,
    QPlainTextEdit,
    QFileDialog,
    QScrollArea,
    QLabel,
    QStyle,
)

from src.advanced_settings_dialog import AdvancedSettingsDialog
from src.progress_widget import DownloadProgressWidget


class DownloadTab(QWidget):
    task_started = pyqtSignal(object)
    task_finished = pyqtSignal(int)
    overall_progress_updated = pyqtSignal(dict)
    system_stats_updated = pyqtSignal(dict)

    def __init__(self, tdl_runner, settings_manager, logger, parent=None):
        super().__init__(parent)
        self.tdl_runner = tdl_runner
        self.settings_manager = settings_manager
        self.logger = logger
        self.worker = None
        self.advanced_settings = {}
        self.progress_widgets = {}
        self.controls = []
        self.has_started_download = False

        self._init_ui()
        self._setup_connections()

    def _init_ui(self):
        """Initializes the UI components for the download tab."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        source_group = self._create_source_group()
        dest_group = self._create_destination_group()
        progress_group = self._create_progress_group()

        self.start_download_button = QPushButton("Start Download")
        self.start_download_button.setObjectName("ActionButton")
        self.resume_download_button = QPushButton("Resume Last Download")
        self.resume_download_button.setObjectName("ActionButton")
        self.resume_download_button.setEnabled(
            False
        )  # Disabled until a download has run

        self.advanced_settings_button = QPushButton("Advanced Options...")

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

        self.controls.extend(
            [
                self.source_input,
                self.load_from_file_button,
                self.clear_source_button,
                self.dest_path_input,
                self.browse_dest_button,
                self.advanced_settings_button,
                self.resume_download_button,
            ]
        )

    def _setup_connections(self):
        """Connects signals to slots for the download tab."""
        self.start_download_button.clicked.connect(self.handle_download_button)
        self.resume_download_button.clicked.connect(self.handle_resume_button)
        self.load_from_file_button.clicked.connect(self.load_source_from_file)
        self.browse_dest_button.clicked.connect(self.select_destination_directory)
        self.clear_source_button.clicked.connect(self.source_input.clear)
        self.advanced_settings_button.clicked.connect(
            self.open_advanced_settings_dialog
        )

    def _create_source_group(self):
        group = QGroupBox("Source Input")
        layout = QVBoxLayout(group)
        self.source_input = QPlainTextEdit()
        self.source_input.setPlaceholderText(
            "Paste message links or file paths here, one per line."
        )
        self.source_input.setToolTip(
            "Enter one Telegram message link (e.g., https://t.me/channel/123) or one local .json file path per line."
        )

        button_layout = QHBoxLayout()
        self.load_from_file_button = QPushButton("Load from File...")
        self.load_from_file_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        )
        self.load_from_file_button.setToolTip(
            "Load a list of sources from a text file."
        )

        self.clear_source_button = QPushButton("Clear")
        self.clear_source_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton)
        )
        self.clear_source_button.setToolTip("Clear all text from the source input box.")

        button_layout.addWidget(self.load_from_file_button)
        button_layout.addWidget(self.clear_source_button)
        button_layout.addStretch()

        layout.addWidget(self.source_input)
        layout.addLayout(button_layout)
        return group

    def _create_destination_group(self):
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

    def _create_progress_group(self):
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

    def open_advanced_settings_dialog(self):
        dialog = AdvancedSettingsDialog(self)
        if dialog.exec():
            self.advanced_settings = dialog.get_settings()
            self.logger.info("Advanced settings saved.")
        else:
            self.logger.info("Advanced settings dialog cancelled.")

    def select_destination_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Destination Directory", QDir.homePath()
        )
        if directory:
            self.dest_path_input.setText(directory)

    def load_source_from_file(self):
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Load Source File", QDir.homePath(), "Text Files (*.txt)"
        )
        if filepath:
            try:
                with open(filepath, "r") as f:
                    self.source_input.setPlainText(f.read())
                self.logger.info(f"Loaded sources from {filepath}")
            except Exception as e:
                self.logger.error(f"Error reading file {filepath}: {e}")

    def handle_download_button(self):
        if self.tdl_runner.is_running():
            self.tdl_runner.stop()
            return

        source_text = self.source_input.toPlainText().strip()
        if not source_text:
            self.logger.error("Source input cannot be empty.")
            return

        command = ["download"]
        lines = source_text.splitlines()
        for line in lines:
            clean_line = line.strip()
            if not clean_line:
                continue
            if clean_line.endswith(".json") and os.path.exists(clean_line):
                command.extend(["-f", clean_line])
            else:
                command.extend(["-u", clean_line])

        dest_path = self.dest_path_input.text().strip() or QDir.home().filePath(
            "Downloads"
        )
        os.makedirs(dest_path, exist_ok=True)
        command.extend(["-d", dest_path])

        if self.advanced_settings:
            command.extend(["-l", str(self.advanced_settings["concurrent_tasks"])])
            command.extend(["-t", str(self.advanced_settings["threads_per_task"])])
            if self.advanced_settings["include_exts"]:
                command.extend(["-i", self.advanced_settings["include_exts"]])
            if self.advanced_settings["exclude_exts"]:
                command.extend(["-e", self.advanced_settings["exclude_exts"]])
            if self.advanced_settings["desc_order"]:
                command.append("--desc")
            if self.advanced_settings["skip_same"]:
                command.append("--skip-same")
            if self.advanced_settings["rewrite_ext"]:
                command.append("--rewrite-ext")
            if self.advanced_settings["group_albums"]:
                command.append("--group")
            if self.advanced_settings["use_takeout"]:
                command.append("--takeout")
            command.extend(["--pool", str(self.advanced_settings["pool_size"])])
            if self.advanced_settings["template"]:
                command.extend(["--template", self.advanced_settings["template"]])
            delay_value = self.advanced_settings["delay"]
            if delay_value > 0:
                delay_unit = self.advanced_settings["delay_unit"]
                command.extend(["--delay", f"{delay_value}{delay_unit}"])

        self.worker = self.tdl_runner.run(command)
        if not self.worker:
            return

        self.task_started.emit(self.worker)
        self.worker.downloadStarted.connect(self.add_download_progress_widget)
        self.worker.downloadProgress.connect(self.update_download_progress)
        self.worker.downloadFinished.connect(self.remove_download_progress_widget)
        self.worker.overallProgress.connect(self.overall_progress_updated)
        self.worker.statsUpdated.connect(self.system_stats_updated)
        self.worker.taskFinished.connect(self.task_finished)
        self.has_started_download = True
        self.worker.start()

    def handle_resume_button(self):
        if self.tdl_runner.is_running():
            self.logger.warning("A task is already running. Please wait.")
            return

        self.logger.info("Attempting to resume the last download...")
        command = ["download", "--continue"]

        self.worker = self.tdl_runner.run(command)
        if not self.worker:
            return

        self.task_started.emit(self.worker)
        self.worker.downloadStarted.connect(self.add_download_progress_widget)
        self.worker.downloadProgress.connect(self.update_download_progress)
        self.worker.downloadFinished.connect(self.remove_download_progress_widget)
        self.worker.overallProgress.connect(self.overall_progress_updated)
        self.worker.statsUpdated.connect(self.system_stats_updated)
        self.worker.taskFinished.connect(self.task_finished)
        self.has_started_download = True
        self.worker.start()

    def set_running_state(self, is_running):
        """Enable or disable controls based on task status."""
        for control in self.controls:
            control.setEnabled(not is_running)

        # The start/stop button should always be enabled.
        self.start_download_button.setEnabled(True)
        self.start_download_button.setText(
            "Stop Download" if is_running else "Start Download"
        )
        if not is_running and self.resume_download_button.isEnabled():
            # Don't disable resume button if it was enabled
            pass
        else:
            self.resume_download_button.setEnabled(not is_running)

    def add_download_progress_widget(self, file_id):
        if file_id not in self.progress_widgets:
            progress_widget = DownloadProgressWidget(file_id)
            self.progress_layout.insertWidget(0, progress_widget)
            self.progress_widgets[file_id] = progress_widget

    def update_download_progress(self, progress_data):
        file_id = progress_data["id"]
        if file_id in self.progress_widgets:
            self.progress_widgets[file_id].update_progress(progress_data)
        else:
            self.add_download_progress_widget(file_id)
            self.progress_widgets[file_id].update_progress(progress_data)

    def remove_download_progress_widget(self, file_id):
        if file_id in self.progress_widgets:
            widget = self.progress_widgets.pop(file_id)
            widget.deleteLater()

    def clear_progress_widgets(self):
        for i in reversed(range(self.progress_layout.count())):
            item = self.progress_layout.itemAt(i)
            widget = item.widget()
            if widget and not isinstance(widget, QLabel):  # Don't remove the stretch
                widget.setParent(None)
                widget.deleteLater()
        self.progress_widgets.clear()
