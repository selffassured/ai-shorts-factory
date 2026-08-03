from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class SubtitleCue:
    start_seconds: float
    end_seconds: float
    text: str


def _parse_srt_timestamp(value: str) -> float:
    hours, minutes, seconds_milliseconds = value.split(":")
    seconds, milliseconds = seconds_milliseconds.split(",")

    return (
        int(hours) * 3600
        + int(minutes) * 60
        + int(seconds)
        + int(milliseconds) / 1000
    )


def _format_ass_timestamp(seconds: float) -> str:
    total_centiseconds = max(0, round(seconds * 100))

    hours, remainder = divmod(total_centiseconds, 360000)
    minutes, remainder = divmod(remainder, 6000)
    whole_seconds, centiseconds = divmod(remainder, 100)

    return (
        f"{hours}:"
        f"{minutes:02d}:"
        f"{whole_seconds:02d}."
        f"{centiseconds:02d}"
    )


def parse_srt(srt_path: Path) -> list[SubtitleCue]:
    """Читает SRT и возвращает список реплик."""

    srt_path = srt_path.resolve()

    if not srt_path.exists():
        raise FileNotFoundError(f"SRT-файл не найден: {srt_path}")

    content = srt_path.read_text(encoding="utf-8-sig").strip()

    if not content:
        raise ValueError("SRT-файл пуст.")

    blocks = re.split(r"\r?\n\r?\n+", content)
    cues: list[SubtitleCue] = []

    for block in blocks:
        lines = [line.strip() for line in block.splitlines() if line.strip()]

        if len(lines) < 2:
            continue

        timing_index = 1 if lines[0].isdigit() else 0

        if timing_index >= len(lines) or "-->" not in lines[timing_index]:
            continue

        start_raw, end_raw = [
            part.strip()
            for part in lines[timing_index].split("-->", maxsplit=1)
        ]

        text = " ".join(lines[timing_index + 1 :]).strip()

        if not text:
            continue

        cues.append(
            SubtitleCue(
                start_seconds=_parse_srt_timestamp(start_raw),
                end_seconds=_parse_srt_timestamp(end_raw),
                text=text,
            )
        )

    if not cues:
        raise ValueError("В SRT-файле не найдено корректных субтитров.")

    return cues


def _escape_ass_text(text: str) -> str:
    return (
        text.replace("\\", r"\\")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("\n", r"\N")
    )


def generate_ass_subtitles(
    srt_path: Path,
    output_ass: Path,
    font_name: str = "Arial",
    font_size: int = 72,
    margin_vertical: int = 520,
) -> Path:
    """Преобразует SRT в оформленный ASS-файл."""

    if font_size <= 0:
        raise ValueError("Размер шрифта должен быть больше нуля.")

    if margin_vertical < 0:
        raise ValueError("Отступ субтитров не может быть отрицательным.")

    cues = parse_srt(srt_path)

    output_ass = output_ass.resolve()
    output_ass.parent.mkdir(parents=True, exist_ok=True)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name},{font_size},&H00FFFFFF,&H0000FFFF,&H00000000,&H64000000,-1,0,0,0,100,100,0,0,1,5,2,2,55,55,{margin_vertical},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    events: list[str] = []

    for cue in cues:
        start = _format_ass_timestamp(cue.start_seconds)
        end = _format_ass_timestamp(cue.end_seconds)
        text = _escape_ass_text(cue.text)

        events.append(
            f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}"
        )

    output_ass.write_text(
        header + "\n".join(events) + "\n",
        encoding="utf-8",
    )

    return output_ass