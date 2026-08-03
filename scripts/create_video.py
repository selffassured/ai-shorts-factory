from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.services.video.renderer import (
    VideoRenderError,
    render_vertical_video,
    render_video_with_audio,
    render_video_with_voice_and_music,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Создание вертикального видео формата 9:16."
    )

    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Путь к исходному видео.",
    )

    parser.add_argument(
        "--audio",
        type=Path,
        help="Необязательный путь к озвучке.",
    )

    parser.add_argument(
        "--music",
        type=Path,
        help="Необязательный путь к фоновой музыке.",
    )

    parser.add_argument(
        "--music-volume",
        type=float,
        default=0.12,
        help="Громкость фоновой музыки от 0 до 1.",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("output/vertical_video.mp4"),
        help="Путь для сохранения результата.",
    )

    parser.add_argument(
        "--fps",
        type=int,
        default=30,
        choices=(24, 25, 30, 50, 60),
        help="Частота кадров выходного видео.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    try:
        if args.music is not None and args.audio is None:
            raise ValueError(
                "Для добавления музыки необходимо также указать --audio."
            )

        if args.audio is not None and args.music is not None:
            result = render_video_with_voice_and_music(
                input_video=args.input,
                voice_audio=args.audio,
                background_music=args.music,
                output_video=args.output,
                fps=args.fps,
                music_volume=args.music_volume,
            )
        elif args.audio is not None:
            result = render_video_with_audio(
                input_video=args.input,
                input_audio=args.audio,
                output_video=args.output,
                fps=args.fps,
            )
        else:
            result = render_vertical_video(
                input_video=args.input,
                output_video=args.output,
                fps=args.fps,
            )

    except (FileNotFoundError, ValueError, VideoRenderError) as error:
        print(f"Ошибка: {error}", file=sys.stderr)
        return 1

    print(f"Видео успешно создано: {result}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())