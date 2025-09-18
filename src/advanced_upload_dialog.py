from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QDialogButtonBox,
    QSpinBox,
    QLineEdit,
    QCheckBox,
    QGroupBox,
)

class AdvancedUploadDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Upload Options")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Concurrency settings
        concurrency_group = QGroupBox("Concurrency")
        concurrency_layout = QFormLayout(concurrency_group)
        self.threads_per_task_spinbox = QSpinBox()
        self.threads_per_task_spinbox.setRange(1, 16)
        self.threads_per_task_spinbox.setValue(4)
        self.threads_per_task_spinbox.setToolTip("Number of connections to use for each concurrent upload.")
        concurrency_layout.addRow("Threads per task:", self.threads_per_task_spinbox)

        self.concurrent_tasks_spinbox = QSpinBox()
        self.concurrent_tasks_spinbox.setRange(1, 16)
        self.concurrent_tasks_spinbox.setValue(4)
        self.concurrent_tasks_spinbox.setToolTip("Number of files to upload simultaneously.")
        concurrency_layout.addRow("Concurrent tasks:", self.concurrent_tasks_spinbox)

        # Filter settings
        filter_group = QGroupBox("Filters")
        filter_layout = QFormLayout(filter_group)
        self.exclude_exts_input = QLineEdit()
        self.exclude_exts_input.setPlaceholderText("e.g., .tmp .log .bak")
        self.exclude_exts_input.setToolTip("Space-separated list of file extensions to exclude.")
        filter_layout.addRow("Exclude extensions:", self.exclude_exts_input)

        # Other options
        options_group = QGroupBox("Options")
        options_layout = QVBoxLayout(options_group)
        self.delete_local_checkbox = QCheckBox("Delete local files after successful upload")
        self.delete_local_checkbox.setToolTip("Activates the --rm flag.")
        self.upload_as_photo_checkbox = QCheckBox("Upload images as photos (not documents)")
        self.upload_as_photo_checkbox.setToolTip("Activates the --photo flag.")
        options_layout.addWidget(self.delete_local_checkbox)
        options_layout.addWidget(self.upload_as_photo_checkbox)

        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)

        layout.addWidget(concurrency_group)
        layout.addWidget(filter_group)
        layout.addWidget(options_group)
        layout.addWidget(button_box)

    def get_settings(self):
        """Returns a dictionary of the selected settings."""
        return {
            "threads_per_task": self.threads_per_task_spinbox.value(),
            "concurrent_tasks": self.concurrent_tasks_spinbox.value(),
            "exclude_exts": self.exclude_exts_input.text().strip(),
            "delete_local": self.delete_local_checkbox.isChecked(),
            "upload_as_photo": self.upload_as_photo_checkbox.isChecked(),
        }
