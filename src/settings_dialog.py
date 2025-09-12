import os
import shutil
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QTabWidget, QWidget, QFormLayout, QGroupBox,
    QComboBox, QLineEdit, QCheckBox, QPushButton, QHBoxLayout, QDialogButtonBox,
    QFileDialog, QInputDialog, QMessageBox, QSpinBox
)
from PyQt6.QtCore import QDir, pyqtSignal
from login_dialog import LoginDialog
from qr_code_dialog import QRCodeDialog

class SettingsDialog(QDialog):
    desktop_login_requested = pyqtSignal(str, str)

    def __init__(self, tdl_path, current_settings, parent=None):
        super().__init__(parent)
        self.tdl_path = tdl_path
        self.settings = current_settings.copy()

        self.setWindowTitle("Global Settings & Login")
        self.setMinimumWidth(500)

        main_layout = QVBoxLayout(self)

        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        tabs.addTab(self._create_account_tab(), "Account")
        tabs.addTab(self._create_network_tab(), "Network")
        tabs.addTab(self._create_storage_tab(), "Storage")
        tabs.addTab(self._create_debug_tab(), "Debug")

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        self.load_settings()

    def _create_account_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        account_group = QGroupBox("Account Management")
        form_layout = QFormLayout()
        self.account_combo = QComboBox()
        form_layout.addRow("Active Account:", self.account_combo)
        account_group.setLayout(form_layout)
        layout.addWidget(account_group)

        login_group = QGroupBox("Login Methods")
        login_layout = QVBoxLayout()

        login_button = QPushButton("Login to New Account (Phone & Code)")
        login_button.clicked.connect(self._handle_code_login_click)

        desktop_login_button = QPushButton("Login from Desktop Client")
        desktop_login_button.setToolTip("Import a login session from an existing Telegram Desktop installation.")
        desktop_login_button.clicked.connect(self._handle_desktop_login_click)

        qr_login_button = QPushButton("Login with QR Code")
        qr_login_button.setToolTip("Login by scanning a QR code with your phone.")
        qr_login_button.clicked.connect(self._handle_qr_login_click)

        login_layout.addWidget(login_button)
        login_layout.addWidget(qr_login_button)
        login_layout.addWidget(desktop_login_button)

        login_group.setLayout(login_layout)
        layout.addWidget(login_group)
        layout.addStretch()
        return widget

    def _create_network_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        proxy_group = QGroupBox("Proxy Settings")
        proxy_layout = QFormLayout()
        self.auto_proxy_checkbox = QCheckBox("Automatically detect system proxy")
        self.auto_proxy_checkbox.setToolTip("Use the system's proxy settings.")
        self.auto_proxy_checkbox.setChecked(True)
        self.manual_proxy_input = QLineEdit()
        self.manual_proxy_input.setPlaceholderText("protocol://user:pass@host:port")
        self.manual_proxy_input.setToolTip("The proxy to use for all connections. Format: `protocol://username:password@host:port`")
        self.manual_proxy_input.setEnabled(False)
        self.auto_proxy_checkbox.toggled.connect(lambda checked: self.manual_proxy_input.setEnabled(not checked))
        proxy_layout.addRow(self.auto_proxy_checkbox)
        proxy_layout.addRow("Manual Proxy:", self.manual_proxy_input)
        proxy_group.setLayout(proxy_layout)
        layout.addWidget(proxy_group)

        tuning_group = QGroupBox("Connection Tuning")
        tuning_layout = QFormLayout()
        self.ntp_server_input = QLineEdit()
        self.ntp_server_input.setPlaceholderText("e.g., time.google.com")
        self.ntp_server_input.setToolTip("Optional NTP server for time synchronization.")

        timeout_layout = QHBoxLayout()
        self.reconnect_timeout_spinbox = QSpinBox()
        self.reconnect_timeout_spinbox.setRange(0, 999)
        self.reconnect_timeout_spinbox.setToolTip("Reconnection timeout. Set to 0 for infinite.")
        self.reconnect_timeout_unit_combo = QComboBox()
        self.reconnect_timeout_unit_combo.addItems(["s", "m", "h"])
        timeout_layout.addWidget(self.reconnect_timeout_spinbox, 1)
        timeout_layout.addWidget(self.reconnect_timeout_unit_combo)

        tuning_layout.addRow("NTP Server:", self.ntp_server_input)
        tuning_layout.addRow("Reconnect Timeout:", timeout_layout)
        tuning_group.setLayout(tuning_layout)
        layout.addWidget(tuning_group)

        return widget

    def _create_storage_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        storage_group = QGroupBox("Storage Configuration")
        storage_group.setToolTip(
            "This is an advanced setting.\n"
            "It controls where tdl saves session data (e.g., login info).\n"
            "This does NOT change your download folder.\n"
            "Leave the path blank to use the default location."
        )
        storage_layout = QFormLayout()
        self.storage_driver_combo = QComboBox()
        self.storage_driver_combo.setToolTip("The storage driver to use for the session.")
        self.storage_driver_combo.addItems(["bolt", "file", "legacy"])
        self.storage_driver_combo.setCurrentText("bolt")
        path_layout = QHBoxLayout()
        self.storage_path_input = QLineEdit()
        self.storage_path_input.setToolTip("The path to the storage file or directory.")
        self.browse_storage_button = QPushButton("...")
        self.browse_storage_button.clicked.connect(self._browse_storage_path)
        path_layout.addWidget(self.storage_path_input)
        path_layout.addWidget(self.browse_storage_button)
        storage_layout.addRow("Storage Driver:", self.storage_driver_combo)
        storage_layout.addRow("Storage Path:", path_layout)
        storage_group.setLayout(storage_layout)
        layout.addWidget(storage_group)
        return widget

    def _create_debug_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        debug_group = QGroupBox("Debug Options")
        debug_layout = QFormLayout(debug_group)
        self.debug_mode_checkbox = QCheckBox("Enable debug mode for verbose logging")
        self.debug_mode_checkbox.setToolTip("Enable debug level logging.")
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setRange(0, 86400)
        self.timeout_spinbox.setSuffix(" s")
        self.timeout_spinbox.setToolTip("Timeout for running commands. Set to 0 for no timeout.")
        debug_layout.addRow(self.debug_mode_checkbox)
        debug_layout.addRow("Command Timeout:", self.timeout_spinbox)
        layout.addWidget(debug_group)

        danger_zone_group = QGroupBox("Danger Zone")
        danger_zone_layout = QVBoxLayout(danger_zone_group)
        reset_button = QPushButton("Reset All TDL Data")
        reset_button.setStyleSheet("background-color: #D32F2F; border-color: #B71C1C;")
        reset_button.setToolTip("Deletes all tdl data, including login sessions and logs.")
        reset_button.clicked.connect(self._handle_reset_data)
        danger_zone_layout.addWidget(reset_button)
        layout.addWidget(danger_zone_group)

        layout.addStretch()
        return widget

    def _handle_reset_data(self):
        tdl_dir = os.path.expanduser('~/.tdl')
        reply = QMessageBox.warning(
            self, "Confirm Reset",
            f"This will permanently delete the entire TDL data directory, including all accounts, sessions, and logs.\n\nDirectory to be deleted:\n{tdl_dir}\n\n<b>This action cannot be undone.</b> Are you absolutely sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.exists(tdl_dir):
                    shutil.rmtree(tdl_dir)
                    QMessageBox.information(self, "Success", f"Successfully deleted {tdl_dir}.")
                else:
                    QMessageBox.information(self, "Not Found", f"The directory {tdl_dir} does not exist.")
                self._populate_accounts()
                self.account_combo.setCurrentText("default")
                self.settings['namespace'] = 'default'
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete directory: {e}")

    def _browse_storage_path(self):
        directory = QFileDialog.getExistingDirectory(self, "Select Storage Directory", QDir.homePath())
        if directory:
            self.storage_path_input.setText(directory)

    def _handle_code_login_click(self):
        text, ok = QInputDialog.getText(self, 'New Account', 'Enter a name for the new account (namespace):')
        if ok and text.strip():
            namespace = text.strip()
            # We need the current settings for proxy, etc.
            current_settings = self.get_current_settings()
            dialog = LoginDialog(self.tdl_path, namespace, current_settings, self)
            if dialog.exec():
                # Success, refresh the account list
                self._populate_accounts()
                self.account_combo.setCurrentText(namespace)

    def _handle_desktop_login_click(self):
        """Handles the logic for logging in from a desktop client."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Telegram Executable",
            "C:\\",
            "Telegram Desktop (Telegram.exe)"
        )

        if not path:
            return

        passcode, ok = QInputDialog.getText(
            self,
            "Passcode",
            "Enter your local passcode if you have one:",
            QLineEdit.EchoMode.Password
        )

        if ok:
            # We need to get the namespace first
            namespace, ok_ns = QInputDialog.getText(self, 'New Account', 'Enter a name for this account (namespace):')
            if ok_ns and namespace.strip():
                self.desktop_login_requested.emit(path, passcode)
            else:
                QMessageBox.warning(self, "Input Error", "A namespace is required to save the account.")

    def _handle_qr_login_click(self):
        text, ok = QInputDialog.getText(self, 'New Account', 'Enter a name for the new account (namespace):')
        if ok and text.strip():
            namespace = text.strip()
            current_settings = self.get_current_settings()
            dialog = QRCodeDialog(self.tdl_path, namespace, current_settings, self)
            if dialog.exec():
                self._populate_accounts()
                self.account_combo.setCurrentText(namespace)

    def _get_storage_path(self):
        path = self.settings.get('storage_path', '').strip()
        if path:
            return path
        return os.path.expanduser('~/.tdl/data')

    def _populate_accounts(self):
        self.account_combo.clear()
        storage_path = self._get_storage_path()
        driver = self.settings.get('storage_driver', 'bolt')
        accounts = {"default"}
        if driver == 'bolt' and os.path.isdir(storage_path):
            try:
                for f_name in os.listdir(storage_path):
                    f_path = os.path.join(storage_path, f_name)
                    if os.path.isfile(f_path) and '.' not in f_name:
                        accounts.add(f_name)
            except FileNotFoundError:
                pass
        self.account_combo.addItems(sorted(list(accounts)))

    def load_settings(self):
        self.debug_mode_checkbox.setChecked(self.settings.get('debug_mode', False))
        self.storage_path_input.setText(self.settings.get('storage_path', ''))
        self.auto_proxy_checkbox.setChecked(self.settings.get('auto_proxy', True))
        self.manual_proxy_input.setText(self.settings.get('manual_proxy', ''))
        self.storage_driver_combo.setCurrentText(self.settings.get('storage_driver', 'bolt'))
        self.timeout_spinbox.setValue(self.settings.get('command_timeout', 300))
        self.ntp_server_input.setText(self.settings.get('ntp_server', ''))
        reconnect_timeout = self.settings.get('reconnect_timeout', '5m')
        timeout_val = 0
        timeout_unit = 'm'
        if reconnect_timeout and reconnect_timeout[:-1].isdigit():
            timeout_val = int(reconnect_timeout[:-1])
            timeout_unit = reconnect_timeout[-1]
        self.reconnect_timeout_spinbox.setValue(timeout_val)
        self.reconnect_timeout_unit_combo.setCurrentText(timeout_unit)
        self._populate_accounts()
        self.account_combo.setCurrentText(self.settings.get('namespace', 'default'))

    def get_current_settings(self):
        """Returns a dictionary of the current settings in the dialog."""
        current = {}
        current['debug_mode'] = self.debug_mode_checkbox.isChecked()
        current['storage_path'] = self.storage_path_input.text()
        current['auto_proxy'] = self.auto_proxy_checkbox.isChecked()
        current['manual_proxy'] = self.manual_proxy_input.text()
        current['storage_driver'] = self.storage_driver_combo.currentText()
        current['namespace'] = self.account_combo.currentText()
        current['command_timeout'] = self.timeout_spinbox.value()
        current['ntp_server'] = self.ntp_server_input.text()
        timeout_val = self.reconnect_timeout_spinbox.value()
        timeout_unit = self.reconnect_timeout_unit_combo.currentText()
        current['reconnect_timeout'] = f"{timeout_val}{timeout_unit}"
        return current

    def accept(self):
        self.settings = self.get_current_settings()
        super().accept()
