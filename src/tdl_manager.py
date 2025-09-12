import sys
import os
import platform
import urllib.request
import urllib.error
import json
import zipfile
import tarfile
import shutil
import subprocess

# --- Configuration ---
GITHUB_API_URL = "https://api.github.com/repos/iyear/tdl/releases/latest"
ASSET_MAP = {
    ('windows', '64bit'): 'tdl_Windows_64bit.zip',
    ('windows', '32bit'): 'tdl_Windows_32bit.zip',
    ('linux', '64bit'): 'tdl_Linux_64bit.tar.gz',
    ('darwin', '64bit'): 'tdl_MacOS_64bit.tar.gz',
    ('darwin', 'arm64'): 'tdl_MacOS_arm64.tar.gz',
}

class TdlManager:
    def __init__(self):
        self.bin_dir = os.path.join(os.path.dirname(__file__), '..', 'bin')
        os.makedirs(self.bin_dir, exist_ok=True)
        self.executable_name = 'tdl.exe' if platform.system() == 'Windows' else 'tdl'
        self.local_tdl_path = os.path.join(self.bin_dir, self.executable_name)

    def get_platform_key(self):
        """Determines the OS and architecture key for the asset map."""
        system = platform.system().lower()
        if system == 'windows':
            os_key = 'windows'
        elif system == 'linux':
            os_key = 'linux'
        elif system == 'darwin':
            os_key = 'darwin'
        else:
            return None, 'Unsupported operating system.'

        architecture = platform.architecture()[0]
        if '64' in architecture:
            arch_key = '64bit'
        elif '32' in architecture:
            arch_key = '32bit'
        elif platform.machine().lower() == 'arm64' and os_key == 'darwin':
            arch_key = 'arm64'
        else:
            return None, f'Unsupported architecture: {platform.machine()}'

        platform_key = (os_key, arch_key)
        if platform_key not in ASSET_MAP:
            return None, f"Your platform ({system}, {platform.machine()}) is not supported for automatic download."

        return platform_key, None

    def check_for_tdl(self):
        """
        Checks for the tdl executable locally or in the system PATH.
        Returns a tuple (path, status), where status is one of:
        'found_local', 'found_path', 'not_found'.
        """
        if os.path.exists(self.local_tdl_path):
            return self.local_tdl_path, 'found_local'

        system_tdl_path = shutil.which(self.executable_name)
        if system_tdl_path:
            return system_tdl_path, 'found_path'

        return None, 'not_found'

    def get_latest_release_info(self):
        """
        Fetches the latest release data from the GitHub API.
        Returns a tuple (data, error_message).
        """
        try:
            with urllib.request.urlopen(GITHUB_API_URL) as response:
                if response.status == 200:
                    return json.load(response), None
                else:
                    return None, f"Failed to fetch release info (Status: {response.status})."
        except urllib.error.URLError as e:
            return None, f"Network error fetching release info: {e.reason}"
        except Exception as e:
            return None, f"An unexpected error occurred while fetching release info: {e}"

    def download_file(self, url, filepath, progress_callback=None):
        """
        Downloads a file, optionally reporting progress.
        Returns (True, None) on success, (False, error_message) on failure.
        """
        try:
            with urllib.request.urlopen(url) as response:
                total_size = int(response.getheader('Content-Length', 0))
                if progress_callback:
                    progress_callback(0, total_size)

                with open(filepath, 'wb') as f:
                    downloaded_size = 0
                    chunk_size = 8192
                    while True:
                        chunk = response.read(chunk_size)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        if progress_callback:
                            progress_callback(downloaded_size, total_size)
            return True, None
        except Exception as e:
            return False, f"Failed to download file: {e}"

    def extract_archive(self, filepath, dest_dir):
        """
        Extracts a .zip or .tar.gz archive.
        Returns (True, None) on success, (False, error_message) on failure.
        """
        try:
            if filepath.endswith('.zip'):
                with zipfile.ZipFile(filepath, 'r') as zip_ref:
                    zip_ref.extractall(dest_dir)
            elif filepath.endswith('.tar.gz'):
                with tarfile.open(filepath, 'r:gz') as tar_ref:
                    tar_ref.extractall(dest_dir)
            else:
                return False, f"Unsupported archive format: {filepath}"
            return True, None
        except Exception as e:
            return False, f"Error extracting archive: {e}"
        finally:
            if os.path.exists(filepath):
                os.remove(filepath)

    def download_and_install_tdl(self, progress_callback=None):
        """
        Main orchestration method to download, extract, and install tdl.
        Returns (path, None) on success, (None, error_message) on failure.
        """
        # On Windows, use the official installer script for robustness.
        # We will modify it on the fly to ensure a portable installation.
        if platform.system() == "Windows":
            try:
                # 1. Download the installer script
                script_url = "https://docs.iyear.me/tdl/install.ps1"
                with urllib.request.urlopen(script_url) as response:
                    if response.status != 200:
                        return None, f"Failed to download installer script (status: {response.status})"
                    original_script = response.read().decode('utf-8')

                # 2. Modify the script for portable use
                # Use a raw string and escape backslashes for the Windows path
                portable_path = self.bin_dir.replace('\\', '\\\\')
                modified_script = original_script.replace(
                    '$Location = "$Env:SystemDrive\\tdl"',
                    f'$Location = "{portable_path}"'
                )

                # Remove the admin check and PATH modification logic
                modified_script = modified_script.replace(
                    'if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]"Administrator"))',
                    'if ($false)'
                )
                modified_script = modified_script.replace(
                    '$PathEnv = [Environment]::GetEnvironmentVariable("Path", [EnvironmentVariableTarget]::Machine)',
                    '# PATH modification disabled for portable install'
                )
                modified_script = modified_script.replace(
                    'if (-not($PathEnv -like "*$Location*"))',
                    'if ($false)'
                )

                # 3. Save the modified script to a temporary file
                temp_script_path = os.path.join(self.bin_dir, 'install_tdl.ps1')
                with open(temp_script_path, 'w', encoding='utf-8') as f:
                    f.write(modified_script)

                # 4. Execute the script
                # We use -ExecutionPolicy Bypass to ensure the script can run.
                command = ['powershell', '-ExecutionPolicy', 'Bypass', '-File', temp_script_path]
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
                stdout, stderr = process.communicate()

                if process.returncode != 0:
                    return None, f"Installer script failed:\n{stdout}\n{stderr}"

                # 5. Clean up the temporary script
                os.remove(temp_script_path)

                # 6. Verify installation
                if os.path.exists(self.local_tdl_path):
                    return self.local_tdl_path, None
                else:
                    return None, f"tdl.exe not found at the expected path after running installer.\n{stdout}\n{stderr}"

            except Exception as e:
                return None, f"An error occurred during the PowerShell install process: {e}"

        # Fallback to the original method for non-Windows platforms
        platform_key, error = self.get_platform_key()
        if error:
            return None, error

        release_info, error = self.get_latest_release_info()
        if error:
            return None, error

        asset_name = ASSET_MAP.get(platform_key)
        if not asset_name:
            return None, f"Could not find a suitable download for your platform: {platform_key}"

        download_url = None
        for asset in release_info.get('assets', []):
            if asset['name'] == asset_name:
                download_url = asset['browser_download_url']
                break

        if not download_url:
            return None, f"Could not find download link for '{asset_name}' in the latest release."

        archive_path = os.path.join(self.bin_dir, asset_name)

        success, error = self.download_file(download_url, archive_path, progress_callback)
        if not success:
            return None, error

        success, error = self.extract_archive(archive_path, self.bin_dir)
        if not success:
            return None, error

        if os.path.exists(self.local_tdl_path):
            if platform.system() != "Windows":
                try:
                    os.chmod(self.local_tdl_path, 0o755)
                except OSError as e:
                    return None, f"Failed to make tdl executable: {e}"
            return self.local_tdl_path, None

        return None, "Could not find tdl executable after extraction."
