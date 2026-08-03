from __future__ import annotations

import asyncio
from pathlib import Path

import edge_tts

DEFAULT_VOICE = "ru-RU-SvetlanaNeural"


class TTSError(RuntimeError):
    """Ошибка генерации озвучки."""


async def _synthesize_async(
    text: str,
    output_audio: Path,
    voice: str,
    rate: str,
    volume: str,
) -> None:
    communicator = edge_tts.Communicate(
        text=text,
        voice=voice,
        rate=rate,
        volume=volume,
    )
    await communicator.save(str(output_audio))


def synthesize_speech(
    text: str,
    output_audio: Path,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    volume: str = "+0%",
) -> Path:
    """Создаёт MP3-файл озвучки из текста."""

    clean_text = text.strip()

    if not clean_text:
        raise ValueError("Текст для озвучки не может быть пустым.")

    if output_audio.suffix.lower() != ".mp3":
        raise ValueError("Выходной файл озвучки должен иметь расширение .mp3.")

    output_audio = output_audio.resolve()
    output_audio.parent.mkdir(parents=True, exist_ok=True)

    try:
        asyncio.run(
            _synthesize_async(
                text=clean_text,
                output_audio=output_audio,
                voice=voice,
                rate=rate,
                volume=volume,
            )
        )
    except Exception as error:
        raise TTSError(f"Не удалось создать озвучку: {error}") from error

    if not output_audio.exists() or output_audio.stat().st_size == 0:
        raise TTSError("Файл озвучки не был создан или оказался пустым.")

    return output_audio