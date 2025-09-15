import os
import platform
import urllib.request
import urllib.error
import shutil
import json
import zipfile
import tempfile


class TdlManager:
    def __init__(self):
        self.bin_dir = os.path.join(os.path.dirname(__file__), "..", "bin")
        os.makedirs(self.bin_dir, exist_ok=True)
        self.executable_name = "tdl.exe" if platform.system() == "Windows" else "tdl"
        self.local_tdl_path = os.path.join(self.bin_dir, self.executable_name)

    def check_for_tdl(self):
        """
        Checks for the tdl executable locally or in the system PATH.
        Returns a tuple (path, status), where status is one of:
        'found_local', 'found_path', 'not_found'.
        """
        if os.path.exists(self.local_tdl_path):
            return self.local_tdl_path, "found_local"

        system_tdl_path = shutil.which(self.executable_name)
        if system_tdl_path:
            return system_tdl_path, "found_path"

        return None, "not_found"

    def download_and_install_tdl(self, progress_callback=None):
        """
        Downloads and installs the latest version of tdl for Windows.
        This method is now self-contained and does not rely on external scripts.
        Returns (path, None) on success, (None, error_message) on failure.
        """
        if platform.system() != "Windows":
            return None, "Automatic installation is only supported on Windows."

        try:
            # 1. Get latest version from GitHub API
            if progress_callback:
                progress_callback(0, 100)

            api_url = "https://api.github.com/repos/iyear/tdl/releases/latest"
            with urllib.request.urlopen(api_url) as response:
                if response.status != 200:
                    return None, f"Failed to get release info (status: {response.status})"
                release_data = json.loads(response.read().decode("utf-8"))
                latest_version = release_data["tag_name"]

            # 2. Determine architecture and construct URL
            arch = "64bit" if platform.architecture()[0] == "64bit" else "32bit"
            file_name = f"tdl_Windows_{arch}.zip"
            download_url = f"https://github.com/iyear/tdl/releases/download/{latest_version}/{file_name}"

            # 3. Download the zip file
            temp_zip_path = os.path.join(tempfile.gettempdir(), file_name)

            def _reporthook(count, block_size, total_size):
                if progress_callback and total_size > 0:
                    percent = int(count * block_size * 100 / total_size)
                    progress_callback(percent, 100)

            urllib.request.urlretrieve(download_url, temp_zip_path, _reporthook)

            # 4. Extract tdl.exe from the zip file
            if progress_callback:
                progress_callback(0, 100)

            with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
                for member in zip_ref.infolist():
                    if member.filename.endswith("tdl.exe"):
                        # Extract to bin_dir, removing any parent folders from zip
                        member.filename = os.path.basename(member.filename)
                        zip_ref.extract(member, self.bin_dir)
                        break
                else:
                    os.remove(temp_zip_path) # Clean up before returning
                    return None, "Could not find tdl.exe in the downloaded archive."

            # 5. Clean up
            os.remove(temp_zip_path)

            # 6. Verify installation
            if os.path.exists(self.local_tdl_path):
                if progress_callback:
                    progress_callback(100, 100)
                return self.local_tdl_path, None
            else:
                return None, "tdl.exe not found at the expected path after installation."

        except urllib.error.URLError as e:
            return None, f"A network error occurred: {e.reason}"
        except (json.JSONDecodeError, KeyError) as e:
            return None, f"Failed to parse GitHub API response: {e}"
        except Exception as e:
            return None, f"An unexpected error occurred: {e}"
