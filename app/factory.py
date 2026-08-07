from __future__ import annotations

import tempfile
from pathlib import Path

from app.services.gameplay.clipper import choose_random_start
from app.services.gameplay.library import GameplayLibrary
from app.services.subtitles.ass_generator import generate_ass_subtitles
from app.services.tts.edge_provider import (
    DEFAULT_VOICE,
    synthesize_speech_with_subtitles,
)
from app.services.video.renderer import render_short_video
from app.services.video.video_info import get_media_duration


class AIShortsFactory:
    """Главный конвейер создания вертикальных видео."""

    def __init__(
        self,
        gameplay_library: GameplayLibrary | None = None,
    ) -> None:
        self.gameplay_library = gameplay_library or GameplayLibrary()

    def _resolve_gameplay(
        self,
        gameplay: str | Path,
    ) -> Path:
        """
        Возвращает конкретный файл геймплея.

        Можно передать путь к видео или название категории.
        """

        candidate = Path(gameplay)

        if candidate.is_file():
            return candidate.resolve()

        category = str(gameplay).strip()

        if not category:
            raise ValueError(
                "Категория геймплея не может быть пустой."
            )

        return self.gameplay_library.get_random_video(category)

    def create_video(
        self,
        story: str,
        gameplay: str | Path,
        output_video: Path,
        music: Path | None = None,
        voice: str = DEFAULT_VOICE,
        voice_rate: str = "+0%",
        music_volume: float = 0.12,
        fps: int = 30,
        subtitles: bool = True,
        subtitle_style: str = "Glow",
        subtitle_font_size: int = 72,
        subtitle_position: str = "Ниже",
        subtitle_background_opacity: int = 72,
        subtitle_font_name: str = "Arial",
        subtitle_text_color: str = "#FFFFFF",
        subtitle_outline_color: str = "#E66BFF",
    ) -> Path:
        """Создаёт готовый вертикальный ролик."""

        clean_story = story.strip()

        if not clean_story:
            raise ValueError("История не может быть пустой.")

        gameplay_path = self._resolve_gameplay(gameplay)
        output_video = output_video.resolve()

        if music is not None:
            music = music.resolve()

            if not music.is_file():
                raise FileNotFoundError(
                    f"Фоновая музыка не найдена: {music}"
                )

        output_video.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        
        with tempfile.TemporaryDirectory(
            prefix="ai_shorts_"
        ) as temporary_directory:
            temporary_path = Path(temporary_directory)

            voice_path = temporary_path / "voice.mp3"
            srt_path = temporary_path / "subtitles.srt"
            ass_path = temporary_path / "subtitles.ass"

           
            speech = synthesize_speech_with_subtitles(
                text=clean_story,
                output_audio=voice_path,
                output_subtitles=srt_path,
                voice=voice,
                rate=voice_rate,
            )

            
            voice_duration = get_media_duration(
                speech.audio_path
            )

            if voice_duration <= 0.05:
                raise RuntimeError(
                    "Озвучка создана, но её длительность "
                    "оказалась нулевой."
                )

            gameplay_duration = get_media_duration(
                gameplay_path
            )

            if gameplay_duration <= 0.05:
                raise RuntimeError(
                    "Выбранный gameplay имеет нулевую "
                    "длительность или повреждён."
                )
            gameplay_start = choose_random_start(
                video_duration=gameplay_duration,
                required_duration=voice_duration,
            )

            generated_ass: Path | None = None

            
            if subtitles:
                generated_ass = generate_ass_subtitles(
                    srt_path=speech.subtitles_path,
                    output_ass=ass_path,
                    font_size=subtitle_font_size,
                    margin_vertical=None,
                    min_words=2,
                    max_words=4,
                    max_duration=2.2,
                    style_name=subtitle_style,
                    position=subtitle_position,
                    background_opacity=(
                        subtitle_background_opacity
                    ),
                    font_name=subtitle_font_name,
                    text_color=subtitle_text_color,
                    outline_color=subtitle_outline_color,
                )

            return render_short_video(
                input_video=gameplay_path,
                voice_audio=speech.audio_path,
                background_music=music,
                subtitles_ass=generated_ass,
                output_video=output_video,
                duration=voice_duration,
                start_seconds=gameplay_start,
                fps=fps,
                music_volume=music_volume,
            )
