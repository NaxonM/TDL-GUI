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

from src.download_tab import DownloadTab

class TestDownloadTab(unittest.TestCase):

    def setUp(self):
        # Mock the dependencies for DownloadTab
        self.mock_tdl_runner = MagicMock()
        self.mock_settings_manager = MagicMock()
        self.mock_logger = MagicMock()

        self.tab = DownloadTab(
            tdl_runner=self.mock_tdl_runner,
            settings_manager=self.mock_settings_manager,
            logger=self.mock_logger,
        )

    def test_set_running_state(self):
        """Tests that controls are enabled/disabled correctly."""
        # --- Test when a download starts (is_running = True) ---
        self.tab.set_running_state(True)

        # The start/stop button should REMAIN ENABLED to allow stopping
        self.assertTrue(self.tab.start_download_button.isEnabled())
        self.assertEqual(self.tab.start_download_button.text(), "Stop Download")

        # Other controls should be disabled
        self.assertFalse(self.tab.source_input.isEnabled())
        self.assertFalse(self.tab.dest_path_input.isEnabled())
        self.assertFalse(self.tab.advanced_settings_button.isEnabled())

        # --- Test when a download finishes (is_running = False) ---
        self.tab.set_running_state(False)

        # The start/stop button should be enabled
        self.assertTrue(self.tab.start_download_button.isEnabled())
        self.assertEqual(self.tab.start_download_button.text(), "Start Download")

        # Other controls should be re-enabled
        self.assertTrue(self.tab.source_input.isEnabled())
        self.assertTrue(self.tab.dest_path_input.isEnabled())
        self.assertTrue(self.tab.advanced_settings_button.isEnabled())

if __name__ == '__main__':
    unittest.main()
