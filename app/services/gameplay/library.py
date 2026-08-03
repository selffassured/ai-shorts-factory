from __future__ import annotations

import random
from pathlib import Path

SUPPORTED_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
}


class GameplayLibrary:
    """Библиотека игровых роликов."""

    def __init__(self, root: Path = Path("assets/gameplay")):
        self.root = root.resolve()

    def get_random_video(self, category: str) -> Path:
        folder = self.root / category

        if not folder.exists():
            raise FileNotFoundError(
                f"Категория '{category}' не существует."
            )

        videos = [
            file
            for file in folder.iterdir()
            if file.suffix.lower() in SUPPORTED_EXTENSIONS
        ]

        if not videos:
            raise FileNotFoundError(
                f"В категории '{category}' нет видео."
            )

        return random.choice(videos)

    def list_categories(self) -> list[str]:
        if not self.root.exists():
            return []

        return sorted(
            folder.name
            for folder in self.root.iterdir()
            if folder.is_dir()
        )