from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

import edge_tts

DEFAULT_VOICE = "ru-RU-SvetlanaNeural"


class TTSError(RuntimeError):
    """Ошибка генерации озвучки."""


@dataclass(frozen=True)
class SpeechResult:
    """Результат генерации речи."""

    audio_path: Path
    subtitles_path: Path


async def _synthesize_with_subtitles_async(
    text: str,
    output_audio: Path,
    output_subtitles: Path,
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

    submaker = edge_tts.SubMaker()

    with output_audio.open("wb") as audio_file:
       async for message in communicator.stream():
        message_type = message["type"]

        if message_type == "audio":
            audio_file.write(message["data"])
        elif message_type in ("WordBoundary", "SentenceBoundary"):
            submaker.feed(message)

    srt_content = submaker.get_srt()

    if not srt_content.strip():
      raise TTSError(
        "Edge TTS создал звук, но не вернул тайминги субтитров."
    )

    output_subtitles.write_text(
        srt_content,
        encoding="utf-8",
    )


def synthesize_speech_with_subtitles(
    text: str,
    output_audio: Path,
    output_subtitles: Path,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    volume: str = "+0%",
) -> SpeechResult:
    """Создаёт MP3 и синхронизированные SRT-субтитры."""

    clean_text = text.strip()

    if not clean_text:
        raise ValueError("Текст для озвучки не может быть пустым.")

    if output_audio.suffix.lower() != ".mp3":
        raise ValueError("Файл озвучки должен иметь расширение .mp3.")

    if output_subtitles.suffix.lower() != ".srt":
        raise ValueError("Файл субтитров должен иметь расширение .srt.")

    output_audio = output_audio.resolve()
    output_subtitles = output_subtitles.resolve()

    output_audio.parent.mkdir(parents=True, exist_ok=True)
    output_subtitles.parent.mkdir(parents=True, exist_ok=True)

    try:
        asyncio.run(
            _synthesize_with_subtitles_async(
                text=clean_text,
                output_audio=output_audio,
                output_subtitles=output_subtitles,
                voice=voice,
                rate=rate,
                volume=volume,
            )
        )
    except Exception as error:
        raise TTSError(
            f"Не удалось создать озвучку и субтитры: {error}"
        ) from error

    if not output_audio.exists() or output_audio.stat().st_size == 0:
        raise TTSError("Файл озвучки не был создан или оказался пустым.")

    if not output_subtitles.exists() or output_subtitles.stat().st_size == 0:
        raise TTSError("Файл субтитров не был создан или оказался пустым.")

    return SpeechResult(
        audio_path=output_audio,
        subtitles_path=output_subtitles,
    )


def synthesize_speech(
    text: str,
    output_audio: Path,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    volume: str = "+0%",
) -> Path:
    """Создаёт только MP3-файл озвучки."""

    temporary_subtitles = output_audio.with_suffix(".srt")

    result = synthesize_speech_with_subtitles(
        text=text,
        output_audio=output_audio,
        output_subtitles=temporary_subtitles,
        voice=voice,
        rate=rate,
        volume=volume,
    )

    temporary_subtitles.unlink(missing_ok=True)

    return result.audio_path