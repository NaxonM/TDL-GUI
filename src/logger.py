import logging
import os
from PyQt6.QtCore import QObject, pyqtSignal


class QtLogHandler(logging.Handler):
    """
    A custom logging handler that emits a PyQt signal for each log record.
    """

    def __init__(self, log_signal):
        super().__init__()
        self.log_signal = log_signal

    def emit(self, record):
        """Emits a signal with the formatted log message and level name."""
        msg = self.format(record)
        self.log_signal.emit(msg, record.levelname)


class Logger(QObject):
    """
    A centralized logger for the application.
    It logs to a file and emits a signal for the GUI to display messages.
    """

    log_signal = pyqtSignal(str, str)  # message, level

    def __init__(self, settings_manager):
        super().__init__()
        self.settings_manager = settings_manager

        # 1. Create a logger instance
        self.logger = logging.getLogger("tdl-gui")
        self.logger.setLevel(logging.DEBUG)  # Capture all levels

        # Prevent messages from propagating to the root logger
        self.logger.propagate = False

        # 2. Create a file handler
        log_file_path = os.path.join(self.settings_manager.config_dir, "app.log")
        file_handler = logging.FileHandler(log_file_path, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)

        # 3. Create a Qt signal handler
        qt_handler = QtLogHandler(self.log_signal)
        # Only show INFO and above in the GUI log by default, unless debug mode is on
        gui_log_level = (
            logging.DEBUG if self.settings_manager.get("debug_mode") else logging.INFO
        )
        qt_handler.setLevel(gui_log_level)

        # 4. Create a formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(formatter)
        qt_handler.setFormatter(formatter)

        # 5. Add handlers to the logger
        self.logger.addHandler(file_handler)
        self.logger.addHandler(qt_handler)

    def debug(self, message):
        self.logger.debug(message)

    def info(self, message):
        self.logger.info(message)

    def warning(self, message):
        self.logger.warning(message)

    def error(self, message):
        self.logger.error(message)

    def critical(self, message):
        self.logger.critical(message)


# Create a single, globally accessible instance
# This will be initialized properly in main.py
LOGGER = None


def initialize_logger(settings_manager):
    """Initializes the global logger instance."""
    global LOGGER
    if LOGGER is None:
        LOGGER = Logger(settings_manager)
    return LOGGER
