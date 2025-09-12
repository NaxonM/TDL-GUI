import sys
import os
from tdl_manager import TdlManager

# --- UI Imports ---
# We delay these imports until we know we have a valid environment
QApplication = None
QMessageBox = None
QProgressDialog = None
QPalette = None
Qt = None
MainWindow = None

# --- STYLESHEETS ---
# (Stylesheets remain the same)
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
        border: 1px solid #D5DBDB;
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

def prepare_tdl_executable_cli():
    """
    Ensures TDL is available, using CLI prompts for interaction.
    Returns the path to the executable or None on failure.
    """
    manager = TdlManager()
    tdl_path, status = manager.check_for_tdl()

    if status == 'not_found':
        print("INFO: The 'tdl' command-line tool was not found.")
        # In a real CLI app, we'd prompt here. For this environment, we'll just proceed.
        print("INFO: A local copy will be downloaded automatically.")

        # Simple text-based progress bar
        def progress_callback(current, total):
            if total > 0:
                percent = int((current / total) * 100)
                bar_length = 40
                filled_length = int(bar_length * current // total)
                bar = '█' * filled_length + '-' * (bar_length - filled_length)
                print(f'\rDownloading... |{bar}| {percent}% Complete', end='', flush=True)

        tdl_path, error = manager.download_and_install_tdl(progress_callback)
        print() # Newline after progress bar

        if error:
            print(f"ERROR: Failed to set up tdl: {error}", file=sys.stderr)
            return None

    if not tdl_path:
        print("ERROR: Could not find or install the tdl executable.", file=sys.stderr)
        return None

    print(f"SUCCESS: tdl executable is ready at: {tdl_path}")
    return tdl_path

def main_gui(tdl_path):
    """Initializes and runs the main PyQt6 GUI application."""
    # Dynamically import PyQt6 components only when we're ready to launch the GUI
    global QApplication, QMessageBox, QProgressDialog, QPalette, Qt, MainWindow
    from PyQt6.QtWidgets import QApplication, QMessageBox, QProgressDialog
    from PyQt6.QtGui import QPalette
    from PyQt6.QtCore import Qt
    from main_window import MainWindow

    app = QApplication(sys.argv)

    is_dark_theme = app.palette().color(QPalette.ColorRole.Window).lightness() < 128
    theme_name = 'dark' if is_dark_theme else 'light'
    app.setStyleSheet(DARK_STYLESHEET if is_dark_theme else LIGHT_STYLESHEET)

    window = MainWindow(theme=theme_name, tdl_path=tdl_path)
    window.show()

    sys.exit(app.exec())


if __name__ == '__main__':
    # Step 1: Prepare the backend executable without any GUI code
    tdl_path = prepare_tdl_executable_cli()

    # Step 2: If preparation was successful, launch the GUI.
    # In a real user scenario, main_gui would be called.
    # In this headless environment, the script will exit after preparation.
    if tdl_path:
        # Check if we are in a headless environment.
        # The presence of certain environment variables can be a hint.
        if os.environ.get('DEBIAN_FRONTEND') == 'noninteractive' or 'CI' in os.environ:
             print("INFO: Headless environment detected. Skipping GUI launch.")
             sys.exit(0)
        else:
            main_gui(tdl_path)
    else:
        # Preparation failed
        sys.exit(1)
