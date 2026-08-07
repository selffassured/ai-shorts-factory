from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SubtitleCue:
    """Одна реплика с временными границами."""

    start_seconds: float
    end_seconds: float
    text: str


def _parse_srt_timestamp(value: str) -> float:
    """Преобразует SRT-таймкод в секунды."""

    hours, minutes, seconds_milliseconds = value.split(":")
    seconds, milliseconds = seconds_milliseconds.split(",")

    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(milliseconds) / 1000
    )


def _format_ass_timestamp(seconds: float) -> str:
    """Преобразует секунды в таймкод ASS."""

    total_centiseconds = max(0, round(seconds * 100))

    hours, remainder = divmod(total_centiseconds, 360_000)
    minutes, remainder = divmod(remainder, 6_000)
    whole_seconds, centiseconds = divmod(remainder, 100)

    return (
        f"{hours}:"
        f"{minutes:02d}:"
        f"{whole_seconds:02d}."
        f"{centiseconds:02d}"
    )


def parse_srt(srt_path: Path) -> list[SubtitleCue]:
    """Читает SRT с отдельным таймингом для каждого слова."""

    srt_path = srt_path.resolve()

    if not srt_path.is_file():
        raise FileNotFoundError(
            f"SRT-файл не найден: {srt_path}"
        )

    content = srt_path.read_text(
        encoding="utf-8-sig"
    ).strip()

    if not content:
        raise ValueError("SRT-файл пуст.")

    blocks = re.split(r"\r?\n\r?\n+", content)
    cues: list[SubtitleCue] = []

    for block in blocks:
        lines = [
            line.strip()
            for line in block.splitlines()
            if line.strip()
        ]

        if len(lines) < 2:
            continue

        timing_index = 1 if lines[0].isdigit() else 0

        if timing_index >= len(lines):
            continue

        timing_line = lines[timing_index]

        if "-->" not in timing_line:
            continue

        start_raw, end_raw = [
            part.strip()
            for part in timing_line.split(
                "-->",
                maxsplit=1,
            )
        ]

        text = " ".join(
            lines[timing_index + 1 :]
        ).strip()

        if not text:
            continue

        start_seconds = _parse_srt_timestamp(start_raw)
        end_seconds = _parse_srt_timestamp(end_raw)

        if end_seconds <= start_seconds:
            end_seconds = start_seconds + 0.05

        cues.append(
            SubtitleCue(
                start_seconds=start_seconds,
                end_seconds=end_seconds,
                text=text,
            )
        )

    if not cues:
        raise ValueError(
            "В SRT-файле не найдено корректных субтитров."
        )

    return cues


def group_subtitle_cues(
    cues: list[SubtitleCue],
    min_words: int = 2,
    max_words: int = 4,
    max_duration: float = 2.2,
) -> list[SubtitleCue]:
    """
    Объединяет слова в короткие последовательные фразы.

    Новое предложение никогда не присоединяется
    к предыдущему предложению.
    """

    if min_words < 1:
        raise ValueError(
            "min_words должен быть не меньше 1."
        )

    if max_words < min_words:
        raise ValueError(
            "max_words не может быть меньше min_words."
        )

    if max_duration <= 0:
        raise ValueError(
            "max_duration должен быть больше нуля."
        )

    grouped: list[SubtitleCue] = []

    current_words: list[str] = []
    current_start: float | None = None
    current_end: float | None = None

    def flush_group() -> None:
        nonlocal current_words
        nonlocal current_start
        nonlocal current_end

        if (
            not current_words
            or current_start is None
            or current_end is None
        ):
            return

        grouped.append(
            SubtitleCue(
                start_seconds=current_start,
                end_seconds=current_end,
                text=" ".join(current_words),
            )
        )

        current_words = []
        current_start = None
        current_end = None

    for cue in cues:
        words = re.findall(r"\S+", cue.text)

        if not words:
            continue

        for word in words:
            # На случай, если один cue содержит несколько слов:
            # приблизительно используем время этого cue.
            word_start = cue.start_seconds
            word_end = cue.end_seconds

            # Если предыдущая группа уже закончилась знаком
            # препинания, закрываем её до начала нового слова.
            if (
                current_words
                and re.search(r"[.!?…]$", current_words[-1])
            ):
                flush_group()

            if current_start is None:
                current_start = word_start

            current_words.append(word)
            current_end = word_end

            duration = current_end - current_start

            reached_word_limit = (
                len(current_words) >= max_words
            )

            reached_duration_limit = (
                len(current_words) >= min_words
                and duration >= max_duration
            )

            reached_sentence_end = bool(
                re.search(r"[.!?…]$", word)
            )

            # Конец предложения закрывает группу независимо
            # от min_words. Так последнее одиночное слово
            # не попадёт в начало следующего предложения.
            if (
                reached_word_limit
                or reached_duration_limit
                or reached_sentence_end
            ):
                flush_group()

    flush_group()

    if not grouped:
        raise ValueError(
            "Не удалось сформировать группы субтитров."
        )

    return grouped


def _escape_ass_text(text: str) -> str:
    """Экранирует специальные символы ASS."""

    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )



