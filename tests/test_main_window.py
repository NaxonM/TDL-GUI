import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication

from src.main_window import MainWindow
from src.settings_manager import SettingsManager

@pytest.fixture
def app(qtbot):
    """Fixture to create a mock application and main window."""
    test_app = QApplication.instance() or QApplication([])

    # Mock dependencies
    settings_manager = MagicMock(spec=SettingsManager)
    settings_manager.get.return_value = 'light' # Default theme

    logger = MagicMock()

    window = MainWindow(
        app=test_app,
        tdl_path='dummy_tdl',
        settings_manager=settings_manager,
        logger=logger,
        theme='light'
    )
    qtbot.addWidget(window)
    yield window
    window.close()

def test_main_window_creation(app):
    """Tests that the main window can be created without errors."""
    assert app.isVisible()
    assert app.windowTitle() == "tdl GUI"

def test_download_tab_exists(app):
    """Tests that the download tab is created and added."""
    assert app.download_tab is not None
    assert app.tabs.widget(0) == app.download_tab
    assert app.tabs.tabText(0) == "Download"

def test_export_tab_exists(app):
    """Tests that the export tab is created and added."""
    assert app.export_tab is not None
    assert app.tabs.widget(1) == app.export_tab
    assert app.tabs.tabText(1) == "Export"

def test_chats_tab_exists(app):
    """Tests that the chats tab is created and added."""
    assert app.chats_tab is not None
    assert app.tabs.widget(2) == app.chats_tab
    assert app.tabs.tabText(2) == "Chats"

def test_refresh_chats_button_click(app, qtbot, monkeypatch):
    """
    Tests that clicking the refresh button in the chats tab
    triggers the tdl_runner.
    """
    mock_runner = MagicMock()
    app.chats_tab.tdl_runner = mock_runner

    # Simulate a click
    qtbot.mouseClick(app.chats_tab.refresh_chats_button, qtbot.button())

    # Assert that the runner's 'run' method was called
    mock_runner.run.assert_called_once()

    # Check that the command passed was correct
    run_args = mock_runner.run.call_args[0][0]
    assert run_args == ['chat', 'ls', '-o', 'json']
