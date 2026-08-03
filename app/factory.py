from __future__ import annotations

import tempfile
from pathlib import Path

from app.services.tts.edge_provider import DEFAULT_VOICE, synthesize_speech
from app.services.video.renderer import (
    render_video_with_audio,
    render_video_with_voice_and_music,
)


class AIShortsFactory:
    """Главный конвейер создания вертикальных видео."""

    def create_video(
        self,
        story: str,
        gameplay: Path,
        output_video: Path,
        music: Path | None = None,
        voice: str = DEFAULT_VOICE,
        voice_rate: str = "+0%",
        music_volume: float = 0.12,
        fps: int = 30,
    ) -> Path:
        clean_story = story.strip()

        if not clean_story:
            raise ValueError("История не может быть пустой.")

        gameplay = gameplay.resolve()
        output_video = output_video.resolve()

        if not gameplay.exists():
            raise FileNotFoundError(f"Геймплей не найден: {gameplay}")

        if music is not None:
            music = music.resolve()

            if not music.exists():
                raise FileNotFoundError(f"Фоновая музыка не найдена: {music}")

        output_video.parent.mkdir(parents=True, exist_ok=True)

        # Временная папка удалится автоматически после завершения рендера.
        with tempfile.TemporaryDirectory(prefix="ai_shorts_") as temporary_directory:
            voice_audio = Path(temporary_directory) / "voice.mp3"

            synthesize_speech(
                text=clean_story,
                output_audio=voice_audio,
                voice=voice,
                rate=voice_rate,
            )

            if music is not None:
                return render_video_with_voice_and_music(
                    input_video=gameplay,
                    voice_audio=voice_audio,
                    background_music=music,
                    output_video=output_video,
                    fps=fps,
                    music_volume=music_volume,
                )

            return render_video_with_audio(
                input_video=gameplay,
                input_audio=voice_audio,
                output_video=output_video,
                fps=fps,
            )