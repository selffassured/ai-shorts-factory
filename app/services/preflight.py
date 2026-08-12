from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from app.services.gameplay.library import GameplayLibrary


MIN_FREE_DISK_BYTES = 250 * 1024 * 1024


def validate_generation(
    *,
    story: str,
    gameplay: str | Path,
    output_video: Path,
    voice: str | None,
    music: Path | None,
    width: int,
    height: int,
    fps: int,
) -> list[str]:
    """Проверяет очевидные проблемы до запуска рендера."""

    problems: list[str] = []

    if not story.strip():
        problems.append("Добавь текст истории.")

    if not voice:
        problems.append("Выбери голос озвучки.")

    if shutil.which("ffmpeg") is None:
        problems.append("FFmpeg не найден в PATH.")

    if shutil.which("ffprobe") is None:
        problems.append("FFprobe не найден в PATH.")

    if width <= 0 or height <= 0:
        problems.append("Некорректное разрешение экспорта.")

    if fps not in {24, 25, 30, 50, 60}:
        problems.append(f"Некорректный FPS: {fps}.")

    gameplay_value = str(gameplay).strip()

    if not gameplay_value or gameplay_value == "Выбрать":
        problems.append("Выбери gameplay.")
    else:
        direct_path = Path(gameplay_value)

        if not direct_path.is_file():
            try:
                videos = GameplayLibrary().list_videos(
                    gameplay_value
                )
            except (OSError, ValueError):
                videos = []

            if not videos:
                problems.append(
                    "В выбранной категории gameplay "
                    "нет доступных видео."
                )

    if music is not None and not music.is_file():
        problems.append(
            "Выбранный музыкальный файл "
            "больше не существует."
        )

    output_dir = Path(output_video).parent

    try:
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        with tempfile.NamedTemporaryFile(
            prefix=".ai_shorts_write_test_",
            dir=output_dir,
            delete=True,
        ):
            pass

        free_bytes = shutil.disk_usage(output_dir).free

        if free_bytes < MIN_FREE_DISK_BYTES:
            problems.append(
                "На диске осталось меньше 250 МБ "
                "свободного места."
            )

    except OSError:
        problems.append(
            "Нет доступа на запись в папку "
            "для готового видео."
        )

    return problems