def _ass_alpha_from_opacity(opacity_percent: int) -> int:
    """
    ASS использует обратную прозрачность:
    00 = непрозрачно, FF = прозрачно.
    """

    opacity_percent = max(0, min(100, opacity_percent))
    return round(255 * (100 - opacity_percent) / 100)


def _resolve_subtitle_position(
    position: str,
) -> tuple[int, int]:
    """Возвращает ASS Alignment и MarginV."""

    normalized = position.strip().lower()

    if normalized in {"центр", "center"}:
        return 5, 0

    if normalized in {
        "ниже",
        "ниже центра",
        "lower",
        "below",
    }:
        return 2, 520

    if normalized in {
        "вниз",
        "внизу",
        "низ",
        "bottom",
    }:
        return 2, 250

    return 2, 520


def _hex_to_ass_color(
    value: str,
    *,
    alpha: int = 0,
) -> str:
    """#RRGGBB -> ASS &HAABBGGRR."""

    clean = value.strip().lstrip("#")

    if len(clean) != 6:
        clean = "FFFFFF"

    try:
        red = int(clean[0:2], 16)
        green = int(clean[2:4], 16)
        blue = int(clean[4:6], 16)
    except ValueError:
        red, green, blue = 255, 255, 255

    alpha = max(0, min(255, alpha))
    return (
        f"&H{alpha:02X}"
        f"{blue:02X}{green:02X}{red:02X}"
    )


def _resolve_subtitle_style(
    style_name: str,
    background_opacity: int,
    text_color: str,
    outline_color: str,
) -> dict[str, str | int]:
    """Параметры ASS-стиля для финального рендера."""

    normalized = style_name.strip().lower()
    alpha = _ass_alpha_from_opacity(
        background_opacity
    )
    back_colour = f"&H{alpha:02X}000000"

    if normalized == "bold":
        return {
            "primary": _hex_to_ass_color(text_color),
            "secondary": _hex_to_ass_color(text_color),
            "outline_colour": _hex_to_ass_color(outline_color),
            "back_colour": back_colour,
            "border_style": 1,
            "outline": 6,
            "shadow": 2,
        }

    if normalized == "classic":
        return {
            "primary": _hex_to_ass_color(text_color),
            "secondary": _hex_to_ass_color(text_color),
            "outline_colour": _hex_to_ass_color(outline_color),
            "back_colour": back_colour,
            "border_style": 1,
            "outline": 4,
            "shadow": 1,
        }

    return {
        "primary": _hex_to_ass_color(text_color),
        "secondary": _hex_to_ass_color(text_color),
        "outline_colour": _hex_to_ass_color(outline_color),
        "back_colour": back_colour,
        "border_style": 1,
        "outline": 5,
        "shadow": 3,
    }


def generate_ass_subtitles(
    srt_path: Path,
    output_ass: Path,
    font_name: str = "Arial",
    font_size: int = 72,
    margin_vertical: int | None = None,
    min_words: int = 2,
    max_words: int = 4,
    max_duration: float = 2.2,
    style_name: str = "Glow",
    position: str = "Ниже",
    background_opacity: int = 72,
    text_color: str = "#FFFFFF",
    outline_color: str = "#E66BFF",
) -> Path:
    """Создаёт оформленные ASS-субтитры из SRT."""

    if font_size <= 0:
        raise ValueError(
            "Размер шрифта должен быть больше нуля."
        )

    if (
        margin_vertical is not None
        and margin_vertical < 0
    ):
        raise ValueError(
            "Отступ субтитров не может быть отрицательным."
        )

    if not 0 <= background_opacity <= 100:
        raise ValueError(
            "Прозрачность фона должна быть от 0 до 100."
        )

    alignment, resolved_margin = (
        _resolve_subtitle_position(position)
    )

    if margin_vertical is None:
        margin_vertical = resolved_margin

    style = _resolve_subtitle_style(
        style_name,
        background_opacity,
        text_color,
        outline_color,
    )

    raw_cues = parse_srt(srt_path)

    grouped_cues = group_subtitle_cues(
        cues=raw_cues,
        min_words=min_words,
        max_words=max_words,
        max_duration=max_duration,
    )

    output_ass = output_ass.resolve()
    output_ass.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},{style["primary"]},{style["secondary"]},{style["outline_colour"]},{style["back_colour"]},-1,0,0,0,100,100,0,0,{style["border_style"]},{style["outline"]},{style["shadow"]},{alignment},55,55,{margin_vertical},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events: list[str] = []

    for cue in grouped_cues:
        start = _format_ass_timestamp(
            cue.start_seconds
        )
        end = _format_ass_timestamp(
            cue.end_seconds
        )
        text = _escape_ass_text(cue.text)

        events.append(
            f"Dialogue: 0,{start},{end},"
            f"Default,,0,0,0,,{text}"
        )

    if not events:
        raise ValueError(
            "Не удалось создать события ASS."
        )

    output_ass.write_text(
        header + "\n".join(events) + "\n",
        encoding="utf-8",
    )

    return output_ass