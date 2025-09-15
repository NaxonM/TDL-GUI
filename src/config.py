from PyQt6.QtGui import QColor

# Configuration for utility commands
UTILITY_CONFIGS = {
    "export_members_by_id": {
        "title": "Export Members by ID",
        "base_cmd": ["tdl", "chat", "users"],
        "fields": [
            {"name": "chat_id", "label": "Chat ID or Username:", "arg": "-c"},
            {
                "name": "output_file",
                "label": "Output JSON File:",
                "arg": "-o",
                "type": "save_file",
            },
        ],
    },
    "backup_data": {
        "title": "Backup Data",
        "base_cmd": ["tdl", "backup"],
        "fields": [
            {
                "name": "output_file",
                "label": "Backup File Path:",
                "arg": "-d",
                "type": "save_file",
            }
        ],
    },
    "recover_data": {
        "title": "Recover Data",
        "base_cmd": ["tdl", "recover"],
        "fields": [
            {
                "name": "input_file",
                "label": "Backup File to Restore:",
                "arg": "-f",
                "type": "open_file",
            }
        ],
    },
    "migrate_data": {
        "title": "Migrate Data",
        "base_cmd": ["tdl", "migrate"],
        "fields": [
            {
                "name": "destination",
                "label": "Destination Storage (e.g., type=file,path=...):",
                "arg": "--to",
            }
        ],
    },
}

CHAT_NAME_COLORS = [
    QColor("#1ABC9C"),
    QColor("#2ECC71"),
    QColor("#3498DB"),
    QColor("#9B59B6"),
    QColor("#34495E"),
    QColor("#F1C40F"),
    QColor("#E67E22"),
    QColor("#E74C3C"),
    QColor("#95A5A6"),
    QColor("#16A085"),
    QColor("#27AE60"),
    QColor("#2980B9"),
    QColor("#8E44AD"),
    QColor("#2C3E50"),
    QColor("#F39C12"),
    QColor("#D35400"),
    QColor("#C0392B"),
    QColor("#7F8C8D"),
]
