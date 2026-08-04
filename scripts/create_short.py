from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.factory import AIShortsFactory
from app.services.gameplay.clipper import GameplayClipError
from app.services.tts.edge_provider import DEFAULT_VOICE, TTSError
from app.services.video.renderer import VideoRenderError
from app.services.video.video_info import MediaInfoError


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Создание вертикального видео из текста."
    )

    story_group = parser.add_mutually_exclusive_group(required=True)

    story_group.add_argument(
        "--text",
        type=str,
        help="Текст истории.",
    )

    story_group.add_argument(
        "--text-file",
        type=Path,
        help="UTF-8 файл с текстом истории.",
    )

    parser.add_argument(
        "--gameplay",
        required=True,
        type=str,
        help=(
            "Категория из assets/gameplay "
            "или путь к конкретному видео."
        ),
    )

    parser.add_argument(
        "--music",
        type=Path,
        help="Необязательный путь к фоновой музыке.",
    )

    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help="Название голоса Edge TTS.",
    )

    parser.add_argument(
        "--voice-rate",
        default="+0%",
        help='Скорость озвучки, например "+10%" или "-5%".',
    )

    parser.add_argument(
        "--music-volume",
        type=float,
        default=0.12,
        help="Громкость фоновой музыки от 0 до 1.",
    )

    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        choices=(24, 25, 30, 50, 60),
        help="Частота кадров итогового видео.",
    )

    parser.add_argument(
        "--no-subtitles",
        action="store_true",
        help="Создать видео без субтитров.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/final_short.mp4"),
        help="Путь к готовому видео.",
    )

    return parser.parse_args()


def load_story(args: argparse.Namespace) -> str:
    """Получает историю из аргумента или текстового файла."""

    if args.text is not None:
        return args.text

    if args.text_file is None:
        raise ValueError("Не указан текст истории.")

    if not args.text_file.is_file():
        raise FileNotFoundError(
            f"Файл с историей не найден: {args.text_file.resolve()}"
        )

    return args.text_file.read_text(encoding="utf-8")


def main() -> int:
    args = parse_arguments()
    factory = AIShortsFactory()

    try:
        story = load_story(args)

        result = factory.create_video(
            story=story,
            gameplay=args.gameplay,
            music=args.music,
            output_video=args.output,
            voice=args.voice,
            voice_rate=args.voice_rate,
            music_volume=args.music_volume,
            fps=args.fps,
            subtitles=not args.no_subtitles,
        )

    except (
        FileNotFoundError,
        ValueError,
        TTSError,
        VideoRenderError,
        GameplayClipError,
        MediaInfoError,
    ) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1

    print(f"Готовое видео создано: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())