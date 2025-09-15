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

class Downloader:
    """A simple class to download a file and report progress."""
    def __init__(self, url, dest_folder, progress_callback=None):
        self.url = url
        self.dest_folder = dest_folder
        self.progress_callback = progress_callback

    def run(self):
        try:
            filename = self.url.split("/")[-1]
            dest_path = os.path.join(self.dest_folder, filename)

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
                        if total_size > 0 and self.progress_callback:
                            percent = int((downloaded_size / total_size) * 100)
                            self.progress_callback(percent)

            if self.progress_callback:
                self.progress_callback(100)

            return dest_path, None
        except Exception as e:
            return None, f"Download failed: {e}"


class UpdateWorker(QObject):
    """Worker to run the download and update process in a separate thread."""
    finished = pyqtSignal(str, str)  # Emits updater script path and version
    error = pyqtSignal(str)
    progress = pyqtSignal(int)

    def __init__(self, url, version, current_tdl_path, temp_dir):
        super().__init__()
        self.url = url
        self.version = version
        self.current_tdl_path = current_tdl_path
        self.temp_dir = temp_dir

    def run(self):
        try:
            downloader = Downloader(self.url, self.temp_dir, self.progress.emit)
            download_path, err = downloader.run()
            if err:
                self.error.emit(err)
                return

            new_exe_path = self._extract_zip(download_path)
            updater_script_path = self._create_updater_script(new_exe_path)
            self.finished.emit(updater_script_path, self.version)

        except Exception as e:
            self.error.emit(f"Update process failed: {e}")

    def _extract_zip(self, zip_path):
        """Extracts the tdl.exe from the zip file."""
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            for file_info in zip_ref.infolist():
                if file_info.filename.endswith("tdl.exe"):
                    zip_ref.extract(file_info, self.temp_dir)
                    return os.path.join(self.temp_dir, file_info.filename)
        raise FileNotFoundError("Could not find tdl.exe in the downloaded archive.")

    def _create_updater_script(self, new_exe_path):
        """Creates a batch script to perform the update on restart."""
        current_exe_path = self.current_tdl_path

        if getattr(sys, 'frozen', False):
            app_path = sys.executable
            start_command = f'start "" "{app_path}"'
        else:
            app_path = os.path.abspath(sys.argv[0])
            start_command = f'python "{app_path}"'

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


class UpdateManager(QObject):
    """Manages the tdl update process by running a worker in a thread."""
    def __init__(self, url, version, current_tdl_path):
        super().__init__()
        self.url = url
        self.version = version
        self.current_tdl_path = current_tdl_path
        self.temp_dir = tempfile.mkdtemp(prefix="tdl-update-")
        self.thread = None
        self.worker = None

    def start(self):
        self.thread = QThread()
        self.worker = UpdateWorker(self.url, self.version, self.current_tdl_path, self.temp_dir)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.thread.start()
        return self.worker


class UpdateDialog(QDialog):
    """Dialog to show update progress."""
    def __init__(self, version, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Updating tdl")
        self.setModal(True)
        self.setMinimumWidth(350)
        self.setDisabled(True)

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
