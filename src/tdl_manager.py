import os
import platform
import urllib.request
import urllib.error
import shutil
import subprocess

class TdlManager:
    def __init__(self):
        self.bin_dir = os.path.join(os.path.dirname(__file__), '..', 'bin')
        os.makedirs(self.bin_dir, exist_ok=True)
        self.executable_name = 'tdl.exe' if platform.system() == 'Windows' else 'tdl'
        self.local_tdl_path = os.path.join(self.bin_dir, self.executable_name)

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

    def download_and_install_tdl(self, progress_callback=None):
        """
        Main orchestration method to download and install tdl.
        On Windows, it uses a modified PowerShell script.
        On other platforms, it returns an error as this is not supported.
        Returns (path, None) on success, (None, error_message) on failure.
        """
        # The primary supported method is the Windows PowerShell installer.
        if platform.system() != "Windows":
            return None, "Automatic installation is only supported on Windows."

        try:
            # 1. Download the installer script
            # The progress_callback is not used here as the script provides its own progress.
            if progress_callback:
                progress_callback(0, 0) # Indicate busy state

            script_url = "https://docs.iyear.me/tdl/install.ps1"
            with urllib.request.urlopen(script_url) as response:
                if response.status != 200:
                    return None, f"Failed to download installer script (status: {response.status})"
                original_script = response.read().decode('utf-8')

            # 2. Modify the script for portable use
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
            command = ['powershell', '-ExecutionPolicy', 'Bypass', '-File', temp_script_path]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()

            if process.returncode != 0:
                return None, f"Installer script failed:\n{stdout}\n{stderr}"

            # 5. Clean up the temporary script
            os.remove(temp_script_path)

            # 6. Verify installation
            if os.path.exists(self.local_tdl_path):
                if progress_callback:
                    progress_callback(100, 100) # Indicate completion
                return self.local_tdl_path, None
            else:
                return None, f"tdl.exe not found at the expected path after running installer.\n{stdout}\n{stderr}"

        except urllib.error.URLError as e:
            return None, f"A network error occurred: {e.reason}"
        except Exception as e:
            return None, f"An error occurred during the PowerShell install process: {e}"
