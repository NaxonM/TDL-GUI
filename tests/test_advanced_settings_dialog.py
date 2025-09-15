import os
import sys
import unittest
from unittest.mock import MagicMock

# Add src to path to allow importing
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# We need a QApplication instance to be able to instantiate QWidgets
from PyQt6.QtWidgets import QApplication
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

from src.advanced_settings_dialog import AdvancedSettingsDialog

class TestAdvancedSettingsDialog(unittest.TestCase):

    def setUp(self):
        self.dialog = AdvancedSettingsDialog()

    def test_get_settings_default_template(self):
        """Tests that the 'Default: ' prefix is correctly stripped."""
        # The default selection is the one with the prefix
        settings = self.dialog.get_settings()
        self.assertEqual(settings['template'], "{{ .DialogID }}_{{ .MessageID }}_{{ filenamify .FileName }}")

    def test_get_settings_other_predefined_template(self):
        """Tests a predefined template without any prefix."""
        self.dialog.template_combo.setCurrentText("{{ .FileName }}")
        settings = self.dialog.get_settings()
        self.assertEqual(settings['template'], "{{ .FileName }}")

    def test_get_settings_custom_template(self):
        """Tests the 'Custom...' template option."""
        self.dialog.template_combo.setCurrentText("Custom...")
        self.dialog.template_input.setText("MyCustom/{{.FileName}}")
        settings = self.dialog.get_settings()
        self.assertEqual(settings['template'], "MyCustom/{{.FileName}}")

    def test_get_settings_other_values(self):
        """Tests that other settings are also retrieved correctly."""
        self.dialog.concurrent_tasks_spinbox.setValue(10)
        self.dialog.skip_same_checkbox.setChecked(False)
        self.dialog.include_ext_input.setText("mkv,mp4")

        settings = self.dialog.get_settings()
        self.assertEqual(settings['concurrent_tasks'], 10)
        self.assertEqual(settings['skip_same'], False)
        self.assertEqual(settings['include_exts'], "mkv,mp4")

if __name__ == '__main__':
    unittest.main()
