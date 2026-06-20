from __future__ import annotations

from pathlib import Path

from ai_validation_swarm.storage.files import read_json, write_json


def update_run_archive_index(index_path: Path, entry: dict[str, object]) -> dict[str, object]:
    if index_path.exists():
        payload = read_json(index_path)
        runs = payload.get("runs", []) if isinstance(payload, dict) else []
    else:
        runs = []

    runs = [item for item in runs if item.get("run_id") != entry["run_id"]]
    runs.append(entry)
    runs.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)

    index_payload = {
        "index_version": "runs-index/v1",
        "run_count": len(runs),
        "runs": runs,
    }
    write_json(index_path, index_payload)
    return index_payload
