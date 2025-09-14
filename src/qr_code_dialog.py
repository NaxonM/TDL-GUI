from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QDialogButtonBox, QMessageBox
)
from PyQt6.QtGui import QFontDatabase
from PyQt6.QtCore import Qt
from login_worker import LoginWorker

class QRCodeDialog(QDialog):
    def __init__(self, tdl_path, namespace, settings_manager, logger, parent=None):
        super().__init__(parent)
        self.tdl_path = tdl_path
        self.namespace = namespace
        self.settings_manager = settings_manager
        self.logger = logger

        self.setWindowTitle("Login with QR Code")
        self.setMinimumSize(500, 400)

        layout = QVBoxLayout(self)

        self.info_label = QLabel("Generating QR code, please wait...")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.qr_code_display = QPlainTextEdit()
        self.qr_code_display.setReadOnly(True)
        font = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        self.qr_code_display.setFont(font)
        self.qr_code_display.hide() # Hide until QR is ready

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.info_label)
        layout.addWidget(self.qr_code_display)
        layout.addWidget(self.button_box)

        self.worker = LoginWorker(self.tdl_path, self.namespace, self.settings_manager, self.logger, mode='qr')
        self.worker.qr_code_ready.connect(self._on_qr_code_ready)
        self.worker.login_success.connect(self._on_login_success)
        self.worker.login_failed.connect(self._on_login_failed)
        self.worker.finished.connect(self._on_worker_finished)
        self.worker.start()

    def _on_qr_code_ready(self, qr_text):
        """Displays the captured QR code text."""
        self.info_label.setText("Scan the QR code below using your Telegram app.")
        self.qr_code_display.show()
        # Clean up the text a bit, remove the cursor-up ANSI codes and other noise
        lines = qr_text.split('\n')
        cleaned_lines = [line for line in lines if '?' not in line and 'Scan' not in line and 'WARN' not in line]
        cleaned_text = "\n".join(cleaned_lines).replace('\x1b[A', '')
        self.qr_code_display.setPlainText(cleaned_text)

    def _on_login_success(self):
        QMessageBox.information(self, "Success", "Login via QR code was successful!")
        self.accept()

    def _on_login_failed(self, error_message):
        if not self.isVisible(): return # Don't show error if dialog is already closed
        QMessageBox.critical(self, "Login Failed", f"The QR code login process failed:\n\n{error_message}")
        self.reject()

    def _on_worker_finished(self):
        self.info_label.setText("Login process finished.")

    def reject(self):
        """Ensures the worker is stopped when the dialog is closed."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        super().reject()
