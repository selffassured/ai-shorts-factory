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
        check=False
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


def render_video_with_audio(
    input_video: Path,
    input_audio: Path,
    output_video: Path,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
) -> Path:
    """
    Создаёт вертикальное видео с внешней аудиодорожкой.

    Исходный звук геймплея не используется.
    Геймплей повторяется до окончания аудиодорожки.
    """

    ensure_ffmpeg_available()

    input_video = input_video.resolve()
    input_audio = input_audio.resolve()
    output_video = output_video.resolve()

    if not input_video.exists():
        raise FileNotFoundError(f"Исходное видео не найдено: {input_video}")

    if not input_audio.exists():
        raise FileNotFoundError(f"Аудиофайл не найден: {input_audio}")

    supported_video_formats = {".mp4", ".mov", ".mkv", ".avi", ".webm"}
    supported_audio_formats = {".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac"}

    if input_video.suffix.lower() not in supported_video_formats:
        raise ValueError(
            f"Неподдерживаемый формат видео: {input_video.suffix}"
        )

    if input_audio.suffix.lower() not in supported_audio_formats:
        raise ValueError(
            f"Неподдерживаемый формат аудио: {input_audio.suffix}"
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

        # Повторяем геймплей до окончания озвучки.
        "-stream_loop",
        "-1",
        "-i",
        str(input_video),

        # Внешняя аудиодорожка.
        "-i",
        str(input_audio),

        "-vf",
        video_filter,

        # Берём только изображение из геймплея.
        "-map",
        "0:v:0",

        # Берём только внешнюю аудиодорожку.
        "-map",
        "1:a:0",

        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",
        "-b:a",
        "192k",

        # Завершаем ролик вместе с аудио.
        "-shortest",
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
        check=False,
    )

    if result.returncode != 0:
        raise VideoRenderError(
            "FFmpeg не смог объединить видео и аудио.\n"
            f"Код ошибки: {result.returncode}\n"
            f"Вывод FFmpeg:\n{result.stderr}"
        )

    if not output_video.exists():
        raise VideoRenderError(
            "FFmpeg завершился без ошибки, но видео не было создано."
        )

    return output_video

def render_video_with_voice_and_music(
    input_video: Path,
    voice_audio: Path,
    background_music: Path,
    output_video: Path,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
    voice_volume: float = 1.0,
    music_volume: float = 0.12,
) -> Path:
    """
    Создаёт вертикальное видео с озвучкой и фоновой музыкой.

    Исходный звук геймплея не используется.
    Геймплей и музыка повторяются до окончания озвучки.
    """

    ensure_ffmpeg_available()

    input_video = input_video.resolve()
    voice_audio = voice_audio.resolve()
    background_music = background_music.resolve()
    output_video = output_video.resolve()

    for path, description in (
        (input_video, "Исходное видео"),
        (voice_audio, "Файл озвучки"),
        (background_music, "Фоновая музыка"),
    ):
        if not path.exists():
            raise FileNotFoundError(f"{description} не найден: {path}")

    if not 0.0 <= voice_volume <= 2.0:
        raise ValueError("Громкость голоса должна находиться в диапазоне 0–2.")

    if not 0.0 <= music_volume <= 1.0:
        raise ValueError("Громкость музыки должна находиться в диапазоне 0–1.")

    output_video.parent.mkdir(parents=True, exist_ok=True)

    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"fps={fps}"
    )

    audio_filter = (
        f"[1:a]volume={voice_volume}[voice];"
        f"[2:a]volume={music_volume}[music];"
        "[voice][music]"
        "amix=inputs=2:duration=first:dropout_transition=2,"
        "alimiter=limit=0.95"
        "[mixed_audio]"
    )

    command = [
        "ffmpeg",
        "-y",

        # Зацикливаем геймплей.
        "-stream_loop",
        "-1",
        "-i",
        str(input_video),

        # Основная озвучка.
        "-i",
        str(voice_audio),

        # Зацикливаем фоновую музыку.
        "-stream_loop",
        "-1",
        "-i",
        str(background_music),

        "-vf",
        video_filter,

        "-filter_complex",
        audio_filter,

        # Берём только изображение из геймплея.
        "-map",
        "0:v:0",

        # Берём только смешанный голос и музыку.
        "-map",
        "[mixed_audio]",

        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",

        "-c:a",
        "aac",
        "-b:a",
        "192k",

        # Ролик заканчивается вместе с озвучкой.
        "-shortest",
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
        check=False
    )

    if result.returncode != 0:
        raise VideoRenderError(
            "FFmpeg не смог смешать голос и музыку.\n"
            f"Код ошибки: {result.returncode}\n"
            f"Вывод FFmpeg:\n{result.stderr}"
        )

    if not output_video.exists():
        raise VideoRenderError(
            "FFmpeg завершился без ошибки, но видео не было создано."
        )

    return output_video


def render_video_with_audio_and_ass_subtitles(
    input_video: Path,
    input_audio: Path,
    subtitles_ass: Path,
    output_video: Path,
    width: int = 1080,
    height: int = 1920,
    fps: int = 30,
) -> Path:
    """Создаёт вертикальное видео с голосом и ASS-субтитрами."""

    ensure_ffmpeg_available()

    input_video = input_video.resolve()
    input_audio = input_audio.resolve()
    subtitles_ass = subtitles_ass.resolve()
    output_video = output_video.resolve()

    for path, description in (
        (input_video, "Исходное видео"),
        (input_audio, "Озвучка"),
        (subtitles_ass, "ASS-субтитры"),
    ):
        if not path.exists():
            raise FileNotFoundError(f"{description} не найдены: {path}")

    output_video.parent.mkdir(parents=True, exist_ok=True)

    subtitle_path = subtitles_ass.as_posix().replace(":", r"\:")

    video_filter = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},"
        f"fps={fps},"
        f"ass='{subtitle_path}'"
    )

    command = [
        "ffmpeg",
        "-y",
        "-stream_loop",
        "-1",
        "-i",
        str(input_video),
        "-i",
        str(input_audio),
        "-vf",
        video_filter,
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "20",
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "192k",
        "-shortest",
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
        check=False,
    )

    if result.returncode != 0:
        raise VideoRenderError(
            "FFmpeg не смог встроить ASS-субтитры.\n"
            f"Код ошибки: {result.returncode}\n"
            f"Вывод FFmpeg:\n{result.stderr}"
        )

    if not output_video.exists():
        raise VideoRenderError(
            "FFmpeg завершился без ошибки, но видео не было создано."
        )

    return output_video