from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class MediaInfoError(RuntimeError):
    """Ошибка получения информации о медиафайле."""


def ensure_ffprobe_available() -> None:
    """Проверяет наличие ffprobe в PATH."""

    if shutil.which("ffprobe") is None:
        raise MediaInfoError(
            "FFprobe не найден. Установи FFmpeg "
            "и перезапусти терминал."
        )


def get_media_duration(media_file: Path) -> float:
    """Возвращает длительность медиафайла в секундах."""

    ensure_ffprobe_available()

    media_file = media_file.resolve()

    if not media_file.is_file():
        raise FileNotFoundError(
            f"Медиафайл не найден: {media_file}"
        )

    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(media_file),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )

    if result.returncode != 0:
        raise MediaInfoError(
            "Не удалось определить длительность файла.\n"
            f"Вывод FFprobe:\n{result.stderr}"
        )

    try:
        duration = float(result.stdout.strip())
    except ValueError as error:
        raise MediaInfoError(
            "FFprobe вернул некорректную длительность: "
            f"{result.stdout!r}"
        ) from error

    if duration <= 0:
        raise MediaInfoError(
            f"Некорректная длительность файла: {duration}"
        )

    return duration