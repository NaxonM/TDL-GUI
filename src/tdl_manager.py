import sys
import os
import platform
import urllib.request
import zipfile
import tarfile
import shutil
from PyQt6.QtWidgets import QProgressDialog, QMessageBox
from PyQt6.QtCore import Qt

# --- Configuration ---
TFL_RELEASES_URL = "https://github.com/iyear/tdl/releases/latest/download/"
ASSET_MAP = {
    ('windows', '64bit'): 'tdl_Windows_x86_64.zip',
    ('windows', '32bit'): 'tdl_Windows_i386.zip',
    ('linux', '64bit'): 'tdl_Linux_x86_64.tar.gz',
    ('darwin', '64bit'): 'tdl_Darwin_x86_64.tar.gz',
    ('darwin', 'arm64'): 'tdl_Darwin_arm64.tar.gz',
}

def get_platform_key():
    """Determines the OS and architecture key for the asset map."""
    system = platform.system().lower()
    if system == 'windows':
        os_key = 'windows'
    elif system == 'linux':
        os_key = 'linux'
    elif system == 'darwin':
        os_key = 'darwin'
    else:
        return None

    architecture = platform.architecture()[0]
    if '64' in architecture:
        arch_key = '64bit'
    elif '32' in architecture:
        arch_key = '32bit'
    elif platform.machine().lower() == 'arm64' and os_key == 'darwin': # For Apple Silicon
        arch_key = 'arm64'
    else:
        return None

    return (os_key, arch_key)

def download_with_progress(url, filepath, parent=None):
    """Downloads a file and shows a QProgressDialog."""
    progress = QProgressDialog("Downloading tdl...", "Cancel", 0, 100, parent)
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.setWindowTitle("Setup")
    progress.show()

    try:
        with urllib.request.urlopen(url) as response:
            total_size = int(response.getheader('Content-Length', 0))
            progress.setMaximum(total_size)

            with open(filepath, 'wb') as f:
                downloaded_size = 0
                chunk_size = 8192
                while True:
                    if progress.wasCanceled():
                        return False
                    chunk = response.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded_size += len(chunk)
                    progress.setValue(downloaded_size)
        return True
    except Exception as e:
        QMessageBox.critical(parent, "Download Error", f"Failed to download tdl: {e}")
        return False
    finally:
        progress.close()

def extract_archive(filepath, dest_dir):
    """Extracts a .zip or .tar.gz archive."""
    try:
        if filepath.endswith('.zip'):
            with zipfile.ZipFile(filepath, 'r') as zip_ref:
                zip_ref.extractall(dest_dir)
        elif filepath.endswith('.tar.gz'):
            with tarfile.open(filepath, 'r:gz') as tar_ref:
                tar_ref.extractall(dest_dir)
        else:
            return False
        return True
    except Exception as e:
        print(f"Error extracting archive: {e}")
        return False
    finally:
        os.remove(filepath) # Clean up the archive

def ensure_tdl_executable(app_parent=None):
    """
    Ensures the tdl executable exists in the local bin directory.
    If not, it downloads and extracts it.
    Returns the path to the executable or None if it fails.
    """
    bin_dir = os.path.join(os.path.dirname(__file__), '..', 'bin')
    os.makedirs(bin_dir, exist_ok=True)

    executable_name = 'tdl.exe' if platform.system() == 'Windows' else 'tdl'
    local_tdl_path = os.path.join(bin_dir, executable_name)

    # 1. Check if it already exists locally (preferred)
    if os.path.exists(local_tdl_path):
        return local_tdl_path

    # 2. Check if it's in the system PATH
    system_tdl_path = shutil.which(executable_name)
    if system_tdl_path:
        return system_tdl_path

    # 3. If not found anywhere, download it to our local bin
    QMessageBox.information(app_parent, "TDL Not Found", "The 'tdl' executable was not found on your system. A local copy will be downloaded now.")
    key = get_platform_key()
    if not key or key not in ASSET_MAP:
        QMessageBox.critical(app_parent, "Unsupported Platform", f"Your platform ({platform.system()}, {platform.machine()}) is not supported for automatic download.")
        return None

    asset_name = ASSET_MAP[key]
    download_url = TFL_RELEASES_URL + asset_name
    archive_path = os.path.join(bin_dir, asset_name)

    if not download_with_progress(download_url, archive_path, app_parent):
        return None

    if not extract_archive(archive_path, bin_dir):
        QMessageBox.critical(app_parent, "Extraction Error", "Failed to extract the downloaded tdl archive.")
        return None

    if os.path.exists(local_tdl_path):
        # On Linux/macOS, we need to make it executable
        if platform.system() != "Windows":
            os.chmod(local_tdl_path, 0o755)
        return local_tdl_path

    QMessageBox.critical(app_parent, "Setup Error", f"Could not find tdl executable after extraction.")
    return None
