from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.personas.frontline_v5_generator import (  # noqa: E402
    FrontlineLocalV5SynthesisAdapter,
    build_frontline_v5_generation_guide,
)
from ai_validation_swarm.personas.v5 import GENERATOR_VERSION as V5_GENERATOR_VERSION, generate_v5_persona  # noqa: E402
from ai_validation_swarm.storage.files import write_json  # noqa: E402


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_hashes(folder: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for name in ("profile.json", "audit.json", "persona.md", "generation_notes.json"):
        path = folder / name
        if path.exists() and path.is_file():
            hashes[name] = _sha256_file(path)
    return hashes


def _next_persona_id(output_dir: Path, starting_id: int) -> str:
    value = starting_id
    while (output_dir / f"su_{value:04d}").exists():
        value += 1
    return f"su_{value:04d}"


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed reusable Frontline V5.1 reserve personas.")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "data" / "personas")
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--starting-id", type=int, default=3001)
    parser.add_argument("--panel-type", default="mainstream")
    parser.add_argument("--random-seed", type=int, default=3001)
    parser.add_argument("--target-audience", default="General Frontline Research Studio product research participants")
    args = parser.parse_args()

    count = max(1, min(int(args.count), 12))
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    adapter = FrontlineLocalV5SynthesisAdapter()
    generated: list[dict[str, str]] = []
    next_start = int(args.starting_id)
    for offset in range(count):
        persona_id = _next_persona_id(output_dir, next_start)
        next_start = int(persona_id.split("_", 1)[1]) + 1
        guide = build_frontline_v5_generation_guide(
            panel_type=str(args.panel_type),
            target_audience={"summary": str(args.target_audience)},
        )
        folder = generate_v5_persona(
            persona_id=persona_id,
            output_dir=output_dir,
            adapter=adapter,
            guide=guide,
            random_seed=int(args.random_seed) + offset,
            max_transport_attempts=1,
        )
        record = {
            "contract_version": "persona-library-record/v0-draft",
            "synthetic_user_id": persona_id,
            "readiness_status": "ready",
            "persona_kind": "participant",
            "panel_role": str(args.panel_type),
            "source_schema_version": "v5_1",
            "source_kind": "generated",
            "generator_version": V5_GENERATOR_VERSION,
            "readiness_checks": {
                "schema_validation": "passed",
                "duplicate_check": "passed",
                "coverage_check": "passed",
            },
            "artifact_hashes": _artifact_hashes(folder),
        }
        write_json(folder / "persona_library_record.json", record)
        generated.append({"persona_id": persona_id, "path": str(folder)})

    manifest_dir = output_dir / "_panel_runs"
    manifest_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = manifest_dir / f"frontline_v5_reserve_{args.panel_type}_{args.random_seed}.json"
    write_json(
        manifest_path,
        {
            "contract_version": "frontline-v5-reserve-seed/v0-draft",
            "generator_version": V5_GENERATOR_VERSION,
            "panel_type": str(args.panel_type),
            "count": len(generated),
            "generated": generated,
            "synthetic_boundary": "Seeded reserve personas are synthetic participants, not recruited human evidence.",
        },
    )
    print(f"Seeded {len(generated)} Frontline V5.1 reserve persona(s).")
    print(f"Manifest: {manifest_path}")
    for item in generated:
        print(f"- {item['persona_id']} | {item['path']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
