from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.core.user_errors import format_user_error
from app.factory import AIShortsFactory
from app.services.tts.edge_provider import synthesize_speech


class VideoGenerationWorker(QThread):
    """Создаёт видео в отдельном потоке."""

    completed = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        *,
        story: str,
        gameplay: str,
        output_video: Path,
        voice: str,
        voice_rate: str,
        music: Path | None,
        music_volume: float,
        subtitles: bool,
        subtitle_style: str = "Glow",
        subtitle_font_size: int = 72,
        subtitle_position: str = "Ниже",
        subtitle_background_opacity: int = 72,
        subtitle_font_name: str = "Arial",
        subtitle_text_color: str = "#FFFFFF",
        subtitle_outline_color: str = "#E66BFF",
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.story = story
        self.gameplay = gameplay
        self.output_video = output_video
        self.voice = voice
        self.voice_rate = voice_rate
        self.music = music
        self.music_volume = music_volume
        self.subtitles = subtitles
        self.subtitle_style = subtitle_style
        self.subtitle_font_size = subtitle_font_size
        self.subtitle_position = subtitle_position
        self.subtitle_background_opacity = (
            subtitle_background_opacity
        )
        self.subtitle_font_name = subtitle_font_name
        self.subtitle_text_color = subtitle_text_color
        self.subtitle_outline_color = subtitle_outline_color

    def run(self) -> None:
        """Запускает полный конвейер генерации."""

        try:
            factory = AIShortsFactory()

            result = factory.create_video(
                story=self.story,
                gameplay=self.gameplay,
                output_video=self.output_video,
                music=self.music,
                voice=self.voice,
                voice_rate=self.voice_rate,
                music_volume=self.music_volume,
                subtitles=self.subtitles,
                subtitle_style=self.subtitle_style,
                subtitle_font_size=self.subtitle_font_size,
                subtitle_position=self.subtitle_position,
                subtitle_background_opacity=(
                    self.subtitle_background_opacity
                ),
                subtitle_font_name=self.subtitle_font_name,
                subtitle_text_color=self.subtitle_text_color,
                subtitle_outline_color=self.subtitle_outline_color,
            )

        except Exception as error:
            self.failed.emit(
                format_user_error(error)
            )
            return

        if (
            not result.is_file()
            or result.stat().st_size == 0
        ):
            self.failed.emit(
                "Рендер завершился, но готовый MP4 "
                "не был создан."
            )
            return

        self.completed.emit(str(result))


class VoicePreviewWorker(QThread):
    """Генерирует короткий preview выбранного голоса."""

    completed = Signal(str)
    failed = Signal(str)

    def __init__(
        self,
        *,
        text: str,
        voice: str,
        rate: str = "+0%",
        parent=None,
    ) -> None:
        super().__init__(parent)

        self.text = text.strip()
        self.voice = voice
        self.rate = rate

    def run(self) -> None:
        try:
            if not self.text:
                raise ValueError(
                    "Текст для preview голоса пуст."
                )

            cache_dir = (
                Path(tempfile.gettempdir())
                / "ai_shorts_factory"
                / "voice_previews"
            )
            cache_dir.mkdir(
                parents=True,
                exist_ok=True,
            )

            cache_key = hashlib.sha1(
                (
                    f"{self.voice}|{self.rate}|"
                    f"{self.text}"
                ).encode("utf-8")
            ).hexdigest()

            output_audio = (
                cache_dir
                / f"{cache_key}.mp3"
            )

            if (
                not output_audio.is_file()
                or output_audio.stat().st_size == 0
            ):
                synthesize_speech(
                    text=self.text,
                    output_audio=output_audio,
                    voice=self.voice,
                    rate=self.rate,
                )

            self.completed.emit(
                str(output_audio)
            )

        except Exception as error:
            self.failed.emit(
                format_user_error(error)
            )
