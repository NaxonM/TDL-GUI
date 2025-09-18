import os
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QLineEdit,
    QPlainTextEdit,
    QComboBox,
    QLabel,
)

from src.advanced_forward_dialog import AdvancedForwardDialog
from src.select_chat_dialog import SelectChatDialog


class ForwardTab(QWidget):
    task_started = pyqtSignal(object)
    task_finished = pyqtSignal(int)
    task_failed = pyqtSignal(str)

    def __init__(self, tdl_runner, settings_manager, logger, parent=None):
        super().__init__(parent)
        self.tdl_runner = tdl_runner
        self.settings_manager = settings_manager
        self.logger = logger
        self.worker = None
        self.advanced_settings = {}
        self.controls = []

        self._init_ui()
        self._setup_connections()

    def _init_ui(self):
        """Initializes the UI components for the forward tab."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        source_group = self._create_source_group()
        dest_group = self._create_destination_group()

        self.start_forward_button = QPushButton("Start Forward")
        self.start_forward_button.setObjectName("ActionButton")

        self.advanced_settings_button = QPushButton("Advanced Options...")

        self.status_label = QLabel("Status: Idle")

        action_button_layout = QHBoxLayout()
        action_button_layout.addStretch()
        action_button_layout.addWidget(self.status_label)
        action_button_layout.addWidget(self.advanced_settings_button)
        action_button_layout.addWidget(self.start_forward_button)
        action_button_layout.addStretch()

        main_layout.addWidget(source_group)
        main_layout.addWidget(dest_group)
        main_layout.addLayout(action_button_layout)
        main_layout.addStretch()

        self.controls.extend(
            [
                self.source_input,
                self.dest_chat_input,
                self.select_chat_button,
                self.advanced_settings_button,
            ]
        )

    def _setup_connections(self):
        """Connects signals to slots for the forward tab."""
        self.start_forward_button.clicked.connect(self.handle_forward_button)
        self.advanced_settings_button.clicked.connect(self.open_advanced_settings_dialog)
        self.select_chat_button.clicked.connect(self._open_select_chat_dialog)

    def _open_select_chat_dialog(self):
        dialog = SelectChatDialog(self.tdl_runner, self.logger, self)
        dialog.chat_selected.connect(self.dest_chat_input.setText)
        dialog.exec()

    def open_advanced_settings_dialog(self):
        dialog = AdvancedForwardDialog(
            tdl_runner=self.tdl_runner,
            settings_manager=self.settings_manager,
            logger=self.logger,
            parent=self,
        )
        if dialog.exec():
            self.advanced_settings = dialog.get_settings()
            self.logger.info(f"Advanced forward settings saved: {self.advanced_settings}")
        else:
            self.logger.info("Advanced forward settings dialog cancelled.")

    def _create_source_group(self):
        group = QGroupBox("Source Messages")
        layout = QVBoxLayout(group)
        self.source_input = QPlainTextEdit()
        self.source_input.setPlaceholderText(
            "Paste message links or file paths here, one per line."
        )
        self.source_input.setToolTip(
            "Enter one Telegram message link (e.g., https://t.me/channel/123) or one local .json file path per line."
        )
        layout.addWidget(self.source_input)
        return group

    def _create_destination_group(self):
        group = QGroupBox("Destination Chat")
        layout = QHBoxLayout(group)
        self.dest_chat_input = QLineEdit()
        self.dest_chat_input.setPlaceholderText(
            "Enter Chat ID, @username, or link (leave empty for Saved Messages)"
        )
        self.dest_chat_input.setToolTip(
            "Enter a single Chat ID, @username, or chat link.\nMultiple destinations are not supported."
        )
        self.select_chat_button = QPushButton("Select Chat...")
        layout.addWidget(self.dest_chat_input)
        layout.addWidget(self.select_chat_button)
        return group

    def update_status_label(self, status):
        self.status_label.setText(f"Status: {status}")

    def handle_forward_button(self):
        if self.tdl_runner.is_running():
            self.tdl_runner.stop()
            return

        source_text = self.source_input.toPlainText().strip()
        if not source_text:
            self.logger.error("Source input cannot be empty.")
            return

        command = ["forward"]

        sources = source_text.splitlines()
        for source in sources:
            clean_source = source.strip()
            if not clean_source:
                continue

            # tdl automatically detects if the source is a link or a JSON file,
            # so we can use the --from flag for both.
            if " " in clean_source and os.name == "nt":
                command.extend(["--from", f'"{clean_source}"'])
            else:
                command.extend(["--from", clean_source])

        dest_chat = self.dest_chat_input.text().strip()
        if dest_chat:
            command.extend(["--to", dest_chat])

        if self.advanced_settings:
            if self.advanced_settings.get("mode"):
                command.extend(["--mode", self.advanced_settings["mode"]])
            if self.advanced_settings.get("edit_expression"):
                command.extend(["--edit", self.advanced_settings["edit_expression"]])
            if self.advanced_settings["dry_run"]:
                command.append("--dry-run")
            if self.advanced_settings["silent"]:
                command.append("--silent")
            if self.advanced_settings["no_group"]:
                command.append("--single")
            if self.advanced_settings["desc_order"]:
                command.append("--desc")

        self.worker = self.tdl_runner.run(command)
        if not self.worker:
            return

        self.task_started.emit(self.worker)
        self.worker.taskFinished.connect(self.task_finished)
        self.worker.taskFailedWithLog.connect(self._on_task_failed)
        self.worker.taskFinished.connect(lambda: self.update_status_label("Completed"))
        self.worker.start()
        self.update_status_label("Running")

    def _on_task_failed(self, exit_code, log):
        self.update_status_label(f"Error (Code: {exit_code})")
        self.task_failed.emit(log)

    def set_running_state(self, is_running):
        """Enable or disable controls based on task status."""
        for control in self.controls:
            control.setEnabled(not is_running)

        self.start_forward_button.setEnabled(True)
        self.start_forward_button.setText(
            "Stop Forwarding" if is_running else "Start Forward"
        )
        if not is_running:
            self.update_status_label("Idle")
