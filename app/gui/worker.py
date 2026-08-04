from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal

from app.factory import AIShortsFactory


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
            )

        except Exception as error:
            self.failed.emit(str(error))
            return

        self.completed.emit(str(result))