from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path


class RenderHistoryStorage:
    def __init__(self, path: Path | str = "render_history.json") -> None:
        self.path = Path(path)

    def load(self) -> list[dict]:
        if not self.path.is_file():
            return []
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return []
        return data if isinstance(data, list) else []

    def add(
        self,
        output_path: str,
        story: str,
        *,
        duration_seconds: float | None = None,
        export_preset: str = "",
        gameplay: str = "",
        voice: str = "",
    ) -> None:
        path = Path(output_path)
        size_bytes = 0
        try:
            if path.is_file():
                size_bytes = path.stat().st_size
        except OSError:
            pass

        items = self.load()
        items.insert(0, {
            "created_at": datetime.now().isoformat(timespec="seconds"),
            "output_path": output_path,
            "story_preview": " ".join(story.split())[:120],
            "duration_seconds": duration_seconds,
            "size_bytes": size_bytes,
            "export_preset": export_preset,
            "gameplay": gameplay,
            "voice": voice,
        })
        self.path.write_text(
            json.dumps(items[:200], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def clear(self) -> None:
        self.path.write_text("[]", encoding="utf-8")
