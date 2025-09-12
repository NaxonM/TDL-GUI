import sys
import threading
import time
import re
from PyQt6.QtCore import QThread, pyqtSignal

# pywinpty is only available on Windows
if sys.platform == "win32":
    import pywinpty

class LoginWorker(QThread):
    warning_detected = pyqtSignal(str)
    status_update = pyqtSignal(str)
    prompt_for_input = pyqtSignal(str, str)
    qr_code_ready = pyqtSignal(str)
    login_success = pyqtSignal()
    login_failed = pyqtSignal(str)
    log_message = pyqtSignal(str)

    def __init__(self, tdl_path, namespace, settings, mode='code', parent=None):
        super().__init__(parent)
        self.tdl_path = tdl_path
        self.namespace = namespace
        self.settings = settings
        self.mode = mode
        self.pty_process = None
        self._is_stopped = False

    def run(self):
        # On non-Windows platforms, pywinpty is not available.
        # We must fall back to the old subprocess logic which is known to fail,
        # but it's better than crashing the application.
        if sys.platform != "win32":
            self.login_failed.emit("Interactive login is currently only supported on Windows.")
            # In a real-world scenario, we would implement a fallback to subprocess
            # or disable the feature entirely on non-Windows platforms.
            # For this fix, we focus on the Windows case as per the user's environment.
            return

        command = [self.tdl_path, 'login', '-T', self.mode, '--ns', self.namespace]
        if self.settings.get('debug_mode', False): command.append('--debug')

        try:
            # Spawn the process in a pseudo-terminal
            self.pty_process = pywinpty.spawn(command)
            self.log_message.emit(f"Started process in PTY: {' '.join(command)}")

            if self.mode == 'code':
                # With PTY, stdout and stderr are combined, so we only need one reader
                output_thread = threading.Thread(target=self._read_pty_output)
            elif self.mode == 'qr':
                # The QR mode might also benefit from PTY, using the same reader
                output_thread = threading.Thread(target=self._read_pty_output_for_qr)
            else:
                self.login_failed.emit(f"Invalid login mode: {self.mode}")
                return

            output_thread.start()
            output_thread.join() # Wait for the reader to finish

            if self.pty_process.isalive():
                self.pty_process.wait()

            # Check exit status
            if self.pty_process.exitstatus == 0:
                self.login_success.emit()
            elif not self._is_stopped:
                self.login_failed.emit(f"Login process finished with exit code {self.pty_process.exitstatus}.")

        except Exception as e:
            self.login_failed.emit(f"Failed to start login process with PTY: {e}")

    def _read_pty_output(self):
        """Reads the combined stdout/stderr from the PTY."""
        buffer = ""
        prompt_regex = re.compile(r"\? (.*):")

        while self.pty_process.isalive() and not self._is_stopped:
            try:
                # Read with a timeout to allow checking the stop flag
                char = self.pty_process.read(1, 1000) # 1 char, 1s timeout
                if not char:
                    continue # Timeout, loop again
            except EOFError:
                break # Process exited

            buffer += char
            # Using strip() is important because PTY output can have extra whitespace
            line = buffer.strip()
            self.log_message.emit(f"[PTY] {repr(char)} -> Buffer: '{line}'")

            # The prompt pattern check remains the same
            prompt_match = prompt_regex.search(line)
            if prompt_match:
                self.log_message.emit(f"[PTY-MATCH] Prompt matched on line: '{line}'")
                prompt_text = prompt_match.group(1).strip()
                prompt_type = 'unknown'

                if 'phone number' in prompt_text.lower():
                    prompt_type = 'phone'
                elif 'code' in prompt_text.lower():
                    prompt_type = 'code'
                elif 'password' in prompt_text.lower():
                    prompt_type = 'password'

                self.prompt_for_input.emit(prompt_type, prompt_text)
                if 'warn:' in line.lower():
                    self.warning_detected.emit(line.split('?')[0].strip())

                buffer = "" # Clear buffer after successful match
                continue

            # Check for other messages on newlines
            if '\n' in buffer:
                # Process lines separated by newline
                parts = buffer.split('\n')
                # The last part might be incomplete, so keep it in the buffer
                buffer = parts[-1]

                for part in parts[:-1]:
                    line_to_check = part.strip()
                    if not line_to_check:
                        continue

                    self.log_message.emit(f"[PTY-LINE] {line_to_check}")
                    if 'login successfully!' in line_to_check.lower():
                        self.login_success.emit()
                        return # End thread

                    if 'sending code...' in line_to_check.lower():
                        self.status_update.emit('Sending verification code...')

    def _read_pty_output_for_qr(self):
        # A simplified reader for QR code mode
        buffer = ""
        while self.pty_process.isalive() and not self._is_stopped:
            try:
                char = self.pty_process.read(1, 1000)
                if not char:
                    continue
                buffer += char
                if "Scan QR code" in buffer:
                    self.qr_code_ready.emit(buffer)
            except EOFError:
                break

    def send_input(self, text):
        if self.pty_process and self.pty_process.isalive():
            try:
                # PTY expects bytes, so we encode the string
                self.pty_process.write(text.encode('utf-8') + b'\r\n')
                self.log_message.emit(f"[PTY-WRITE] Wrote: {text}")
            except Exception as e:
                self.login_failed.emit(f"Failed to write to PTY process: {e}")

    def stop(self):
        self._is_stopped = True
        if self.pty_process and self.pty_process.isalive():
            try:
                self.pty_process.terminate(force=True)
                self.log_message.emit("Login process terminated by user.")
            except Exception as e:
                self.log_message.emit(f"Error terminating PTY process: {e}")
