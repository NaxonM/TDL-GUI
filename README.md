# TDL GUI

A modern, feature-rich graphical user interface for the `tdl` command-line tool, built with PyQt6 for Windows.

This application provides an intuitive way to access the powerful features of `tdl` without needing to use the command line. It is designed to be user-friendly, robust, and self-sufficient.

## Features

- **Automatic `tdl` Installation**: The GUI automatically detects if `tdl` is missing and downloads the correct version for your system.
- **Light & Dark Themes**: Automatically detects your system's theme and applies a modern, harmonious color scheme for excellent readability.
- **Comprehensive Download Tab**:
    - Download from multiple message links or JSON files.
    - Full control over advanced options like concurrency, file filtering, and naming templates.
    - Collapsible "Advanced Options" section for a clean and compact layout.
- **Intuitive Export Tab**:
    - A guided workflow to export message data from any chat.
    - Filter by time range, message ID range, or the last N messages.
- **Full Account Management**:
    - Automatically discovers all your logged-in `tdl` accounts (namespaces).
    - Easily switch between accounts or log into new ones via the Settings dialog.
- **Hybrid Progress Display**:
    - A "Live Downloads" area shows a separate progress bar for each channel you are downloading from.
    - The main status bar displays the total, aggregate progress and live stats (speed, ETA) for the entire download batch.
- **Robust Error & Process Handling**:
    - A configurable command timeout prevents the application from hanging on stalled processes.
    - Gracefully stops background tasks when the application is closed.
    - Provides a "Reset All Data" option in the settings to safely clear all `tdl` login sessions and data.

## Requirements

- Windows 10 or newer.
- Python 3.8+

## How to Use

Simply double-click the **`start.bat`** file to launch the application.

The script is intelligent and will handle the setup for you:
- If you already have the required `PyQt6` library installed on your system, the application will start immediately.
- If `PyQt6` is missing, the script will prompt you to automatically create a local, sandboxed environment and install it. Just follow the on-screen instructions.

## Development & Testing

To contribute to development, you'll need to install the testing dependencies:
```bash
pip install -r requirements-dev.txt
```

You can run the full test suite using `pytest`:
```bash
pytest
```

This project uses `ruff` for linting and formatting. You can check the code for issues with:
```bash
ruff check .
```

To automatically fix issues, run:
```bash
ruff check . --fix
```

## Screenshots

*(Placeholder for screenshots of the application)*

### Main Window (Dark Theme)
![image](https://github.com/user-attachments/assets/953288f5-9653-4351-b857-e6f6630f9a2d)


### Download Tab
![image](https://github.com/user-attachments/assets/05a6119b-c29b-43d9-a72a-f9b8c081e7d8)


### Export Tab
![image](https://github.com/user-attachments/assets/382d56d8-9993-4f9e-a8aa-536413233816)


### Settings Dialog
![image](https://github.com/user-attachments/assets/34f9a15c-3435-430c-a991-309a47464016)
