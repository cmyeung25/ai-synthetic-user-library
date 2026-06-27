from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from ai_validation_swarm.domain.models import PersonaSeed, PersonaSkill, SyntheticUser, utc_now_iso
from ai_validation_swarm.personas.schema_v5_1 import LEGACY_V5_SCHEMA_VERSION, upgrade_profile_payload_to_v5_1
from ai_validation_swarm.personas.seed_coherence import occupation_title_for_band
from ai_validation_swarm.personas.validator import ensure_valid_persona_artifact
from ai_validation_swarm.saas.metadata_store import persist_persona_metadata


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: dict[str, Any] | list[Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_markdown(path: Path, content: str) -> None:
    path.write_text(content, encoding="utf-8-sig")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    payload = read_json(path)
    return payload if isinstance(payload, dict) else None


def index_saved_persona_folder(base_dir: Path, folder: Path, *, active: bool = True) -> Path:
    persona = load_persona(folder)
    now = utc_now_iso()
    persist_persona_metadata(
        index_root=base_dir,
        persona=persona,
        artifact_root=folder,
        profile_json_path=folder / "profile.json",
        audit_json_path=folder / "audit.json",
        narrative_path=folder / "persona.md",
        created_at=now,
        updated_at=now,
        active=active,
        duplicate_report_payload=_read_optional_json(folder / "duplicate_report.json"),
        quality_report_payload=_read_optional_json(folder / "quality_report.json"),
    )
    return folder


def rebuild_persona_metadata_index(base_dir: Path) -> int:
    if not base_dir.exists():
        return 0
    indexed = 0
    for folder in sorted(base_dir.iterdir()):
        if not folder.is_dir() or folder.name.startswith((".", "_")):
            continue
        version_folder = resolve_persona_version_folder(folder)
        index_saved_persona_folder(base_dir, version_folder)
        indexed += 1
    return indexed


def save_persona(persona: PersonaSkill, base_dir: Path) -> Path:
    ensure_valid_persona_artifact(persona)
    folder = base_dir / persona.profile.synthetic_user_id
    ensure_dir(folder)
    write_json(folder / "profile.json", persona.profile.to_dict())
    write_json(folder / "audit.json", persona.to_audit_payload())
    (folder / "persona.md").write_text(persona.narrative, encoding="utf-8")
    index_saved_persona_folder(base_dir, folder)
    return folder


def load_persona(folder: Path) -> PersonaSkill:
    profile_payload = read_json(folder / "profile.json")
    audit_payload = read_json(folder / "audit.json")
    narrative = (folder / "persona.md").read_text(encoding="utf-8")
    skill_version = str(audit_payload["skill_version"])
    if skill_version == LEGACY_V5_SCHEMA_VERSION:
        profile_payload, _ = upgrade_profile_payload_to_v5_1(
            profile_payload,
            source_version=skill_version,
            force_meta=True,
        )
    profile = SyntheticUser(**profile_payload)
    seed_payload = dict(audit_payload["seed"])
    if not seed_payload.get("occupation_title") and seed_payload.get("occupation_band"):
        seed_payload["occupation_title"] = occupation_title_for_band(str(seed_payload["occupation_band"]))
    seed = PersonaSeed(**seed_payload)
    persona = PersonaSkill(
        skill_version=skill_version,
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
    for version in ("v5_1", "v5", "v4", "v3_3", "v3_2", "v3_1_2", "v3_1_1", "v3_1", "v3", "v2"):
        candidate = folder / version
        if (candidate / "profile.json").exists():
            return candidate
    raise ValueError(f"No supported persona artifact found under {folder}.")


def resolve_current_persona_version_folder(folder: Path) -> Path:
    if (folder / "profile.json").exists():
        return folder
    for version in ("v5_1", "v5"):
        candidate = folder / version
        if (candidate / "profile.json").exists():
            return candidate
    raise ValueError(
        f"No current persona artifact found under {folder}. "
        "Current runtime paths support native v5.1 artifacts and v5 fallback upgrade only."
    )


def load_personas(base_dir: Path) -> list[PersonaSkill]:
    if not base_dir.exists():
        return []
    personas = [
        load_persona(resolve_persona_version_folder(folder))
        for folder in sorted(base_dir.iterdir())
        if folder.is_dir() and not folder.name.startswith((".", "_"))
    ]
    return personas


def export_file(source: Path, destination: Path) -> None:
    ensure_dir(destination.parent)
    shutil.copyfile(source, destination)
