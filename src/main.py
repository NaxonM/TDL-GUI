import sys
import sys
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtGui import QPalette
from main_window import MainWindow
from tdl_manager import ensure_tdl_executable

# --- STYLESHEETS ---

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


def main():
    app = QApplication(sys.argv)

    # Detect theme and apply stylesheet
    is_dark_theme = app.palette().color(QPalette.ColorRole.Window).lightness() < 128
    theme_name = 'dark' if is_dark_theme else 'light'

    if is_dark_theme:
        app.setStyleSheet(DARK_STYLESHEET)
    else:
        app.setStyleSheet(LIGHT_STYLESHEET)

    # Ensure tdl executable is available
    tdl_path = ensure_tdl_executable(app_parent=None) # Pass a parent? maybe later
    if not tdl_path:
        # The manager shows its own error message
        sys.exit(1)

    window = MainWindow(theme=theme_name, tdl_path=tdl_path)
    window.show()

    sys.exit(app.exec())

if __name__ == '__main__':
    main()
