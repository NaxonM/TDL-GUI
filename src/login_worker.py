import subprocess
import threading
from PyQt6.QtCore import QThread, pyqtSignal

class LoginWorker(QThread):
    # For 'code' mode
    prompt_detected = pyqtSignal(str)

    # For 'qr' mode
    qr_code_ready = pyqtSignal(str)

    # General signals
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

        if self.settings.get('debug_mode', False):
            command.append('--debug')

        # Note: A more robust implementation would also add proxy and storage args here.

        try:
            self.process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                bufsize=1
            )

            stdout_thread = threading.Thread(target=self._read_stdout)
            stderr_thread = threading.Thread(target=self._read_stderr)
            stdout_thread.start()
            stderr_thread.start()
            stdout_thread.join()
            stderr_thread.join()
            self.process.wait()

            if self.process.returncode != 0 and not self._is_stopped:
                self.login_failed.emit(f"Login process finished with exit code {self.process.returncode}.")

        except Exception as e:
            self.login_failed.emit(f"Failed to start login process: {e}")

    def _read_stdout(self):
        qr_code_lines = []
        is_reading_qr = False

        for line in iter(self.process.stdout.readline, ''):
            if self._is_stopped:
                break

            # Don't strip the line for QR codes, as whitespace is important
            line_stripped = line.strip()
            self.log_message.emit(f"[STDOUT] {line_stripped}")

            if self.mode == 'code':
                if '?' in line_stripped:
                    self.prompt_detected.emit(line_stripped)

            elif self.mode == 'qr':
                if 'Scan QR code' in line_stripped:
                    is_reading_qr = True
                if is_reading_qr:
                    qr_code_lines.append(line)
                    # Heuristic: QR codes are typically square. A large number of lines
                    # suggests we have the whole thing. This is fragile but simple.
                    if len(qr_code_lines) > 20:
                        self.qr_code_ready.emit("".join(qr_code_lines))
                        is_reading_qr = False # Stop appending

            if 'Login successfully!' in line_stripped:
                self.login_success.emit()
                # We can stop reading now
                break

    def _read_stderr(self):
        error_lines = []
        for line in iter(self.process.stderr.readline, ''):
            if self._is_stopped:
                break
            line_stripped = line.strip()
            self.log_message.emit(f"[STDERR] {line_stripped}")
            error_lines.append(line_stripped)

        if error_lines:
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
