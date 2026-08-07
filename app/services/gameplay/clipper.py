from __future__ import annotations

import random
import shutil
import subprocess
from pathlib import Path

from app.services.video.video_info import get_media_duration


class GameplayClipError(RuntimeError):
    """Ошибка подготовки фрагмента геймплея."""


def ensure_ffmpeg_available() -> None:
    """Проверяет наличие FFmpeg в PATH."""

    if shutil.which("ffmpeg") is None:
        raise GameplayClipError(
            "FFmpeg не найден. Установи FFmpeg "
            "и перезапусти терминал."
        )


def choose_random_start(
    video_duration: float,
    required_duration: float,
) -> float:
    """Выбирает случайную безопасную точку начала."""

    if video_duration <= 0:
        raise ValueError(
            "Длительность геймплея должна быть больше нуля."
        )

    if required_duration <= 0:
        raise ValueError(
            "Требуемая длительность должна быть больше нуля."
        )

    maximum_start = video_duration - required_duration

    if maximum_start <= 0:
        return 0.0

    return random.uniform(0.0, maximum_start)


def prepare_gameplay_segment(
    input_video: Path,
    output_video: Path,
    required_duration: float,
) -> Path:
    """
    Вырезает случайный фрагмент геймплея.

    Если исходное видео короче озвучки, возвращает исходный
    файл: существующий рендерер сам зациклит геймплей.
    """

    ensure_ffmpeg_available()

    input_video = input_video.resolve()
    output_video = output_video.resolve()

    if not input_video.is_file():
        raise FileNotFoundError(
            f"Геймплей не найден: {input_video}"
        )

    if required_duration <= 0:
        raise ValueError(
            "Длительность фрагмента должна быть больше нуля."
        )

    video_duration = get_media_duration(input_video)

    # Нет смысла вырезать фрагмент, если видео недостаточно длинное.
    if video_duration <= required_duration + 0.5:
        return input_video

    start_seconds = choose_random_start(
        video_duration=video_duration,
        required_duration=required_duration,
    )

    output_video.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    command = [
        "ffmpeg",
        "-y",

        # Быстрый переход к случайной позиции.
        "-ss",
        f"{start_seconds:.3f}",

        "-i",
        str(input_video),

        # Вырезаем фрагмент немного длиннее озвучки.
        "-t",
        f"{required_duration + 0.25:.3f}",

        # Используем только видео, звук игры удаляем.
        "-map",
        "0:v:0",
        "-an",

        # ВАЖНО: здесь больше не перекодируем видео.
        # Финальный renderer всё равно перекодирует его один раз,
        # поэтому повторный libx264 на промежуточном этапе только
        # тратил CPU и время.
        "-c:v",
        "copy",
        "-reset_timestamps",
        "1",
        "-avoid_negative_ts",
        "make_zero",

        str(output_video),
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
        raise GameplayClipError(
            "FFmpeg не смог подготовить случайный "
            "фрагмент геймплея.\n"
            f"Точка начала: {start_seconds:.3f} сек.\n"
            f"Код ошибки: {result.returncode}\n"
            f"Вывод FFmpeg:\n{result.stderr}"
        )

    if (
        not output_video.is_file()
        or output_video.stat().st_size == 0
    ):
        raise GameplayClipError(
            "Фрагмент геймплея не был создан."
        )

    print(
        "Выбран фрагмент геймплея: "
        f"{start_seconds:.2f}–"
        f"{start_seconds + required_duration:.2f} сек."
    )

    return output_video