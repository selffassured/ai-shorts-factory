from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.services.video.renderer import (
    VideoRenderError,
    render_vertical_video,
)


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Преобразование видео в вертикальный формат 9:16."
    )

    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Путь к исходному видео.",
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
        help="Частота кадров выходного видео.",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_arguments()

    try:
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