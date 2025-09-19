from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar


class DownloadProgressWidget(QWidget):
    """
    A custom widget to display detailed progress of a single file download.
    """

    def __init__(self, file_id, parent=None):
        super().__init__(parent)
        self.file_id = file_id

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(3, 3, 3, 3)
        main_layout.setSpacing(2)

        self.filename_label = QLabel(self.file_id)
        self.filename_label.setWordWrap(True)
        # Set object names for styling
        self.filename_label.setObjectName("filenameLabel")
        self.size_label = QLabel("Size: N/A")
        self.eta_label = QLabel("ETA: N/A")
        self.speed_label = QLabel("Speed: N/A")
        self.size_label.setObjectName("statsLabel")
        self.eta_label.setObjectName("statsLabel")
        self.speed_label.setObjectName("statsLabel")

        self.progress_bar = QProgressBar()
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 0, 0, 0)

        stats_layout.addWidget(self.size_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.eta_label)
        stats_layout.addStretch()
        stats_layout.addWidget(self.speed_label)

        main_layout.addWidget(self.filename_label)
        main_layout.addWidget(self.progress_bar)
        main_layout.addLayout(stats_layout)

        # Add a frame for better visual separation
        self.setContentsMargins(0, 0, 0, 0)

    def update_progress(self, data):
        """Updates the progress bar and labels with new data."""
        self.progress_bar.setValue(int(data["percent"]))
        self.size_label.setText(f"Size: {data['size_info']}")
        self.eta_label.setText(f"ETA: {data['eta']}")
        self.speed_label.setText(f"Speed: {data['speed']}")
