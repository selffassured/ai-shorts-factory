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

    def __init__(
        self,
        root: Path = Path("assets/gameplay"),
    ) -> None:
        self.root = root.resolve()

    def get_random_video(self, category: str) -> Path:
        """Возвращает случайное видео из категории."""

        clean_category = category.strip().lower()

        if not clean_category:
            raise ValueError(
                "Название категории не может быть пустым."
            )

        folder = self.root / clean_category

        if not folder.is_dir():
            raise FileNotFoundError(
                f"Категория '{clean_category}' не существует: {folder}"
            )

        videos = sorted(
            file.resolve()
            for file in folder.iterdir()
            if (
                file.is_file()
                and file.suffix.lower() in SUPPORTED_EXTENSIONS
            )
        )

        if not videos:
            raise FileNotFoundError(
                f"В категории '{clean_category}' нет поддерживаемых видео."
            )

        return random.choice(videos)

    def list_categories(self) -> list[str]:
        """Возвращает список доступных категорий."""

        if not self.root.is_dir():
            return []

        return sorted(
            folder.name
            for folder in self.root.iterdir()
            if folder.is_dir()
        )