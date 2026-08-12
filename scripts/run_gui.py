from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.gui.main_window import MainWindow


def _resource_path(relative: str) -> Path:
    """Путь к ресурсу в source-режиме и PyInstaller."""
    if getattr(sys, "frozen", False):
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parents[1]

    return base / relative


def main() -> int:
    application = QApplication(sys.argv)
    application.setApplicationName(
        "AI Shorts Factory"
    )

    icon_path = _resource_path(
        "ai_shorts_factory.ico"
    )
    if icon_path.is_file():
        application.setWindowIcon(
            QIcon(str(icon_path))
        )

    window = MainWindow()
    window.show()

    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())