import subprocess
import threading
import time
from PyQt6.QtCore import QThread, pyqtSignal

class LoginWorker(QThread):
    prompt_detected = pyqtSignal(str)
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
                stderr=subprocess.PIPE
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
        for byte_char in iter(lambda: self.process.stdout.read(1), b''):
            if self._is_stopped: break

            try:
                char = byte_char.decode('utf-8')
                buffer += char
            except UnicodeDecodeError:
                continue

            if char == ':':
                prompt_line = buffer.strip()
                if '?' in prompt_line:
                    self.log_message.emit(f"[PROMPT DETECTED] {prompt_line}")
                    self.prompt_detected.emit(prompt_line)
                    buffer = ""

            elif char == '\n':
                line_stripped = buffer.strip()
                if line_stripped:
                    self.log_message.emit(f"[STDOUT] {line_stripped}")
                    if 'Login successfully!' in line_stripped:
                        self.login_success.emit()
                        return
                buffer = ""

    def _read_stdout_for_qr(self):
        buffer = ""
        last_char_time = time.time()

        while not self._is_stopped:
            try:
                byte_char = self.process.stdout.read(1)
                if not byte_char:
                    break # Pipe closed

                last_char_time = time.time()
                char = byte_char.decode('utf-8', errors='ignore')
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
        for line_bytes in iter(self.process.stderr.readline, b''):
            if self._is_stopped: break
            line = line_bytes.decode('utf-8', errors='ignore').strip()
            if line:
                self.log_message.emit(f"[STDERR] {line}")
                error_lines.append(line)
        if error_lines and not self._is_stopped:
            self.login_failed.emit("\n".join(error_lines))

    def send_input(self, text):
        if self.process and self.process.poll() is None:
            try:
                self.process.stdin.write(text.encode('utf-8') + b'\n')
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
