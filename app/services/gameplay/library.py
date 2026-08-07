from __future__ import annotations

import random
import shutil
from pathlib import Path


SUPPORTED_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".avi",
    ".mkv",
    ".webm",
}


class GameplayLibrary:
    """Локальная библиотека игровых роликов."""

    def __init__(
        self,
        root: Path = Path("assets/gameplay"),
    ) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _category_folder(self, category: str) -> Path:
        clean = category.strip()
        if not clean:
            raise ValueError("Название категории не может быть пустым.")
        return self.root / clean

    def list_categories(self) -> list[str]:
        return sorted(
            folder.name
            for folder in self.root.iterdir()
            if folder.is_dir()
        )

    def list_videos(self, category: str) -> list[Path]:
        folder = self._category_folder(category)

        if not folder.is_dir():
            return []

        return sorted(
            file.resolve()
            for file in folder.iterdir()
            if (
                file.is_file()
                and file.suffix.lower() in SUPPORTED_EXTENSIONS
            )
        )

    def get_random_video(self, category: str) -> Path:
        videos = self.list_videos(category)

        if not videos:
            raise FileNotFoundError(
                f"В категории '{category}' нет поддерживаемых видео."
            )

        return random.choice(videos)

    def create_category(self, category: str) -> Path:
        folder = self._category_folder(category)
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def add_video(
        self,
        category: str,
        source: Path,
    ) -> Path:
        source = Path(source).resolve()

        if not source.is_file():
            raise FileNotFoundError(
                f"Видео не найдено: {source}"
            )

        if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
            raise ValueError(
                f"Неподдерживаемый формат: {source.suffix}"
            )

        folder = self.create_category(category)
        target = folder / source.name

        if target.exists():
            stem = source.stem
            suffix = source.suffix
            index = 2

            while target.exists():
                target = folder / f"{stem}_{index}{suffix}"
                index += 1

        shutil.copy2(source, target)
        return target.resolve()

    def delete_video(self, video: Path) -> None:
        video = Path(video).resolve()

        try:
            video.relative_to(self.root)
        except ValueError as error:
            raise ValueError(
                "Можно удалять только видео из gameplay-библиотеки."
            ) from error

        if video.is_file():
            video.unlink()

    def delete_category(self, category: str) -> None:
        folder = self._category_folder(category)

        try:
            folder.resolve().relative_to(self.root)
        except ValueError as error:
            raise ValueError("Некорректная категория.") from error

        if folder.is_dir():
            shutil.rmtree(folder)
