import sys
import threading
import re
from PyQt6.QtCore import QThread, pyqtSignal

# pywinpty is only available on Windows
if sys.platform == "win32":
    try:
        from winpty import PtyProcess

        # Alias for backward compatibility in the rest of the file
        pywinpty = PtyProcess
    except ImportError:
        PtyProcess = None
        pywinpty = None


class LoginWorker(QThread):
    warning_detected = pyqtSignal(str)
    status_update = pyqtSignal(str)
    prompt_for_input = pyqtSignal(str, str)
    qr_code_ready = pyqtSignal(str)
    login_success = pyqtSignal()
    login_failed = pyqtSignal(str)

    def __init__(
        self, tdl_path, namespace, settings_manager, logger, mode="code", parent=None
    ):
        super().__init__(parent)
        self.tdl_path = tdl_path
        self.namespace = namespace
        self.settings_manager = settings_manager
        self.logger = logger
        self.mode = mode
        self.pty_process = None
        self._is_stopped = False
        self._login_success_emitted = False

    def _strip_ansi(self, text):
        """Removes ANSI escape codes from a string."""
        # This regex covers most common cases of ANSI escape sequences
        ansi_escape = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")
        return ansi_escape.sub("", text)

    def run(self):
        # On non-Windows platforms, pywinpty is not available.
        # We must fall back to the old subprocess logic which is known to fail,
        # but it's better than crashing the application.
        if sys.platform != "win32":
            self.login_failed.emit(
                "Interactive login is currently only supported on Windows."
            )
            # In a real-world scenario, we would implement a fallback to subprocess
            # or disable the feature entirely on non-Windows platforms.
            # For this fix, we focus on the Windows case as per the user's environment.
            return

        command = [self.tdl_path, "login", "-T", self.mode, "--ns", self.namespace]
        if self.settings_manager.get("debug_mode", False):
            command.append("--debug")

        try:
            # Spawn the process in a pseudo-terminal
            self.pty_process = pywinpty.spawn(command)
            self.logger.info(f"Started login process in PTY: {' '.join(command)}")

            if self.mode == "code":
                # With PTY, stdout and stderr are combined, so we only need one reader
                output_thread = threading.Thread(target=self._read_pty_output)
            elif self.mode == "qr":
                # The QR mode might also benefit from PTY, using the same reader
                output_thread = threading.Thread(target=self._read_pty_output_for_qr)
            else:
                self.login_failed.emit(f"Invalid login mode: {self.mode}")
                return

            output_thread.start()
            output_thread.join()  # Wait for the reader to finish

            if self.pty_process.isalive():
                self.pty_process.wait()

            # Check exit status, but only if success hasn't been emitted from the output reader
            if self.pty_process.exitstatus == 0 and not self._login_success_emitted:
                self.login_success.emit()
                self._login_success_emitted = True
            elif not self._is_stopped and self.pty_process.exitstatus != 0:
                self.login_failed.emit(
                    f"Login process finished with exit code {self.pty_process.exitstatus}."
                )

        except Exception as e:
            self.login_failed.emit(f"Failed to start login process with PTY: {e}")

    def _read_pty_output(self):
        """Reads and processes the combined stdout/stderr from the PTY."""
        buffer = ""
        prompt_regex = re.compile(r"\? (.*):")

        while self.pty_process.isalive() and not self._is_stopped:
            try:
                char = self.pty_process.read(1)
            except EOFError:
                break  # Process exited

            buffer += char
            # Clean the buffer to remove ANSI codes before processing
            clean_buffer = self._strip_ansi(buffer)
            line = clean_buffer.strip()

            self.logger.debug(f"[PTY] {repr(char)} -> Buffer: '{line}'")

            # Check for prompts in the cleaned buffer
            prompt_match = prompt_regex.search(line)
            if prompt_match:
                self.logger.debug(f"[PTY-MATCH] Prompt matched on line: '{line}'")
                prompt_text = prompt_match.group(1).strip()
                prompt_type = "unknown"

                if "phone number" in prompt_text.lower():
                    prompt_type = "phone"
                elif "code" in prompt_text.lower():
                    prompt_type = "code"
                elif "password" in prompt_text.lower():
                    prompt_type = "password"

                # The warning might also be in the line, extract it
                if "warn:" in line.lower():
                    self.warning_detected.emit(line.split("?")[0].strip())

                self.prompt_for_input.emit(prompt_type, prompt_text)
                buffer = ""  # Clear buffer after successful match
                continue

            # Check for other messages on newlines in the raw buffer
            if "\n" in buffer:
                parts = buffer.split("\n")
                buffer = parts[-1]  # Keep the last, possibly incomplete part

                for part in parts[:-1]:
                    clean_part = self._strip_ansi(part)
                    line_to_check = clean_part.strip()
                    if not line_to_check:
                        continue

                    self.logger.debug(f"[PTY-LINE] {line_to_check}")
                    if "login successfully!" in line_to_check.lower():
                        if not self._login_success_emitted:
                            self.login_success.emit()
                            self._login_success_emitted = True
                        return  # End thread
                    if "sending code..." in line_to_check.lower():
                        self.status_update.emit("Sending verification code...")

    def _read_pty_output_for_qr(self):
        # A simplified reader for QR code mode.
        # We do NOT strip ANSI codes here, as they are used to render the QR code.
        buffer = ""
        while self.pty_process.isalive() and not self._is_stopped:
            try:
                char = self.pty_process.read(1)
                buffer += char
                # Check for the trigger phrase in the raw buffer
                if "Scan QR code" in buffer:
                    # Emit the raw buffer to preserve ANSI-based QR code formatting
                    self.qr_code_ready.emit(buffer)
            except EOFError:
                break

    def send_input(self, text):
        if self.pty_process and self.pty_process.isalive():
            try:
                # The new PTY API expects a string, not bytes.
                self.pty_process.write(text + "\r\n")
                self.logger.debug(f"[PTY-WRITE] Wrote: {text}")
            except Exception as e:
                self.login_failed.emit(f"Failed to write to PTY process: {e}")

    def stop(self):
        self._is_stopped = True
        if self.pty_process and self.pty_process.isalive():
            try:
                self.pty_process.terminate()
                self.logger.warning("Login process terminated by user.")
            except Exception as e:
                self.logger.error(f"Error terminating PTY process: {e}")
