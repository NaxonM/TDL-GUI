import subprocess
import threading
import time
from PyQt6.QtCore import QThread, pyqtSignal

import re
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
        self.process = None
        self._is_stopped = False

    def run(self):
        command = [self.tdl_path, 'login', '-T', self.mode, '--ns', self.namespace]
        if self.settings.get('debug_mode', False): command.append('--debug')

        try:
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='ignore'
            )

            if self.mode == 'code':
                stdout_thread = threading.Thread(target=self._read_stdout_for_code)
            elif self.mode == 'qr':
                stdout_thread = threading.Thread(target=self._read_stdout_for_qr)
            else:
                self.login_failed.emit(f"Invalid login mode: {self.mode}")
                return

            stderr_thread = threading.Thread(target=self._read_stderr)
            stdout_thread.start()
            stderr_thread.start()

            return_code = self.process.wait()

            stdout_thread.join()
            stderr_thread.join()

            if return_code == 0:
                # On successful QR scan, the success message is the only thing we get
                # after the process ends.
                self.login_success.emit()
            elif not self._is_stopped:
                self.login_failed.emit(f"Login process finished with exit code {return_code}.")

        except Exception as e:
            self.login_failed.emit(f"Failed to start login process: {e}")

    def _read_stdout_for_code(self):
        buffer = ""
        # Regex to find a question mark and capture the text of the prompt.
        prompt_regex = re.compile(r"\? (.*):")

        for char in iter(lambda: self.process.stdout.read(1), ''):
            if self._is_stopped:
                break
            buffer += char

            # Process buffer when we hit a colon (prompts) or newline (other messages)
            if char == ':' or char == '\n':
                line = buffer.strip()
                if not line:
                    buffer = ""
                    continue

                self.log_message.emit(f"[STDOUT] {line}")

                # --- Check for Prompts ---
                prompt_match = prompt_regex.search(line)
                if prompt_match:
                    prompt_text = prompt_match.group(1).strip()
                    prompt_type = 'unknown'
                    if 'phone number' in prompt_text.lower():
                        prompt_type = 'phone'
                    elif 'code' in prompt_text.lower():
                        prompt_type = 'code'
                    elif 'password' in prompt_text.lower():
                        prompt_type = 'password'

                    self.prompt_for_input.emit(prompt_type, prompt_text)

                    # Check for a warning on the same line, before the prompt
                    if 'warn:' in line.lower():
                        # Extract just the warning part
                        warn_text = line.split('?')[0].strip()
                        self.warning_detected.emit(warn_text)

                    buffer = ""
                    continue

                # --- Check for other messages ---
                if 'login successfully!' in line.lower():
                    self.login_success.emit()
                    buffer = ""
                    return  # End of process

                if 'sending code...' in line.lower():
                    self.status_update.emit('Sending verification code...')
                    buffer = ""
                    continue

                # If it's just a line break and we haven't matched anything else,
                # we can probably just clear the buffer and wait for more content.
                if char == '\n':
                    buffer = ""

    def _read_stdout_for_qr(self):
        buffer = ""
        last_char_time = time.time()

        while not self._is_stopped:
            try:
                char = self.process.stdout.read(1)
                if not char:
                    break # Pipe closed

                last_char_time = time.time()
                buffer += char

                # Assume the QR code is complete if we see a newline and "Scan QR"
                if char == '\n' and "Scan QR code" in buffer:
                    self.qr_code_ready.emit(buffer)
                    # Don't clear buffer, as more of the QR code might be coming

            except:
                break # Exit on error

        # Final emit after loop finishes, in case there was no newline
        if buffer:
             self.qr_code_ready.emit(buffer)


    def _read_stderr(self):
        error_lines = []
        for line in iter(self.process.stderr.readline, ''):
            if self._is_stopped: break
            line = line.strip()
            if line:
                self.log_message.emit(f"[STDERR] {line}")
                error_lines.append(line)
        if error_lines and not self._is_stopped:
            self.login_failed.emit("\n".join(error_lines))

    def send_input(self, text):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(text + '\n')
                self.process.stdin.flush()
                self.log_message.emit(f"[STDIN] Wrote: {text}")
            except Exception as e:
                self.login_failed.emit(f"Failed to write to login process: {e}")

    def stop(self):
        self._is_stopped = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.log_message.emit("Login process terminated by user.")
            except Exception as e:
                self.log_message.emit(f"Error terminating login process: {e}")
