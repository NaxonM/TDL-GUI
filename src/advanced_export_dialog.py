from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QDialogButtonBox,
    QGroupBox,
)


class AdvancedExportDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Export Options")
        self.setMinimumWidth(500)

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)

        group = QGroupBox("Advanced Filtering")
        form_layout = QFormLayout(group)

        self.export_filter_input = QLineEdit()
        self.export_filter_input.setPlaceholderText("e.g., 'IsPhoto && HasViews'")
        self.export_filter_input.setToolTip(
            "Filter messages using a powerful expression.\nSee tdl documentation for syntax."
        )

        self.export_reply_input = QLineEdit()
        self.export_reply_input.setPlaceholderText(
            "Export replies to a specific message ID"
        )
        self.export_reply_input.setToolTip(
            "Only export messages that are replies to this specific message ID."
        )

        self.export_topic_input = QLineEdit()
        self.export_topic_input.setPlaceholderText(
            "Export from a specific topic/forum ID"
        )
        self.export_topic_input.setToolTip(
            "For groups with Topics enabled, export messages from a specific topic ID."
        )

        form_layout.addRow("Filter Expression:", self.export_filter_input)
        form_layout.addRow("Replies to Message ID:", self.export_reply_input)
        form_layout.addRow("Topic ID:", self.export_topic_input)

        layout.addWidget(group)

        # OK and Cancel buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_settings(self):
        return {
            "filter": self.export_filter_input.text(),
            "reply": self.export_reply_input.text(),
            "topic": self.export_topic_input.text(),
        }
