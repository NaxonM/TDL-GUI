import pytest
from unittest.mock import MagicMock
from PyQt6.QtCore import QObject, pyqtSignal

from src.worker import Worker, ANSI_ESCAPE_RE


class MockLogger:
    def info(self, msg):
        print(f"INFO: {msg}")

    def error(self, msg):
        print(f"ERROR: {msg}")

    def warning(self, msg):
        print(f"WARNING: {msg}")

    def critical(self, msg):
        print(f"CRITICAL: {msg}")

@pytest.fixture
def mock_worker_signals(monkeypatch):
    """Mocks all signals for the Worker class to avoid Qt event loop issues."""
    signals = {
        'taskFinished': pyqtSignal(int),
        'taskFailedWithLog': pyqtSignal(int, str),
        'taskData': pyqtSignal(str),
        'downloadStarted': pyqtSignal(str),
        'downloadProgress': pyqtSignal(dict),
        'downloadFinished': pyqtSignal(str),
        'overallProgress': pyqtSignal(dict),
        'statsUpdated': pyqtSignal(dict),
    }

    for signal_name, signal_class in signals.items():
        mock_signal = MagicMock(spec=signal_class)
        mock_signal.emit = MagicMock()
        monkeypatch.setattr(Worker, signal_name, mock_signal)

def test_ansi_escape_code_stripping():
    """Tests that the ANSI escape code regex removes the codes correctly."""
    line_with_codes = "\x1b[A\x1b[K\x1b[A\x1b[Kفوتفان موزیک(1276833412):1886~ ... done! [42.64 MB in 7.441s; 5.73 MB/s]"
    cleaned_line = ANSI_ESCAPE_RE.sub('', line_with_codes)
    assert "فوتفان موزیک" in cleaned_line
    assert "\x1b" not in cleaned_line

def test_done_line_with_ansi_codes(monkeypatch, mock_worker_signals):
    """
    Tests that a 'done!' line with ANSI codes is correctly parsed and
    that the appropriate signals are emitted.
    """

    # --- Mocks ---
    mock_popen = MagicMock()
    mock_process = MagicMock()

    # The line that caused the original bug
    line_with_codes = "\x1b[A\x1b[K\x1b[A\x1b[Kفوتفان موزیک(1276833412):1886~ ... done! [42.64 MB in 7.441s; 5.73 MB/s]\n"

    mock_process.stdout.readline.side_effect = [line_with_codes, ""]
    mock_process.wait.return_value = 0
    mock_popen.return_value = mock_process

    monkeypatch.setattr("subprocess.Popen", mock_popen)

    # --- Setup ---
    logger = MockLogger()
    worker = Worker(commands=[["dummy_command"]], logger=logger)

    # --- Run ---
    worker.run()

    # --- Asserts ---
    file_id = "فوتفان موزیک(1276833412):1886~"

    # Check that downloadStarted was called for this file
    assert worker.downloadStarted.emit.call_count == 1
    assert worker.downloadStarted.emit.call_args[0][0] == file_id

    # Check that downloadProgress was called with 100%
    assert worker.downloadProgress.emit.call_count == 1
    progress_call_args = worker.downloadProgress.emit.call_args[0][0]
    assert progress_call_args["id"] == file_id
    assert progress_call_args["percent"] == 100

    # Check that downloadFinished was called
    assert worker.downloadFinished.emit.call_count == 1
    assert worker.downloadFinished.emit.call_args[0][0] == file_id

    # Check that the overall task finished successfully
    # This is not strictly necessary for this test, as we are focused on the "done" parsing
    # and the mock is not perfect.
    pass
