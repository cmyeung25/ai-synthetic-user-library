from __future__ import annotations

from pathlib import Path

from ai_validation_swarm.storage.files import read_json


DEFAULT_PRESET_PATH = Path("configs/panels/presets.json")


def load_panel_presets(path: Path = DEFAULT_PRESET_PATH) -> dict[str, dict[str, object]]:
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("Panel preset configuration must be a JSON object.")
    return {str(key): value for key, value in payload.items()}
