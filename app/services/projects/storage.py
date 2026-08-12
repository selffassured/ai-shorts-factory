from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path


class ProjectStorage:
    """Простое JSON-хранилище проектов AI Shorts Factory."""

    def __init__(self, root: Path | str = "projects") -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _safe_name(name: str) -> str:
        name = name.strip()
        name = re.sub(r'[<>:"/\\|?*]+', "_", name)
        name = re.sub(r"\s+", " ", name).strip(" .")
        if not name:
            raise ValueError("Название проекта не может быть пустым.")
        return name[:80]

    def path_for(self, name: str) -> Path:
        return self.root / f"{self._safe_name(name)}.json"

    def list_projects(self) -> list[str]:
        return [p.stem for p in sorted(
            self.root.glob("*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )]

    def save(self, name: str, data: dict) -> Path:
        path = self.path_for(name)
        path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return path

    def load(self, name: str) -> dict:
        path = self.path_for(name)
        if not path.is_file():
            raise FileNotFoundError(f"Проект не найден: {name}")
        return json.loads(path.read_text(encoding="utf-8"))

    def describe(self, name: str) -> dict:
        path = self.path_for(name)
        data = self.load(name)
        modified = datetime.fromtimestamp(
            path.stat().st_mtime
        ).isoformat(timespec="minutes")
        return {
            "name": name,
            "modified_at": modified,
            "gameplay": data.get("gameplay", "—"),
            "voice": data.get("voice", "—"),
            "story_preview": " ".join(
                str(data.get("story_text", "")).split()
            )[:100],
        }

    def delete(self, name: str) -> None:
        path = self.path_for(name)
        if path.is_file():
            path.unlink()
