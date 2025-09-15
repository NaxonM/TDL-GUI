import sys
import os
from tdl_manager import TdlManager
from worker import InitialSetupWorker
from settings_manager import SettingsManager
from logger import initialize_logger
from theme_manager import ThemeManager

# --- UI Imports ---
from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressDialog
from PyQt6.QtGui import QPalette
from PyQt6.QtCore import Qt, QTimer


class AppController:
    def __init__(self, app, settings_manager, theme_name="light"):
        self.app = app
        self.settings_manager = settings_manager
        self.theme_name = theme_name
        self.main_window = None
        self.logger = initialize_logger(self.settings_manager)

    def start(self):
        self.logger.info("Application starting...")
        self.manager = TdlManager()
        tdl_path, status = self.manager.check_for_tdl()

        if status == "not_found":
            self.run_initial_setup()
        else:
            self.launch_main_window(tdl_path)

    def run_initial_setup(self):
        reply = QMessageBox.information(
            None,
            "TDL Not Found",
            "The 'tdl' command-line tool was not found.\nA local copy will be downloaded automatically.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Ok,
        )
        if reply == QMessageBox.StandardButton.Cancel:
            sys.exit(0)

        self.progress_dialog = QProgressDialog(
            "Downloading tdl...", "Cancel", 0, 100, None
        )
        self.progress_dialog.setWindowModality(Qt.WindowModality.WindowModal)
        self.progress_dialog.setWindowTitle("Setup")

        self.setup_worker = InitialSetupWorker(self.manager)
        self.setup_worker.progress.connect(self.update_progress)
        self.setup_worker.success.connect(self.on_setup_success)
        self.setup_worker.failure.connect(self.on_setup_failure)
        self.progress_dialog.canceled.connect(self.setup_worker.terminate)

        self.setup_worker.start()
        self.progress_dialog.exec()

    def update_progress(self, current, total):
        if total > 0:
            self.progress_dialog.setMaximum(total)
            self.progress_dialog.setValue(current)
        else:  # Show a busy indicator if total size is unknown
            self.progress_dialog.setMaximum(0)
            self.progress_dialog.setValue(0)

    def on_setup_success(self, tdl_path):
        self.progress_dialog.close()
        QMessageBox.information(
            None, "Setup Complete", "tdl has been downloaded successfully."
        )
        self.launch_main_window(tdl_path)

    def on_setup_failure(self, error_message):
        self.progress_dialog.close()
        QMessageBox.critical(
            None, "Setup Error", f"Failed to set up tdl:\n\n{error_message}"
        )
        sys.exit(1)

    def launch_main_window(self, tdl_path):
        # Dynamically import MainWindow to avoid circular dependencies if it ever needs the app controller
        from main_window import MainWindow

        self.main_window = MainWindow(
            app=self.app,
            tdl_path=tdl_path,
            settings_manager=self.settings_manager,
            logger=self.logger,
            theme=self.theme_name,
        )
        self.main_window.show()


def main():
    app = QApplication(sys.argv)

    settings_manager = SettingsManager()
    theme_manager = ThemeManager()

    theme_name = settings_manager.get("theme", "light")
    stylesheet = theme_manager.get_stylesheet(theme_name)
    app.setStyleSheet(stylesheet)

    controller = AppController(app, settings_manager, theme_name)

    # Use a QTimer to start the controller after the event loop has started.
    # This ensures that the initial QMessageBox and QProgressDialog are properly displayed.
    QTimer.singleShot(10, controller.start)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
