from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.services.tts.edge_provider import (
    DEFAULT_VOICE,
    TTSError,
    synthesize_speech,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Генерация озвучки из текста."
    )

    input_group = parser.add_mutually_exclusive_group(required=True)

    input_group.add_argument(
        "--text",
        type=str,
        help="Текст для озвучки.",
    )

    input_group.add_argument(
        "--text-file",
        type=Path,
        help="UTF-8 файл с текстом для озвучки.",
    )

    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help="Название голоса Edge TTS.",
    )

    parser.add_argument(
        "--rate",
        default="+0%",
        help='Скорость речи, например "+10%" или "-5%".',
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/voice.mp3"),
        help="Путь к выходному MP3.",
    )

    return parser.parse_args()


def load_text(args: argparse.Namespace) -> str:
    if args.text is not None:
        return args.text

    if args.text_file is None:
        raise ValueError("Не указан текст для озвучки.")

    if not args.text_file.exists():
        raise FileNotFoundError(
            f"Файл с текстом не найден: {args.text_file.resolve()}"
        )

    return args.text_file.read_text(encoding="utf-8")


def main() -> int:
    args = parse_arguments()

    try:
        text = load_text(args)
        result = synthesize_speech(
            text=text,
            output_audio=args.output,
            voice=args.voice,
            rate=args.rate,
        )
    except (FileNotFoundError, ValueError, TTSError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1

    print(f"Озвучка создана: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())