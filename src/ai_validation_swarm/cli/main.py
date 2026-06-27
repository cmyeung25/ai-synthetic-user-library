from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys

from ai_validation_swarm.domain.validators import (
    InputValidationError,
    load_and_validate_founder_brief,
    validate_panel_spec,
)
from ai_validation_swarm.evaluation.comparison import compare_evaluation_files
from ai_validation_swarm.evaluation.harness import run_evaluation_suite
from ai_validation_swarm.personas.analysis import build_persona_library_summary
from ai_validation_swarm.personas.batch import enrich_persona_library, enrich_persona_library_to_target, list_valid_persona_ids
from ai_validation_swarm.personas.generator import PANEL_ROLES, generate_personas
from ai_validation_swarm.personas.v2 import migrate_personas_to_v2, validate_v2_persona_library
from ai_validation_swarm.personas.v3 import (
    generate_v3_personas,
    run_distinctiveness_check,
    validate_v3_persona_library,
)
from ai_validation_swarm.personas.v3_1 import (
    generate_v3_1_personas,
    run_distinctiveness_check_v3_1,
    validate_v3_1_persona_library,
)
from ai_validation_swarm.personas.v3_1_1 import (
    generate_v3_1_1_personas,
    run_distinctiveness_check_v3_1_1,
    validate_v3_1_1_persona_library,
)
from ai_validation_swarm.personas.v3_1_2 import (
    generate_v3_1_2_personas,
    run_distinctiveness_check_v3_1_2,
    validate_v3_1_2_persona_library,
)
from ai_validation_swarm.personas.v3_2 import (
    OpenAIV32SynthesisAdapter,
    SectionBatchedV32SynthesisAdapter,
    generate_v3_2_personas,
    validate_v3_2_persona_folder,
)
from ai_validation_swarm.personas.v3_3 import (
    FullPassRepairV33SynthesisAdapter,
    OpenAIV33SynthesisAdapter,
    generate_v3_3_personas,
    validate_v3_3_persona_folder,
)
from ai_validation_swarm.personas.v5 import (
    OpenAIV5SynthesisAdapter,
    generate_v5_persona,
    validate_v5_persona_folder,
)
from ai_validation_swarm.personas.v5_panels import (
    HK_RETAIL_BANK_PORTFOLIO_HEALTH_CHECK,
    build_v5_panel_preset,
)
from ai_validation_swarm.personas.validator import validate_personas
from ai_validation_swarm.providers.factory import build_provider
from ai_validation_swarm.providers.openai_client import OpenAIProviderError
from ai_validation_swarm.reporting.exporters import render_report_csv
from ai_validation_swarm.sampling.presets import load_panel_presets
from ai_validation_swarm.sampling.engine import sample_personas
from ai_validation_swarm.storage.files import ensure_dir, export_file, load_persona, load_personas, read_json, save_persona, write_json
from ai_validation_swarm.validation.runner import run_validation
from ai_validation_swarm.domain.models import PanelSpec


PERSONA_LLM_BACKENDS = ["template", "openai", "agnes", "codex"]
PERSONA_ENRICH_BACKENDS = ["openai", "agnes", "codex"]
LIVE_LLM_BACKENDS = ["agnes", "openai", "codex", "codex-sdk"]
LIVE_CHAT_BACKENDS = ["mock", "agnes", "openai", "codex", "codex-sdk"]
AGNES_DEFAULT_BASE_URL = "https://apihub.agnes-ai.com/v1"
AGNES_DEFAULT_MODEL = "agnes-2.0-flash"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _load_repo_runtime_defaults() -> dict[str, object]:
    path = _repo_root() / "configs" / "runtime_defaults.json"
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _repo_default_choice(key: str, *, fallback: str, allowed: list[str]) -> str:
    payload = _load_repo_runtime_defaults()
    value = str(payload.get(key, "")).strip()
    return value if value in allowed else fallback


def _repo_default_text(key: str) -> str | None:
    payload = _load_repo_runtime_defaults()
    value = str(payload.get(key, "")).strip()
    return value or None


def _default_live_backend() -> str:
    return _repo_default_choice("live_backend", fallback="codex", allowed=LIVE_LLM_BACKENDS)


def _default_live_model() -> str | None:
    return _repo_default_text("live_model")


def _default_persona_enrich_backend() -> str:
    return _repo_default_choice("persona_enrich_backend", fallback="codex", allowed=PERSONA_ENRICH_BACKENDS)


def _default_persona_compare_candidate_backend() -> str:
    return _repo_default_choice(
        "persona_compare_candidate_backend",
        fallback=_default_persona_enrich_backend(),
        allowed=PERSONA_ENRICH_BACKENDS,
    )


def _load_live_llm_config(backend: str, *, timeout_default: int | None = None):
    from ai_validation_swarm.providers.openai_client import load_openai_provider_config

    if backend == "codex":
        return load_openai_provider_config(
            prefer_codex_auth=True,
            force_transport="codex_cli",
            timeout_default=timeout_default,
        )
    if backend == "codex-sdk":
        return load_openai_provider_config(
            prefer_codex_auth=True,
            force_transport="codex_sdk_node",
            timeout_default=timeout_default,
        )
    if backend == "agnes":
        return load_openai_provider_config(
            force_transport="powershell_webrequest",
            force_provider_name="agnes",
            force_api_key_env="AGNES_API_KEY",
            default_model=AGNES_DEFAULT_MODEL,
            default_profile=AGNES_DEFAULT_MODEL,
            default_api_base=AGNES_DEFAULT_BASE_URL,
            timeout_default=timeout_default,
        )
    return load_openai_provider_config(timeout_default=timeout_default)


def _load_persona_llm_config(backend: str):
    return _load_live_llm_config(backend)


def _build_conversation_provider(
    backend: str,
    *,
    model: str | None = None,
    reasoning_effort: str | None = None,
    debug_writer=None,
):
    from ai_validation_swarm.conversation.providers import MockConversationProvider, OpenAIConversationProvider
    from ai_validation_swarm.providers.openai_client import OpenAIResponsesClient

    if backend == "mock":
        return MockConversationProvider()
    config = _load_live_llm_config(backend)
    if model:
        config.model = model
    if reasoning_effort:
        config.model_reasoning_effort = reasoning_effort
    return OpenAIConversationProvider(OpenAIResponsesClient(config, debug_writer=debug_writer))


def _build_facilitator_provider(
    backend: str,
    *,
    model: str | None = None,
    reasoning_effort: str | None = None,
    debug_writer=None,
):
    from ai_validation_swarm.facilitator.providers import OpenAIFacilitatorProvider
    from ai_validation_swarm.providers.openai_client import OpenAIResponsesClient

    config = _load_live_llm_config(backend)
    if model:
        config.model = model
    if reasoning_effort:
        config.model_reasoning_effort = reasoning_effort
    return OpenAIFacilitatorProvider(OpenAIResponsesClient(config, debug_writer=debug_writer))


def _console_safe(value: object) -> str:
    text = str(value)
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return text.encode(encoding, errors="replace").decode(encoding, errors="replace")


def _make_progress_writer(enabled: bool):
    return (lambda message: print(_console_safe(message), flush=True)) if enabled else None


def _build_persona_generation_components(args: argparse.Namespace) -> tuple[object | None, object | None]:
    backend = getattr(args, "backend", "template")
    judge_enabled = bool(getattr(args, "judge_personas", False))

    if backend == "template" and not judge_enabled:
        return None, None

    from ai_validation_swarm.personas.llm import OpenAIPersonaEnricher, OpenAIPersonaJudge
    from ai_validation_swarm.providers.openai_client import OpenAIResponsesClient

    config = _load_persona_llm_config(backend)
    setattr(args, "_resolved_openai_config", config)
    client = OpenAIResponsesClient(config)
    enricher = OpenAIPersonaEnricher(client, config) if backend in {"openai", "agnes", "codex"} else None
    judge = OpenAIPersonaJudge(client, config) if judge_enabled else None
    return enricher, judge


def _load_openai_runtime_config():
    return _load_live_llm_config(_default_live_backend())


def _build_codex_probe_components():
    from ai_validation_swarm.providers.openai_client import (
        OpenAIResponsesClient,
        load_openai_provider_config,
        resolve_codex_cli_path,
        resolve_codex_home,
    )

    config = load_openai_provider_config(prefer_codex_auth=True, force_transport="codex_cli")
    client = OpenAIResponsesClient(config)
    return client, config, resolve_codex_cli_path(config), resolve_codex_home(config)


def _parse_filter_items(raw_filters: list[str] | None) -> dict[str, object]:
    if not raw_filters:
        return {}
    filters: dict[str, object] = {}
    for raw_filter in raw_filters:
        if "=" not in raw_filter:
            raise ValueError(f"Invalid filter '{raw_filter}'. Expected key=value.")
        key, raw_value = raw_filter.split("=", 1)
        key = key.strip()
        value = raw_value.strip()
        if not key or not value:
            raise ValueError(f"Invalid filter '{raw_filter}'. Expected key=value.")
        if "," in value:
            filters[key] = [part.strip() for part in value.split(",") if part.strip()]
        else:
            filters[key] = value
    return filters


def _resolve_panel_spec(
    *,
    panel_type: str,
    sample_size: int | None,
    random_seed: int | None,
    raw_filters: list[str] | None,
) -> PanelSpec:
    presets = load_panel_presets()
    preset = presets.get(panel_type, {})
    resolved_sample_size = sample_size if sample_size is not None else int(preset.get("default_sample_size", 5))
    panel_spec = PanelSpec(
        panel_type=panel_type,
        sample_size=resolved_sample_size,
        random_seed=random_seed,
        filters=_parse_filter_items(raw_filters),
        preset_name=panel_type,
    )
    return validate_panel_spec(panel_spec, allowed_panel_types=set(PANEL_ROLES))


def _resolve_export_format(output: Path, requested_format: str | None) -> str:
    if requested_format:
        return requested_format
    suffix = output.suffix.lower()
    if suffix in {".md", ".markdown"}:
        return "markdown"
    if suffix == ".json":
        return "json"
    if suffix == ".csv":
        return "csv"
    return "markdown"


def _resolve_interview_turn_policy(
    args: argparse.Namespace,
    *,
    default_soft: int,
    default_hard: int,
) -> tuple[int, int]:
    soft = getattr(args, "soft_turn_limit", None)
    hard = getattr(args, "hard_turn_limit", None)
    max_turns = getattr(args, "max_turns", None)
    if soft is None and hard is None and max_turns is not None:
        soft = max_turns
        hard = max_turns
    if soft is None:
        soft = default_soft
    if hard is None:
        hard = max(hard or 0, default_hard, soft)
    return int(soft), int(hard)


