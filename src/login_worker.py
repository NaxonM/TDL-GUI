import subprocess
import threading
import time
import logging
from PyQt6.QtCore import QThread, pyqtSignal

import re

# --- Set up debugging logger ---
log_file = 'login_debug.log'
# Clear the log file for each new run
with open(log_file, 'w'):
    pass

debug_logger = logging.getLogger('login_worker_debug')
debug_logger.setLevel(logging.DEBUG)
handler = logging.FileHandler(log_file)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if not debug_logger.handlers:
    debug_logger.addHandler(handler)
# --- End of logger setup ---


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
        debug_logger.info("LoginWorker initialized.")

    def run(self):
        command = [self.tdl_path, 'login', '-T', self.mode, '--ns', self.namespace]
        if self.settings.get('debug_mode', False): command.append('--debug')

        debug_logger.info(f"Starting TDL process with command: {' '.join(command)}")

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
            debug_logger.info("TDL process started.")

            if self.mode == 'code':
                stdout_thread = threading.Thread(target=self._read_stdout_for_code)
            elif self.mode == 'qr':
                stdout_thread = threading.Thread(target=self._read_stdout_for_qr)
            else:
                err_msg = f"Invalid login mode: {self.mode}"
                debug_logger.error(err_msg)
                self.login_failed.emit(err_msg)
                return

            stderr_thread = threading.Thread(target=self._read_stderr)
            stdout_thread.start()
            stderr_thread.start()
            debug_logger.info("STDOUT and STDERR reader threads started.")

            return_code = self.process.wait()
            debug_logger.info(f"TDL process finished with exit code: {return_code}")

            stdout_thread.join()
            stderr_thread.join()

            if return_code == 0:
                debug_logger.info("Login process seems successful (exit code 0).")
                self.login_success.emit()
            elif not self._is_stopped:
                err_msg = f"Login process finished with non-zero exit code {return_code}."
                debug_logger.error(err_msg)
                self.login_failed.emit(err_msg)

        except Exception as e:
            err_msg = f"Failed to start login process: {e}"
            debug_logger.critical(err_msg, exc_info=True)
            self.login_failed.emit(err_msg)

    def _read_stdout_for_code(self):
        buffer = ""
        prompt_regex = re.compile(r"\? (.*):")
        debug_logger.info("STDOUT reader started for code login.")

        for char in iter(lambda: self.process.stdout.read(1), ''):
            if self._is_stopped:
                debug_logger.warning("STDOUT reader stopping because stop flag is set.")
                break

            debug_logger.debug(f"STDOUT Raw Char: {repr(char)}")
            buffer += char
            line = buffer.strip()
            debug_logger.debug(f"STDOUT Buffer: '{buffer.strip()}'")

            prompt_match = prompt_regex.search(line)
            if prompt_match:
                debug_logger.info(f"Prompt pattern matched on line: '{line}'")
                self.log_message.emit(f"[STDOUT] {line}")

                prompt_text = prompt_match.group(1).strip()
                prompt_type = 'unknown'
                if 'phone number' in prompt_text.lower():
                    prompt_type = 'phone'
                elif 'code' in prompt_text.lower():
                    prompt_type = 'code'
                elif 'password' in prompt_text.lower():
                    prompt_type = 'password'

                debug_logger.info(f"Detected prompt type '{prompt_type}' with text: '{prompt_text}'")
                self.prompt_for_input.emit(prompt_type, prompt_text)

                if 'warn:' in line.lower():
                    warn_text = line.split('?')[0].strip()
                    debug_logger.warning(f"Warning detected on same line: '{warn_text}'")
                    self.warning_detected.emit(warn_text)

                buffer = ""
                debug_logger.debug("Buffer cleared after prompt match.")
                continue

            if char == '\n':
                debug_logger.info(f"Newline detected. Processing line: '{line}'")
                if not line:
                    buffer = ""
                    continue

                self.log_message.emit(f"[STDOUT] {line}")

                if 'login successfully!' in line.lower():
                    debug_logger.info("'Login successfully!' detected.")
                    self.login_success.emit()
                    buffer = ""
                    return

                if 'sending code...' in line.lower():
                    debug_logger.info("'Sending code...' detected.")
                    self.status_update.emit('Sending verification code...')
                    buffer = ""
                    continue

                debug_logger.info("Unrecognized line on newline, clearing buffer.")
                buffer = ""

    def _read_stdout_for_qr(self):
        # ... (unchanged, but adding logging would be good practice if used)
        buffer = ""
        last_char_time = time.time()

        while not self._is_stopped:
            try:
                char = self.process.stdout.read(1)
                if not char:
                    break # Pipe closed

                last_char_time = time.time()
                buffer += char

                if char == '\n' and "Scan QR code" in buffer:
                    self.qr_code_ready.emit(buffer)

            except:
                break

        if buffer:
             self.qr_code_ready.emit(buffer)

    def _read_stderr(self):
        error_lines = []
        debug_logger.info("STDERR reader started.")
        for line in iter(self.process.stderr.readline, ''):
            if self._is_stopped:
                debug_logger.warning("STDERR reader stopping because stop flag is set.")
                break
            line = line.strip()
            if line:
                debug_logger.error(f"STDERR: {line}")
                self.log_message.emit(f"[STDERR] {line}")
                error_lines.append(line)
        if error_lines and not self._is_stopped:
            self.login_failed.emit("\n".join(error_lines))

    def send_input(self, text):
        if self.process and self.process.poll() is None:
            try:
                debug_logger.info(f"Writing to STDIN: {text}")
                self.process.stdin.write(text + '\n')
                self.process.stdin.flush()
                self.log_message.emit(f"[STDIN] Wrote: {text}")
            except Exception as e:
                err_msg = f"Failed to write to login process: {e}"
                debug_logger.critical(err_msg, exc_info=True)
                self.login_failed.emit(err_msg)

    def stop(self):
        self._is_stopped = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.log_message.emit("Login process terminated by user.")
            except Exception as e:
                self.log_message.emit(f"Error terminating login process: {e}")
