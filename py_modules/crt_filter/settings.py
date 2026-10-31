"""Persisted plugin settings, stored as JSON in Decky's settings directory."""

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path

from .shaders import DEFAULT_SHADER_ID


@dataclass
class Settings:
    # The Default State: whether the filter is on outside Auto-apply Sessions.
    enabled: bool = False
    shader_id: str = DEFAULT_SHADER_ID
    # Steam app IDs (as strings, so non-Steam shortcuts fit too) of Auto-apply Games.
    auto_apply_app_ids: list[str] = field(default_factory=list)


class SettingsStore:
    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> Settings:
        try:
            raw = json.loads(self._path.read_text())
        except (OSError, ValueError):
            return Settings()
        if not isinstance(raw, dict):
            return Settings()
        defaults = Settings()
        app_ids = raw.get("auto_apply_app_ids", defaults.auto_apply_app_ids)
        return Settings(
            enabled=bool(raw.get("enabled", defaults.enabled)),
            shader_id=str(raw.get("shader_id", defaults.shader_id)),
            auto_apply_app_ids=[str(app_id) for app_id in app_ids] if isinstance(app_ids, list) else [],
        )

    def save(self, settings: Settings) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self._path.with_suffix(".tmp")
        temp_path.write_text(json.dumps(asdict(settings), indent=2))
        os.replace(temp_path, self._path)