def _select_personas_by_id(
    personas: list,
    *,
    persona_ids: list[str] | None = None,
    limit: int | None = None,
) -> list:
    selected = personas
    if persona_ids:
        requested = set(persona_ids)
        selected = [
            persona
            for persona in personas
            if persona.profile.synthetic_user_id in requested
        ]
        missing_ids = sorted(requested - {persona.profile.synthetic_user_id for persona in selected})
        if missing_ids:
            raise ValueError(f"Requested persona IDs not found: {', '.join(missing_ids)}")
    if limit is not None:
        selected = selected[:limit]
    return selected


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ai-validation-swarm")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_cmd = subparsers.add_parser("generate-personas")
    generate_cmd.add_argument("--count", type=int, default=50)
    generate_cmd.add_argument("--seed", type=int, default=11)
    generate_cmd.add_argument("--output-dir", type=Path, default=Path("data/personas"))
    generate_cmd.add_argument("--backend", choices=PERSONA_LLM_BACKENDS, default="template")
    generate_cmd.add_argument("--judge-personas", action="store_true")

    list_cmd = subparsers.add_parser("list-personas")
    list_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))

    sample_cmd = subparsers.add_parser("sample-panel")
    sample_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))
    sample_cmd.add_argument("--panel-type", choices=PANEL_ROLES, required=True)
    sample_cmd.add_argument("--sample-size", type=int)
    sample_cmd.add_argument("--seed", type=int, default=11)
    sample_cmd.add_argument("--filter", action="append", dest="filters")

    validate_cmd = subparsers.add_parser("validate-personas")
    validate_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))

    migrate_v2_cmd = subparsers.add_parser("migrate-personas-v2")
    migrate_v2_cmd.add_argument("--input-dir", type=Path, default=Path("data/personas"))
    migrate_v2_cmd.add_argument("--output-dir", type=Path, default=Path("data/personas_v2_review"))
    migrate_v2_cmd.add_argument("--persona-id", action="append", dest="persona_ids")
    migrate_v2_cmd.add_argument("--limit", type=int)
    migrate_v2_cmd.add_argument("--seed-offset", type=int, default=0)

    validate_v2_cmd = subparsers.add_parser("validate-personas-v2")
    validate_v2_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas_v2_review"))

    generate_v3_cmd = subparsers.add_parser("generate-v3-persona")
    generate_v3_cmd.add_argument("--persona-id", action="append", dest="persona_ids", required=True)
    generate_v3_cmd.add_argument("--source-dir", type=Path, default=Path("data/personas_v2_review"))
    generate_v3_cmd.add_argument("--output-dir", type=Path, default=Path("data/personas"))
    generate_v3_cmd.add_argument("--compare-against", type=Path, default=Path("data/personas"))
    generate_v3_cmd.add_argument("--against-persona-id", action="append", dest="against_persona_ids")
    generate_v3_cmd.add_argument("--seed-offset", type=int, default=0)

    distinctiveness_cmd = subparsers.add_parser("run-distinctiveness-check")
    distinctiveness_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))
    distinctiveness_cmd.add_argument("--persona-id", required=True)
    distinctiveness_cmd.add_argument("--against-persona-id", action="append", dest="against_persona_ids", required=True)
    distinctiveness_cmd.add_argument("--output", type=Path)

    validate_v3_cmd = subparsers.add_parser("validate-personas-v3")
    validate_v3_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))

    generate_v3_1_cmd = subparsers.add_parser("generate-v3-1-persona")
    generate_v3_1_cmd.add_argument("--persona-id", action="append", dest="persona_ids", required=True)
    generate_v3_1_cmd.add_argument("--source-dir", type=Path, default=Path("data/personas"))
    generate_v3_1_cmd.add_argument("--output-dir", type=Path, default=Path("data/personas"))
    generate_v3_1_cmd.add_argument("--compare-against", type=Path, default=Path("data/personas"))
    generate_v3_1_cmd.add_argument("--against-persona-id", action="append", dest="against_persona_ids")
    generate_v3_1_cmd.add_argument("--seed-offset", type=int, default=0)

    distinctiveness_v3_1_cmd = subparsers.add_parser("run-distinctiveness-check-v3-1")
    distinctiveness_v3_1_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))
    distinctiveness_v3_1_cmd.add_argument("--persona-id", required=True)
    distinctiveness_v3_1_cmd.add_argument("--against-persona-id", action="append", dest="against_persona_ids", required=True)
    distinctiveness_v3_1_cmd.add_argument("--output", type=Path)

    validate_v3_1_cmd = subparsers.add_parser("validate-personas-v3-1")
    validate_v3_1_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))

    generate_v3_1_1_cmd = subparsers.add_parser("generate-v3-1-1-persona")
    generate_v3_1_1_cmd.add_argument("--persona-id", action="append", dest="persona_ids", required=True)
    generate_v3_1_1_cmd.add_argument("--source-dir", type=Path, default=Path("data/personas"))
    generate_v3_1_1_cmd.add_argument("--output-dir", type=Path, default=Path("data/personas"))
    generate_v3_1_1_cmd.add_argument("--compare-against", type=Path, default=Path("data/personas"))
    generate_v3_1_1_cmd.add_argument("--against-persona-id", action="append", dest="against_persona_ids")
    generate_v3_1_1_cmd.add_argument("--seed-offset", type=int, default=0)

    generate_v3_1_2_cmd = subparsers.add_parser("generate-v3-1-2-persona")
    generate_v3_1_2_cmd.add_argument("--persona-id", action="append", dest="persona_ids", required=True)
    generate_v3_1_2_cmd.add_argument("--source-dir", type=Path, default=Path("data/personas"))
    generate_v3_1_2_cmd.add_argument("--output-dir", type=Path, default=Path("data/personas"))
    generate_v3_1_2_cmd.add_argument("--compare-against", type=Path, default=Path("data/personas"))
    generate_v3_1_2_cmd.add_argument("--against-persona-id", action="append", dest="against_persona_ids")
    generate_v3_1_2_cmd.add_argument("--seed-offset", type=int, default=0)
    generate_v3_1_2_cmd.add_argument("--max-attempts", type=int, default=3)

    generate_v3_2_cmd = subparsers.add_parser("generate-v3-2-persona")
    generate_v3_2_cmd.add_argument("--persona-id", action="append", dest="persona_ids", required=True)
    generate_v3_2_cmd.add_argument("--output-dir", type=Path, default=Path("data/personas"))
    generate_v3_2_cmd.add_argument("--compare-against", type=Path, default=Path("data/personas"))
    generate_v3_2_cmd.add_argument("--section", action="append", dest="enabled_sections")
    generate_v3_2_cmd.add_argument("--seed-offset", type=int, default=11)
    generate_v3_2_cmd.add_argument("--max-attempts", type=int, default=3)
    generate_v3_2_cmd.add_argument("--backend", choices=LIVE_LLM_BACKENDS, default=_default_live_backend())
    generate_v3_2_cmd.add_argument("--brief-dir", type=Path)
    generate_v3_2_cmd.add_argument("--section-batch-size", type=int, default=0)
    generate_v3_2_cmd.add_argument("--debug-progress", action="store_true")

    validate_v3_2_cmd = subparsers.add_parser("validate-personas-v3-2")
    validate_v3_2_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))

    generate_v3_3_cmd = subparsers.add_parser("generate-v3-3-persona")
    generate_v3_3_cmd.add_argument("--persona-id", action="append", dest="persona_ids", required=True)
    generate_v3_3_cmd.add_argument("--output-dir", type=Path, default=Path("data/personas"))
    generate_v3_3_cmd.add_argument("--compare-against", type=Path, default=Path("data/personas"))
    generate_v3_3_cmd.add_argument("--section", action="append", dest="enabled_sections")
    generate_v3_3_cmd.add_argument("--seed-offset", type=int, default=11)
    generate_v3_3_cmd.add_argument("--max-attempts", type=int, default=3)
    generate_v3_3_cmd.add_argument("--backend", choices=LIVE_LLM_BACKENDS, default=_default_live_backend())
    generate_v3_3_cmd.add_argument("--brief-dir", type=Path)
    generate_v3_3_cmd.add_argument("--repair-batch-size", type=int, default=1)
    generate_v3_3_cmd.add_argument("--debug-progress", action="store_true")

    validate_v3_3_cmd = subparsers.add_parser("validate-personas-v3-3")
    validate_v3_3_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))

    generate_v5_cmd = subparsers.add_parser("generate-v5-persona")
    generate_v5_cmd.add_argument("--persona-id", required=True)
    generate_v5_cmd.add_argument("--output-dir", type=Path, default=Path("data/personas"))
    generate_v5_cmd.add_argument("--backend", choices=LIVE_LLM_BACKENDS, default=_default_live_backend())
    generate_v5_cmd.add_argument("--guide-file", type=Path)
    generate_v5_cmd.add_argument("--fixed", action="append", default=[], metavar="KEY=VALUE")
    generate_v5_cmd.add_argument("--prefer", action="append", default=[], metavar="KEY=VALUE")
    generate_v5_cmd.add_argument("--interest", action="append", default=[])
    generate_v5_cmd.add_argument("--random-seed", type=int)
    generate_v5_cmd.add_argument("--max-transport-attempts", type=int, default=2)
    generate_v5_cmd.add_argument("--resume-response", action="store_true")
    generate_v5_cmd.add_argument("--debug-progress", action="store_true")

    generate_v5_panel_cmd = subparsers.add_parser(
        "generate-v5-panel",
        help="Legacy project-specific V5 preset generator; not the current default V5 panel path.",
        description=(
            "Generate a legacy project-specific V5 panel preset. "
            "Current V5 platform direction favors reusable V5 personas plus dynamic panel selection "
            "rather than fixed concept-shaped archetype panels."
        ),
    )
    generate_v5_panel_cmd.add_argument(
        "--panel-preset",
        choices=[HK_RETAIL_BANK_PORTFOLIO_HEALTH_CHECK],
        default=HK_RETAIL_BANK_PORTFOLIO_HEALTH_CHECK,
    )
    generate_v5_panel_cmd.add_argument("--starting-id", type=int, default=1201)
    generate_v5_panel_cmd.add_argument("--output-dir", type=Path, default=Path("data/personas"))
    generate_v5_panel_cmd.add_argument("--backend", choices=LIVE_LLM_BACKENDS, default=_default_live_backend())
    generate_v5_panel_cmd.add_argument("--random-seed", type=int)
    generate_v5_panel_cmd.add_argument("--max-transport-attempts", type=int, default=2)
    generate_v5_panel_cmd.add_argument("--debug-progress", action="store_true")

    validate_v5_cmd = subparsers.add_parser("validate-personas-v5")
    validate_v5_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))

    generate_target_cmd = subparsers.add_parser("generate-persona-to-target")
    generate_target_cmd.add_argument("--target-version", choices=["v3", "v3_1", "v3_1_1", "v3_1_2"], required=True)
    generate_target_cmd.add_argument("--persona-id", action="append", dest="persona_ids", required=True)
    generate_target_cmd.add_argument("--source-dir", type=Path, default=Path("data/personas_v2_review"))
    generate_target_cmd.add_argument("--output-dir", type=Path, default=Path("data/personas"))
    generate_target_cmd.add_argument("--compare-against", type=Path, default=Path("data/personas"))
    generate_target_cmd.add_argument("--against-persona-id", action="append", dest="against_persona_ids")
    generate_target_cmd.add_argument("--seed-offset", type=int, default=0)
    generate_target_cmd.add_argument("--max-attempts", type=int, default=3)

    distinctiveness_v3_1_1_cmd = subparsers.add_parser("run-distinctiveness-check-v3-1-1")
    distinctiveness_v3_1_1_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))
    distinctiveness_v3_1_1_cmd.add_argument("--persona-id", required=True)
    distinctiveness_v3_1_1_cmd.add_argument("--against-persona-id", action="append", dest="against_persona_ids", required=True)
    distinctiveness_v3_1_1_cmd.add_argument("--output", type=Path)

    validate_v3_1_1_cmd = subparsers.add_parser("validate-personas-v3-1-1")
    validate_v3_1_1_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))

    distinctiveness_v3_1_2_cmd = subparsers.add_parser("run-distinctiveness-check-v3-1-2")
    distinctiveness_v3_1_2_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))
    distinctiveness_v3_1_2_cmd.add_argument("--persona-id", required=True)
    distinctiveness_v3_1_2_cmd.add_argument("--against-persona-id", action="append", dest="against_persona_ids", required=True)
    distinctiveness_v3_1_2_cmd.add_argument("--output", type=Path)

    validate_v3_1_2_cmd = subparsers.add_parser("validate-personas-v3-1-2")
    validate_v3_1_2_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))

    summarize_cmd = subparsers.add_parser("summarize-personas")
    summarize_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))
    summarize_cmd.add_argument("--output", type=Path)

    inspect_auth_cmd = subparsers.add_parser("inspect-openai-auth")
    inspect_auth_cmd.add_argument("--output", type=Path)

    probe_codex_cmd = subparsers.add_parser("probe-codex-auth")
    probe_codex_cmd.add_argument("--output", type=Path)

    enrich_cmd = subparsers.add_parser("enrich-personas")
    enrich_cmd.add_argument("--input-dir", type=Path, default=Path("data/personas"))
    enrich_cmd.add_argument("--output-dir", type=Path, default=Path("data/personas_llm"))
    enrich_cmd.add_argument("--backend", choices=PERSONA_ENRICH_BACKENDS, default=_default_persona_enrich_backend())
    enrich_cmd.add_argument("--judge-personas", action="store_true")
    enrich_cmd.add_argument("--limit", type=int)
    enrich_cmd.add_argument("--target-count", type=int)
    enrich_cmd.add_argument("--batch-size", type=int)
    enrich_cmd.add_argument("--max-rounds", type=int)
    enrich_cmd.add_argument("--max-stall-rounds", type=int, default=2)
    enrich_cmd.add_argument("--max-persona-failures", type=int, default=2)
    enrich_cmd.add_argument("--workers", type=int, default=1)
    enrich_cmd.add_argument("--no-resume", action="store_true")
    enrich_cmd.add_argument("--report", type=Path)

    validate_brief_cmd = subparsers.add_parser("validate-brief")
    validate_brief_cmd.add_argument("--brief", type=Path, required=True)

    run_cmd = subparsers.add_parser("run-validation")
    run_cmd.add_argument("--brief", type=Path, required=True)
    run_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))
    run_cmd.add_argument("--panel-type", choices=PANEL_ROLES, default="mainstream")
    run_cmd.add_argument("--sample-size", type=int)
    run_cmd.add_argument("--seed", type=int, default=11)
    run_cmd.add_argument("--max-retries", type=int, default=1)
    run_cmd.add_argument("--run-dir", type=Path, default=Path("runs"))
    run_cmd.add_argument("--provider", default="mock")
    run_cmd.add_argument("--filter", action="append", dest="filters")

    audit_cmd = subparsers.add_parser("audit-report")
    audit_cmd.add_argument("--run-path", type=Path, required=True)

    export_cmd = subparsers.add_parser("export-report")
    export_cmd.add_argument("--run-path", type=Path, required=True)
    export_cmd.add_argument("--output", type=Path, required=True)
    export_cmd.add_argument("--format", choices=["markdown", "json", "csv"])

    evaluation_cmd = subparsers.add_parser("run-evaluation")
    evaluation_cmd.add_argument("--suite", type=Path, default=Path("fixtures/evaluation/suite.json"))
    evaluation_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))
    evaluation_cmd.add_argument("--provider", default="mock")
    evaluation_cmd.add_argument("--output-dir", type=Path, default=Path("evaluations"))
    evaluation_cmd.add_argument("--repeat-count", type=int, default=2)
    evaluation_cmd.add_argument("--max-retries", type=int, default=1)

    bootstrap_saas_cmd = subparsers.add_parser("bootstrap-saas-workspace")
    bootstrap_saas_cmd.add_argument("--runtime-root", type=Path, default=Path("saas_runtime"))
    bootstrap_saas_cmd.add_argument("--workspace-id", required=True)
    bootstrap_saas_cmd.add_argument("--slug", required=True)
    bootstrap_saas_cmd.add_argument("--display-name", required=True)
    bootstrap_saas_cmd.add_argument("--owner-user-id", required=True)
    bootstrap_saas_cmd.add_argument("--api-token", required=True)
    bootstrap_saas_cmd.add_argument("--plan-tier", default="trial")
    bootstrap_saas_cmd.add_argument("--billing-status", default="trialing")
    bootstrap_saas_cmd.add_argument("--region-code", default="HK")
    bootstrap_saas_cmd.add_argument("--data-residency-region", default="ap-east-1")
    bootstrap_saas_cmd.add_argument("--retention-days", type=int)
    bootstrap_saas_cmd.add_argument("--daily-runs", type=int)
    bootstrap_saas_cmd.add_argument("--max-concurrent-jobs", type=int)

    serve_saas_api_cmd = subparsers.add_parser("serve-saas-api")
    serve_saas_api_cmd.add_argument("--runtime-root", type=Path, default=Path("saas_runtime"))
    serve_saas_api_cmd.add_argument("--host", default="127.0.0.1")
    serve_saas_api_cmd.add_argument("--port", type=int, default=8011)

    saas_worker_cmd = subparsers.add_parser("run-saas-worker")
    saas_worker_cmd.add_argument("--runtime-root", type=Path, default=Path("saas_runtime"))
    saas_worker_cmd.add_argument("--poll-seconds", type=float, default=1.0)
    saas_worker_cmd.add_argument("--once", action="store_true")

    purge_saas_cmd = subparsers.add_parser("purge-saas-expired-artifacts")
    purge_saas_cmd.add_argument("--runtime-root", type=Path, default=Path("saas_runtime"))

    compare_cmd = subparsers.add_parser("compare-evaluations")
    compare_cmd.add_argument("--baseline", type=Path, required=True)
    compare_cmd.add_argument("--candidate", type=Path, required=True)
    compare_cmd.add_argument("--output", type=Path)

    compare_persona_quality_cmd = subparsers.add_parser("compare-persona-quality")
    compare_persona_quality_cmd.add_argument("--baseline-backend", choices=PERSONA_ENRICH_BACKENDS, default="codex")
    compare_persona_quality_cmd.add_argument(
        "--candidate-backend",
        choices=PERSONA_ENRICH_BACKENDS,
        default=_default_persona_compare_candidate_backend(),
    )
    compare_persona_quality_cmd.add_argument("--judge-backend", choices=PERSONA_ENRICH_BACKENDS, default="codex")
    compare_persona_quality_cmd.add_argument("--seed", action="append", dest="seeds", type=int)
    compare_persona_quality_cmd.add_argument("--output-dir", type=Path, default=Path("experiments"))
    compare_persona_quality_cmd.add_argument("--experiment-id", default="")
    compare_persona_quality_cmd.add_argument("--baseline-label", default="")
    compare_persona_quality_cmd.add_argument("--candidate-label", default="")
    compare_persona_quality_cmd.add_argument("--judge-label", default="")
    compare_persona_quality_cmd.add_argument("--max-baseline-retries", type=int, default=1)
    compare_persona_quality_cmd.add_argument("--max-candidate-retries", type=int, default=3)
    compare_persona_quality_cmd.add_argument("--pause-seconds", type=float, default=6.0)

    chat_cmd = subparsers.add_parser("chat-with-persona")
    chat_cmd.add_argument("--persona-id")
    chat_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))
    chat_cmd.add_argument("--session-dir", type=Path, default=Path("conversations"))
    chat_cmd.add_argument("--resume", dest="session_id")
    chat_cmd.add_argument("--backend", choices=LIVE_CHAT_BACKENDS, default="mock")
    chat_cmd.add_argument("--model")
    chat_cmd.add_argument("--reasoning-effort", choices=["low", "medium", "high"])
    chat_cmd.add_argument("--friction-mode", choices=["off", "light", "natural", "high"], default="off")
    chat_cmd.add_argument("--message", action="append", dest="messages")

    interview_cmd = subparsers.add_parser("run-facilitated-interview")
    interview_cmd.add_argument("--persona-id", required=True)
    interview_cmd.add_argument("--research-goal", required=True)
    interview_cmd.add_argument("--interview-mode", choices=["pain_point_discovery", "adoption_barrier_validation", "prototype_validation", "decision_reconstruction", "explore_root_cause", "validate_hypothesis", "concept_validation"], default="explore_root_cause")
    interview_cmd.add_argument("--hypothesis", default="")
    interview_cmd.add_argument("--product-context", default="")
    interview_cmd.add_argument("--concept-protocol", default="")
    interview_cmd.add_argument("--concept-label", default="")
    interview_cmd.add_argument("--stimulus-type", choices=["text_concept", "image", "flow", "clickable", "live_app"], default="")
    interview_cmd.add_argument("--stimulus-artifact", default="")
    interview_cmd.add_argument("--prototype-task", default="")
    interview_cmd.add_argument("--language", default="Traditional Chinese")
    interview_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))
    interview_cmd.add_argument("--session-dir", type=Path, default=Path("interviews"))
    interview_cmd.add_argument("--backend", choices=LIVE_LLM_BACKENDS, default=_default_live_backend())
    interview_cmd.add_argument("--model", default=_default_live_model())
    interview_cmd.add_argument("--reasoning-effort", choices=["low", "medium", "high"], default="medium")
    interview_cmd.add_argument("--max-turns", type=int)
    interview_cmd.add_argument("--soft-turn-limit", type=int)
    interview_cmd.add_argument("--hard-turn-limit", type=int)
    interview_cmd.add_argument("--friction-mode", choices=["off", "light", "natural", "high"], default="off")
    interview_cmd.add_argument("--approved-learning-rules-path", type=Path)
    interview_cmd.add_argument("--debug-progress", action="store_true")

    observer_cmd = subparsers.add_parser("observe-facilitated-interview")
    observer_cmd.add_argument("--persona-id")
    observer_cmd.add_argument("--resume", dest="interview_id")
    observer_cmd.add_argument("--research-goal")
    observer_cmd.add_argument("--interview-mode", choices=["pain_point_discovery", "adoption_barrier_validation", "prototype_validation", "decision_reconstruction", "explore_root_cause", "validate_hypothesis", "concept_validation"], default="explore_root_cause")
    observer_cmd.add_argument("--hypothesis", default="")
    observer_cmd.add_argument("--product-context", default="")
    observer_cmd.add_argument("--concept-protocol", default="")
    observer_cmd.add_argument("--concept-label", default="")
    observer_cmd.add_argument("--stimulus-type", choices=["text_concept", "image", "flow", "clickable", "live_app"], default="")
    observer_cmd.add_argument("--stimulus-artifact", default="")
    observer_cmd.add_argument("--prototype-task", default="")
    observer_cmd.add_argument("--language", default="Traditional Chinese")
    observer_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))
    observer_cmd.add_argument("--session-dir", type=Path, default=Path("interviews"))
    observer_cmd.add_argument("--backend", choices=LIVE_LLM_BACKENDS, default=_default_live_backend())
    observer_cmd.add_argument("--model", default=_default_live_model())
    observer_cmd.add_argument("--reasoning-effort", choices=["low", "medium", "high"], default="medium")
    observer_cmd.add_argument("--max-turns", type=int)
    observer_cmd.add_argument("--soft-turn-limit", type=int)
    observer_cmd.add_argument("--hard-turn-limit", type=int)
    observer_cmd.add_argument("--friction-mode", choices=["off", "light", "natural", "high"], default="off")
    observer_cmd.add_argument("--approved-learning-rules-path", type=Path)
    observer_cmd.add_argument("--action", action="append", dest="actions")
    observer_cmd.add_argument("--debug-progress", action="store_true")

    concept_panel_generic_cmd = subparsers.add_parser("run-concept-panel")
    concept_panel_generic_cmd.add_argument("--research-goal", required=True)
    concept_panel_generic_cmd.add_argument("--product-context", required=True)
    concept_panel_generic_cmd.add_argument("--topic-label", required=True)
    concept_panel_generic_cmd.add_argument("--concept-protocol", default="")
    concept_panel_generic_cmd.add_argument("--concept-label", default="")
    concept_panel_generic_cmd.add_argument("--language", default="Natural Cantonese Traditional Chinese")
    concept_panel_generic_cmd.add_argument("--persona-id", action="append", dest="persona_ids")
    concept_panel_generic_cmd.add_argument("--core-assumption-count", type=int, default=8)
    concept_panel_generic_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))
    concept_panel_generic_cmd.add_argument("--output-dir", type=Path, default=Path("experiments"))
    concept_panel_generic_cmd.add_argument("--backend", choices=LIVE_LLM_BACKENDS, default=_default_live_backend())
    concept_panel_generic_cmd.add_argument("--model", default=_default_live_model())
    concept_panel_generic_cmd.add_argument("--reasoning-effort", choices=["low", "medium", "high"], default="medium")
    concept_panel_generic_cmd.add_argument("--max-turns", type=int)
    concept_panel_generic_cmd.add_argument("--soft-turn-limit", type=int)
    concept_panel_generic_cmd.add_argument("--hard-turn-limit", type=int)
    concept_panel_generic_cmd.add_argument("--friction-mode", choices=["off", "light", "natural", "high"], default="off")
    concept_panel_generic_cmd.add_argument("--approved-learning-rules-path", type=Path)
    concept_panel_generic_cmd.add_argument("--debug-progress", action="store_true")

    concept_panel_cmd = subparsers.add_parser("run-followup-copilot-panel")
    concept_panel_cmd.add_argument("--data-dir", type=Path, default=Path("data/personas"))
    concept_panel_cmd.add_argument("--output-dir", type=Path, default=Path("experiments"))
    concept_panel_cmd.add_argument("--backend", choices=LIVE_LLM_BACKENDS, default=_default_live_backend())
    concept_panel_cmd.add_argument("--model", default=_default_live_model())
    concept_panel_cmd.add_argument("--reasoning-effort", choices=["low", "medium", "high"], default="medium")
    concept_panel_cmd.add_argument("--max-turns", type=int)
    concept_panel_cmd.add_argument("--soft-turn-limit", type=int)
    concept_panel_cmd.add_argument("--hard-turn-limit", type=int)
    concept_panel_cmd.add_argument("--friction-mode", choices=["off", "light", "natural", "high"], default="off")
    concept_panel_cmd.add_argument("--approved-learning-rules-path", type=Path)
    concept_panel_cmd.add_argument("--debug-progress", action="store_true")

    concept_summary_generic_cmd = subparsers.add_parser("summarize-concept-panel")
    concept_summary_generic_cmd.add_argument("--run-dir", type=Path, required=True)
    concept_summary_generic_cmd.add_argument("--persona-id", action="append", dest="persona_ids", required=True)
    concept_summary_generic_cmd.add_argument("--topic-label", default="")
    concept_summary_generic_cmd.add_argument("--language", default="")
    concept_summary_generic_cmd.add_argument("--core-assumption-count", type=int)

    concept_summary_cmd = subparsers.add_parser("summarize-followup-copilot-panel")
    concept_summary_cmd.add_argument("--run-dir", type=Path, required=True)
    concept_summary_cmd.add_argument("--persona-id", action="append", dest="persona_ids", required=True)

    facilitator_audit_runs_cmd = subparsers.add_parser("aggregate-facilitator-audit-runs")
    facilitator_audit_runs_cmd.add_argument("--run-dir", type=Path, action="append", dest="run_dirs", required=True)
    facilitator_audit_runs_cmd.add_argument("--output-dir", type=Path, required=True)
    facilitator_audit_runs_cmd.add_argument("--label", default="Facilitator Audit Learning Report")

    promote_learning_rules_cmd = subparsers.add_parser("promote-facilitator-learning-rules")
    promote_learning_rules_cmd.add_argument("--report-path", type=Path, required=True)
    promote_learning_rules_cmd.add_argument("--registry-path", type=Path, required=True)
    promote_learning_rules_cmd.add_argument("--rule-id", action="append", dest="rule_ids", required=True)
    promote_learning_rules_cmd.add_argument("--approved-by", default="")
    promote_learning_rules_cmd.add_argument("--note", default="")

    disable_learning_rules_cmd = subparsers.add_parser("disable-facilitator-learning-rules")
    disable_learning_rules_cmd.add_argument("--registry-path", type=Path, required=True)
    disable_learning_rules_cmd.add_argument("--rule-id", action="append", dest="rule_ids", required=True)
    disable_learning_rules_cmd.add_argument("--disabled-by", default="")
    disable_learning_rules_cmd.add_argument("--note", default="")

    compare_learning_effects_cmd = subparsers.add_parser("compare-facilitator-learning-effects")
    compare_learning_effects_cmd.add_argument("--baseline-run-dir", type=Path, action="append", dest="baseline_run_dirs", required=True)
    compare_learning_effects_cmd.add_argument("--candidate-run-dir", type=Path, action="append", dest="candidate_run_dirs", required=True)
    compare_learning_effects_cmd.add_argument("--output-dir", type=Path, required=True)
    compare_learning_effects_cmd.add_argument("--label", default="Facilitator Learning Effect Report")

    return parser


