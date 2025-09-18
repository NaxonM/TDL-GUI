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
    QFileDialog,
    QStyle,
)

from src.advanced_upload_dialog import AdvancedUploadDialog
from src.drag_drop_widget import DragDropPlainTextEdit
from src.select_chat_dialog import SelectChatDialog
from src.progress_widget import DownloadProgressWidget # Can be reused for uploads
from PyQt6.QtWidgets import QScrollArea, QLabel


class UploadTab(QWidget):
    task_started = pyqtSignal(object)
    task_finished = pyqtSignal(int)
    system_stats_updated = pyqtSignal(dict) # To pass through to main window

    def __init__(self, tdl_runner, settings_manager, logger, parent=None):
        super().__init__(parent)
        self.tdl_runner = tdl_runner
        self.settings_manager = settings_manager
        self.logger = logger
        self.worker = None
        self.advanced_settings = {}
        self.progress_widgets = {}
        self.controls = []

        self._init_ui()
        self._setup_connections()

    def _init_ui(self):
        """Initializes the UI components for the upload tab."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        source_group = self._create_source_group()
        dest_group = self._create_destination_group()

        self.start_upload_button = QPushButton("Start Upload")
        self.start_upload_button.setObjectName("ActionButton")

        self.advanced_settings_button = QPushButton("Advanced Options...")

        action_button_layout = QHBoxLayout()
        action_button_layout.addStretch()
        action_button_layout.addWidget(self.advanced_settings_button)
        action_button_layout.addWidget(self.start_upload_button)
        action_button_layout.addStretch()

        progress_group = self._create_progress_group()

        main_layout.addWidget(source_group)
        main_layout.addWidget(dest_group)
        main_layout.addLayout(action_button_layout)
        main_layout.addWidget(progress_group)

        self.controls.extend(
            [
                self.source_input,
                self.load_files_button,
                self.load_folder_button,
                self.clear_source_button,
                self.dest_chat_input,
                self.select_chat_button,
                self.advanced_settings_button,
            ]
        )

    def _setup_connections(self):
        """Connects signals to slots for the upload tab."""
        self.start_upload_button.clicked.connect(self.handle_upload_button)
        self.load_files_button.clicked.connect(self.select_files_to_upload)
        self.load_folder_button.clicked.connect(self.select_folder_to_upload)
        self.clear_source_button.clicked.connect(self.source_input.clear)
        self.advanced_settings_button.clicked.connect(self.open_advanced_settings_dialog)
        self.select_chat_button.clicked.connect(self._open_select_chat_dialog)

    def _open_select_chat_dialog(self):
        dialog = SelectChatDialog(self.tdl_runner, self.logger, self)
        dialog.chat_selected.connect(self.dest_chat_input.setText)
        dialog.exec()

    def open_advanced_settings_dialog(self):
        dialog = AdvancedUploadDialog(self)
        if dialog.exec():
            self.advanced_settings = dialog.get_settings()
            self.logger.info(f"Advanced upload settings saved: {self.advanced_settings}")
        else:
            self.logger.info("Advanced upload settings dialog cancelled.")

    def _create_source_group(self):
        group = QGroupBox("Source Files/Folders")
        layout = QVBoxLayout(group)
        self.source_input = DragDropPlainTextEdit()
        self.source_input.setPlaceholderText(
            "Add file or folder paths here, one per line, or drag and drop them."
        )
        self.source_input.setToolTip(
            "Enter one file path or folder path per line. You can also use the buttons below."
        )

        button_layout = QHBoxLayout()
        self.load_files_button = QPushButton("Add Files...")
        self.load_files_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)
        )
        self.load_folder_button = QPushButton("Add Folder...")
        self.load_folder_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        )
        self.clear_source_button = QPushButton("Clear")
        self.clear_source_button.setIcon(
            self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton)
        )

        button_layout.addWidget(self.load_files_button)
        button_layout.addWidget(self.load_folder_button)
        button_layout.addWidget(self.clear_source_button)
        button_layout.addStretch()

        layout.addWidget(self.source_input)
        layout.addLayout(button_layout)
        return group

    def _create_destination_group(self):
        group = QGroupBox("Destination Chat")
        layout = QHBoxLayout(group)
        self.dest_chat_input = QLineEdit()
        self.dest_chat_input.setPlaceholderText(
            "Enter Chat ID, @username, or chat link (leave empty for Saved Messages)"
        )
        self.select_chat_button = QPushButton("Select Chat...")
        layout.addWidget(self.dest_chat_input)
        layout.addWidget(self.select_chat_button)
        return group

    def select_files_to_upload(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Files to Upload", QDir.homePath()
        )
        if files:
            self.source_input.appendPlainText("\n".join(files))

    def select_folder_to_upload(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder to Upload", QDir.homePath()
        )
        if folder:
            self.source_input.appendPlainText(folder)

    def handle_upload_button(self):
        if self.tdl_runner.is_running():
            self.tdl_runner.stop()
            return

        source_text = self.source_input.toPlainText().strip()
        if not source_text:
            self.logger.error("Source input cannot be empty.")
            return

        command = ["up"] # 'up' is the tdl command for upload

        paths = source_text.splitlines()
        for path in paths:
            clean_path = path.strip()
            if clean_path:
                # On Windows, paths with spaces must be quoted for many command-line tools.
                if " " in clean_path and os.name == "nt":
                    command.extend(["-p", f'"{clean_path}"'])
                else:
                    command.extend(["-p", clean_path])

        dest_chat = self.dest_chat_input.text().strip()
        if dest_chat:
            command.extend(["-c", dest_chat])

        if self.advanced_settings:
            command.extend(["-l", str(self.advanced_settings["concurrent_tasks"])])
            command.extend(["-t", str(self.advanced_settings["threads_per_task"])])
            if self.advanced_settings["exclude_exts"]:
                # The --exclude flag in tdl might take multiple arguments
                # For simplicity, we'll assume it's a space-separated string for now
                # that the user needs to format correctly.
                # A more robust implementation could split the string.
                for ext in self.advanced_settings["exclude_exts"].split():
                    command.extend(["-e", ext])
            if self.advanced_settings["delete_local"]:
                command.append("--rm")
            if self.advanced_settings["upload_as_photo"]:
                command.append("--photo")

        self.worker = self.tdl_runner.run(command)
        if not self.worker:
            return

        self.task_started.emit(self.worker)
        self.worker.uploadStarted.connect(self.add_upload_progress_widget)
        self.worker.uploadProgress.connect(self.update_upload_progress)
        self.worker.uploadFinished.connect(self.remove_upload_progress_widget)
        self.worker.statsUpdated.connect(self.system_stats_updated)
        self.worker.taskFinished.connect(self.on_task_finished)
        self.worker.start()

    def _create_progress_group(self):
        group = QGroupBox("Live Uploads")
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

    def add_upload_progress_widget(self, file_id):
        if file_id not in self.progress_widgets:
            progress_widget = DownloadProgressWidget(file_id) # Reusing the download widget
            self.progress_layout.insertWidget(0, progress_widget)
            self.progress_widgets[file_id] = progress_widget

    def update_upload_progress(self, progress_data):
        file_id = progress_data["id"]
        if file_id in self.progress_widgets:
            self.progress_widgets[file_id].update_progress(progress_data)
        else:
            # This can happen if the first progress update arrives before the "started" signal
            self.add_upload_progress_widget(file_id)
            self.progress_widgets[file_id].update_progress(progress_data)

    def remove_upload_progress_widget(self, file_id):
        if file_id in self.progress_widgets:
            widget = self.progress_widgets.pop(file_id)
            widget.deleteLater()

    def clear_progress_widgets(self):
        for i in reversed(range(self.progress_layout.count())):
            item = self.progress_layout.itemAt(i)
            if item and item.widget():
                widget = item.widget()
                if not isinstance(widget, QLabel):
                    widget.setParent(None)
                    widget.deleteLater()
        self.progress_widgets.clear()

    def on_task_finished(self, exit_code):
        # This is connected to the worker's taskFinished signal
        if exit_code != 0:
            # Don't clear on failure, so user can see where it stopped
            pass
        else:
            # Clear progress widgets on success
            self.clear_progress_widgets()
        self.task_finished.emit(exit_code) # Pass the signal on to the main window

    def set_running_state(self, is_running):
        """Enable or disable controls based on task status."""
        for control in self.controls:
            control.setEnabled(not is_running)

        self.start_upload_button.setEnabled(True)
        self.start_upload_button.setText(
            "Stop Upload" if is_running else "Start Upload"
        )
