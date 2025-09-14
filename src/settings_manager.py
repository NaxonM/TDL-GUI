import os
import json
from PyQt6.QtCore import QStandardPaths, QCoreApplication

class SettingsManager:
    """
    Manages loading and saving of application settings from a JSON file
    in a platform-appropriate application data directory.
    """
    def __init__(self, organization='tdl-gui', app_name='tdl-gui'):
        # Set organization and application name for QStandardPaths
        QCoreApplication.setOrganizationName(organization)
        QCoreApplication.setApplicationName(app_name)

        self.config_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppConfigLocation)
        self.settings_path = os.path.join(self.config_dir, 'settings.json')

        # Ensure the configuration directory exists
        os.makedirs(self.config_dir, exist_ok=True)

        self.defaults = {
            'theme': 'light',
            'debug_mode': False,
            'storage_path': '',
            'auto_proxy': True,
            'manual_proxy': '',
            'storage_driver': 'bolt',
            'namespace': 'default',
            'command_timeout': 300,
            'ntp_server': '',
            'reconnect_timeout': '5m'
        }
        self.settings = self.defaults.copy()
        self.load_settings()

    def load_settings(self):
        """Loads settings from the JSON file, merging with defaults."""
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, 'r') as f:
                    loaded_settings = json.load(f)
                    # Merge loaded settings with defaults to ensure all keys are present
                    self.settings.update(loaded_settings)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load settings from {self.settings_path}. Using defaults. Error: {e}")
            self.settings = self.defaults.copy()

    def save_settings(self):
        """Saves the current settings to the JSON file."""
        try:
            with open(self.settings_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except IOError as e:
            print(f"Error: Could not save settings to {self.settings_path}. Error: {e}")

    def get(self, key, default=None):
        """Gets a setting value by key."""
        return self.settings.get(key, default)

    def set(self, key, value):
        """Sets a setting value by key."""
        self.settings[key] = value

    def get_all(self):
        """Returns the entire settings dictionary."""
        return self.settings.copy()

    def update(self, new_settings_dict):
        """Updates the settings with a dictionary of new values."""
        self.settings.update(new_settings_dict)

    def reset_ui_settings(self):
        """Resets the settings to their default values and saves."""
        self.settings = self.defaults.copy()
        self.save_settings()
