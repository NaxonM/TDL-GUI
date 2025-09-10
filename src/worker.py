import subprocess
import re
from PyQt6.QtCore import QThread, pyqtSignal

# Regex for lines containing per-file progress updates.
# Example: 'AnimeGate Archive(1868796312):23639 -> C:~ ... 6.1% [............] [4.00 MB in 11.587s; ETA: 3m2s; 353.50 KB/s]'
TDL_IN_PROGRESS_RE = re.compile(
    r"^(?P<file_id>.+?)\s+\.{3}\s+"
    r"(?P<percent>[\d\.]+%)\s*"
    r"(?:\[.*?\]\s*)?"
    r"\[(?P<size_info>.+? in .+?);\s*~?ETA:\s*(?P<eta>.+?);\s*(?P<speed>.+?)\]"
)

# Regex for a completed file download.
# Example: 'AnimeGate Archive(1868796312):23636 -> C:~ ... done! [65.37 MB in 1m37.935s; 682.85 KB/s]'
TDL_DONE_RE = re.compile(
    r"^(?P<file_id>.+?)\s+\.{3}\s+done!\s*"
    r"\[(?P<size_info>.+? in .+?);\s*(?P<speed>.+?)\]"
)

# Regex for the overall progress bar.
# Example: '[####################################.............................] [1m26s; 1.17 MB/s]'
TDL_OVERALL_RE = re.compile(
    r"^\[(?P<bar>#+\.*)\]\s+"
    r"\[(?P<time>.+?);\s*(?P<speed>.+?)\]"
)

# Regex for CPU/Memory stats
# Example: 'CPU: 3.13% Memory: 31.26 MB Goroutines: 54'
TDL_STATS_RE = re.compile(
    r"CPU:\s*(?P<cpu>[\d\.]+%)\s+"
    r"Memory:\s*(?P<mem>[\d\.]+\s+\w+)\s+"
    r"Goroutines:\s*(?P<goroutines>\d+)"
)


class Worker(QThread):
    logMessage = pyqtSignal(str)
    taskFinished = pyqtSignal(int)

    # New signals for structured data
    downloadStarted = pyqtSignal(str)
    downloadProgress = pyqtSignal(dict)
    downloadFinished = pyqtSignal(str)
    overallProgress = pyqtSignal(dict)
    statsUpdated = pyqtSignal(dict)


    def __init__(self, commands, tdl_path, timeout=300, parent=None):
        super().__init__(parent)
        if not isinstance(commands[0], list):
            commands = [commands]
        self.commands = commands
        self.tdl_path = tdl_path
        self.process = None
        self._is_stopped = False
        self.seen_files = set()
        self.timeout = timeout if timeout > 0 else None

    def run(self):
        overall_return_code = 0

        for i, command in enumerate(self.commands):
            if self._is_stopped:
                break

            self.logMessage.emit(f"--- Running task {i+1}/{len(self.commands)}: {' '.join(command)} ---")
            try:
                self.process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='replace'
                )

                for line in iter(self.process.stdout.readline, ''):
                    if self._is_stopped:
                        break

                    line = line.strip()
                    if not line:
                        continue

                    # Check for a completed file first
                    done_match = TDL_DONE_RE.search(line)
                    if done_match:
                        data = done_match.groupdict()
                        file_id = data['file_id'].strip()

                        if file_id not in self.seen_files:
                            self.seen_files.add(file_id)
                            self.downloadStarted.emit(file_id)

                        progress_data = {
                            'id': file_id,
                            'percent': 100,
                            'size_info': data['size_info'],
                            'eta': 'Done',
                            'speed': data['speed'],
                        }
                        self.downloadProgress.emit(progress_data)
                        self.downloadFinished.emit(file_id)
                        self.logMessage.emit(line) # Also log the raw message
                        continue

                    # Check for in-progress file
                    progress_match = TDL_IN_PROGRESS_RE.search(line)
                    if progress_match:
                        data = progress_match.groupdict()
                        file_id = data['file_id'].strip()

                        if file_id not in self.seen_files:
                            self.seen_files.add(file_id)
                            self.downloadStarted.emit(file_id)

                        progress_data = {
                            'id': file_id,
                            'percent': float(data['percent'].replace('%', '')),
                            'size_info': data['size_info'],
                            'eta': data.get('eta', 'N/A'),
                            'speed': data['speed'],
                        }
                        self.downloadProgress.emit(progress_data)
                        continue

                    # Check for overall progress
                    overall_match = TDL_OVERALL_RE.search(line)
                    if overall_match:
                        data = overall_match.groupdict()
                        bar = data['bar']
                        hashes = bar.count('#')
                        dots = bar.count('.')
                        total = hashes + dots
                        percentage = int((hashes / total) * 100) if total > 0 else 0

                        overall_data = {
                            'percent': percentage,
                            'time': data['time'],
                            'speed': data['speed'],
                        }
                        self.overallProgress.emit(overall_data)
                        continue

                    # Check for stats
                    stats_match = TDL_STATS_RE.search(line)
                    if stats_match:
                        self.statsUpdated.emit(stats_match.groupdict())
                        continue

                    self.logMessage.emit(line)

                if self._is_stopped:
                    break

                self.process.stdout.close()
                return_code = self.process.wait(timeout=self.timeout)

                if return_code != 0:
                    overall_return_code = return_code
                    self.logMessage.emit(f"Task failed with exit code {return_code}. Halting execution.")
                    break

            except subprocess.TimeoutExpired:
                self.process.kill()
                self.logMessage.emit(f"[ERROR] Command timed out after {self.timeout} seconds. Process terminated.")
                overall_return_code = -1
                break
            except FileNotFoundError:
                self.logMessage.emit(f"[ERROR] Command not found: {command[0]}")
                overall_return_code = -1
                break
            except Exception as e:
                self.logMessage.emit(f"[ERROR] An unexpected error occurred: {e}")
                overall_return_code = -1
                break

        self.taskFinished.emit(overall_return_code)

    def stop(self):
        self._is_stopped = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.logMessage.emit("Task terminated by user.")
            except Exception as e:
                self.logMessage.emit(f"Error terminating process: {e}")
