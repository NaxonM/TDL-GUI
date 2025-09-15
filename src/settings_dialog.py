import os
import shutil
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QTabWidget,
    QWidget,
    QFormLayout,
    QGroupBox,
    QComboBox,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QHBoxLayout,
    QDialogButtonBox,
    QFileDialog,
    QInputDialog,
    QMessageBox,
    QSpinBox,
    QLabel,
)
from PyQt6.QtCore import QDir, pyqtSignal
from .login_dialog import LoginDialog
from .qr_code_dialog import QRCodeDialog
from .settings_manager import SettingsManager
from .theme_manager import ThemeManager


class SettingsDialog(QDialog):
    desktop_login_requested = pyqtSignal(str, str)

    def __init__(self, tdl_path, settings_manager, parent=None):
        super().__init__(parent)
        self.tdl_path = tdl_path
        self.settings_manager = settings_manager
        # Assuming the parent is MainWindow which has the logger
        self.logger = parent.logger if parent and hasattr(parent, "logger") else None
        self.original_theme = self.settings_manager.get("theme", "light")

        self.setWindowTitle("Global Settings & Login")
        self.setMinimumWidth(500)

        main_layout = QVBoxLayout(self)

        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        self.theme_manager = ThemeManager()

        tabs.addTab(self._create_account_tab(), "Account")
        tabs.addTab(self._create_appearance_tab(), "Appearance")
        tabs.addTab(self._create_network_tab(), "Network")
        tabs.addTab(self._create_storage_tab(), "Storage")
        tabs.addTab(self._create_debug_tab(), "Debug")

        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)

        self.load_settings()

    def _create_account_tab(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        account_group = QGroupBox("Account Management")
        account_layout = QHBoxLayout()

        self.account_combo = QComboBox()
        self.account_combo.setToolTip("Select the active account (namespace).")

        self.rename_button = QPushButton("Rename")
        self.rename_button.setToolTip("Rename the selected account.")
        self.rename_button.clicked.connect(self._rename_account)

        self.remove_button = QPushButton("Remove")
        self.remove_button.setToolTip("Remove the selected account.")
        self.remove_button.clicked.connect(self._remove_account)
        self.account_combo.currentTextChanged.connect(self._update_account_buttons)

        account_layout.addWidget(QLabel("Active Account:"))
        account_layout.addWidget(self.account_combo, 1)
        account_layout.addWidget(self.rename_button)
        account_layout.addWidget(self.remove_button)

        account_group.setLayout(account_layout)
        layout.addWidget(account_group)

        login_group = QGroupBox("Login Methods")
        login_layout = QVBoxLayout()

        login_button = QPushButton("Login to New Account (Phone & Code)")
        login_button.clicked.connect(self._handle_code_login_click)

        desktop_login_button = QPushButton("Login from Desktop Client")
        desktop_login_button.setToolTip(
            "Import a login session from an existing Telegram Desktop installation."
        )
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

    def _create_appearance_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)

        theme_group = QGroupBox("Application Theme")
        theme_layout = QFormLayout()

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(self.theme_manager.get_theme_names())
        self.theme_combo.setToolTip(
            "Select the visual theme for the application.\nA restart is required for changes to take full effect."
        )

        theme_layout.addRow("Theme:", self.theme_combo)

        restart_label = QLabel(
            "<i>A restart is required for the theme to fully apply.</i>"
        )
        restart_label.setWordWrap(True)

        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        layout.addWidget(restart_label)

        return widget

    def _create_network_tab(self):
        widget = QWidget()
        layout = QFormLayout(widget)
        proxy_group = QGroupBox("Proxy Settings")
        proxy_layout = QFormLayout()
        self.auto_proxy_checkbox = QCheckBox("Automatically detect system proxy")
        self.auto_proxy_checkbox.setToolTip(
            "If checked, tdl-gui will attempt to use the proxy configured in your operating system.\nThis is the recommended setting."
        )
        self.auto_proxy_checkbox.setChecked(True)
        self.manual_proxy_input = QLineEdit()
        self.manual_proxy_input.setPlaceholderText("protocol://user:pass@host:port")
        self.manual_proxy_input.setToolTip(
            "If automatic detection is off, specify the full proxy URL here.\nExample: socks5://127.0.0.1:1080"
        )
        self.manual_proxy_input.setEnabled(False)
        self.auto_proxy_checkbox.toggled.connect(
            lambda checked: self.manual_proxy_input.setEnabled(not checked)
        )
        proxy_layout.addRow(self.auto_proxy_checkbox)
        proxy_layout.addRow("Manual Proxy:", self.manual_proxy_input)
        proxy_group.setLayout(proxy_layout)
        layout.addWidget(proxy_group)

        tuning_group = QGroupBox("Connection Tuning")
        tuning_layout = QFormLayout()
        self.ntp_server_input = QLineEdit()
        self.ntp_server_input.setPlaceholderText("e.g., time.google.com")
        self.ntp_server_input.setToolTip(
            "Optional: Specify a custom NTP server to sync time with.\nThis can help with login issues in some networks."
        )

        timeout_layout = QHBoxLayout()
        self.reconnect_timeout_spinbox = QSpinBox()
        self.reconnect_timeout_spinbox.setRange(0, 999)
        self.reconnect_timeout_spinbox.setToolTip(
            "How long to wait before trying to reconnect if the connection to Telegram is lost.\nSet to 0 for infinite."
        )
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
        self.storage_driver_combo.setToolTip(
            "The storage driver to use for the session."
        )
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
        self.debug_mode_checkbox.setToolTip(
            "Greatly increases the amount of information in the Log tab and app.log file.\nUseful for troubleshooting."
        )
        self.timeout_spinbox = QSpinBox()
        self.timeout_spinbox.setRange(0, 86400)
        self.timeout_spinbox.setSuffix(" s")
        self.timeout_spinbox.setToolTip(
            "Maximum time to wait for any tdl command to complete.\nSet to 0 for no timeout (not recommended)."
        )
        debug_layout.addRow(self.debug_mode_checkbox)
        debug_layout.addRow("Command Timeout:", self.timeout_spinbox)
        layout.addWidget(debug_group)

        danger_zone_group = QGroupBox("Danger Zone")
        danger_zone_layout = QVBoxLayout(danger_zone_group)

        reset_settings_button = QPushButton("Reset UI Settings")
        reset_settings_button.setToolTip(
            "Resets all settings in this dialog to their defaults."
        )
        reset_settings_button.clicked.connect(self._handle_reset_settings)

        reset_data_button = QPushButton("Reset All TDL Data")
        reset_data_button.setStyleSheet(
            "background-color: #D32F2F; border-color: #B71C1C;"
        )
        reset_data_button.setToolTip(
            "Deletes all tdl data, including login sessions and logs."
        )
        reset_data_button.clicked.connect(self._handle_reset_data)

        danger_zone_layout.addWidget(reset_settings_button)
        danger_zone_layout.addWidget(reset_data_button)
        layout.addWidget(danger_zone_group)

        layout.addStretch()
        return widget

    def _handle_reset_settings(self):
        reply = QMessageBox.warning(
            self,
            "Confirm Reset",
            "This will reset all UI settings to their default values. Your accounts and login data will not be affected.\n\nAre you sure you want to continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.reset_ui_settings()
            self.load_settings()
            QMessageBox.information(
                self,
                "Settings Reset",
                "UI settings have been reset to their defaults.\nThe theme will update on restart.",
            )

    def _handle_reset_data(self):
        tdl_dir = os.path.expanduser("~/.tdl")
        reply = QMessageBox.warning(
            self,
            "Confirm Reset",
            f"This will permanently delete the entire TDL data directory, including all accounts, sessions, and logs.\n\nDirectory to be deleted:\n{tdl_dir}\n\n<b>This action cannot be undone.</b> Are you absolutely sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if os.path.exists(tdl_dir):
                    shutil.rmtree(tdl_dir)
                    QMessageBox.information(
                        self, "Success", f"Successfully deleted {tdl_dir}."
                    )
                else:
                    QMessageBox.information(
                        self, "Not Found", f"The directory {tdl_dir} does not exist."
                    )
                self._populate_accounts()
                self.account_combo.setCurrentText("default")
                self.settings["namespace"] = "default"
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete directory: {e}")

    def _update_account_buttons(self, text):
        """Enable/disable account management buttons based on the selected account."""
        is_default = text == "default"
        self.rename_button.setEnabled(not is_default)
        self.remove_button.setEnabled(not is_default)

    def _browse_storage_path(self):
        directory = QFileDialog.getExistingDirectory(
            self, "Select Storage Directory", QDir.homePath()
        )
        if directory:
            self.storage_path_input.setText(directory)

    def _rename_account(self):
        current_name = self.account_combo.currentText()
        if not current_name or current_name == "default":
            QMessageBox.warning(
                self, "Rename Not Allowed", "The 'default' account cannot be renamed."
            )
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Account",
            f"Enter a new name for '{current_name}':",
            text=current_name,
        )
        if not ok or not new_name.strip():
            return

        new_name = new_name.strip()
        if new_name == current_name:
            return

        existing_accounts = [
            self.account_combo.itemText(i) for i in range(self.account_combo.count())
        ]
        if new_name in existing_accounts:
            QMessageBox.warning(
                self, "Name Exists", f"An account named '{new_name}' already exists."
            )
            return

        storage_path = self._get_storage_path()
        old_file = os.path.join(storage_path, current_name)
        new_file = os.path.join(storage_path, new_name)

        try:
            if os.path.exists(old_file):
                os.rename(old_file, new_file)
                QMessageBox.information(
                    self,
                    "Success",
                    f"Account '{current_name}' has been renamed to '{new_name}'.",
                )
                self._populate_accounts()
                self.account_combo.setCurrentText(new_name)
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Could not find the data file for account '{current_name}'.",
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to rename account: {e}")

    def _remove_account(self):
        current_name = self.account_combo.currentText()
        if not current_name or current_name == "default":
            QMessageBox.warning(
                self, "Remove Not Allowed", "The 'default' account cannot be removed."
            )
            return

        reply = QMessageBox.warning(
            self,
            "Confirm Deletion",
            f"Are you sure you want to permanently delete the account '{current_name}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.No:
            return

        storage_path = self._get_storage_path()
        file_to_delete = os.path.join(storage_path, current_name)

        try:
            if os.path.exists(file_to_delete):
                os.remove(file_to_delete)
                QMessageBox.information(
                    self, "Success", f"Account '{current_name}' has been deleted."
                )
                self._populate_accounts()
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    f"Could not find the data file for account '{current_name}'.",
                )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to delete account: {e}")

    def _handle_code_login_click(self):
        text, ok = QInputDialog.getText(
            self, "New Account", "Enter a name for the new account (namespace):"
        )
        if ok and text.strip():
            namespace = text.strip()
            # Apply current UI settings to the manager before launching dialog
            self._apply_settings_from_ui()
            dialog = LoginDialog(
                self.tdl_path, namespace, self.settings_manager, self.logger, self
            )
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
            "Telegram Desktop (Telegram.exe)",
        )

        if not path:
            return

        passcode, ok = QInputDialog.getText(
            self,
            "Passcode",
            "Enter your local passcode if you have one:",
            QLineEdit.EchoMode.Password,
        )

        if ok:
            # We need to get the namespace first
            namespace, ok_ns = QInputDialog.getText(
                self, "New Account", "Enter a name for this account (namespace):"
            )
            if ok_ns and namespace.strip():
                self.desktop_login_requested.emit(path, passcode)
            else:
                QMessageBox.warning(
                    self, "Input Error", "A namespace is required to save the account."
                )

    def _handle_qr_login_click(self):
        text, ok = QInputDialog.getText(
            self, "New Account", "Enter a name for the new account (namespace):"
        )
        if ok and text.strip():
            namespace = text.strip()
            self._apply_settings_from_ui()
            dialog = QRCodeDialog(
                self.tdl_path, namespace, self.settings_manager, self.logger, self
            )
            if dialog.exec():
                self._populate_accounts()
                self.account_combo.setCurrentText(namespace)

    def _get_storage_path(self):
        path = self.settings_manager.get("storage_path", "").strip()
        if path:
            return path
        return os.path.expanduser("~/.tdl/data")

    def _populate_accounts(self):
        self.account_combo.clear()
        storage_path = self._get_storage_path()
        driver = self.settings_manager.get("storage_driver", "bolt")
        accounts = {"default"}
        if driver == "bolt" and os.path.isdir(storage_path):
            try:
                for f_name in os.listdir(storage_path):
                    f_path = os.path.join(storage_path, f_name)
                    if os.path.isfile(f_path) and "." not in f_name:
                        accounts.add(f_name)
            except FileNotFoundError:
                pass
        self.account_combo.addItems(sorted(list(accounts)))

    def load_settings(self):
        self.debug_mode_checkbox.setChecked(
            self.settings_manager.get("debug_mode", False)
        )
        self.storage_path_input.setText(self.settings_manager.get("storage_path", ""))
        self.auto_proxy_checkbox.setChecked(
            self.settings_manager.get("auto_proxy", True)
        )
        self.manual_proxy_input.setText(self.settings_manager.get("manual_proxy", ""))
        self.storage_driver_combo.setCurrentText(
            self.settings_manager.get("storage_driver", "bolt")
        )
        self.timeout_spinbox.setValue(self.settings_manager.get("command_timeout", 300))
        self.ntp_server_input.setText(self.settings_manager.get("ntp_server", ""))
        reconnect_timeout = self.settings_manager.get("reconnect_timeout", "5m")
        timeout_val = 0
        timeout_unit = "m"
        if reconnect_timeout and reconnect_timeout[:-1].isdigit():
            timeout_val = int(reconnect_timeout[:-1])
            timeout_unit = reconnect_timeout[-1]
        self.reconnect_timeout_spinbox.setValue(timeout_val)
        self.reconnect_timeout_unit_combo.setCurrentText(timeout_unit)
        self._populate_accounts()
        self.account_combo.setCurrentText(
            self.settings_manager.get("namespace", "default")
        )
        self.theme_combo.setCurrentText(self.settings_manager.get("theme", "light"))

    def _apply_settings_from_ui(self):
        """Applies the current UI values to the settings manager."""
        self.settings_manager.set("debug_mode", self.debug_mode_checkbox.isChecked())
        self.settings_manager.set("storage_path", self.storage_path_input.text())
        self.settings_manager.set("auto_proxy", self.auto_proxy_checkbox.isChecked())
        self.settings_manager.set("manual_proxy", self.manual_proxy_input.text())
        self.settings_manager.set(
            "storage_driver", self.storage_driver_combo.currentText()
        )
        self.settings_manager.set("namespace", self.account_combo.currentText())
        self.settings_manager.set("command_timeout", self.timeout_spinbox.value())
        self.settings_manager.set("ntp_server", self.ntp_server_input.text())
        timeout_val = self.reconnect_timeout_spinbox.value()
        timeout_unit = self.reconnect_timeout_unit_combo.currentText()
        self.settings_manager.set("reconnect_timeout", f"{timeout_val}{timeout_unit}")
        self.settings_manager.set("theme", self.theme_combo.currentText())

    def accept(self):
        new_theme = self.theme_combo.currentText()
        self._apply_settings_from_ui()

        if self.original_theme != new_theme:
            QMessageBox.information(
                self,
                "Theme Changed",
                "A restart is required for the new theme to be fully applied.",
            )
            # Try to apply the theme dynamically
            if self.parent() and hasattr(self.parent(), "app"):
                stylesheet = self.theme_manager.get_stylesheet(new_theme)
                self.parent().app.setStyleSheet(stylesheet)

        super().accept()
