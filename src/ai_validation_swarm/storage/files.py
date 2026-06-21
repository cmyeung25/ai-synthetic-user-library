from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ai_validation_swarm.domain.models import PersonaSeed, PersonaSkill, SyntheticUser
from ai_validation_swarm.personas.seed_coherence import occupation_title_for_band
from ai_validation_swarm.personas.validator import ensure_valid_persona_artifact


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def save_persona(persona: PersonaSkill, base_dir: Path) -> Path:
    ensure_valid_persona_artifact(persona)
    folder = base_dir / persona.profile.synthetic_user_id
    ensure_dir(folder)
    write_json(folder / "profile.json", persona.profile.to_dict())
    write_json(folder / "audit.json", persona.to_audit_payload())
    (folder / "persona.md").write_text(persona.narrative, encoding="utf-8")
    return folder


def load_persona(folder: Path) -> PersonaSkill:
    profile_payload = read_json(folder / "profile.json")
    audit_payload = read_json(folder / "audit.json")
    narrative = (folder / "persona.md").read_text(encoding="utf-8")
    profile = SyntheticUser(**profile_payload)
    seed_payload = dict(audit_payload["seed"])
    if not seed_payload.get("occupation_title") and seed_payload.get("occupation_band"):
        seed_payload["occupation_title"] = occupation_title_for_band(str(seed_payload["occupation_band"]))
    seed = PersonaSeed(**seed_payload)
    persona = PersonaSkill(
        skill_version=audit_payload["skill_version"],
        seed=seed,
        profile=profile,
        decision_policy=audit_payload["decision_policy"],
        response_style=audit_payload["response_style"],
        narrative=narrative,
        audit=audit_payload["audit"],
    )
    ensure_valid_persona_artifact(persona)
    return persona


def resolve_persona_version_folder(folder: Path) -> Path:
    if (folder / "profile.json").exists():
        return folder
    for version in ("v4", "v3_3", "v3_2", "v3_1_2", "v3_1_1", "v3_1", "v3", "v2"):
        candidate = folder / version
        if (candidate / "profile.json").exists():
            return candidate
    raise ValueError(f"No supported persona artifact found under {folder}.")


def load_personas(base_dir: Path) -> list[PersonaSkill]:
    if not base_dir.exists():
        return []
    personas = [
        load_persona(resolve_persona_version_folder(folder))
        for folder in sorted(base_dir.iterdir())
        if folder.is_dir()
    ]
    return personas


def export_file(source: Path, destination: Path) -> None:
    ensure_dir(destination.parent)
    shutil.copyfile(source, destination)
