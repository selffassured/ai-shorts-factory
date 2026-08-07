from __future__ import annotations

import json
from pathlib import Path

DEFAULT_SETTINGS = {
    "output_directory": "output",
    "default_voice": "ru-RU-SvetlanaNeural",
    "default_voice_rate": 0,
    "default_music_volume": 12,
}

class AppSettingsStorage:
    def __init__(self, path: Path | str = "settings.json") -> None:
        self.path = Path(path)

    def load(self) -> dict:
        result = dict(DEFAULT_SETTINGS)
        if not self.path.is_file():
            return result
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return result
        if isinstance(data, dict):
            result.update(data)
        return result

    def save(self, data: dict) -> Path:
        merged = dict(DEFAULT_SETTINGS)
        merged.update(data)
        self.path.write_text(
            json.dumps(merged, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return self.path