def _cmd_generate(args: argparse.Namespace) -> int:
    ensure_dir(args.output_dir)
    enricher, judge = _build_persona_generation_components(args)
    openai_config = getattr(args, "_resolved_openai_config", None)
    personas = generate_personas(count=args.count, random_seed=args.seed, enricher=enricher, judge=judge)
    for persona in personas:
        save_persona(persona, args.output_dir)
    backend_note = "template"
    if enricher is not None:
        provider_note = "codex" if args.backend == "codex" else getattr(openai_config, "provider_name", args.backend)
        backend_note = f"{provider_note}-enriched"
    if judge is not None:
        backend_note = f"{backend_note}+judge"
    auth_note = ""
    if openai_config is not None:
        auth_note = f" auth_source={openai_config.auth_source}"
    print(f"Generated {len(personas)} personas in {args.output_dir} using {backend_note}.{auth_note}")
    return 0


def _cmd_list(args: argparse.Namespace) -> int:
    personas = load_personas(args.data_dir)
    if not personas:
        print("No personas found.")
        return 0
    for persona in personas:
        identity = persona.profile.basic_identity
        print(
            f"{identity['synthetic_user_id']} | {identity['name']} | "
            f"{persona.seed.panel_role} | {identity['occupation']} | {identity['location']}"
        )
    return 0


def _cmd_sample(args: argparse.Namespace) -> int:
    personas = load_personas(args.data_dir)
    panel_spec = _resolve_panel_spec(
        panel_type=args.panel_type,
        sample_size=args.sample_size,
        random_seed=args.seed,
        raw_filters=args.filters,
    )
    sampling_result = sample_personas(personas, panel_spec)
    print(sampling_result.rationale)
    for persona in sampling_result.personas:
        identity = persona.profile.basic_identity
        print(f"- {identity['synthetic_user_id']} | {identity['name']} | {identity['occupation']}")
    return 0


def _cmd_validate(args: argparse.Namespace) -> int:
    personas = load_personas(args.data_dir)
    if not personas:
        print("No personas found.")
        return 1

    issues = validate_personas(personas)
    if not issues:
        print(f"Validation passed for {len(personas)} personas.")
        return 0

    issue_counts = Counter(issue.check_name for issue in issues)
    print(f"Validation found {len(issues)} issues across {len(personas)} personas.")
    print("Issue summary:")
    for check_name, count in sorted(issue_counts.items()):
        print(f"- {check_name}: {count}")
    print("Issues:")
    for issue in issues:
        print(f"- {issue.persona_id} | {issue.check_name} | {issue.message}")
    return 1


def _cmd_migrate_personas_v2(args: argparse.Namespace) -> int:
    personas = load_personas(args.input_dir)
    if not personas:
        print("No personas found.")
        return 1

    selected = _select_personas_by_id(personas, persona_ids=args.persona_ids, limit=args.limit)
    if not selected:
        print("No personas selected for v2 migration.")
        return 1

    ensure_dir(args.output_dir)
    written_folders = migrate_personas_to_v2(
        personas=selected,
        output_dir=args.output_dir,
        source_base_dir=args.input_dir,
        random_seed_offset=args.seed_offset,
    )
    print(f"Migrated {len(written_folders)} personas to v2 artifacts in {args.output_dir}")
    return 0


def _cmd_validate_personas_v2(args: argparse.Namespace) -> int:
    report = validate_v2_persona_library(args.data_dir)
    if report["library_size"] == 0:
        print("No personas found.")
        return 1

    if report["issue_count"] == 0 and report["warning_count"] == 0:
        print(f"V2 validation passed for {report['library_size']} personas.")
        return 0

    print(
        f"V2 validation found {report['issue_count']} issues and "
        f"{report['warning_count']} warnings across {report['library_size']} personas."
    )
    for persona_report in report["persona_reports"]:
        persona_id = persona_report["persona_id"]
        for message in persona_report["missing_fields"]:
            print(f"- {persona_id} | missing_field | {message}")
        for message in persona_report["consistency_warnings"]:
            print(f"- {persona_id} | consistency_warning | {message}")
        for message in persona_report["stereotype_warnings"]:
            print(f"- {persona_id} | stereotype_warning | {message}")
    return 1


def _cmd_generate_v3_persona(args: argparse.Namespace) -> int:
    written_paths = generate_v3_personas(
        persona_ids=args.persona_ids,
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        compare_against_dir=args.compare_against,
        against_persona_ids=args.against_persona_ids,
        random_seed_offset=args.seed_offset,
    )
    print(f"Generated {len(written_paths)} V3 personas in {args.output_dir}")
    return 0


def _cmd_run_distinctiveness_check(args: argparse.Namespace) -> int:
    report = run_distinctiveness_check(
        base_dir=args.data_dir,
        persona_id=args.persona_id,
        against_persona_ids=args.against_persona_ids,
    )
    if args.output is not None:
        ensure_dir(args.output.parent)
        write_json(args.output, report)
        print(f"Distinctiveness report written to {args.output}")
    else:
        print(f"Persona: {report['synthetic_user_id']}")
        print(f"Compared against: {', '.join(report['compared_against']) or '(none)'}")
        print(f"Overall similarity score: {report['overall_similarity_score']}")
        print(f"Distinctiveness score: {report['distinctiveness_score']}")
        for warning in report["warnings"]:
            print(f"- warning: {warning}")
    return 0


def _cmd_validate_personas_v3(args: argparse.Namespace) -> int:
    report = validate_v3_persona_library(args.data_dir)
    if report["library_size"] == 0:
        print("No personas found.")
        return 1

    if report["issue_count"] == 0 and report["warning_count"] == 0:
        print(f"V3 validation passed for {report['library_size']} personas.")
        return 0

    print(
        f"V3 validation found {report['issue_count']} issues and "
        f"{report['warning_count']} warnings across {report['library_size']} personas."
    )
    for persona_report in report["persona_reports"]:
        persona_id = persona_report["persona_id"]
        for message in persona_report["missing_fields"]:
            print(f"- {persona_id} | missing_field | {message}")
        for message in persona_report["consistency_warnings"]:
            print(f"- {persona_id} | consistency_warning | {message}")
        for message in persona_report["stereotype_warnings"]:
            print(f"- {persona_id} | stereotype_warning | {message}")
    return 1


def _cmd_generate_v3_1_persona(args: argparse.Namespace) -> int:
    written_paths = generate_v3_1_personas(
        persona_ids=args.persona_ids,
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        compare_against_dir=args.compare_against,
        against_persona_ids=args.against_persona_ids,
        random_seed_offset=args.seed_offset,
    )
    print(f"Generated {len(written_paths)} V3.1 personas in {args.output_dir}")
    return 0


def _cmd_run_distinctiveness_check_v3_1(args: argparse.Namespace) -> int:
    report = run_distinctiveness_check_v3_1(
        base_dir=args.data_dir,
        persona_id=args.persona_id,
        against_persona_ids=args.against_persona_ids,
    )
    if args.output is not None:
        ensure_dir(args.output.parent)
        write_json(args.output, report)
        print(f"Distinctiveness report written to {args.output}")
    else:
        print(f"Persona: {report['synthetic_user_id']}")
        print(f"Compared against: {', '.join(report['compared_against']) or '(none)'}")
        print(f"Overall similarity score: {report['overall_similarity_score']}")
        print(f"Distinctiveness score: {report['distinctiveness_score']}")
        for warning in report["warnings"]:
            print(f"- warning: {warning}")
    return 0


def _cmd_validate_personas_v3_1(args: argparse.Namespace) -> int:
    report = validate_v3_1_persona_library(args.data_dir)
    if report["library_size"] == 0:
        print("No personas found.")
        return 1

    if report["issue_count"] == 0 and report["warning_count"] == 0:
        print(f"V3.1 validation passed for {report['library_size']} personas.")
        return 0

    print(
        f"V3.1 validation found {report['issue_count']} issues and "
        f"{report['warning_count']} warnings across {report['library_size']} personas."
    )
    for persona_report in report["persona_reports"]:
        persona_id = persona_report["persona_id"]
        for message in persona_report["missing_fields"]:
            print(f"- {persona_id} | missing_field | {message}")
        for message in persona_report["consistency_warnings"]:
            print(f"- {persona_id} | consistency_warning | {message}")
        for message in persona_report["stereotype_warnings"]:
            print(f"- {persona_id} | stereotype_warning | {message}")
    return 1


def _cmd_generate_v3_1_1_persona(args: argparse.Namespace) -> int:
    written_paths = generate_v3_1_1_personas(
        persona_ids=args.persona_ids,
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        compare_against_dir=args.compare_against,
        against_persona_ids=args.against_persona_ids,
        random_seed_offset=args.seed_offset,
    )
    print(f"Generated {len(written_paths)} V3.1.1 personas in {args.output_dir}")
    return 0


def _cmd_generate_v3_1_2_persona(args: argparse.Namespace) -> int:
    written_paths = generate_v3_1_2_personas(
        persona_ids=args.persona_ids,
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        compare_against_dir=args.compare_against,
        against_persona_ids=args.against_persona_ids,
        random_seed_offset=args.seed_offset,
        max_attempts=args.max_attempts,
    )
    print(f"Generated {len(written_paths)} V3.1.2 personas in {args.output_dir}")
    return 0


def _cmd_generate_v3_2_persona(args: argparse.Namespace) -> int:
    from ai_validation_swarm.providers.openai_client import OpenAIResponsesClient

    config = _load_live_llm_config(args.backend)
    if args.backend == "codex" and config.transport == "codex_cli" and config.codex_cli_output_mode == "auto":
        config.codex_cli_output_mode = "direct"
    progress_writer = (lambda message: print(message, flush=True)) if args.debug_progress else None
    client = OpenAIResponsesClient(config, debug_writer=progress_writer)
    adapter = OpenAIV32SynthesisAdapter(client, config)
    if progress_writer is not None:
        progress_writer(
            f"[v3.2] backend={args.backend} transport={config.transport} model={config.model} "
            f"reasoning={config.model_reasoning_effort} timeout={config.timeout_seconds}s "
            f"batch_size={args.section_batch_size or 'full'}"
        )
    if args.section_batch_size:
        adapter = SectionBatchedV32SynthesisAdapter(
            adapter,
            batch_size=args.section_batch_size,
            cache_dir=args.output_dir / ".v3_2_generation_cache",
            progress_writer=progress_writer,
        )
    generation_briefs = {}
    if args.brief_dir:
        for persona_id in args.persona_ids:
            brief_path = args.brief_dir / f"{persona_id}.json"
            if not brief_path.exists():
                raise ValueError(f"Generation brief not found: {brief_path}")
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            if not isinstance(brief, dict):
                raise ValueError(f"Generation brief must be an object: {brief_path}")
            if brief.get("synthetic_user_id") not in {None, persona_id}:
                raise ValueError(f"Generation brief ID does not match {persona_id}: {brief_path}")
            generation_briefs[persona_id] = brief
    comparison_personas = []
    if args.compare_against.exists():
        for persona_root in sorted(path for path in args.compare_against.iterdir() if path.is_dir()):
            folder = persona_root / "v3_2"
            if not folder.exists():
                continue
            try:
                comparison_personas.append(load_persona(folder))
            except (OSError, ValueError, KeyError):
                continue
    written_paths = generate_v3_2_personas(
        persona_ids=args.persona_ids,
        output_dir=args.output_dir,
        adapter=adapter,
        enabled_sections=args.enabled_sections,
        random_seed_offset=args.seed_offset,
        max_attempts=args.max_attempts,
        comparison_personas=comparison_personas,
        generation_briefs=generation_briefs,
        progress_writer=progress_writer,
    )
    print(
        f"Generated {len(written_paths)} V3.2 personas in {args.output_dir} "
        f"using {args.backend} direct synthesis."
    )
    return 0


def _cmd_validate_personas_v3_2(args: argparse.Namespace) -> int:
    reports = []
    if args.data_dir.exists():
        for persona_root in sorted(path for path in args.data_dir.iterdir() if path.is_dir()):
            folder = persona_root / "v3_2"
            if folder.exists():
                reports.append((persona_root.name, validate_v3_2_persona_folder(folder)))
    if not reports:
        print("No V3.2 personas found.")
        return 1
    invalid = [(persona_id, report) for persona_id, report in reports if not report["valid"]]
    if not invalid:
        print(f"V3.2 validation passed for {len(reports)} personas.")
        return 0
    print(f"V3.2 validation found issues in {len(invalid)} of {len(reports)} personas.")
    for persona_id, report in invalid:
        for message in report["missing_fields"]:
            print(f"- {persona_id} | missing_field | {message}")
        for message in report["warnings"]:
            print(f"- {persona_id} | warning | {message}")
    return 1


def _cmd_generate_v3_3_persona(args: argparse.Namespace) -> int:
    from ai_validation_swarm.providers.openai_client import OpenAIResponsesClient

    config = _load_live_llm_config(args.backend)
    progress_writer = (lambda message: print(message, flush=True)) if args.debug_progress else None
    client = OpenAIResponsesClient(config, debug_writer=progress_writer)
    if progress_writer is not None:
        progress_writer(
            f"[v3.3] backend={args.backend} transport={config.transport} model={config.model} "
            f"reasoning={config.model_reasoning_effort} timeout={config.timeout_seconds}s "
            f"repair_batch_size={args.repair_batch_size}"
        )
    primary_adapter = OpenAIV33SynthesisAdapter(client, config)
    repair_adapter = SectionBatchedV32SynthesisAdapter(
        OpenAIV33SynthesisAdapter(client, config),
        batch_size=args.repair_batch_size,
        cache_dir=args.output_dir / ".v3_3_repair_cache",
        progress_writer=progress_writer,
    )
    adapter = FullPassRepairV33SynthesisAdapter(
        primary_adapter,
        repair_adapter,
        progress_writer=progress_writer,
        state_dir=args.output_dir / ".v3_3_resume_state",
    )
    generation_briefs = {}
    if args.brief_dir:
        for persona_id in args.persona_ids:
            brief_path = args.brief_dir / f"{persona_id}.json"
            if not brief_path.exists():
                raise ValueError(f"Generation brief not found: {brief_path}")
            brief = json.loads(brief_path.read_text(encoding="utf-8"))
            if not isinstance(brief, dict):
                raise ValueError(f"Generation brief must be an object: {brief_path}")
            if brief.get("synthetic_user_id") not in {None, persona_id}:
                raise ValueError(f"Generation brief ID does not match {persona_id}: {brief_path}")
            generation_briefs[persona_id] = brief
    comparison_personas = []
    if args.compare_against.exists():
        for persona_root in sorted(path for path in args.compare_against.iterdir() if path.is_dir()):
            folder = persona_root / "v3_3"
            if not folder.exists():
                continue
            try:
                comparison_personas.append(load_persona(folder))
            except (OSError, ValueError, KeyError):
                continue
    written_paths = generate_v3_3_personas(
        persona_ids=args.persona_ids,
        output_dir=args.output_dir,
        adapter=adapter,
        enabled_sections=args.enabled_sections,
        random_seed_offset=args.seed_offset,
        max_attempts=args.max_attempts,
        comparison_personas=comparison_personas,
        generation_briefs=generation_briefs,
        progress_writer=progress_writer,
    )
    print(
        f"Generated {len(written_paths)} V3.3 personas in {args.output_dir} "
        f"using {args.backend} full synthesis with repair fallback."
    )
    return 0


def _cmd_validate_personas_v3_3(args: argparse.Namespace) -> int:
    reports = []
    if args.data_dir.exists():
        for persona_root in sorted(path for path in args.data_dir.iterdir() if path.is_dir()):
            folder = persona_root / "v3_3"
            if folder.exists():
                reports.append((persona_root.name, validate_v3_3_persona_folder(folder)))
    if not reports:
        print("No V3.3 personas found.")
        return 1
    invalid = [(persona_id, report) for persona_id, report in reports if not report["valid"]]
    if not invalid:
        print(f"V3.3 validation passed for {len(reports)} personas.")
        return 0
    print(f"V3.3 validation found issues in {len(invalid)} of {len(reports)} personas.")
    for persona_id, report in invalid:
        for message in report["missing_fields"]:
            print(f"- {persona_id} | missing_field | {message}")
        for message in report["warnings"]:
            print(f"- {persona_id} | warning | {message}")
    return 1


def _parse_v5_guide_values(items: list[str]) -> dict[str, object]:
    parsed: dict[str, object] = {}
    for item in items:
        if "=" not in item:
            raise ValueError(f"Invalid guide value '{item}'. Expected KEY=VALUE.")
        key, raw_value = item.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid guide value '{item}'. KEY cannot be empty.")
        value_text = raw_value.strip()
        try:
            value: object = json.loads(value_text)
        except json.JSONDecodeError:
            value = value_text
        parsed[key] = value
    return parsed


def _build_v5_adapter_components(
    *,
    backend: str,
    output_dir: Path,
    persona_id: str,
    progress_writer,
):
    from ai_validation_swarm.providers.openai_client import OpenAIResponsesClient

    config = _load_live_llm_config(backend, timeout_default=360)
    transport_log = output_dir / persona_id / "v5_1" / "llm_transport.log"
    ensure_dir(transport_log.parent)

    def transport_writer(message: str) -> None:
        with transport_log.open("a", encoding="utf-8") as handle:
            handle.write(message + "\n")
        if progress_writer is not None:
            progress_writer(message)

    client = OpenAIResponsesClient(config, debug_writer=transport_writer)
    return config, OpenAIV5SynthesisAdapter(client, config)


