import sys
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QDialogButtonBox,
    QMessageBox,
)
from PyQt6.QtCore import pyqtSignal, QRegularExpression
from PyQt6.QtGui import QRegularExpressionValidator
from src.login_worker import LoginWorker


class LoginDialog(QDialog):
    def __init__(self, tdl_path, namespace, settings_manager, logger, parent=None):
        super().__init__(parent)
        self.tdl_path = tdl_path
        self.namespace = namespace
        self.settings_manager = settings_manager
        self.logger = logger

        self.setWindowTitle(f"Interactive Login for '{namespace}'")
        self.setMinimumWidth(450)

        # --- Validators ---
        self.phone_validator = QRegularExpressionValidator(
            QRegularExpression(r"\+?\d+")
        )
        self.code_validator = QRegularExpressionValidator(QRegularExpression(r"\d+"))

        layout = QVBoxLayout(self)

        self.warning_label = QLabel()
        self.warning_label.setWordWrap(True)
        self.warning_label.setStyleSheet("color: #D32F2F; font-weight: bold;")
        self.warning_label.hide()

        self.status_label = QLabel("Starting login process...")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #757575;")  # A softer grey color

        self.prompt_label = QLabel()
        self.prompt_label.setWordWrap(True)
        self.prompt_label.hide()

        self.input_line_edit = QLineEdit()
        self.input_line_edit.setPlaceholderText("Enter information here")
        self.input_line_edit.returnPressed.connect(self._on_submit)
        self.input_line_edit.hide()

        self.submit_button = QPushButton("Submit")
        self.submit_button.clicked.connect(self._on_submit)
        self.submit_button.hide()
        self.submit_button.setDefault(True)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        # Prevent the cancel button from becoming the default
        cancel_button = self.button_box.button(QDialogButtonBox.StandardButton.Cancel)
        if cancel_button:
            cancel_button.setAutoDefault(False)
        self.button_box.rejected.connect(self.reject)

        layout.addWidget(self.warning_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.prompt_label)
        layout.addWidget(self.input_line_edit)
        layout.addWidget(self.submit_button)
        layout.addWidget(self.button_box)

        self.worker = LoginWorker(
            self.tdl_path, self.namespace, self.settings_manager, self.logger
        )
        self.worker.warning_detected.connect(self._on_warning)
        self.worker.status_update.connect(self._on_status_update)
        self.worker.prompt_for_input.connect(self._on_prompt)
        self.worker.login_success.connect(self._on_login_success)
        self.worker.login_failed.connect(self._on_login_failed)
        # self.worker.log_message.connect(self._on_log_message) # No longer needed
        self.worker.finished.connect(self._on_worker_finished)

        self.worker.start()

    def _on_warning(self, message):
        """Displays a warning message."""
        self.warning_label.setText(message)
        self.warning_label.show()

    def _on_status_update(self, message):
        """Displays a status message."""
        self.status_label.setText(message)
        self.status_label.show()
        # Hide prompt while status is active
        self.prompt_label.hide()
        self.input_line_edit.hide()
        self.submit_button.hide()

    def _on_prompt(self, prompt_type, prompt_text):
        """Handles a prompt for user input from the worker."""
        self.prompt_label.setText(prompt_text)
        self.prompt_label.show()

        self.status_label.hide()
        self.input_line_edit.show()
        self.submit_button.show()
        self.input_line_edit.setFocus()

        if prompt_type == "password":
            self.input_line_edit.setEchoMode(QLineEdit.EchoMode.Password)
            self.input_line_edit.setValidator(None)
        else:
            self.input_line_edit.setEchoMode(QLineEdit.EchoMode.Normal)

        if prompt_type == "phone":
            self.input_line_edit.setPlaceholderText("e.g. +12223334444")
            self.input_line_edit.setValidator(self.phone_validator)
        elif prompt_type == "code":
            self.input_line_edit.setPlaceholderText("e.g. 12345")
            self.input_line_edit.setValidator(self.code_validator)
        else:  # Default case, e.g. 2FA password
            self.input_line_edit.setPlaceholderText("Enter information here")
            self.input_line_edit.setValidator(None)

    def _on_login_success(self):
        """Handles the successful login signal."""
        QMessageBox.information(self, "Success", "Login was successful!")
        self.accept()

    def _on_login_failed(self, error_message):
        """Handles the login failed signal."""
        # This can be noisy, so we might want to filter some errors
        if "finished with a non-zero exit code" in error_message and self.isFinished():
            return  # Ignore this if we already handled success/failure

        QMessageBox.critical(
            self, "Login Failed", f"The login process failed:\n\n{error_message}"
        )
        self.reject()

    def _on_submit(self):
        """Sends the user's input to the worker."""
        user_input = self.input_line_edit.text()
        if not user_input.strip():
            QMessageBox.warning(self, "Input Error", "The input field cannot be empty.")
            return

        self.worker.send_input(user_input)
        self.input_line_edit.clear()

        # Hide input and show processing message
        self.prompt_label.hide()
        self.input_line_edit.hide()
        self.submit_button.hide()
        self.status_label.setText("Processing...")
        self.status_label.show()

    def _on_worker_finished(self):
        """Cleans up when the worker thread is finished."""
        self.submit_button.setEnabled(False)
        self.input_line_edit.setEnabled(False)

    def reject(self):
        """Ensures the worker is stopped when the dialog is cancelled."""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        super().reject()
