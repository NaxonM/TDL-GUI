# Agent Onboarding Guide

## Overview
- **Purpose**: PyQt6 desktop GUI for operating the `tdl` CLI (Telegram downloader) located under `bin/tdl.exe`.
- **Entry point**: `src/main.py` initializes global services (settings, logger, theme) and launches `MainWindow` from `src/main_window.py`.
- **Primary responsibilities**: orchestrate `tdl` commands (downloads, uploads, forwarding, exports), handle authentication, and manage application updates.

## Directory Layout
- `src/`
  - `main.py`: application bootstrap.
  - `main_window.py`: central UI shell, tab management, global actions (settings, updater).
  - `tdl_runner.py` & `worker.py`: async execution of `tdl` subprocesses with signal-driven progress reporting.
  - `tdl_manager.py`: utilities for installing/upgrading the CLI binary.
  - `update_manager.py`: background download/update workflow for `tdl.exe` (uses `UpdateManager` + `UpdateDialog`).
  - `settings_manager.py`: persistent JSON settings stored under `QStandardPaths.AppConfigLocation`.
  - `logger.py`: central logger emitting to file (`app.log`) and UI via Qt signals.
  - `*_tab.py`: feature tabs (download, upload, export, chats, forward) sharing `TdlRunner` and settings instances.
  - Dialog helpers (e.g., `settings_dialog.py`, `login_dialog.py`, `advanced_*_dialog.py`) encapsulate modal workflows.
  - `styles/`: Qt stylesheet resources for theming.
- `tests/`: pytest-based unit tests covering dialogs, runners, and managers; requires PyQt6 with `pytest-qt` plugin.
- `bin/`: bundled `tdl.exe` binary provided with releases.
- `requirements.txt`: runtime dependencies (minimal — PyQt6 expected installed separately).
- `requirements-dev.txt`: developer tooling (`pytest`, `pytest-qt`, `ruff`).

## Key Flows
- **Command Execution**: `MainWindow` delegates to per-tab controllers which call `TdlRunner.run(...)`; runner spins up `Worker` threads to stream subprocess output back to the UI.
- **Update Check**: `MainWindow.check_for_updates()` hits GitHub releases, prompts user, then `start_update_process()` wires progress/error/finished signals to an `UpdateDialog` and the threaded `UpdateManager`.
- **Settings & Logs**: `SettingsManager` loads defaults and merges user overrides; `Logger` writes to `<AppConfig>/app.log` while broadcasting messages for the log tab.

## Recent Findings
- `tdl chat export` exposes a flattened `Message` field inside the filter environment; user input like `Message.Message` or `Message.Text` must be normalized to `Message` before compilation.
- The expr engine used by `tdl` understands string operators (`contains`, `startsWith`, `endsWith`) directly; avoid wrapping them in custom helper rewrites.
- When exporting with filters, keep infix syntax but ensure string literals remain quoted (e.g., `Message contains "#tag"`).

## Reference Resources Consulted
- **tdl Export Docs**: https://docs.iyear.me/tdl/guide/tools/export-messages/
- **tdl CLI Reference (`chat export`)**: https://docs.iyear.me/tdl/more/cli/tdl_chat_export/
- **tdl Forward Guide (filter examples)**: https://docs.iyear.me/tdl/guide/forward/
- **Expr Language Definition**: https://expr-lang.org/docs/language-definition
- **tdl Source Repository (field mappings)**: https://github.com/iyear/tdl
- **Local tdl Clone for Reference**: `C:\Users\Mehdi\Documents\Softwares\TDL-GUI\_external\tdl`

## Testing & Tooling
- Activate venv: `venv\Scripts\activate` (Windows). Install dev deps via `pip install -r requirements-dev.txt`.
- Run test suite: `pytest` (headless Qt via pytest-qt).
- Linting: `ruff` is available but not enforced by CI.

## Integration Tips for Agents
- Stick to existing Qt signal/slot patterns; UI components typically emit signals reconnected in `MainWindow._setup_connections()`.
- Respect threading boundaries: long-running work uses `QThread` + worker objects; avoid blocking the UI thread.
- When manipulating settings or logs, use the singletons instantiated in `main.py` (settings manager, logger) to ensure consistency.
- For new tabs or dialogs, follow conventions seen in existing `*_tab.py` and dialog modules to integrate with global controls and theming.
