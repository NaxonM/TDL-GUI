import sys
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QDialogButtonBox, QMessageBox
)
from PyQt6.QtCore import pyqtSignal
from login_worker import LoginWorker

class LoginDialog(QDialog):
    def __init__(self, tdl_path, namespace, settings, parent=None):
        super().__init__(parent)
        self.tdl_path = tdl_path
        self.namespace = namespace
        self.settings = settings.copy()

        self.setWindowTitle(f"Interactive Login for '{namespace}'")
        self.setMinimumWidth(450)

        layout = QVBoxLayout(self)

        self.prompt_label = QLabel("Starting login process...")
        self.prompt_label.setWordWrap(True)

        self.input_line_edit = QLineEdit()
        self.input_line_edit.setPlaceholderText("Enter information here")
        self.input_line_edit.returnPressed.connect(self._on_submit) # Allow pressing Enter

        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self._on_submit)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.prompt_label)
        layout.addWidget(self.input_line_edit)
        layout.addWidget(self.submit_button)
        layout.addWidget(self.button_box)

        self.input_line_edit.hide()
        self.submit_button.hide()

        self.worker = LoginWorker(self.tdl_path, self.namespace, self.settings)
        self.worker.prompt_detected.connect(self._on_prompt)
        self.worker.login_success.connect(self._on_login_success)
        self.worker.login_failed.connect(self._on_login_failed)
        self.worker.log_message.connect(self._on_log_message)
        self.worker.finished.connect(self._on_worker_finished)

        self.worker.start()

    def _on_prompt(self, prompt_text):
        """Handles a prompt detected from the tdl tool."""
        self.prompt_label.setText(prompt_text.replace('?', '').strip())

        # Make input visible
        self.input_line_edit.show()
        self.submit_button.show()
        self.input_line_edit.setFocus()

        # Check for password prompt to hide input
        if "password" in prompt_text.lower():
            self.input_line_edit.setEchoMode(QLineEdit.EchoMode.Password)
        else:
            self.input_line_edit.setEchoMode(QLineEdit.EchoMode.Normal)

    def _on_login_success(self):
        """Handles the successful login signal."""
        QMessageBox.information(self, "Success", "Login was successful!")
        self.accept()

    def _on_login_failed(self, error_message):
        """Handles the login failed signal."""
        # This can be noisy, so we might want to filter some errors
        if "finished with a non-zero exit code" in error_message and self.isFinished():
            return # Ignore this if we already handled success/failure

        QMessageBox.critical(self, "Login Failed", f"The login process failed:\n\n{error_message}")
        self.reject()

    def _on_log_message(self, message):
        """For debugging, prints log messages from the worker."""
        print(f"[LoginDialog Log] {message}")

    def _on_submit(self):
        """Sends the user's input to the worker."""
        user_input = self.input_line_edit.text()
        if not user_input:
            return

        self.worker.send_input(user_input)
        self.input_line_edit.clear()
        self.input_line_edit.hide()
        self.submit_button.hide()
        self.prompt_label.setText("Processing...")

    def _on_worker_finished(self):
        """Cleans up when the worker thread is finished."""
        self.submit_button.setEnabled(False)
        self.input_line_edit.setEnabled(False)

    def reject(self):
        """Ensures the worker is stopped when the dialog is cancelled."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        super().reject()
