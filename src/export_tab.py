from PyQt6.QtCore import pyqtSignal, QDate, QDateTime, Qt
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QGroupBox,
    QPushButton,
    QLineEdit,
    QSpinBox,
    QCheckBox,
    QFileDialog,
    QDateEdit,
    QLabel,
    QComboBox,
    QStackedWidget,
    QMessageBox,
)
from src.advanced_export_dialog import AdvancedExportDialog


class ExportTab(QWidget):
    task_started = pyqtSignal(object)
    task_finished = pyqtSignal(int)

    def __init__(self, tdl_runner, settings_manager, logger, parent=None):
        super().__init__(parent)
        self.tdl_runner = tdl_runner
        self.settings_manager = settings_manager
        self.logger = logger
        self.worker = None
        self.advanced_export_settings = {}
        self.controls = []

        self._init_ui()
        self._setup_connections()

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)

        source_group = self._create_source_group()
        options_group = self._create_options_group()
        content_group = self._create_content_group()

        self.run_export_button = QPushButton("Export to JSON...")
        self.run_export_button.setObjectName("ActionButton")

        self.advanced_export_button = QPushButton("Advanced Options...")

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

        self.controls.extend(
            [
                self.export_source_input,
                self.export_type_combo,
                self.filter_stack,
                self.export_with_content_checkbox,
                self.export_all_types_checkbox,
                self.advanced_export_button,
                self.run_export_button,
            ]
        )

    def _setup_connections(self):
        self.run_export_button.clicked.connect(self.handle_export_button)
        self.export_type_combo.currentIndexChanged.connect(
            self.filter_stack.setCurrentIndex
        )
        self.advanced_export_button.clicked.connect(self.open_advanced_export_dialog)

    def _create_source_group(self):
        group = QGroupBox("Export Source")
        layout = QFormLayout(group)
        self.export_source_input = QLineEdit()
        self.export_source_input.setPlaceholderText("Enter Channel/Chat ID or Username")
        self.export_source_input.setToolTip(
            "Enter the source to export from, e.g., 'telegram' or '-100123456789'."
        )
        layout.addRow("Channel/Chat Source:", self.export_source_input)
        return group

    def _create_options_group(self):
        group = QGroupBox("Export Options")
        layout = QFormLayout(group)

        self.export_type_combo = QComboBox()
        self.export_type_combo.addItems(
            ["All Messages", "By Time Range", "By ID Range", "Last N Messages"]
        )

        self.filter_stack = QStackedWidget()
        self.filter_stack.addWidget(QWidget())

        time_range_widget = QWidget()
        time_range_layout = QHBoxLayout(time_range_widget)
        self.from_date_edit = QDateEdit(calendarPopup=True, displayFormat="yyyy-MM-dd")
        self.to_date_edit = QDateEdit(
            calendarPopup=True, displayFormat="yyyy-MM-dd", date=QDate.currentDate()
        )
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

    def _create_content_group(self):
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

    def handle_export_button(self):
        if self.tdl_runner.is_running():
            self.logger.warning("A task is already running. Please wait.")
            return

        source = self.export_source_input.text().strip()
        if not source:
            QMessageBox.warning(self, "Input Error", "Export source cannot be empty.")
            return

        output_path, _ = QFileDialog.getSaveFileName(
            self, "Save Exported JSON", "", "JSON Files (*.json)"
        )
        if not output_path:
            self.logger.info("Export cancelled by user.")
            return

        command = ["chat", "export", "-c", source, "-o", output_path]
        export_type_index = self.export_type_combo.currentIndex()
        if export_type_index == 1:
            from_dt = QDateTime(self.from_date_edit.date())
            to_dt = QDateTime(self.to_date_edit.date()).addDays(1).addSecs(-1)
            command.extend(
                [
                    "-T",
                    "time",
                    "-i",
                    f"{int(from_dt.toSecsSinceEpoch())},{int(to_dt.toSecsSinceEpoch())}",
                ]
            )
        elif export_type_index == 2:
            from_id = self.from_id_input.text().strip() or "0"
            to_id = self.to_id_input.text().strip() or "0"
            command.extend(["-T", "id", "-i", f"{from_id},{to_id}"])
        elif export_type_index == 3:
            n_messages = self.last_n_spinbox.value()
            command.extend(["-T", "last", "-i", str(n_messages)])
        if self.export_with_content_checkbox.isChecked():
            command.append("--with-content")
        if self.export_all_types_checkbox.isChecked():
            command.append("--all")

        if self.advanced_export_settings:
            if self.advanced_export_settings["filter"]:
                command.extend(["--filter", self.advanced_export_settings["filter"]])
            if self.advanced_export_settings["reply"]:
                command.extend(["--reply", self.advanced_export_settings["reply"]])
            if self.advanced_export_settings["topic"]:
                command.extend(["--topic", self.advanced_export_settings["topic"]])

        self.worker = self.tdl_runner.run(command)
        if not self.worker:
            return

        self.task_started.emit(self.worker)
        self.worker.taskFinished.connect(self.task_finished)
        self.worker.start()

    def set_running_state(self, is_running):
        for control in self.controls:
            control.setEnabled(not is_running)

    def set_export_source(self, source):
        self.export_source_input.setText(source)
