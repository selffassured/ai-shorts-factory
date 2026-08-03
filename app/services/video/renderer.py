from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class VideoRenderError(RuntimeError):
    """Ошибка во время обработки видео."""


def ensure_ffmpeg_available() -> None:
    """Проверяет, доступен ли FFmpeg в PATH."""

    if shutil.which("ffmpeg") is None:
        raise VideoRenderError(
            "FFmpeg не найден. Установите FFmpeg и перезапустите терминал."
        )


def render_vertical_video(
    input_video: Path,
    output_video: Path,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
) -> Path:
    """
    Преобразует видео в вертикальный формат.

    Видео масштабируется с сохранением пропорций,
    после чего лишние края обрезаются по центру.
    """

    ensure_ffmpeg_available()

    input_video = input_video.resolve()
    output_video = output_video.resolve()

    if not input_video.exists():
        raise FileNotFoundError(f"Исходное видео не найдено: {input_video}")

    if input_video.suffix.lower() not in {".mp4", ".mov", ".mkv", ".avi", ".webm"}:
        raise ValueError(
            f"Неподдерживаемый формат видео: {input_video.suffix}"
        )

    output_video.parent.mkdir(parents=True, exist_ok=True)

    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"fps={fps}"
    )

    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(input_video),
        "-vf",
        video_filter,
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-an",
        "-movflags",
        "+faststart",
        str(output_video),
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if result.returncode != 0:
        raise VideoRenderError(
            "FFmpeg не смог обработать видео.\n"
            f"Код ошибки: {result.returncode}\n"
            f"Вывод FFmpeg:\n{result.stderr}"
        )

    if not output_video.exists():
        raise VideoRenderError(
            "FFmpeg завершился без ошибки, но выходной файл не был создан."
        )

    return output_video