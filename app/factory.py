from __future__ import annotations

import tempfile
from pathlib import Path

from app.services.subtitles.ass_generator import generate_ass_subtitles
from app.services.tts.edge_provider import (
    DEFAULT_VOICE,
    synthesize_speech_with_subtitles,
)
from app.services.video.renderer import (
    render_video_with_audio,
    render_video_with_audio_and_ass_subtitles,
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
        subtitles: bool = True,
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
                raise FileNotFoundError(
                    f"Фоновая музыка не найдена: {music}"
                )

        output_video.parent.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(
            prefix="ai_shorts_"
        ) as temporary_directory:
            temporary_path = Path(temporary_directory)

            speech = synthesize_speech_with_subtitles(
                text=clean_story,
                output_audio=temporary_path / "voice.mp3",
                output_subtitles=temporary_path / "subtitles.srt",
                voice=voice,
                rate=voice_rate,
            )

            if subtitles:
                ass_path = generate_ass_subtitles(
                    srt_path=speech.subtitles_path,
                    output_ass=temporary_path / "subtitles.ass",
                    font_size=72,
                    margin_vertical=520,
                )

                if music is None:
                    return render_video_with_audio_and_ass_subtitles(
                        input_video=gameplay,
                        input_audio=speech.audio_path,
                        subtitles_ass=ass_path,
                        output_video=output_video,
                        fps=fps,
                    )

            if music is not None:
                return render_video_with_voice_and_music(
                    input_video=gameplay,
                    voice_audio=speech.audio_path,
                    background_music=music,
                    output_video=output_video,
                    fps=fps,
                    music_volume=music_volume,
                )

            return render_video_with_audio(
                input_video=gameplay,
                input_audio=speech.audio_path,
                output_video=output_video,
                fps=fps,
            )