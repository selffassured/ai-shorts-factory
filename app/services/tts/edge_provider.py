from __future__ import annotations

import asyncio
import hashlib
import random
import shutil
import time
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import edge_tts

DEFAULT_VOICE = "ru-RU-SvetlanaNeural"
TICKS_PER_SECOND = 10_000_000


class TTSError(RuntimeError):
    """Ошибка генерации озвучки."""


@dataclass(frozen=True)
class SpeechResult:
    """Результат генерации речи."""

    audio_path: Path
    subtitles_path: Path


def _format_srt_timestamp(seconds: float) -> str:
    """Преобразует секунды в таймкод SRT."""

    total_milliseconds = max(0, round(seconds * 1000))

    hours, remainder = divmod(total_milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)

    return (
        f"{hours:02d}:"
        f"{minutes:02d}:"
        f"{whole_seconds:02d},"
        f"{milliseconds:03d}"
    )


def _normalize_word(value: str) -> str:
    """
    Убирает знаки препинания для сравнения слов.

    Например:
    'один.' -> 'один'
    'кто-то' -> 'кто-то'
    """

    return re.sub(
        r"[^\wа-яА-ЯёЁ-]",
        "",
        value,
    ).casefold()


def _tokenize_source_text(text: str) -> list[str]:
    """
    Разбивает исходный текст на слова,
    сохраняя знаки препинания.

    Например:
    'один. Возле' -> ['один.', 'Возле']
    """

    return re.findall(r"\S+", text)


def _restore_punctuation(
    source_text: str,
    word_events: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], str]]:
    """
    Сопоставляет слова Edge TTS с исходным текстом.

    Edge TTS обычно возвращает слова без точек и запятых.
    Здесь мы возвращаем знаки препинания из исходной истории.
    """

    source_tokens = _tokenize_source_text(source_text)
    restored: list[tuple[dict[str, Any], str]] = []

    source_index = 0

    for event in word_events:
        event_word = str(event.get("text", "")).strip()

        if not event_word:
            continue

        normalized_event = _normalize_word(event_word)
        restored_word = event_word

        while source_index < len(source_tokens):
            source_token = source_tokens[source_index]
            source_index += 1

            normalized_source = _normalize_word(source_token)

            if normalized_source == normalized_event:
                restored_word = source_token
                break

        restored.append((event, restored_word))

    return restored


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
        boundary="WordBoundary",
    )

    word_events: list[dict[str, Any]] = []

    with output_audio.open("wb") as audio_file:
        async for message in communicator.stream():
            message_type = message["type"]

            if message_type == "audio":
                audio_file.write(message["data"])

            elif message_type == "WordBoundary":
                word_events.append(message)

    if not word_events:
        raise TTSError(
            "Edge TTS создал звук, но не вернул тайминги слов."
        )

    restored_events = _restore_punctuation(
        source_text=text,
        word_events=word_events,
    )

    srt_blocks: list[str] = []

    for index, (event, restored_word) in enumerate(
        restored_events,
        start=1,
    ):
        offset_ticks = int(event["offset"])
        duration_ticks = int(event["duration"])

        start_seconds = offset_ticks / TICKS_PER_SECOND
        end_seconds = (
            offset_ticks + duration_ticks
        ) / TICKS_PER_SECOND

        if end_seconds <= start_seconds:
            end_seconds = start_seconds + 0.05

        srt_blocks.append(
            "\n".join(
                (
                    str(index),
                    (
                        f"{_format_srt_timestamp(start_seconds)} --> "
                        f"{_format_srt_timestamp(end_seconds)}"
                    ),
                    restored_word,
                )
            )
        )

    if not srt_blocks:
        raise TTSError(
            "Не удалось сформировать субтитры из таймингов слов."
        )

    output_subtitles.write_text(
        "\n\n".join(srt_blocks) + "\n",
        encoding="utf-8",
    )


def _tts_cache_paths(
    text: str,
    voice: str,
    rate: str,
    volume: str,
) -> tuple[Path, Path]:
    """Возвращает пути к кэшированным MP3/SRT."""

    cache_key = hashlib.sha1(
        (
            f"{voice}|{rate}|{volume}|{text}"
        ).encode("utf-8")
    ).hexdigest()

    cache_dir = Path(".cache") / "tts"
    cache_dir.mkdir(parents=True, exist_ok=True)

    return (
        cache_dir / f"{cache_key}.mp3",
        cache_dir / f"{cache_key}.srt",
    )


def synthesize_speech_with_subtitles(
    text: str,
    output_audio: Path,
    output_subtitles: Path,
    voice: str = DEFAULT_VOICE,
    rate: str = "+0%",
    volume: str = "+0%",
) -> SpeechResult:
    """Создаёт MP3 и SRT с точными таймингами слов."""

    clean_text = text.strip()

    if not clean_text:
        raise ValueError(
            "Текст для озвучки не может быть пустым."
        )

    if output_audio.suffix.lower() != ".mp3":
        raise ValueError(
            "Файл озвучки должен иметь расширение .mp3."
        )

    if output_subtitles.suffix.lower() != ".srt":
        raise ValueError(
            "Файл субтитров должен иметь расширение .srt."
        )

    output_audio = output_audio.resolve()
    output_subtitles = output_subtitles.resolve()

    output_audio.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    output_subtitles.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    cache_audio, cache_subtitles = _tts_cache_paths(
        clean_text,
        voice,
        rate,
        volume,
    )

    # Повторный рендер того же текста/голоса не обращается к Edge TTS.
    if (
        cache_audio.is_file()
        and cache_audio.stat().st_size > 0
        and cache_subtitles.is_file()
        and cache_subtitles.stat().st_size > 0
    ):
        shutil.copy2(cache_audio, output_audio)
        shutil.copy2(cache_subtitles, output_subtitles)
        return SpeechResult(
            audio_path=output_audio,
            subtitles_path=output_subtitles,
        )

    last_error: Exception | None = None

    for attempt in range(1, 4):
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
            last_error = None
            break
        except Exception as error:
            last_error = error

            for partial in (
                output_audio,
                output_subtitles,
            ):
                try:
                    partial.unlink(missing_ok=True)
                except OSError:
                    pass

            if attempt < 3:
                time.sleep(
                    0.6 * attempt
                    + random.uniform(0.05, 0.25)
                )

    if last_error is not None:
        raise TTSError(
            "Не удалось создать озвучку после 3 попыток. "
            f"Голос: {voice}. Причина: {last_error}"
        ) from last_error

    if (
        not output_audio.is_file()
        or output_audio.stat().st_size == 0
    ):
        raise TTSError(
            "Файл озвучки не был создан или оказался пустым."
        )

    if (
        not output_subtitles.is_file()
        or output_subtitles.stat().st_size == 0
    ):
        raise TTSError(
            "Файл субтитров не был создан или оказался пустым."
        )

    try:
        shutil.copy2(output_audio, cache_audio)
        shutil.copy2(output_subtitles, cache_subtitles)
    except OSError:
        # Кэш — оптимизация, а не обязательная часть рендера.
        pass

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