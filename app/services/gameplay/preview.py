from __future__ import annotations

import hashlib
import shutil
import subprocess
import tempfile
from pathlib import Path


class GameplayPreviewError(RuntimeError):
    """Ошибка создания кадра предпросмотра."""


def ensure_ffmpeg_available() -> None:
    """Проверяет наличие FFmpeg в PATH."""

    if shutil.which("ffmpeg") is None:
        raise GameplayPreviewError(
            "FFmpeg не найден. Установи FFmpeg "
            "и перезапусти терминал."
        )


def create_gameplay_preview(
    video_path: Path,
    *,
    width: int = 480,
    height: int = 854,
    timestamp_seconds: float = 1.0,
) -> Path:
    """
    Создаёт вертикальный JPG-кадр для быстрого GUI-preview.

    Результаты кэшируются во временной папке, поэтому повторный
    выбор того же ролика не запускает FFmpeg заново.
    """

    ensure_ffmpeg_available()

    video_path = video_path.resolve()

    if not video_path.is_file():
        raise FileNotFoundError(
            f"Видео для предпросмотра не найдено: {video_path}"
        )

    stat = video_path.stat()
    cache_key = hashlib.sha1(
        (
            f"{video_path}|{stat.st_mtime_ns}|{stat.st_size}|"
            f"{width}x{height}|{timestamp_seconds}"
        ).encode("utf-8")
    ).hexdigest()

    cache_dir = (
        Path(tempfile.gettempdir())
        / "ai_shorts_factory"
        / "gameplay_previews"
    )
    cache_dir.mkdir(parents=True, exist_ok=True)

    output_path = cache_dir / f"{cache_key}.jpg"

    if output_path.is_file() and output_path.stat().st_size > 0:
        return output_path

    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height}"
    )

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        str(max(0.0, timestamp_seconds)),
        "-i",
        str(video_path),
        "-frames:v",
        "1",
        "-vf",
        video_filter,
        "-q:v",
        "3",
        str(output_path),
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
        raise GameplayPreviewError(
            "Не удалось создать кадр предпросмотра.\n"
            f"FFmpeg: {result.stderr.strip()}"
        )

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise GameplayPreviewError(
            "FFmpeg завершился без ошибки, "
            "но кадр предпросмотра не был создан."
        )

    return output_path
