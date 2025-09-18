import json
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMenu,
    QMessageBox,
)

from src.config import CHAT_NAME_COLORS


class ChatsTab(QWidget):
    task_started = pyqtSignal(object)
    task_finished = pyqtSignal(int)
    export_chat_messages = pyqtSignal(str)
    export_chat_members = pyqtSignal(str)

    def __init__(self, tdl_runner, settings_manager, logger, parent=None):
        super().__init__(parent)
        self.tdl_runner = tdl_runner
        self.settings_manager = settings_manager
        self.logger = logger
        self.worker = None
        self.controls = []

        self._init_ui()
        self._setup_connections()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        self.chats_table = QTableWidget()
        self.chats_table.setColumnCount(4)
        self.chats_table.setHorizontalHeaderLabels(["Name", "Type", "ID", "Username"])
        self.chats_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.chats_table.verticalHeader().setVisible(False)
        self.chats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.chats_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.chats_table.setSortingEnabled(True)
        self.chats_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        button_layout = QHBoxLayout()
        self.refresh_chats_button = QPushButton("Refresh Chat List")
        self.refresh_chats_button.setToolTip(
            "Fetch the latest list of your chats from Telegram."
        )
        button_layout.addStretch()
        button_layout.addWidget(self.refresh_chats_button)

        layout.addWidget(self.chats_table)
        layout.addLayout(button_layout)

        self.controls.extend([self.refresh_chats_button, self.chats_table])

    def _setup_connections(self):
        self.refresh_chats_button.clicked.connect(self.handle_refresh_chats)
        self.chats_table.customContextMenuRequested.connect(
            self._show_chat_context_menu
        )

    def handle_refresh_chats(self):
        if self.tdl_runner.is_running():
            self.logger.warning(
                "A task is already running. Please wait for it to complete."
            )
            return

        self.logger.info("Fetching chat list...")
        command = ["chat", "ls", "-o", "json"]

        self.worker = self.tdl_runner.run(command)
        if not self.worker:
            return

        self.task_started.emit(self.worker)
        self.worker.taskData.connect(self._populate_chats_table)
        self.worker.taskFinished.connect(self.task_finished)
        self.worker.start()

    def _show_chat_context_menu(self, position):
        selected_items = self.chats_table.selectedItems()
        if not selected_items:
            return

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
            self.export_chat_messages.emit(chat_id)
        elif action == export_members_action:
            self.export_chat_members.emit(chat_id)

    def _handle_copy_chat_id(self, chat_id):
        from PyQt6.QtWidgets import QApplication

        clipboard = QApplication.clipboard()
        clipboard.setText(chat_id)
        self.logger.info(f"Copied Chat ID to clipboard: {chat_id}")

    def _populate_chats_table(self, json_data):
        try:
            chats = json.loads(json_data)
            self.chats_table.setSortingEnabled(False)
            self.chats_table.setRowCount(0)

            for chat in chats:
                row_position = self.chats_table.rowCount()
                self.chats_table.insertRow(row_position)

                name = chat.get("visible_name", "")
                type = chat.get("type", "")
                id_str = str(chat.get("id", ""))
                username = chat.get("username", "")

                name_item = QTableWidgetItem(name)
                if id_str:
                    color_index = hash(id_str) % len(CHAT_NAME_COLORS)
                    name_item.setForeground(CHAT_NAME_COLORS[color_index])

                self.chats_table.setItem(row_position, 0, name_item)
                self.chats_table.setItem(row_position, 1, QTableWidgetItem(type))
                self.chats_table.setItem(row_position, 2, QTableWidgetItem(id_str))
                self.chats_table.setItem(row_position, 3, QTableWidgetItem(username))

            self.chats_table.setSortingEnabled(True)
            self.logger.info(
                f"Successfully populated chats table with {len(chats)} chats."
            )

        except json.JSONDecodeError:
            self.logger.error("Failed to parse JSON data from 'tdl chat ls' command.")
            QMessageBox.critical(
                self,
                "Error",
                "Could not parse the chat list from tdl. See logs for details.",
            )

    def set_running_state(self, is_running):
        for control in self.controls:
            control.setEnabled(not is_running)
