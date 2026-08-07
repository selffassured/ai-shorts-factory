from __future__ import annotations

from pathlib import Path


def format_user_error(error: BaseException) -> str:
    """Преобразует техническую ошибку в понятное сообщение для GUI."""

    raw = str(error).strip()
    lowered = raw.lower()

    if not raw:
        return (
            "Произошла неизвестная ошибка. "
            "Попробуй ещё раз."
        )

    if (
        "no audio was received" in lowered
        or "noaudioreceived" in lowered
        or "edge tts" in lowered
        or "озвучк" in lowered
    ):
        return (
            "Не удалось получить озвучку от сервиса.\n\n"
            "Проверь интернет и попробуй ещё раз. "
            "Если ошибка повторяется — выбери другой голос."
        )

    if "ffmpeg не найден" in lowered:
        return (
            "FFmpeg не найден.\n\n"
            "Установи FFmpeg или добавь его в PATH, "
            "затем перезапусти программу."
        )

    if (
        "permission denied" in lowered
        or "access is denied" in lowered
        or "отказано в доступе" in lowered
    ):
        return (
            "Нет доступа к файлу или папке.\n\n"
            "Закрой файл в других программах или выбери "
            "другую папку для сохранения."
        )

    if (
        "no space left" in lowered
        or "not enough space" in lowered
        or "недостаточно места" in lowered
    ):
        return (
            "Недостаточно свободного места на диске "
            "для создания видео."
        )

    if (
        "фонова" in lowered
        and "не найден" in lowered
    ):
        return (
            "Выбранный музыкальный файл больше не существует.\n\n"
            "Выбери музыку заново или установи «Без музыки»."
        )

    if (
        "геймп" in lowered
        and (
            "не найден" in lowered
            or "нет поддерживаемых видео" in lowered
        )
    ):
        return (
            "Не удалось найти выбранный gameplay.\n\n"
            "Открой библиотеку геймплея и выбери "
            "существующее видео."
        )

    if (
        "invalid data found" in lowered
        or "moov atom not found" in lowered
        or "could not find codec" in lowered
        or "ошибка ffprobe" in lowered
        or "ffprobe" in lowered
    ):
        return (
            "Не удалось прочитать один из медиафайлов.\n\n"
            "Возможно, видео или аудио повреждено. "
            "Попробуй другой файл."
        )

    if (
        "не смог создать short" in lowered
        or "ffmpeg" in lowered
    ):
        return (
            "FFmpeg не смог собрать итоговый Short.\n\n"
            "Проверь gameplay и музыку. Если ошибка "
            "повторится с другим файлом — пришли лог ошибки."
        )

    if isinstance(error, FileNotFoundError):
        return (
            "Не найден необходимый файл.\n\n"
            f"{raw}"
        )

    if isinstance(error, ValueError):
        return raw

    return (
        "Не удалось создать Short.\n\n"
        f"{raw}"
    )


def safe_remove(path: Path) -> None:
    """Удаляет незавершённый файл, не маскируя исходную ошибку."""

    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass
