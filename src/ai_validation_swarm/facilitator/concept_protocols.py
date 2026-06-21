from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re


DEFAULT_CONCEPT_PROTOCOL = "ai-followup-copilot/v1"
DEFAULT_CONCEPT_LABEL = "AI Follow-up Copilot"


@dataclass(frozen=True, slots=True)
class ConceptProtocol:
    identifier: str
    label: str
    path: Path
    prompt_text: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _concept_prompt_dir() -> Path:
    return _repo_root() / "src" / "ai_validation_swarm" / "prompts" / "concept-interview"


def _infer_label(ref: str, path: Path) -> str:
    source = ref.strip() or path.stem
    slug = Path(source).stem if source.endswith(".md") else source
    slug = slug.replace("\\", "/").split("/")[-1]
    slug = re.sub(r"-v\d+(?:_\d+)*$", "", slug)
    words = [part for part in slug.split("-") if part]
    if not words:
        return "Concept Validation"
    return " ".join(word.upper() if len(word) <= 3 else word.capitalize() for word in words)


def _resolve_path(protocol_ref: str) -> tuple[str, Path]:
    ref = protocol_ref.strip()
    if not ref:
        ref = DEFAULT_CONCEPT_PROTOCOL

    candidate = Path(ref)
    if candidate.is_absolute() and candidate.exists():
        return ref, candidate

    root = _repo_root()
    if candidate.suffix == ".md":
        repo_relative = root / candidate
        if repo_relative.exists():
            return ref, repo_relative
        prompt_relative = _concept_prompt_dir() / candidate
        if prompt_relative.exists():
            return ref, prompt_relative

    normalized = ref.replace("\\", "/")
    if candidate.suffix != ".md":
        filename = normalized.replace("/", "-") + ".md"
        prompt_relative = _concept_prompt_dir() / filename
        if prompt_relative.exists():
            return normalized, prompt_relative

    repo_relative = root / normalized
    if repo_relative.exists():
        return normalized, repo_relative

    raise ValueError(f"Concept protocol '{protocol_ref}' could not be resolved.")


def load_concept_protocol(protocol_ref: str = "", *, label: str = "") -> ConceptProtocol:
    identifier, path = _resolve_path(protocol_ref)
    resolved_label = label.strip() or (
        DEFAULT_CONCEPT_LABEL if identifier == DEFAULT_CONCEPT_PROTOCOL else _infer_label(identifier, path)
    )
    return ConceptProtocol(
        identifier=identifier,
        label=resolved_label,
        path=path,
        prompt_text=path.read_text(encoding="utf-8").strip(),
    )
