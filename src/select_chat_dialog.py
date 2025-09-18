import json
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLineEdit,
    QDialogButtonBox,
    QMessageBox,
)

from src.config import CHAT_NAME_COLORS


class SelectChatDialog(QDialog):
    chat_selected = pyqtSignal(str)

    def __init__(self, tdl_runner, logger, parent=None):
        super().__init__(parent)
        self.tdl_runner = tdl_runner
        self.logger = logger
        self.worker = None

        self._init_ui()
        self._setup_connections()
        self._load_chats()

    def _init_ui(self):
        self.setWindowTitle("Select a Chat")
        self.setMinimumSize(500, 400)
        layout = QVBoxLayout(self)

        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for chats...")
        search_layout.addWidget(self.search_input)

        self.chats_table = QTableWidget()
        self.chats_table.setColumnCount(3)
        self.chats_table.setHorizontalHeaderLabels(["Name", "Type", "Username"])
        self.chats_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )
        self.chats_table.verticalHeader().setVisible(False)
        self.chats_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.chats_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.chats_table.setSortingEnabled(True)

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addLayout(search_layout)
        layout.addWidget(self.chats_table)
        layout.addWidget(button_box)

    def _setup_connections(self):
        self.search_input.textChanged.connect(self._filter_table)
        self.chats_table.itemDoubleClicked.connect(self.accept)

    def _load_chats(self):
        if self.tdl_runner.is_running():
            self.logger.warning(
                "A task is already running. Cannot load chats at the moment."
            )
            QMessageBox.warning(
                self,
                "Busy",
                "Another task is in progress. Please wait for it to finish before selecting a chat.",
            )
            return

        self.logger.info("Fetching chat list for selection...")
        command = ["chat", "ls", "-o", "json"]

        self.worker = self.tdl_runner.run(command)
        if not self.worker:
            return

        self.worker.taskData.connect(self._populate_chats_table)
        self.worker.taskFinished.connect(self._on_load_finished)
        self.worker.start()

    def _on_load_finished(self, exit_code):
        if exit_code != 0:
            self.logger.error("Failed to load chat list.")
            QMessageBox.critical(
                self, "Error", "Could not load the chat list from tdl."
            )

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

                # Store the ID in a custom role for later retrieval
                id_item = QTableWidgetItem(id_str)
                id_item.setData(Qt.ItemDataRole.UserRole, id_str)

                self.chats_table.setItem(row_position, 0, name_item)
                self.chats_table.setItem(row_position, 1, QTableWidgetItem(type))
                self.chats_table.setItem(row_position, 2, QTableWidgetItem(username))
                # We store the ID in the first item's data
                self.chats_table.item(row_position, 0).setData(Qt.ItemDataRole.UserRole, id_str)


            self.chats_table.setSortingEnabled(True)
            self.logger.info(
                f"Successfully populated select-chat dialog with {len(chats)} chats."
            )
        except json.JSONDecodeError:
            self.logger.error("Failed to parse JSON from 'tdl chat ls' in dialog.")
            QMessageBox.critical(
                self,
                "Error",
                "Could not parse the chat list from tdl. See logs for details.",
            )

    def _filter_table(self, text):
        for i in range(self.chats_table.rowCount()):
            match = False
            for j in range(self.chats_table.columnCount()):
                item = self.chats_table.item(i, j)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.chats_table.setRowHidden(i, not match)

    def get_selected_chat_id(self):
        selected_items = self.chats_table.selectedItems()
        if not selected_items:
            return None

        # Retrieve the ID from the custom data role of the first item in the selected row
        selected_row = selected_items[0].row()
        id_item = self.chats_table.item(selected_row, 0)
        return id_item.data(Qt.ItemDataRole.UserRole) if id_item else None

    def accept(self):
        chat_id = self.get_selected_chat_id()
        if chat_id:
            self.chat_selected.emit(chat_id)
            super().accept()
        else:
            QMessageBox.warning(self, "No Selection", "Please select a chat from the list.")
