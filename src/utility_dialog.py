from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QDialogButtonBox, QFileDialog, QWidget, QHBoxLayout
)
from PyQt6.QtCore import QDir

class UtilityDialog(QDialog):
    def __init__(self, title, fields, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(400)
        self.fields = {}

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        for field_config in fields:
            name = field_config['name']
            label = field_config['label']
            field_type = field_config.get('type', 'text')

            if field_type == 'open_file':
                widget = self._create_file_input(True)
            elif field_type == 'save_file':
                widget = self._create_file_input(False)
            else:
                widget = QLineEdit()

            form_layout.addRow(label, widget)
            self.fields[name] = widget

        main_layout.addLayout(form_layout)

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

    def _create_file_input(self, open_file=True):
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0,0,0,0)

        line_edit = QLineEdit()
        button = QPushButton("...")

        if open_file:
            button.clicked.connect(lambda: self._get_file_path(line_edit))
        else:
            button.clicked.connect(lambda: self._get_save_path(line_edit))

        layout.addWidget(line_edit)
        layout.addWidget(button)
        container.line_edit = line_edit # Store reference
        return container

    def _get_file_path(self, line_edit):
        path, _ = QFileDialog.getOpenFileName(self, "Select File", QDir.homePath())
        if path:
            line_edit.setText(path)

    def _get_save_path(self, line_edit):
        path, _ = QFileDialog.getSaveFileName(self, "Select File", QDir.homePath())
        if path:
            line_edit.setText(path)

    def get_values(self):
        values = {}
        for name, widget in self.fields.items():
            if isinstance(widget, QLineEdit):
                 values[name] = widget.text()
            elif hasattr(widget, 'line_edit'): # For file input containers
                 values[name] = widget.line_edit.text()
        return values
