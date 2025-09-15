import os
import sys
import time
import urllib.request
import zipfile
import tempfile
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal, QObject
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QProgressBar,
    QLabel,
    QMessageBox,
    QApplication,
)


class UpdateManager(QObject):
    """Handles the tdl update process."""

    progress = pyqtSignal(int)
    finished = pyqtSignal(str, str)  # Emits new executable path and version
    error = pyqtSignal(str)

    def __init__(self, url, version, current_tdl_path):
        super().__init__()
        self.url = url
        self.version = version
        self.current_tdl_path = current_tdl_path
        self.temp_dir = tempfile.mkdtemp(prefix="tdl-update-")
        self.thread = None
        self.downloader = None

    def start_download(self):
        self.thread = QThread()
        self.downloader = Downloader(self.url, self.temp_dir)
        self.downloader.moveToThread(self.thread)

        self.downloader.progress.connect(self.progress.emit)
        self.downloader.finished.connect(self.on_download_finished)
        self.downloader.error.connect(self.error.emit)

        self.thread.started.connect(self.downloader.run)
        self.thread.start()

    def on_download_finished(self, download_path):
        try:
            new_exe_path = self._extract_zip(download_path)
            updater_script_path = self._create_updater_script(new_exe_path)
            self.finished.emit(updater_script_path, self.version)
        except Exception as e:
            self.error.emit(f"Failed during update preparation: {e}")
        finally:
            if self.thread:
                self.thread.quit()
                self.thread.wait()

    def _extract_zip(self, zip_path):
        """Extracts the tdl.exe from the zip file."""
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            # Find the executable in the zip file
            for file_info in zip_ref.infolist():
                if file_info.filename.endswith("tdl.exe"):
                    zip_ref.extract(file_info, self.temp_dir)
                    return os.path.join(self.temp_dir, file_info.filename)
        raise FileNotFoundError("Could not find tdl.exe in the downloaded archive.")

    def _create_updater_script(self, new_exe_path):
        """Creates a batch script to perform the update on restart."""
        current_exe_path = self.current_tdl_path

        # Determine the command to relaunch the application
        if getattr(sys, 'frozen', False):
            # Running as a bundled executable (e.g., PyInstaller)
            app_path = sys.executable
            start_command = f'start "" "{app_path}"'
        else:
            # Running as a Python script
            app_path = os.path.abspath(sys.argv[0])
            start_command = f'python "{app_path}"'

        # Use the executable name for the taskkill command
        app_exe_name = os.path.basename(sys.executable if getattr(sys, 'frozen', False) else 'python.exe')

        script_content = f"""
@echo off
echo Closing tdl-gui...
taskkill /IM {app_exe_name} /F > nul 2>&1
timeout /t 2 /nobreak > nul

echo Replacing executable...
move /Y "{new_exe_path}" "{current_exe_path}"

echo Cleaning up...
rmdir /S /Q "{self.temp_dir}"

echo Relaunching application...
{start_command}

del "%~f0"
"""
        script_path = os.path.join(self.temp_dir, "updater.bat")
        with open(script_path, "w") as f:
            f.write(script_content)
        return script_path


class Downloader(QObject):
    """Worker to download a file in a separate thread."""

    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, url, dest_folder):
        super().__init__()
        self.url = url
        self.dest_folder = dest_folder

    def run(self):
        try:
            filename = self.url.split("/")[-1]
            dest_path = os.path.join(self.dest_folder, filename)

            # Use a context manager for the request to ensure it's closed
            with urllib.request.urlopen(self.url) as response:
                if response.status != 200:
                    raise urllib.error.URLError(f"Bad response status: {response.status}")

                total_size = int(response.getheader("Content-Length", 0))

                with open(dest_path, "wb") as f:
                    downloaded_size = 0
                    chunk_size = 8192
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            percent = int((downloaded_size / total_size) * 100)
                            self.progress.emit(percent)

            self.progress.emit(100)
            self.finished.emit(dest_path)
        except Exception as e:
            self.error.emit(f"Download failed: {e}")


class UpdateDialog(QDialog):
    """Dialog to show update progress."""

    def __init__(self, version, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Updating tdl")
        self.setModal(True)
        self.setMinimumWidth(350)
        self.setDisabled(True) # Disable closing while in progress

        layout = QVBoxLayout(self)
        self.label = QLabel(f"Downloading tdl version {version}...")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)

    def update_progress(self, percent):
        self.progress_bar.setValue(percent)
        if percent == 100:
            self.label.setText("Download complete. Preparing update...")

    def close_on_completion(self):
        self.setDisabled(False)
        QMessageBox.information(
            self,
            "Update Ready",
            "The update has been downloaded. The application will now restart to install it.",
        )
        self.accept()