def _cmd_generate_v5_persona(args: argparse.Namespace) -> int:
    progress_writer = (lambda message: print(_console_safe(message), flush=True)) if args.debug_progress else None
    config, adapter = _build_v5_adapter_components(
        backend=args.backend,
        output_dir=args.output_dir,
        persona_id=args.persona_id,
        progress_writer=progress_writer,
    )

    guide: dict[str, object] = {"mode": "open", "fixed": {}, "preferred": {}}
    if args.guide_file:
        if not args.guide_file.exists():
            raise ValueError(f"V5 guide file not found: {args.guide_file}")
        loaded = json.loads(args.guide_file.read_text(encoding="utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("V5 guide file must contain one JSON object.")
        guide = loaded
    fixed = dict(guide.get("fixed", {})) if isinstance(guide.get("fixed", {}), dict) else {}
    preferred = dict(guide.get("preferred", {})) if isinstance(guide.get("preferred", {}), dict) else {}
    fixed.update(_parse_v5_guide_values(args.fixed))
    preferred.update(_parse_v5_guide_values(args.prefer))
    if args.interest:
        preferred["interests"] = list(args.interest)
    guide["fixed"] = fixed
    guide["preferred"] = preferred
    guide["mode"] = "guided" if fixed or preferred or args.guide_file else "open"

    if progress_writer is not None:
        progress_writer(
            f"[v5] backend={args.backend} transport={config.transport} model={config.model} "
            f"reasoning={config.model_reasoning_effort} timeout={config.timeout_seconds}s guide_mode={guide['mode']}"
        )
    target = generate_v5_persona(
        persona_id=args.persona_id,
        output_dir=args.output_dir,
        adapter=adapter,
        guide=guide,
        random_seed=args.random_seed,
        max_transport_attempts=args.max_transport_attempts,
        resume_response=args.resume_response,
        progress_writer=progress_writer,
    )
    print(f"Generated V5 persona {args.persona_id} at {target} using {args.backend}.")
    return 0


def _cmd_generate_v5_panel(args: argparse.Namespace) -> int:
    progress_writer = (lambda message: print(_console_safe(message), flush=True)) if args.debug_progress else None
    print(
        "Legacy preset warning: generate-v5-panel exists only for backward-compatible project regeneration. "
        "It is not the current default V5 panel path."
    )
    panel = build_v5_panel_preset(args.panel_preset, starting_id=args.starting_id)
    generated: list[dict[str, str]] = []

    for offset, persona_spec in enumerate(panel["personas"]):
        persona_id = str(persona_spec["persona_id"])
        persona_seed = args.random_seed + offset if args.random_seed is not None else None
        config, adapter = _build_v5_adapter_components(
            backend=args.backend,
            output_dir=args.output_dir,
            persona_id=persona_id,
            progress_writer=progress_writer,
        )
        guide = dict(persona_spec["guide"])
        if progress_writer is not None:
            progress_writer(
                f"[v5-panel] preset={args.panel_preset} persona_id={persona_id} "
                f"label={persona_spec['label']} transport={config.transport}"
            )
        target = generate_v5_persona(
            persona_id=persona_id,
            output_dir=args.output_dir,
            adapter=adapter,
            guide=guide,
            random_seed=persona_seed,
            max_transport_attempts=args.max_transport_attempts,
            progress_writer=progress_writer,
        )
        generated.append(
            {
                "persona_id": persona_id,
                "label": str(persona_spec["label"]),
                "archetype": str(persona_spec["archetype"]),
                "path": str(target),
            }
        )

    manifest_dir = args.output_dir / "_panel_runs"
    ensure_dir(manifest_dir)
    manifest_path = manifest_dir / f"{args.panel_preset}_{args.starting_id}.json"
    write_json(
        manifest_path,
        {
            "preset_name": panel["preset_name"],
            "starting_id": panel["starting_id"],
            "persona_count": panel["persona_count"],
            "generated": generated,
        },
    )
    print(f"Generated V5 panel {args.panel_preset} with {len(generated)} personas.")
    print(f"Manifest: {manifest_path}")
    return 0


def _cmd_validate_personas_v5(args: argparse.Namespace) -> int:
    reports = []
    if args.data_dir.exists():
        for persona_root in sorted(path for path in args.data_dir.iterdir() if path.is_dir()):
            folder = persona_root / "v5_1"
            if folder.exists():
                reports.append((persona_root.name, validate_v5_persona_folder(folder)))
    if not reports:
        print("No V5 personas found.")
        return 1
    invalid = [(persona_id, report) for persona_id, report in reports if not report["valid"]]
    if not invalid:
        print(f"V5 validation passed for {len(reports)} personas.")
        return 0
    print(f"V5 validation found issues in {len(invalid)} of {len(reports)} personas.")
    for persona_id, report in invalid:
        for message in report["missing_fields"]:
            print(f"- {persona_id} | missing_field | {message}")
        for message in report["warnings"]:
            print(f"- {persona_id} | warning | {message}")
    return 1


def _cmd_generate_persona_to_target(args: argparse.Namespace) -> int:
    if args.target_version == "v3":
        written_paths = generate_v3_personas(
            persona_ids=args.persona_ids,
            source_dir=args.source_dir,
            output_dir=args.output_dir,
            compare_against_dir=args.compare_against,
            against_persona_ids=args.against_persona_ids,
            random_seed_offset=args.seed_offset,
        )
    elif args.target_version == "v3_1":
        written_paths = generate_v3_1_personas(
            persona_ids=args.persona_ids,
            source_dir=args.source_dir,
            output_dir=args.output_dir,
            compare_against_dir=args.compare_against,
            against_persona_ids=args.against_persona_ids,
            random_seed_offset=args.seed_offset,
        )
    elif args.target_version == "v3_1_2":
        written_paths = generate_v3_1_2_personas(
            persona_ids=args.persona_ids,
            source_dir=args.source_dir,
            output_dir=args.output_dir,
            compare_against_dir=args.compare_against,
            against_persona_ids=args.against_persona_ids,
            random_seed_offset=args.seed_offset,
            max_attempts=args.max_attempts,
        )
    else:
        written_paths = generate_v3_1_1_personas(
            persona_ids=args.persona_ids,
            source_dir=args.source_dir,
            output_dir=args.output_dir,
            compare_against_dir=args.compare_against,
            against_persona_ids=args.against_persona_ids,
            random_seed_offset=args.seed_offset,
        )
    print(f"Generated {len(written_paths)} personas to target {args.target_version} in {args.output_dir}")
    return 0


def _cmd_run_distinctiveness_check_v3_1_1(args: argparse.Namespace) -> int:
    report = run_distinctiveness_check_v3_1_1(
        base_dir=args.data_dir,
        persona_id=args.persona_id,
        against_persona_ids=args.against_persona_ids,
    )
    if args.output is not None:
        ensure_dir(args.output.parent)
        write_json(args.output, report)
        print(f"Distinctiveness report written to {args.output}")
    else:
        print(f"Persona: {report['synthetic_user_id']}")
        print(f"Compared against: {', '.join(report['compared_against']) or '(none)'}")
        print(f"Overall similarity score: {report['overall_similarity_score']}")
        print(f"Distinctiveness score: {report['distinctiveness_score']}")
        for warning in report["warnings"]:
            print(f"- warning: {warning}")
    return 0


def _cmd_run_distinctiveness_check_v3_1_2(args: argparse.Namespace) -> int:
    report = run_distinctiveness_check_v3_1_2(
        base_dir=args.data_dir,
        persona_id=args.persona_id,
        against_persona_ids=args.against_persona_ids,
    )
    if args.output is not None:
        ensure_dir(args.output.parent)
        write_json(args.output, report)
        print(f"Distinctiveness report written to {args.output}")
    else:
        print(f"Persona: {report['synthetic_user_id']}")
        print(f"Compared against: {', '.join(report['compared_against']) or '(none)'}")
        print(f"Overall similarity score: {report['overall_similarity_score']}")
        print(f"Distinctiveness score: {report['distinctiveness_score']}")
        for warning in report["warnings"]:
            print(f"- warning: {warning}")
    return 0


def _cmd_validate_personas_v3_1_1(args: argparse.Namespace) -> int:
    report = validate_v3_1_1_persona_library(args.data_dir)
    if report["library_size"] == 0:
        print("No personas found.")
        return 1

    if report["issue_count"] == 0 and report["warning_count"] == 0:
        print(f"V3.1.1 validation passed for {report['library_size']} personas.")
        return 0

    print(
        f"V3.1.1 validation found {report['issue_count']} issues and "
        f"{report['warning_count']} warnings across {report['library_size']} personas."
    )
    for persona_report in report["persona_reports"]:
        persona_id = persona_report["persona_id"]
        for message in persona_report["missing_fields"]:
            print(f"- {persona_id} | missing_field | {message}")
        for message in persona_report["consistency_warnings"]:
            print(f"- {persona_id} | consistency_warning | {message}")
        for message in persona_report["stereotype_warnings"]:
            print(f"- {persona_id} | stereotype_warning | {message}")
    return 1


def _cmd_validate_personas_v3_1_2(args: argparse.Namespace) -> int:
    report = validate_v3_1_2_persona_library(args.data_dir)
    if report["library_size"] == 0:
        print("No personas found.")
        return 1

    if report["issue_count"] == 0 and report["warning_count"] == 0:
        print(f"V3.1.2 validation passed for {report['library_size']} personas.")
        return 0

    print(
        f"V3.1.2 validation found {report['issue_count']} issues and "
        f"{report['warning_count']} warnings across {report['library_size']} personas."
    )
    for persona_report in report["persona_reports"]:
        persona_id = persona_report["persona_id"]
        for message in persona_report["missing_fields"]:
            print(f"- {persona_id} | missing_field | {message}")
        for message in persona_report["consistency_warnings"]:
            print(f"- {persona_id} | consistency_warning | {message}")
        for message in persona_report["stereotype_warnings"]:
            print(f"- {persona_id} | stereotype_warning | {message}")
    return 1


def _cmd_summarize_personas(args: argparse.Namespace) -> int:
    personas = load_personas(args.data_dir)
    if not personas:
        print("No personas found.")
        return 1

    summary = build_persona_library_summary(personas)
    if args.output is not None:
        ensure_dir(args.output.parent)
        write_json(args.output, summary)
        print(f"Persona summary written to {args.output}")
    else:
        print(f"Persona library size: {summary['library_size']}")
        print(f"Unique names: {summary['unique_name_count']}")
        print("Distinct counts:")
        for key, value in summary["distinct_counts"].items():
            print(f"- {key}: {value}")
        print("Coverage checks:")
        for key, value in summary["coverage_checks"].items():
            print(f"- {key}: {value}")
    return 0


def _cmd_inspect_openai_auth(args: argparse.Namespace) -> int:
    from ai_validation_swarm.providers.openai_client import inspect_openai_auth

    config = _load_openai_runtime_config()
    summary = inspect_openai_auth(config)
    if args.output is not None:
        ensure_dir(args.output.parent)
        write_json(args.output, summary)
        print(f"OpenAI auth summary written to {args.output}")
    else:
        print(f"Auth source: {summary['auth_source']}")
        print(f"Transport: {summary['transport']}")
        print(f"Has api.responses.write scope: {summary['has_api_responses_write_scope']}")
        scopes = ", ".join(summary["scopes"]) if summary["scopes"] else "(none)"
        print(f"Scopes: {scopes}")
    return 0


def _cmd_probe_codex_auth(args: argparse.Namespace) -> int:
    from ai_validation_swarm.providers.openai_client import inspect_openai_auth

    client, config, codex_cli_path, codex_home = _build_codex_probe_components()
    report = {
        "ok": False,
        "codex_cli_path": str(codex_cli_path),
        "codex_home": str(codex_home),
        "probe_transport": "codex_cli",
        "auth": inspect_openai_auth(config),
    }

    try:
        result = client.create_json_response(
            system_prompt="Return exactly one JSON object that matches the schema.",
            user_prompt="Set ok=true and message='codex probe succeeded'.",
            output_schema={
                "type": "object",
                "additionalProperties": False,
                "required": ["ok", "message"],
                "properties": {
                    "ok": {"type": "boolean"},
                    "message": {"type": "string"},
                },
            },
        )
        report["ok"] = bool(result.get("ok"))
        report["result"] = result
    except OpenAIProviderError as exc:
        report["error"] = str(exc)

    if args.output is not None:
        ensure_dir(args.output.parent)
        write_json(args.output, report)
        print(f"Codex auth probe written to {args.output}")
    else:
        print(f"Codex CLI path: {report['codex_cli_path']}")
        print(f"Codex home: {report['codex_home']}")
        print(f"Probe ok: {report['ok']}")
        if "result" in report:
            print(f"Probe result: {report['result']}")
        if "error" in report:
            print(f"Probe error: {report['error']}")
    return 0 if report["ok"] else 1


def _cmd_enrich_personas(args: argparse.Namespace) -> int:
    ensure_dir(args.output_dir)
    enricher, judge = _build_persona_generation_components(args)
    report_path = args.report or (args.output_dir / "llm_batch_report.json")
    openai_config = getattr(args, "_resolved_openai_config", None)
    report_payload_base = {
        "input_dir": str(args.input_dir),
        "output_dir": str(args.output_dir),
        "backend": args.backend,
        "judge_personas": bool(args.judge_personas),
        "resume_enabled": not args.no_resume,
        "limit": args.limit,
        "target_count": args.target_count,
        "batch_size": args.batch_size,
        "max_rounds": args.max_rounds,
        "max_stall_rounds": args.max_stall_rounds,
        "max_persona_failures": args.max_persona_failures,
        "workers": args.workers,
        "provider_name": getattr(openai_config, "provider_name", ""),
        "auth_source": getattr(openai_config, "auth_source", ""),
        "transport": getattr(openai_config, "transport", ""),
    }

    if args.target_count is not None:
        batch_size = args.batch_size or args.limit or 1
        target_result = enrich_persona_library_to_target(
            input_dir=args.input_dir,
            output_dir=args.output_dir,
            enricher=enricher,
            judge=judge,
            target_count=args.target_count,
            batch_size=batch_size,
            resume=not args.no_resume,
            workers=args.workers,
            max_rounds=args.max_rounds,
            max_stall_rounds=args.max_stall_rounds,
            max_persona_failures=args.max_persona_failures,
        )
        round_failures = [
            failure
            for round_result in target_result.rounds
            for failure in round_result.batch.failures
        ]
        report_payload = {
            **report_payload_base,
            "mode": "target",
            "valid_output_persona_ids": list_valid_persona_ids(args.output_dir),
            "failures": round_failures,
            **target_result.to_dict(),
        }
        write_json(report_path, report_payload)
        print(
            f"Persona target enrichment completed: valid={target_result.final_valid_count}/{target_result.target_count}, "
            f"rounds={len(target_result.rounds)}, completed={target_result.completed}, "
            f"stop_reason={target_result.stopped_reason}. Report: {report_path}"
        )
        return 0 if target_result.completed else 1

    result = enrich_persona_library(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        enricher=enricher,
        judge=judge,
        limit=args.limit,
        resume=not args.no_resume,
        workers=args.workers,
    )
    report_payload = {
        **report_payload_base,
        "mode": "single_batch",
        **result.to_dict(),
    }
    write_json(report_path, report_payload)
    print(
        f"Persona enrichment batch completed: processed={result.processed_count}, "
        f"succeeded={result.succeeded_count}, skipped={result.skipped_count}, failed={result.failed_count}. "
        f"Report: {report_path}"
    )
    return 0 if result.failed_count == 0 else 1


def _cmd_validate_brief(args: argparse.Namespace) -> int:
    brief = load_and_validate_founder_brief(args.brief)
    print(f"Founder brief is valid: {brief.brief_id} | {brief.project_name}")
    return 0


def _cmd_run(args: argparse.Namespace) -> int:
    panel_spec = _resolve_panel_spec(
        panel_type=args.panel_type,
        sample_size=args.sample_size,
        random_seed=args.seed,
        raw_filters=args.filters,
    )
    provider = build_provider(args.provider)
    run_dir = run_validation(args.brief, args.data_dir, panel_spec, provider, args.run_dir, max_retries=args.max_retries)
    print(f"Validation run archived at {run_dir}")
    return 0


def _cmd_audit(args: argparse.Namespace) -> int:
    findings = read_json(args.run_path / "audit.json")
    for finding in findings:
        print(f"{finding['category']} [{finding['severity']}]: {finding['observation']}")
    return 0


def _cmd_export(args: argparse.Namespace) -> int:
    export_format = _resolve_export_format(args.output, args.format)
    ensure_dir(args.output.parent)

    if export_format == "markdown":
        export_file(args.run_path / "report.md", args.output)
    elif export_format == "json":
        report_payload = read_json(args.run_path / "report.json")
        write_json(args.output, report_payload)
    elif export_format == "csv":
        report_payload = read_json(args.run_path / "report.json")
        args.output.write_text(render_report_csv(report_payload), encoding="utf-8")
    else:  # pragma: no cover
        raise ValueError(f"Unsupported export format '{export_format}'.")
    print(f"Exported report to {args.output}")
    return 0


def _cmd_run_evaluation(args: argparse.Namespace) -> int:
    provider = build_provider(args.provider)
    evaluation_dir = run_evaluation_suite(
        suite_path=args.suite,
        persona_dir=args.data_dir,
        provider=provider,
        output_root=args.output_dir,
        max_retries=args.max_retries,
        repeat_count=args.repeat_count,
    )
    print(f"Evaluation suite archived at {evaluation_dir}")
    return 0


def _cmd_compare_evaluations(args: argparse.Namespace) -> int:
    comparison = compare_evaluation_files(
        baseline_path=args.baseline,
        candidate_path=args.candidate,
        output_path=args.output,
    )
    print(
        f"Compared {comparison['fixture_count']} fixtures; "
        f"{comparison['changed_fixture_count']} changed, "
        f"{comparison['unchanged_fixture_count']} unchanged."
    )
    if args.output is not None:
        print(f"Comparison written to {args.output}")
    return 0


def _cmd_compare_persona_quality(args: argparse.Namespace) -> int:
    from ai_validation_swarm.evaluation.persona_quality_compare import run_persona_quality_compare

    report = run_persona_quality_compare(
        seeds=args.seeds or [101, 202, 303],
        output_root=args.output_dir,
        experiment_id=args.experiment_id,
        baseline_backend=args.baseline_backend,
        candidate_backend=args.candidate_backend,
        judge_backend=args.judge_backend,
        baseline_label=args.baseline_label,
        candidate_label=args.candidate_label,
        judge_label=args.judge_label,
        max_baseline_retries=args.max_baseline_retries,
        max_candidate_retries=args.max_candidate_retries,
        pause_seconds=args.pause_seconds,
    )
    print(
        f"Persona quality compare completed: seeds={len(report['seeds'])}, "
        f"baseline={report['setup']['baseline_label']}, "
        f"candidate={report['setup']['candidate_label']}. "
        f"Report: {report['output_paths']['report_json']}"
    )
    return 0


def _cmd_chat_with_persona(args: argparse.Namespace) -> int:
    from ai_validation_swarm.conversation.runtime import ConversationRuntime

    if not args.session_id and not args.persona_id:
        raise ValueError("Provide --persona-id to start a chat, or --resume to continue one.")
    if args.session_id and args.persona_id:
        raise ValueError("Use either --persona-id or --resume, not both.")

    provider = _build_conversation_provider(
        args.backend,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
    )
    runtime = ConversationRuntime(data_dir=args.data_dir, session_dir=args.session_dir, provider=provider)
    if args.session_id:
        session, persona, persona_folder = runtime.resume(args.session_id)
        if session.provider != provider.provider_name:
            raise ValueError(
                f"Session uses provider '{session.provider}'. Resume it with --backend {session.provider}."
            )
    else:
        session, persona, persona_folder = runtime.start(args.persona_id, friction_mode=args.friction_mode)

    print(f"Synthetic User: {session.persona_name} ({session.persona_id})")
    print(session.synthetic_only_disclaimer)
    print(f"Session: {session.session_id}")

    if args.messages:
        for message in args.messages:
            print(_console_safe(f"\nYou: {message}"))
            print(_console_safe(f"{session.persona_name}: {runtime.send(session, persona, persona_folder, message)}"))
        runtime.close(session)
        print(f"\nTranscript: {args.session_dir / session.session_id / 'transcript.md'}")
        return 0

    print("Commands: /help, /reset, /quit")
    while True:
        try:
            message = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            runtime.close(session)
            break
        if not message:
            continue
        if message == "/quit":
            runtime.close(session)
            break
        if message == "/reset":
            runtime.reset(session)
            print("Conversation history cleared.")
            continue
        if message == "/help":
            print("/reset clears this session's turns; /quit saves and closes the session.")
            continue
        try:
            reply = runtime.send(session, persona, persona_folder, message)
        except (OpenAIProviderError, ValueError) as exc:
            print(f"Error: {exc}")
            continue
        print(_console_safe(f"{session.persona_name}: {reply}"))

    print(f"Transcript: {args.session_dir / session.session_id / 'transcript.md'}")
    return 0


def _cmd_run_facilitated_interview(args: argparse.Namespace) -> int:
    from ai_validation_swarm.facilitator.runtime import FacilitatedInterviewRuntime

    progress_writer = _make_progress_writer(getattr(args, "debug_progress", False))
    facilitator_provider = _build_facilitator_provider(
        args.backend,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        debug_writer=progress_writer,
    )
    persona_provider = _build_conversation_provider(
        args.backend,
        model=args.model,
        reasoning_effort=args.reasoning_effort,
        debug_writer=progress_writer,
    )

    def observer(role: str, message: str) -> None:
        label = "Facilitator" if role == "facilitator" else args.persona_id
        print(_console_safe(f"\n{label}: {message}"))

    soft_limit, hard_limit = _resolve_interview_turn_policy(args, default_soft=10, default_hard=12)
    runtime = FacilitatedInterviewRuntime(
        data_dir=args.data_dir,
        session_dir=args.session_dir,
        facilitator_provider=facilitator_provider,
        persona_provider=persona_provider,
        observer=observer,
        progress_writer=progress_writer,
        approved_learning_rules_path=args.approved_learning_rules_path,
    )
    print("Synthetic-user interview for AI pre-validation only; not human market evidence.")
    output = runtime.run(
        persona_id=args.persona_id,
        research_goal=args.research_goal,
        interview_mode=args.interview_mode,
        hypothesis=args.hypothesis,
        product_context=args.product_context,
        concept_protocol=args.concept_protocol,
        concept_label=args.concept_label,
        stimulus_type=args.stimulus_type,
        stimulus_artifact=args.stimulus_artifact,
        prototype_task=args.prototype_task,
        output_language=args.language,
        max_turns=hard_limit,
        soft_turn_limit=soft_limit,
        hard_turn_limit=hard_limit,
        friction_mode=args.friction_mode,
    )
    print(f"\nInterview completed: {output}")
    print(f"Transcript: {output / 'transcript.md'}")
    print(f"Insights: {output / 'insights.md'}")
    print(f"Persona driver trace: {output / 'persona_driver_trace.md'}")
    return 0


def _print_observer_state(session) -> None:
    print(_console_safe(
        f"\nStatus: {session.status} | Exchanges: {len(session.exchanges)} | "
        f"Soft/Hard: {session.soft_turn_limit}/{session.hard_turn_limit}"
    ))
    if session.last_error:
        print(_console_safe(f"Failed operation: {session.failed_operation}\nError: {session.last_error}"))
    coverage = getattr(session, "coverage_status", {}) or {}
    if coverage:
        missing = ", ".join(coverage.get("missing", [])) or "(none)"
        print(_console_safe(f"Coverage complete: {coverage.get('coverage_complete', False)} | Missing: {missing}"))
    pending = session.pending_facilitator_decision
    if pending:
        print(_console_safe(f"Phase: {pending.get('interview_phase', '')}"))
        print(_console_safe(f"Strategy: {pending.get('probing_strategy', '')}"))
        print(_console_safe(f"Rationale: {pending.get('decision_rationale', '')}"))
        if pending.get("message_to_persona"):
            print(_console_safe(f"Proposed question: {pending['message_to_persona']}"))
        hypotheses = pending.get("root_cause_hypotheses", [])
        if hypotheses:
            print("Root-cause hypotheses:")
            for item in hypotheses:
                if isinstance(item, dict):
                    print(_console_safe(f"- [{item.get('confidence', '')}] {item.get('hypothesis', '')}"))
                else:
                    print(_console_safe(f"- {str(item)}"))
        evidence = pending.get("evidence_updates", [])
        if evidence:
            print("Evidence updates:")
            for item in evidence:
                if isinstance(item, dict):
                    print(_console_safe(f"- {item.get('evidence_type', '')}: {item.get('claim', '')}"))
                else:
                    print(_console_safe(f"- {str(item)}"))


def _apply_observer_action(runtime, interview_id: str, action: str):
    normalized = action.strip()
    if normalized in {"", "continue"}:
        return runtime.continue_interview(interview_id)
    if normalized == "pause":
        return runtime.pause(interview_id)
    if normalized == "retry":
        return runtime.retry(interview_id)
    if normalized == "stop":
        return runtime.finalize(interview_id, stop_reason="observer_stop")
    if normalized == "reevaluate":
        return runtime.reevaluate_quality(interview_id)
    if normalized == "resynthesize":
        return runtime.resynthesize(interview_id)
    if normalized.startswith("steer:"):
        return runtime.steer(interview_id, normalized.split(":", 1)[1])
    if normalized.startswith("deepen:"):
        topic = normalized.split(":", 1)[1].strip()
        return runtime.steer(interview_id, f"Deepen the evidence around this topic without leading the participant: {topic}")
    if normalized.startswith("ask:"):
        return runtime.suggest_question(interview_id, normalized.split(":", 1)[1])
    if normalized.startswith("ask-exact:"):
        return runtime.ask_direct(interview_id, normalized.split(":", 1)[1])
    raise ValueError("Unknown action. Use continue, pause, retry, stop, reevaluate, resynthesize, steer:..., deepen:..., ask:..., or ask-exact:...")


def _cmd_observe_facilitated_interview(args: argparse.Namespace) -> int:
    from ai_validation_swarm.observer.runtime import ObserverControlledInterviewRuntime

    if bool(args.interview_id) == bool(args.persona_id):
        raise ValueError("Provide either --persona-id to start or --resume to continue an observed interview.")
    if not args.interview_id and not args.research_goal:
        raise ValueError("--research-goal is required when starting an observed interview.")

    progress_writer = _make_progress_writer(getattr(args, "debug_progress", False))
    facilitator_provider = _build_facilitator_provider(
        args.backend, model=args.model, reasoning_effort=args.reasoning_effort, debug_writer=progress_writer
    )
    persona_provider = _build_conversation_provider(
        args.backend, model=args.model, reasoning_effort=args.reasoning_effort, debug_writer=progress_writer
    )
    quality_provider = _build_facilitator_provider(
        args.backend, model=args.model, reasoning_effort=args.reasoning_effort, debug_writer=progress_writer
    )
    runtime = ObserverControlledInterviewRuntime(
        data_dir=args.data_dir,
        session_dir=args.session_dir,
        facilitator_provider=facilitator_provider,
        persona_provider=persona_provider,
        quality_provider=quality_provider,
        progress_writer=progress_writer,
        approved_learning_rules_path=args.approved_learning_rules_path,
    )
    soft_limit, hard_limit = _resolve_interview_turn_policy(args, default_soft=12, default_hard=16)
    if args.interview_id:
        folder, session = runtime.load(args.interview_id)
    else:
        folder, session = runtime.start(
            persona_id=args.persona_id,
            research_goal=args.research_goal,
            interview_mode=args.interview_mode,
            hypothesis=args.hypothesis,
            product_context=args.product_context,
            concept_protocol=args.concept_protocol,
            concept_label=args.concept_label,
            stimulus_type=args.stimulus_type,
            stimulus_artifact=args.stimulus_artifact,
            prototype_task=args.prototype_task,
            output_language=args.language,
            max_turns=hard_limit,
            soft_turn_limit=soft_limit,
            hard_turn_limit=hard_limit,
            friction_mode=args.friction_mode,
        )
    interview_id = session.interview_id
    print("Synthetic-user interview for AI pre-validation only; not human market evidence.")
    print(f"Observed interview: {interview_id}")
    _print_observer_state(session)

    if args.actions:
        for action in args.actions:
            previous_count = len(session.exchanges)
            session = _apply_observer_action(runtime, interview_id, action)
            for exchange in session.exchanges[previous_count:]:
                print(_console_safe(f"\nQuestion: {exchange.facilitator_question}"))
                print(_console_safe(f"{session.persona_name}: {exchange.persona_response}"))
            _print_observer_state(session)
            if session.status == "completed":
                break
        print(f"\nSession folder: {folder}")
        return 0 if session.status != "failed" else 1

    print("Commands: Enter or /continue, /steer TEXT, /deepen TOPIC, /ask QUESTION, /ask-exact QUESTION, /pause, /retry, /reevaluate, /resynthesize, /status, /stop, /quit")
    while session.status != "completed":
        try:
            raw = input("\nObserver: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            session = runtime.pause(interview_id)
            break
        if raw == "/quit":
            session = runtime.pause(interview_id)
            break
        if raw == "/status":
            _print_observer_state(session)
            continue
        command = "continue" if raw in {"", "/continue"} else raw.removeprefix("/")
        if command.startswith("steer "):
            command = "steer:" + command[6:]
        elif command.startswith("deepen "):
            command = "deepen:" + command[7:]
        elif command.startswith("ask "):
            command = "ask:" + command[4:]
        elif command.startswith("ask-exact "):
            command = "ask-exact:" + command[10:]
        previous_count = len(session.exchanges)
        try:
            session = _apply_observer_action(runtime, interview_id, command)
        except ValueError as exc:
            print(f"Error: {exc}")
            continue
        for exchange in session.exchanges[previous_count:]:
            print(_console_safe(f"\nQuestion: {exchange.facilitator_question}"))
            print(_console_safe(f"{session.persona_name}: {exchange.persona_response}"))
        _print_observer_state(session)

    print(f"\nSession folder: {folder}")
    if session.status == "completed":
        print(f"Insights: {folder / 'insights.md'}")
        print(f"Persona driver trace: {folder / 'persona_driver_trace.md'}")
        print(f"Facilitator audit feedback: {folder / 'facilitator_audit_feedback.md'}")
    print(f"Quality: {folder / 'quality_evaluation.md'}")
    return 0 if session.status != "failed" else 1


def _cmd_run_concept_panel(args: argparse.Namespace) -> int:
    from ai_validation_swarm.facilitator.concept_panel import run_concept_panel

    progress_writer = _make_progress_writer(getattr(args, "debug_progress", False))
    facilitator_provider = _build_facilitator_provider(
        args.backend, model=args.model, reasoning_effort=args.reasoning_effort, debug_writer=progress_writer
    )
    persona_provider = _build_conversation_provider(
        args.backend, model=args.model, reasoning_effort=args.reasoning_effort, debug_writer=progress_writer
    )
    quality_provider = _build_facilitator_provider(
        args.backend, model=args.model, reasoning_effort=args.reasoning_effort, debug_writer=progress_writer
    )
    soft_limit, hard_limit = _resolve_interview_turn_policy(args, default_soft=12, default_hard=16)
    print("Running synthetic concept panel in Cantonese; not human market evidence.")
    output = run_concept_panel(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        facilitator_provider=facilitator_provider,
        persona_provider=persona_provider,
        quality_provider=quality_provider,
        research_goal=args.research_goal,
        product_context=args.product_context,
        topic_label=args.topic_label,
        concept_protocol=args.concept_protocol,
        concept_label=args.concept_label,
        output_language=args.language,
        core_assumption_count=args.core_assumption_count,
        persona_ids=args.persona_ids,
        max_turns=hard_limit,
        soft_turn_limit=soft_limit,
        hard_turn_limit=hard_limit,
        friction_mode=args.friction_mode,
        progress_writer=progress_writer,
        approved_learning_rules_path=args.approved_learning_rules_path,
    )
    print(f"Panel completed: {output}")
    print(f"Summary: {output / 'panel_summary.md'}")
    print(f"Facilitator audit digest: {output / 'facilitator_audit_panel.md'}")
    return 0


def _cmd_run_followup_copilot_panel(args: argparse.Namespace) -> int:
    from ai_validation_swarm.facilitator.concept_panel import run_ai_followup_copilot_panel

    progress_writer = _make_progress_writer(getattr(args, "debug_progress", False))
    facilitator_provider = _build_facilitator_provider(
        args.backend, model=args.model, reasoning_effort=args.reasoning_effort, debug_writer=progress_writer
    )
    persona_provider = _build_conversation_provider(
        args.backend, model=args.model, reasoning_effort=args.reasoning_effort, debug_writer=progress_writer
    )
    quality_provider = _build_facilitator_provider(
        args.backend, model=args.model, reasoning_effort=args.reasoning_effort, debug_writer=progress_writer
    )
    soft_limit, hard_limit = _resolve_interview_turn_policy(args, default_soft=12, default_hard=16)
    print("Running AI Follow-up Copilot synthetic panel in Cantonese; not human market evidence.")
    output = run_ai_followup_copilot_panel(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        facilitator_provider=facilitator_provider,
        persona_provider=persona_provider,
        quality_provider=quality_provider,
        max_turns=hard_limit,
        soft_turn_limit=soft_limit,
        hard_turn_limit=hard_limit,
        friction_mode=args.friction_mode,
        progress_writer=progress_writer,
        approved_learning_rules_path=args.approved_learning_rules_path,
    )
    print(f"Panel completed: {output}")
    print(f"Summary: {output / 'panel_summary.md'}")
    print(f"Facilitator audit digest: {output / 'facilitator_audit_panel.md'}")
    return 0


def _cmd_summarize_concept_panel(args: argparse.Namespace) -> int:
    from ai_validation_swarm.facilitator.concept_panel import summarize_existing_concept_panel

    output = summarize_existing_concept_panel(
        run_dir=args.run_dir,
        persona_ids=args.persona_ids,
        topic_label=args.topic_label,
        output_language=args.language,
        core_assumption_count=args.core_assumption_count,
    )
    print(f"Panel summary rebuilt for {', '.join(args.persona_ids)}: {output / 'panel_summary.md'}")
    print(f"Facilitator audit digest rebuilt: {output / 'facilitator_audit_panel.md'}")
    return 0


def _cmd_summarize_followup_copilot_panel(args: argparse.Namespace) -> int:
    from ai_validation_swarm.facilitator.concept_panel import summarize_existing_concept_panel

    output = summarize_existing_concept_panel(run_dir=args.run_dir, persona_ids=args.persona_ids)
    print(f"Panel summary rebuilt for {', '.join(args.persona_ids)}: {output / 'panel_summary.md'}")
    print(f"Facilitator audit digest rebuilt: {output / 'facilitator_audit_panel.md'}")
    return 0


def _cmd_aggregate_facilitator_audit_runs(args: argparse.Namespace) -> int:
    from ai_validation_swarm.facilitator.concept_panel import aggregate_facilitator_audit_runs

    output = aggregate_facilitator_audit_runs(
        run_dirs=args.run_dirs,
        output_dir=args.output_dir,
        label=args.label,
    )
    print(f"Facilitator audit learning report: {output / 'facilitator_audit_learning_report.md'}")
    return 0


def _cmd_promote_facilitator_learning_rules(args: argparse.Namespace) -> int:
    from ai_validation_swarm.facilitator.learning import promote_facilitator_learning_rules

    registry = promote_facilitator_learning_rules(
        report_path=args.report_path,
        registry_path=args.registry_path,
        rule_ids=args.rule_ids,
        approved_by=args.approved_by,
        approval_note=args.note,
    )
    print(f"Promoted {len(args.rule_ids)} facilitator learning rules to {args.registry_path}")
    print(f"Registry markdown: {args.registry_path.with_suffix('.md')}")
    print(f"Approved rules now active: {len(registry.get('approved_rules', []))}")
    return 0


def _cmd_disable_facilitator_learning_rules(args: argparse.Namespace) -> int:
    from ai_validation_swarm.facilitator.learning import disable_facilitator_learning_rules

    registry = disable_facilitator_learning_rules(
        registry_path=args.registry_path,
        rule_ids=args.rule_ids,
        disabled_by=args.disabled_by,
        disable_note=args.note,
    )
    active_count = sum(1 for item in registry.get("approved_rules", []) if item.get("status") == "approved")
    disabled_count = sum(1 for item in registry.get("approved_rules", []) if item.get("status") == "disabled")
    print(f"Disabled {len(args.rule_ids)} facilitator learning rules in {args.registry_path}")
    print(f"Registry markdown: {args.registry_path.with_suffix('.md')}")
    print(f"Active rules remaining: {active_count}")
    print(f"Disabled rules total: {disabled_count}")
    return 0


def _cmd_compare_facilitator_learning_effects(args: argparse.Namespace) -> int:
    from ai_validation_swarm.facilitator.concept_panel import compare_facilitator_learning_effects

    output = compare_facilitator_learning_effects(
        baseline_run_dirs=args.baseline_run_dirs,
        candidate_run_dirs=args.candidate_run_dirs,
        output_dir=args.output_dir,
        label=args.label,
    )
    print(f"Facilitator learning effect report: {output / 'facilitator_learning_effect_report.md'}")
    return 0


def _cmd_bootstrap_saas_workspace(args: argparse.Namespace) -> int:
    from ai_validation_swarm.saas.runtime import SaasRuntime

    settings: dict[str, object] = {}
    if args.retention_days is not None:
        settings["artifact_retention_days"] = args.retention_days
    if args.daily_runs is not None:
        settings["daily_runs"] = args.daily_runs
    if args.max_concurrent_jobs is not None:
        settings["max_concurrent_jobs"] = args.max_concurrent_jobs

    runtime = SaasRuntime(args.runtime_root)
    result = runtime.bootstrap_workspace(
        workspace_id=args.workspace_id,
        slug=args.slug,
        display_name=args.display_name,
        owner_user_id=args.owner_user_id,
        api_token=args.api_token,
        plan_tier=args.plan_tier,
        billing_status=args.billing_status,
        region_code=args.region_code,
        data_residency_region=args.data_residency_region,
        settings=settings,
    )
    print(f"Workspace bootstrapped: {result['workspace_root']}")
    print(f"Workspace ID: {args.workspace_id}")
    print(f"Plan tier: {args.plan_tier}")
    print(f"Billing status: {args.billing_status}")
    return 0


def _cmd_serve_saas_api(args: argparse.Namespace) -> int:
    from ai_validation_swarm.saas.api import serve_saas_api

    serve_saas_api(args.runtime_root, host=args.host, port=args.port)
    return 0


def _cmd_run_saas_worker(args: argparse.Namespace) -> int:
    from ai_validation_swarm.saas.runtime import SaasRuntime

    runtime = SaasRuntime(args.runtime_root)
    processed = runtime.run_worker_loop(poll_seconds=args.poll_seconds, stop_after_one=bool(args.once))
    print(f"Processed {processed} SaaS validation jobs.")
    return 0


def _cmd_purge_saas_expired_artifacts(args: argparse.Namespace) -> int:
    from ai_validation_swarm.saas.runtime import SaasRuntime

    runtime = SaasRuntime(args.runtime_root)
    purged = runtime.purge_expired_run_artifacts()
    print(f"Purged {len(purged)} expired run artifact sets.")
    for job_id in purged:
        print(job_id)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    handlers = {
        "generate-personas": _cmd_generate,
        "list-personas": _cmd_list,
        "sample-panel": _cmd_sample,
        "validate-personas": _cmd_validate,
        "migrate-personas-v2": _cmd_migrate_personas_v2,
        "validate-personas-v2": _cmd_validate_personas_v2,
        "generate-v3-persona": _cmd_generate_v3_persona,
        "run-distinctiveness-check": _cmd_run_distinctiveness_check,
        "validate-personas-v3": _cmd_validate_personas_v3,
        "generate-v3-1-persona": _cmd_generate_v3_1_persona,
        "run-distinctiveness-check-v3-1": _cmd_run_distinctiveness_check_v3_1,
        "validate-personas-v3-1": _cmd_validate_personas_v3_1,
        "generate-v3-1-1-persona": _cmd_generate_v3_1_1_persona,
        "generate-v3-1-2-persona": _cmd_generate_v3_1_2_persona,
        "generate-v3-2-persona": _cmd_generate_v3_2_persona,
        "generate-v3-3-persona": _cmd_generate_v3_3_persona,
        "generate-v5-persona": _cmd_generate_v5_persona,
        "generate-v5-panel": _cmd_generate_v5_panel,
        "generate-persona-to-target": _cmd_generate_persona_to_target,
        "run-distinctiveness-check-v3-1-1": _cmd_run_distinctiveness_check_v3_1_1,
        "run-distinctiveness-check-v3-1-2": _cmd_run_distinctiveness_check_v3_1_2,
        "validate-personas-v3-1-1": _cmd_validate_personas_v3_1_1,
        "validate-personas-v3-1-2": _cmd_validate_personas_v3_1_2,
        "validate-personas-v3-2": _cmd_validate_personas_v3_2,
        "validate-personas-v3-3": _cmd_validate_personas_v3_3,
        "validate-personas-v5": _cmd_validate_personas_v5,
        "summarize-personas": _cmd_summarize_personas,
        "inspect-openai-auth": _cmd_inspect_openai_auth,
        "probe-codex-auth": _cmd_probe_codex_auth,
        "enrich-personas": _cmd_enrich_personas,
        "validate-brief": _cmd_validate_brief,
        "run-validation": _cmd_run,
        "audit-report": _cmd_audit,
        "export-report": _cmd_export,
        "run-evaluation": _cmd_run_evaluation,
        "bootstrap-saas-workspace": _cmd_bootstrap_saas_workspace,
        "serve-saas-api": _cmd_serve_saas_api,
        "run-saas-worker": _cmd_run_saas_worker,
        "purge-saas-expired-artifacts": _cmd_purge_saas_expired_artifacts,
        "compare-evaluations": _cmd_compare_evaluations,
        "compare-persona-quality": _cmd_compare_persona_quality,
        "chat-with-persona": _cmd_chat_with_persona,
        "run-facilitated-interview": _cmd_run_facilitated_interview,
        "observe-facilitated-interview": _cmd_observe_facilitated_interview,
        "run-concept-panel": _cmd_run_concept_panel,
        "run-followup-copilot-panel": _cmd_run_followup_copilot_panel,
        "summarize-concept-panel": _cmd_summarize_concept_panel,
        "summarize-followup-copilot-panel": _cmd_summarize_followup_copilot_panel,
        "aggregate-facilitator-audit-runs": _cmd_aggregate_facilitator_audit_runs,
        "promote-facilitator-learning-rules": _cmd_promote_facilitator_learning_rules,
        "disable-facilitator-learning-rules": _cmd_disable_facilitator_learning_rules,
        "compare-facilitator-learning-effects": _cmd_compare_facilitator_learning_effects,
    }
    try:
        return handlers[args.command](args)
    except InputValidationError as exc:
        print(str(exc))
        return 1
    except OpenAIProviderError as exc:
        print(f"Error: {exc}")
        return 1
    except ValueError as exc:
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
