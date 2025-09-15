import pytest
from unittest.mock import MagicMock
from src.tdl_runner import TdlRunner

@pytest.fixture
def mock_settings_manager():
    """Fixture to create a mock SettingsManager."""
    manager = MagicMock()
    # Default settings
    manager.get.side_effect = lambda key, default=None: {
        'auto_proxy': False,
        'manual_proxy': '',
        'storage_driver': 'bolt',
        'storage_path': '',
        'namespace': 'default',
        'ntp_server': '',
        'reconnect_timeout': '5m',
        'debug_mode': False,
    }.get(key, default)
    return manager

class MockLogger:
    def info(self, msg): pass
    def debug(self, msg): pass

def test_tdl_runner_base_command(mock_settings_manager):
    """Tests that the runner builds a basic command correctly."""
    logger = MockLogger()
    runner = TdlRunner(tdl_path='/usr/bin/tdl', settings_manager=mock_settings_manager, logger=logger)

    base_command = ['download', '-u', 'some_url']
    worker = runner.run(base_command)

    expected_command = ['/usr/bin/tdl', 'download', '-u', 'some_url']
    assert worker.commands[0] == expected_command

def test_tdl_runner_with_proxy(mock_settings_manager):
    """Tests that the runner correctly adds proxy arguments."""
    mock_settings_manager.get.side_effect = lambda key, default=None: {
            'auto_proxy': False,
        'manual_proxy': 'http://proxy.example.com:8080',
    }.get(key, default)

    logger = MockLogger()
    runner = TdlRunner(tdl_path='tdl', settings_manager=mock_settings_manager, logger=logger)

    worker = runner.run(['download'])

    assert '--proxy' in worker.commands[0]
    assert 'http://proxy.example.com:8080' in worker.commands[0]

def test_tdl_runner_with_namespace(mock_settings_manager):
    """Tests that the runner correctly adds the namespace argument."""
    mock_settings_manager.get.side_effect = lambda key, default=None: {
        'namespace': 'my-personal-account',
    }.get(key, default)

    logger = MockLogger()
    runner = TdlRunner(tdl_path='tdl', settings_manager=mock_settings_manager, logger=logger)

    worker = runner.run(['chat', 'ls'])

    assert '--ns' in worker.commands[0]
    assert 'my-personal-account' in worker.commands[0]

def test_tdl_runner_with_debug_mode(mock_settings_manager):
    """Tests that the runner correctly adds the debug flag."""
    mock_settings_manager.get.side_effect = lambda key, default=None: {
        'debug_mode': True,
    }.get(key, default)

    logger = MockLogger()
    runner = TdlRunner(tdl_path='tdl', settings_manager=mock_settings_manager, logger=logger)

    worker = runner.run(['backup'])

    assert '--debug' in worker.commands[0]
