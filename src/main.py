import sys
import os
from tdl_manager import TdlManager
from worker import InitialSetupWorker

# --- UI Imports ---
from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressDialog
from PyQt6.QtGui import QPalette
from PyQt6.QtCore import Qt, QTimer

# --- STYLESHEETS (remain the same) ---
LIGHT_STYLESHEET = """
    QWidget {
        background-color: #FDFEFE;
        color: #17202A;
        font-size: 14px;
        font-family: "Segoe UI", "Roboto", "Helvetica Neue", sans-serif;
    }
    QMainWindow, QDialog {
        background-color: #F2F4F4;
    }
    QGroupBox {
        background-color: #FBFCFC;
        border: 1px solid #D5DBDB;
        border-radius: 5px;
        margin-top: 1ex;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        background-color: transparent;
    }
    QLineEdit, QPlainTextEdit, QSpinBox, QDateEdit, QComboBox {
        padding: 5px;
        border: 1px solid #BFC9CA;
        border-radius: 4px;
        background-color: #FFFFFF;
    }
    QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDateEdit:focus, QComboBox:focus {
        border: 1px solid #5DADE2;
    }
    QPushButton, QToolButton {
        background-color: #3498DB;
        color: white;
        border-radius: 4px;
        padding: 6px 12px;
        font-weight: bold;
        border: 1px solid #2874A6;
    }
    QToolButton {
        padding: 4px;
    }
    QPushButton:hover, QToolButton:hover {
        background-color: #2E86C1;
    }
    QPushButton:pressed, QToolButton:pressed {
        background-color: #2874A6;
    }
    QPushButton:disabled, QToolButton:disabled {
        background-color: #BDC3C7;
        color: #7F8C8D;
        border: 1px solid #AAB1B5;
    }
    QProgressBar {
        border: 1px solid #BFC9CA;
        border-radius: 5px;
        text-align: center;
        background-color: #E5E8E8;
    }
    QProgressBar::chunk {
        background-color: #3498DB;
        border-radius: 4px;
    }
    QTabBar::tab {
        background: #EAECEE;
        border: 1px solid #D5DBDB;
        border-bottom: none;
        padding: 6px 10px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background: #FBFCFC;
        border-color: #D5DBDB;
    }
    QTabBar::tab:!selected:hover {
        background: #ECF0F1;
    }
    QTabWidget::pane {
        border: 1px solid #D5DBDB;
    }
    QScrollBar:vertical {
        border: 1px solid #D5DBDB;
        background: #F2F4F4;
        width: 15px;
        margin: 15px 0 15px 0;
    }
    QScrollBar::handle:vertical {
        background: #BDC3C7;
        min-height: 20px;
        border-radius: 4px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
"""

DARK_STYLESHEET = """
    QWidget {
        background-color: #2E3440;
        color: #D8DEE9;
        font-size: 14px;
        font-family: "Segoe UI", "Roboto", "Helvetica Neue", sans-serif;
    }
    QMainWindow, QDialog {
        background-color: #242933;
    }
    QGroupBox {
        background-color: #3B4252;
        border: 1px solid #4C566A;
        border-radius: 5px;
        margin-top: 1ex;
        font-weight: bold;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 5px;
        background-color: transparent;
    }
    QLineEdit, QPlainTextEdit, QSpinBox, QDateEdit, QComboBox {
        padding: 5px;
        border: 1px solid #4C566A;
        border-radius: 4px;
        background-color: #2E3440;
        color: #ECEFF4;
    }
    QLineEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QDateEdit:focus, QComboBox:focus {
        border: 1px solid #81A1C1;
    }
    QPushButton, QToolButton {
        background-color: #5E81AC;
        color: #ECEFF4;
        border-radius: 4px;
        padding: 6px 12px;
        font-weight: bold;
        border: 1px solid #4C566A;
    }
    QToolButton {
        padding: 4px;
    }
    QPushButton:hover, QToolButton:hover {
        background-color: #81A1C1;
    }
    QPushButton:pressed, QToolButton:pressed {
        background-color: #4C566A;
    }
    QPushButton:disabled, QToolButton:disabled {
        background-color: #4C566A;
        color: #6B7A90;
        border: 1px solid #434C5E;
    }
    QProgressBar {
        border: 1px solid #4C566A;
        border-radius: 5px;
        text-align: center;
        background-color: #2E3440;
        color: #D8DEE9;
    }
    QProgressBar::chunk {
        background-color: #5E81AC;
        border-radius: 4px;
    }
    QTabBar::tab {
        background: #3B4252;
        border: 1px solid #434C5E;
        border-bottom: none;
        padding: 6px 10px;
        border-top-left-radius: 4px;
        border-top-right-radius: 4px;
    }
    QTabBar::tab:selected {
        background: #434C5E;
        border-color: #4C566A;
    }
    QTabBar::tab:!selected:hover {
        background: #4C566A;
    }
    QTabWidget::pane {
        border: 1px solid #4C566A;
    }
    QScrollBar:vertical {
        border: 1px solid #434C5E;
        background: #2E3440;
        width: 15px;
        margin: 15px 0 15px 0;
    }
    QScrollBar::handle:vertical {
        background: #4C566A;
        min-height: 20px;
        border-radius: 4px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
        height: 0px;
    }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
        background: none;
    }
"""

class AppController:
    def __init__(self, app):
        self.app = app
        self.main_window = None
        self.theme_name = 'light'

    def start(self):
        self.manager = TdlManager()
        tdl_path, status = self.manager.check_for_tdl()

        if status == 'not_found':
            self.run_initial_setup()
        else:
            self.launch_main_window(tdl_path)

    def run_initial_setup(self):
        reply = QMessageBox.information(
            None, "TDL Not Found",
            "The 'tdl' command-line tool was not found.\nA local copy will be downloaded automatically.",
            QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Ok
        )
        if reply == QMessageBox.StandardButton.Cancel:
            sys.exit(0)

        self.progress_dialog = QProgressDialog("Downloading tdl...", "Cancel", 0, 100, None)
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
        else: # Show a busy indicator if total size is unknown
            self.progress_dialog.setMaximum(0)
            self.progress_dialog.setValue(0)

    def on_setup_success(self, tdl_path):
        self.progress_dialog.close()
        QMessageBox.information(None, "Setup Complete", "tdl has been downloaded successfully.")
        self.launch_main_window(tdl_path)

    def on_setup_failure(self, error_message):
        self.progress_dialog.close()
        QMessageBox.critical(None, "Setup Error", f"Failed to set up tdl:\n\n{error_message}")
        sys.exit(1)

    def launch_main_window(self, tdl_path):
        # Dynamically import MainWindow to avoid circular dependencies if it ever needs the app controller
        from main_window import MainWindow
        self.main_window = MainWindow(theme=self.theme_name, tdl_path=tdl_path)
        self.main_window.show()


def main():
    app = QApplication(sys.argv)

    is_dark_theme = app.palette().color(QPalette.ColorRole.Window).lightness() < 128
    app.setStyleSheet(DARK_STYLESHEET if is_dark_theme else LIGHT_STYLESHEET)

    controller = AppController(app)
    controller.theme_name = 'dark' if is_dark_theme else 'light'

    # Use a QTimer to start the controller after the event loop has started.
    # This ensures that the initial QMessageBox and QProgressDialog are properly displayed.
    QTimer.singleShot(10, controller.start)

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
