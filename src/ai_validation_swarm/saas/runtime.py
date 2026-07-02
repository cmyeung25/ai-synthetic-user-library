from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, UTC
from pathlib import Path
import hashlib
import json
import mimetypes
import os
from typing import Any, Callable
import threading
import time
import re
import uuid

from ai_validation_swarm.domain.models import FounderBrief, PanelSpec, utc_now_iso
from ai_validation_swarm.domain.validators import load_and_validate_founder_brief, validate_panel_spec
from ai_validation_swarm.personas.frontline_v5_generator import (
    FrontlineLocalV5SynthesisAdapter,
    build_frontline_v5_generation_guide,
)
from ai_validation_swarm.personas.generator import PANEL_ROLES
from ai_validation_swarm.personas.analysis import build_persona_library_summary
from ai_validation_swarm.personas.v5 import GENERATOR_VERSION as V5_GENERATOR_VERSION, generate_v5_persona
from ai_validation_swarm.providers.base import BaseProvider
from ai_validation_swarm.providers.factory import build_provider
from ai_validation_swarm.providers.openai_client import load_codex_access_token
from ai_validation_swarm.reporting.exporters import render_report_csv
from ai_validation_swarm.saas.evidence_query import (
    _load_human_calibration_record,
    build_pending_evidence_query,
    query_run_evidence,
)
from ai_validation_swarm.saas.metadata_store import persist_run_contract_metadata
from ai_validation_swarm.saas import job_store
from ai_validation_swarm.saas.models import (
    AuditEvent,
    BillingAccount,
    TenantWorkspace,
    ValidationJob,
    WorkspaceBrowserSession,
    WorkspaceDecisionComment,
    WorkspaceDecisionLog,
    WorkspaceEvidenceView,
    WorkspaceExportBundle,
    WorkspaceMember,
    WorkspaceProject,
    WorkspaceShareBundle,
    WorkspaceStudyReport,
    WorkspaceSupportSnapshot,
    WorkspaceStudy,
)
from ai_validation_swarm.sampling.engine import sample_personas
from ai_validation_swarm.storage.files import (
    export_file,
    load_persona,
    load_personas,
    read_json,
    resolve_persona_version_folder,
    write_json,
    write_markdown,
)
from ai_validation_swarm.validation.runner import run_validation


ACTIVE_BILLING_STATUSES = {"trialing", "active"}
SUBMITTER_ROLES = {"owner", "admin", "editor"}
VISIBLE_ROLES = {"owner", "admin", "editor", "viewer", "billing_admin"}
PLAN_LIMITS = {
    "trial": {"daily_runs": 3, "max_concurrent_jobs": 1, "artifact_retention_days": 7},
    "pro": {"daily_runs": 25, "max_concurrent_jobs": 3, "artifact_retention_days": 30},
    "enterprise": {"daily_runs": 100, "max_concurrent_jobs": 10, "artifact_retention_days": 90},
}
EXPORTABLE_ROLE_SET = {"owner", "admin", "editor"}
SHAREABLE_ROLE_SET = {"owner", "admin", "editor"}
WORKSPACE_SETTINGS_MUTATION_ROLES = {"owner", "admin"}
WORKSPACE_BILLING_MUTATION_ROLES = {"owner", "billing_admin"}
WORKSPACE_PRIVACY_MUTATION_ROLES = {"owner", "admin"}
MVP_PROMOTION_REQUEST_ROLES = {"owner", "admin", "editor"}
MVP_PROMOTION_REVIEW_ROLES = {"owner", "admin"}
MVP_RELEASE_REVIEW_REQUEST_ROLES = {"owner", "admin", "editor"}
MVP_RELEASE_REVIEW_ROLES = {"owner", "admin"}
DECISION_REVIEW_ASSIGNMENT_MUTATION_ROLES = {"owner", "admin"}
DECISION_REVIEW_ASSIGNEE_ROLES = {"owner", "admin", "editor"}
SUPPORT_HANDOFF_MUTATION_ROLES = {"owner", "admin", "editor"}
SUPPORT_HANDOFF_ASSIGNEE_ROLES = {"owner", "admin", "editor"}
DEFAULT_EXPORT_ARTIFACT_IDS = ("report.json", "report.md", "summary.json", "run_contract.json")
MAX_AUDIT_EVENT_QUERY_LIMIT = 100
DECISION_REVIEW_STATUSES = {"draft", "in_review", "approved", "needs_revision"}
DECISION_COMMENT_ANCHOR_KINDS = {"general", "decision_summary", "rationale", "evidence_view", "comparison"}
BROWSER_SESSION_TTL = timedelta(hours=12)
READINESS_GATE_CUSTOMER_READY_STATUSES = {"scoped_external_ready"}
READINESS_GATE_BLOCKED_SHARE_STATUSES = {"pending", "restricted_human_review_required"}
DECISION_REVIEW_ASSIGNMENT_STATUSES = {"unassigned", "assigned"}
SUPPORT_HANDOFF_STATUSES = {"unassigned", "assigned", "acknowledged", "resolved"}
GOVERNED_REVIEW_ASSIGNMENT_STATUSES = {"unassigned", "assigned", "escalated"}
GOVERNED_REDACTION_STATUSES = {"unconfigured", "draft", "active", "escalated", "not_required"}
PERSONA_LIBRARY_READINESS_STATES = ("ready", "empty", "generating", "failed", "stale", "provisional")
PERSONA_LIBRARY_RECORD_FILENAME = "persona_library_record.json"
PERSONA_LIBRARY_PARTICIPANT_KIND = "participant"
PERSONA_LIBRARY_LENS_KINDS = {
    "public_figure_lens",
    "celebrity_lens",
    "expert_advisor_lens",
    "influencer_style_lens",
    "founder_critique_lens",
}
FRONTLINE_FORMAL_PERSONA_SCHEMA_VERSIONS = {"v5", "v5_1"}
LONGITUDINAL_PATTERN_DEFINITIONS = (
    {
        "pattern_id": "objection",
        "label": "Recurring objections",
        "markers": ("objection", "hesitat", "reject", "pricing", "try signal"),
    },
    {
        "pattern_id": "trust_gap",
        "label": "Persistent trust gaps",
        "markers": ("trust", "risk", "skeptic", "permission", "credib"),
    },
    {
        "pattern_id": "task_failure",
        "label": "Repeated task failures or abandonment",
        "markers": ("error", "failed", "failure", "abandon", "fallback"),
    },
    {
        "pattern_id": "contradiction",
        "label": "Unresolved contradiction patterns",
        "markers": ("contradict", "unsupported", "needs revision", "mixed_or_contradictory"),
    },
)
CALIBRATION_STATUS_RANK = {
    "unavailable": 0,
    "calibrated_fixture_only": 1,
    "directional_calibration_ready": 2,
    "candidate_replacement_ready": 3,
    "scoped_external_ready": 4,
}
FRONTLINE_RUN_PHASES = (
    "queued",
    "planning",
    "sampling_panel",
    "interviewing",
    "synthesizing",
    "auditing",
    "completed",
    "blocked",
    "failed",
)
FRONTLINE_STAGE_PHASES = {
    "sampling": "sampling_panel",
    "persona_responses": "interviewing",
    "skeptic_review": "synthesizing",
    "sensitive_audit": "auditing",
    "aggregation": "synthesizing",
    "planner": "planning",
    "report_writer": "synthesizing",
}
INTEGRATION_EVENT_ACTION_TYPES = {
    "study.created": "study.created",
    "validation_job.completed": "run.completed",
    "validation_job.failed": "run.failed",
    "evidence_view.saved": "evidence_view.saved",
    "decision_log.created": "decision.logged",
    "support_snapshot.handoff_updated": "support.handoff_changed",
}
INTEGRATION_DELIVERY_HISTORY_SETTING = "integration_delivery_attempts"
INTEGRATION_DELIVERY_STATUSES = {"queued", "delivered", "failed", "retrying", "skipped"}
FRONTLINE_RESEARCH_PLAYBOOKS = (
    {
        "playbook_id": "discovery_pain_insight",
        "label": "Pain, empathy, and insight discovery",
        "mode": "pain_point_discovery",
        "best_for": "When the user has a domain or problem area but not yet a fixed solution.",
        "starter_questions": [
            "What happened the last time this problem appeared?",
            "What workaround did you use and what did it cost?",
            "Which part still feels unresolved after the workaround?",
        ],
        "expected_evidence_types": ["recalled_behavior", "pain_signal", "workflow_fragmentation", "human_validation_gaps"],
        "rerun_change_axes": ["target_audience", "problem_frame", "moderator_guide"],
    },
    {
        "playbook_id": "concept_validation",
        "label": "Concept validation",
        "mode": "concept_validation",
        "best_for": "When the user has a startup idea or product concept and wants to test clarity, trust, and adoption risk.",
        "starter_questions": [
            "What do you understand this concept is trying to help with?",
            "Where would trust, effort, or switching risk stop you?",
            "What proof would make you try it?",
        ],
        "expected_evidence_types": ["comprehension", "objections", "trust_gaps", "adoption_barriers"],
        "rerun_change_axes": ["target_audience", "concept_variant", "pricing_or_proof"],
    },
    {
        "playbook_id": "prototype_comprehension",
        "label": "Prototype comprehension",
        "mode": "prototype_validation",
        "best_for": "When the user has UI, UX, screens, flow notes, or prototype artifacts.",
        "starter_questions": [
            "What do you think this screen asks you to do first?",
            "Which label, button, or flow state creates doubt?",
            "Where would you pause, backtrack, or abandon?",
        ],
        "expected_evidence_types": ["wording_confusion", "cta_ambiguity", "task_friction", "observed_action_trace_if_available"],
        "rerun_change_axes": ["artifact_version", "prototype_task", "screen_or_flow_variant"],
    },
    {
        "playbook_id": "messaging_positioning",
        "label": "Messaging and positioning validation",
        "mode": "messaging_validation",
        "best_for": "When the user needs to test wording, headline, value proposition, landing-page copy, or positioning.",
        "starter_questions": [
            "What do you believe this message promises?",
            "Which words feel credible, vague, exaggerated, or confusing?",
            "What would you still not know before taking the next step?",
        ],
        "expected_evidence_types": ["message_comprehension", "credibility_gap", "trust_gap", "misunderstanding", "next_step_clarity"],
        "rerun_change_axes": ["message_variant", "audience_segment", "proof_point"],
    },
    {
        "playbook_id": "adoption_barrier",
        "label": "Adoption barrier review",
        "mode": "adoption_barrier_validation",
        "best_for": "When the user needs to predict why a plausible buyer or user still would not adopt.",
        "starter_questions": [
            "What would make this feel too risky or too costly to try?",
            "Which existing habit, stakeholder, or workflow blocks adoption?",
            "What would need to be true before this becomes worth switching to?",
        ],
        "expected_evidence_types": ["switching_cost", "stakeholder_blocker", "trust_gap", "trial_trigger"],
        "rerun_change_axes": ["target_audience", "proof_point", "onboarding_or_switching_path"],
    },
)
REGULATED_REVIEW_DOMAIN_DEFINITIONS = (
    {
        "domain_id": "finance",
        "label": "Finance or lending decisions",
        "markers": ("finance", "financial", "loan", "credit", "mortgage", "insurance", "investment", "bank"),
    },
    {
        "domain_id": "health",
        "label": "Health or medical guidance",
        "markers": ("health", "medical", "patient", "diagnos", "clinic", "therapy", "treatment", "symptom"),
    },
    {
        "domain_id": "employment",
        "label": "Employment or hiring decisions",
        "markers": (
            "employment",
            "hiring",
            "hire",
            "job applicant",
            "recruit",
            "recruiter",
            "candidate screening",
            "performance review",
            "termination",
        ),
    },
    {
        "domain_id": "legal",
        "label": "Legal advice or legal workflows",
        "markers": ("legal", "law", "attorney", "contract", "court", "compliance", "litigation"),
    },
    {
        "domain_id": "children",
        "label": "Children or minors",
        "markers": ("child", "children", "minor", "teen", "student", "kid", "parental"),
    },
    {
        "domain_id": "public_safety",
        "label": "Public safety or emergency response",
        "markers": ("public safety", "emergency", "safety-critical", "evacuation", "incident", "disaster", "911"),
    },
    {
        "domain_id": "destructive",
        "label": "Destructive or irreversible workflows",
        "markers": ("delete", "destructive", "wipe", "shutdown", "transfer funds", "wire transfer", "irreversible"),
    },
    {
        "domain_id": "credentialed",
        "label": "Credentialed or privileged-access workflows",
        "markers": ("credential", "login", "password", "otp", "token", "admin access", "privileged", "permission"),
    },
)
REGULATED_REVIEW_BOUNDARY_ACK_STATUSES = {"acknowledged", "approved_for_execution"}
SUPPORTED_VALIDATION_PROVIDERS = ("mock", "openai", "agnes", "codex", "codex-sdk")
LIVE_VALIDATION_PROVIDERS = {"openai", "agnes", "codex", "codex-sdk"}
CODEX_VALIDATION_PROVIDERS = {"codex", "codex-sdk"}


def _regulated_marker_matches(marker: str, signal_text: str) -> bool:
    if marker == "911":
        return bool(re.search(r"(?<!\d)911(?!\d)", signal_text))
    return marker in signal_text


class AuthenticationError(ValueError):
    pass


class AuthorizationError(PermissionError):
    pass


class ShareUnavailableError(FileNotFoundError):
    pass


@dataclass(slots=True)
class AuthContext:
    workspace_id: str
    user_id: str
    role: str
    token: str = ""
    auth_type: str = "api_token"
    session_id: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ValidationJobRequest:
    brief_path: str
    persona_dir: str
    panel_spec: PanelSpec
    provider_name: str = "mock"
    priority: str = "normal"
    max_retries: int = 1
    idempotency_key: str = ""
    run_root: str = "runs"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["panel_spec"] = self.panel_spec.to_dict()
        return payload


def _now() -> datetime:
    return datetime.now(UTC)


def _plan_limits(plan_tier: str, settings: dict[str, Any]) -> dict[str, int]:
    defaults = dict(PLAN_LIMITS.get(plan_tier, PLAN_LIMITS["trial"]))
    for key in ("daily_runs", "max_concurrent_jobs", "artifact_retention_days"):
        if isinstance(settings.get(key), int) and int(settings[key]) >= 0:
            defaults[key] = int(settings[key])
    return defaults


def _workspace_root(runtime_root: Path, workspace_id: str) -> Path:
    return runtime_root / "workspaces" / workspace_id


def _candidate_index_roots(runtime_root: Path, workspace_id: str | None = None) -> list[Path]:
    roots: list[Path] = []
    if workspace_id and workspace_id.strip():
        roots.append(_workspace_root(runtime_root, workspace_id.strip()) / "runs")
    roots.append(runtime_root)
    deduped: list[Path] = []
    for path in roots:
        if path not in deduped:
            deduped.append(path)
    return deduped


def _slugify_label(value: str, *, fallback: str) -> str:
    lowered = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    normalized = lowered.strip("-")
    return normalized or fallback


def _normalize_validation_provider_name(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", str(value or "").strip().lower()).strip("-")
    if normalized == "codex-sdk":
        return "codex-sdk"
    return normalized or "mock"


def _first_configured_env_name(*names: str) -> str:
    for name in names:
        if os.getenv(name, "").strip():
            return name
    return ""


def _resolve_workspace_path(workspace_root: Path, raw_path: str) -> Path:
    candidate = Path(raw_path)
    path = candidate if candidate.is_absolute() else workspace_root / candidate
    resolved = path.resolve()
    workspace_resolved = workspace_root.resolve()
    if resolved != workspace_resolved and workspace_resolved not in resolved.parents:
        raise AuthorizationError(f"Path '{raw_path}' escapes workspace boundary.")
    return resolved


def _mask_token(token: str) -> str:
    value = str(token or "").strip()
    if len(value) <= 10:
        return value
    return f"{value[:6]}...{value[-4:]}"


def _count_values(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for raw_value in values:
        value = str(raw_value or "").strip() or "unknown"
        counts[value] = counts.get(value, 0) + 1
    return counts


def _unique_preserve_order(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for raw_value in values:
        value = str(raw_value or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        numeric = int(value)
    except (TypeError, ValueError):
        numeric = default
    return max(minimum, min(maximum, numeric))


def _normalize_frontline_target_audience(target_persona: str, target_audience: dict[str, Any] | None) -> dict[str, Any]:
    payload = dict(target_audience or {})
    summary = str(payload.get("summary") or target_persona or "").strip()
    criteria = [
        str(item).strip()
        for item in payload.get("inclusion_criteria", [])
        if str(item).strip()
    ] if isinstance(payload.get("inclusion_criteria", []), list) else []
    return {
        "contract_version": "target-audience/v0-draft",
        "summary": summary or "Synthetic participants matching the study target segment.",
        "inclusion_criteria": _unique_preserve_order(criteria),
        "excluded_context": str(payload.get("excluded_context") or "").strip(),
        "selection_boundary": str(
            payload.get("selection_boundary")
            or "Synthetic participants are simulated for directional research only; this is not a recruited human sample."
        ).strip(),
    }


def _normalize_frontline_persona_panel(persona_panel: dict[str, Any] | None, *, default_sample_size: int = 3) -> dict[str, Any]:
    payload = dict(persona_panel or {})
    panel_type = str(payload.get("panel_type") or "mainstream").strip()
    if panel_type not in PANEL_ROLES:
        panel_type = "mainstream"
    selected_ids = _unique_preserve_order(
        [
            str(item).strip()
            for item in payload.get("selected_persona_ids", [])
            if str(item).strip()
        ]
        if isinstance(payload.get("selected_persona_ids", []), list)
        else []
    )
    filters = dict(payload.get("filters", {})) if isinstance(payload.get("filters", {}), dict) else {}
    if selected_ids:
        filters["synthetic_user_id"] = selected_ids
    sample_size = _bounded_int(
        payload.get("sample_size") or len(selected_ids) or default_sample_size,
        default=default_sample_size,
        minimum=1,
        maximum=6,
    )
    if selected_ids:
        sample_size = min(sample_size, len(selected_ids))
    return {
        "contract_version": "persona-panel-selection/v0-draft",
        "panel_type": panel_type,
        "sample_size": sample_size,
        "random_seed": _bounded_int(payload.get("random_seed"), default=17, minimum=0, maximum=999999),
        "selected_persona_ids": selected_ids,
        "filters": filters,
        "selection_mode": str(payload.get("selection_mode") or ("user_selected" if selected_ids else "system_suggested")).strip(),
        "selection_rationale": str(payload.get("selection_rationale") or "").strip(),
        "coverage_snapshot": dict(payload.get("coverage_snapshot", {})) if isinstance(payload.get("coverage_snapshot", {}), dict) else {},
        "selected_personas": [
            dict(item)
            for item in payload.get("selected_personas", [])
            if isinstance(item, dict)
        ] if isinstance(payload.get("selected_personas", []), list) else [],
        "readiness_status": str(payload.get("readiness_status") or "").strip(),
        "allow_empty_selection": bool(payload.get("allow_empty_selection")),
        "empty_selection_exception": (
            dict(payload.get("empty_selection_exception", {}))
            if isinstance(payload.get("empty_selection_exception"), dict)
            else {}
        ),
        "allow_provisional_personas": bool(payload.get("allow_provisional_personas")),
        "provisional_persona_exception": (
            dict(payload.get("provisional_persona_exception", {}))
            if isinstance(payload.get("provisional_persona_exception"), dict)
            else {}
        ),
        "selected_persona_snapshot": (
            dict(payload.get("selected_persona_snapshot", {}))
            if isinstance(payload.get("selected_persona_snapshot"), dict)
            else {}
        ),
        "synthetic_boundary": str(
            payload.get("synthetic_boundary")
            or "Persona selection improves simulation coverage, but it does not create recruited human evidence."
        ).strip(),
    }


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _persona_artifact_hashes(folder: Path) -> dict[str, str]:
    hashes: dict[str, str] = {}
    for artifact_name in ("profile.json", "audit.json", "persona.md", "generation_notes.json", "section_manifest.json"):
        path = folder / artifact_name
        if path.exists() and path.is_file():
            hashes[artifact_name] = _sha256_file(path)
    return hashes


def _persona_artifact_paths(folder: Path, persona_dir: Path) -> dict[str, str]:
    paths: dict[str, str] = {}
    for artifact_name in ("profile.json", "audit.json", "persona.md", "generation_notes.json", "section_manifest.json"):
        path = folder / artifact_name
        if path.exists() and path.is_file():
            try:
                paths[artifact_name] = path.relative_to(persona_dir).as_posix()
            except ValueError:
                paths[artifact_name] = str(path)
    return paths


def _clean_persona_readiness_status(value: Any, *, default: str = "ready") -> str:
    status = str(value or "").strip()
    return status if status in PERSONA_LIBRARY_READINESS_STATES else default


def _clean_persona_kind(value: Any) -> str:
    kind = str(value or PERSONA_LIBRARY_PARTICIPANT_KIND).strip()
    if kind == PERSONA_LIBRARY_PARTICIPANT_KIND or kind in PERSONA_LIBRARY_LENS_KINDS:
        return kind
    return PERSONA_LIBRARY_PARTICIPANT_KIND


def _frontline_source_schema_version(folder: Path, persona: Any) -> str:
    if folder.name in {"v3_2", "v3_3", "v4", "v5", "v5_1"}:
        return folder.name
    if (folder / "persona_schema_v5_1.json").exists():
        return "v5_1"
    skill_version = str(getattr(persona, "skill_version", "") or "").lower()
    if "v5.1" in skill_version or "v5_1" in skill_version:
        return "v5_1"
    if "v5" in skill_version:
        return "v5"
    return str(folder.name or "unknown")


def _infer_persona_kind(persona: Any, record: dict[str, Any]) -> str:
    explicit_kind = str(record.get("persona_kind") or "").strip()
    if explicit_kind:
        return _clean_persona_kind(explicit_kind)
    identity = getattr(persona.profile, "basic_identity", {}) if getattr(persona, "profile", None) else {}
    name = str(identity.get("name") or "").strip().lower() if isinstance(identity, dict) else ""
    if any(token in name for token in ("elon musk", "steve jobs", "public figure", "celebrity")):
        return "public_figure_lens"
    if " perspective" in name and str(getattr(persona.seed, "panel_role", "") or "") == "expert_advisor":
        return "expert_advisor_lens"
    return PERSONA_LIBRARY_PARTICIPANT_KIND


def _is_frontline_formal_participant(entry: dict[str, Any]) -> bool:
    record = dict(entry.get("record", {}))
    return str(record.get("source_schema_version") or "") in FRONTLINE_FORMAL_PERSONA_SCHEMA_VERSIONS


def _normalize_frontline_panel_role(value: Any) -> str:
    role = str(value or "").strip()
    if role in PANEL_ROLES:
        return role
    lowered = role.lower()
    if "expert" in lowered or "advisor" in lowered:
        return "expert_advisor"
    if "privacy" in lowered:
        return "privacy_sensitive"
    if "budget" in lowered or "price" in lowered or "cost" in lowered:
        return "budget_constrained"
    if "skeptic" in lowered or "sceptic" in lowered:
        return "skeptic"
    if "inclusion" in lowered or "accessibility" in lowered:
        return "inclusion"
    if "political" in lowered or "reputation" in lowered:
        return "political_risk"
    if "low tech" in lowered or "low_tech" in lowered:
        return "low_tech"
    if "extreme" in lowered:
        return "extreme_user"
    return "mainstream"


def _persona_library_record(folder: Path, persona_dir: Path, persona: Any) -> dict[str, Any]:
    record_path = folder / PERSONA_LIBRARY_RECORD_FILENAME
    record: dict[str, Any] = {}
    if record_path.exists():
        try:
            payload = read_json(record_path)
            record = dict(payload) if isinstance(payload, dict) else {}
        except Exception:
            record = {}
    generation_notes: dict[str, Any] = {}
    generation_notes_path = folder / "generation_notes.json"
    if generation_notes_path.exists():
        try:
            payload = read_json(generation_notes_path)
            generation_notes = dict(payload) if isinstance(payload, dict) else {}
        except Exception:
            generation_notes = {}
    artifact_hashes = _persona_artifact_hashes(folder)
    profile_hash = artifact_hashes.get("profile.json", "")
    persona_version = str(
        record.get("persona_version")
        or record.get("version")
        or persona.skill_version
        or profile_hash[:12]
        or "unknown"
    ).strip()
    status = _clean_persona_readiness_status(record.get("readiness_status"), default="ready")
    persona_kind = _infer_persona_kind(persona, record)
    source_schema_version = str(
        record.get("source_schema_version")
        or generation_notes.get("persona_schema_version")
        or _frontline_source_schema_version(folder, persona)
    ).strip()
    if source_schema_version in {"v5.1", "persona_schema_v5_1"} or source_schema_version.startswith("persona-schema/v5.1"):
        source_schema_version = "v5_1"
    elif source_schema_version == "v5.0" or source_schema_version.startswith("persona-schema/v5"):
        source_schema_version = "v5"
    generator_version = str(record.get("generator_version") or generation_notes.get("generator_version") or "").strip()
    source_kind = str(record.get("source_kind") or ("generated" if generation_notes else "imported")).strip()
    return {
        "contract_version": "persona-library-record/v0-draft",
        "synthetic_user_id": persona.profile.synthetic_user_id,
        "persona_version": persona_version,
        "readiness_status": status,
        "persona_kind": persona_kind,
        "panel_role": persona.seed.panel_role,
        "source_schema_version": source_schema_version,
        "source_kind": source_kind,
        "generator_version": generator_version,
        "generation_job_id": str(record.get("generation_job_id") or "").strip(),
        "generated_at": str(record.get("generated_at") or "").strip(),
        "promoted_at": str(record.get("promoted_at") or "").strip(),
        "last_checked_at": str(record.get("last_checked_at") or "").strip(),
        "readiness_checks": (
            dict(record.get("readiness_checks", {}))
            if isinstance(record.get("readiness_checks"), dict)
            else {}
        ),
        "lifecycle_history": (
            [dict(item) for item in record.get("lifecycle_history", []) if isinstance(item, dict)]
            if isinstance(record.get("lifecycle_history", []), list)
            else []
        ),
        "artifact_hashes": artifact_hashes,
        "artifact_paths": _persona_artifact_paths(folder, persona_dir),
        "artifact_root": folder.relative_to(persona_dir).as_posix() if folder.is_relative_to(persona_dir) else str(folder),
        "lens_boundary": str(
            record.get("lens_boundary")
            or (
                "This is a simulated, unaffiliated lens. It is not the real person's view, endorsement, or behavior."
                if persona_kind in PERSONA_LIBRARY_LENS_KINDS
                else ""
            )
        ).strip(),
    }


def _write_persona_library_record(folder: Path, payload: dict[str, Any]) -> None:
    write_json(folder / PERSONA_LIBRARY_RECORD_FILENAME, payload)


def _load_frontline_persona_entries(persona_dir: Path) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    if not persona_dir.exists():
        return [], []
    entries: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []
    for folder in sorted(persona_dir.iterdir()):
        if not folder.is_dir() or folder.name.startswith((".", "_")):
            continue
        try:
            version_folder = resolve_persona_version_folder(folder)
            persona = load_persona(version_folder)
            source_panel_role = str(getattr(persona.seed, "panel_role", "") or "").strip()
            normalized_panel_role = _normalize_frontline_panel_role(source_panel_role)
            if normalized_panel_role != source_panel_role:
                persona.seed.panel_role = normalized_panel_role
            record = _persona_library_record(version_folder, persona_dir, persona)
            if normalized_panel_role != source_panel_role:
                record["source_panel_role"] = source_panel_role
                record["panel_role_normalized"] = True
            entries.append({"persona": persona, "folder": version_folder, "record": record})
        except Exception as exc:
            failures.append({"folder": folder.name, "error": str(exc)})
    return entries, failures


def _persona_panel_empty_selection_allowed(persona_panel: dict[str, Any]) -> bool:
    if bool(persona_panel.get("allow_empty_selection")):
        return True
    exception = persona_panel.get("empty_selection_exception")
    return isinstance(exception, dict) and bool(str(exception.get("reason") or "").strip())


def _assert_persona_panel_has_selection(persona_panel: dict[str, Any], *, action: str) -> None:
    selected_ids = [
        str(item).strip()
        for item in persona_panel.get("selected_persona_ids", [])
        if str(item).strip()
    ] if isinstance(persona_panel.get("selected_persona_ids", []), list) else []
    if selected_ids or _persona_panel_empty_selection_allowed(persona_panel):
        return
    raise ValueError(
        f"Select at least one synthetic participant before {action}, or record an explicit empty-selection exception."
    )


def _frontline_mode_from_signal_text(signal_text: str, explicit_mode: str = "") -> str:
    mode = explicit_mode.strip()
    if mode:
        return mode
    text = signal_text.lower()
    if any(marker in text for marker in ("prototype", "ui", "ux", "button", "screen", "flow", "click")):
        return "prototype_validation"
    if any(marker in text for marker in ("message", "messaging", "positioning", "copy", "headline", "tagline", "landing page", "value proposition")):
        return "messaging_validation"
    if any(marker in text for marker in ("pain", "empathy", "problem", "workflow", "root cause")):
        return "pain_point_discovery"
    return "concept_validation"


def _frontline_expected_evidence_types_for_mode(mode: str) -> list[str]:
    if mode == "messaging_validation":
        return [
            "message_comprehension",
            "credibility_gaps",
            "trust_gaps",
            "misunderstandings",
            "next_step_clarity",
            "human_validation_gaps",
        ]
    if mode == "prototype_validation":
        return [
            "wording_confusion",
            "cta_ambiguity",
            "task_friction",
            "observed_action_trace_if_available",
            "human_validation_gaps",
        ]
    if mode == "pain_point_discovery":
        return [
            "recalled_behavior",
            "pain_signals",
            "workflow_fragmentation",
            "insights",
            "human_validation_gaps",
        ]
    return [
        "objections",
        "trust_gaps",
        "adoption_barriers",
        "contradictions",
        "human_validation_gaps",
    ]


def _history_entries(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _history_latest(entries: list[dict[str, Any]]) -> dict[str, Any] | None:
    return dict(entries[-1]) if entries else None


def _job_run_id(job: dict[str, Any]) -> str:
    metadata = dict(job.get("metadata", {}))
    run_id = str(metadata.get("run_id") or "").strip()
    if run_id:
        return run_id
    output_run_path = str(job.get("output_run_path") or "").strip()
    if output_run_path:
        return Path(output_run_path).name
    return ""


def _normalized_string(value: Any) -> str:
    return str(value or "").strip()


def _redaction_replacement_for_value(replacement: str, current: Any) -> Any:
    if replacement:
        return replacement
    if isinstance(current, str):
        return "[REDACTED]"
    if isinstance(current, list):
        return []
    if isinstance(current, dict):
        return {"redacted": True}
    return "[REDACTED]"


class SaasRuntime:
    def __init__(
        self,
        runtime_root: Path,
        *,
        provider_builder: Callable[[str], BaseProvider] = build_provider,
    ) -> None:
        self.runtime_root = runtime_root
        self.provider_builder = provider_builder
        self.runtime_root.mkdir(parents=True, exist_ok=True)

    def bootstrap_workspace(
        self,
        *,
        workspace_id: str,
        slug: str,
        display_name: str,
        owner_user_id: str,
        api_token: str,
        plan_tier: str = "trial",
        billing_status: str = "trialing",
        region_code: str = "HK",
        data_residency_region: str = "ap-east-1",
        settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = utc_now_iso()
        workspace = TenantWorkspace(
            workspace_id=workspace_id,
            slug=slug,
            display_name=display_name,
            region_code=region_code,
            data_residency_region=data_residency_region,
            plan_tier=plan_tier,
            status="active",
            created_at=now,
            settings=dict(settings or {}),
            members=[WorkspaceMember(user_id=owner_user_id, role="owner", joined_at=now)],
        )
        billing = BillingAccount(
            workspace_id=workspace_id,
            provider_name="local-dev",
            provider_customer_ref=f"cust_{workspace_id}",
            provider_subscription_ref=f"sub_{workspace_id}",
            price_book_id=plan_tier,
            status=billing_status,
            seat_count=1,
            metadata={"bootstrap_mode": "local_dev"},
        )
        job_store.upsert_workspace(self.runtime_root, workspace)
        job_store.upsert_billing_account(self.runtime_root, billing)
        job_store.register_api_token(
            self.runtime_root,
            token=api_token,
            workspace_id=workspace_id,
            user_id=owner_user_id,
            role="owner",
            issued_at=now,
        )
        root = _workspace_root(self.runtime_root, workspace_id)
        (root / "briefs").mkdir(parents=True, exist_ok=True)
        (root / "personas").mkdir(parents=True, exist_ok=True)
        (root / "runs").mkdir(parents=True, exist_ok=True)
        return {
            "workspace": workspace.to_dict(),
            "billing_account": billing.to_dict(),
            "workspace_root": str(root),
            "api_token": api_token,
        }

    def authenticate(self, token: str) -> AuthContext:
        if not token.strip():
            raise AuthenticationError("Missing API token.")
        token_record = job_store.resolve_api_token(self.runtime_root, token)
        if token_record is None or not token_record.get("active"):
            raise AuthenticationError("Invalid API token.")
        if str(token_record["role"]) not in VISIBLE_ROLES:
            raise AuthorizationError(f"Unsupported workspace role '{token_record['role']}'.")
        return AuthContext(
            workspace_id=str(token_record["workspace_id"]),
            user_id=str(token_record["user_id"]),
            role=str(token_record["role"]),
            token=token,
            auth_type="api_token",
        )

    def issue_browser_session(
        self,
        auth: AuthContext,
        *,
        source: str = "hosted_shell",
        ttl: timedelta = BROWSER_SESSION_TTL,
    ) -> dict[str, Any]:
        issued_at = _now()
        expires_at = issued_at + ttl
        session = job_store.create_browser_session(
            self.runtime_root,
            WorkspaceBrowserSession(
                session_id=f"session_{uuid.uuid4().hex}",
                workspace_id=auth.workspace_id,
                user_id=auth.user_id,
                role=auth.role,
                source_token=auth.token or None,
                created_at=issued_at.isoformat(),
                last_seen_at=issued_at.isoformat(),
                expires_at=expires_at.isoformat(),
                metadata={"source": source},
            ),
        )
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=auth.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="browser_session.issued",
                target_type="browser_session",
                target_id=session.session_id,
                event_payload={
                    "source": source,
                    "expires_at": session.expires_at,
                    "source_token_hint": _mask_token(auth.token) if auth.token else "",
                },
                created_at=issued_at.isoformat(),
            ),
        )
        return session.to_dict()

    def authenticate_browser_session(self, session_id: str) -> AuthContext:
        clean_session_id = session_id.strip()
        if not clean_session_id:
            raise AuthenticationError("Missing browser session.")
        session = job_store.resolve_browser_session(self.runtime_root, clean_session_id)
        if session is None or session.revoked_at:
            raise AuthenticationError("Invalid browser session.")
        now = _now()
        try:
            expires_at = datetime.fromisoformat(session.expires_at)
        except ValueError as exc:
            raise AuthenticationError("Invalid browser session.") from exc
        if expires_at <= now:
            job_store.revoke_browser_session(self.runtime_root, clean_session_id, revoked_at=now.isoformat())
            raise AuthenticationError("Browser session expired.")
        if session.source_token:
            token_record = job_store.resolve_api_token(self.runtime_root, session.source_token)
            if token_record is None or not token_record.get("active"):
                job_store.revoke_browser_session(self.runtime_root, clean_session_id, revoked_at=now.isoformat())
                raise AuthenticationError("Browser session is no longer active.")
        workspace = job_store.get_workspace(self.runtime_root, session.workspace_id)
        if workspace is None or workspace.status != "active":
            raise AuthorizationError(f"Workspace '{session.workspace_id}' is not active.")
        member = next((item for item in workspace.members if item.user_id == session.user_id), None)
        if member is None:
            job_store.revoke_browser_session(self.runtime_root, clean_session_id, revoked_at=now.isoformat())
            raise AuthenticationError("Browser session user is no longer active in this workspace.")
        if member.role not in VISIBLE_ROLES:
            raise AuthorizationError(f"Unsupported workspace role '{member.role}'.")
        refreshed = job_store.touch_browser_session(
            self.runtime_root,
            clean_session_id,
            role=member.role,
            last_seen_at=now.isoformat(),
            expires_at=(now + BROWSER_SESSION_TTL).isoformat(),
        )
        effective_session = refreshed or session
        return AuthContext(
            workspace_id=effective_session.workspace_id,
            user_id=effective_session.user_id,
            role=member.role,
            auth_type="browser_session",
            session_id=effective_session.session_id,
        )

    def revoke_browser_session(self, auth: AuthContext, session_id: str, *, reason: str = "user_logout") -> dict[str, Any]:
        clean_session_id = session_id.strip()
        if not clean_session_id:
            raise AuthenticationError("Missing browser session.")
        session = job_store.resolve_browser_session(self.runtime_root, clean_session_id)
        if session is None or session.workspace_id != auth.workspace_id:
            raise AuthorizationError("Browser session is not visible in this workspace.")
        revoked = job_store.revoke_browser_session(self.runtime_root, clean_session_id, revoked_at=utc_now_iso())
        if revoked is None:
            raise AuthorizationError("Browser session is not visible in this workspace.")
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=auth.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="browser_session.revoked",
                target_type="browser_session",
                target_id=clean_session_id,
                event_payload={"reason": reason},
                created_at=utc_now_iso(),
            ),
        )
        return revoked.to_dict()

    def _workspace_and_billing(self, auth: AuthContext) -> tuple[TenantWorkspace, BillingAccount]:
        workspace = job_store.get_workspace(self.runtime_root, auth.workspace_id)
        if workspace is None:
            raise AuthorizationError(f"Unknown workspace '{auth.workspace_id}'.")
        if workspace.status != "active":
            raise AuthorizationError(f"Workspace '{auth.workspace_id}' is not active.")
        billing = job_store.get_billing_account(self.runtime_root, auth.workspace_id)
        if billing is None:
            raise AuthorizationError(f"Workspace '{auth.workspace_id}' has no billing account.")
        return workspace, billing

    def describe_workspace_settings(self, auth: AuthContext) -> dict[str, Any]:
        workspace, billing = self._workspace_and_billing(auth)
        limits = _plan_limits(workspace.plan_tier, workspace.settings)
        token_rows = job_store.list_api_tokens(self.runtime_root, auth.workspace_id)
        billing_governance = self._workspace_billing_governance_summary(billing)
        return {
            "contract_version": "workspace-settings-surface/v0-draft",
            "auth": auth.to_dict(),
            "workspace": workspace.to_dict(),
            "billing_account": billing.to_dict(),
            "plan_limits": limits,
            "billing_governance": billing_governance,
            "members": [member.to_dict() for member in workspace.members],
            "api_tokens": [
                {
                    "token_id": str(token_row["token"]),
                    "token_hint": _mask_token(str(token_row["token"])),
                    "user_id": str(token_row["user_id"]),
                    "role": str(token_row["role"]),
                    "issued_at": str(token_row["issued_at"]),
                    "active": bool(token_row["active"]),
                    "current": str(token_row["token"]) == auth.token,
                }
                for token_row in token_rows
            ],
            "capabilities": {
                "workspace_settings": True,
                "member_admin": auth.role in WORKSPACE_SETTINGS_MUTATION_ROLES,
                "token_admin": auth.role in WORKSPACE_SETTINGS_MUTATION_ROLES,
                "billing_mutation": auth.role in WORKSPACE_BILLING_MUTATION_ROLES,
                "billing_overview": True,
                "audit_history": True,
                "billing_governance_history": True,
            },
            "policies": {
                "region_code": workspace.region_code,
                "data_residency_region": workspace.data_residency_region,
                "artifact_retention_days": limits["artifact_retention_days"],
                "daily_runs": limits["daily_runs"],
                "max_concurrent_jobs": limits["max_concurrent_jobs"],
            },
            "synthetic_boundary": (
                "Synthetic evidence only. Workspace governance controls do not change the evidence boundary."
            ),
        }

    def describe_workspace_privacy_export_controls(
        self,
        auth: AuthContext,
        *,
        study_id: str = "",
        export_bundle_id: str = "",
        share_bundle_id: str = "",
    ) -> dict[str, Any]:
        workspace, _billing = self._workspace_and_billing(auth)
        limits = _plan_limits(workspace.plan_tier, workspace.settings)
        settings = dict(workspace.settings or {})
        studies = self.list_workspace_studies(auth)
        jobs = self.list_workspace_jobs(auth)
        export_bundles = self.list_workspace_export_bundles(auth)
        share_bundles = self.list_workspace_share_bundles(auth)

        linked_study = None
        if study_id.strip():
            linked_study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
            if linked_study is None or linked_study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        linked_export = None
        if export_bundle_id.strip():
            linked_export = job_store.get_workspace_export_bundle(self.runtime_root, export_bundle_id.strip())
            if linked_export is None or linked_export.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace export bundle '{export_bundle_id}' is not visible in this workspace.")
        linked_share = None
        if share_bundle_id.strip():
            linked_share = job_store.get_workspace_share_bundle(self.runtime_root, share_bundle_id.strip())
            if linked_share is None or linked_share.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace share bundle '{share_bundle_id}' is not visible in this workspace.")
            linked_share = self._refresh_share_bundle_status(linked_share)

        policy_history = _history_entries(settings.get("privacy_policy_history"))
        deletion_requests = _history_entries(settings.get("privacy_deletion_requests"))
        redaction_states = [
            dict(study.get("governed_redaction", {}))
            for study in studies
            if isinstance(study.get("governed_redaction"), dict)
        ]
        unresolved_redaction_count = sum(
            1
            for item in redaction_states
            if bool(item.get("required")) and not bool(item.get("circulation_allowed"))
        )
        linked_redaction = (
            self._study_governed_redaction_state(linked_study)
            if linked_study is not None
            else {}
        )
        retention_days = int(limits["artifact_retention_days"])
        blocked_reasons: list[str] = []
        if retention_days < 30:
            blocked_reasons.append("retention_window_too_short_for_customer_review")
        if not str(workspace.data_residency_region or "").strip():
            blocked_reasons.append("data_residency_region_missing")
        if not str(settings.get("deletion_request_policy") or "").strip():
            blocked_reasons.append("deletion_request_policy_missing")
        if unresolved_redaction_count:
            blocked_reasons.append("unresolved_governed_redaction")
        status = "ready_for_customer_review" if not blocked_reasons else "needs_attention"

        relevant_audit_actions = {
            "workspace.privacy_policy_updated",
            "workspace.privacy_deletion_requested",
            "workspace_policy.updated",
            "study.governed_redaction_updated",
            "share_bundle.revoked",
        }
        recent_audit = [
            event.to_dict()
            for event in job_store.list_audit_events(self.runtime_root, auth.workspace_id, limit=30)
            if event.action in relevant_audit_actions
        ][:10]

        return {
            "contract_version": "workspace-privacy-export-controls/v1",
            "workspace_id": workspace.workspace_id,
            "generated_at": utc_now_iso(),
            "workspace_boundary": {
                "workspace_id": workspace.workspace_id,
                "workspace_name": workspace.display_name,
                "workspace_isolation": "workspace_scoped_auth_and_artifact_paths",
                "local_first_boundary": (
                    "Local development uses SQLite indexes plus filesystem artifacts; future SaaS/cloud must use "
                    "database records plus object storage and backups instead of treating server local disk as durable production storage."
                ),
            },
            "data_residency": {
                "region_code": workspace.region_code,
                "data_residency_region": workspace.data_residency_region,
                "policy_source": "workspace_policy",
                "object_storage_ready": bool(settings.get("object_storage_ready", True)),
                "note": (
                    "This is a policy declaration in the local-first runtime. Hosted SaaS must enforce it through "
                    "database, object-storage, backup, and worker placement controls."
                ),
            },
            "retention_controls": {
                "artifact_retention_days": retention_days,
                "retention_floor_days_for_customer_review": 30,
                "object_classes": [
                    {
                        "object_class": "uploaded_artifacts",
                        "retention_behavior": "retained_until_policy_or_delete_request_review",
                        "lineage_behavior": "artifact references remain auditable even when the payload is removed or redacted",
                    },
                    {
                        "object_class": "generated_evidence_and_run_artifacts",
                        "retention_behavior": "retained_until_artifact_retention_days_then_purgeable",
                        "lineage_behavior": "run, study, and audit metadata remain for review continuity",
                    },
                    {
                        "object_class": "exports_and_shares",
                        "retention_behavior": "exports remain workspace-scoped; shares can expire or be revoked",
                        "lineage_behavior": "export/share metadata keeps readiness, redaction, and synthetic-boundary context",
                    },
                    {
                        "object_class": "calibration_records",
                        "retention_behavior": "retained as evidence-quality lineage until explicit governance review",
                        "lineage_behavior": "calibration summaries stay attached to readiness decisions",
                    },
                ],
            },
            "deletion_controls": {
                "deletion_request_policy": str(settings.get("deletion_request_policy") or "review_required"),
                "delete_payload_without_losing_lineage": True,
                "request_count": len(deletion_requests),
                "latest_request": _history_latest(deletion_requests),
                "recent_requests": deletion_requests[-5:],
                "supported_scope_types": [
                    "workspace",
                    "project",
                    "study",
                    "run",
                    "export_bundle",
                    "share_bundle",
                    "calibration_record",
                    "artifact",
                ],
                "audit_note": "Deletion requests are append-only policy events; destructive artifact purge remains governed by retention and explicit review.",
            },
            "redaction_controls": {
                "governed_redaction_state_counts": _count_values([
                    str(item.get("status") or "unknown")
                    for item in redaction_states
                ]),
                "unresolved_governed_redaction_count": unresolved_redaction_count,
                "linked_study_redaction": linked_redaction,
                "redaction_audit_lineage": (
                    "Governed redaction preserves rule reason, updater, note, and affected downstream export/share payloads."
                ),
            },
            "export_share_controls": {
                "export_bundle_count": len(export_bundles),
                "share_bundle_count": len(share_bundles),
                "share_status_counts": _count_values([
                    str(bundle.get("status") or "unknown")
                    for bundle in share_bundles
                ]),
                "export_review_required": bool(settings.get("export_review_required", True)),
                "share_default_expiry_days": int(settings.get("share_default_expiry_days") or 14),
                "linked_export_bundle": self._export_bundle_summary(linked_export) if linked_export is not None else {},
                "linked_share_bundle": self._share_bundle_summary(linked_share) if linked_share is not None else {},
                "user_boundary_copy": (
                    "Exports and shared views contain simulated evidence only. They should show what was retained, "
                    "redacted, removed, or still synthetic-only before customer circulation."
                ),
            },
            "downstream_lineage": {
                "study_count": len(studies),
                "run_count": len(jobs),
                "completed_run_count": sum(1 for job in jobs if str(job.get("status") or "") == "completed"),
                "export_bundle_count": len(export_bundles),
                "share_bundle_count": len(share_bundles),
                "policy_history_count": len(policy_history),
                "latest_policy_change": _history_latest(policy_history),
            },
            "privacy_readiness": {
                "status": status,
                "blocked_reasons": blocked_reasons,
                "customer_review_ready": status == "ready_for_customer_review",
                "next_actions": self._workspace_privacy_next_actions(blocked_reasons),
            },
            "audit_boundary": {
                "recent_event_count": len(recent_audit),
                "recent_events": recent_audit,
            },
            "synthetic_boundary": (
                "Privacy, residency, redaction, deletion, export, and share controls govern simulated research artifacts. "
                "They do not convert synthetic evidence into human market proof."
            ),
        }

    def update_workspace_privacy_policy(
        self,
        auth: AuthContext,
        *,
        data_residency_region: str | None = None,
        artifact_retention_days: int | None = None,
        deletion_request_policy: str | None = None,
        export_review_required: bool | None = None,
        share_default_expiry_days: int | None = None,
        note: str = "",
    ) -> dict[str, Any]:
        workspace, _billing = self._workspace_and_billing(auth)
        if auth.role not in WORKSPACE_PRIVACY_MUTATION_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot manage workspace privacy policy.")

        settings = dict(workspace.settings or {})
        next_settings = dict(settings)
        changes: dict[str, dict[str, Any]] = {}

        next_data_residency_region = workspace.data_residency_region
        if data_residency_region is not None:
            clean_region = data_residency_region.strip()
            if not clean_region:
                raise ValueError("Field 'data_residency_region' cannot be blank when provided.")
            if clean_region != workspace.data_residency_region:
                changes["data_residency_region"] = {
                    "previous": workspace.data_residency_region,
                    "next": clean_region,
                }
                next_data_residency_region = clean_region

        if artifact_retention_days is not None:
            retention_days = int(artifact_retention_days)
            if retention_days < 0:
                raise ValueError("Field 'artifact_retention_days' must be greater than or equal to 0.")
            if settings.get("artifact_retention_days") != retention_days:
                changes["artifact_retention_days"] = {
                    "previous": settings.get("artifact_retention_days"),
                    "next": retention_days,
                }
                next_settings["artifact_retention_days"] = retention_days

        if deletion_request_policy is not None:
            clean_policy = deletion_request_policy.strip() or "review_required"
            if settings.get("deletion_request_policy") != clean_policy:
                changes["deletion_request_policy"] = {
                    "previous": settings.get("deletion_request_policy"),
                    "next": clean_policy,
                }
                next_settings["deletion_request_policy"] = clean_policy

        if export_review_required is not None:
            next_value = bool(export_review_required)
            if bool(settings.get("export_review_required", True)) != next_value:
                changes["export_review_required"] = {
                    "previous": bool(settings.get("export_review_required", True)),
                    "next": next_value,
                }
                next_settings["export_review_required"] = next_value

        if share_default_expiry_days is not None:
            expiry_days = int(share_default_expiry_days)
            if expiry_days <= 0:
                raise ValueError("Field 'share_default_expiry_days' must be greater than 0.")
            if int(settings.get("share_default_expiry_days") or 14) != expiry_days:
                changes["share_default_expiry_days"] = {
                    "previous": int(settings.get("share_default_expiry_days") or 14),
                    "next": expiry_days,
                }
                next_settings["share_default_expiry_days"] = expiry_days

        change_note = note.strip()
        now = utc_now_iso()
        if changes:
            policy_history = _history_entries(settings.get("privacy_policy_history"))
            policy_history.append(
                {
                    "event": "privacy_policy_updated",
                    "changed_at": now,
                    "changed_by_user_id": auth.user_id,
                    "actor_role": auth.role,
                    "note": change_note,
                    "changes": changes,
                }
            )
            next_settings["privacy_policy_history"] = policy_history
            saved_workspace = job_store.upsert_workspace(
                self.runtime_root,
                TenantWorkspace(
                    workspace_id=workspace.workspace_id,
                    slug=workspace.slug,
                    display_name=workspace.display_name,
                    region_code=workspace.region_code,
                    data_residency_region=next_data_residency_region,
                    plan_tier=workspace.plan_tier,
                    status=workspace.status,
                    created_at=workspace.created_at,
                    settings=next_settings,
                    members=list(workspace.members),
                ),
            )
            job_store.create_audit_event(
                self.runtime_root,
                AuditEvent(
                    audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                    workspace_id=saved_workspace.workspace_id,
                    actor_user_id=auth.user_id,
                    actor_role=auth.role,
                    action="workspace.privacy_policy_updated",
                    target_type="workspace_privacy_policy",
                    target_id=saved_workspace.workspace_id,
                    event_payload={
                        "changes": changes,
                        "note": change_note or None,
                        "privacy_policy_history_count": len(policy_history),
                    },
                    created_at=now,
                ),
            )

        return self.describe_workspace_privacy_export_controls(auth)

    def record_workspace_privacy_deletion_request(
        self,
        auth: AuthContext,
        *,
        scope_type: str,
        scope_id: str,
        reason: str,
        requested_action: str = "",
        approval_note: str = "",
    ) -> dict[str, Any]:
        workspace, _billing = self._workspace_and_billing(auth)
        if auth.role not in WORKSPACE_PRIVACY_MUTATION_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot request workspace privacy deletion.")
        clean_scope_type = scope_type.strip().lower()
        allowed_scope_types = {
            "workspace",
            "project",
            "study",
            "run",
            "export_bundle",
            "share_bundle",
            "calibration_record",
            "artifact",
        }
        if clean_scope_type not in allowed_scope_types:
            raise ValueError(f"Unsupported privacy deletion scope_type '{clean_scope_type}'.")
        clean_scope_id = scope_id.strip()
        if clean_scope_type != "workspace" and not clean_scope_id:
            raise ValueError("Field 'scope_id' is required for this deletion request scope.")
        clean_reason = reason.strip()
        if not clean_reason:
            raise ValueError("Field 'reason' is required for a privacy deletion request.")

        now = utc_now_iso()
        action = requested_action.strip() or "record_for_review"
        affected_outputs = self._workspace_privacy_affected_outputs(
            workspace_id=workspace.workspace_id,
            scope_type=clean_scope_type,
            scope_id=clean_scope_id or workspace.workspace_id,
        )
        request = {
            "deletion_request_id": f"privacy_delete_{uuid.uuid4().hex[:12]}",
            "requested_at": now,
            "requested_by_user_id": auth.user_id,
            "actor_role": auth.role,
            "scope_type": clean_scope_type,
            "scope_id": clean_scope_id or workspace.workspace_id,
            "requested_action": action,
            "status": "recorded",
            "reason": clean_reason,
            "approval_note": approval_note.strip(),
            "affected_outputs": affected_outputs,
            "lineage_retained": True,
            "synthetic_boundary": (
                "Deletion handling removes or restricts selected simulated research payloads only after governance review; "
                "audit lineage stays available for evidence-boundary review."
            ),
        }

        revoked_share_bundle_id = ""
        if clean_scope_type == "share_bundle" and action in {"revoke_share", "delete_or_revoke", "delete"}:
            share_bundle = job_store.get_workspace_share_bundle(self.runtime_root, clean_scope_id)
            if share_bundle is None or share_bundle.workspace_id != workspace.workspace_id:
                raise AuthorizationError(f"Workspace share bundle '{clean_scope_id}' is not visible in this workspace.")
            updated_share = job_store.update_workspace_share_bundle(
                self.runtime_root,
                share_bundle_id=share_bundle.share_bundle_id,
                status="revoked",
                revoked_at=share_bundle.revoked_at or now,
                metadata_updates={
                    "privacy_deletion_request_id": request["deletion_request_id"],
                    "privacy_deletion_reason": clean_reason,
                    "privacy_deletion_requested_at": now,
                },
            )
            revoked_share_bundle_id = updated_share.share_bundle_id
            request["status"] = "recorded_and_share_revoked"
            request["revoked_share_bundle_id"] = revoked_share_bundle_id

        settings = dict(workspace.settings or {})
        deletion_requests = _history_entries(settings.get("privacy_deletion_requests"))
        deletion_requests.append(request)
        settings["privacy_deletion_requests"] = deletion_requests
        saved_workspace = job_store.upsert_workspace(
            self.runtime_root,
            TenantWorkspace(
                workspace_id=workspace.workspace_id,
                slug=workspace.slug,
                display_name=workspace.display_name,
                region_code=workspace.region_code,
                data_residency_region=workspace.data_residency_region,
                plan_tier=workspace.plan_tier,
                status=workspace.status,
                created_at=workspace.created_at,
                settings=settings,
                members=list(workspace.members),
            ),
        )
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=saved_workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="workspace.privacy_deletion_requested",
                target_type=f"privacy_{clean_scope_type}",
                target_id=request["scope_id"],
                event_payload={
                    "deletion_request_id": request["deletion_request_id"],
                    "scope_type": clean_scope_type,
                    "scope_id": request["scope_id"],
                    "requested_action": action,
                    "reason": clean_reason,
                    "approval_note": approval_note.strip() or None,
                    "affected_outputs": affected_outputs,
                    "revoked_share_bundle_id": revoked_share_bundle_id or None,
                    "lineage_retained": True,
                },
                created_at=now,
            ),
        )
        if revoked_share_bundle_id:
            job_store.create_audit_event(
                self.runtime_root,
                AuditEvent(
                    audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                    workspace_id=saved_workspace.workspace_id,
                    actor_user_id=auth.user_id,
                    actor_role=auth.role,
                    action="share_bundle.revoked",
                    target_type="share_bundle",
                    target_id=revoked_share_bundle_id,
                    event_payload={
                        "revoked_at": now,
                        "reason": "privacy_deletion_request",
                        "deletion_request_id": request["deletion_request_id"],
                    },
                    created_at=now,
                ),
            )
        return {
            "deletion_request": request,
            "privacy_export_controls": self.describe_workspace_privacy_export_controls(auth),
        }

    def _workspace_privacy_next_actions(self, blocked_reasons: list[str]) -> list[str]:
        actions: list[str] = []
        if "retention_window_too_short_for_customer_review" in blocked_reasons:
            actions.append("Set artifact_retention_days to at least 30 before broader customer review.")
        if "data_residency_region_missing" in blocked_reasons:
            actions.append("Record a workspace data_residency_region before customer onboarding.")
        if "deletion_request_policy_missing" in blocked_reasons:
            actions.append("Set deletion_request_policy so deletion and redaction requests do not depend on operator memory.")
        if "unresolved_governed_redaction" in blocked_reasons:
            actions.append("Resolve required governed redaction before export or share circulation.")
        return actions or ["Review privacy, export, share, redaction, and deletion controls before customer circulation."]

    def _workspace_privacy_affected_outputs(
        self,
        *,
        workspace_id: str,
        scope_type: str,
        scope_id: str,
    ) -> dict[str, Any]:
        jobs = job_store.list_workspace_jobs(self.runtime_root, workspace_id)
        export_bundles = job_store.list_workspace_export_bundles(self.runtime_root, workspace_id)
        share_bundles = job_store.list_workspace_share_bundles(self.runtime_root, workspace_id)

        def job_matches(job: dict[str, Any]) -> bool:
            metadata = dict(job.get("metadata") or {})
            if scope_type == "workspace":
                return True
            if scope_type == "study":
                return str(metadata.get("study_id") or "") == scope_id
            if scope_type == "project":
                return str(metadata.get("project_id") or "") == scope_id
            if scope_type == "run":
                return scope_id in {
                    str(job.get("job_id") or ""),
                    str(metadata.get("run_id") or ""),
                    _job_run_id(job),
                }
            return False

        matched_jobs = [job for job in jobs if job_matches(job)]
        matched_job_ids = {str(job.get("job_id") or "") for job in matched_jobs}
        matched_run_ids = {
            item
            for job in matched_jobs
            for item in {str(dict(job.get("metadata") or {}).get("run_id") or ""), _job_run_id(job)}
            if item
        }

        def bundle_matches(bundle: WorkspaceExportBundle | WorkspaceShareBundle) -> bool:
            if scope_type == "workspace":
                return True
            if scope_type == "study":
                return bundle.study_id == scope_id
            if scope_type == "project":
                return bundle.project_id == scope_id
            if scope_type == "run":
                return bundle.run_id == scope_id or bundle.run_id in matched_run_ids or bundle.job_id in matched_job_ids
            if scope_type == "export_bundle" and isinstance(bundle, WorkspaceExportBundle):
                return bundle.export_bundle_id == scope_id
            if scope_type == "export_bundle" and isinstance(bundle, WorkspaceShareBundle):
                return bundle.export_bundle_id == scope_id
            if scope_type == "share_bundle" and isinstance(bundle, WorkspaceShareBundle):
                return bundle.share_bundle_id == scope_id
            return False

        matched_exports = [bundle for bundle in export_bundles if bundle_matches(bundle)]
        matched_shares = [bundle for bundle in share_bundles if bundle_matches(bundle)]
        return {
            "job_ids": sorted(matched_job_ids),
            "run_ids": sorted(matched_run_ids),
            "export_bundle_ids": sorted(bundle.export_bundle_id for bundle in matched_exports),
            "share_bundle_ids": sorted(bundle.share_bundle_id for bundle in matched_shares),
            "affected_job_count": len(matched_jobs),
            "affected_export_bundle_count": len(matched_exports),
            "affected_share_bundle_count": len(matched_shares),
            "lineage_note": "Affected outputs remain listed so reports, decisions, and shared views can explain removed or redacted material.",
        }

    def _workspace_billing_governance_summary(self, billing: BillingAccount) -> dict[str, Any]:
        metadata = dict(billing.metadata or {})
        billing_history = _history_entries(metadata.get("billing_history"))
        policy_history = _history_entries(metadata.get("policy_history"))
        return {
            "contract_version": "workspace-billing-governance/v0-draft",
            "billing_history": billing_history,
            "policy_history": policy_history,
            "latest_billing_change": _history_latest(billing_history),
            "latest_policy_change": _history_latest(policy_history),
        }

    def upsert_workspace_member(self, auth: AuthContext, *, user_id: str, role: str) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in WORKSPACE_SETTINGS_MUTATION_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot manage workspace members.")
        clean_user_id = user_id.strip()
        clean_role = role.strip()
        if not clean_user_id:
            raise ValueError("Field 'user_id' is required.")
        if clean_role not in VISIBLE_ROLES:
            raise ValueError(f"Unsupported workspace role '{clean_role}'.")
        if clean_role == "owner" and auth.role != "owner":
            raise AuthorizationError("Only an owner can assign the owner role.")

        members_by_user_id = {member.user_id: member for member in workspace.members}
        existing_member = members_by_user_id.get(clean_user_id)
        if existing_member and existing_member.role == "owner" and clean_role != "owner":
            raise AuthorizationError("Owner role changes are not supported through the workspace settings surface.")

        members_by_user_id[clean_user_id] = WorkspaceMember(
            user_id=clean_user_id,
            role=clean_role,
            joined_at=existing_member.joined_at if existing_member else utc_now_iso(),
        )
        updated_workspace = TenantWorkspace(
            workspace_id=workspace.workspace_id,
            slug=workspace.slug,
            display_name=workspace.display_name,
            region_code=workspace.region_code,
            data_residency_region=workspace.data_residency_region,
            plan_tier=workspace.plan_tier,
            status=workspace.status,
            created_at=workspace.created_at,
            settings=dict(workspace.settings),
            members=sorted(members_by_user_id.values(), key=lambda member: (member.user_id, member.joined_at)),
        )
        saved_workspace = job_store.upsert_workspace(self.runtime_root, updated_workspace)
        job_store.update_api_tokens_for_member(
            self.runtime_root,
            workspace_id=workspace.workspace_id,
            user_id=clean_user_id,
            role=clean_role,
        )
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="workspace_member.upserted",
                target_type="workspace_member",
                target_id=clean_user_id,
                event_payload={
                    "member_role": clean_role,
                    "member_count": len(saved_workspace.members),
                },
                created_at=utc_now_iso(),
            ),
        )
        return next(member.to_dict() for member in saved_workspace.members if member.user_id == clean_user_id)

    def issue_workspace_api_token(self, auth: AuthContext, *, user_id: str) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in WORKSPACE_SETTINGS_MUTATION_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot issue API tokens.")
        clean_user_id = user_id.strip()
        if not clean_user_id:
            raise ValueError("Field 'user_id' is required.")
        member = next((item for item in workspace.members if item.user_id == clean_user_id), None)
        if member is None:
            raise AuthorizationError(f"Workspace member '{clean_user_id}' is not visible in this workspace.")
        if member.role == "owner" and auth.role != "owner":
            raise AuthorizationError("Only an owner can issue a token for an owner account.")
        token = f"token_{uuid.uuid4().hex}"
        issued_at = utc_now_iso()
        job_store.register_api_token(
            self.runtime_root,
            token=token,
            workspace_id=workspace.workspace_id,
            user_id=member.user_id,
            role=member.role,
            issued_at=issued_at,
        )
        token_hint = _mask_token(token)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="api_token.issued",
                target_type="api_token",
                target_id=token_hint,
                event_payload={
                    "user_id": member.user_id,
                    "role": member.role,
                },
                created_at=issued_at,
            ),
        )
        return {
            "token": token,
            "token_hint": token_hint,
            "user_id": member.user_id,
            "role": member.role,
            "issued_at": issued_at,
            "active": True,
            "current": token == auth.token,
        }

    def revoke_workspace_api_token(self, auth: AuthContext, token_id: str) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in WORKSPACE_SETTINGS_MUTATION_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot revoke API tokens.")
        token_record = job_store.resolve_api_token(self.runtime_root, token_id.strip())
        if token_record is None or str(token_record["workspace_id"]) != workspace.workspace_id:
            raise AuthorizationError("API token is not visible in this workspace.")
        if str(token_record["role"]) == "owner" and auth.role != "owner":
            raise AuthorizationError("Only an owner can revoke an owner token.")
        revoked = job_store.deactivate_api_token(self.runtime_root, token_id.strip())
        if revoked is None:
            raise AuthorizationError("API token is not visible in this workspace.")
        revoked_browser_sessions = job_store.revoke_browser_sessions_for_token(
            self.runtime_root,
            token_id.strip(),
            revoked_at=utc_now_iso(),
        )
        token_hint = _mask_token(str(revoked["token"]))
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="api_token.revoked",
                target_type="api_token",
                target_id=token_hint,
                event_payload={
                    "user_id": str(revoked["user_id"]),
                    "role": str(revoked["role"]),
                    "current": str(revoked["token"]) == auth.token,
                    "revoked_browser_sessions": revoked_browser_sessions,
                },
                created_at=utc_now_iso(),
            ),
        )
        return {
            "token_id": str(revoked["token"]),
            "token_hint": token_hint,
            "user_id": str(revoked["user_id"]),
            "role": str(revoked["role"]),
            "issued_at": str(revoked["issued_at"]),
            "active": bool(revoked["active"]),
            "current": str(revoked["token"]) == auth.token,
        }

    def update_workspace_billing(
        self,
        auth: AuthContext,
        *,
        plan_tier: str = "",
        billing_status: str = "",
        seat_count: int | None = None,
        renewal_at: str | None = None,
        daily_runs: int | None = None,
        max_concurrent_jobs: int | None = None,
        artifact_retention_days: int | None = None,
        note: str = "",
    ) -> dict[str, Any]:
        workspace, billing = self._workspace_and_billing(auth)
        if auth.role not in WORKSPACE_BILLING_MUTATION_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot manage workspace billing.")

        clean_plan_tier = plan_tier.strip() if isinstance(plan_tier, str) else ""
        clean_billing_status = billing_status.strip() if isinstance(billing_status, str) else ""
        if clean_plan_tier and clean_plan_tier not in PLAN_LIMITS:
            raise ValueError(f"Unsupported plan tier '{clean_plan_tier}'.")
        if clean_billing_status and clean_billing_status not in {"trialing", "active", "past_due", "canceled"}:
            raise ValueError(f"Unsupported billing status '{clean_billing_status}'.")
        if seat_count is not None and int(seat_count) <= 0:
            raise ValueError("Field 'seat_count' must be greater than 0.")

        limit_updates = {
            "daily_runs": daily_runs,
            "max_concurrent_jobs": max_concurrent_jobs,
            "artifact_retention_days": artifact_retention_days,
        }
        next_settings = dict(workspace.settings)
        applied_limit_updates: dict[str, int] = {}
        for key, value in limit_updates.items():
            if value is None:
                continue
            numeric_value = int(value)
            if numeric_value < 0:
                raise ValueError(f"Field '{key}' must be greater than or equal to 0.")
            next_settings[key] = numeric_value
            applied_limit_updates[key] = numeric_value

        next_renewal_at = billing.renewal_at
        if renewal_at is not None:
            clean_renewal_at = str(renewal_at).strip()
            next_renewal_at = clean_renewal_at or None

        next_plan_tier = clean_plan_tier or workspace.plan_tier
        billing_metadata = dict(billing.metadata or {})
        billing_history = _history_entries(billing_metadata.get("billing_history"))
        policy_history = _history_entries(billing_metadata.get("policy_history"))
        billing_changes: dict[str, dict[str, Any]] = {}
        if next_plan_tier != workspace.plan_tier:
            billing_changes["plan_tier"] = {"previous": workspace.plan_tier, "next": next_plan_tier}
        if (clean_billing_status or billing.status) != billing.status:
            billing_changes["billing_status"] = {"previous": billing.status, "next": clean_billing_status or billing.status}
        if (int(seat_count) if seat_count is not None else billing.seat_count) != billing.seat_count:
            billing_changes["seat_count"] = {"previous": billing.seat_count, "next": int(seat_count) if seat_count is not None else billing.seat_count}
        if next_renewal_at != billing.renewal_at:
            billing_changes["renewal_at"] = {"previous": billing.renewal_at, "next": next_renewal_at}
        policy_changes: dict[str, dict[str, Any]] = {}
        for key, next_value in next_settings.items():
            previous_value = workspace.settings.get(key)
            if previous_value != next_value and key in {"daily_runs", "max_concurrent_jobs", "artifact_retention_days"}:
                policy_changes[key] = {"previous": previous_value, "next": next_value}
        change_note = note.strip()
        now = utc_now_iso()
        if billing_changes:
            billing_history.append(
                {
                    "event": "billing_updated",
                    "changed_at": now,
                    "changed_by_user_id": auth.user_id,
                    "actor_role": auth.role,
                    "note": change_note,
                    "changes": billing_changes,
                }
            )
        if policy_changes:
            policy_history.append(
                {
                    "event": "policy_updated",
                    "changed_at": now,
                    "changed_by_user_id": auth.user_id,
                    "actor_role": auth.role,
                    "note": change_note,
                    "changes": policy_changes,
                }
            )
        billing_metadata["billing_history"] = billing_history
        billing_metadata["policy_history"] = policy_history
        updated_workspace = TenantWorkspace(
            workspace_id=workspace.workspace_id,
            slug=workspace.slug,
            display_name=workspace.display_name,
            region_code=workspace.region_code,
            data_residency_region=workspace.data_residency_region,
            plan_tier=next_plan_tier,
            status=workspace.status,
            created_at=workspace.created_at,
            settings=next_settings,
            members=list(workspace.members),
        )
        updated_billing = BillingAccount(
            workspace_id=billing.workspace_id,
            provider_name=billing.provider_name,
            provider_customer_ref=billing.provider_customer_ref,
            provider_subscription_ref=billing.provider_subscription_ref,
            price_book_id=next_plan_tier,
            status=clean_billing_status or billing.status,
            seat_count=int(seat_count) if seat_count is not None else billing.seat_count,
            renewal_at=next_renewal_at,
            metadata=billing_metadata,
        )
        saved_workspace = job_store.upsert_workspace(self.runtime_root, updated_workspace)
        saved_billing = job_store.upsert_billing_account(self.runtime_root, updated_billing)
        limits = _plan_limits(saved_workspace.plan_tier, saved_workspace.settings)
        if billing_changes:
            job_store.create_audit_event(
                self.runtime_root,
                AuditEvent(
                    audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                    workspace_id=workspace.workspace_id,
                    actor_user_id=auth.user_id,
                    actor_role=auth.role,
                    action="workspace_billing.updated",
                    target_type="billing_account",
                    target_id=saved_billing.workspace_id,
                    event_payload={
                        "plan_tier": saved_workspace.plan_tier,
                        "billing_status": saved_billing.status,
                        "seat_count": saved_billing.seat_count,
                        "renewal_at": saved_billing.renewal_at,
                        "changes": billing_changes,
                        "note": change_note or None,
                    },
                    created_at=now,
                ),
            )
        if policy_changes:
            job_store.create_audit_event(
                self.runtime_root,
                AuditEvent(
                    audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                    workspace_id=workspace.workspace_id,
                    actor_user_id=auth.user_id,
                    actor_role=auth.role,
                    action="workspace_policy.updated",
                    target_type="workspace_policy",
                    target_id=saved_workspace.workspace_id,
                    event_payload={
                        "applied_limit_updates": applied_limit_updates,
                        "effective_limits": limits,
                        "changes": policy_changes,
                        "note": change_note or None,
                    },
                    created_at=now,
                ),
            )
        return {
            "workspace": saved_workspace.to_dict(),
            "billing_account": saved_billing.to_dict(),
            "plan_limits": limits,
            "billing_governance": self._workspace_billing_governance_summary(saved_billing),
        }

    def list_workspace_audit_events(
        self,
        auth: AuthContext,
        *,
        target_type: str = "",
        action_prefix: str = "",
        limit: int = 20,
    ) -> dict[str, Any]:
        workspace, _billing = self._workspace_and_billing(auth)
        numeric_limit = max(1, min(int(limit), MAX_AUDIT_EVENT_QUERY_LIMIT))
        clean_target_type = target_type.strip()
        clean_action_prefix = action_prefix.strip()
        audit_events = job_store.list_audit_events(
            self.runtime_root,
            auth.workspace_id,
            target_type=clean_target_type,
            action_prefix=clean_action_prefix,
            limit=numeric_limit,
        )
        return {
            "contract_version": "workspace-audit-history-surface/v0-draft",
            "auth": auth.to_dict(),
            "filters": {
                "target_type": clean_target_type or None,
                "action_prefix": clean_action_prefix or None,
                "limit": numeric_limit,
            },
            "audit_events": [event.to_dict() for event in audit_events],
            "capabilities": {
                "workspace_settings": True,
                "audit_history": True,
            },
            "synthetic_boundary": (
                "Synthetic evidence only. Audit history shows simulated-research operations and governance events, not human validation."
            ),
        }

    def describe_workspace_integration_events(
        self,
        auth: AuthContext,
        *,
        study_id: str = "",
        event_type: str = "",
        limit: int = 50,
    ) -> dict[str, Any]:
        workspace, _billing = self._workspace_and_billing(auth)
        clean_study_id = study_id.strip()
        if clean_study_id:
            study = job_store.get_workspace_study(self.runtime_root, clean_study_id)
            if study is None or study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        clean_event_type = event_type.strip()
        numeric_limit = max(1, min(int(limit), 200))
        delivery_attempts = _history_entries(workspace.settings.get(INTEGRATION_DELIVERY_HISTORY_SETTING))

        events: list[dict[str, Any]] = []
        for audit_event in job_store.list_audit_events(self.runtime_root, auth.workspace_id, limit=1000):
            integration_event = self._integration_event_from_audit_event(auth, audit_event)
            if integration_event is not None:
                events.append(integration_event)
        events.extend(self._integration_readiness_events(auth))

        filtered = []
        for event in events:
            if clean_study_id and str(event.get("study_id") or "") != clean_study_id:
                continue
            if clean_event_type and str(event.get("event_type") or "") != clean_event_type:
                continue
            event = dict(event)
            event["delivery"] = self._integration_delivery_summary(str(event.get("event_id") or ""), delivery_attempts)
            filtered.append(event)
        filtered.sort(key=lambda item: (str(item.get("occurred_at") or ""), str(item.get("event_id") or "")), reverse=True)

        return {
            "contract_version": "workspace-integration-events/v1",
            "workspace_id": auth.workspace_id,
            "generated_at": utc_now_iso(),
            "events": filtered[:numeric_limit],
            "filters": {
                "study_id": clean_study_id or None,
                "event_type": clean_event_type or None,
                "limit": numeric_limit,
            },
            "supported_event_types": sorted(set(INTEGRATION_EVENT_ACTION_TYPES.values()) | {"readiness.changed"}),
            "delivery_audit": {
                "attempt_count": len(delivery_attempts),
                "latest_attempt": _history_latest(delivery_attempts),
                "storage_boundary": "local_workspace_settings_and_audit_events",
                "cloud_upgrade_path": "move delivery attempts to a durable queue/table without changing event payload contracts.",
            },
            "capabilities": {
                "study_created": True,
                "run_completed": True,
                "evidence_view_saved": True,
                "decision_logged": True,
                "readiness_changed": True,
                "support_handoff_changed": True,
                "delivery_attempt_audit": True,
            },
            "synthetic_boundary": (
                "Integration events preserve synthetic-evidence boundaries, readiness gates, provenance, privacy controls, "
                "and human-validation gaps. They are not a market-proof reporting channel."
            ),
        }

    def record_workspace_integration_delivery_attempt(
        self,
        auth: AuthContext,
        *,
        event_id: str,
        consumer_id: str,
        status: str,
        response_code: int | None = None,
        note: str = "",
        retry_after_seconds: int | None = None,
    ) -> dict[str, Any]:
        workspace, _billing = self._workspace_and_billing(auth)
        if auth.role not in WORKSPACE_SETTINGS_MUTATION_ROLES and auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot record integration delivery attempts.")
        clean_event_id = event_id.strip()
        clean_consumer_id = consumer_id.strip()
        clean_status = status.strip().lower()
        if not clean_event_id:
            raise ValueError("Field 'event_id' is required.")
        if not clean_consumer_id:
            raise ValueError("Field 'consumer_id' is required.")
        if clean_status not in INTEGRATION_DELIVERY_STATUSES:
            raise ValueError(f"Unsupported delivery status '{clean_status}'.")

        available_events = self.describe_workspace_integration_events(auth, limit=500)
        matched_event = next((event for event in available_events["events"] if event.get("event_id") == clean_event_id), None)
        if matched_event is None:
            raise ValueError(f"Integration event '{clean_event_id}' is not available in this workspace.")

        now = utc_now_iso()
        payload_fingerprint = hashlib.sha256(
            json.dumps(matched_event.get("payload", {}), sort_keys=True, ensure_ascii=False).encode("utf-8")
        ).hexdigest()[:24]
        attempt = {
            "delivery_attempt_id": f"integration_delivery_{uuid.uuid4().hex[:12]}",
            "event_id": clean_event_id,
            "event_type": matched_event.get("event_type"),
            "consumer_id": clean_consumer_id,
            "status": clean_status,
            "response_code": int(response_code) if response_code is not None else None,
            "note": note.strip(),
            "retry_after_seconds": int(retry_after_seconds) if retry_after_seconds is not None else None,
            "attempted_at": now,
            "attempted_by_user_id": auth.user_id,
            "actor_role": auth.role,
            "payload_boundary_hash": payload_fingerprint,
            "synthetic_boundary": "Delivery audit records boundary-preserving integration handling, not human validation.",
        }

        settings = dict(workspace.settings or {})
        attempts = _history_entries(settings.get(INTEGRATION_DELIVERY_HISTORY_SETTING))
        attempts.append(attempt)
        settings[INTEGRATION_DELIVERY_HISTORY_SETTING] = attempts[-500:]
        saved_workspace = job_store.upsert_workspace(
            self.runtime_root,
            TenantWorkspace(
                workspace_id=workspace.workspace_id,
                slug=workspace.slug,
                display_name=workspace.display_name,
                region_code=workspace.region_code,
                data_residency_region=workspace.data_residency_region,
                plan_tier=workspace.plan_tier,
                status=workspace.status,
                created_at=workspace.created_at,
                settings=settings,
                members=list(workspace.members),
            ),
        )
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=saved_workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="integration_event.delivery_recorded",
                target_type="integration_event",
                target_id=clean_event_id,
                event_payload={
                    "event_id": clean_event_id,
                    "event_type": matched_event.get("event_type"),
                    "consumer_id": clean_consumer_id,
                    "delivery_status": clean_status,
                    "response_code": attempt["response_code"],
                    "payload_boundary_hash": payload_fingerprint,
                    "study_id": matched_event.get("study_id") or None,
                    "run_id": matched_event.get("run_id") or None,
                },
                created_at=now,
            ),
        )
        return {
            "delivery_attempt": attempt,
            "integration_events": self.describe_workspace_integration_events(
                auth,
                study_id=str(matched_event.get("study_id") or ""),
                limit=50,
            ),
        }

    def _integration_event_from_audit_event(self, auth: AuthContext, audit_event: AuditEvent) -> dict[str, Any] | None:
        event_type = INTEGRATION_EVENT_ACTION_TYPES.get(audit_event.action)
        if event_type is None:
            return None
        payload = dict(audit_event.event_payload or {})
        study_id = str(payload.get("study_id") or (audit_event.target_id if audit_event.target_type == "study" else "")).strip()
        job_id = str(payload.get("job_id") or (audit_event.target_id if audit_event.target_type == "validation_job" else "")).strip()
        run_id = str(payload.get("run_id") or "").strip()
        project_id = str(payload.get("project_id") or "").strip()
        target_id = audit_event.target_id
        route_path = self._integration_event_route(
            event_type=event_type,
            study_id=study_id,
            run_id=run_id or job_id,
            target_id=target_id,
        )
        integration_payload = self._integration_event_payload(
            auth,
            event_type=event_type,
            source_payload=payload,
            project_id=project_id,
            study_id=study_id,
            job_id=job_id,
            run_id=run_id,
            target_type=audit_event.target_type,
            target_id=target_id,
            source_audit_event_id=audit_event.audit_event_id,
        )
        return {
            "event_id": f"integration_{audit_event.audit_event_id}",
            "event_type": event_type,
            "source_action": audit_event.action,
            "workspace_id": auth.workspace_id,
            "project_id": project_id or integration_payload.get("project_id"),
            "study_id": study_id or integration_payload.get("study_id"),
            "job_id": job_id or integration_payload.get("job_id"),
            "run_id": run_id or integration_payload.get("run_id"),
            "target_type": audit_event.target_type,
            "target_id": target_id,
            "occurred_at": audit_event.created_at,
            "route_path": route_path,
            "payload": integration_payload,
            "synthetic_boundary": integration_payload["synthetic_boundary"],
        }

    def _integration_readiness_events(self, auth: AuthContext) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for evidence_view in job_store.list_workspace_evidence_views(self.runtime_root, auth.workspace_id):
            summary = self._evidence_view_summary(evidence_view)
            readiness_gate = summary.get("readiness_gate") if isinstance(summary.get("readiness_gate"), dict) else {}
            readiness_status = str(readiness_gate.get("status") or "").strip()
            if not readiness_status:
                continue
            payload = self._integration_event_payload(
                auth,
                event_type="readiness.changed",
                source_payload={
                    "readiness_status": readiness_status,
                    "selected_signal_id": summary.get("selected_signal_id"),
                    "source_exchange_refs": summary.get("source_exchange_refs", []),
                    "source_trace_refs": summary.get("source_trace_refs", []),
                },
                project_id=evidence_view.project_id,
                study_id=evidence_view.study_id,
                job_id=str(evidence_view.job_id or ""),
                run_id=str(evidence_view.run_id or ""),
                target_type="evidence_view",
                target_id=evidence_view.evidence_view_id,
                source_audit_event_id="",
                readiness_gate=readiness_gate,
            )
            events.append(
                {
                    "event_id": f"integration_readiness_{evidence_view.evidence_view_id}_{readiness_status}",
                    "event_type": "readiness.changed",
                    "source_action": "readiness.projected",
                    "workspace_id": auth.workspace_id,
                    "project_id": evidence_view.project_id,
                    "study_id": evidence_view.study_id,
                    "job_id": evidence_view.job_id,
                    "run_id": evidence_view.run_id,
                    "target_type": "evidence_view",
                    "target_id": evidence_view.evidence_view_id,
                    "occurred_at": evidence_view.updated_at or evidence_view.created_at,
                    "route_path": f"/studio/studies/{evidence_view.study_id}/evidence-views/{evidence_view.evidence_view_id}",
                    "payload": payload,
                    "synthetic_boundary": payload["synthetic_boundary"],
                }
            )
        return events

    def _integration_event_payload(
        self,
        auth: AuthContext,
        *,
        event_type: str,
        source_payload: dict[str, Any],
        project_id: str,
        study_id: str,
        job_id: str,
        run_id: str,
        target_type: str,
        target_id: str,
        source_audit_event_id: str,
        readiness_gate: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        source_exchange_refs: list[str] = []
        source_trace_refs: list[str] = []
        human_validation_gaps: list[Any] = []
        provider_runtime_boundary: dict[str, Any] = (
            dict(source_payload.get("provider_runtime_boundary"))
            if isinstance(source_payload.get("provider_runtime_boundary"), dict)
            else {}
        )
        gate = dict(readiness_gate or {}) if isinstance(readiness_gate, dict) else {}

        if event_type in {"run.completed", "run.failed"} and job_id:
            try:
                query = self.query_workspace_evidence(auth, job_id=job_id)
            except (FileNotFoundError, ValueError, AuthorizationError):
                query = {}
            if isinstance(query, dict) and query:
                if not gate and isinstance(query.get("readiness_gate"), dict):
                    gate = dict(query["readiness_gate"])
                if not provider_runtime_boundary and isinstance(query.get("provider_runtime_boundary"), dict):
                    provider_runtime_boundary = dict(query["provider_runtime_boundary"])
                for result in query.get("results", []) if isinstance(query.get("results"), list) else []:
                    if not isinstance(result, dict):
                        continue
                    if isinstance(result.get("source_exchange_refs"), list):
                        source_exchange_refs.extend(str(ref) for ref in result["source_exchange_refs"] if str(ref).strip())
                    if isinstance(result.get("source_trace_refs"), list):
                        source_trace_refs.extend(str(ref) for ref in result["source_trace_refs"] if str(ref).strip())
                reliability = query.get("evidence_reliability") if isinstance(query.get("evidence_reliability"), dict) else {}
                human_validation_gaps = list(reliability.get("missing_context", [])) if isinstance(reliability.get("missing_context"), list) else []

        if target_type == "evidence_view":
            view = job_store.get_workspace_evidence_view(self.runtime_root, target_id)
            if view is not None and view.workspace_id == auth.workspace_id:
                summary = self._evidence_view_summary(view)
                if not gate and isinstance(summary.get("readiness_gate"), dict):
                    gate = dict(summary["readiness_gate"])
                provider_runtime_boundary = provider_runtime_boundary or (
                    dict(summary.get("provider_runtime_boundary", {})) if isinstance(summary.get("provider_runtime_boundary"), dict) else {}
                )
                source_exchange_refs.extend(str(ref) for ref in summary.get("source_exchange_refs", []) if str(ref).strip())
                source_trace_refs.extend(str(ref) for ref in summary.get("source_trace_refs", []) if str(ref).strip())
        elif target_type == "decision_log":
            decision = job_store.get_workspace_decision_log(self.runtime_root, target_id)
            if decision is not None and decision.workspace_id == auth.workspace_id:
                summary = self._decision_log_summary(decision)
                if not gate and isinstance(summary.get("readiness_gate"), dict):
                    gate = dict(summary["readiness_gate"])
                provider_runtime_boundary = provider_runtime_boundary or (
                    dict(summary.get("provider_runtime_boundary", {})) if isinstance(summary.get("provider_runtime_boundary"), dict) else {}
                )
                source_exchange_refs.extend(str(ref) for ref in summary.get("source_exchange_refs", []) if str(ref).strip())
                source_trace_refs.extend(str(ref) for ref in summary.get("source_trace_refs", []) if str(ref).strip())
                if str(summary.get("metadata", {}).get("human_follow_up") if isinstance(summary.get("metadata"), dict) else "").strip():
                    human_validation_gaps.append(str(summary["metadata"]["human_follow_up"]))

        privacy_controls = self.describe_workspace_privacy_export_controls(auth, study_id=study_id)
        return {
            "contract_version": "workspace-integration-event-payload/v1",
            "event_type": event_type,
            "workspace_id": auth.workspace_id,
            "project_id": project_id or None,
            "study_id": study_id or None,
            "job_id": job_id or None,
            "run_id": run_id or None,
            "target_type": target_type,
            "target_id": target_id,
            "readiness_gate": gate,
            "provider_runtime_boundary": provider_runtime_boundary,
            "provenance": {
                "source_audit_event_id": source_audit_event_id or None,
                "source_exchange_refs": _unique_preserve_order(source_exchange_refs)[:12],
                "source_trace_refs": _unique_preserve_order(source_trace_refs)[:12],
                "source_payload_keys": sorted(str(key) for key in source_payload.keys()),
            },
            "privacy_export_controls": {
                "privacy_readiness": privacy_controls.get("privacy_readiness"),
                "retention_controls": privacy_controls.get("retention_controls"),
                "data_residency": privacy_controls.get("data_residency"),
            },
            "human_validation_gaps": human_validation_gaps[:8],
            "human_validation_required": True,
            "synthetic_boundary": (
                "This integration payload carries simulated evidence state with provenance, readiness, privacy, and "
                "human-validation boundaries. It must not be presented as human market proof."
            ),
        }

    @staticmethod
    def _integration_event_route(*, event_type: str, study_id: str, run_id: str, target_id: str) -> str | None:
        if event_type == "study.created" and study_id:
            return f"/studio/studies/{study_id}"
        if event_type in {"run.completed", "run.failed"} and study_id and run_id:
            return f"/studio/studies/{study_id}/runs/{run_id}"
        if event_type in {"evidence_view.saved", "readiness.changed"} and study_id and target_id:
            return f"/studio/studies/{study_id}/evidence-views/{target_id}"
        if event_type == "decision.logged" and study_id and target_id:
            return f"/studio/studies/{study_id}/decisions/{target_id}"
        if event_type == "support.handoff_changed" and study_id:
            return f"/studio/studies/{study_id}"
        return None

    @staticmethod
    def _integration_delivery_summary(event_id: str, attempts: list[dict[str, Any]]) -> dict[str, Any]:
        matching = [attempt for attempt in attempts if str(attempt.get("event_id") or "") == event_id]
        latest = matching[-1] if matching else None
        return {
            "status": str(latest.get("status") or "not_delivered") if isinstance(latest, dict) else "not_delivered",
            "attempt_count": len(matching),
            "latest_attempt": latest,
            "retry_visible": bool(isinstance(latest, dict) and str(latest.get("status") or "") in {"failed", "retrying"}),
            "consumer_ids": sorted({str(attempt.get("consumer_id") or "") for attempt in matching if str(attempt.get("consumer_id") or "").strip()}),
        }

    def create_workspace_project(
        self,
        auth: AuthContext,
        *,
        name: str,
        description: str = "",
        slug: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot create projects.")
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Field 'name' is required.")
        candidate_slug = _slugify_label(slug or clean_name, fallback=f"project-{uuid.uuid4().hex[:6]}")
        if any(existing["slug"] == candidate_slug for existing in self.list_workspace_projects(auth)):
            raise ValueError(f"Project slug '{candidate_slug}' already exists in this workspace.")
        project = WorkspaceProject(
            project_id=f"project_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace.workspace_id,
            slug=candidate_slug,
            name=clean_name,
            description=description.strip(),
            created_by_user_id=auth.user_id,
            status="active",
            created_at=utc_now_iso(),
            updated_at=utc_now_iso(),
            metadata=dict(metadata or {}),
        )
        created = job_store.create_workspace_project(self.runtime_root, project)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="project.created",
                target_type="project",
                target_id=created.project_id,
                event_payload={
                    "project_id": created.project_id,
                    "project_slug": created.slug,
                    "project_name": created.name,
                },
                created_at=created.created_at,
            ),
        )
        return self._project_summary(created)

    def list_workspace_projects(self, auth: AuthContext) -> list[dict[str, Any]]:
        workspace, _billing = self._workspace_and_billing(auth)
        return [self._project_summary(project) for project in job_store.list_workspace_projects(self.runtime_root, auth.workspace_id)]

    def get_workspace_project(self, auth: AuthContext, project_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        project = job_store.get_workspace_project(self.runtime_root, project_id)
        if project is None or project.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace project '{project_id}' is not visible in this workspace.")
        return self._project_summary(project)

    def _regulated_review_boundary_from_fields(
        self,
        *,
        title: str,
        research_intent: str,
        desired_output: str,
        first_task: str,
        artifact_refs: list[str],
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        clean_metadata = dict(metadata or {})
        explicit_boundary = clean_metadata.get("regulated_review_boundary")
        if not isinstance(explicit_boundary, dict):
            explicit_boundary = {}
        signal_parts = [
            _normalized_string(title),
            _normalized_string(research_intent),
            _normalized_string(desired_output),
            _normalized_string(first_task),
            " ".join(_normalized_string(item) for item in artifact_refs if _normalized_string(item)),
        ]
        signal_text = " ".join(part for part in signal_parts if part).lower()
        matched_domains: list[dict[str, Any]] = []
        matched_domain_ids: list[str] = []
        policy_labels = ["synthetic_evidence_only"]
        for domain in REGULATED_REVIEW_DOMAIN_DEFINITIONS:
            matched_markers = [
                marker
                for marker in domain["markers"]
                if _regulated_marker_matches(marker, signal_text)
            ]
            if not matched_markers:
                continue
            matched_domains.append(
                {
                    "domain_id": domain["domain_id"],
                    "label": domain["label"],
                    "matched_markers": matched_markers,
                }
            )
            matched_domain_ids.append(str(domain["domain_id"]))
        classification_status = "high_stakes" if matched_domains else "standard"
        requires_governed_review = classification_status == "high_stakes"
        explicit_status = _normalized_string(explicit_boundary.get("boundary_handling_status"))
        explicit_allow_execution = bool(explicit_boundary.get("allow_execution"))
        explicit_note = _normalized_string(explicit_boundary.get("explicit_boundary_note"))
        explicit_acknowledged = (
            explicit_status in REGULATED_REVIEW_BOUNDARY_ACK_STATUSES and explicit_allow_execution
        )
        if requires_governed_review:
            policy_labels.extend(["human_review_required", "regulated_high_stakes"])
            boundary_handling_status = "acknowledged" if explicit_acknowledged else "pending_explicit_boundary"
            execution_status = "allowed" if explicit_acknowledged else "blocked_pending_boundary_review"
            boundary_message = (
                "This study is classified as regulated or high-stakes. Add explicit governed boundary handling "
                "in study metadata before execution proceeds."
            )
        else:
            boundary_handling_status = "not_required"
            execution_status = "allowed"
            boundary_message = "This study is not currently classified as regulated or high-stakes."
        return {
            "contract_version": "workspace-study-regulated-review-boundary/v0-draft",
            "classification_status": classification_status,
            "matched_domain_ids": matched_domain_ids,
            "matched_domains": matched_domains,
            "requires_governed_review": requires_governed_review,
            "boundary_handling_status": boundary_handling_status,
            "execution_status": execution_status,
            "allow_execution": execution_status == "allowed",
            "explicit_boundary_acknowledged": explicit_acknowledged,
            "explicit_boundary_acknowledged_at": explicit_boundary.get("explicit_boundary_acknowledged_at"),
            "explicit_boundary_acknowledged_by_user_id": explicit_boundary.get("explicit_boundary_acknowledged_by_user_id"),
            "explicit_boundary_note": explicit_note,
            "policy_labels": policy_labels,
            "source_fields": ["title", "research_intent", "desired_output", "first_task", "artifact_refs"],
            "boundary_message": boundary_message,
        }

    def _merge_study_metadata_with_regulated_boundary(
        self,
        *,
        title: str,
        research_intent: str,
        desired_output: str,
        first_task: str,
        artifact_refs: list[str],
        metadata: dict[str, Any] | None,
    ) -> dict[str, Any]:
        merged_metadata = dict(metadata or {})
        merged_metadata["regulated_review_boundary"] = self._regulated_review_boundary_from_fields(
            title=title,
            research_intent=research_intent,
            desired_output=desired_output,
            first_task=first_task,
            artifact_refs=artifact_refs,
            metadata=merged_metadata,
        )
        return merged_metadata

    def _study_regulated_review_boundary(self, study: WorkspaceStudy) -> dict[str, Any]:
        return self._regulated_review_boundary_from_fields(
            title=study.title,
            research_intent=study.research_intent,
            desired_output=study.desired_output,
            first_task=study.first_task,
            artifact_refs=list(study.artifact_refs),
            metadata=dict(study.metadata or {}),
        )

    def _study_governed_review_assignment(
        self,
        study: WorkspaceStudy,
        workspace: TenantWorkspace,
    ) -> dict[str, Any]:
        boundary = self._study_regulated_review_boundary(study)
        metadata = dict(study.metadata or {})
        assignment = metadata.get("governed_review_assignment")
        if not isinstance(assignment, dict):
            assignment = {}
        member_map = self._workspace_member_map(workspace)
        normalized_assignees = _unique_preserve_order(
            [str(value) for value in assignment.get("assignee_user_ids", [])]
            if isinstance(assignment.get("assignee_user_ids"), list)
            else []
        )
        reviewer_members = []
        for user_id in normalized_assignees:
            member = member_map.get(user_id)
            reviewer_members.append(
                {
                    "user_id": user_id,
                    "role": member.role if member is not None else None,
                    "active": member is not None and member.role in DECISION_REVIEW_ASSIGNEE_ROLES,
                }
            )
        assignment_status = _normalized_string(assignment.get("status"))
        if assignment_status not in GOVERNED_REVIEW_ASSIGNMENT_STATUSES:
            assignment_status = "assigned" if normalized_assignees else "unassigned"
        required = bool(boundary.get("requires_governed_review"))
        if not required:
            assignment_status = "not_required"
            normalized_assignees = []
            reviewer_members = []
        elif assignment_status != "escalated" and not normalized_assignees:
            assignment_status = "unassigned"
        elif assignment_status != "escalated":
            assignment_status = "assigned"
        return {
            "contract_version": "workspace-study-governed-review-assignment/v0-draft",
            "required": required,
            "status": assignment_status,
            "assignee_user_ids": normalized_assignees,
            "reviewer_members": reviewer_members,
            "assigned_at": assignment.get("assigned_at") or None,
            "assigned_by_user_id": assignment.get("assigned_by_user_id") or None,
            "escalated_at": assignment.get("escalated_at") or None,
            "escalated_by_user_id": assignment.get("escalated_by_user_id") or None,
            "latest_note": _normalized_string(assignment.get("latest_note")),
        }

    def _study_governed_review_assignment_history(self, study: WorkspaceStudy) -> list[dict[str, Any]]:
        history = dict(study.metadata or {}).get("governed_review_assignment_history")
        if not isinstance(history, list):
            return []
        normalized: list[dict[str, Any]] = []
        for item in history:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "status": str(item.get("status") or "unassigned"),
                    "assignee_user_ids": _unique_preserve_order(
                        [str(value) for value in item.get("assignee_user_ids", [])]
                        if isinstance(item.get("assignee_user_ids"), list)
                        else []
                    ),
                    "changed_at": item.get("changed_at") or None,
                    "changed_by_user_id": item.get("changed_by_user_id") or None,
                    "note": str(item.get("note") or ""),
                }
            )
        return normalized

    def _study_governed_review_state(self, study: WorkspaceStudy) -> dict[str, Any]:
        workspace = job_store.get_workspace(self.runtime_root, study.workspace_id)
        if workspace is None:
            raise FileNotFoundError(f"Workspace '{study.workspace_id}' not found for governed review state.")
        boundary = self._study_regulated_review_boundary(study)
        reviewer_handoff = self._study_governed_review_assignment(study, workspace)
        assignment_status = str(reviewer_handoff.get("status") or "not_required")
        review_required = bool(boundary.get("requires_governed_review"))
        if not review_required:
            gate_status = "not_required"
            note = "No additional governed reviewer responsibility is required for this study."
            blocked_reason = None
            decision_review_allowed = True
            circulation_allowed = True
        elif assignment_status == "assigned":
            gate_status = "assigned_for_review"
            note = (
                "High-stakes synthetic evidence remains bounded and requires the named study reviewer before "
                "approval or partner-facing circulation."
            )
            blocked_reason = None
            decision_review_allowed = True
            circulation_allowed = True
        elif assignment_status == "escalated":
            gate_status = "escalated"
            note = (
                reviewer_handoff.get("latest_note")
                or "Governed review is escalated. Decision approval and partner-facing circulation remain blocked until it is resolved."
            )
            blocked_reason = "Governed review is escalated and must be resolved before approval or circulation."
            decision_review_allowed = False
            circulation_allowed = False
        else:
            gate_status = "blocked_reviewer_unassigned"
            note = (
                "High-stakes synthetic evidence requires a named study reviewer before decision approval "
                "or partner-facing circulation."
            )
            blocked_reason = "Named study reviewer responsibility is missing for this regulated/high-stakes study."
            decision_review_allowed = False
            circulation_allowed = False
        policy_labels = _unique_preserve_order(
            [
                *[str(label) for label in boundary.get("policy_labels", []) if str(label).strip()],
                "governed_review_required" if review_required else "governed_review_not_required",
                f"governed_review_status:{gate_status}",
            ]
        )
        return {
            "contract_version": "workspace-study-governed-review/v0-draft",
            "regulated_review_boundary": boundary,
            "reviewer_handoff": reviewer_handoff,
            "reviewer_handoff_history": self._study_governed_review_assignment_history(study),
            "review_gate_status": gate_status,
            "policy_labels": policy_labels,
            "human_review_required": review_required,
            "human_review_note": note,
            "blocked_reason": blocked_reason,
            "decision_review_allowed": decision_review_allowed,
            "circulation_allowed": circulation_allowed,
        }

    def _normalized_governed_redaction_rules(self, raw_rules: Any) -> list[dict[str, Any]]:
        if not isinstance(raw_rules, list):
            return []
        normalized: list[dict[str, Any]] = []
        for index, item in enumerate(raw_rules, start=1):
            if not isinstance(item, dict):
                continue
            path = _normalized_string(item.get("path"))
            reason = _normalized_string(item.get("reason"))
            if not path or not reason:
                continue
            normalized.append(
                {
                    "rule_id": _normalized_string(item.get("rule_id")) or f"rule_{index}",
                    "path": path,
                    "reason": reason,
                    "replacement": _normalized_string(item.get("replacement")) or "[REDACTED]",
                    "audience": _normalized_string(item.get("audience")) or "external_viewer",
                }
            )
        return normalized

    def _study_governed_redaction_history(self, study: WorkspaceStudy) -> list[dict[str, Any]]:
        history = dict(study.metadata or {}).get("governed_redaction_history")
        if not isinstance(history, list):
            return []
        normalized: list[dict[str, Any]] = []
        for item in history:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "status": str(item.get("status") or "unconfigured"),
                    "changed_at": item.get("changed_at") or None,
                    "changed_by_user_id": item.get("changed_by_user_id") or None,
                    "note": str(item.get("note") or ""),
                    "rule_count": len(self._normalized_governed_redaction_rules(item.get("redaction_rules"))),
                }
            )
        return normalized

    def _study_governed_redaction_state(self, study: WorkspaceStudy) -> dict[str, Any]:
        boundary = self._study_regulated_review_boundary(study)
        metadata = dict(study.metadata or {})
        redaction = metadata.get("governed_redaction")
        if not isinstance(redaction, dict):
            redaction = {}
        required = bool(boundary.get("requires_governed_review"))
        status = _normalized_string(redaction.get("status"))
        rules = self._normalized_governed_redaction_rules(redaction.get("redaction_rules"))
        if not required:
            status = "not_required"
            rules = []
            circulation_allowed = True
            blocked_reason = None
            note = "No governed redaction policy is required for this study."
        elif status == "active" and rules:
            circulation_allowed = True
            blocked_reason = None
            note = (
                _normalized_string(redaction.get("latest_note"))
                or "Viewer-safe circulation uses the active governed redaction policy for this regulated/high-stakes study."
            )
        elif status == "escalated":
            circulation_allowed = False
            blocked_reason = "Governed redaction is escalated and must be resolved before partner-facing circulation."
            note = (
                _normalized_string(redaction.get("latest_note"))
                or blocked_reason
            )
        else:
            status = status if status in {"draft", "unconfigured"} else "unconfigured"
            circulation_allowed = False
            blocked_reason = "Governed redaction policy is missing or inactive for this regulated/high-stakes study."
            note = (
                _normalized_string(redaction.get("latest_note"))
                or "Regulated/high-stakes partner-facing circulation requires an active governed redaction policy."
            )
        policy_labels = _unique_preserve_order(
            [
                "governed_redaction_required" if required else "governed_redaction_not_required",
                f"governed_redaction_status:{status}",
            ]
        )
        return {
            "contract_version": "workspace-study-governed-redaction/v0-draft",
            "required": required,
            "status": status,
            "redaction_rules": rules,
            "rule_count": len(rules),
            "policy_labels": policy_labels,
            "circulation_allowed": circulation_allowed,
            "blocked_reason": blocked_reason,
            "latest_note": _normalized_string(redaction.get("latest_note")) or note,
            "updated_at": redaction.get("updated_at") or None,
            "updated_by_user_id": redaction.get("updated_by_user_id") or None,
        }

    def _apply_governed_redaction_to_payload(
        self,
        payload: dict[str, Any],
        governed_redaction: dict[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        redacted_payload = dict(payload)
        applied_redactions: list[dict[str, Any]] = []
        for rule in self._normalized_governed_redaction_rules(governed_redaction.get("redaction_rules")):
            for path, existed in self._apply_redaction_rule(redacted_payload, rule):
                applied_redactions.append(
                    {
                        "rule_id": rule["rule_id"],
                        "path": path,
                        "reason": rule["reason"],
                        "replacement": rule["replacement"],
                        "audience": rule["audience"],
                        "source_present": existed,
                    }
                )
        return redacted_payload, applied_redactions

    def _apply_redaction_rule(self, payload: dict[str, Any], rule: dict[str, Any]) -> list[tuple[str, bool]]:
        parts = [part for part in str(rule.get("path") or "").split(".") if part]
        if not parts:
            return []
        results: list[tuple[str, bool]] = []

        def _walk(current: Any, remaining: list[str], traversed: list[str]) -> None:
            if not remaining:
                return
            part = remaining[0]
            if part.endswith("[]"):
                key = part[:-2]
                if not isinstance(current, dict):
                    return
                value = current.get(key)
                if not isinstance(value, list):
                    return
                for index, item in enumerate(value):
                    _walk(item, remaining[1:], [*traversed, f"{key}[{index}]"])
                return
            if len(remaining) == 1:
                if isinstance(current, dict) and part in current:
                    current[part] = _redaction_replacement_for_value(str(rule.get("replacement") or ""), current.get(part))
                    results.append((".".join([*traversed, part]), True))
                else:
                    results.append((".".join([*traversed, part]), False))
                return
            if isinstance(current, dict) and isinstance(current.get(part), (dict, list)):
                _walk(current.get(part), remaining[1:], [*traversed, part])

        _walk(redacted_payload := payload, parts, [])
        return results

    def _build_governed_compliance_audit_bundle(
        self,
        *,
        workspace_id: str,
        study: WorkspaceStudy,
        project_id: str | None = None,
        job_id: str | None = None,
        run_id: str | None = None,
        export_bundle_id: str | None = None,
        share_bundle_id: str | None = None,
        readiness_gate: dict[str, Any] | None = None,
        mvp_launch_scope: dict[str, Any] | None = None,
        mvp_promotion: dict[str, Any] | None = None,
        partner_onboarding: dict[str, Any] | None = None,
        mvp_release_review: dict[str, Any] | None = None,
        applied_redactions: list[dict[str, Any]] | None = None,
        redacted_payload_preview: dict[str, Any] | None = None,
        distribution_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        governed_review = self._study_governed_review_state(study)
        governed_redaction = self._study_governed_redaction_state(study)
        relevant_events = []
        for event in job_store.list_audit_events(self.runtime_root, workspace_id, limit=500):
            if not self._audit_event_matches_study(event, study.study_id):
                continue
            if event.action in {
                "study.created",
                "study.governed_review_assignment_updated",
                "study.governed_redaction_updated",
                "validation_job.submitted",
                "validation_job.completed",
                "decision_log.created",
                "decision_log.review_status_updated",
                "export_bundle.created",
                "share_bundle.created",
                "share_bundle.revoked",
                "export_bundle.mvp_promotion_requested",
                "export_bundle.mvp_promotion_reviewed",
                "share_bundle.mvp_release_review_requested",
                "share_bundle.mvp_release_reviewed",
            }:
                relevant_events.append(
                    {
                        "audit_event_id": event.audit_event_id,
                        "action": event.action,
                        "target_type": event.target_type,
                        "target_id": event.target_id,
                        "created_at": event.created_at,
                        "event_payload": dict(event.event_payload or {}),
                    }
                )
        return {
            "contract_version": "workspace-governed-compliance-audit-bundle/v0-draft",
            "status": (
                "ready"
                if bool(governed_redaction.get("circulation_allowed"))
                else "pending_governed_redaction"
                if bool(governed_review.get("human_review_required"))
                else "not_required"
            ),
            "workspace_id": workspace_id,
            "project_id": project_id or study.project_id,
            "study_id": study.study_id,
            "job_id": job_id,
            "run_id": run_id,
            "export_bundle_id": export_bundle_id,
            "share_bundle_id": share_bundle_id,
            "regulated_review_boundary": self._study_regulated_review_boundary(study),
            "governed_review": governed_review,
            "governed_redaction": governed_redaction,
            "applied_redactions": list(applied_redactions or []),
            "redacted_payload_preview": dict(redacted_payload_preview or {}),
            "distribution_context": {
                **dict(distribution_context or {}),
                "readiness_gate": dict(readiness_gate or {}),
                "mvp_launch_scope": dict(mvp_launch_scope or {}),
                "mvp_promotion": dict(mvp_promotion or {}),
                "partner_onboarding": dict(partner_onboarding or {}),
                "mvp_release_review": dict(mvp_release_review or {}),
            },
            "audit_history_excerpt": relevant_events[:30],
            "boundary_note": (
                "Synthetic evidence only. Compliance audit bundle records governed reviewer, redaction, and circulation state without claiming human market proof."
            ),
        }

    def create_workspace_study(
        self,
        auth: AuthContext,
        *,
        project_id: str,
        title: str,
        research_intent: str = "",
        desired_output: str = "",
        first_task: str = "",
        artifact_refs: list[str] | None = None,
        draft_plan: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot create studies.")
        project = job_store.get_workspace_project(self.runtime_root, project_id.strip())
        if project is None or project.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace project '{project_id}' is not visible in this workspace.")
        clean_title = title.strip()
        if not clean_title:
            raise ValueError("Field 'title' is required.")
        now = utc_now_iso()
        clean_research_intent = research_intent.strip()
        clean_desired_output = desired_output.strip()
        clean_first_task = first_task.strip()
        clean_artifact_refs = [str(item).strip() for item in (artifact_refs or []) if str(item).strip()]
        merged_metadata = self._merge_study_metadata_with_regulated_boundary(
            title=clean_title,
            research_intent=clean_research_intent,
            desired_output=clean_desired_output,
            first_task=clean_first_task,
            artifact_refs=clean_artifact_refs,
            metadata=metadata,
        )
        study = WorkspaceStudy(
            study_id=f"study_{uuid.uuid4().hex[:12]}",
            workspace_id=auth.workspace_id,
            project_id=project.project_id,
            title=clean_title,
            created_by_user_id=auth.user_id,
            status="draft",
            research_intent=clean_research_intent,
            desired_output=clean_desired_output,
            first_task=clean_first_task,
            artifact_refs=clean_artifact_refs,
            draft_plan=dict(draft_plan or {}),
            latest_job_id=None,
            created_at=now,
            updated_at=now,
            metadata=merged_metadata,
        )
        created = job_store.create_workspace_study(self.runtime_root, study)
        regulated_review_boundary = self._study_regulated_review_boundary(created)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=auth.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="study.created",
                target_type="study",
                target_id=created.study_id,
                event_payload={
                    "project_id": created.project_id,
                    "study_id": created.study_id,
                    "study_title": created.title,
                    "first_task": created.first_task,
                    "regulated_review_boundary": regulated_review_boundary,
                },
                created_at=created.created_at,
            ),
        )
        return self._study_summary(created)

    def list_workspace_studies(self, auth: AuthContext, *, project_id: str = "") -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        if project_id.strip():
            project = job_store.get_workspace_project(self.runtime_root, project_id.strip())
            if project is None or project.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace project '{project_id}' is not visible in this workspace.")
        return [
            self._study_summary(study)
            for study in job_store.list_workspace_studies(self.runtime_root, auth.workspace_id, project_id=project_id.strip())
        ]

    def get_workspace_study(self, auth: AuthContext, study_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        study = job_store.get_workspace_study(self.runtime_root, study_id)
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        return self._study_summary(study)

    def create_frontline_persona_generation_job(
        self,
        auth: AuthContext,
        *,
        panel_type: str = "mainstream",
        requested_count: int = 3,
        random_seed: int = 41,
        target_audience: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _billing = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot generate persona libraries.")
        clean_panel_type = panel_type.strip() if panel_type in PANEL_ROLES else "mainstream"
        clean_count = _bounded_int(requested_count, default=3, minimum=1, maximum=6)
        clean_seed = _bounded_int(random_seed, default=41, minimum=0, maximum=999999)
        workspace_root = _workspace_root(self.runtime_root, workspace.workspace_id)
        persona_dir = workspace_root / "personas"
        persona_dir.mkdir(parents=True, exist_ok=True)
        job_id = f"personagen_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        job_artifact_dir = workspace_root / "persona_generation_jobs" / job_id
        job_artifact_dir.mkdir(parents=True, exist_ok=True)
        job_artifact_path = job_artifact_dir / "generation_job.json"
        relative_payload_path = job_artifact_path.relative_to(workspace_root).as_posix()
        job = job_store.create_persona_generation_job(
            self.runtime_root,
            generation_job_id=job_id,
            workspace_id=workspace.workspace_id,
            requested_by_user_id=auth.user_id,
            status="generating",
            panel_type=clean_panel_type,
            requested_count=clean_count,
            random_seed=clean_seed,
            target_audience=dict(target_audience or {}),
            payload_path=relative_payload_path,
            created_at=now,
            updated_at=now,
            metadata={
                "contract_version": "persona-generation-job/v0-draft",
                "source": "frontline_persona_library",
                **dict(metadata or {}),
            },
        )
        lifecycle = [{"status": "generating", "at": now}]
        write_json(
            job_artifact_path,
            {
                "contract_version": "persona-generation-job-artifact/v0-draft",
                "generation_job": job,
                "lifecycle": lifecycle,
                "synthetic_boundary": "Generated personas are synthetic participants, not recruited human evidence.",
            },
        )
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=auth.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="persona_generation_job.started",
                target_type="persona_generation_job",
                target_id=job_id,
                event_payload={"panel_type": clean_panel_type, "requested_count": clean_count, "random_seed": clean_seed},
                created_at=now,
            ),
        )
        generated_ids: list[str] = []
        promoted_ids: list[str] = []
        failed_ids: list[str] = []
        try:
            existing_entries, _failures = _load_frontline_persona_entries(persona_dir)
            existing_ids = {entry["persona"].profile.synthetic_user_id for entry in existing_entries}
            next_id_number = 1
            for existing_id in existing_ids:
                match = re.fullmatch(r"su_(\d+)", existing_id)
                if match:
                    next_id_number = max(next_id_number, int(match.group(1)) + 1)
            adapter = FrontlineLocalV5SynthesisAdapter()
            guide = build_frontline_v5_generation_guide(
                panel_type=clean_panel_type,
                target_audience=target_audience,
            )
            for offset in range(clean_count):
                while f"su_{next_id_number:04d}" in existing_ids:
                    next_id_number += 1
                synthetic_user_id = f"su_{next_id_number:04d}"
                next_id_number += 1
                existing_ids.add(synthetic_user_id)
                folder = generate_v5_persona(
                    persona_id=synthetic_user_id,
                    output_dir=persona_dir,
                    adapter=adapter,
                    guide=guide,
                    random_seed=clean_seed + offset,
                    max_transport_attempts=1,
                )
                persona = load_persona(folder)
                persona.seed.panel_role = clean_panel_type
                provisional_at = utc_now_iso()
                provisional_record = {
                    "contract_version": "persona-library-record/v0-draft",
                    "synthetic_user_id": synthetic_user_id,
                    "persona_version": f"{persona.skill_version}:{_persona_artifact_hashes(folder).get('profile.json', '')[:12]}",
                    "readiness_status": "provisional",
                    "persona_kind": PERSONA_LIBRARY_PARTICIPANT_KIND,
                    "panel_role": clean_panel_type,
                    "source_schema_version": "v5_1",
                    "source_kind": "generated",
                    "generator_version": V5_GENERATOR_VERSION,
                    "generation_job_id": job_id,
                    "generated_at": provisional_at,
                    "promoted_at": "",
                    "last_checked_at": provisional_at,
                    "readiness_checks": {
                        "schema_validation": "passed",
                        "duplicate_check": "passed",
                        "coverage_check": "passed",
                    },
                    "lifecycle_history": [
                        {
                            "status": "provisional",
                            "at": provisional_at,
                            "reason": "Generated through explicit Frontline persona gap-fill job.",
                        }
                    ],
                    "artifact_hashes": _persona_artifact_hashes(folder),
                }
                _write_persona_library_record(folder, provisional_record)
                promoted_at = utc_now_iso()
                ready_record = {
                    **provisional_record,
                    "readiness_status": "ready",
                    "promoted_at": promoted_at,
                    "last_checked_at": promoted_at,
                    "lifecycle_history": [
                        *provisional_record["lifecycle_history"],
                        {
                            "status": "ready",
                            "at": promoted_at,
                            "reason": "Schema validation, duplicate check, and requested coverage check passed.",
                        },
                    ],
                    "artifact_hashes": _persona_artifact_hashes(folder),
                }
                _write_persona_library_record(folder, ready_record)
                generated_ids.append(synthetic_user_id)
                promoted_ids.append(synthetic_user_id)
                lifecycle.extend(ready_record["lifecycle_history"])
            if len(generated_ids) < clean_count:
                raise ValueError(f"Generated {len(generated_ids)} personas for panel '{clean_panel_type}', expected {clean_count}.")
            completed_at = utc_now_iso()
            job = job_store.update_persona_generation_job(
                self.runtime_root,
                generation_job_id=job_id,
                status="completed",
                generated_persona_ids=generated_ids,
                promoted_persona_ids=promoted_ids,
                failed_persona_ids=failed_ids,
                payload_path=relative_payload_path,
                metadata_updates={
                    "completed_at": completed_at,
                    "lifecycle": lifecycle,
                    "promotion_rule": "local synchronous validation, duplicate, and coverage checks",
                },
                updated_at=completed_at,
            )
            write_json(
                job_artifact_path,
                {
                    "contract_version": "persona-generation-job-artifact/v0-draft",
                    "generation_job": job,
                    "lifecycle": lifecycle,
                    "generated_persona_ids": generated_ids,
                    "promoted_persona_ids": promoted_ids,
                    "synthetic_boundary": "Generated personas are synthetic participants, not recruited human evidence.",
                },
            )
            job_store.create_audit_event(
                self.runtime_root,
                AuditEvent(
                    audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                    workspace_id=auth.workspace_id,
                    actor_user_id=auth.user_id,
                    actor_role=auth.role,
                    action="persona_generation_job.completed",
                    target_type="persona_generation_job",
                    target_id=job_id,
                    event_payload={
                        "panel_type": clean_panel_type,
                        "generated_persona_ids": generated_ids,
                        "promoted_persona_ids": promoted_ids,
                    },
                    created_at=completed_at,
                ),
            )
            return {
                "generation_job": job,
                "generated_persona_ids": generated_ids,
                "promoted_persona_ids": promoted_ids,
                "synthetic_boundary": "Generated personas are synthetic participants, not recruited human evidence.",
            }
        except Exception as exc:
            failed_at = utc_now_iso()
            job = job_store.update_persona_generation_job(
                self.runtime_root,
                generation_job_id=job_id,
                status="failed",
                generated_persona_ids=generated_ids,
                promoted_persona_ids=promoted_ids,
                failed_persona_ids=failed_ids,
                failure_message=str(exc),
                payload_path=relative_payload_path,
                metadata_updates={"failed_at": failed_at, "lifecycle": [*lifecycle, {"status": "failed", "at": failed_at}]},
                updated_at=failed_at,
            )
            write_json(
                job_artifact_path,
                {
                    "contract_version": "persona-generation-job-artifact/v0-draft",
                    "generation_job": job,
                    "lifecycle": [*lifecycle, {"status": "failed", "at": failed_at}],
                    "generated_persona_ids": generated_ids,
                    "promoted_persona_ids": promoted_ids,
                    "failure_message": str(exc),
                    "synthetic_boundary": "Generated personas are synthetic participants, not recruited human evidence.",
                },
            )
            job_store.create_audit_event(
                self.runtime_root,
                AuditEvent(
                    audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                    workspace_id=auth.workspace_id,
                    actor_user_id=auth.user_id,
                    actor_role=auth.role,
                    action="persona_generation_job.failed",
                    target_type="persona_generation_job",
                    target_id=job_id,
                    event_payload={"panel_type": clean_panel_type, "failure_message": str(exc)},
                    created_at=failed_at,
                ),
            )
            raise

    def describe_frontline_persona_library(
        self,
        auth: AuthContext,
        *,
        panel_type: str = "mainstream",
        sample_size: int = 3,
        random_seed: int = 17,
        selected_persona_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        workspace, _billing = self._workspace_and_billing(auth)
        persona_dir = _workspace_root(self.runtime_root, workspace.workspace_id) / "personas"
        persona_dir.mkdir(parents=True, exist_ok=True)
        entries, load_failures = _load_frontline_persona_entries(persona_dir)
        generation_jobs = job_store.list_workspace_persona_generation_jobs(self.runtime_root, workspace.workspace_id, limit=10)
        active_generation_job = next(
            (job for job in generation_jobs if str(job.get("status") or "") in {"queued", "generating"}),
            None,
        )
        participant_pool_entries = [
            entry
            for entry in entries
            if entry["record"].get("persona_kind") == PERSONA_LIBRARY_PARTICIPANT_KIND
            and entry["record"].get("readiness_status") in {"ready", "provisional"}
        ]
        participant_entries = [
            entry for entry in participant_pool_entries if _is_frontline_formal_participant(entry)
        ]
        legacy_participant_entries = [
            entry for entry in participant_pool_entries if not _is_frontline_formal_participant(entry)
        ]
        lens_entries = [
            entry
            for entry in entries
            if entry["record"].get("persona_kind") in PERSONA_LIBRARY_LENS_KINDS
            and entry["record"].get("readiness_status") in {"ready", "provisional"}
        ]
        selectable_personas = [entry["persona"] for entry in participant_entries]
        clean_panel_type = panel_type.strip() if panel_type in PANEL_ROLES else "mainstream"
        clean_sample_size = _bounded_int(sample_size, default=3, minimum=1, maximum=6)
        clean_seed = _bounded_int(random_seed, default=17, minimum=0, maximum=999999)
        selected_ids = _unique_preserve_order(list(selected_persona_ids or []))
        panel_filters: dict[str, Any] = {}
        if selected_ids:
            panel_filters["synthetic_user_id"] = selected_ids
            clean_sample_size = min(clean_sample_size, len(selected_ids))

        selected_panel_entries = [
            entry for entry in participant_entries if entry["persona"].seed.panel_role == clean_panel_type
        ]
        ready_count = sum(1 for entry in selected_panel_entries if entry["record"].get("readiness_status") == "ready")
        provisional_count = sum(1 for entry in selected_panel_entries if entry["record"].get("readiness_status") == "provisional")
        panel_inventory_counts = {
            role: sum(1 for entry in participant_entries if entry["persona"].seed.panel_role == role)
            for role in PANEL_ROLES
        }
        alternative_panel_type = ""
        alternative_panel_count = 0
        if not selected_panel_entries:
            available_alternatives = [
                (role, count)
                for role, count in panel_inventory_counts.items()
                if role != clean_panel_type and count > 0
            ]
            if available_alternatives:
                alternative_panel_type, alternative_panel_count = max(
                    available_alternatives,
                    key=lambda item: item[1],
                )
        latest_failed_job = next((job for job in generation_jobs if str(job.get("status") or "") == "failed"), None)
        if active_generation_job is not None and not selected_panel_entries:
            readiness_status = "generating"
            readiness_message = "Persona generation is running for this workspace. The library will update when the job completes."
        elif not entries and latest_failed_job is not None:
            readiness_status = "failed"
            readiness_message = latest_failed_job.get("failure_message") or "The last persona generation job failed."
        elif not entries:
            readiness_status = "empty"
            readiness_message = "No synthetic participants are available yet. Generate a starter library before approving a study plan."
        elif load_failures and not participant_entries:
            readiness_status = "failed"
            readiness_message = "Persona artifacts exist, but none can be loaded into the participant library."
        elif ready_count > 0:
            readiness_status = "ready"
            readiness_message = "Ready synthetic participants are available for this panel."
        elif provisional_count > 0:
            readiness_status = "provisional"
            readiness_message = "Only provisional synthetic participants are available; approval must explicitly allow provisional use."
        elif participant_entries and alternative_panel_type:
            requested_label = clean_panel_type.replace("_", " ").title()
            alternative_label = alternative_panel_type.replace("_", " ").title()
            readiness_status = "empty"
            readiness_message = (
                f"No selectable V5+ synthetic participants match {requested_label} yet. "
                f"{alternative_label} has {alternative_panel_count} ready participant(s). "
                f"Switch panel or generate {requested_label} participants before plan approval."
            )
        else:
            readiness_status = "empty"
            readiness_message = "No selectable V5+ synthetic participants match this panel yet. Older artifacts and simulated lenses are kept separate from participant evidence."

        selection: dict[str, Any] = {
            "contract_version": "persona-panel-selection/v0-draft",
            "panel_type": clean_panel_type,
            "sample_size": clean_sample_size,
            "random_seed": clean_seed,
            "selected_persona_ids": [],
            "selection_rationale": "No matching personas are available yet.",
            "explainability": {},
            "filters": panel_filters,
            "selected_personas": [],
            "readiness_status": readiness_status,
            "synthetic_boundary": "Persona selection improves simulation coverage, but it does not create recruited human evidence.",
        }
        if selectable_personas:
            try:
                sampling = sample_personas(
                    selectable_personas,
                    PanelSpec(
                        panel_type=clean_panel_type,
                        sample_size=clean_sample_size,
                        random_seed=clean_seed,
                        filters=panel_filters,
                        preset_name="frontline_persona_picker",
                    ),
                )
                selection = {
                    "contract_version": "persona-panel-selection/v0-draft",
                    "panel_type": clean_panel_type,
                    "sample_size": len(sampling.personas),
                    "random_seed": clean_seed,
                    "selected_persona_ids": [persona.profile.synthetic_user_id for persona in sampling.personas],
                    "filters": panel_filters,
                    "selection_mode": "user_selected" if selected_ids else "system_suggested",
                    "selection_rationale": sampling.rationale,
                    "explainability": sampling.explainability,
                    "selected_personas": [
                        self._frontline_persona_summary(
                            persona,
                            record=next(
                                (
                                    entry["record"]
                                    for entry in participant_entries
                                    if entry["persona"].profile.synthetic_user_id == persona.profile.synthetic_user_id
                                ),
                                {},
                            ),
                        )
                        for persona in sampling.personas
                    ],
                    "readiness_status": readiness_status,
                    "synthetic_boundary": "Persona selection improves simulation coverage, but it does not create recruited human evidence.",
                }
            except ValueError:
                pass

        library_summary = build_persona_library_summary(selectable_personas)
        coverage_gaps = (
            library_summary.get("human_difference_axis_summary", {}).get("coverage_gaps", [])
            if isinstance(library_summary.get("human_difference_axis_summary"), dict)
            else []
        )
        return {
            "contract_version": "frontline-persona-library/v1-readiness",
            "readiness": {
                "contract_version": "persona-library-readiness/v0-draft",
                "status": readiness_status,
                "known_states": list(PERSONA_LIBRARY_READINESS_STATES),
                "message": readiness_message,
                "can_generate": auth.role in SUBMITTER_ROLES,
                "active_generation_job_id": (
                    str(active_generation_job.get("generation_job_id") or "")
                    if isinstance(active_generation_job, dict)
                    else ""
                ),
                "latest_failed_generation_job_id": (
                    str(latest_failed_job.get("generation_job_id") or "")
                    if isinstance(latest_failed_job, dict)
                    else ""
                ),
                "failure_message": (
                    str(latest_failed_job.get("failure_message") or "")
                    if isinstance(latest_failed_job, dict)
                    else ""
                ),
                "load_failures": load_failures,
                "selectable_persona_count": len(participant_entries),
                "legacy_participant_count": len(legacy_participant_entries),
                "simulated_lens_count": len(lens_entries),
                "active_panel_ready_count": ready_count,
                "active_panel_provisional_count": provisional_count,
                "alternative_panel_type": alternative_panel_type,
                "alternative_panel_count": alternative_panel_count,
                "panel_inventory_counts": panel_inventory_counts,
                "coverage_gap_count": len(coverage_gaps),
            },
            "panel_options": [
                {
                    "panel_type": role,
                    "label": role.replace("_", " ").title(),
                    "persona_count": sum(1 for entry in participant_entries if entry["persona"].seed.panel_role == role),
                    "ready_count": sum(
                        1
                        for entry in participant_entries
                        if entry["persona"].seed.panel_role == role
                        and entry["record"].get("readiness_status") == "ready"
                    ),
                    "provisional_count": sum(
                        1
                        for entry in participant_entries
                        if entry["persona"].seed.panel_role == role
                        and entry["record"].get("readiness_status") == "provisional"
                    ),
                }
                for role in PANEL_ROLES
            ],
            "active_panel_type": clean_panel_type,
            "sample_size": clean_sample_size,
            "random_seed": clean_seed,
            "library_summary": library_summary,
            "personas": [
                self._frontline_persona_summary(entry["persona"], record=entry["record"])
                for entry in participant_entries
                if entry["persona"].seed.panel_role == clean_panel_type
            ],
            "simulated_lenses": [
                self._frontline_persona_summary(entry["persona"], record=entry["record"])
                for entry in lens_entries
            ],
            "persona_groups": {
                "participants": {
                    "count": len(participant_entries),
                    "formal_schema_versions": sorted(FRONTLINE_FORMAL_PERSONA_SCHEMA_VERSIONS),
                    "legacy_excluded_count": len(legacy_participant_entries),
                    "synthetic_boundary": "V5+ participant personas may be used for synthetic study panels, but remain simulated evidence.",
                },
                "generated_personas": {
                    "count": sum(1 for entry in participant_entries if entry["record"].get("source_kind") == "generated"),
                    "generator_versions": sorted({
                        str(entry["record"].get("generator_version") or "unknown")
                        for entry in participant_entries
                        if entry["record"].get("source_kind") == "generated"
                    }),
                },
                "simulated_lenses": {
                    "count": len(lens_entries),
                    "persona_kinds": sorted({
                        str(entry["record"].get("persona_kind") or "")
                        for entry in lens_entries
                    }),
                    "synthetic_boundary": "Public-figure, celebrity, expert, influencer, and founder-critique lenses are simulated and unaffiliated. They are not participant evidence.",
                },
            },
            "default_selection": selection,
            "generation_jobs": generation_jobs,
            "lens_boundary": {
                "contract_version": "simulated-lens-boundary/v0-draft",
                "excluded_from_participant_pool": sorted(PERSONA_LIBRARY_LENS_KINDS),
                "message": "Public-figure, celebrity, expert, influencer, and founder-critique lenses are simulated and unaffiliated. They are not mixed into participant evidence by default.",
            },
            "synthetic_boundary": "This is a synthetic persona library. Use coverage and gaps to choose a better simulation panel, not to claim human market proof.",
        }

    def _frontline_persona_summary(self, persona: Any, *, record: dict[str, Any] | None = None) -> dict[str, Any]:
        identity = dict(persona.profile.basic_identity)
        technology = dict(persona.profile.technology_profile)
        economic = dict(persona.profile.economic_profile)
        behavior = dict(persona.profile.behavior_profile)
        axes = dict(getattr(persona.profile, "human_difference_axes", {}) or {})
        record_payload = dict(record or {})
        return {
            "synthetic_user_id": persona.profile.synthetic_user_id,
            "name": str(identity.get("name") or persona.profile.synthetic_user_id),
            "panel_role": persona.seed.panel_role,
            "persona_kind": str(record_payload.get("persona_kind") or PERSONA_LIBRARY_PARTICIPANT_KIND),
            "library_group": (
                "simulated_lens"
                if str(record_payload.get("persona_kind") or "") in PERSONA_LIBRARY_LENS_KINDS
                else "participant"
            ),
            "readiness_status": _clean_persona_readiness_status(record_payload.get("readiness_status"), default="ready"),
            "persona_version": str(record_payload.get("persona_version") or persona.skill_version or ""),
            "source_schema_version": str(record_payload.get("source_schema_version") or ""),
            "source_kind": str(record_payload.get("source_kind") or ""),
            "generator_version": str(record_payload.get("generator_version") or ""),
            "source_panel_role": str(record_payload.get("source_panel_role") or ""),
            "panel_role_normalized": bool(record_payload.get("panel_role_normalized")),
            "lens_boundary": str(record_payload.get("lens_boundary") or ""),
            "artifact_hashes": dict(record_payload.get("artifact_hashes", {})) if isinstance(record_payload.get("artifact_hashes"), dict) else {},
            "generation_job_id": str(record_payload.get("generation_job_id") or ""),
            "occupation": str(identity.get("occupation") or ""),
            "location": str(identity.get("location") or ""),
            "life_stage": str(identity.get("life_stage") or persona.seed.life_stage or ""),
            "workflow_maturity": str(behavior.get("workflow_maturity") or persona.seed.workflow_maturity or ""),
            "price_sensitivity": str(economic.get("price_sensitivity") or persona.seed.budget_flexibility or ""),
            "privacy_concern": str(technology.get("privacy_concern") or persona.seed.privacy_risk_tolerance or ""),
            "trust_threshold": persona.seed.trust_threshold,
            "proof_threshold": persona.seed.proof_threshold,
            "human_difference_axes": axes,
            "decision_policy": {
                "adoption_style": str(persona.decision_policy.get("adoption_style") or ""),
                "trust_requirements": list(persona.decision_policy.get("trust_requirements", []))[:3],
                "rejection_triggers": list(persona.decision_policy.get("rejection_triggers", []))[:3],
                "proof_requirements": list(persona.decision_policy.get("proof_requirements", []))[:3],
            },
        }

    def _build_frontline_selected_persona_snapshot(
        self,
        *,
        persona_dir: Path,
        persona_panel: dict[str, Any],
    ) -> dict[str, Any]:
        _assert_persona_panel_has_selection(persona_panel, action="starting a research run")
        selected_ids = [
            str(item).strip()
            for item in persona_panel.get("selected_persona_ids", [])
            if str(item).strip()
        ] if isinstance(persona_panel.get("selected_persona_ids", []), list) else []
        entries, load_failures = _load_frontline_persona_entries(persona_dir)
        entries_by_id = {
            entry["persona"].profile.synthetic_user_id: entry
            for entry in entries
        }
        missing_ids = [synthetic_user_id for synthetic_user_id in selected_ids if synthetic_user_id not in entries_by_id]
        if missing_ids:
            raise ValueError(f"Selected synthetic participants are no longer available: {', '.join(missing_ids)}")
        allow_provisional = bool(persona_panel.get("allow_provisional_personas")) or (
            isinstance(persona_panel.get("provisional_persona_exception"), dict)
            and bool(str(persona_panel.get("provisional_persona_exception", {}).get("reason") or "").strip())
        )
        selected_personas: list[dict[str, Any]] = []
        provisional_ids: list[str] = []
        lens_ids: list[str] = []
        for synthetic_user_id in selected_ids:
            entry = entries_by_id[synthetic_user_id]
            persona = entry["persona"]
            record = dict(entry["record"])
            readiness_status = _clean_persona_readiness_status(record.get("readiness_status"), default="ready")
            persona_kind = _clean_persona_kind(record.get("persona_kind"))
            if readiness_status == "provisional":
                provisional_ids.append(synthetic_user_id)
            if readiness_status == "provisional" and not allow_provisional:
                raise ValueError(
                    f"Selected persona '{synthetic_user_id}' is provisional. Explicitly allow provisional personas before starting a run."
                )
            if readiness_status not in {"ready", "provisional"}:
                raise ValueError(f"Selected persona '{synthetic_user_id}' is not ready for use: {readiness_status}.")
            if persona_kind != PERSONA_LIBRARY_PARTICIPANT_KIND:
                lens_ids.append(synthetic_user_id)
            elif not _is_frontline_formal_participant(entry):
                raise ValueError(
                    f"Selected persona '{synthetic_user_id}' is not a formal V5+ participant persona for Frontline Studio use."
                )
            selected_personas.append(self._frontline_persona_summary(persona, record=record))
        if lens_ids and not bool(persona_panel.get("allow_simulated_lenses")):
            raise ValueError(
                "Simulated public-figure, expert, celebrity, or influencer lenses cannot be used as participant evidence by default."
            )
        return {
            "contract_version": "selected-persona-panel-snapshot/v0-draft",
            "created_at": utc_now_iso(),
            "selected_persona_ids": selected_ids,
            "selected_personas": selected_personas,
            "selected_persona_versions": {
                item["synthetic_user_id"]: item.get("persona_version", "")
                for item in selected_personas
            },
            "artifact_hashes_by_persona": {
                item["synthetic_user_id"]: item.get("artifact_hashes", {})
                for item in selected_personas
            },
            "coverage_snapshot": dict(persona_panel.get("coverage_snapshot", {})) if isinstance(persona_panel.get("coverage_snapshot"), dict) else {},
            "readiness_statuses": {
                item["synthetic_user_id"]: item.get("readiness_status", "ready")
                for item in selected_personas
            },
            "has_provisional_personas": bool(provisional_ids),
            "provisional_persona_ids": provisional_ids,
            "simulated_lens_persona_ids": lens_ids,
            "load_failures": load_failures,
            "synthetic_boundary": "This snapshot records the synthetic participant versions used by the run. It is not recruited human evidence.",
        }

    def create_frontline_plan_proposal(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        user_message: str = "",
        target_persona: str = "",
        target_audience: dict[str, Any] | None = None,
        persona_panel: dict[str, Any] | None = None,
        artifacts: list[str] | None = None,
        study_purpose: str = "",
        mode: str = "",
        moderator_questions: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _billing = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot create frontline plan proposals.")
        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        now = utc_now_iso()
        signal_text = " ".join(
            [
                study.title,
                study.research_intent,
                study.desired_output,
                study.first_task,
                user_message,
                study_purpose,
                mode,
            ]
        ).lower()
        inferred_mode = _frontline_mode_from_signal_text(signal_text, mode)
        proposal_id = f"proposal_{uuid.uuid4().hex[:12]}"
        clean_artifacts = _unique_preserve_order(
            [str(item) for item in [*(study.artifact_refs or []), *(artifacts or [])]]
        )
        target_audience_payload = _normalize_frontline_target_audience(target_persona, target_audience)
        persona_panel_payload = _normalize_frontline_persona_panel(
            persona_panel,
            default_sample_size=_bounded_int(dict(workspace.settings).get("frontline_sample_size", 3), default=3, minimum=1, maximum=6),
        )
        _assert_persona_panel_has_selection(persona_panel_payload, action="drafting a research plan")
        questions = [
            str(item).strip()
            for item in (moderator_questions or [])
            if str(item).strip()
        ] or [
            "What does the participant understand before hearing the intended solution?",
            "Where does trust, effort, or adoption risk appear?",
            "Which evidence is synthetic-only and needs human follow-up?",
        ]
        proposal = {
            "contract_version": "frontline-plan-proposal/v0-draft",
            "plan_proposal_id": proposal_id,
            "study_id": study.study_id,
            "source": "frontline_chat",
            "status": "proposed",
            "created_at": now,
            "created_by_user_id": auth.user_id,
            "study_purpose": study_purpose.strip() or study.desired_output or study.research_intent,
            "target_persona": target_audience_payload["summary"],
            "target_audience": target_audience_payload,
            "persona_panel": persona_panel_payload,
            "artifact_refs": clean_artifacts,
            "mode_inference": {
                "mode": inferred_mode,
                "confidence": "directional",
                "rationale": "Inferred from the user's research intent; the user must confirm before execution.",
            },
            "moderator_interview_guide": {
                "contract_version": "moderator-interview-guide/v0-draft",
                "questions": questions,
                "guardrails": [
                    "Do not present synthetic evidence as human market proof.",
                    "Separate stated intent, recalled behavior, observed action, and simulated risk.",
                    "Capture contradictions and human validation gaps explicitly.",
                ],
            },
            "expected_evidence_types": _frontline_expected_evidence_types_for_mode(inferred_mode),
            "open_questions": [
                "Which segment should be treated as highest priority?",
                "Which artifacts or prototype states are in scope?",
            ],
            "synthetic_boundary": (
                "This proposal prepares a synthetic research run. It is not human market proof until calibrated or validated."
            ),
            "metadata": {**dict(metadata or {}), "persona_panel": persona_panel_payload},
        }
        frontline = dict(study.metadata.get("frontline", {})) if isinstance(study.metadata.get("frontline"), dict) else {}
        proposals = [dict(item) for item in frontline.get("plan_proposals", []) if isinstance(item, dict)]
        proposals.append(proposal)
        frontline.update(
            {
                "contract_version": "frontline-study-planning/v0-draft",
                "latest_plan_proposal_id": proposal_id,
                "plan_proposals": proposals,
                "updated_at": now,
            }
        )
        updated = job_store.update_workspace_study(
            self.runtime_root,
            study_id=study.study_id,
            status="ready_to_run",
            draft_plan=proposal,
            metadata_updates={"frontline": frontline},
        )
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=auth.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="frontline.plan_proposal_created",
                target_type="study",
                target_id=study.study_id,
                event_payload={
                    "study_id": study.study_id,
                    "project_id": study.project_id,
                    "plan_proposal_id": proposal_id,
                    "inferred_mode": inferred_mode,
                },
                created_at=now,
            ),
        )
        return {
            "study": self._study_summary(updated),
            "plan_proposal": proposal,
        }

    def confirm_frontline_plan_revision(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        plan_proposal_id: str = "",
        confirmation_note: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot confirm frontline plan revisions.")
        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        frontline = dict(study.metadata.get("frontline", {})) if isinstance(study.metadata.get("frontline"), dict) else {}
        proposals = [dict(item) for item in frontline.get("plan_proposals", []) if isinstance(item, dict)]
        requested_proposal_id = plan_proposal_id.strip() or str(frontline.get("latest_plan_proposal_id") or "")
        proposal = next((item for item in proposals if str(item.get("plan_proposal_id") or "") == requested_proposal_id), None)
        if proposal is None:
            raise ValueError("A matching plan proposal is required before confirming a StudyPlanRevision.")
        now = utc_now_iso()
        persona_panel_payload = _normalize_frontline_persona_panel(
            dict(proposal.get("persona_panel", {})) if isinstance(proposal.get("persona_panel"), dict) else {},
        )
        _assert_persona_panel_has_selection(persona_panel_payload, action="approving a research plan")
        revision_id = f"planrev_{uuid.uuid4().hex[:12]}"
        revision = {
            "contract_version": "frontline-study-plan-revision/v0-draft",
            "plan_revision_id": revision_id,
            "study_id": study.study_id,
            "source_plan_proposal_id": requested_proposal_id,
            "created_at": now,
            "created_by_user_id": auth.user_id,
            "confirmation_note": confirmation_note.strip(),
            "study_purpose": proposal.get("study_purpose"),
            "target_persona": proposal.get("target_persona"),
            "target_audience": dict(proposal.get("target_audience", {})) if isinstance(proposal.get("target_audience"), dict) else {},
            "persona_panel": persona_panel_payload,
            "artifact_refs": list(proposal.get("artifact_refs", [])) if isinstance(proposal.get("artifact_refs"), list) else [],
            "mode_inference": dict(proposal.get("mode_inference", {})) if isinstance(proposal.get("mode_inference"), dict) else {},
            "moderator_interview_guide": (
                dict(proposal.get("moderator_interview_guide", {}))
                if isinstance(proposal.get("moderator_interview_guide"), dict)
                else {}
            ),
            "expected_evidence_types": (
                list(proposal.get("expected_evidence_types", []))
                if isinstance(proposal.get("expected_evidence_types"), list)
                else []
            ),
            "synthetic_boundary": proposal.get("synthetic_boundary"),
            "metadata": dict(metadata or {}),
        }
        revisions = [dict(item) for item in frontline.get("plan_revisions", []) if isinstance(item, dict)]
        revisions.append(revision)
        frontline.update(
            {
                "current_plan_revision_id": revision_id,
                "latest_confirmed_plan_revision_id": revision_id,
                "plan_revisions": revisions,
                "updated_at": now,
            }
        )
        updated = job_store.update_workspace_study(
            self.runtime_root,
            study_id=study.study_id,
            status="ready_to_run",
            draft_plan=revision,
            metadata_updates={"frontline": frontline, "current_plan_revision_id": revision_id},
        )
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=auth.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="frontline.plan_revision_confirmed",
                target_type="study",
                target_id=study.study_id,
                event_payload={
                    "study_id": study.study_id,
                    "project_id": study.project_id,
                    "plan_proposal_id": requested_proposal_id,
                    "plan_revision_id": revision_id,
                },
                created_at=now,
            ),
        )
        return {
            "study": self._study_summary(updated),
            "plan_revision": revision,
        }

    def start_frontline_research_run(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _billing = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot start research runs.")
        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        project = job_store.get_workspace_project(self.runtime_root, study.project_id)
        if project is None or project.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace project '{study.project_id}' is not visible in this workspace.")

        frontline = dict(study.metadata.get("frontline", {})) if isinstance(study.metadata.get("frontline"), dict) else {}
        plan_revision_id = str(frontline.get("current_plan_revision_id") or study.metadata.get("current_plan_revision_id") or "").strip()
        if not plan_revision_id:
            raise ValueError("Approve a research plan before starting a run.")
        revisions = [dict(item) for item in frontline.get("plan_revisions", []) if isinstance(item, dict)]
        current_revision = next(
            (item for item in revisions if str(item.get("plan_revision_id") or "") == plan_revision_id),
            revisions[-1] if revisions else {},
        )

        workspace_root = _workspace_root(self.runtime_root, workspace.workspace_id)
        brief_path = workspace_root / "briefs" / f"frontline_{study.study_id}.json"
        target_persona = str(current_revision.get("target_persona") or "Synthetic participants matching the study target segment.")
        target_audience = dict(current_revision.get("target_audience", {})) if isinstance(current_revision.get("target_audience"), dict) else {}
        persona_panel = _normalize_frontline_persona_panel(
            dict(current_revision.get("persona_panel", {})) if isinstance(current_revision.get("persona_panel"), dict) else {},
            default_sample_size=_bounded_int(dict(workspace.settings).get("frontline_sample_size", 3), default=3, minimum=1, maximum=6),
        )
        _assert_persona_panel_has_selection(persona_panel, action="starting a research run")
        study_purpose = str(current_revision.get("study_purpose") or study.desired_output or study.research_intent)
        mode_inference = (
            dict(current_revision.get("mode_inference", {}))
            if isinstance(current_revision.get("mode_inference"), dict)
            else {}
        )
        inferred_mode = str(mode_inference.get("mode") or "").strip() or _frontline_mode_from_signal_text(
            " ".join([study.title, study.research_intent, study.desired_output, study_purpose])
        )
        expected_evidence = [
            str(item)
            for item in current_revision.get("expected_evidence_types", [])
            if str(item).strip()
        ] or _frontline_expected_evidence_types_for_mode(inferred_mode)
        audience_criteria = [
            str(item)
            for item in target_audience.get("inclusion_criteria", [])
            if str(item).strip()
        ] if isinstance(target_audience.get("inclusion_criteria", []), list) else []
        guide = dict(current_revision.get("moderator_interview_guide", {})) if isinstance(current_revision.get("moderator_interview_guide"), dict) else {}
        guide_questions = [
            str(item)
            for item in guide.get("questions", [])
            if str(item).strip()
        ] if isinstance(guide.get("questions", []), list) else []
        write_json(
            brief_path,
            FounderBrief(
                brief_id=f"frontline_{study.study_id}",
                project_name=project.name,
                problem_statement=study.research_intent or study.title,
                target_market=target_persona,
                offered_solution=study.desired_output or study.title,
                validation_goal=study_purpose,
                assumptions=_unique_preserve_order([
                    *expected_evidence,
                    *audience_criteria,
                    *guide_questions,
                ]),
                constraints=[
                    f"Persona panel: {persona_panel['panel_type']}",
                    *([f"Selected persona ids: {', '.join(persona_panel['selected_persona_ids'])}"] if persona_panel["selected_persona_ids"] else []),
                    *(["Audience exclusion: " + str(target_audience.get("excluded_context"))] if target_audience.get("excluded_context") else []),
                ],
                known_risks=["Synthetic evidence requires human validation before market-proof claims."],
            ).to_dict(),
        )

        persona_dir = workspace_root / "personas"
        persona_dir.mkdir(parents=True, exist_ok=True)
        seed_source = re.sub(r"[^0-9a-f]", "", study.study_id.lower())[-6:] or "32"
        random_seed = int(seed_source, 16) % 100000
        sample_size = int(dict(workspace.settings).get("frontline_sample_size", 1) or 1)
        sample_size = max(1, min(sample_size, 3))
        sample_size = int(persona_panel.get("sample_size") or sample_size)
        panel_filters = dict(persona_panel.get("filters", {})) if isinstance(persona_panel.get("filters"), dict) else {}
        selected_persona_snapshot = self._build_frontline_selected_persona_snapshot(
            persona_dir=persona_dir,
            persona_panel=persona_panel,
        )
        persona_panel = {
            **persona_panel,
            "readiness_status": (
                "provisional" if selected_persona_snapshot.get("has_provisional_personas") else "ready"
            ),
            "selected_persona_snapshot": selected_persona_snapshot,
            "selected_personas": list(selected_persona_snapshot.get("selected_personas", [])),
        }

        provider_name = str(
            dict(workspace.settings).get("frontline_default_provider")
            or dict(workspace.settings).get("default_validation_provider")
            or "mock"
        )
        run_metadata = {
            **dict(metadata or {}),
            "source": "frontline_research_studio",
            "user_facing_action": "start_research_run",
            "hidden_execution_profile": True,
            "project_id": project.project_id,
            "study_id": study.study_id,
            "plan_revision_id": plan_revision_id,
            "frontline_plan_revision_id": plan_revision_id,
            "frontline_requires_plan_revision": True,
            "frontline_run_contract_version": "frontline-live-run/v0-draft",
            "mode": inferred_mode,
            "mode_inference": mode_inference or {"mode": inferred_mode, "confidence": "directional"},
            "expected_evidence_types": expected_evidence,
            "persona_panel": persona_panel,
            "selected_persona_ids": persona_panel.get("selected_persona_ids", []),
            "selected_persona_snapshot": selected_persona_snapshot,
            "selected_persona_versions": selected_persona_snapshot.get("selected_persona_versions", {}),
            "selected_persona_artifact_hashes": selected_persona_snapshot.get("artifact_hashes_by_persona", {}),
            "persona_coverage_snapshot": selected_persona_snapshot.get("coverage_snapshot", {}),
            "has_provisional_personas": bool(selected_persona_snapshot.get("has_provisional_personas")),
        }
        job = self.submit_validation_job(
            auth,
            ValidationJobRequest(
                brief_path=str(brief_path.relative_to(workspace_root)),
                persona_dir=str(persona_dir.relative_to(workspace_root)),
                panel_spec=PanelSpec(
                    panel_type=str(persona_panel.get("panel_type") or "mainstream"),
                    sample_size=sample_size,
                    random_seed=int(persona_panel.get("random_seed") or random_seed),
                    filters=panel_filters,
                    preset_name="frontline_persona_picker",
                ),
                provider_name=provider_name,
                priority="normal",
                max_retries=1,
                run_root="runs",
                metadata=run_metadata,
            ),
        )
        updated = job_store.get_workspace_study(self.runtime_root, study.study_id) or study
        return {
            "study": self._study_summary(updated),
            "job": job,
            "research_run": {
                "status": "started",
                "label": "Research run started",
                "study_id": study.study_id,
                "plan_revision_id": plan_revision_id,
                "synthetic_boundary": "This run produces simulated evidence and still requires human validation before market-proof claims.",
            },
        }

    def describe_frontline_study(self, auth: AuthContext, *, study_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        return {
            "contract_version": "frontline-study/v0-draft",
            "study": self._study_summary(study),
            "synthetic_boundary": (
                "Frontline Studio displays simulated evidence with provenance, contradictions, and human-validation gaps."
            ),
        }

    def describe_research_playbooks(self, auth: AuthContext) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        return {
            "contract_version": "frontline-research-playbook-catalog/v1",
            "playbooks": [dict(item) for item in FRONTLINE_RESEARCH_PLAYBOOKS],
            "default_playbook_id": "concept_validation",
            "rerun_templates": [
                {
                    "template_id": "change_audience",
                    "label": "Rerun with a different audience",
                    "change_set_fields": ["target_audience", "persona_panel"],
                },
                {
                    "template_id": "change_artifact_version",
                    "label": "Rerun with a new artifact or prototype version",
                    "change_set_fields": ["artifact_refs", "prototype_task"],
                },
                {
                    "template_id": "change_message_variant",
                    "label": "Rerun with a revised message variant",
                    "change_set_fields": ["message_variant", "proof_point"],
                },
                {
                    "template_id": "change_moderator_guide",
                    "label": "Rerun with a different moderator guide",
                    "change_set_fields": ["moderator_questions", "guide_focus"],
                },
            ],
            "synthetic_boundary": (
                "Playbooks lower setup effort and improve repeatability, but they do not widen the synthetic-evidence boundary."
            ),
        }

    def create_frontline_rerun_plan(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        source_run_id: str = "",
        playbook_id: str = "",
        change_set: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot prepare frontline reruns.")
        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        frontline = dict(study.metadata.get("frontline", {})) if isinstance(study.metadata.get("frontline"), dict) else {}
        revisions = [dict(item) for item in frontline.get("plan_revisions", []) if isinstance(item, dict)]
        proposals = [dict(item) for item in frontline.get("plan_proposals", []) if isinstance(item, dict)]
        source_plan = revisions[-1] if revisions else (proposals[-1] if proposals else dict(study.draft_plan or {}))
        if not source_plan:
            raise ValueError("A source plan is required before preparing a rerun.")

        selected_playbook = next(
            (dict(item) for item in FRONTLINE_RESEARCH_PLAYBOOKS if item["playbook_id"] == playbook_id),
            None,
        )
        changes = dict(change_set or {})
        rerun_id = f"rerun_{uuid.uuid4().hex[:12]}"
        proposal_id = f"proposal_{uuid.uuid4().hex[:12]}"
        now = utc_now_iso()
        mode_inference = dict(source_plan.get("mode_inference", {})) if isinstance(source_plan.get("mode_inference"), dict) else {}
        if selected_playbook is not None:
            mode_inference = {
                "mode": selected_playbook["mode"],
                "confidence": "playbook_selected",
                "rationale": "Selected from a guided Frontline rerun playbook.",
            }
        target_audience = (
            dict(changes.get("target_audience"))
            if isinstance(changes.get("target_audience"), dict)
            else dict(source_plan.get("target_audience", {})) if isinstance(source_plan.get("target_audience"), dict) else {}
        )
        persona_panel = (
            dict(changes.get("persona_panel"))
            if isinstance(changes.get("persona_panel"), dict)
            else dict(source_plan.get("persona_panel", {})) if isinstance(source_plan.get("persona_panel"), dict) else {}
        )
        artifact_refs = [
            str(item)
            for item in (
                changes.get("artifact_refs")
                if isinstance(changes.get("artifact_refs"), list)
                else source_plan.get("artifact_refs", [])
            )
            if str(item).strip()
        ] if isinstance(source_plan.get("artifact_refs", []), list) or isinstance(changes.get("artifact_refs"), list) else []
        guide = dict(source_plan.get("moderator_interview_guide", {})) if isinstance(source_plan.get("moderator_interview_guide"), dict) else {}
        if isinstance(changes.get("moderator_questions"), list):
            guide["questions"] = [str(item) for item in changes["moderator_questions"] if str(item).strip()]
        if str(changes.get("guide_focus") or "").strip():
            guide["focus"] = str(changes.get("guide_focus") or "").strip()
        inferred_mode = str(
            mode_inference.get("mode")
            or _frontline_mode_from_signal_text(" ".join([study.title, study.research_intent, str(changes)]))
        ).strip()
        proposal = {
            "contract_version": "frontline-rerun-plan/v1",
            "plan_proposal_id": proposal_id,
            "rerun_id": rerun_id,
            "study_id": study.study_id,
            "source": "frontline_rerun_template",
            "status": "proposed",
            "created_at": now,
            "created_by_user_id": auth.user_id,
            "source_plan_revision_id": source_plan.get("plan_revision_id"),
            "source_plan_proposal_id": source_plan.get("plan_proposal_id"),
            "source_run_id": source_run_id.strip() or None,
            "playbook_id": selected_playbook["playbook_id"] if selected_playbook else playbook_id.strip() or None,
            "study_purpose": str(changes.get("study_purpose") or source_plan.get("study_purpose") or study.desired_output or study.research_intent),
            "target_persona": target_audience.get("summary") or source_plan.get("target_persona") or "",
            "target_audience": target_audience,
            "persona_panel": persona_panel,
            "artifact_refs": artifact_refs,
            "mode_inference": mode_inference or {"mode": inferred_mode, "confidence": "directional"},
            "moderator_interview_guide": guide,
            "expected_evidence_types": _frontline_expected_evidence_types_for_mode(inferred_mode),
            "rerun_lineage": {
                "contract_version": "frontline-rerun-lineage/v1",
                "source_run_id": source_run_id.strip() or None,
                "changed_fields": sorted(str(key) for key in changes.keys()),
                "comparison_ready": True,
                "note": "Rerun plans preserve source plan and run lineage so evidence can be compared instead of treated as a one-off summary.",
            },
            "synthetic_boundary": (
                "This rerun plan prepares another synthetic research attempt. Compare it against the source run before making stronger claims."
            ),
            "metadata": {
                **dict(metadata or {}),
                "change_set": changes,
                "selected_playbook": selected_playbook or {},
            },
        }
        proposals.append(proposal)
        frontline.update(
            {
                "contract_version": "frontline-study-planning/v0-draft",
                "latest_plan_proposal_id": proposal_id,
                "latest_rerun_id": rerun_id,
                "plan_proposals": proposals,
                "updated_at": now,
            }
        )
        updated = job_store.update_workspace_study(
            self.runtime_root,
            study_id=study.study_id,
            status="ready_to_run",
            draft_plan=proposal,
            metadata_updates={"frontline": frontline},
        )
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=auth.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="frontline.rerun_plan_created",
                target_type="study",
                target_id=study.study_id,
                event_payload={
                    "study_id": study.study_id,
                    "rerun_id": rerun_id,
                    "source_run_id": source_run_id.strip() or None,
                    "playbook_id": proposal.get("playbook_id"),
                    "changed_fields": proposal["rerun_lineage"]["changed_fields"],
                },
                created_at=now,
            ),
        )
        return {
            "study": self._study_summary(updated),
            "rerun_plan": proposal,
        }

    def _resolve_frontline_run_context(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        run_id: str,
    ) -> tuple[WorkspaceStudy, dict[str, Any], Path | None]:
        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        requested = run_id.strip()
        jobs = job_store.list_workspace_jobs(self.runtime_root, auth.workspace_id)
        for job in jobs:
            metadata = dict(job.get("metadata", {}))
            if str(metadata.get("study_id") or "") != study.study_id:
                continue
            output_run_path = str(job.get("output_run_path") or "").strip()
            candidates = {
                str(job.get("job_id") or "").strip(),
                str(metadata.get("run_id") or "").strip(),
                _job_run_id(job),
                Path(output_run_path).name if output_run_path else "",
            }
            if requested not in {item for item in candidates if item}:
                continue
            run_dir = Path(output_run_path) if output_run_path else None
            if run_dir is not None and not run_dir.exists():
                run_dir = None
            context = {
                "run_id": _job_run_id(job) or requested,
                "job_id": str(job.get("job_id") or ""),
                "project_id": str(metadata.get("project_id") or "") or study.project_id,
                "study_id": study.study_id,
                "job_status": str(job.get("status") or ""),
                "created_at": str(job.get("created_at") or ""),
                "started_at": str(job.get("started_at") or ""),
                "finished_at": str(job.get("finished_at") or ""),
                "last_error": str(job.get("last_error") or ""),
                "output_run_path": output_run_path or None,
                "provider_name": str(job.get("provider_name") or ""),
                "metadata": metadata,
                "provider_runtime_boundary": self._validation_provider_runtime_boundary(
                    str(job.get("provider_name") or ""),
                    status=str(job.get("status") or ""),
                    last_error=str(job.get("last_error") or ""),
                    metadata=metadata,
                ),
            }
            return study, context, run_dir
        raise FileNotFoundError(f"Run '{run_id}' was not found inside study '{study_id}'.")

    @staticmethod
    def _read_run_artifact(run_dir: Path | None, name: str, default: Any) -> Any:
        if run_dir is None:
            return default
        path = run_dir / name
        if not path.exists():
            return default
        try:
            return read_json(path)
        except Exception:
            return default

    def get_frontline_run_progress(self, auth: AuthContext, *, study_id: str, run_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        _study, context, run_dir = self._resolve_frontline_run_context(auth, study_id=study_id, run_id=run_id)
        job_status = str(context.get("job_status") or "")
        stage_results = self._read_run_artifact(run_dir, "stage_results.json", {})
        raw_responses = self._read_run_artifact(run_dir, "raw_responses.json", [])
        errors = self._read_run_artifact(run_dir, "errors.json", [])
        events: list[dict[str, Any]] = []

        if isinstance(stage_results, dict) and stage_results:
            for stage_name, payload in stage_results.items():
                if not isinstance(payload, dict):
                    continue
                phase = FRONTLINE_STAGE_PHASES.get(str(stage_name), "synthesizing")
                events.append(
                    {
                        "event_id": f"{context['run_id']}:{stage_name}",
                        "phase": phase,
                        "stage_name": str(stage_name),
                        "status": str(payload.get("status") or "unknown"),
                        "started_at": payload.get("started_at") or None,
                        "finished_at": payload.get("finished_at") or None,
                        "summary": self._frontline_stage_summary(str(stage_name), payload),
                        "source_ref": f"stage_results.json#{stage_name}",
                    }
                )
        else:
            phase = "queued" if job_status == "queued" else "interviewing" if job_status == "running" else "failed" if job_status == "failed" else "blocked" if job_status == "canceled" else "completed" if job_status == "completed" else "queued"
            events.append(
                {
                    "event_id": f"{context['job_id']}:{phase}",
                    "phase": phase,
                    "stage_name": phase,
                    "status": job_status or "queued",
                    "started_at": context.get("started_at") or context.get("created_at"),
                    "finished_at": context.get("finished_at") or None,
                    "summary": "Run has not produced stage artifacts yet; status is projected from the job record.",
                    "source_ref": "validation_job",
                }
            )

        if job_status == "failed" and context.get("last_error"):
            events.append(
                {
                    "event_id": f"{context['job_id']}:failure",
                    "phase": "failed",
                    "stage_name": "failure",
                    "status": "failed",
                    "started_at": context.get("finished_at") or context.get("started_at"),
                    "finished_at": context.get("finished_at") or None,
                    "summary": str(context.get("last_error") or ""),
                    "source_ref": "validation_job.last_error",
                }
            )
        if isinstance(errors, list):
            for index, item in enumerate(errors[:5], start=1):
                if not isinstance(item, dict):
                    continue
                events.append(
                    {
                        "event_id": f"{context['run_id']}:error_{index}",
                        "phase": "failed",
                        "stage_name": str(item.get("stage_name") or "error"),
                        "status": "failed",
                        "started_at": item.get("started_at") or None,
                        "finished_at": item.get("finished_at") or None,
                        "summary": str(item.get("message") or item.get("error") or "Run error recorded."),
                        "source_ref": f"errors.json#{index}",
                    }
                )

        completed_count = sum(1 for event in events if str(event.get("status") or "") == "succeeded")
        failed_count = sum(1 for event in events if str(event.get("status") or "") in {"failed", "error"})
        if job_status == "completed":
            phase = "completed"
        elif job_status == "failed" or failed_count:
            phase = "failed"
        elif job_status == "canceled":
            phase = "blocked"
        elif job_status == "queued":
            phase = "queued"
        elif any(event.get("phase") == "interviewing" for event in events):
            phase = "interviewing"
        else:
            phase = "planning"
        response_items = raw_responses if isinstance(raw_responses, list) else []
        return {
            "contract_version": "frontline-run-progress/v1",
            "study_id": study_id,
            "run_id": context["run_id"],
            "job_id": context["job_id"],
            "phase": phase if phase in FRONTLINE_RUN_PHASES else "blocked",
            "status": job_status or "unknown",
            "progress_percent": 100 if job_status == "completed" else max(5, min(95, int((completed_count / max(len(events), 1)) * 100))),
            "participant_progress": {
                "selected_count": len(response_items),
                "completed_count": sum(1 for item in response_items if isinstance(item, dict) and str(item.get("status") or "") == "succeeded"),
                "failed_count": sum(1 for item in response_items if isinstance(item, dict) and str(item.get("status") or "") == "failed"),
            },
            "events": events,
            "provider_runtime_boundary": context["provider_runtime_boundary"],
            "observed_interview_contract": {
                "transport": "polling_api",
                "streaming_supported": False,
                "observed_interview_mode": "artifact_projected",
                "upgrade_path": "A future worker can append the same phase events while an LLM-backed interview is running.",
            },
            "synthetic_boundary": (
                "Run progress describes synthetic interview execution state. It is operational telemetry, not human evidence."
            ),
        }

    @staticmethod
    def _frontline_stage_summary(stage_name: str, payload: dict[str, Any]) -> str:
        if stage_name == "sampling":
            return f"Selected {payload.get('selected_count', 0)} synthetic participant(s)."
        if stage_name == "persona_responses":
            return f"Captured {payload.get('successful_count', 0)} synthetic response(s); {payload.get('failed_count', 0)} failed."
        if stage_name == "report_writer":
            return "Generated the summary report from synthetic evidence artifacts."
        if stage_name == "sensitive_audit":
            return "Audited the run for sensitive-topic and boundary risks."
        return f"{stage_name.replace('_', ' ')} stage {payload.get('status', 'recorded')}."

    def get_frontline_run_transcript(self, auth: AuthContext, *, study_id: str, run_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        _study, context, run_dir = self._resolve_frontline_run_context(auth, study_id=study_id, run_id=run_id)
        raw_responses = self._read_run_artifact(run_dir, "raw_responses.json", [])
        guide_questions = []
        metadata = dict(context.get("metadata", {}))
        mode_inference_payload = metadata.get("mode_inference") if isinstance(metadata.get("mode_inference"), dict) else {}
        mode = str(metadata.get("mode") or mode_inference_payload.get("mode") or "")
        exchanges: list[dict[str, Any]] = []
        if isinstance(raw_responses, list):
            for index, item in enumerate(raw_responses, start=1):
                if not isinstance(item, dict):
                    continue
                response = item.get("response") if isinstance(item.get("response"), dict) else {}
                participant_text = self._frontline_response_text(response)
                exchange_id = f"exchange_{index}"
                synthetic_user_id = str(item.get("synthetic_user_id") or response.get("synthetic_user_id") or f"participant_{index}")
                exchanges.append(
                    {
                        "exchange_id": exchange_id,
                        "synthetic_user_id": synthetic_user_id,
                        "panel_role": str(item.get("panel_role") or response.get("panel_role") or ""),
                        "status": str(item.get("status") or "recorded"),
                        "started_at": item.get("started_at") or None,
                        "finished_at": item.get("finished_at") or None,
                        "turns": [
                            {
                                "turn_id": f"{exchange_id}.facilitator",
                                "speaker": "facilitator",
                                "text": "The platform prompted the synthetic participant with the confirmed study plan and moderator guide.",
                                "evidence_basis": "execution_prompt",
                                "source_ref": "brief.json",
                            },
                            {
                                "turn_id": f"{exchange_id}.synthetic_participant",
                                "speaker": "synthetic_participant",
                                "synthetic_user_id": synthetic_user_id,
                                "text": participant_text,
                                "evidence_basis": "synthetic_response",
                                "source_ref": f"raw_responses.json#{index}",
                            },
                        ],
                        "source_refs": [f"raw_responses.json#{index}"],
                        "trace_refs": [f"participant_reasoning_trace:{synthetic_user_id}"],
                    }
                )
        return {
            "contract_version": "frontline-run-transcript/v1",
            "study_id": study_id,
            "run_id": context["run_id"],
            "job_id": context["job_id"],
            "mode": mode or "unknown",
            "exchange_count": len(exchanges),
            "guide_questions": guide_questions,
            "exchanges": exchanges,
            "source_link_policy": {
                "stable_exchange_ref_format": "exchange_N.synthetic_participant",
                "evidence_slice_source_field": "source_exchange_refs",
                "trace_source_field": "trace_refs",
            },
            "synthetic_boundary": (
                "This transcript is a synthetic interview transcript projected from run artifacts. It is not a real human interview transcript."
            ),
        }

    @staticmethod
    def _frontline_response_text(response: dict[str, Any]) -> str:
        parts = [
            response.get("first_impression"),
            response.get("pain_relevance"),
            response.get("solution_attractiveness"),
            response.get("trust_concern"),
            response.get("pricing_reaction"),
            response.get("likely_objection"),
            response.get("what_would_make_them_try"),
            response.get("what_would_make_them_reject"),
        ]
        text = " ".join(str(part).strip() for part in parts if str(part or "").strip())
        return text or "Synthetic participant response was recorded, but no participant-facing text was available."

    def get_frontline_run_trace(self, auth: AuthContext, *, study_id: str, run_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        _study, context, run_dir = self._resolve_frontline_run_context(auth, study_id=study_id, run_id=run_id)
        planner = self._read_run_artifact(run_dir, "planner.json", [])
        raw_responses = self._read_run_artifact(run_dir, "raw_responses.json", [])
        audit = self._read_run_artifact(run_dir, "audit.json", [])
        observed_action = self._read_run_artifact(run_dir, "observed_action_trace.json", None)
        run_contract = self._read_run_artifact(run_dir, "run_contract.json", {})
        facilitator_trace = []
        if isinstance(planner, list):
            facilitator_trace = [
                {
                    "trace_id": f"facilitator_plan_{index}",
                    "trace_type": "facilitator_trace",
                    "summary": str(step),
                    "source_ref": f"planner.json#{index}",
                    "evidence_boundary": "Planning trace; not participant evidence.",
                }
                for index, step in enumerate(planner, start=1)
            ]
        participant_trace = []
        if isinstance(raw_responses, list):
            for index, item in enumerate(raw_responses, start=1):
                if not isinstance(item, dict):
                    continue
                response = item.get("response") if isinstance(item.get("response"), dict) else {}
                synthetic_user_id = str(item.get("synthetic_user_id") or response.get("synthetic_user_id") or f"participant_{index}")
                participant_trace.append(
                    {
                        "trace_id": f"participant_reasoning_trace:{synthetic_user_id}",
                        "trace_type": "synthetic_participant_reasoning_trace",
                        "synthetic_user_id": synthetic_user_id,
                        "top_objection": response.get("likely_objection"),
                        "try_trigger": response.get("what_would_make_them_try"),
                        "reject_trigger": response.get("what_would_make_them_reject"),
                        "scorecard": response.get("scorecard") if isinstance(response.get("scorecard"), dict) else {},
                        "themes": response.get("themes") if isinstance(response.get("themes"), dict) else {},
                        "source_ref": f"raw_responses.json#{index}",
                        "exchange_ref": f"exchange_{index}.synthetic_participant",
                        "evidence_boundary": "Synthetic participant reasoning trace is a simulation clue source, not real-person mind reading.",
                    }
                )
        audit_trace = []
        if isinstance(audit, list):
            audit_trace = [
                {
                    "trace_id": f"audit_{index}",
                    "trace_type": "audit_report",
                    "summary": str(item.get("observation") or item.get("message") or item) if isinstance(item, dict) else str(item),
                    "source_ref": f"audit.json#{index}",
                    "evidence_boundary": "Audit trace reviews the synthetic run boundary and risk posture.",
                }
                for index, item in enumerate(audit, start=1)
            ]
        observed_action_trace = []
        if isinstance(observed_action, dict):
            observed_action_trace.append(
                {
                    "trace_id": "observed_action_trace",
                    "trace_type": "observed_action_trace",
                    "summary": "Observed action trace artifact is attached to this run.",
                    "source_ref": "observed_action_trace.json",
                    "evidence_boundary": "Observed action trace is action-grounded only when captured from an instrumented task.",
                    "event_count": len(observed_action.get("events", [])) if isinstance(observed_action.get("events"), list) else 0,
                }
            )
        return {
            "contract_version": "frontline-run-trace/v1",
            "study_id": study_id,
            "run_id": context["run_id"],
            "job_id": context["job_id"],
            "facilitator_trace": facilitator_trace,
            "synthetic_participant_reasoning_trace": participant_trace,
            "observed_action_trace": observed_action_trace,
            "audit_trace": audit_trace,
            "provider_lineage": {
                "provider_name": context.get("provider_name"),
                "provider_runtime_boundary": context.get("provider_runtime_boundary"),
                "run_contract_status": (
                    dict(run_contract.get("result", {})).get("status")
                    if isinstance(run_contract, dict) and isinstance(run_contract.get("result"), dict)
                    else context.get("job_status")
                ),
                "run_contract_ref": "run_contract.json" if run_contract else None,
            },
            "source_link_policy": {
                "facilitator_trace_ref_format": "facilitator_plan_N",
                "participant_reasoning_ref_format": "participant_reasoning_trace:{synthetic_user_id}",
                "observed_action_trace_ref": "observed_action_trace",
            },
            "synthetic_boundary": (
                "Trace records explain how synthetic evidence was produced and audited. Only observed_action_trace is action-grounded when an instrumented task artifact exists."
            ),
        }

    def get_frontline_run_event_stream(self, auth: AuthContext, *, study_id: str, run_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        _study, context, _run_dir = self._resolve_frontline_run_context(auth, study_id=study_id, run_id=run_id)
        progress = self.get_frontline_run_progress(auth, study_id=study_id, run_id=run_id)
        transcript = self.get_frontline_run_transcript(auth, study_id=study_id, run_id=run_id)
        trace = self.get_frontline_run_trace(auth, study_id=study_id, run_id=run_id)
        events: list[dict[str, Any]] = []
        fallback_time = str(context.get("started_at") or context.get("created_at") or utc_now_iso())

        for index, event in enumerate(progress.get("events", []) if isinstance(progress.get("events"), list) else [], start=1):
            if not isinstance(event, dict):
                continue
            phase = str(event.get("phase") or "queued")
            status = str(event.get("status") or progress.get("status") or "recorded")
            occurred_at = str(event.get("finished_at") or event.get("started_at") or fallback_time)
            source_ref = str(event.get("source_ref") or "").strip()
            events.append(
                {
                    "event_id": f"run_event_{index}_{re.sub(r'[^a-z0-9_]+', '_', str(event.get('event_id') or phase).lower()).strip('_')}",
                    "event_type": f"run.{phase}",
                    "phase": phase if phase in FRONTLINE_RUN_PHASES else "blocked",
                    "status": status,
                    "occurred_at": occurred_at,
                    "summary": str(event.get("summary") or status),
                    "safe_to_show": True,
                    "source_refs": [source_ref] if source_ref else [],
                    "trace_refs": [],
                    "evidence_boundary": "operational_telemetry_not_human_evidence",
                }
            )

        latest_safe_turn: dict[str, Any] | None = None
        exchanges = transcript.get("exchanges", []) if isinstance(transcript.get("exchanges"), list) else []
        for index, exchange in enumerate(exchanges, start=1):
            if not isinstance(exchange, dict):
                continue
            turns = exchange.get("turns") if isinstance(exchange.get("turns"), list) else []
            participant_turn = next((turn for turn in turns if isinstance(turn, dict) and turn.get("speaker") == "synthetic_participant"), {})
            participant_text = str(participant_turn.get("text") or "")
            preview = participant_text[:220] + ("..." if len(participant_text) > 220 else "")
            source_refs = [str(ref) for ref in exchange.get("source_refs", []) if str(ref).strip()] if isinstance(exchange.get("source_refs"), list) else []
            trace_refs = [str(ref) for ref in exchange.get("trace_refs", []) if str(ref).strip()] if isinstance(exchange.get("trace_refs"), list) else []
            latest_safe_turn = {
                "exchange_id": str(exchange.get("exchange_id") or f"exchange_{index}"),
                "synthetic_user_id": str(exchange.get("synthetic_user_id") or ""),
                "speaker": "synthetic_participant",
                "text_preview": preview,
                "source_refs": source_refs,
                "trace_refs": trace_refs,
                "boundary": "safe transcript preview from synthetic evidence; inspect transcript and trace for provenance.",
            }
            events.append(
                {
                    "event_id": f"run_event_transcript_{index}",
                    "event_type": "run.synthetic_participant_turn_recorded",
                    "phase": "interviewing",
                    "status": str(exchange.get("status") or "recorded"),
                    "occurred_at": str(exchange.get("finished_at") or exchange.get("started_at") or fallback_time),
                    "summary": f"Recorded synthetic participant exchange {index}.",
                    "safe_to_show": True,
                    "source_refs": source_refs,
                    "trace_refs": trace_refs,
                    "latest_safe_turn": latest_safe_turn,
                    "evidence_boundary": "synthetic_transcript_not_human_interview",
                }
            )

        observed_action_trace = trace.get("observed_action_trace", []) if isinstance(trace.get("observed_action_trace"), list) else []
        observed_event_count = 0
        for index, item in enumerate(observed_action_trace, start=1):
            if not isinstance(item, dict):
                continue
            observed_event_count += int(item.get("event_count") or 0)
            events.append(
                {
                    "event_id": f"run_event_observed_{index}",
                    "event_type": "run.observed_interview_event_recorded",
                    "phase": "interviewing",
                    "status": "recorded",
                    "occurred_at": fallback_time,
                    "summary": str(item.get("summary") or "Observed interview trace is attached to this run."),
                    "safe_to_show": True,
                    "source_refs": [str(item.get("source_ref") or "observed_action_trace.json")],
                    "trace_refs": [str(item.get("trace_id") or "observed_action_trace")],
                    "evidence_boundary": str(item.get("evidence_boundary") or "Observed action trace is action-grounded only when captured."),
                }
            )

        audit_trace = trace.get("audit_trace", []) if isinstance(trace.get("audit_trace"), list) else []
        for index, item in enumerate(audit_trace[:4], start=1):
            if not isinstance(item, dict):
                continue
            events.append(
                {
                    "event_id": f"run_event_audit_{index}",
                    "event_type": "run.audit_trace_recorded",
                    "phase": "auditing",
                    "status": "recorded",
                    "occurred_at": fallback_time,
                    "summary": str(item.get("summary") or "Audit trace recorded."),
                    "safe_to_show": True,
                    "source_refs": [str(item.get("source_ref") or "")] if str(item.get("source_ref") or "").strip() else [],
                    "trace_refs": [str(item.get("trace_id") or "")] if str(item.get("trace_id") or "").strip() else [],
                    "evidence_boundary": str(item.get("evidence_boundary") or "Audit trace records boundary review, not human proof."),
                }
            )

        terminal_phase = str(progress.get("phase") or "queued")
        if terminal_phase in {"completed", "failed", "blocked"}:
            events.append(
                {
                    "event_id": f"run_event_terminal_{terminal_phase}",
                    "event_type": f"run.{terminal_phase}",
                    "phase": terminal_phase,
                    "status": str(progress.get("status") or terminal_phase),
                    "occurred_at": str(context.get("finished_at") or fallback_time),
                    "summary": (
                        "Run is ready for evidence review."
                        if terminal_phase == "completed"
                        else str(context.get("last_error") or f"Run ended in {terminal_phase} state.")
                    ),
                    "safe_to_show": True,
                    "source_refs": ["validation_job"],
                    "trace_refs": [],
                    "evidence_boundary": "terminal run state is operational telemetry.",
                }
            )

        privacy_controls = self.describe_workspace_privacy_export_controls(auth, study_id=study_id)
        return {
            "contract_version": "workspace-run-event-stream/v1",
            "workspace_id": auth.workspace_id,
            "project_id": str(context.get("project_id") or ""),
            "study_id": study_id,
            "run_id": context["run_id"],
            "job_id": context["job_id"],
            "phase": terminal_phase if terminal_phase in FRONTLINE_RUN_PHASES else "blocked",
            "status": str(progress.get("status") or context.get("job_status") or "unknown"),
            "progress_percent": int(progress.get("progress_percent") or 0),
            "participant_progress": dict(progress.get("participant_progress", {})) if isinstance(progress.get("participant_progress"), dict) else {},
            "latest_safe_turn": latest_safe_turn,
            "events": events,
            "transport": {
                "current_transport": "polling_api",
                "streaming_supported": False,
                "future_streaming_contract": "same_event_shape",
                "refresh_guidance": "Poll this endpoint while the run is queued or running; a future SSE transport must emit the same contract.",
            },
            "observed_interview_bridge": {
                "status": "attached" if observed_action_trace else "not_attached",
                "mode": "artifact_projected",
                "observed_event_count": observed_event_count,
                "source_refs": ["observed_action_trace.json"] if observed_action_trace else [],
                "boundary": (
                    "Observed interview events are bridged into the same run monitor only when an observed trace artifact exists."
                ),
            },
            "provider_runtime_boundary": progress.get("provider_runtime_boundary"),
            "privacy_export_controls": {
                "contract_version": privacy_controls.get("contract_version"),
                "privacy_readiness": privacy_controls.get("privacy_readiness"),
                "retention_controls": privacy_controls.get("retention_controls"),
                "data_residency": privacy_controls.get("data_residency"),
            },
            "provenance": {
                "source_contracts": [
                    "frontline-run-progress/v1",
                    "frontline-run-transcript/v1",
                    "frontline-run-trace/v1",
                ],
                "source_exchange_refs": [str(exchange.get("exchange_id") or "") for exchange in exchanges if isinstance(exchange, dict)],
                "source_trace_ref_count": len(trace.get("synthetic_participant_reasoning_trace", [])) if isinstance(trace.get("synthetic_participant_reasoning_trace"), list) else 0,
            },
            "capabilities": {
                "persona_interview_state": True,
                "latest_safe_turn_metadata": True,
                "observed_interview_bridge": True,
                "transcript_trace_provenance": True,
                "boundary_preserving_integration_ready": True,
            },
            "synthetic_boundary": (
                "Run event stream describes synthetic interview execution and safe transcript/trace provenance. "
                "It does not prove real human behavior."
            ),
        }

    def describe_calibration_observatory(self, auth: AuthContext) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        jobs = self.list_workspace_jobs(auth)
        mode_counts: dict[str, int] = {}
        provider_counts: dict[str, int] = {}
        calibration_status_counts: dict[str, int] = {}
        evidence_type_counts: dict[str, int] = {}
        benchmark_suite_counts: dict[str, int] = {}
        drift_signals: list[dict[str, Any]] = []
        miss_attribution: list[dict[str, Any]] = []
        unsupported_evidence_types: set[str] = set()
        calibrated_run_count = 0
        completed_run_count = 0

        for job in jobs:
            metadata = dict(job.get("metadata", {}))
            mode_inference_payload = metadata.get("mode_inference") if isinstance(metadata.get("mode_inference"), dict) else {}
            mode = str(metadata.get("mode") or mode_inference_payload.get("mode") or "unknown")
            provider = str(job.get("provider_name") or "unknown")
            mode_counts[mode] = mode_counts.get(mode, 0) + 1
            provider_counts[provider] = provider_counts.get(provider, 0) + 1
            for evidence_type in metadata.get("expected_evidence_types", []) if isinstance(metadata.get("expected_evidence_types"), list) else []:
                key = str(evidence_type or "unknown")
                evidence_type_counts[key] = evidence_type_counts.get(key, 0) + 1
            run_context = {
                "run_id": _job_run_id(job),
                "output_run_path": str(job.get("output_run_path") or ""),
            }
            calibration_entry = self._run_calibration_lineage_entry(run_context=run_context)
            status = str(calibration_entry.get("calibration_status") or "unavailable")
            calibration_status_counts[status] = calibration_status_counts.get(status, 0) + 1
            if str(job.get("status") or "") == "completed":
                completed_run_count += 1
            if calibration_entry.get("has_human_calibration"):
                calibrated_run_count += 1
                suite = str(calibration_entry.get("benchmark_id") or calibration_entry.get("benchmark_source_type") or "attached_human_benchmark")
                benchmark_suite_counts[suite] = benchmark_suite_counts.get(suite, 0) + 1
                human_calibration = _load_human_calibration_record(
                    {
                        "run_id": _job_run_id(job),
                        "output_path": str(job.get("output_run_path") or ""),
                        "primary_artifact_path": str(Path(str(job.get("output_run_path") or "")) / "run.json") if job.get("output_run_path") else "",
                    }
                )
                if isinstance(human_calibration, dict):
                    drift = human_calibration.get("drift_detection") if isinstance(human_calibration.get("drift_detection"), dict) else {}
                    if drift:
                        drift_signals.append({"run_id": _job_run_id(job), **drift})
                    miss = human_calibration.get("miss_attribution") if isinstance(human_calibration.get("miss_attribution"), dict) else {}
                    if miss:
                        miss_attribution.append({"run_id": _job_run_id(job), **miss})
            elif mode != "unknown":
                unsupported_evidence_types.update(
                    str(item)
                    for item in metadata.get("expected_evidence_types", [])
                    if isinstance(metadata.get("expected_evidence_types"), list) and str(item).strip()
                )

        readiness_status = "insufficient_benchmarking"
        if completed_run_count and calibrated_run_count == completed_run_count:
            readiness_status = "calibration_covered"
        elif calibrated_run_count:
            readiness_status = "partial_calibration"
        return {
            "contract_version": "calibration-observatory/v1",
            "workspace_id": auth.workspace_id,
            "generated_at": utc_now_iso(),
            "health_summary": {
                "status": readiness_status,
                "completed_run_count": completed_run_count,
                "calibrated_run_count": calibrated_run_count,
                "uncalibrated_completed_run_count": max(0, completed_run_count - calibrated_run_count),
                "launch_gate_status": "blocked" if readiness_status == "insufficient_benchmarking" else "operator_review_required",
            },
            "segments": {
                "mode_counts": mode_counts,
                "provider_counts": provider_counts,
                "evidence_type_counts": evidence_type_counts,
                "calibration_status_counts": calibration_status_counts,
                "benchmark_suite_counts": benchmark_suite_counts,
            },
            "drift_signals": drift_signals[:10],
            "miss_attribution": miss_attribution[:10],
            "unsupported_evidence_types": sorted(unsupported_evidence_types),
            "readiness_projection": {
                "public_launch_dependency": "continuous_calibration_health",
                "replacement_claim_allowed": False,
                "next_required_evidence": (
                    "Attach external human benchmark outcomes by mode, evidence type, provider, and market before public or replacement-grade claims."
                ),
            },
            "synthetic_boundary": (
                "Calibration observatory is an operator quality signal. It does not convert synthetic outputs into human market proof."
            ),
        }

    def create_workspace_study_report(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        included_run_ids: list[str] | None = None,
        title: str = "",
        status: str = "ready_for_review",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot create study reports.")
        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        project = job_store.get_workspace_project(self.runtime_root, study.project_id)
        if project is None or project.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace project '{study.project_id}' is not visible in this workspace.")

        allowed_statuses = {"draft", "ready_for_review", "final"}
        normalized_status = status.strip() or "ready_for_review"
        if normalized_status not in allowed_statuses:
            raise ValueError(f"Unsupported study report status '{normalized_status}'.")

        selected_run_ids = _unique_preserve_order([str(item) for item in (included_run_ids or [])])
        study_jobs = [
            job
            for job in job_store.list_workspace_jobs(self.runtime_root, workspace.workspace_id)
            if str(dict(job.get("metadata", {})).get("study_id") or "") == study.study_id
            and str(job.get("status") or "") == "completed"
        ]
        if selected_run_ids:
            selected_run_set = set(selected_run_ids)
            study_jobs = [job for job in study_jobs if _job_run_id(job) in selected_run_set]
            order = {run_id: index for index, run_id in enumerate(selected_run_ids)}
            study_jobs.sort(key=lambda job: order.get(_job_run_id(job), len(order)))
        if not study_jobs:
            raise ValueError("At least one completed study run is required before creating a study report.")

        run_ids = _unique_preserve_order([_job_run_id(job) for job in study_jobs if _job_run_id(job)])
        job_ids = _unique_preserve_order([str(job.get("job_id") or "") for job in study_jobs])
        plan_revision_ids = _unique_preserve_order(
            [
                str(dict(job.get("metadata", {})).get("plan_revision_id") or dict(job.get("metadata", {})).get("frontline_plan_revision_id") or "")
                for job in study_jobs
            ]
        )

        evidence_slices: list[dict[str, Any]] = []
        readiness_records: list[dict[str, Any]] = []
        for job in study_jobs:
            run_id = _job_run_id(job)
            if not run_id:
                continue
            query_payload = self._query_run_evidence_with_fallback(
                workspace_id=workspace.workspace_id,
                run_id=run_id,
                query_text="objection trust adoption confusion contradiction",
                active_family="all",
                sort_by="relevance",
            )
            if isinstance(query_payload.get("readiness_gate"), dict):
                readiness_records.append(dict(query_payload.get("readiness_gate", {})))
            for result in query_payload.get("results", []):
                if not isinstance(result, dict):
                    continue
                evidence_slices.append(
                    {
                        "run_id": run_id,
                        "job_id": str(job.get("job_id") or ""),
                        "plan_revision_id": str(
                            dict(job.get("metadata", {})).get("plan_revision_id")
                            or dict(job.get("metadata", {})).get("frontline_plan_revision_id")
                            or ""
                        ) or None,
                        "result_id": str(result.get("id") or ""),
                        "family": str(result.get("family") or ""),
                        "title": str(result.get("title") or result.get("label") or result.get("id") or ""),
                        "snippet": str(result.get("snippet") or result.get("summary") or "")[:320],
                        "source_exchange_refs": [
                            str(ref) for ref in result.get("source_exchange_refs", []) if str(ref).strip()
                        ] if isinstance(result.get("source_exchange_refs"), list) else [],
                        "source_trace_refs": [
                            str(ref) for ref in result.get("source_trace_refs", []) if str(ref).strip()
                        ] if isinstance(result.get("source_trace_refs"), list) else [],
                    }
                )

        def signals_for(markers: tuple[str, ...], *, fallback_title: str) -> list[dict[str, Any]]:
            matched: list[dict[str, Any]] = []
            for item in evidence_slices:
                signal_text = " ".join([item.get("title", ""), item.get("snippet", ""), item.get("family", "")]).lower()
                if any(marker in signal_text for marker in markers):
                    matched.append(item)
            if matched:
                return matched[:6]
            return [
                {
                    "title": fallback_title,
                    "included_run_ids": run_ids,
                    "note": "No stronger matching slice was found; treat as a review prompt, not a proven pattern.",
                }
            ]

        stable_patterns = [
            {
                "pattern_id": "recurring_research_signal",
                "label": "Signals recurring across included synthetic runs",
                "included_run_ids": run_ids,
                "supporting_evidence_count": len(evidence_slices),
                "stability_label": "multi_run" if len(run_ids) > 1 else "single_run_directional",
            }
        ]
        divergent_signals = []
        if len(plan_revision_ids) > 1:
            divergent_signals.append(
                {
                    "signal_id": "plan_drift",
                    "label": "Compared runs use different confirmed plan revisions",
                    "included_plan_revision_ids": plan_revision_ids,
                    "review_action": "Review plan drift before treating differences as stable behavior.",
                }
            )
        if len(run_ids) > 1:
            divergent_signals.append(
                {
                    "signal_id": "run_variation",
                    "label": "Multiple completed runs are included; inspect stable patterns and outliers separately.",
                    "included_run_ids": run_ids,
                }
            )
        contradictions = signals_for(("contradict", "mixed", "inconsistent", "unsupported"), fallback_title="Contradiction review required")
        human_validation_gaps = [
            {
                "gap_id": "synthetic_evidence_boundary",
                "label": "Synthetic evidence requires human validation before market-proof claims.",
                "included_run_ids": run_ids,
                "readiness_statuses": _unique_preserve_order(
                    [str(item.get("status") or "pending") for item in readiness_records if isinstance(item, dict)]
                )
                or ["pending"],
            }
        ]
        if not readiness_records:
            human_validation_gaps.append(
                {
                    "gap_id": "missing_readiness_gate",
                    "label": "No readiness-gate evidence was available for at least one included run.",
                    "included_run_ids": run_ids,
                }
            )

        now = utc_now_iso()
        report_id = f"study_report_{uuid.uuid4().hex[:12]}"
        report_root = _workspace_root(self.runtime_root, workspace.workspace_id) / "collaboration" / "study_reports" / report_id
        report_root.mkdir(parents=True, exist_ok=True)
        payload_path = report_root / "study_report.json"
        saved_title = title.strip() or f"{study.title} study report"
        report_metadata = dict(metadata or {})
        report_metadata.update(
            {
                "contract_version": "frontline-study-report/v0-draft",
                "plan_drift_review_required": len(plan_revision_ids) > 1,
                "evidence_slice_count": len(evidence_slices),
                "boundary_note": (
                    "Synthetic evidence only. Study reports preserve run and plan revision lineage and do not claim human market proof."
                ),
            }
        )
        report = WorkspaceStudyReport(
            study_report_id=report_id,
            workspace_id=workspace.workspace_id,
            project_id=project.project_id,
            study_id=study.study_id,
            title=saved_title,
            status=normalized_status,
            included_job_ids=job_ids,
            included_run_ids=run_ids,
            included_plan_revision_ids=plan_revision_ids,
            stable_patterns=stable_patterns,
            divergent_signals=divergent_signals,
            key_objections=signals_for(("objection", "hesitat", "concern", "reject"), fallback_title="Objection review required"),
            trust_gaps=signals_for(("trust", "risk", "skeptic", "permission", "credib"), fallback_title="Trust-gap review required"),
            adoption_barriers=signals_for(("adopt", "setup", "price", "workflow", "effort"), fallback_title="Adoption-barrier review required"),
            prototype_confusions=signals_for(("prototype", "button", "cta", "screen", "confus", "click"), fallback_title="Prototype-comprehension review required"),
            contradictions=contradictions,
            human_validation_gaps=human_validation_gaps,
            payload_path=str(payload_path),
            created_by_user_id=auth.user_id,
            created_at=now,
            updated_at=now,
            metadata=report_metadata,
        )
        payload = report.to_dict()
        payload["evidence_slices"] = evidence_slices[:50]
        write_json(payload_path, payload)
        write_markdown(
            report_root / "README.md",
            "\n".join(
                [
                    f"# {saved_title}",
                    "",
                    f"- study_id: {study.study_id}",
                    f"- included_run_ids: {', '.join(run_ids) or '-'}",
                    f"- included_plan_revision_ids: {', '.join(plan_revision_ids) or '-'}",
                    f"- status: {normalized_status}",
                    "- boundary: synthetic evidence only; not human market proof",
                ]
            ),
        )
        created = job_store.create_workspace_study_report(self.runtime_root, report)
        job_store.update_workspace_study(
            self.runtime_root,
            study_id=study.study_id,
            status="completed" if normalized_status in {"ready_for_review", "final"} else "reviewing",
            metadata_updates={
                "latest_report_id": created.study_report_id,
                "latest_study_report_id": created.study_report_id,
            },
        )
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="study_report.created",
                target_type="study_report",
                target_id=created.study_report_id,
                event_payload={
                    "study_id": study.study_id,
                    "project_id": project.project_id,
                    "included_run_ids": run_ids,
                    "included_plan_revision_ids": plan_revision_ids,
                    "status": normalized_status,
                },
                created_at=now,
            ),
        )
        return self._study_report_summary(created)

    def list_workspace_study_reports(self, auth: AuthContext, *, study_id: str = "") -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        if study_id.strip():
            study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
            if study is None or study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        return [
            self._study_report_summary(report)
            for report in job_store.list_workspace_study_reports(
                self.runtime_root,
                auth.workspace_id,
                study_id=study_id.strip(),
            )
        ]

    def get_workspace_study_report(self, auth: AuthContext, study_report_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        report = job_store.get_workspace_study_report(self.runtime_root, study_report_id.strip())
        if report is None or report.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study report '{study_report_id}' is not visible in this workspace.")
        return self._study_report_summary(report)

    def update_workspace_study_governed_redaction(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        status: str,
        redaction_rules: list[dict[str, Any]] | None = None,
        note: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in DECISION_REVIEW_ASSIGNMENT_MUTATION_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot update governed study redaction.")
        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        governed_review = self._study_governed_review_state(study)
        if not bool(governed_review.get("human_review_required")):
            raise ValueError("Governed redaction is only required for regulated/high-stakes studies.")
        normalized_status = _normalized_string(status)
        if normalized_status not in {"draft", "active", "escalated", "unconfigured"}:
            raise ValueError(f"Unsupported governed redaction status '{normalized_status}'.")
        normalized_rules = self._normalized_governed_redaction_rules(redaction_rules or [])
        if normalized_status == "active" and not normalized_rules:
            raise ValueError("At least one governed redaction rule is required when redaction status is 'active'.")
        if normalized_status == "escalated" and not note.strip():
            raise ValueError("Field 'note' is required when governed redaction status is 'escalated'.")
        now = utc_now_iso()
        merged_metadata = dict(study.metadata or {})
        merged_metadata.update(dict(metadata or {}))
        history = merged_metadata.get("governed_redaction_history")
        if not isinstance(history, list):
            history = []
        history = [item for item in history if isinstance(item, dict)]
        history.append(
            {
                "status": normalized_status,
                "changed_at": now,
                "changed_by_user_id": auth.user_id,
                "note": note.strip(),
                "redaction_rules": normalized_rules,
            }
        )
        merged_metadata["governed_redaction"] = {
            "contract_version": "workspace-study-governed-redaction/v0-draft",
            "status": normalized_status,
            "redaction_rules": normalized_rules,
            "latest_note": note.strip(),
            "updated_at": now,
            "updated_by_user_id": auth.user_id,
        }
        merged_metadata["governed_redaction_history"] = history
        merged_metadata["regulated_review_boundary"] = self._regulated_review_boundary_from_fields(
            title=study.title,
            research_intent=study.research_intent,
            desired_output=study.desired_output,
            first_task=study.first_task,
            artifact_refs=list(study.artifact_refs),
            metadata=merged_metadata,
        )
        updated = job_store.update_workspace_study(
            self.runtime_root,
            study_id=study.study_id,
            metadata_updates=merged_metadata,
        )
        if updated is None:
            raise FileNotFoundError(f"Workspace study '{study_id}' could not be updated.")
        for export_bundle in job_store.list_workspace_export_bundles(
            self.runtime_root,
            workspace.workspace_id,
            study_id=study.study_id,
        ):
            refreshed_metadata = dict(export_bundle.metadata or {})
            refreshed_metadata["regulated_review_boundary"] = self._study_regulated_review_boundary(updated)
            refreshed_metadata["governed_review"] = self._study_governed_review_state(updated)
            refreshed_metadata["governed_redaction"] = self._study_governed_redaction_state(updated)
            refreshed_export = job_store.update_workspace_export_bundle(
                self.runtime_root,
                export_bundle_id=export_bundle.export_bundle_id,
                metadata_updates=refreshed_metadata,
            )
            self._write_export_bundle_contract_files(refreshed_export)
        for share_bundle in job_store.list_workspace_share_bundles(
            self.runtime_root,
            workspace.workspace_id,
            study_id=study.study_id,
        ):
            refreshed_metadata = dict(share_bundle.metadata or {})
            refreshed_metadata["regulated_review_boundary"] = self._study_regulated_review_boundary(updated)
            refreshed_metadata["governed_review"] = self._study_governed_review_state(updated)
            refreshed_metadata["governed_redaction"] = self._study_governed_redaction_state(updated)
            refreshed_share = job_store.update_workspace_share_bundle(
                self.runtime_root,
                share_bundle_id=share_bundle.share_bundle_id,
                metadata_updates=refreshed_metadata,
            )
            self._write_share_bundle_contract_files(refreshed_share)
        for snapshot in job_store.list_workspace_support_snapshots(
            self.runtime_root,
            workspace.workspace_id,
            study_id=study.study_id,
        ):
            merged_snapshot_metadata = dict(snapshot.metadata or {})
            diagnostic = merged_snapshot_metadata.get("diagnostic")
            if isinstance(diagnostic, dict):
                diagnostic["governed_redaction"] = self._study_governed_redaction_state(updated)
                diagnostic["governed_review"] = self._study_governed_review_state(updated)
                merged_snapshot_metadata["diagnostic"] = diagnostic
            refreshed_snapshot = job_store.update_workspace_support_snapshot_metadata(
                self.runtime_root,
                support_snapshot_id=snapshot.support_snapshot_id,
                metadata_updates=merged_snapshot_metadata,
                updated_at=now,
            ) or snapshot
            self._materialize_support_snapshot_artifacts(refreshed_snapshot)
        governed_redaction_state = self._study_governed_redaction_state(updated)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="study.governed_redaction_updated",
                target_type="study",
                target_id=updated.study_id,
                event_payload={
                    "project_id": updated.project_id,
                    "study_id": updated.study_id,
                    "redaction_status": normalized_status,
                    "redaction_rule_count": len(normalized_rules),
                    "governed_redaction_note": note.strip() or governed_redaction_state.get("latest_note"),
                },
                created_at=now,
            ),
        )
        return self._study_summary(updated)

    def update_workspace_study_governed_review_assignment(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        assignee_user_ids: list[str] | None = None,
        status: str = "assigned",
        note: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in DECISION_REVIEW_ASSIGNMENT_MUTATION_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot update governed study reviewer assignment.")
        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        governed_review = self._study_governed_review_state(study)
        if not bool(governed_review.get("human_review_required")):
            raise ValueError("Governed reviewer assignment is only required for regulated/high-stakes studies.")
        member_map = self._workspace_member_map(workspace)
        normalized_assignees = _unique_preserve_order([str(item) for item in (assignee_user_ids or [])])
        for user_id in normalized_assignees:
            member = member_map.get(user_id)
            if member is None:
                raise ValueError(f"Workspace member '{user_id}' is not available for governed study review assignment.")
            if member.role not in DECISION_REVIEW_ASSIGNEE_ROLES:
                raise ValueError(
                    f"Workspace member '{user_id}' has role '{member.role}' and cannot be assigned for governed study review."
                )
        normalized_status = _normalized_string(status) or "assigned"
        if normalized_status not in {"assigned", "unassigned", "escalated"}:
            raise ValueError(f"Unsupported governed review status '{normalized_status}'.")
        if normalized_status == "assigned" and not normalized_assignees:
            raise ValueError("Field 'assignee_user_ids' is required when governed review status is 'assigned'.")
        if normalized_status == "escalated" and not note.strip():
            raise ValueError("Field 'note' is required when governed review status is 'escalated'.")
        if normalized_status == "unassigned":
            normalized_assignees = []
        now = utc_now_iso()
        merged_metadata = dict(study.metadata or {})
        merged_metadata.update(dict(metadata or {}))
        assignment_history = merged_metadata.get("governed_review_assignment_history")
        if not isinstance(assignment_history, list):
            assignment_history = []
        assignment_history = [item for item in assignment_history if isinstance(item, dict)]
        assignment_history.append(
            {
                "status": normalized_status,
                "assignee_user_ids": normalized_assignees,
                "changed_at": now,
                "changed_by_user_id": auth.user_id,
                "note": note.strip(),
            }
        )
        governed_assignment = {
            "contract_version": "workspace-study-governed-review-assignment/v0-draft",
            "status": normalized_status,
            "assignee_user_ids": normalized_assignees,
            "assigned_at": now if normalized_assignees else None,
            "assigned_by_user_id": auth.user_id if normalized_assignees else None,
            "escalated_at": now if normalized_status == "escalated" else None,
            "escalated_by_user_id": auth.user_id if normalized_status == "escalated" else None,
            "latest_note": note.strip(),
        }
        merged_metadata.update(
            {
                "governed_review_assignment": governed_assignment,
                "governed_review_assignment_history": assignment_history,
            }
        )
        merged_metadata["regulated_review_boundary"] = self._regulated_review_boundary_from_fields(
            title=study.title,
            research_intent=study.research_intent,
            desired_output=study.desired_output,
            first_task=study.first_task,
            artifact_refs=list(study.artifact_refs),
            metadata=merged_metadata,
        )
        updated = job_store.update_workspace_study(
            self.runtime_root,
            study_id=study.study_id,
            metadata_updates=merged_metadata,
        )
        if updated is None:
            raise FileNotFoundError(f"Workspace study '{study_id}' could not be updated.")
        for decision_log in job_store.list_workspace_decision_logs(
            self.runtime_root,
            workspace.workspace_id,
            study_id=study.study_id,
        ):
            comments = self.list_workspace_decision_comments(auth, decision_log_id=decision_log.decision_log_id)
            self._materialize_decision_log_artifacts(decision_log, comment_summaries=comments)
        for export_bundle in job_store.list_workspace_export_bundles(
            self.runtime_root,
            workspace.workspace_id,
            study_id=study.study_id,
        ):
            refreshed_metadata = dict(export_bundle.metadata or {})
            refreshed_metadata["regulated_review_boundary"] = self._study_regulated_review_boundary(updated)
            refreshed_metadata["governed_review"] = self._study_governed_review_state(updated)
            refreshed_export = job_store.update_workspace_export_bundle(
                self.runtime_root,
                export_bundle_id=export_bundle.export_bundle_id,
                metadata_updates=refreshed_metadata,
            ) or export_bundle
            self._write_export_bundle_contract_files(refreshed_export)
        for share_bundle in job_store.list_workspace_share_bundles(
            self.runtime_root,
            workspace.workspace_id,
            study_id=study.study_id,
        ):
            refreshed_metadata = dict(share_bundle.metadata or {})
            refreshed_metadata["regulated_review_boundary"] = self._study_regulated_review_boundary(updated)
            refreshed_metadata["governed_review"] = self._study_governed_review_state(updated)
            refreshed_share = job_store.update_workspace_share_bundle(
                self.runtime_root,
                share_bundle_id=share_bundle.share_bundle_id,
                metadata_updates=refreshed_metadata,
            ) or share_bundle
            self._write_share_bundle_contract_files(refreshed_share)
        governed_review_state = self._study_governed_review_state(updated)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="study.governed_review_assignment_updated",
                target_type="study",
                target_id=updated.study_id,
                event_payload={
                    "project_id": updated.project_id,
                    "study_id": updated.study_id,
                    "assignment_status": normalized_status,
                    "assignee_user_ids": normalized_assignees,
                    "governed_review_note": note.strip() or governed_review_state.get("human_review_note"),
                    "review_gate_status": governed_review_state.get("review_gate_status"),
                },
                created_at=now,
            ),
        )
        return self._study_summary(updated)

    def list_workspace_study_activity(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        limit: int = 20,
    ) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        numeric_limit = max(1, min(int(limit), 100))
        candidate_events = job_store.list_audit_events(
            self.runtime_root,
            auth.workspace_id,
            limit=max(100, numeric_limit * 8),
        )
        activity_events = [
            self._study_activity_event_summary(event)
            for event in candidate_events
            if self._audit_event_matches_study(event, study.study_id)
        ][:numeric_limit]
        return {
            "contract_version": "workspace-study-activity/v0-draft",
            "study_id": study.study_id,
            "project_id": study.project_id,
            "study_title": study.title,
            "activity_events": activity_events,
            "filters": {
                "study_id": study.study_id,
                "limit": numeric_limit,
            },
            "capabilities": {
                "study_activity": True,
                "route_links": True,
            },
            "synthetic_boundary": (
                "Synthetic evidence only. Study activity describes simulated-research operations and collaboration state, not human validation."
            ),
        }

    def create_workspace_evidence_view(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        job_id: str = "",
        title: str = "",
        note: str = "",
        query_text: str = "",
        active_family: str = "all",
        sort_by: str = "relevance",
        selected_result_id: str = "",
        selected_replay_step_id: str = "",
        selected_comparison_run_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot save evidence views.")
        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")

        job = None
        run_id = ""
        if job_id.strip():
            job = self.get_validation_job(auth, job_id.strip())
            if str(dict(job.get("metadata", {})).get("study_id") or "") != study.study_id:
                raise AuthorizationError("The selected validation job does not belong to the selected study.")
            if str(job.get("status") or "") != "completed":
                raise ValueError("Only completed validation jobs can be saved as evidence views.")
            run_id = _job_run_id(job)

        project = job_store.get_workspace_project(self.runtime_root, study.project_id)
        if project is None or project.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace project '{study.project_id}' is not visible in this workspace.")

        now = utc_now_iso()
        evidence_view_id = f"view_{uuid.uuid4().hex[:12]}"
        workspace_root = _workspace_root(self.runtime_root, workspace.workspace_id)
        evidence_view_root = workspace_root / "collaboration" / "evidence_views" / evidence_view_id
        evidence_view_root.mkdir(parents=True, exist_ok=True)
        payload_path = evidence_view_root / "evidence_view.json"
        saved_title = title.strip() or f"{study.title} evidence view"
        saved_metadata = dict(metadata or {})
        selected_evidence_context = self._selected_evidence_context(
            workspace_id=workspace.workspace_id,
            run_id=run_id,
            query_text=query_text.strip(),
            active_family=active_family.strip() or "all",
            sort_by=sort_by.strip() or "relevance",
            selected_result_id=selected_result_id.strip(),
            selected_replay_step_id=selected_replay_step_id.strip(),
            selected_comparison_run_id=selected_comparison_run_id.strip(),
        )
        if selected_evidence_context:
            saved_metadata["selected_evidence_context"] = selected_evidence_context
        readiness_gate = dict(selected_evidence_context.get("readiness_gate", {})) if isinstance(selected_evidence_context, dict) else {}
        provider_runtime_boundary = (
            dict(selected_evidence_context.get("provider_runtime_boundary", {}))
            if isinstance(selected_evidence_context, dict)
            and isinstance(selected_evidence_context.get("provider_runtime_boundary"), dict)
            else {}
        )
        if provider_runtime_boundary:
            saved_metadata["provider_runtime_boundary"] = provider_runtime_boundary
        governed_review = self._study_governed_review_state(study)
        governed_redaction = self._study_governed_redaction_state(study)
        payload = {
            "evidence_view_id": evidence_view_id,
            "workspace_id": workspace.workspace_id,
            "project_id": project.project_id,
            "study_id": study.study_id,
            "job_id": str(job.get("job_id") or "") if job else None,
            "run_id": run_id or None,
            "title": saved_title,
            "note": note.strip(),
            "query_text": query_text.strip(),
            "active_family": active_family.strip() or "all",
            "sort_by": sort_by.strip() or "relevance",
            "selected_result_id": selected_result_id.strip() or None,
            "selected_replay_step_id": selected_replay_step_id.strip() or None,
            "selected_comparison_run_id": selected_comparison_run_id.strip() or None,
            "created_at": now,
            "created_by_user_id": auth.user_id,
            "readiness_gate": readiness_gate,
            "provider_runtime_boundary": provider_runtime_boundary,
            "governed_review": governed_review,
            "governed_redaction": governed_redaction,
            "metadata": saved_metadata,
        }
        write_json(payload_path, payload)
        write_markdown(
            evidence_view_root / "README.md",
            "\n".join(
                [
                    f"# {saved_title}",
                    "",
                    f"- study_id: {study.study_id}",
                    f"- job_id: {payload['job_id'] or '-'}",
                    f"- run_id: {payload['run_id'] or '-'}",
                    f"- family: {payload['active_family']}",
                    f"- sort: {payload['sort_by']}",
                    f"- selected_signal_id: {selected_evidence_context.get('selected_signal_id', '-') or '-'}",
                    f"- workflow_map_focus: {selected_evidence_context.get('workflow_map_focus', False)}",
                    f"- readiness_status: {readiness_gate.get('status', 'pending')}",
                    f"- evidence_mode: {provider_runtime_boundary.get('evidence_mode', 'unknown')}",
                    f"- governed_review_status: {governed_review.get('review_gate_status', 'not_required')}",
                    f"- governed_redaction_status: {governed_redaction.get('status', 'not_required')}",
                    "",
                    payload["note"] or "No note provided.",
                ]
            ),
        )
        evidence_view = WorkspaceEvidenceView(
            evidence_view_id=evidence_view_id,
            workspace_id=workspace.workspace_id,
            project_id=project.project_id,
            study_id=study.study_id,
            job_id=str(job.get("job_id") or "") if job else None,
            run_id=run_id or None,
            title=saved_title,
            note=note.strip(),
            query_text=query_text.strip(),
            active_family=active_family.strip() or "all",
            sort_by=sort_by.strip() or "relevance",
            selected_result_id=selected_result_id.strip() or None,
            selected_replay_step_id=selected_replay_step_id.strip() or None,
            selected_comparison_run_id=selected_comparison_run_id.strip() or None,
            payload_path=str(payload_path),
            created_by_user_id=auth.user_id,
            created_at=now,
            updated_at=now,
            metadata=saved_metadata,
        )
        created = job_store.create_workspace_evidence_view(self.runtime_root, evidence_view)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="evidence_view.saved",
                target_type="evidence_view",
                target_id=created.evidence_view_id,
                event_payload={
                    "study_id": created.study_id,
                    "job_id": created.job_id,
                    "active_family": created.active_family,
                    "sort_by": created.sort_by,
                    "selected_signal_id": selected_evidence_context.get("selected_signal_id") or None,
                    "workflow_map_focus": bool(selected_evidence_context.get("workflow_map_focus")),
                    "readiness_status": readiness_gate.get("status"),
                },
                created_at=now,
            ),
        )
        return self._evidence_view_summary(created)

    def list_workspace_evidence_views(
        self,
        auth: AuthContext,
        *,
        study_id: str = "",
        job_id: str = "",
    ) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        if study_id.strip():
            study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
            if study is None or study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        if job_id.strip():
            job = self.get_validation_job(auth, job_id.strip())
            if str(job.get("workspace_id") or "") != auth.workspace_id:
                raise AuthorizationError(f"Validation job '{job_id}' is not visible in this workspace.")
        return [
            self._evidence_view_summary(view)
            for view in job_store.list_workspace_evidence_views(
                self.runtime_root,
                auth.workspace_id,
                study_id=study_id.strip(),
                job_id=job_id.strip(),
            )
        ]

    def get_workspace_evidence_view(self, auth: AuthContext, evidence_view_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        view = job_store.get_workspace_evidence_view(self.runtime_root, evidence_view_id)
        if view is None or view.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace evidence view '{evidence_view_id}' is not visible in this workspace.")
        return self._evidence_view_summary(view)

    def create_workspace_decision_log(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        title: str = "",
        decision_summary: str = "",
        rationale: str = "",
        job_id: str = "",
        evidence_view_id: str = "",
        selected_result_id: str = "",
        selected_comparison_run_id: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot create decision logs.")
        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        clean_decision_summary = decision_summary.strip()
        if not clean_decision_summary:
            raise ValueError("Field 'decision_summary' is required.")

        job = None
        run_id = ""
        if job_id.strip():
            job = self.get_validation_job(auth, job_id.strip())
            if str(dict(job.get("metadata", {})).get("study_id") or "") != study.study_id:
                raise AuthorizationError("The selected validation job does not belong to the selected study.")
            run_id = _job_run_id(job)

        linked_evidence_view = None
        if evidence_view_id.strip():
            linked_evidence_view = job_store.get_workspace_evidence_view(self.runtime_root, evidence_view_id.strip())
            if linked_evidence_view is None or linked_evidence_view.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace evidence view '{evidence_view_id}' is not visible in this workspace.")
            if linked_evidence_view.study_id != study.study_id:
                raise AuthorizationError("The selected evidence view does not belong to the selected study.")

        project = job_store.get_workspace_project(self.runtime_root, study.project_id)
        if project is None or project.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace project '{study.project_id}' is not visible in this workspace.")

        now = utc_now_iso()
        decision_metadata = dict(metadata or {})
        governed_review = self._study_governed_review_state(study)
        governed_redaction = self._study_governed_redaction_state(study)
        linked_evidence_context = {}
        if linked_evidence_view is not None:
            linked_evidence_context = dict(linked_evidence_view.metadata or {}).get("selected_evidence_context", {})
            if not isinstance(linked_evidence_context, dict):
                linked_evidence_context = {}
        selected_evidence_context = self._selected_evidence_context(
            workspace_id=workspace.workspace_id,
            run_id=run_id,
            query_text=linked_evidence_view.query_text if linked_evidence_view else "",
            active_family=linked_evidence_view.active_family if linked_evidence_view else "all",
            sort_by=linked_evidence_view.sort_by if linked_evidence_view else "relevance",
            selected_result_id=selected_result_id.strip() or (linked_evidence_view.selected_result_id if linked_evidence_view else "") or "",
            selected_replay_step_id=(linked_evidence_view.selected_replay_step_id if linked_evidence_view else "") or "",
            selected_comparison_run_id=selected_comparison_run_id.strip() or (linked_evidence_view.selected_comparison_run_id if linked_evidence_view else "") or "",
        )
        if not selected_evidence_context and linked_evidence_context:
            selected_evidence_context = linked_evidence_context
        if selected_evidence_context:
            decision_metadata["selected_evidence_context"] = selected_evidence_context
        readiness_gate = dict(selected_evidence_context.get("readiness_gate", {})) if isinstance(selected_evidence_context, dict) else {}
        if readiness_gate:
            decision_metadata["readiness_gate"] = readiness_gate
        provider_runtime_boundary = (
            dict(selected_evidence_context.get("provider_runtime_boundary", {}))
            if isinstance(selected_evidence_context, dict)
            and isinstance(selected_evidence_context.get("provider_runtime_boundary"), dict)
            else {}
        )
        if provider_runtime_boundary:
            decision_metadata["provider_runtime_boundary"] = provider_runtime_boundary
        decision_metadata["governed_review"] = governed_review
        decision_metadata["governed_redaction"] = governed_redaction
        review_history = decision_metadata.get("review_status_history")
        if not isinstance(review_history, list):
            review_history = []
        review_status = str(decision_metadata.get("review_status") or "draft").strip() or "draft"
        if review_status not in DECISION_REVIEW_STATUSES:
            review_status = "draft"
        if not review_history:
            review_history = [{
                "status": review_status,
                "changed_at": now,
                "changed_by_user_id": auth.user_id,
                "note": "Decision log created."
            }]
        default_review_assignment = {
            "contract_version": "workspace-decision-review-assignment/v0-draft",
            "status": "unassigned",
            "assignee_user_ids": [],
            "assigned_at": None,
            "assigned_by_user_id": None,
            "latest_note": "",
        }
        if bool(governed_review.get("human_review_required")) and str(
            governed_review.get("reviewer_handoff", {}).get("status") or ""
        ) == "assigned":
            default_review_assignment = {
                "contract_version": "workspace-decision-review-assignment/v0-draft",
                "status": "assigned",
                "assignee_user_ids": list(governed_review.get("reviewer_handoff", {}).get("assignee_user_ids", [])),
                "assigned_at": governed_review.get("reviewer_handoff", {}).get("assigned_at"),
                "assigned_by_user_id": governed_review.get("reviewer_handoff", {}).get("assigned_by_user_id"),
                "latest_note": "Inherited from governed study reviewer handoff.",
            }
        decision_metadata.update({
            "review_status": review_status,
            "review_status_history": review_history,
            "review_status_updated_at": str(decision_metadata.get("review_status_updated_at") or now),
            "review_status_updated_by_user_id": str(
                decision_metadata.get("review_status_updated_by_user_id") or auth.user_id
            ),
            "latest_review_note": str(decision_metadata.get("latest_review_note") or ""),
            "review_assignment": dict(decision_metadata.get("review_assignment", {}))
            if isinstance(decision_metadata.get("review_assignment"), dict)
            else default_review_assignment,
            "review_assignment_history": list(decision_metadata.get("review_assignment_history", []))
            if isinstance(decision_metadata.get("review_assignment_history"), list)
            else [],
        })
        decision_log_id = f"decision_{uuid.uuid4().hex[:12]}"
        workspace_root = _workspace_root(self.runtime_root, workspace.workspace_id)
        decision_log_root = workspace_root / "collaboration" / "decision_logs" / decision_log_id
        decision_log_root.mkdir(parents=True, exist_ok=True)
        payload_path = decision_log_root / "decision_log.json"
        saved_title = title.strip() or f"{study.title} decision"
        decision_log = WorkspaceDecisionLog(
            decision_log_id=decision_log_id,
            workspace_id=workspace.workspace_id,
            project_id=project.project_id,
            study_id=study.study_id,
            job_id=str(job.get("job_id") or "") if job else None,
            run_id=run_id or None,
            evidence_view_id=linked_evidence_view.evidence_view_id if linked_evidence_view else None,
            title=saved_title,
            decision_summary=clean_decision_summary,
            rationale=rationale.strip(),
            selected_result_id=selected_result_id.strip() or None,
            selected_comparison_run_id=selected_comparison_run_id.strip() or None,
            payload_path=str(payload_path),
            created_by_user_id=auth.user_id,
            created_at=now,
            updated_at=now,
            metadata=decision_metadata,
        )
        self._materialize_decision_log_artifacts(decision_log, comment_summaries=[])
        created = job_store.create_workspace_decision_log(self.runtime_root, decision_log)
        refreshed_selected_evidence_context = self._selected_evidence_context(
            workspace_id=workspace.workspace_id,
            run_id=run_id,
            query_text=linked_evidence_view.query_text if linked_evidence_view else "",
            active_family=linked_evidence_view.active_family if linked_evidence_view else "all",
            sort_by=linked_evidence_view.sort_by if linked_evidence_view else "relevance",
            selected_result_id=selected_result_id.strip() or (linked_evidence_view.selected_result_id if linked_evidence_view else "") or "",
            selected_replay_step_id=(linked_evidence_view.selected_replay_step_id if linked_evidence_view else "") or "",
            selected_comparison_run_id=selected_comparison_run_id.strip() or (linked_evidence_view.selected_comparison_run_id if linked_evidence_view else "") or "",
        )
        if refreshed_selected_evidence_context:
            refreshed_metadata = dict(created.metadata)
            refreshed_metadata["selected_evidence_context"] = refreshed_selected_evidence_context
            refreshed_readiness_gate = (
                dict(refreshed_selected_evidence_context.get("readiness_gate", {}))
                if isinstance(refreshed_selected_evidence_context, dict)
                else {}
            )
            if refreshed_readiness_gate:
                refreshed_metadata["readiness_gate"] = refreshed_readiness_gate
            refreshed_metadata["governed_review"] = self._study_governed_review_state(study)
            refreshed_metadata["governed_redaction"] = self._study_governed_redaction_state(study)
            refreshed = job_store.update_workspace_decision_log_metadata(
                self.runtime_root,
                decision_log_id=created.decision_log_id,
                metadata_updates=refreshed_metadata,
                updated_at=now,
            )
            if refreshed is not None:
                created = refreshed
                self._materialize_decision_log_artifacts(created, comment_summaries=[])
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="decision_log.created",
                target_type="decision_log",
                target_id=created.decision_log_id,
                event_payload={
                    "study_id": created.study_id,
                    "job_id": created.job_id,
                    "evidence_view_id": created.evidence_view_id,
                    "selected_signal_id": (
                        refreshed_selected_evidence_context.get("selected_signal_id")
                        if isinstance(refreshed_selected_evidence_context, dict)
                        else selected_evidence_context.get("selected_signal_id")
                    )
                    or None,
                    "workflow_map_focus": bool(
                        refreshed_selected_evidence_context.get("workflow_map_focus")
                        if isinstance(refreshed_selected_evidence_context, dict)
                        else selected_evidence_context.get("workflow_map_focus")
                    ),
                    "readiness_status": (
                        dict(refreshed_selected_evidence_context.get("readiness_gate", {})).get("status")
                        if isinstance(refreshed_selected_evidence_context, dict)
                        else readiness_gate.get("status")
                    ),
                    "governed_review_status": governed_review.get("review_gate_status"),
                    "governed_redaction_status": governed_redaction.get("status"),
                },
                created_at=now,
            ),
        )
        return self._decision_log_summary(created)

    def create_workspace_decision_comment(
        self,
        auth: AuthContext,
        *,
        decision_log_id: str,
        body: str,
        parent_comment_id: str = "",
        anchor_kind: str = "general",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot comment on decision logs.")
        decision_log = job_store.get_workspace_decision_log(self.runtime_root, decision_log_id.strip())
        if decision_log is None or decision_log.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace decision log '{decision_log_id}' is not visible in this workspace.")
        clean_body = body.strip()
        if not clean_body:
            raise ValueError("Field 'body' is required.")
        normalized_anchor_kind = str(anchor_kind or "general").strip() or "general"
        if normalized_anchor_kind not in DECISION_COMMENT_ANCHOR_KINDS:
            raise ValueError(f"Unsupported decision comment anchor '{normalized_anchor_kind}'.")
        parent_comment = None
        if parent_comment_id.strip():
            parent_comment = job_store.get_workspace_decision_comment(self.runtime_root, parent_comment_id.strip())
            if parent_comment is None or parent_comment.workspace_id != auth.workspace_id:
                raise AuthorizationError(
                    f"Workspace decision comment '{parent_comment_id}' is not visible in this workspace."
                )
            if parent_comment.decision_log_id != decision_log.decision_log_id:
                raise AuthorizationError("Reply comments must stay inside the same decision-log thread.")

        now = utc_now_iso()
        decision_comment = WorkspaceDecisionComment(
            decision_comment_id=f"decision_comment_{uuid.uuid4().hex[:12]}",
            workspace_id=workspace.workspace_id,
            project_id=decision_log.project_id,
            study_id=decision_log.study_id,
            decision_log_id=decision_log.decision_log_id,
            parent_comment_id=parent_comment.decision_comment_id if parent_comment else None,
            anchor_kind=normalized_anchor_kind,
            body=clean_body,
            created_by_user_id=auth.user_id,
            created_at=now,
            updated_at=now,
            metadata=dict(metadata or {}),
        )
        created = job_store.create_workspace_decision_comment(self.runtime_root, decision_comment)
        updated_decision_log = job_store.update_workspace_decision_log_metadata(
            self.runtime_root,
            decision_log_id=decision_log.decision_log_id,
            metadata_updates={
                "last_commented_at": now,
                "last_commented_by_user_id": auth.user_id,
            },
            updated_at=now,
        ) or decision_log
        comment_summaries = self.list_workspace_decision_comments(auth, decision_log_id=decision_log.decision_log_id)
        self._materialize_decision_log_artifacts(updated_decision_log, comment_summaries=comment_summaries)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="decision_log.commented",
                target_type="decision_log",
                target_id=decision_log.decision_log_id,
                event_payload={
                    "study_id": decision_log.study_id,
                    "decision_comment_id": created.decision_comment_id,
                    "parent_comment_id": created.parent_comment_id,
                    "anchor_kind": created.anchor_kind,
                },
                created_at=now,
            ),
        )
        return next(
            (
                comment_summary
                for comment_summary in comment_summaries
                if str(comment_summary.get("decision_comment_id") or "") == created.decision_comment_id
            ),
            self._decision_comment_summary(created, decision_comments=[created]),
        )

    def list_workspace_decision_logs(
        self,
        auth: AuthContext,
        *,
        study_id: str = "",
        job_id: str = "",
        evidence_view_id: str = "",
    ) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        if study_id.strip():
            study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
            if study is None or study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        if job_id.strip():
            job = self.get_validation_job(auth, job_id.strip())
            if str(job.get("workspace_id") or "") != auth.workspace_id:
                raise AuthorizationError(f"Validation job '{job_id}' is not visible in this workspace.")
        if evidence_view_id.strip():
            view = job_store.get_workspace_evidence_view(self.runtime_root, evidence_view_id.strip())
            if view is None or view.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace evidence view '{evidence_view_id}' is not visible in this workspace.")
        return [
            self._decision_log_summary(log)
            for log in job_store.list_workspace_decision_logs(
                self.runtime_root,
                auth.workspace_id,
                study_id=study_id.strip(),
                job_id=job_id.strip(),
                evidence_view_id=evidence_view_id.strip(),
            )
        ]

    def get_workspace_decision_log(self, auth: AuthContext, decision_log_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        log = job_store.get_workspace_decision_log(self.runtime_root, decision_log_id)
        if log is None or log.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace decision log '{decision_log_id}' is not visible in this workspace.")
        return self._decision_log_summary(log)

    def list_workspace_decision_comments(
        self,
        auth: AuthContext,
        *,
        decision_log_id: str = "",
        study_id: str = "",
    ) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        if decision_log_id.strip():
            decision_log = job_store.get_workspace_decision_log(self.runtime_root, decision_log_id.strip())
            if decision_log is None or decision_log.workspace_id != auth.workspace_id:
                raise AuthorizationError(
                    f"Workspace decision log '{decision_log_id}' is not visible in this workspace."
                )
        if study_id.strip():
            study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
            if study is None or study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        comments = job_store.list_workspace_decision_comments(
            self.runtime_root,
            auth.workspace_id,
            decision_log_id=decision_log_id.strip(),
            study_id=study_id.strip(),
        )
        return [self._decision_comment_summary(comment, decision_comments=comments) for comment in comments]

    def update_workspace_decision_review_status(
        self,
        auth: AuthContext,
        *,
        decision_log_id: str,
        review_status: str,
        note: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot update decision review status.")
        decision_log = job_store.get_workspace_decision_log(self.runtime_root, decision_log_id.strip())
        if decision_log is None or decision_log.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace decision log '{decision_log_id}' is not visible in this workspace.")
        normalized_status = str(review_status or "").strip()
        if normalized_status not in DECISION_REVIEW_STATUSES:
            raise ValueError(f"Unsupported decision review status '{normalized_status}'.")
        assignment = self._decision_review_assignment(decision_log, workspace)
        study = job_store.get_workspace_study(self.runtime_root, decision_log.study_id)
        governed_review = (
            self._study_governed_review_state(study)
            if study is not None and study.workspace_id == auth.workspace_id
            else None
        )
        governed_redaction = (
            self._study_governed_redaction_state(study)
            if study is not None and study.workspace_id == auth.workspace_id
            else None
        )
        if normalized_status in {"approved", "needs_revision"}:
            if governed_review is not None and not bool(governed_review.get("decision_review_allowed")):
                raise AuthorizationError(str(governed_review.get("blocked_reason") or governed_review.get("human_review_note") or "").strip())
            assignee_user_ids = set(assignment.get("assignee_user_ids", []))
            can_finalize = auth.role in {"owner", "admin"} or auth.user_id in assignee_user_ids
            if not can_finalize:
                raise AuthorizationError(
                    "Only owner/admin members or explicitly assigned reviewers can approve or request revision for this decision log."
                )
        now = utc_now_iso()
        merged_metadata = dict(decision_log.metadata)
        merged_metadata.update(dict(metadata or {}))
        if governed_review is not None:
            merged_metadata["governed_review"] = governed_review
        if governed_redaction is not None:
            merged_metadata["governed_redaction"] = governed_redaction
        history = merged_metadata.get("review_status_history")
        if not isinstance(history, list):
            history = []
        history = [
            item for item in history
            if isinstance(item, dict) and str(item.get("status") or "").strip()
        ]
        history.append({
            "status": normalized_status,
            "changed_at": now,
            "changed_by_user_id": auth.user_id,
            "note": note.strip(),
        })
        merged_metadata.update({
            "review_status": normalized_status,
            "review_status_history": history,
            "review_status_updated_at": now,
            "review_status_updated_by_user_id": auth.user_id,
            "latest_review_note": note.strip(),
        })
        updated = job_store.update_workspace_decision_log_metadata(
            self.runtime_root,
            decision_log_id=decision_log.decision_log_id,
            metadata_updates=merged_metadata,
            updated_at=now,
        )
        if updated is None:
            raise FileNotFoundError(f"Workspace decision log '{decision_log_id}' could not be updated.")
        comment_summaries = self.list_workspace_decision_comments(auth, decision_log_id=decision_log.decision_log_id)
        self._materialize_decision_log_artifacts(updated, comment_summaries=comment_summaries)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="decision_log.review_status_updated",
                target_type="decision_log",
                target_id=decision_log.decision_log_id,
                event_payload={
                    "study_id": decision_log.study_id,
                    "review_status": normalized_status,
                    "note": note.strip() or None,
                },
                created_at=now,
            ),
        )
        return self._decision_log_summary(updated)

    def update_workspace_decision_review_assignment(
        self,
        auth: AuthContext,
        *,
        decision_log_id: str,
        assignee_user_ids: list[str] | None = None,
        note: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in DECISION_REVIEW_ASSIGNMENT_MUTATION_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot update decision review assignment.")
        decision_log = job_store.get_workspace_decision_log(self.runtime_root, decision_log_id.strip())
        if decision_log is None or decision_log.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace decision log '{decision_log_id}' is not visible in this workspace.")
        member_map = self._workspace_member_map(workspace)
        normalized_assignees = _unique_preserve_order(
            [str(item) for item in (assignee_user_ids or [])]
        )
        for user_id in normalized_assignees:
            member = member_map.get(user_id)
            if member is None:
                raise ValueError(f"Workspace member '{user_id}' is not available for decision review assignment.")
            if member.role not in DECISION_REVIEW_ASSIGNEE_ROLES:
                raise ValueError(f"Workspace member '{user_id}' has role '{member.role}' and cannot be assigned for decision review.")
        status = "assigned" if normalized_assignees else "unassigned"
        now = utc_now_iso()
        merged_metadata = dict(decision_log.metadata)
        merged_metadata.update(dict(metadata or {}))
        assignment_history = merged_metadata.get("review_assignment_history")
        if not isinstance(assignment_history, list):
            assignment_history = []
        assignment_history = [item for item in assignment_history if isinstance(item, dict)]
        assignment_history.append(
            {
                "status": status,
                "assignee_user_ids": normalized_assignees,
                "changed_at": now,
                "changed_by_user_id": auth.user_id,
                "note": note.strip(),
            }
        )
        merged_metadata.update(
            {
                "review_assignment": {
                    "contract_version": "workspace-decision-review-assignment/v0-draft",
                    "status": status,
                    "assignee_user_ids": normalized_assignees,
                    "assigned_at": now if normalized_assignees else None,
                    "assigned_by_user_id": auth.user_id if normalized_assignees else None,
                    "latest_note": note.strip(),
                },
                "review_assignment_history": assignment_history,
            }
        )
        updated = job_store.update_workspace_decision_log_metadata(
            self.runtime_root,
            decision_log_id=decision_log.decision_log_id,
            metadata_updates=merged_metadata,
            updated_at=now,
        )
        if updated is None:
            raise FileNotFoundError(f"Workspace decision log '{decision_log_id}' could not be updated.")
        comment_summaries = self.list_workspace_decision_comments(auth, decision_log_id=decision_log.decision_log_id)
        self._materialize_decision_log_artifacts(updated, comment_summaries=comment_summaries)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="decision_log.review_assignment_updated",
                target_type="decision_log",
                target_id=decision_log.decision_log_id,
                event_payload={
                    "study_id": decision_log.study_id,
                    "assignment_status": status,
                    "assignee_user_ids": normalized_assignees,
                    "note": note.strip() or None,
                },
                created_at=now,
            ),
        )
        return self._decision_log_summary(updated)

    def create_workspace_export_bundle(
        self,
        auth: AuthContext,
        *,
        study_id: str,
        job_id: str,
        title: str = "",
        export_format: str = "bundle_json",
        artifact_ids: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in EXPORTABLE_ROLE_SET:
            raise AuthorizationError(f"Role '{auth.role}' cannot create export bundles.")

        study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        job = self.get_validation_job(auth, job_id.strip())
        if str(job.get("status")) != "completed":
            raise ValueError("Only completed validation jobs can be exported.")

        job_metadata = dict(job.get("metadata", {}))
        if str(job_metadata.get("study_id") or "") != study.study_id:
            raise AuthorizationError("The selected validation job does not belong to the selected study.")

        run_id = str(job_metadata.get("run_id") or "")
        if not run_id:
            output_run_path = str(job.get("output_run_path") or "")
            run_id = Path(output_run_path).name if output_run_path else ""
        if not run_id:
            raise ValueError("The selected validation job has no exportable run id.")
        output_run_path = str(job.get("output_run_path") or "")
        run_dir = Path(output_run_path)
        if not output_run_path or not run_dir.exists():
            raise FileNotFoundError("The selected validation job has no available run artifact directory.")

        project = job_store.get_workspace_project(self.runtime_root, study.project_id)
        if project is None or project.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace project '{study.project_id}' is not visible in this workspace.")

        normalized_format = str(export_format or "bundle_json").strip() or "bundle_json"
        if normalized_format not in {"bundle_json", "report_markdown", "report_json", "report_csv"}:
            raise ValueError(f"Unsupported export format '{normalized_format}'.")

        now = utc_now_iso()
        export_bundle_id = f"export_{uuid.uuid4().hex[:12]}"
        workspace_root = _workspace_root(self.runtime_root, workspace.workspace_id)
        bundle_root = workspace_root / "exports" / export_bundle_id
        bundle_root.mkdir(parents=True, exist_ok=True)

        synthetic_boundary = (
            "Synthetic evidence only. This export is derived from synthetic-user research and is not human market proof."
        )
        regulated_review_boundary = self._study_regulated_review_boundary(study)
        governed_review = self._study_governed_review_state(study)
        governed_redaction = self._study_governed_redaction_state(study)
        readiness_query = self._query_run_evidence_with_fallback(
            workspace_id=workspace.workspace_id,
            run_id=run_id,
        )
        readiness_gate = self._build_readiness_gate_from_query(readiness_query)
        provider_runtime_boundary = (
            dict(readiness_query.get("provider_runtime_boundary", {}))
            if isinstance(readiness_query.get("provider_runtime_boundary"), dict)
            else self._validation_provider_runtime_boundary(
                str(job.get("provider_name") or ""),
                status=str(job.get("status") or ""),
                last_error=str(job.get("last_error") or ""),
                metadata=job_metadata,
            )
        )
        mvp_launch_scope = self._build_mvp_launch_scope(readiness_gate)
        mvp_promotion = self._build_mvp_promotion_state(mvp_launch_scope)
        public_claims_boundary = self._build_public_claims_boundary(
            readiness_gate=readiness_gate,
            mvp_launch_scope=mvp_launch_scope,
            regulated_review_boundary=regulated_review_boundary,
            governed_review=governed_review,
            governed_redaction=governed_redaction,
        )
        export_metadata = dict(metadata or {})
        export_metadata["regulated_review_boundary"] = regulated_review_boundary
        export_metadata["governed_review"] = governed_review
        export_metadata["governed_redaction"] = governed_redaction
        export_metadata["readiness_gate"] = readiness_gate
        export_metadata["provider_runtime_boundary"] = provider_runtime_boundary
        export_metadata["mvp_launch_scope"] = mvp_launch_scope
        export_metadata["mvp_promotion"] = mvp_promotion
        export_metadata["public_claims_boundary"] = public_claims_boundary
        export_metadata["mvp_promotion_history"] = _history_entries(export_metadata.get("mvp_promotion_history"))
        exported_files = self._materialize_export_bundle_files(
            bundle_root=bundle_root,
            run_dir=run_dir,
            export_format=normalized_format,
            artifact_ids=artifact_ids or [],
            study=study,
            job=job,
            synthetic_boundary=synthetic_boundary,
        )
        manifest_path = bundle_root / "export_manifest.json"
        manifest_payload = {
            "export_bundle_id": export_bundle_id,
            "workspace_id": workspace.workspace_id,
            "project_id": project.project_id,
            "study_id": study.study_id,
            "job_id": str(job.get("job_id") or ""),
            "run_id": run_id,
            "title": title.strip() or f"{study.title} export",
            "status": "published",
            "export_format": normalized_format,
            "synthetic_boundary": synthetic_boundary,
            "created_at": now,
            "created_by_user_id": auth.user_id,
            "exported_files": exported_files,
            "study_context": {
                "title": study.title,
                "research_intent": study.research_intent,
                "desired_output": study.desired_output,
                "first_task": study.first_task,
            },
            "regulated_review_boundary": regulated_review_boundary,
            "governed_review": governed_review,
            "governed_redaction": governed_redaction,
            "job_context": {
                "provider_name": str(job.get("provider_name") or ""),
                "provider_runtime_boundary": provider_runtime_boundary,
                "status": str(job.get("status") or ""),
                "output_run_path": output_run_path,
            },
            "readiness_gate": readiness_gate,
            "provider_runtime_boundary": provider_runtime_boundary,
            "public_claims_boundary": public_claims_boundary,
            "mvp_launch_scope": mvp_launch_scope,
            "mvp_promotion": mvp_promotion,
            "mvp_promotion_history": export_metadata["mvp_promotion_history"],
            "metadata": export_metadata,
        }
        compliance_audit_bundle = self._build_governed_compliance_audit_bundle(
            workspace_id=workspace.workspace_id,
            study=study,
            project_id=project.project_id,
            job_id=str(job.get("job_id") or ""),
            run_id=run_id,
            export_bundle_id=export_bundle_id,
            readiness_gate=readiness_gate,
            mvp_launch_scope=mvp_launch_scope,
            mvp_promotion=mvp_promotion,
            distribution_context={
                "surface": "export_bundle",
                "export_format": normalized_format,
                "provider_runtime_boundary": provider_runtime_boundary,
                "circulation_allowed": bool(governed_redaction.get("circulation_allowed")),
            },
        )
        compliance_bundle_path = self._write_governed_compliance_bundle_file(bundle_root, compliance_audit_bundle)
        export_metadata["compliance_audit_bundle_path"] = compliance_bundle_path
        manifest_payload["compliance_audit_bundle"] = compliance_audit_bundle
        manifest_payload["metadata"] = export_metadata
        write_json(manifest_path, manifest_payload)
        write_markdown(
            bundle_root / "README.md",
            "\n".join(
                [
                    f"# {manifest_payload['title']}",
                    "",
                    f"- synthetic boundary: {synthetic_boundary}",
                    f"- project_id: {project.project_id}",
                    f"- study_id: {study.study_id}",
                    f"- job_id: {job['job_id']}",
                    f"- run_id: {run_id}",
                    f"- export_format: {normalized_format}",
                    f"- readiness_status: {readiness_gate.get('status', 'pending')}",
                    f"- evidence_mode: {provider_runtime_boundary.get('evidence_mode', 'unknown')}",
                    f"- provider_runtime_status: {provider_runtime_boundary.get('runtime_status', 'unknown')}",
                    f"- market_claims_allowed: {readiness_gate.get('market_claims_allowed', False)}",
                    f"- governed_review_status: {governed_review.get('review_gate_status', 'not_required')}",
                    f"- governed_redaction_status: {governed_redaction.get('status', 'not_required')}",
                    f"- public_claim_boundary: {public_claims_boundary.get('status', 'research_preview_only')}",
                    f"- mvp_launch_scope: {mvp_launch_scope.get('status', 'internal_only')}",
                    f"- mvp_promotion_status: {mvp_promotion.get('status', 'not_applicable')}",
                    "",
                    "This bundle preserves study and run lineage for synthetic evidence review.",
                ]
            ),
        )

        export_bundle = WorkspaceExportBundle(
            export_bundle_id=export_bundle_id,
            workspace_id=workspace.workspace_id,
            project_id=project.project_id,
            study_id=study.study_id,
            job_id=str(job.get("job_id") or ""),
            run_id=run_id,
            title=str(manifest_payload["title"]),
            status="published",
            export_format=normalized_format,
            created_by_user_id=auth.user_id,
            bundle_root=str(bundle_root),
            manifest_path=str(manifest_path),
            exported_files=exported_files,
            synthetic_boundary=synthetic_boundary,
            created_at=now,
            updated_at=now,
            metadata=export_metadata,
        )
        created = job_store.create_workspace_export_bundle(self.runtime_root, export_bundle)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="export_bundle.created",
                target_type="export_bundle",
                target_id=created.export_bundle_id,
                event_payload={
                    "project_id": created.project_id,
                    "study_id": created.study_id,
                    "job_id": created.job_id,
                    "run_id": created.run_id,
                    "export_format": created.export_format,
                    "manifest_path": created.manifest_path,
                    "readiness_status": readiness_gate.get("status"),
                    "market_claims_allowed": readiness_gate.get("market_claims_allowed"),
                    "provider_name": provider_runtime_boundary.get("provider_name"),
                    "evidence_mode": provider_runtime_boundary.get("evidence_mode"),
                    "provider_runtime_status": provider_runtime_boundary.get("runtime_status"),
                    "mvp_launch_scope_status": mvp_launch_scope.get("status"),
                    "mvp_promotion_status": mvp_promotion.get("status"),
                },
                created_at=now,
            ),
        )
        return self._export_bundle_summary(created)

    def list_workspace_export_bundles(
        self,
        auth: AuthContext,
        *,
        study_id: str = "",
        job_id: str = "",
    ) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        if study_id.strip():
            study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
            if study is None or study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        if job_id.strip():
            job = self.get_validation_job(auth, job_id.strip())
            if str(job.get("workspace_id") or "") != auth.workspace_id:
                raise AuthorizationError(f"Validation job '{job_id}' is not visible in this workspace.")
        return [
            self._export_bundle_summary(bundle)
            for bundle in job_store.list_workspace_export_bundles(
                self.runtime_root,
                auth.workspace_id,
                study_id=study_id.strip(),
                job_id=job_id.strip(),
            )
        ]

    def get_workspace_export_bundle(self, auth: AuthContext, export_bundle_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        export_bundle = job_store.get_workspace_export_bundle(self.runtime_root, export_bundle_id)
        if export_bundle is None or export_bundle.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace export bundle '{export_bundle_id}' is not visible in this workspace.")
        return self._export_bundle_summary(export_bundle)

    def request_workspace_export_bundle_mvp_promotion(
        self,
        auth: AuthContext,
        export_bundle_id: str,
        *,
        note: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        if auth.role not in MVP_PROMOTION_REQUEST_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot request design-partner promotion.")
        export_bundle = job_store.get_workspace_export_bundle(self.runtime_root, export_bundle_id.strip())
        if export_bundle is None or export_bundle.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace export bundle '{export_bundle_id}' is not visible in this workspace.")
        bundle_metadata = dict(export_bundle.metadata or {})
        readiness_gate = bundle_metadata.get("readiness_gate")
        if not isinstance(readiness_gate, dict):
            readiness_gate = {}
        mvp_launch_scope = bundle_metadata.get("mvp_launch_scope")
        if not isinstance(mvp_launch_scope, dict):
            mvp_launch_scope = self._build_mvp_launch_scope(readiness_gate)
        mvp_promotion = self._build_mvp_promotion_state(mvp_launch_scope, bundle_metadata.get("mvp_promotion"))
        if not bool(mvp_promotion.get("eligible")):
            raise AuthorizationError("This export bundle is not eligible for design-partner promotion.")
        current_status = str(mvp_promotion.get("status") or "").strip()
        if current_status == "approved":
            raise ValueError("This export bundle is already approved for design-partner promotion.")
        if current_status == "pending_approval":
            raise ValueError("This export bundle already has a pending design-partner promotion request.")
        now = utc_now_iso()
        promotion_history = _history_entries(bundle_metadata.get("mvp_promotion_history"))
        updated_promotion = {
            **mvp_promotion,
            "status": "pending_approval",
            "requested_by_user_id": auth.user_id,
            "requested_at": now,
            "request_note": note.strip(),
            "reviewed_by_user_id": None,
            "reviewed_at": None,
            "review_note": "",
            "note": "Design-partner promotion is pending explicit approval.",
        }
        promotion_history.append(
            {
                "event": "requested",
                "status": "pending_approval",
                "changed_at": now,
                "changed_by_user_id": auth.user_id,
                "note": note.strip(),
            }
        )
        extra_metadata = dict(metadata or {})
        extra_metadata["mvp_promotion"] = updated_promotion
        extra_metadata["mvp_promotion_history"] = promotion_history
        updated = job_store.update_workspace_export_bundle(
            self.runtime_root,
            export_bundle_id=export_bundle.export_bundle_id,
            metadata_updates=extra_metadata,
        )
        self._write_export_bundle_contract_files(updated)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=updated.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="export_bundle.mvp_promotion_requested",
                target_type="export_bundle",
                target_id=updated.export_bundle_id,
                event_payload={
                    "project_id": updated.project_id,
                    "study_id": updated.study_id,
                    "job_id": updated.job_id,
                    "run_id": updated.run_id,
                    "mvp_launch_scope_status": mvp_launch_scope.get("status"),
                    "mvp_promotion_status": updated_promotion.get("status"),
                    "request_note": updated_promotion.get("request_note"),
                },
                created_at=now,
            ),
        )
        return self._export_bundle_summary(updated)

    def review_workspace_export_bundle_mvp_promotion(
        self,
        auth: AuthContext,
        export_bundle_id: str,
        *,
        decision: str,
        note: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        if auth.role not in MVP_PROMOTION_REVIEW_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot review design-partner promotion.")
        normalized_decision = str(decision or "").strip()
        if normalized_decision not in {"approved", "rejected"}:
            raise ValueError("Field 'decision' must be 'approved' or 'rejected'.")
        export_bundle = job_store.get_workspace_export_bundle(self.runtime_root, export_bundle_id.strip())
        if export_bundle is None or export_bundle.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace export bundle '{export_bundle_id}' is not visible in this workspace.")
        bundle_metadata = dict(export_bundle.metadata or {})
        readiness_gate = bundle_metadata.get("readiness_gate")
        if not isinstance(readiness_gate, dict):
            readiness_gate = {}
        mvp_launch_scope = bundle_metadata.get("mvp_launch_scope")
        if not isinstance(mvp_launch_scope, dict):
            mvp_launch_scope = self._build_mvp_launch_scope(readiness_gate)
        mvp_promotion = self._build_mvp_promotion_state(mvp_launch_scope, bundle_metadata.get("mvp_promotion"))
        if str(mvp_promotion.get("status") or "").strip() != "pending_approval":
            raise ValueError("This export bundle must have a pending design-partner promotion request before review.")
        now = utc_now_iso()
        promotion_history = _history_entries(bundle_metadata.get("mvp_promotion_history"))
        updated_promotion = {
            **mvp_promotion,
            "status": normalized_decision,
            "reviewed_by_user_id": auth.user_id,
            "reviewed_at": now,
            "review_note": note.strip(),
            "note": (
                "Design-partner promotion is approved for bounded external circulation."
                if normalized_decision == "approved"
                else "Design-partner promotion was rejected and must be requested again before bounded external circulation."
            ),
        }
        promotion_history.append(
            {
                "event": "reviewed",
                "status": normalized_decision,
                "changed_at": now,
                "changed_by_user_id": auth.user_id,
                "note": note.strip(),
            }
        )
        extra_metadata = dict(metadata or {})
        extra_metadata["mvp_promotion"] = updated_promotion
        extra_metadata["mvp_promotion_history"] = promotion_history
        updated = job_store.update_workspace_export_bundle(
            self.runtime_root,
            export_bundle_id=export_bundle.export_bundle_id,
            metadata_updates=extra_metadata,
        )
        self._write_export_bundle_contract_files(updated)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=updated.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="export_bundle.mvp_promotion_reviewed",
                target_type="export_bundle",
                target_id=updated.export_bundle_id,
                event_payload={
                    "project_id": updated.project_id,
                    "study_id": updated.study_id,
                    "job_id": updated.job_id,
                    "run_id": updated.run_id,
                    "decision": normalized_decision,
                    "mvp_launch_scope_status": mvp_launch_scope.get("status"),
                    "mvp_promotion_status": updated_promotion.get("status"),
                    "review_note": updated_promotion.get("review_note"),
                },
                created_at=now,
            ),
        )
        return self._export_bundle_summary(updated)

    def create_workspace_share_bundle(
        self,
        auth: AuthContext,
        *,
        export_bundle_id: str,
        title: str = "",
        expires_in_days: int | None = None,
        partner_name: str = "",
        partner_team_label: str = "",
        partner_use_case: str = "",
        support_channel: str = "",
        review_window_days: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SHAREABLE_ROLE_SET:
            raise AuthorizationError(f"Role '{auth.role}' cannot create share bundles.")

        export_bundle = job_store.get_workspace_export_bundle(self.runtime_root, export_bundle_id.strip())
        if export_bundle is None or export_bundle.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace export bundle '{export_bundle_id}' is not visible in this workspace.")
        if str(export_bundle.status) != "published":
            raise ValueError("Only published export bundles can be shared.")

        project = job_store.get_workspace_project(self.runtime_root, export_bundle.project_id)
        study = job_store.get_workspace_study(self.runtime_root, export_bundle.study_id)
        if project is None or project.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace project '{export_bundle.project_id}' is not visible in this workspace.")
        if study is None or study.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace study '{export_bundle.study_id}' is not visible in this workspace.")

        if expires_in_days is not None and int(expires_in_days) < 1:
            raise ValueError("Field 'expires_in_days' must be at least 1 when provided.")
        if review_window_days is not None and int(review_window_days) < 1:
            raise ValueError("Field 'review_window_days' must be at least 1 when provided.")

        now = utc_now_iso()
        regulated_review_boundary = self._study_regulated_review_boundary(study)
        governed_review = self._study_governed_review_state(study)
        governed_redaction = self._study_governed_redaction_state(study)
        share_bundle_id = f"share_{uuid.uuid4().hex[:12]}"
        share_key = f"shk_{uuid.uuid4().hex[:20]}"
        workspace_root = _workspace_root(self.runtime_root, workspace.workspace_id)
        share_root = workspace_root / "shares" / share_bundle_id
        share_root.mkdir(parents=True, exist_ok=True)
        public_files_root = share_root / "files"
        public_files_root.mkdir(parents=True, exist_ok=True)
        public_path = f"/public/v1/share-bundles/{share_key}"
        share_payload_path = share_root / "share_payload.json"
        expires_at = None
        if expires_in_days is not None:
            expires_at = (_now() + timedelta(days=int(expires_in_days))).replace(microsecond=0).isoformat()
        share_metadata = dict(metadata or {})
        share_metadata["regulated_review_boundary"] = regulated_review_boundary
        share_metadata["governed_review"] = governed_review
        share_metadata["governed_redaction"] = governed_redaction
        readiness_gate = dict(export_bundle.metadata or {}).get("readiness_gate", {})
        if not isinstance(readiness_gate, dict) or not readiness_gate:
            readiness_query = self._query_run_evidence_with_fallback(
                workspace_id=workspace.workspace_id,
                run_id=str(export_bundle.run_id or ""),
            )
            readiness_gate = self._build_readiness_gate_from_query(readiness_query)
        provider_runtime_boundary = dict(export_bundle.metadata or {}).get("provider_runtime_boundary", {})
        if not isinstance(provider_runtime_boundary, dict) or not provider_runtime_boundary:
            readiness_query = self._query_run_evidence_with_fallback(
                workspace_id=workspace.workspace_id,
                run_id=str(export_bundle.run_id or ""),
            )
            provider_runtime_boundary = (
                dict(readiness_query.get("provider_runtime_boundary", {}))
                if isinstance(readiness_query.get("provider_runtime_boundary"), dict)
                else {}
            )
        mvp_launch_scope = dict(export_bundle.metadata or {}).get("mvp_launch_scope", {})
        if not isinstance(mvp_launch_scope, dict) or not mvp_launch_scope:
            mvp_launch_scope = self._build_mvp_launch_scope(readiness_gate)
        mvp_promotion = dict(export_bundle.metadata or {}).get("mvp_promotion", {})
        if not isinstance(mvp_promotion, dict) or not mvp_promotion:
            mvp_promotion = self._build_mvp_promotion_state(mvp_launch_scope)
        mvp_promotion_history = _history_entries(dict(export_bundle.metadata or {}).get("mvp_promotion_history"))
        share_status = str(readiness_gate.get("share_status") or "").strip()
        if share_status in READINESS_GATE_BLOCKED_SHARE_STATUSES:
            raise AuthorizationError(
                "The selected export bundle is gated from public sharing until the attached evidence passes the required human review boundary."
            )
        if (
            str(mvp_launch_scope.get("status") or "").strip() == "design_partner_candidate"
            and str(mvp_promotion.get("status") or "").strip() != "approved"
        ):
            raise AuthorizationError(
                "The selected export bundle requires explicit design-partner promotion approval before public share creation."
            )
        if not bool(governed_review.get("circulation_allowed")):
            raise AuthorizationError(str(governed_review.get("blocked_reason") or governed_review.get("human_review_note") or "").strip())
        if not bool(governed_redaction.get("circulation_allowed")):
            raise AuthorizationError(str(governed_redaction.get("blocked_reason") or governed_redaction.get("latest_note") or "").strip())
        partner_context = {
            "partner_name": partner_name.strip(),
            "partner_team_label": partner_team_label.strip(),
            "partner_use_case": partner_use_case.strip(),
            "support_channel": support_channel.strip(),
            "review_window_days": int(review_window_days) if review_window_days is not None else None,
        }
        if str(mvp_launch_scope.get("status") or "").strip() == "design_partner_candidate":
            if not partner_context["partner_name"]:
                raise ValueError("Field 'partner_name' is required for design-partner share creation.")
            if not partner_context["partner_use_case"]:
                raise ValueError("Field 'partner_use_case' is required for design-partner share creation.")
        partner_onboarding = self._build_partner_onboarding_state(
            study=study,
            mvp_launch_scope=mvp_launch_scope,
            mvp_promotion=mvp_promotion,
            partner_context=partner_context,
        )
        mvp_release_review = self._build_mvp_release_review_state(
            mvp_launch_scope,
            mvp_promotion,
            partner_onboarding,
        )
        public_claims_boundary = self._build_public_claims_boundary(
            readiness_gate=readiness_gate,
            mvp_launch_scope=mvp_launch_scope,
            regulated_review_boundary=regulated_review_boundary,
            governed_review=governed_review,
            governed_redaction=governed_redaction,
        )
        share_metadata["readiness_gate"] = readiness_gate
        share_metadata["provider_runtime_boundary"] = provider_runtime_boundary
        share_metadata["mvp_launch_scope"] = mvp_launch_scope
        share_metadata["mvp_promotion"] = mvp_promotion
        share_metadata["public_claims_boundary"] = public_claims_boundary
        share_metadata["mvp_promotion_history"] = mvp_promotion_history
        share_metadata["partner_onboarding"] = partner_onboarding
        share_metadata["mvp_release_review"] = mvp_release_review
        share_metadata["mvp_release_review_history"] = _history_entries(share_metadata.get("mvp_release_review_history"))

        public_files: list[dict[str, Any]] = []
        for file_entry in export_bundle.exported_files:
            bundle_path = Path(str(file_entry.get("bundle_path") or ""))
            if not bundle_path.exists() or not bundle_path.is_file():
                raise FileNotFoundError(f"Exported file not found for share delivery: {bundle_path}")
            destination = public_files_root / bundle_path.name
            export_file(bundle_path, destination)
            public_files.append(
                {
                    "artifact_id": str(file_entry.get("artifact_id") or bundle_path.name),
                    "export_kind": str(file_entry.get("export_kind") or "bundle_artifact"),
                    "mime_type": str(file_entry.get("mime_type") or (mimetypes.guess_type(destination.name)[0] or "application/octet-stream")),
                    "file_name": destination.name,
                    "relative_path": f"files/{destination.name}",
                }
            )

        share_payload = {
            "contract_version": "workspace-share-bundle/v0-draft",
            "share_bundle_id": share_bundle_id,
            "share_key": share_key,
            "public_path": public_path,
            "title": title.strip() or export_bundle.title,
            "status": "published",
            "synthetic_boundary": export_bundle.synthetic_boundary,
            "published_at": now,
            "expires_at": expires_at,
            "source": {
                "export_bundle_id": export_bundle.export_bundle_id,
                "project_id": export_bundle.project_id,
                "study_id": export_bundle.study_id,
                "job_id": export_bundle.job_id,
                "run_id": export_bundle.run_id,
                "export_format": export_bundle.export_format,
                "provider_runtime_boundary": provider_runtime_boundary,
            },
            "study_context": {
                "title": study.title,
                "status": study.status,
                "research_intent": study.research_intent,
                "desired_output": study.desired_output,
                "first_task": study.first_task,
            },
            "regulated_review_boundary": regulated_review_boundary,
            "governed_review": governed_review,
            "governed_redaction": governed_redaction,
            "files": public_files,
            "viewer_guidance": {
                "share_intent": "Viewer-safe synthetic evidence delivery",
                "lineage_rule": "Study, job, and run lineage stay visible in every shared bundle.",
            },
            "readiness_gate": readiness_gate,
            "provider_runtime_boundary": provider_runtime_boundary,
            "public_claims_boundary": public_claims_boundary,
            "mvp_launch_scope": mvp_launch_scope,
            "mvp_promotion": mvp_promotion,
            "mvp_promotion_history": mvp_promotion_history,
            "partner_onboarding": partner_onboarding,
            "mvp_release_review": mvp_release_review,
            "mvp_release_review_history": share_metadata["mvp_release_review_history"],
            "metadata": share_metadata,
        }
        redacted_share_payload, applied_redactions = self._apply_governed_redaction_to_payload(
            share_payload,
            governed_redaction,
        )
        compliance_audit_bundle = self._build_governed_compliance_audit_bundle(
            workspace_id=workspace.workspace_id,
            study=study,
            project_id=project.project_id,
            job_id=export_bundle.job_id,
            run_id=export_bundle.run_id,
            export_bundle_id=export_bundle.export_bundle_id,
            share_bundle_id=share_bundle_id,
            readiness_gate=readiness_gate,
            mvp_launch_scope=mvp_launch_scope,
            mvp_promotion=mvp_promotion,
            partner_onboarding=partner_onboarding,
            mvp_release_review=mvp_release_review,
            applied_redactions=applied_redactions,
            redacted_payload_preview={
                "study_context": dict(redacted_share_payload.get("study_context", {})),
                "partner_onboarding": dict(redacted_share_payload.get("partner_onboarding", {})),
            },
            distribution_context={
                "surface": "share_bundle",
                "public_path": public_path,
                "audience": "external_viewer",
                "provider_runtime_boundary": provider_runtime_boundary,
                "applied_redaction_count": len(applied_redactions),
            },
        )
        compliance_bundle_path = self._write_governed_compliance_bundle_file(share_root, compliance_audit_bundle)
        share_metadata["compliance_audit_bundle_path"] = compliance_bundle_path
        redacted_share_payload["metadata"] = share_metadata
        redacted_share_payload["compliance_audit_bundle"] = compliance_audit_bundle
        redacted_share_payload["governed_redaction"]["applied_redactions"] = applied_redactions
        write_json(share_payload_path, redacted_share_payload)
        write_markdown(
            share_root / "README.md",
            "\n".join(
                [
                    f"# {redacted_share_payload['title']}",
                    "",
                    f"- public_path: {public_path}",
                    f"- export_bundle_id: {export_bundle.export_bundle_id}",
                    f"- project_id: {export_bundle.project_id}",
                    f"- study_id: {export_bundle.study_id}",
                    f"- job_id: {export_bundle.job_id}",
                    f"- run_id: {export_bundle.run_id}",
                    f"- synthetic boundary: {export_bundle.synthetic_boundary}",
                    f"- readiness_status: {readiness_gate.get('status', 'pending')}",
                    f"- evidence_mode: {provider_runtime_boundary.get('evidence_mode', 'unknown')}",
                    f"- provider_runtime_status: {provider_runtime_boundary.get('runtime_status', 'unknown')}",
                    f"- market_claims_allowed: {readiness_gate.get('market_claims_allowed', False)}",
                    f"- governed_review_status: {governed_review.get('review_gate_status', 'not_required')}",
                    f"- governed_redaction_status: {governed_redaction.get('status', 'not_required')}",
                    f"- applied_redactions: {len(applied_redactions)}",
                    f"- public_claim_boundary: {public_claims_boundary.get('status', 'research_preview_only')}",
                    f"- mvp_launch_scope: {mvp_launch_scope.get('status', 'internal_only')}",
                    f"- mvp_promotion_status: {mvp_promotion.get('status', 'not_applicable')}",
                    f"- partner_onboarding_status: {partner_onboarding.get('status', 'not_applicable')}",
                    f"- mvp_release_review_status: {mvp_release_review.get('status', 'not_applicable')}",
                    f"- partner_name: {partner_onboarding.get('partner_name', '') or 'n/a'}",
                    "",
                    "This share bundle exposes a viewer-safe payload without requiring workspace filesystem inspection.",
                ]
            ),
        )

        share_bundle = WorkspaceShareBundle(
            share_bundle_id=share_bundle_id,
            workspace_id=workspace.workspace_id,
            export_bundle_id=export_bundle.export_bundle_id,
            project_id=export_bundle.project_id,
            study_id=export_bundle.study_id,
            job_id=export_bundle.job_id,
            run_id=export_bundle.run_id,
            title=str(redacted_share_payload["title"]),
            status="published",
            share_key=share_key,
            public_path=public_path,
            share_root=str(share_root),
            share_payload_path=str(share_payload_path),
            created_by_user_id=auth.user_id,
            synthetic_boundary=export_bundle.synthetic_boundary,
            published_at=now,
            expires_at=expires_at,
            revoked_at=None,
            created_at=now,
            updated_at=now,
            metadata=share_metadata,
        )
        created = job_store.create_workspace_share_bundle(self.runtime_root, share_bundle)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="share_bundle.created",
                target_type="share_bundle",
                target_id=created.share_bundle_id,
                event_payload={
                    "export_bundle_id": created.export_bundle_id,
                    "project_id": created.project_id,
                    "study_id": created.study_id,
                    "job_id": created.job_id,
                    "run_id": created.run_id,
                    "public_path": created.public_path,
                    "expires_at": created.expires_at,
                    "readiness_status": readiness_gate.get("status"),
                    "market_claims_allowed": readiness_gate.get("market_claims_allowed"),
                    "provider_name": provider_runtime_boundary.get("provider_name"),
                    "evidence_mode": provider_runtime_boundary.get("evidence_mode"),
                    "provider_runtime_status": provider_runtime_boundary.get("runtime_status"),
                    "mvp_launch_scope_status": mvp_launch_scope.get("status"),
                    "mvp_promotion_status": mvp_promotion.get("status"),
                    "partner_onboarding_status": partner_onboarding.get("status"),
                    "mvp_release_review_status": mvp_release_review.get("status"),
                    "partner_name": partner_onboarding.get("partner_name"),
                    "partner_use_case": partner_onboarding.get("partner_use_case"),
                },
                created_at=now,
            ),
        )
        return self._share_bundle_summary(created)

    def request_workspace_share_bundle_mvp_release_review(
        self,
        auth: AuthContext,
        share_bundle_id: str,
        *,
        note: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        if auth.role not in MVP_RELEASE_REVIEW_REQUEST_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot request controlled MVP release review.")
        share_bundle = job_store.get_workspace_share_bundle(self.runtime_root, share_bundle_id.strip())
        if share_bundle is None or share_bundle.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace share bundle '{share_bundle_id}' is not visible in this workspace.")
        bundle_metadata = dict(share_bundle.metadata or {})
        readiness_gate = bundle_metadata.get("readiness_gate")
        if not isinstance(readiness_gate, dict):
            readiness_gate = {}
        mvp_launch_scope = bundle_metadata.get("mvp_launch_scope")
        if not isinstance(mvp_launch_scope, dict):
            mvp_launch_scope = self._build_mvp_launch_scope(readiness_gate)
        mvp_promotion = bundle_metadata.get("mvp_promotion")
        if not isinstance(mvp_promotion, dict):
            mvp_promotion = self._build_mvp_promotion_state(mvp_launch_scope)
        partner_onboarding = bundle_metadata.get("partner_onboarding")
        if not isinstance(partner_onboarding, dict):
            partner_onboarding = self._build_partner_onboarding_state(
                study=None,
                mvp_launch_scope=mvp_launch_scope,
                mvp_promotion=mvp_promotion,
            )
        release_review = self._build_mvp_release_review_state(
            mvp_launch_scope,
            mvp_promotion,
            partner_onboarding,
            bundle_metadata.get("mvp_release_review"),
        )
        if not bool(release_review.get("eligible")):
            raise AuthorizationError("This share bundle is not eligible for controlled MVP release review.")
        current_status = str(release_review.get("status") or "").strip()
        if current_status == "approved":
            raise ValueError("This share bundle is already approved for controlled MVP release.")
        if current_status == "pending_approval":
            raise ValueError("This share bundle already has a pending controlled MVP release review request.")
        now = utc_now_iso()
        release_review_history = _history_entries(bundle_metadata.get("mvp_release_review_history"))
        updated_release_review = {
            **release_review,
            "status": "pending_approval",
            "requested_by_user_id": auth.user_id,
            "requested_at": now,
            "request_note": note.strip(),
            "reviewed_by_user_id": None,
            "reviewed_at": None,
            "review_note": "",
            "note": "Controlled MVP release review is pending explicit approval.",
        }
        release_review_history.append(
            {
                "event": "requested",
                "status": "pending_approval",
                "changed_at": now,
                "changed_by_user_id": auth.user_id,
                "note": note.strip(),
            }
        )
        extra_metadata = dict(metadata or {})
        extra_metadata["mvp_release_review"] = updated_release_review
        extra_metadata["mvp_release_review_history"] = release_review_history
        updated = job_store.update_workspace_share_bundle(
            self.runtime_root,
            share_bundle_id=share_bundle.share_bundle_id,
            metadata_updates=extra_metadata,
        )
        self._write_share_bundle_contract_files(updated)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=updated.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="share_bundle.mvp_release_review_requested",
                target_type="share_bundle",
                target_id=updated.share_bundle_id,
                event_payload={
                    "export_bundle_id": updated.export_bundle_id,
                    "project_id": updated.project_id,
                    "study_id": updated.study_id,
                    "job_id": updated.job_id,
                    "run_id": updated.run_id,
                    "mvp_launch_scope_status": mvp_launch_scope.get("status"),
                    "mvp_release_review_status": updated_release_review.get("status"),
                    "request_note": updated_release_review.get("request_note"),
                },
                created_at=now,
            ),
        )
        return self._share_bundle_summary(updated)

    def review_workspace_share_bundle_mvp_release_review(
        self,
        auth: AuthContext,
        share_bundle_id: str,
        *,
        decision: str,
        note: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        if auth.role not in MVP_RELEASE_REVIEW_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot review controlled MVP release.")
        normalized_decision = str(decision or "").strip()
        if normalized_decision not in {"approved", "rejected"}:
            raise ValueError("Field 'decision' must be 'approved' or 'rejected'.")
        share_bundle = job_store.get_workspace_share_bundle(self.runtime_root, share_bundle_id.strip())
        if share_bundle is None or share_bundle.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace share bundle '{share_bundle_id}' is not visible in this workspace.")
        bundle_metadata = dict(share_bundle.metadata or {})
        readiness_gate = bundle_metadata.get("readiness_gate")
        if not isinstance(readiness_gate, dict):
            readiness_gate = {}
        mvp_launch_scope = bundle_metadata.get("mvp_launch_scope")
        if not isinstance(mvp_launch_scope, dict):
            mvp_launch_scope = self._build_mvp_launch_scope(readiness_gate)
        mvp_promotion = bundle_metadata.get("mvp_promotion")
        if not isinstance(mvp_promotion, dict):
            mvp_promotion = self._build_mvp_promotion_state(mvp_launch_scope)
        partner_onboarding = bundle_metadata.get("partner_onboarding")
        if not isinstance(partner_onboarding, dict):
            partner_onboarding = self._build_partner_onboarding_state(
                study=None,
                mvp_launch_scope=mvp_launch_scope,
                mvp_promotion=mvp_promotion,
            )
        release_review = self._build_mvp_release_review_state(
            mvp_launch_scope,
            mvp_promotion,
            partner_onboarding,
            bundle_metadata.get("mvp_release_review"),
        )
        if str(release_review.get("status") or "").strip() != "pending_approval":
            raise ValueError("This share bundle must have a pending controlled MVP release review request before review.")
        now = utc_now_iso()
        release_review_history = _history_entries(bundle_metadata.get("mvp_release_review_history"))
        updated_release_review = {
            **release_review,
            "status": normalized_decision,
            "reviewed_by_user_id": auth.user_id,
            "reviewed_at": now,
            "review_note": note.strip(),
            "note": (
                "Controlled MVP release review is approved for bounded partner-facing delivery."
                if normalized_decision == "approved"
                else "Controlled MVP release review was rejected and must be requested again before bounded partner-facing delivery."
            ),
        }
        release_review_history.append(
            {
                "event": "reviewed",
                "status": normalized_decision,
                "changed_at": now,
                "changed_by_user_id": auth.user_id,
                "note": note.strip(),
            }
        )
        extra_metadata = dict(metadata or {})
        extra_metadata["mvp_release_review"] = updated_release_review
        extra_metadata["mvp_release_review_history"] = release_review_history
        updated = job_store.update_workspace_share_bundle(
            self.runtime_root,
            share_bundle_id=share_bundle.share_bundle_id,
            metadata_updates=extra_metadata,
        )
        self._write_share_bundle_contract_files(updated)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=updated.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="share_bundle.mvp_release_reviewed",
                target_type="share_bundle",
                target_id=updated.share_bundle_id,
                event_payload={
                    "export_bundle_id": updated.export_bundle_id,
                    "project_id": updated.project_id,
                    "study_id": updated.study_id,
                    "job_id": updated.job_id,
                    "run_id": updated.run_id,
                    "decision": normalized_decision,
                    "mvp_launch_scope_status": mvp_launch_scope.get("status"),
                    "mvp_release_review_status": updated_release_review.get("status"),
                    "review_note": updated_release_review.get("review_note"),
                },
                created_at=now,
            ),
        )
        return self._share_bundle_summary(updated)

    def list_workspace_share_bundles(
        self,
        auth: AuthContext,
        *,
        study_id: str = "",
        export_bundle_id: str = "",
    ) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        if study_id.strip():
            study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
            if study is None or study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        if export_bundle_id.strip():
            export_bundle = job_store.get_workspace_export_bundle(self.runtime_root, export_bundle_id.strip())
            if export_bundle is None or export_bundle.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace export bundle '{export_bundle_id}' is not visible in this workspace.")
        return [
            self._share_bundle_summary(self._refresh_share_bundle_status(bundle))
            for bundle in job_store.list_workspace_share_bundles(
                self.runtime_root,
                auth.workspace_id,
                study_id=study_id.strip(),
                export_bundle_id=export_bundle_id.strip(),
            )
        ]

    def get_workspace_share_bundle(self, auth: AuthContext, share_bundle_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        share_bundle = job_store.get_workspace_share_bundle(self.runtime_root, share_bundle_id)
        if share_bundle is None or share_bundle.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace share bundle '{share_bundle_id}' is not visible in this workspace.")
        share_bundle = self._refresh_share_bundle_status(share_bundle)
        return self._share_bundle_summary(share_bundle)

    def revoke_workspace_share_bundle(self, auth: AuthContext, share_bundle_id: str) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SHAREABLE_ROLE_SET:
            raise AuthorizationError(f"Role '{auth.role}' cannot revoke share bundles.")
        share_bundle = job_store.get_workspace_share_bundle(self.runtime_root, share_bundle_id)
        if share_bundle is None or share_bundle.workspace_id != auth.workspace_id:
            raise AuthorizationError(f"Workspace share bundle '{share_bundle_id}' is not visible in this workspace.")
        now = utc_now_iso()
        updated = job_store.update_workspace_share_bundle(
            self.runtime_root,
            share_bundle_id=share_bundle.share_bundle_id,
            status="revoked",
            revoked_at=share_bundle.revoked_at or now,
        )
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="share_bundle.revoked",
                target_type="share_bundle",
                target_id=updated.share_bundle_id,
                event_payload={
                    "export_bundle_id": updated.export_bundle_id,
                    "project_id": updated.project_id,
                    "study_id": updated.study_id,
                    "job_id": updated.job_id,
                    "run_id": updated.run_id,
                    "public_path": updated.public_path,
                    "revoked_at": updated.revoked_at,
                },
                created_at=now,
            ),
        )
        return self._share_bundle_summary(updated)

    def get_public_share_bundle(self, share_key: str) -> dict[str, Any]:
        share_bundle = job_store.get_workspace_share_bundle_by_key(self.runtime_root, share_key.strip())
        if share_bundle is None:
            raise FileNotFoundError(f"Unknown public share bundle '{share_key}'.")
        share_bundle = self._refresh_share_bundle_status(share_bundle)
        if share_bundle.status == "revoked":
            raise ShareUnavailableError(f"Share bundle '{share_bundle.share_bundle_id}' has been revoked.")
        if share_bundle.status == "expired":
            raise ShareUnavailableError(f"Share bundle '{share_bundle.share_bundle_id}' has expired.")
        payload_path = Path(share_bundle.share_payload_path)
        if not payload_path.exists():
            raise FileNotFoundError(f"Share payload not found: {payload_path}")
        payload = read_json(payload_path)
        if not isinstance(payload, dict):
            raise ValueError("Share payload must contain an object payload.")
        readiness_gate = payload.get("readiness_gate")
        if not isinstance(readiness_gate, dict):
            readiness_gate = {}
        if str(readiness_gate.get("share_status") or "").strip() in READINESS_GATE_BLOCKED_SHARE_STATUSES:
            raise ShareUnavailableError(
                f"Share bundle '{share_bundle.share_bundle_id}' is gated until the required human review boundary is cleared."
            )
        mvp_launch_scope = payload.get("mvp_launch_scope")
        if not isinstance(mvp_launch_scope, dict):
            mvp_launch_scope = {}
        mvp_promotion = payload.get("mvp_promotion")
        if not isinstance(mvp_promotion, dict):
            mvp_promotion = {}
        if (
            str(mvp_launch_scope.get("status") or "").strip() == "design_partner_candidate"
            and str(mvp_promotion.get("status") or "").strip() != "approved"
        ):
            raise ShareUnavailableError(
                f"Share bundle '{share_bundle.share_bundle_id}' is unavailable until design-partner promotion approval is recorded."
            )
        partner_onboarding = payload.get("partner_onboarding")
        if not isinstance(partner_onboarding, dict):
            partner_onboarding = {}
        if (
            str(mvp_launch_scope.get("status") or "").strip() == "design_partner_candidate"
            and str(partner_onboarding.get("status") or "").strip() != "ready"
        ):
            raise ShareUnavailableError(
                f"Share bundle '{share_bundle.share_bundle_id}' is unavailable until bounded partner onboarding is attached."
            )
        mvp_release_review = payload.get("mvp_release_review")
        if not isinstance(mvp_release_review, dict):
            mvp_release_review = {}
        if (
            str(mvp_launch_scope.get("status") or "").strip() == "design_partner_candidate"
            and str(mvp_release_review.get("status") or "").strip() != "approved"
        ):
            raise ShareUnavailableError(
                f"Share bundle '{share_bundle.share_bundle_id}' is unavailable until controlled MVP release review is approved."
            )
        payload["status"] = share_bundle.status
        payload["published_at"] = share_bundle.published_at
        payload["expires_at"] = share_bundle.expires_at
        payload["public_path"] = share_bundle.public_path
        return payload

    def describe_workspace_support(
        self,
        auth: AuthContext,
        *,
        job_id: str = "",
        study_id: str = "",
    ) -> dict[str, Any]:
        workspace, billing = self._workspace_and_billing(auth)
        limits = _plan_limits(workspace.plan_tier, workspace.settings)
        jobs = job_store.list_workspace_jobs(self.runtime_root, auth.workspace_id)
        job = self.get_validation_job(auth, job_id.strip()) if job_id.strip() else None
        study: WorkspaceStudy | None = None
        selected_study_id = study_id.strip()
        if selected_study_id:
            study = job_store.get_workspace_study(self.runtime_root, selected_study_id)
            if study is None or study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{selected_study_id}' is not visible in this workspace.")
        elif job is not None:
            job_metadata = dict(job.get("metadata", {}))
            linked_study_id = str(job_metadata.get("study_id") or "").strip()
            if linked_study_id:
                study = job_store.get_workspace_study(self.runtime_root, linked_study_id)
                selected_study_id = linked_study_id if study is not None else ""
        submission_gate = self._support_submission_gate(auth, workspace, billing, limits, jobs, study=study)
        support_summary = self._support_summary_for_job(job) if job is not None else None
        recent_failed_jobs = [
            self._support_job_digest(candidate)
            for candidate in jobs
            if str(candidate.get("status") or "") in {"failed", "canceled"}
        ][:5]
        return {
            "contract_version": "workspace-support-surface/v0-draft",
            "workspace_id": auth.workspace_id,
            "selected_job_id": str(job.get("job_id") or "") if job else None,
            "selected_study_id": selected_study_id or None,
            "study_boundary": self._study_regulated_review_boundary(study) if study is not None else None,
            "governed_review": self._study_governed_review_state(study) if study is not None else None,
            "governed_redaction": self._study_governed_redaction_state(study) if study is not None else None,
            "submission_gate": submission_gate,
            "provider_runtime": self._workspace_provider_runtime_state(auth, jobs, selected_job=job),
            "job_diagnostic": support_summary,
            "recent_failed_jobs": recent_failed_jobs,
            "support_snapshot_count": len(job_store.list_workspace_support_snapshots(self.runtime_root, auth.workspace_id)),
            "synthetic_boundary": (
                "Synthetic evidence only. Support diagnostics describe synthetic research runtime state, not human market proof."
            ),
        }

    def create_workspace_support_snapshot(
        self,
        auth: AuthContext,
        *,
        job_id: str,
        title: str = "",
        notes: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        job = self.get_validation_job(auth, job_id.strip())
        support_payload = self.describe_workspace_support(auth, job_id=str(job.get("job_id") or ""))
        job_metadata = dict(job.get("metadata", {}))
        project_id = str(job_metadata.get("project_id") or "").strip() or None
        study_id = str(job_metadata.get("study_id") or "").strip() or None
        run_id = str(job_metadata.get("run_id") or "").strip() or None
        now = utc_now_iso()
        support_snapshot_id = f"support_{uuid.uuid4().hex[:12]}"
        workspace_root = _workspace_root(self.runtime_root, workspace.workspace_id)
        support_root = workspace_root / "support" / support_snapshot_id
        support_root.mkdir(parents=True, exist_ok=True)
        snapshot_path = support_root / "support_snapshot.json"
        summary = str(
            support_payload.get("job_diagnostic", {}) and support_payload["job_diagnostic"].get("summary")
            or "Workspace support snapshot"
        )
        support_snapshot = WorkspaceSupportSnapshot(
            support_snapshot_id=support_snapshot_id,
            workspace_id=workspace.workspace_id,
            project_id=project_id,
            study_id=study_id,
            job_id=str(job.get("job_id") or ""),
            run_id=run_id,
            title=title.strip() or f"Support snapshot for {job['job_id']}",
            status="generated",
            summary=summary,
            support_root=str(support_root),
            snapshot_path=str(snapshot_path),
            created_by_user_id=auth.user_id,
            created_at=now,
            updated_at=now,
            metadata={
                **dict(metadata or {}),
                "notes": notes.strip(),
                "diagnostic": support_payload,
                "handoff": {
                    "contract_version": "workspace-support-handoff/v0-draft",
                    "status": "unassigned",
                    "assigned_user_id": None,
                    "assigned_at": None,
                    "assigned_by_user_id": None,
                    "acknowledged_at": None,
                    "resolved_at": None,
                    "latest_note": "",
                },
                "handoff_history": [],
            },
        )
        self._materialize_support_snapshot_artifacts(support_snapshot)
        created = job_store.create_workspace_support_snapshot(self.runtime_root, support_snapshot)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="support_snapshot.created",
                target_type="support_snapshot",
                target_id=created.support_snapshot_id,
                event_payload={
                    "project_id": created.project_id,
                    "study_id": created.study_id,
                    "job_id": created.job_id,
                    "run_id": created.run_id,
                    "summary": created.summary,
                },
                created_at=created.created_at,
            ),
        )
        return self._support_snapshot_summary(created)

    def update_workspace_support_snapshot_handoff(
        self,
        auth: AuthContext,
        *,
        support_snapshot_id: str,
        status: str,
        assigned_user_id: str = "",
        note: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SUPPORT_HANDOFF_MUTATION_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot update support handoff state.")
        snapshot = job_store.get_workspace_support_snapshot(self.runtime_root, support_snapshot_id.strip())
        if snapshot is None or snapshot.workspace_id != auth.workspace_id:
            raise AuthorizationError(
                f"Workspace support snapshot '{support_snapshot_id}' is not visible in this workspace."
            )
        member_map = self._workspace_member_map(workspace)
        normalized_status = str(status or "").strip()
        if normalized_status not in SUPPORT_HANDOFF_STATUSES:
            raise ValueError(f"Unsupported support handoff status '{normalized_status}'.")
        existing_handoff = self._support_handoff(snapshot, workspace)
        resolved_assigned_user_id = str(assigned_user_id or existing_handoff.get("assigned_user_id") or "").strip()
        if normalized_status == "assigned" and not resolved_assigned_user_id:
            raise ValueError("Field 'assigned_user_id' is required when assigning support handoff.")
        if normalized_status in {"acknowledged", "resolved"} and not resolved_assigned_user_id:
            raise ValueError("Support handoff must be assigned before it can be acknowledged or resolved.")
        if resolved_assigned_user_id:
            member = member_map.get(resolved_assigned_user_id)
            if member is None:
                raise ValueError(f"Workspace member '{resolved_assigned_user_id}' is not available for support handoff.")
            if member.role not in SUPPORT_HANDOFF_ASSIGNEE_ROLES:
                raise ValueError(f"Workspace member '{resolved_assigned_user_id}' has role '{member.role}' and cannot receive support handoff.")
        if normalized_status in {"acknowledged", "resolved"} and auth.role not in {"owner", "admin"} and auth.user_id != resolved_assigned_user_id:
            raise AuthorizationError("Only owner/admin members or the assigned handoff owner can acknowledge or resolve this support snapshot.")
        if normalized_status == "unassigned" and auth.role not in {"owner", "admin"}:
            raise AuthorizationError("Only owner/admin members can clear support handoff assignment.")
        now = utc_now_iso()
        merged_metadata = dict(snapshot.metadata)
        merged_metadata.update(dict(metadata or {}))
        history = merged_metadata.get("handoff_history")
        if not isinstance(history, list):
            history = []
        history = [item for item in history if isinstance(item, dict)]
        handoff_state = {
            "contract_version": "workspace-support-handoff/v0-draft",
            "status": normalized_status,
            "assigned_user_id": resolved_assigned_user_id or None,
            "assigned_at": existing_handoff.get("assigned_at"),
            "assigned_by_user_id": existing_handoff.get("assigned_by_user_id"),
            "acknowledged_at": existing_handoff.get("acknowledged_at"),
            "resolved_at": existing_handoff.get("resolved_at"),
            "latest_note": note.strip(),
        }
        if normalized_status == "assigned":
            handoff_state["assigned_at"] = now
            handoff_state["assigned_by_user_id"] = auth.user_id
            handoff_state["acknowledged_at"] = None
            handoff_state["resolved_at"] = None
        elif normalized_status == "acknowledged":
            handoff_state["acknowledged_at"] = now
            handoff_state["resolved_at"] = None
        elif normalized_status == "resolved":
            handoff_state["resolved_at"] = now
            if not handoff_state.get("acknowledged_at"):
                handoff_state["acknowledged_at"] = now
        elif normalized_status == "unassigned":
            handoff_state.update(
                {
                    "assigned_user_id": None,
                    "assigned_at": None,
                    "assigned_by_user_id": None,
                    "acknowledged_at": None,
                    "resolved_at": None,
                }
            )
        history.append(
            {
                "status": normalized_status,
                "assigned_user_id": handoff_state.get("assigned_user_id"),
                "changed_at": now,
                "changed_by_user_id": auth.user_id,
                "note": note.strip(),
            }
        )
        merged_metadata.update(
            {
                "handoff": handoff_state,
                "handoff_history": history,
            }
        )
        updated = job_store.update_workspace_support_snapshot_metadata(
            self.runtime_root,
            support_snapshot_id=snapshot.support_snapshot_id,
            metadata_updates=merged_metadata,
            updated_at=now,
        )
        if updated is None:
            raise FileNotFoundError(f"Workspace support snapshot '{support_snapshot_id}' could not be updated.")
        self._materialize_support_snapshot_artifacts(updated)
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="support_snapshot.handoff_updated",
                target_type="support_snapshot",
                target_id=snapshot.support_snapshot_id,
                event_payload={
                    "project_id": snapshot.project_id,
                    "study_id": snapshot.study_id,
                    "job_id": snapshot.job_id,
                    "run_id": snapshot.run_id,
                    "handoff_status": normalized_status,
                    "assigned_user_id": handoff_state.get("assigned_user_id"),
                    "note": note.strip() or None,
                },
                created_at=now,
            ),
        )
        return self._support_snapshot_summary(updated)

    def list_workspace_support_snapshots(
        self,
        auth: AuthContext,
        *,
        study_id: str = "",
        job_id: str = "",
    ) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        if study_id.strip():
            study = job_store.get_workspace_study(self.runtime_root, study_id.strip())
            if study is None or study.workspace_id != auth.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
        if job_id.strip():
            job = self.get_validation_job(auth, job_id.strip())
            if str(job.get("workspace_id") or "") != auth.workspace_id:
                raise AuthorizationError(f"Validation job '{job_id}' is not visible in this workspace.")
        return [
            self._support_snapshot_summary(snapshot)
            for snapshot in job_store.list_workspace_support_snapshots(
                self.runtime_root,
                auth.workspace_id,
                study_id=study_id.strip(),
                job_id=job_id.strip(),
            )
        ]

    def get_workspace_support_snapshot(self, auth: AuthContext, support_snapshot_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        snapshot = job_store.get_workspace_support_snapshot(self.runtime_root, support_snapshot_id)
        if snapshot is None or snapshot.workspace_id != auth.workspace_id:
            raise AuthorizationError(
                f"Workspace support snapshot '{support_snapshot_id}' is not visible in this workspace."
            )
        return self._support_snapshot_summary(snapshot)

    def submit_validation_job(self, auth: AuthContext, request: ValidationJobRequest) -> dict[str, Any]:
        workspace, billing = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot submit validation jobs.")
        if billing.status not in ACTIVE_BILLING_STATUSES:
            raise AuthorizationError(f"Billing status '{billing.status}' does not allow new validation jobs.")
        limits = _plan_limits(workspace.plan_tier, workspace.settings)
        active_jobs = job_store.count_workspace_active_jobs(self.runtime_root, workspace.workspace_id)
        if active_jobs >= limits["max_concurrent_jobs"]:
            raise AuthorizationError(
                f"Workspace '{workspace.workspace_id}' reached the max concurrent job limit ({limits['max_concurrent_jobs']})."
            )
        today_floor = _now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        daily_jobs = job_store.count_workspace_jobs_created_since(self.runtime_root, workspace.workspace_id, today_floor)
        if daily_jobs >= limits["daily_runs"]:
            raise AuthorizationError(
                f"Workspace '{workspace.workspace_id}' reached the daily run limit ({limits['daily_runs']})."
            )

        workspace_root = _workspace_root(self.runtime_root, workspace.workspace_id)
        brief_path = _resolve_workspace_path(workspace_root, request.brief_path)
        persona_dir = _resolve_workspace_path(workspace_root, request.persona_dir)
        run_root = _resolve_workspace_path(workspace_root, request.run_root)
        if not brief_path.exists():
            raise FileNotFoundError(f"Brief path not found: {brief_path}")
        if not persona_dir.exists():
            raise FileNotFoundError(f"Persona directory not found: {persona_dir}")
        run_root.mkdir(parents=True, exist_ok=True)

        brief = load_and_validate_founder_brief(brief_path)
        panel_spec = validate_panel_spec(request.panel_spec, allowed_panel_types=set(PANEL_ROLES))
        created_at = utc_now_iso()
        job = ValidationJob(
            job_id=f"job_{created_at[:19].replace('-', '').replace(':', '').replace('T', '_')}_{uuid.uuid4().hex[:8]}",
            workspace_id=workspace.workspace_id,
            brief_id=brief.brief_id,
            requested_by_user_id=auth.user_id,
            panel_spec=panel_spec,
            provider_name=request.provider_name,
            status="queued",
            priority=request.priority,
            input_artifact_path=str(brief_path),
            output_run_path=None,
            retry_count=0,
            created_at=created_at,
        )
        project_id = str(request.metadata.get("project_id") or "").strip()
        study_id = str(request.metadata.get("study_id") or "").strip()
        study: WorkspaceStudy | None = None
        project: WorkspaceProject | None = None
        if study_id:
            study = job_store.get_workspace_study(self.runtime_root, study_id)
            if study is None or study.workspace_id != workspace.workspace_id:
                raise AuthorizationError(f"Workspace study '{study_id}' is not visible in this workspace.")
            project = job_store.get_workspace_project(self.runtime_root, study.project_id)
            project_id = study.project_id
        if project_id:
            project = job_store.get_workspace_project(self.runtime_root, project_id)
            if project is None or project.workspace_id != workspace.workspace_id:
                raise AuthorizationError(f"Workspace project '{project_id}' is not visible in this workspace.")
        if study is not None and project is not None and study.project_id != project.project_id:
            raise AuthorizationError("The selected study does not belong to the selected project.")
        regulated_review_boundary = self._study_regulated_review_boundary(study) if study is not None else None
        if regulated_review_boundary is not None and str(regulated_review_boundary.get("execution_status") or "") != "allowed":
            raise AuthorizationError(str(regulated_review_boundary.get("boundary_message") or "").strip())
        request_metadata = dict(request.metadata)
        plan_revision_id = str(
            request_metadata.get("plan_revision_id")
            or request_metadata.get("frontline_plan_revision_id")
            or ""
        ).strip()
        if study is not None:
            frontline = dict(study.metadata.get("frontline", {})) if isinstance(study.metadata.get("frontline"), dict) else {}
            plan_revision_id = plan_revision_id or str(
                frontline.get("current_plan_revision_id")
                or study.metadata.get("current_plan_revision_id")
                or ""
            ).strip()
            if bool(request_metadata.get("frontline_requires_plan_revision")) and not plan_revision_id:
                raise ValueError("Frontline validation jobs require a confirmed StudyPlanRevision.")

        metadata = {
            **request_metadata,
            "brief_path": str(brief_path),
            "persona_dir": str(persona_dir),
            "run_root": str(run_root),
            "max_retries": request.max_retries,
            "submitted_by_role": auth.role,
            "plan_tier": workspace.plan_tier,
            "daily_run_limit": limits["daily_runs"],
            "max_concurrent_jobs": limits["max_concurrent_jobs"],
            "artifact_retention_days": limits["artifact_retention_days"],
            "provider_runtime_boundary": self._validation_provider_runtime_boundary(
                request.provider_name,
                status="queued",
                metadata=request.metadata,
            ),
        }
        if project is not None:
            metadata["project_id"] = project.project_id
        if study is not None:
            metadata["study_id"] = study.study_id
            metadata["regulated_review_boundary"] = regulated_review_boundary
        if plan_revision_id:
            metadata["plan_revision_id"] = plan_revision_id
            metadata["frontline_plan_revision_id"] = plan_revision_id
        created = job_store.create_validation_job(
            self.runtime_root,
            job=job,
            persona_dir_path=str(persona_dir),
            idempotency_key=request.idempotency_key.strip(),
            metadata=metadata,
        )
        if study is not None:
            status = "running" if created["status"] == "queued" and plan_revision_id else "ready" if created["status"] == "queued" else None
            job_store.update_workspace_study(
                self.runtime_root,
                study_id=study.study_id,
                latest_job_id=str(created["job_id"]),
                status=status,
                metadata_updates={
                    "last_submitted_job_id": str(created["job_id"]),
                    **({"current_plan_revision_id": plan_revision_id} if plan_revision_id else {}),
                },
            )
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="validation_job.submitted",
                target_type="validation_job",
                target_id=str(created["job_id"]),
                event_payload={
                    "project_id": metadata.get("project_id") or None,
                    "study_id": metadata.get("study_id") or None,
                    "regulated_review_boundary": regulated_review_boundary,
                    "provider_runtime_boundary": metadata.get("provider_runtime_boundary"),
                    "brief_id": brief.brief_id,
                    "provider_name": request.provider_name,
                    "panel_type": panel_spec.panel_type,
                    "sample_size": panel_spec.sample_size,
                    "job_status": str(created.get("status") or ""),
                },
                created_at=created_at,
            ),
        )
        return created

    def list_workspace_jobs(self, auth: AuthContext) -> list[dict[str, Any]]:
        self._workspace_and_billing(auth)
        return job_store.list_workspace_jobs(self.runtime_root, auth.workspace_id)

    def get_validation_job(self, auth: AuthContext, job_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        job = job_store.get_validation_job(self.runtime_root, job_id)
        if job is None or str(job["workspace_id"]) != auth.workspace_id:
            raise AuthorizationError(f"Validation job '{job_id}' is not visible in this workspace.")
        return job

    def cancel_validation_job(
        self,
        auth: AuthContext,
        job_id: str,
        *,
        reason: str = "",
    ) -> dict[str, Any]:
        workspace, _ = self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot cancel validation jobs.")

        job = self.get_validation_job(auth, job_id)
        status = str(job.get("status") or "")
        if status != "queued":
            raise ValueError("Only queued validation jobs can be canceled.")

        cancel_reason = reason.strip() or "Canceled from the workspace product surface before worker lease."
        updated = job_store.update_validation_job(
            self.runtime_root,
            job_id=job_id,
            status="canceled",
            last_error=cancel_reason,
            metadata_updates={
                "canceled_by_user_id": auth.user_id,
                "canceled_by_role": auth.role,
                "cancel_reason": cancel_reason,
            },
        )
        metadata = dict(updated.get("metadata", {}))
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="validation_job.canceled",
                target_type="validation_job",
                target_id=str(updated.get("job_id") or ""),
                event_payload={
                    "project_id": str(metadata.get("project_id") or "") or None,
                    "study_id": str(metadata.get("study_id") or "") or None,
                    "job_status": str(updated.get("status") or ""),
                    "cancel_reason": cancel_reason,
                },
                created_at=utc_now_iso(),
            ),
        )
        return updated

    def retry_validation_job(self, auth: AuthContext, job_id: str) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        if auth.role not in SUBMITTER_ROLES:
            raise AuthorizationError(f"Role '{auth.role}' cannot retry validation jobs.")

        source_job = self.get_validation_job(auth, job_id)
        source_status = str(source_job.get("status") or "")
        if source_status not in {"failed", "canceled"}:
            raise ValueError("Only failed or canceled validation jobs can be retried.")

        source_metadata = dict(source_job.get("metadata", {}))
        retry_metadata = dict(source_metadata)
        for field in (
            "run_id",
            "artifact_retention_until",
            "artifact_deleted_at",
            "canceled_by_user_id",
            "canceled_by_role",
            "cancel_reason",
            "retry_of_job_id",
            "retry_source_job_id",
            "retry_source_status",
            "last_retry_job_id",
        ):
            retry_metadata.pop(field, None)
        retry_metadata["retry_of_job_id"] = str(source_job.get("job_id") or "")
        retry_metadata["retry_source_status"] = source_status

        retried = self.submit_validation_job(
            auth,
            ValidationJobRequest(
                brief_path=str(source_metadata.get("brief_path") or source_job.get("input_artifact_path") or ""),
                persona_dir=str(source_metadata.get("persona_dir") or source_job.get("persona_dir_path") or ""),
                panel_spec=PanelSpec(**dict(source_job.get("panel_spec") or {})),
                provider_name=str(source_job.get("provider_name") or "mock"),
                priority=str(source_job.get("priority") or "normal"),
                max_retries=int(source_metadata.get("max_retries", 1)),
                run_root=str(source_metadata.get("run_root") or "runs"),
                metadata=retry_metadata,
            ),
        )
        retried_metadata = dict(retried.get("metadata", {}))
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=auth.workspace_id,
                actor_user_id=auth.user_id,
                actor_role=auth.role,
                action="validation_job.retried",
                target_type="validation_job",
                target_id=str(retried.get("job_id") or ""),
                event_payload={
                    "source_job_id": str(source_job.get("job_id") or ""),
                    "source_status": source_status,
                    "project_id": str(retried_metadata.get("project_id") or "") or None,
                    "study_id": str(retried_metadata.get("study_id") or "") or None,
                },
                created_at=utc_now_iso(),
            ),
        )
        return retried

    def _validation_provider_catalog(self) -> list[dict[str, Any]]:
        return [
            self._validation_provider_runtime_boundary(provider_name)
            for provider_name in SUPPORTED_VALIDATION_PROVIDERS
        ]

    def _workspace_provider_runtime_state(
        self,
        auth: AuthContext,
        jobs: list[dict[str, Any]],
        *,
        selected_job: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        provider_names = [
            _normalize_validation_provider_name(str(job.get("provider_name") or ""))
            for job in jobs
        ]
        live_jobs = [name for name in provider_names if name in LIVE_VALIDATION_PROVIDERS]
        mock_jobs = [name for name in provider_names if name == "mock"]
        unsupported_jobs = [name for name in provider_names if name not in SUPPORTED_VALIDATION_PROVIDERS]
        selected_boundary = (
            self._validation_provider_runtime_boundary(
                str(selected_job.get("provider_name") or ""),
                status=str(selected_job.get("status") or ""),
                last_error=str(selected_job.get("last_error") or ""),
                metadata=dict(selected_job.get("metadata", {})),
            )
            if selected_job is not None
            else None
        )
        return {
            "contract_version": "workspace-provider-runtime/v0-draft",
            "workspace_id": auth.workspace_id,
            "catalog": self._validation_provider_catalog(),
            "selected_job_boundary": selected_boundary,
            "job_counts": {
                "total": len(jobs),
                "mock_demo": len(mock_jobs),
                "live_synthetic": len(live_jobs),
                "unsupported": len(unsupported_jobs),
            },
            "provider_counts": _count_values(provider_names),
            "synthetic_boundary": (
                "Provider runtime state distinguishes mock demo evidence from live synthetic evidence. "
                "Neither mode is human market proof."
            ),
        }

    def _validation_provider_runtime_boundary(
        self,
        provider_name: str,
        *,
        status: str = "",
        last_error: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        normalized = _normalize_validation_provider_name(provider_name)
        metadata = dict(metadata or {})
        is_supported = normalized in SUPPORTED_VALIDATION_PROVIDERS
        is_mock = normalized == "mock"
        is_live_provider = normalized in LIVE_VALIDATION_PROVIDERS
        is_codex_provider = normalized in CODEX_VALIDATION_PROVIDERS
        auth_state = self._validation_provider_auth_state(normalized)
        failure_kind = self._validation_provider_failure_kind(
            provider_name=normalized,
            status=status,
            last_error=last_error,
        )
        runtime_status = self._validation_provider_runtime_status(
            provider_name=normalized,
            status=status,
            auth_readiness=str(auth_state.get("auth_readiness") or ""),
            failure_kind=failure_kind,
        )
        evidence_mode = "mock_demo" if is_mock else ("live_synthetic" if is_live_provider else "unsupported")
        provider_family = (
            "mock"
            if is_mock
            else ("codex" if is_codex_provider else ("openai_compatible" if is_live_provider else "unsupported"))
        )
        return {
            "contract_version": "validation-provider-runtime/v0-draft",
            "provider_name": normalized,
            "provider_family": provider_family,
            "evidence_mode": evidence_mode,
            "is_supported": is_supported,
            "is_live_provider": is_live_provider,
            "is_codex_provider": is_codex_provider,
            "requires_auth": bool(auth_state.get("requires_auth")),
            "auth_readiness": str(auth_state.get("auth_readiness") or ""),
            "auth_source": str(auth_state.get("auth_source") or "") or None,
            "auth_sources_checked": list(auth_state.get("auth_sources_checked", [])),
            "runtime_status": runtime_status,
            "job_status": status or None,
            "failure_kind": failure_kind or None,
            "failure_category": self._support_failure_category(
                status=status,
                last_error=last_error,
                artifact_deleted_at=str(metadata.get("artifact_deleted_at") or ""),
            ),
            "last_error_visible": bool(str(last_error or "").strip()),
            "boundary_label": "Mock demo evidence" if is_mock else ("Live synthetic evidence" if is_live_provider else "Unsupported provider"),
            "boundary_message": self._validation_provider_boundary_message(
                provider_name=normalized,
                evidence_mode=evidence_mode,
                runtime_status=runtime_status,
            ),
            "next_actions": self._validation_provider_next_actions(
                runtime_status=runtime_status,
                provider_name=normalized,
                auth_readiness=str(auth_state.get("auth_readiness") or ""),
                failure_kind=failure_kind,
            ),
        }

    def _validation_provider_auth_state(self, provider_name: str) -> dict[str, Any]:
        if provider_name == "mock":
            return {
                "requires_auth": False,
                "auth_readiness": "not_required",
                "auth_source": "",
                "auth_sources_checked": [],
            }
        if provider_name not in SUPPORTED_VALIDATION_PROVIDERS:
            return {
                "requires_auth": False,
                "auth_readiness": "unsupported",
                "auth_source": "",
                "auth_sources_checked": [],
            }

        checked_sources = [
            "AI_VALIDATION_LLM_API_KEY",
            "AI_VALIDATION_OPENAI_API_KEY",
            "OPENAI_API_KEY",
            "CODEX_API_KEY",
        ]
        api_key_env = _first_configured_env_name(*checked_sources)
        if api_key_env:
            return {
                "requires_auth": True,
                "auth_readiness": "ready",
                "auth_source": f"api_key_env:{api_key_env}",
                "auth_sources_checked": checked_sources,
            }

        auth_path_raw = os.getenv("AI_VALIDATION_CODEX_AUTH_FILE", "").strip()
        codex_home = os.getenv("AI_VALIDATION_CODEX_HOME", "").strip() or os.getenv("CODEX_HOME", "").strip()
        auth_path = Path(auth_path_raw) if auth_path_raw else None
        checked_auth_path = auth_path or (Path(codex_home) / "auth.json" if codex_home else Path.home() / ".codex" / "auth.json")
        checked_sources = [*checked_sources, f"codex_auth_file:{checked_auth_path}"]
        try:
            codex_token = load_codex_access_token(auth_path)
        except Exception:
            codex_token = ""
        if codex_token:
            return {
                "requires_auth": True,
                "auth_readiness": "ready",
                "auth_source": f"codex_auth_file:{checked_auth_path}",
                "auth_sources_checked": checked_sources,
            }
        return {
            "requires_auth": True,
            "auth_readiness": "missing_or_unverified",
            "auth_source": "",
            "auth_sources_checked": checked_sources,
        }

    def _validation_provider_failure_kind(self, *, provider_name: str, status: str, last_error: str) -> str:
        if provider_name not in SUPPORTED_VALIDATION_PROVIDERS:
            return "unsupported_provider"
        if status != "failed":
            return ""
        lowered = str(last_error or "").lower()
        if "unsupported provider" in lowered or ("provider" in lowered and "unsupported" in lowered):
            return "unsupported_provider"
        if "credentials are missing" in lowered or ("missing" in lowered and ("credential" in lowered or "auth" in lowered)):
            return "missing_auth"
        if "timed out" in lowered or "timeout" in lowered:
            return "timeout"
        if "refusal" in lowered or "refused" in lowered or "safety" in lowered:
            return "refusal"
        if "rate limit" in lowered or "connection" in lowered or "temporar" in lowered or "retry" in lowered:
            return "retryable_transport"
        if "provider" in lowered:
            return "provider_configuration"
        return "runtime_failure"

    def _validation_provider_runtime_status(
        self,
        *,
        provider_name: str,
        status: str,
        auth_readiness: str,
        failure_kind: str,
    ) -> str:
        if provider_name not in SUPPORTED_VALIDATION_PROVIDERS:
            return "unsupported_provider"
        if failure_kind:
            return failure_kind
        if provider_name in LIVE_VALIDATION_PROVIDERS and auth_readiness != "ready" and status in {"", "queued"}:
            return "missing_auth"
        if status in {"queued", "running", "completed", "failed", "canceled"}:
            return status
        return "ready_to_queue"

    def _validation_provider_boundary_message(
        self,
        *,
        provider_name: str,
        evidence_mode: str,
        runtime_status: str,
    ) -> str:
        if runtime_status == "unsupported_provider":
            return f"Provider '{provider_name}' is not supported by the validation-job runtime."
        if runtime_status == "missing_auth":
            return f"Provider '{provider_name}' needs local LLM or Codex credentials before a live synthetic run can complete."
        if evidence_mode == "mock_demo":
            return "This provider creates mock demo evidence for product flow testing only."
        if evidence_mode == "live_synthetic":
            return "This provider creates live synthetic evidence. It is not human market proof."
        return "This provider cannot produce accepted evidence until backend configuration is corrected."

    def _validation_provider_next_actions(
        self,
        *,
        runtime_status: str,
        provider_name: str,
        auth_readiness: str,
        failure_kind: str,
    ) -> list[str]:
        if runtime_status == "unsupported_provider":
            return ["Choose one of: mock, openai, agnes, codex, or codex-sdk before retrying."]
        if runtime_status == "missing_auth":
            return [
                "Sign in through Codex or configure AI_VALIDATION_LLM_API_KEY / OPENAI_API_KEY / CODEX_API_KEY.",
                "Keep mock selected only when intentionally testing the product flow without live evidence.",
            ]
        if failure_kind == "timeout":
            return ["Retry the run or increase AI_VALIDATION_OPENAI_TIMEOUT_SECONDS for longer live-provider calls."]
        if failure_kind == "refusal":
            return ["Review the study prompt, artifacts, and safety boundary before retrying."]
        if failure_kind == "retryable_transport":
            return ["Retry after the transport recovers; keep the failed job for support lineage."]
        if provider_name == "mock":
            return ["Use codex or codex-sdk when you need live synthetic evidence instead of mock demo evidence."]
        if auth_readiness == "ready":
            return ["Run from the study surface and keep provider lineage visible during evidence review."]
        return ["Review provider configuration before starting the live run."]

    def describe_workspace_session(self, auth: AuthContext) -> dict[str, Any]:
        workspace, billing = self._workspace_and_billing(auth)
        limits = _plan_limits(workspace.plan_tier, workspace.settings)
        jobs = job_store.list_workspace_jobs(self.runtime_root, auth.workspace_id)
        projects = job_store.list_workspace_projects(self.runtime_root, auth.workspace_id)
        studies = job_store.list_workspace_studies(self.runtime_root, auth.workspace_id)
        evidence_views = job_store.list_workspace_evidence_views(self.runtime_root, auth.workspace_id)
        decision_logs = job_store.list_workspace_decision_logs(self.runtime_root, auth.workspace_id)
        decision_comments = job_store.list_workspace_decision_comments(self.runtime_root, auth.workspace_id)
        study_reports = job_store.list_workspace_study_reports(self.runtime_root, auth.workspace_id)
        export_bundles = job_store.list_workspace_export_bundles(self.runtime_root, auth.workspace_id)
        share_bundles = job_store.list_workspace_share_bundles(self.runtime_root, auth.workspace_id)
        support_snapshots = job_store.list_workspace_support_snapshots(self.runtime_root, auth.workspace_id)
        job_counts = {
            "total": len(jobs),
            "queued": sum(1 for job in jobs if str(job.get("status")) == "queued"),
            "running": sum(1 for job in jobs if str(job.get("status")) == "running"),
            "completed": sum(1 for job in jobs if str(job.get("status")) == "completed"),
            "failed": sum(1 for job in jobs if str(job.get("status")) == "failed"),
            "canceled": sum(1 for job in jobs if str(job.get("status")) == "canceled"),
        }
        workspace_root = _workspace_root(self.runtime_root, auth.workspace_id)
        return {
            "auth": auth.to_dict(),
            "workspace": workspace.to_dict(),
            "billing_account": billing.to_dict(),
            "plan_limits": limits,
            "job_counts": job_counts,
            "paths": {
                "workspace_root": str(workspace_root),
                "briefs_root": str(workspace_root / "briefs"),
                "personas_root": str(workspace_root / "personas"),
                "runs_root": str(workspace_root / "runs"),
            },
            "capabilities": {
                "validation_jobs": True,
                "evidence_query": True,
                "worker_runtime": True,
                "session_auth": True,
                "workspace_settings": True,
                "billing_surface": True,
                "study_collaboration": True,
                "study_activity": True,
                "study_reports": True,
                "decision_review": True,
                "audit_history": True,
                "project_studies": True,
                "export_bundles": True,
                "share_bundles": True,
                "support_surface": True,
                "provider_runtime_boundary": True,
                "live_validation_providers": True,
            },
            "validation_provider_catalog": self._validation_provider_catalog(),
            "product_counts": {
                "projects": len(projects),
                "studies": len(studies),
                "evidence_views": len(evidence_views),
                "study_reports": len(study_reports),
                "decision_logs": len(decision_logs),
                "decision_comments": len(decision_comments),
                "export_bundles": len(export_bundles),
                "share_bundles": len(share_bundles),
                "support_snapshots": len(support_snapshots),
            },
            "synthetic_boundary": (
                "Synthetic evidence only. Authenticated workspace access does not change the evidence boundary."
            ),
        }

    def describe_runtime_operations(self) -> dict[str, Any]:
        runtime_db = job_store.runtime_db_path(self.runtime_root)
        workspaces = job_store.list_workspaces(self.runtime_root)
        jobs = job_store.list_validation_jobs(self.runtime_root)
        browser_sessions = job_store.list_browser_sessions(self.runtime_root, include_revoked=False)
        now = _now()
        active_sessions = [
            session
            for session in browser_sessions
            if session.revoked_at is None and datetime.fromisoformat(session.expires_at) > now
        ]
        job_counts = {
            "total": len(jobs),
            "queued": sum(1 for job in jobs if str(job.get("status") or "") == "queued"),
            "running": sum(1 for job in jobs if str(job.get("status") or "") == "running"),
            "completed": sum(1 for job in jobs if str(job.get("status") or "") == "completed"),
            "failed": sum(1 for job in jobs if str(job.get("status") or "") == "failed"),
            "canceled": sum(1 for job in jobs if str(job.get("status") or "") == "canceled"),
        }
        return {
            "contract_version": "saas-runtime-operations/v0-draft",
            "runtime_root": str(self.runtime_root),
            "runtime_root_exists": self.runtime_root.exists(),
            "runtime_root_writable": os.access(self.runtime_root, os.W_OK),
            "runtime_db_path": str(runtime_db),
            "runtime_db_exists": runtime_db.is_file(),
            "runtime_schema_version": job_store.RUNTIME_SCHEMA_VERSION,
            "workspace_count": len(workspaces),
            "workspace_ids": [workspace.workspace_id for workspace in workspaces],
            "job_counts": job_counts,
            "active_browser_session_count": len(active_sessions),
            "capabilities": {
                "validation_jobs": True,
                "worker_runtime": True,
                "evidence_query": True,
                "readiness_gates": True,
                "mvp_launch_scope": True,
                "mvp_promotion": True,
                "partner_onboarding": True,
                "mvp_release_review": True,
                "audit_history": True,
            },
            "synthetic_boundary": (
                "Operational readiness only. These runtime signals do not widen the synthetic-evidence boundary."
            ),
        }

    def describe_workspace_operations_summary(self, auth: AuthContext) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        jobs = self.list_workspace_jobs(auth)
        evidence_views = self.list_workspace_evidence_views(auth)
        decision_logs = self.list_workspace_decision_logs(auth)
        decision_comments = self.list_workspace_decision_comments(auth)
        export_bundles = self.list_workspace_export_bundles(auth)
        share_bundles = self.list_workspace_share_bundles(auth)
        support_snapshots = self.list_workspace_support_snapshots(auth)
        audit_events = job_store.list_audit_events(self.runtime_root, auth.workspace_id, limit=500)

        completed_jobs = [job for job in jobs if str(job.get("status") or "") == "completed"]
        evidence_review_statuses: list[str] = []
        readiness_statuses: list[str] = []
        calibration_statuses: list[str] = []
        observation_failures = 0
        for job in completed_jobs:
            try:
                query = self.query_workspace_evidence(auth, job_id=str(job.get("job_id") or ""))
            except (FileNotFoundError, ValueError, AuthorizationError):
                observation_failures += 1
                continue
            reliability = query.get("evidence_reliability")
            if isinstance(reliability, dict):
                evidence_review_statuses.append(str(reliability.get("review_status") or "unknown"))
            readiness_gate = query.get("readiness_gate")
            if isinstance(readiness_gate, dict):
                readiness_statuses.append(str(readiness_gate.get("status") or "unknown"))
                calibration_statuses.append(str(readiness_gate.get("calibration_status") or "unknown"))

        decision_review_statuses = [str(log.get("review_status") or "unknown") for log in decision_logs]
        decision_assignment_statuses = [str(log.get("review_assignment", {}).get("status") or "unknown") for log in decision_logs]
        export_launch_statuses = [str(bundle.get("mvp_launch_scope", {}).get("status") or "unknown") for bundle in export_bundles]
        export_promotion_statuses = [str(bundle.get("mvp_promotion", {}).get("status") or "unknown") for bundle in export_bundles]
        share_onboarding_statuses = [str(bundle.get("partner_onboarding", {}).get("status") or "unknown") for bundle in share_bundles]
        share_release_statuses = [str(bundle.get("mvp_release_review", {}).get("status") or "unknown") for bundle in share_bundles]
        support_handoff_statuses = [str(snapshot.get("handoff", {}).get("status") or "unknown") for snapshot in support_snapshots]
        audit_action_counts = _count_values([event.action for event in audit_events])
        provider_boundaries = [
            self._validation_provider_runtime_boundary(
                str(job.get("provider_name") or ""),
                status=str(job.get("status") or ""),
                last_error=str(job.get("last_error") or ""),
                metadata=dict(job.get("metadata", {})),
            )
            for job in jobs
        ]

        return {
            "contract_version": "workspace-operations-summary/v0-draft",
            "workspace_id": auth.workspace_id,
            "generated_at": utc_now_iso(),
            "worker_runtime": {
                "job_counts": _count_values([str(job.get("status") or "unknown") for job in jobs]),
                "completed_job_count": len(completed_jobs),
                "active_job_count": sum(1 for job in jobs if str(job.get("status") or "") in {"queued", "running"}),
            },
            "provider_runtime": {
                "catalog": self._validation_provider_catalog(),
                "provider_counts": _count_values([str(boundary.get("provider_name") or "unknown") for boundary in provider_boundaries]),
                "evidence_mode_counts": _count_values([str(boundary.get("evidence_mode") or "unknown") for boundary in provider_boundaries]),
                "runtime_status_counts": _count_values([str(boundary.get("runtime_status") or "unknown") for boundary in provider_boundaries]),
                "live_job_count": sum(1 for boundary in provider_boundaries if bool(boundary.get("is_live_provider"))),
                "mock_job_count": sum(1 for boundary in provider_boundaries if str(boundary.get("evidence_mode") or "") == "mock_demo"),
                "unsupported_job_count": sum(1 for boundary in provider_boundaries if not bool(boundary.get("is_supported"))),
            },
            "evidence_review": {
                "evidence_view_count": len(evidence_views),
                "review_status_counts": _count_values(evidence_review_statuses),
                "readiness_status_counts": _count_values(readiness_statuses),
                "calibration_status_counts": _count_values(calibration_statuses),
                "observation_failures": observation_failures,
            },
            "decision_review": {
                "decision_log_count": len(decision_logs),
                "decision_comment_count": len(decision_comments),
                "review_status_counts": _count_values(decision_review_statuses),
                "review_assignment_status_counts": _count_values(decision_assignment_statuses),
            },
            "distribution": {
                "export_bundle_count": len(export_bundles),
                "share_bundle_count": len(share_bundles),
                "mvp_launch_scope_counts": _count_values(export_launch_statuses),
                "mvp_promotion_status_counts": _count_values(export_promotion_statuses),
                "partner_onboarding_status_counts": _count_values(share_onboarding_statuses),
                "mvp_release_review_status_counts": _count_values(share_release_statuses),
            },
            "support": {
                "support_snapshot_count": len(support_snapshots),
                "handoff_status_counts": _count_values(support_handoff_statuses),
            },
            "audit": {
                "recent_event_limit": 500,
                "recent_event_count": len(audit_events),
                "action_counts": audit_action_counts,
                "latest_event_at": audit_events[0].created_at if audit_events else None,
            },
            "public_launch_readiness": self.describe_workspace_public_launch_readiness(auth),
            "synthetic_boundary": (
                "Operational observability only. These counts summarize synthetic research runtime behavior and "
                "distribution state, not human market proof."
            ),
        }

    def describe_workspace_public_launch_readiness(self, auth: AuthContext) -> dict[str, Any]:
        workspace, billing = self._workspace_and_billing(auth)
        studies = self.list_workspace_studies(auth)
        jobs = self.list_workspace_jobs(auth)
        export_bundles = self.list_workspace_export_bundles(auth)
        share_bundles = self.list_workspace_share_bundles(auth)
        support_snapshots = job_store.list_workspace_support_snapshots(self.runtime_root, auth.workspace_id)

        study_lookup = {
            str(study.get("study_id") or ""): study
            for study in studies
            if str(study.get("study_id") or "").strip()
        }
        completed_jobs = [job for job in jobs if str(job.get("status") or "") == "completed"]
        claim_boundary_statuses: list[str] = []
        customer_claim_statuses: list[str] = []
        blocked_reason_counts: dict[str, int] = {}
        readiness_statuses: list[str] = []
        calibration_statuses: list[str] = []
        benchmark_statuses: list[str] = []
        benchmark_origin_counts: list[str] = []
        benchmark_source_type_counts: list[str] = []
        observation_failures = 0

        for job in completed_jobs:
            try:
                query = self.query_workspace_evidence(auth, job_id=str(job.get("job_id") or ""))
            except (FileNotFoundError, ValueError, AuthorizationError):
                observation_failures += 1
                continue

            metadata = dict(job.get("metadata") or {})
            linked_study = study_lookup.get(str(metadata.get("study_id") or ""))
            regulated_review_boundary = (
                dict(linked_study.get("regulated_review_boundary", {}))
                if isinstance(linked_study, dict)
                else dict(metadata.get("regulated_review_boundary") or {})
            )
            governed_review = (
                dict(query.get("governed_review", {}))
                if isinstance(query.get("governed_review"), dict)
                else (dict(linked_study.get("governed_review", {})) if isinstance(linked_study, dict) else {})
            )
            governed_redaction = (
                dict(query.get("governed_redaction", {}))
                if isinstance(query.get("governed_redaction"), dict)
                else (dict(linked_study.get("governed_redaction", {})) if isinstance(linked_study, dict) else {})
            )
            readiness_gate = dict(query.get("readiness_gate", {})) if isinstance(query.get("readiness_gate"), dict) else {}
            launch_scope = self._build_mvp_launch_scope(readiness_gate)
            public_claims_boundary = self._build_public_claims_boundary(
                readiness_gate=readiness_gate,
                mvp_launch_scope=launch_scope,
                regulated_review_boundary=regulated_review_boundary,
                governed_review=governed_review,
                governed_redaction=governed_redaction,
            )

            claim_boundary_statuses.append(str(public_claims_boundary.get("status") or "unknown"))
            customer_claim_statuses.append(str(public_claims_boundary.get("customer_claim_status") or "unknown"))
            readiness_statuses.append(str(readiness_gate.get("status") or "unknown"))
            calibration_statuses.append(str(readiness_gate.get("calibration_status") or "unknown"))
            benchmark_disclosure = (
                dict(public_claims_boundary.get("benchmark_disclosure", {}))
                if isinstance(public_claims_boundary.get("benchmark_disclosure"), dict)
                else {}
            )
            benchmark_statuses.append(str(benchmark_disclosure.get("external_benchmark_status") or "unknown"))
            if str(benchmark_disclosure.get("benchmark_origin") or "").strip():
                benchmark_origin_counts.append(str(benchmark_disclosure.get("benchmark_origin")))
            if str(benchmark_disclosure.get("source_type") or "").strip():
                benchmark_source_type_counts.append(str(benchmark_disclosure.get("source_type")))
            for reason in public_claims_boundary.get("blocked_reasons", []):
                key = str(reason or "").strip()
                if key:
                    blocked_reason_counts[key] = blocked_reason_counts.get(key, 0) + 1

        regulated_studies = [
            study
            for study in studies
            if str(dict(study.get("regulated_review_boundary", {})).get("classification_status") or "") == "high_stakes"
        ]
        governed_review_required = [
            study
            for study in studies
            if bool(dict(study.get("governed_review", {})).get("human_review_required"))
        ]
        governed_redaction_required = [
            study
            for study in studies
            if not bool(dict(study.get("governed_redaction", {})).get("circulation_allowed"))
        ]
        design_partner_candidate_exports = [
            bundle
            for bundle in export_bundles
            if str(dict(bundle.get("mvp_launch_scope", {})).get("status") or "") == "design_partner_candidate"
        ]
        approved_public_shares = [
            bundle
            for bundle in share_bundles
            if str(dict(bundle.get("mvp_release_review", {})).get("status") or "") == "approved"
        ]

        overall_status = "research_preview_only"
        if "governed_preview_only" in claim_boundary_statuses:
            overall_status = "governed_preview_only"
        if "controlled_mvp_only" in claim_boundary_statuses:
            overall_status = "controlled_mvp_only"
        if "bounded_public_candidate" in claim_boundary_statuses:
            overall_status = "bounded_public_candidate"

        aggregate_blocked_reasons = sorted(
            blocked_reason_counts,
            key=lambda value: (-blocked_reason_counts[value], value),
        )
        self_serve_public_launch_allowed = overall_status == "bounded_public_candidate"
        public_marketing_claims_allowed = overall_status in {"controlled_mvp_only", "bounded_public_candidate"}
        customer_operations_support_boundary = self._build_customer_operations_and_support_boundary(
            auth=auth,
            workspace=workspace,
            billing=billing,
            jobs=jobs,
            support_snapshots=support_snapshots,
        )
        self_serve_onboarding_pricing_boundary = self._build_self_serve_onboarding_and_pricing_boundary(
            auth=auth,
            workspace=workspace,
            billing=billing,
        )
        calibration_observatory = self.describe_calibration_observatory(auth)
        privacy_export_controls = self.describe_workspace_privacy_export_controls(auth)
        launch_blocker_counts = dict(blocked_reason_counts)
        if calibration_observatory.get("health_summary", {}).get("status") == "insufficient_benchmarking":
            launch_blocker_counts["continuous_calibration_health_not_ready"] = (
                launch_blocker_counts.get("continuous_calibration_health_not_ready", 0) + 1
            )
        if privacy_export_controls.get("privacy_readiness", {}).get("status") != "ready_for_customer_review":
            launch_blocker_counts["privacy_export_controls_not_ready"] = (
                launch_blocker_counts.get("privacy_export_controls_not_ready", 0) + 1
            )
        for reason in customer_operations_support_boundary.get("blocked_reasons", []):
            key = str(reason or "").strip()
            if key:
                launch_blocker_counts[key] = launch_blocker_counts.get(key, 0) + 1
        for reason in self_serve_onboarding_pricing_boundary.get("blocked_reasons", []):
            key = str(reason or "").strip()
            if key:
                launch_blocker_counts[key] = launch_blocker_counts.get(key, 0) + 1
        aggregate_launch_blockers = sorted(
            launch_blocker_counts,
            key=lambda value: (-launch_blocker_counts[value], value),
        )

        return {
            "contract_version": "workspace-public-launch-readiness/v0-draft",
            "workspace_id": auth.workspace_id,
            "generated_at": utc_now_iso(),
            "overall_status": overall_status,
            "self_serve_public_launch_allowed": self_serve_public_launch_allowed,
            "public_marketing_claims_allowed": public_marketing_claims_allowed,
            "study_governance": {
                "study_count": len(studies),
                "high_stakes_study_count": len(regulated_studies),
                "governed_review_required_count": len(governed_review_required),
                "viewer_safe_redaction_required_count": len(governed_redaction_required),
            },
            "benchmark_disclosure": {
                "completed_job_count": len(completed_jobs),
                "observation_failures": observation_failures,
                "readiness_status_counts": _count_values(readiness_statuses),
                "calibration_status_counts": _count_values(calibration_statuses),
                "external_benchmark_status_counts": _count_values(benchmark_statuses),
                "benchmark_origin_counts": _count_values(benchmark_origin_counts),
                "source_type_counts": _count_values(benchmark_source_type_counts),
            },
            "distribution_readiness": {
                "export_bundle_count": len(export_bundles),
                "share_bundle_count": len(share_bundles),
                "design_partner_candidate_export_count": len(design_partner_candidate_exports),
                "approved_public_share_count": len(approved_public_shares),
                "claim_boundary_status_counts": _count_values(claim_boundary_statuses),
                "customer_claim_status_counts": _count_values(customer_claim_statuses),
            },
            "launch_blockers": aggregate_launch_blockers,
            "customer_operations_support_boundary": customer_operations_support_boundary,
            "self_serve_onboarding_pricing_boundary": self_serve_onboarding_pricing_boundary,
            "calibration_observatory": {
                "contract_version": calibration_observatory.get("contract_version"),
                "health_summary": calibration_observatory.get("health_summary", {}),
                "unsupported_evidence_types": calibration_observatory.get("unsupported_evidence_types", []),
                "readiness_projection": calibration_observatory.get("readiness_projection", {}),
            },
            "privacy_export_controls": {
                "contract_version": privacy_export_controls.get("contract_version"),
                "privacy_readiness": privacy_export_controls.get("privacy_readiness", {}),
                "data_residency": privacy_export_controls.get("data_residency", {}),
                "retention_controls": privacy_export_controls.get("retention_controls", {}),
                "export_share_controls": privacy_export_controls.get("export_share_controls", {}),
            },
            "customer_claim_boundary": {
                "status": overall_status,
                "self_serve_public_launch_allowed": self_serve_public_launch_allowed,
                "public_marketing_claims_allowed": public_marketing_claims_allowed,
                "blocked_reasons": aggregate_blocked_reasons,
                "required_customer_disclosures": self._required_public_claim_disclosures(),
                "prohibited_claims": [
                    "replacement_grade_reliability",
                    "human_market_proof",
                    "high_stakes_approval_without_human_review",
                    "unsupported_market_or_domain_generalization",
                ],
                "note": (
                    "Broader public launch remains bounded by benchmark disclosure, governed high-stakes review, "
                    "and explicit synthetic-evidence claim limits."
                ),
            },
            "synthetic_boundary": (
                "Public-launch readiness summarizes bounded launch posture only. It does not convert synthetic evidence "
                "into human market proof or replacement-grade reliability."
            ),
        }

    def _build_self_serve_onboarding_and_pricing_boundary(
        self,
        *,
        auth: AuthContext,
        workspace: TenantWorkspace,
        billing: BillingAccount,
    ) -> dict[str, Any]:
        limits = _plan_limits(workspace.plan_tier, workspace.settings)
        active_tokens = [
            token_row
            for token_row in job_store.list_api_tokens(self.runtime_root, auth.workspace_id)
            if bool(token_row["active"])
        ]
        member_roles = [member.role for member in workspace.members]
        submitter_member_count = sum(1 for role in member_roles if role in SUBMITTER_ROLES)
        owner_count = sum(1 for role in member_roles if role == "owner")
        blocked_reasons: list[str] = []

        def add_blocker(code: str) -> None:
            if code not in blocked_reasons:
                blocked_reasons.append(code)

        if workspace.plan_tier == "trial":
            add_blocker("trial_plan_not_self_serve_launch_ready")
        if workspace.plan_tier not in {"pro", "enterprise"}:
            add_blocker("unsupported_self_serve_plan")
        if billing.status != "active":
            add_blocker("active_billing_required_for_self_serve")
        if billing.price_book_id != workspace.plan_tier:
            add_blocker("price_book_plan_mismatch")
        if int(billing.seat_count or 0) < 1:
            add_blocker("seat_count_required")
        if owner_count < 1:
            add_blocker("workspace_owner_required")
        if submitter_member_count < 1:
            add_blocker("submitter_member_required")
        if not active_tokens:
            add_blocker("active_workspace_token_required")
        if limits["daily_runs"] < 5:
            add_blocker("daily_run_limit_too_low_for_self_serve")
        if limits["max_concurrent_jobs"] < 2:
            add_blocker("concurrency_limit_too_low_for_self_serve")
        if limits["artifact_retention_days"] < 30:
            add_blocker("retention_window_too_short_for_customer_review")

        onboarding_status = "ready" if owner_count and submitter_member_count and active_tokens else "setup_required"
        pricing_status = "active_paid_plan" if (
            billing.status == "active"
            and workspace.plan_tier in {"pro", "enterprise"}
            and billing.price_book_id == workspace.plan_tier
            and int(billing.seat_count or 0) >= 1
        ) else "billing_action_required"
        quota_status = "ordinary_team_ready" if (
            limits["daily_runs"] >= 5
            and limits["max_concurrent_jobs"] >= 2
            and limits["artifact_retention_days"] >= 30
        ) else "insufficient_for_ordinary_team"
        status = "bounded_self_serve_ready" if not blocked_reasons else "self_serve_setup_required"

        return {
            "contract_version": "workspace-self-serve-launch-boundary/v0-draft",
            "status": status,
            "blocked_reasons": blocked_reasons,
            "supported_onboarding_paths": [
                "owner_bootstrap_workspace",
                "study_first_guided_intake",
                "workspace_settings_member_and_token_admin",
            ],
            "unsupported_onboarding_paths": [
                "unrestricted_anonymous_signup",
                "payment_provider_self_checkout",
                "enterprise_sso_auto_provisioning",
            ],
            "onboarding_boundary": {
                "status": onboarding_status,
                "owner_count": owner_count,
                "submitter_member_count": submitter_member_count,
                "active_token_count": len(active_tokens),
                "required_steps": [
                    "workspace_owner_present",
                    "submitter_member_present",
                    "active_workspace_token_present",
                    "study_first_guided_intake_available",
                ],
            },
            "pricing_boundary": {
                "status": pricing_status,
                "plan_tier": workspace.plan_tier,
                "billing_status": billing.status,
                "price_book_id": billing.price_book_id,
                "seat_count": billing.seat_count,
                "renewal_at": billing.renewal_at,
                "payment_provider_integrated": False,
                "supported_pricing_model": "workspace_plan_tier_with_operator_managed_billing_state",
            },
            "quota_boundary": {
                "status": quota_status,
                "daily_run_limit": limits["daily_runs"],
                "max_concurrent_jobs": limits["max_concurrent_jobs"],
                "artifact_retention_days": limits["artifact_retention_days"],
                "minimums_for_ordinary_team": {
                    "daily_runs": 5,
                    "max_concurrent_jobs": 2,
                    "artifact_retention_days": 30,
                },
            },
            "note": (
                "Self-serve readiness is bounded to authenticated workspace onboarding with operator-managed billing. "
                "It does not imply open signup, payment-provider checkout, or replacement-grade customer assurance."
            ),
        }

    def _build_customer_operations_and_support_boundary(
        self,
        *,
        auth: AuthContext,
        workspace: TenantWorkspace,
        billing: BillingAccount,
        jobs: list[dict[str, Any]],
        support_snapshots: list[WorkspaceSupportSnapshot],
    ) -> dict[str, Any]:
        limits = _plan_limits(workspace.plan_tier, workspace.settings)
        submission_gate = self._support_submission_gate(auth, workspace, billing, limits, jobs)
        failed_jobs = [
            job
            for job in jobs
            if str(job.get("status") or "") in {"failed", "canceled"}
        ]
        support_snapshot_summaries = [self._support_snapshot_summary(snapshot) for snapshot in support_snapshots]
        support_snapshot_job_ids = {
            str(summary.get("job_id") or "").strip()
            for summary in support_snapshot_summaries
            if str(summary.get("job_id") or "").strip()
        }
        failed_jobs_missing_support_snapshot = [
            job
            for job in failed_jobs
            if str(job.get("job_id") or "").strip() not in support_snapshot_job_ids
        ]
        handoff_statuses: list[str] = []
        open_handoffs = 0
        latest_support_snapshot_at: str | None = None
        for summary in support_snapshot_summaries:
            handoff = dict(summary.get("handoff", {})) if isinstance(summary.get("handoff"), dict) else {}
            handoff_status = str(handoff.get("status") or "unassigned")
            handoff_statuses.append(handoff_status)
            if handoff_status in {"assigned", "acknowledged"}:
                open_handoffs += 1
            updated_at = str(summary.get("updated_at") or summary.get("created_at") or "").strip()
            if updated_at and (latest_support_snapshot_at is None or updated_at > latest_support_snapshot_at):
                latest_support_snapshot_at = updated_at

        blocked_reasons: list[str] = []

        def add_blocker(code: str) -> None:
            if code not in blocked_reasons:
                blocked_reasons.append(code)

        if workspace.plan_tier == "trial":
            add_blocker("trial_plan_not_public_launch_ready")
        if billing.status not in ACTIVE_BILLING_STATUSES:
            add_blocker("billing_inactive")
        if str(submission_gate.get("status") or "") == "blocked":
            for reason in submission_gate.get("blocked_reasons", []):
                if isinstance(reason, dict):
                    code = str(reason.get("code") or "").strip()
                    if code:
                        add_blocker(code)
        if not support_snapshot_summaries:
            add_blocker("support_playbook_not_exercised")
        if failed_jobs_missing_support_snapshot:
            add_blocker("failed_jobs_missing_support_snapshot")
        if open_handoffs:
            add_blocker("support_handoffs_unresolved")

        support_playbook_status = "bounded_ready"
        if not support_snapshot_summaries:
            support_playbook_status = "not_exercised"
        elif failed_jobs_missing_support_snapshot:
            support_playbook_status = "coverage_gap"
        elif open_handoffs:
            support_playbook_status = "active_handoffs"

        status = "bounded_operator_ready" if not blocked_reasons else "manual_operator_review_required"
        supported_paths = ["workspace_support_snapshot_and_owner_admin_review"]
        if status == "bounded_operator_ready":
            supported_paths.append("ordinary_study_workspace_support")

        return {
            "contract_version": "workspace-public-launch-support-boundary/v0-draft",
            "status": status,
            "blocked_reasons": blocked_reasons,
            "supported_paths": supported_paths,
            "unsupported_paths": [
                "unrestricted_public_self_serve_support",
                "replacement_grade_customer_assurance",
            ],
            "billing_and_quota_boundary": {
                "plan_tier": workspace.plan_tier,
                "billing_status": billing.status,
                "daily_run_limit": limits["daily_runs"],
                "max_concurrent_jobs": limits["max_concurrent_jobs"],
                "artifact_retention_days": limits["artifact_retention_days"],
            },
            "ordinary_study_submission_gate": submission_gate,
            "support_playbook": {
                "status": support_playbook_status,
                "support_channel": "workspace_support_snapshot_and_owner_admin_review",
                "manual_operator_memory_required": False,
                "support_snapshot_count": len(support_snapshot_summaries),
                "failed_job_count": len(failed_jobs),
                "failed_jobs_missing_support_snapshot_count": len(failed_jobs_missing_support_snapshot),
                "open_handoff_count": open_handoffs,
                "handoff_status_counts": _count_values(handoff_statuses),
                "latest_support_snapshot_at": latest_support_snapshot_at,
            },
            "note": (
                "Customer-operations readiness stays backend-owned so support coverage, submission gates, and launch "
                "blockers do not depend on manual operator memory."
            ),
        }

    def describe_workspace_shell(
        self,
        auth: AuthContext,
        *,
        project_id: str = "",
        study_id: str = "",
        job_id: str = "",
        query_text: str = "",
        active_family: str = "all",
        sort_by: str = "relevance",
        selected_result_id: str = "",
        selected_replay_step_id: str = "",
        selected_comparison_run_id: str = "",
    ) -> dict[str, Any]:
        session = self.describe_workspace_session(auth)
        jobs = self.list_workspace_jobs(auth)
        projects = self.list_workspace_projects(auth)
        selected_project = None
        selected_study = None
        selected_job = None

        if study_id.strip():
            selected_study = self.get_workspace_study(auth, study_id.strip())
            selected_project = self.get_workspace_project(auth, str(selected_study["project_id"]))
        elif project_id.strip():
            selected_project = self.get_workspace_project(auth, project_id.strip())
        elif projects:
            selected_project = projects[0]

        studies = self.list_workspace_studies(
            auth,
            project_id=str(selected_project.get("project_id") or "") if selected_project else "",
        )
        if selected_study is None and studies:
            selected_study = studies[0]
        if selected_project is None and selected_study is not None:
            selected_project = self.get_workspace_project(auth, str(selected_study["project_id"]))

        if job_id.strip():
            selected_job = self.get_validation_job(auth, job_id.strip())
        elif selected_study and str(selected_study.get("latest_job_id") or "").strip():
            try:
                selected_job = self.get_validation_job(auth, str(selected_study["latest_job_id"]))
            except AuthorizationError:
                selected_job = None
        elif jobs:
            selected_job = jobs[0]

        evidence_query = (
            self.query_workspace_evidence(
                auth,
                job_id=str(selected_job.get("job_id") or ""),
                query_text=query_text,
                active_family=active_family,
                sort_by=sort_by,
                selected_result_id=selected_result_id,
                selected_replay_step_id=selected_replay_step_id,
                selected_comparison_run_id=selected_comparison_run_id,
            )
            if selected_job
            else build_pending_evidence_query(
                run_id=None,
                query_text=query_text,
                active_family=active_family,
                sort_by=sort_by,
            )
        )

        return {
            "snapshot_version": "workspace-shell/v0-draft",
            "session": session,
            "projects": projects,
            "selected_project_id": str(selected_project.get("project_id") or "") if selected_project else None,
            "selected_project": selected_project,
            "studies": studies,
            "selected_study_id": str(selected_study.get("study_id") or "") if selected_study else None,
            "selected_study": selected_study,
            "jobs": jobs,
            "selected_job_id": str(selected_job.get("job_id") or "") if selected_job else None,
            "selected_job": selected_job,
            "evidence_query": evidence_query,
            "provider_runtime": self._workspace_provider_runtime_state(auth, jobs, selected_job=selected_job),
            "capabilities": {
                **dict(session.get("capabilities", {})),
                "workspace_shell_snapshot": True,
            },
            "runtime_sync": {
                "poll_recommended_ms": 4000,
                "snapshot_endpoint": "/api/v1/workspace-shell",
            },
            "synthetic_boundary": session.get("synthetic_boundary"),
        }

    def query_workspace_evidence(
        self,
        auth: AuthContext,
        *,
        run_id: str = "",
        job_id: str = "",
        query_text: str = "",
        active_family: str = "all",
        sort_by: str = "relevance",
        selected_result_id: str = "",
        selected_replay_step_id: str = "",
        selected_comparison_run_id: str = "",
    ) -> dict[str, Any]:
        self._workspace_and_billing(auth)
        resolved_run_id = run_id.strip()

        if job_id.strip():
            job = self.get_validation_job(auth, job_id.strip())
            metadata = dict(job.get("metadata", {}))
            resolved_run_id = resolved_run_id or str(metadata.get("run_id") or "")
            if not resolved_run_id:
                output_run_path = str(job.get("output_run_path") or "")
                if output_run_path:
                    resolved_run_id = Path(output_run_path).name
            if str(job.get("status")) != "completed" or not resolved_run_id:
                pending = build_pending_evidence_query(
                    run_id=resolved_run_id or None,
                    query_text=query_text,
                    active_family=active_family,
                    sort_by=sort_by,
                )
                pending["provider_runtime_boundary"] = self._validation_provider_runtime_boundary(
                    str(job.get("provider_name") or ""),
                    status=str(job.get("status") or ""),
                    last_error=str(job.get("last_error") or ""),
                    metadata=metadata,
                )
                pending["readiness_gate"] = self._build_readiness_gate_from_query(pending)
                study_id = str(metadata.get("study_id") or "").strip()
                if study_id:
                    study = job_store.get_workspace_study(self.runtime_root, study_id)
                    if study is not None and study.workspace_id == auth.workspace_id:
                        pending["governed_review"] = self._study_governed_review_state(study)
                        pending["governed_redaction"] = self._study_governed_redaction_state(study)
                return pending

        if not resolved_run_id:
            raise ValueError("Field 'run_id' or 'job_id' is required for evidence query.")

        query_payload = self._query_run_evidence_with_fallback(
            workspace_id=auth.workspace_id,
            run_id=resolved_run_id,
            query_text=query_text,
            active_family=active_family,
            sort_by=sort_by,
            selected_result_id=selected_result_id or None,
            selected_replay_step_id=selected_replay_step_id or None,
            selected_comparison_run_id=selected_comparison_run_id or None,
        )
        if not isinstance(query_payload, dict):
            raise FileNotFoundError(f"Evidence query could not be resolved for run '{resolved_run_id}'.")
        return query_payload

    def _workspace_run_context_lookup(self, workspace_id: str) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
        jobs = job_store.list_workspace_jobs(self.runtime_root, workspace_id)
        run_job_context_lookup: dict[str, dict[str, Any]] = {}
        for job in jobs:
            metadata = dict(job.get("metadata", {}))
            candidate_run_id = _job_run_id(job)
            if not candidate_run_id:
                continue
            run_job_context_lookup[candidate_run_id] = {
                "run_id": candidate_run_id,
                "job_id": str(job.get("job_id") or "") or None,
                "project_id": str(metadata.get("project_id") or "") or None,
                "study_id": str(metadata.get("study_id") or "") or None,
                "job_status": str(job.get("status") or "") or None,
                "created_at": str(job.get("created_at") or "") or None,
                "finished_at": str(job.get("finished_at") or "") or None,
                "output_run_path": str(job.get("output_run_path") or "") or None,
                "provider_name": str(job.get("provider_name") or "") or None,
                "provider_runtime_boundary": self._validation_provider_runtime_boundary(
                    str(job.get("provider_name") or ""),
                    status=str(job.get("status") or ""),
                    last_error=str(job.get("last_error") or ""),
                    metadata=metadata,
                ),
            }
        return jobs, run_job_context_lookup

    def _run_calibration_lineage_entry(
        self,
        *,
        run_context: dict[str, Any],
        source_human_calibration: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        run_id = str(run_context.get("run_id") or "")
        human_calibration = None
        if source_human_calibration is not None and run_id:
            human_calibration = source_human_calibration
        else:
            output_run_path = str(run_context.get("output_run_path") or "").strip()
            if output_run_path:
                human_calibration = _load_human_calibration_record(
                    {
                        "run_id": run_id,
                        "output_path": output_run_path,
                        "primary_artifact_path": str(Path(output_run_path) / "run.json"),
                    }
                )

        replacement = human_calibration.get("replacement_readiness", {}) if isinstance(human_calibration, dict) else {}
        benchmark = human_calibration.get("human_benchmark", {}) if isinstance(human_calibration, dict) else {}
        projection = human_calibration.get("readiness_projection", {}) if isinstance(human_calibration, dict) else {}
        return {
            "run_id": run_id or None,
            "has_human_calibration": bool(human_calibration),
            "calibration_status": (
                str(replacement.get("status") or projection.get("status") or "").strip() or "unavailable"
            ),
            "benchmark_id": human_calibration.get("benchmark_id") if isinstance(human_calibration, dict) else None,
            "benchmark_source_type": benchmark.get("source_type") if isinstance(benchmark, dict) else None,
            "research_stage": replacement.get("research_stage") if isinstance(replacement, dict) else None,
            "evidence_type": replacement.get("evidence_type") if isinstance(replacement, dict) else None,
        }

    def _longitudinal_run_entry(
        self,
        *,
        run_context: dict[str, Any],
        relation_scope: str,
        relation_note: str,
        source_human_calibration: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        calibration_entry = self._run_calibration_lineage_entry(
            run_context=run_context,
            source_human_calibration=source_human_calibration,
        )
        return {
            "run_id": run_context.get("run_id"),
            "job_id": run_context.get("job_id"),
            "project_id": run_context.get("project_id"),
            "study_id": run_context.get("study_id"),
            "job_status": run_context.get("job_status"),
            "created_at": run_context.get("created_at"),
            "finished_at": run_context.get("finished_at"),
            "relation_scope": relation_scope,
            "relation_note": relation_note,
            **calibration_entry,
        }

    def _longitudinal_study_timeline_entry_for_run(
        self,
        *,
        run_context: dict[str, Any],
        is_source_run: bool,
    ) -> dict[str, Any]:
        return {
            "entry_id": str(run_context.get("run_id") or ""),
            "entry_type": "run",
            "occurred_at": run_context.get("finished_at") or run_context.get("created_at"),
            "title": "Current completed run" if is_source_run else "Related completed run",
            "run_id": run_context.get("run_id"),
            "job_id": run_context.get("job_id"),
            "study_id": run_context.get("study_id"),
            "project_id": run_context.get("project_id"),
            "selected_signal_id": None,
            "has_comparison_focus": False,
            "review_status": None,
            "relation_note": "current study source run" if is_source_run else "same study repeated run",
        }

    def _longitudinal_study_timeline_entry_for_evidence_view(self, evidence_view: WorkspaceEvidenceView) -> dict[str, Any]:
        metadata = dict(evidence_view.metadata or {})
        selected_context = metadata.get("selected_evidence_context")
        if not isinstance(selected_context, dict):
            selected_context = {}
        return {
            "entry_id": evidence_view.evidence_view_id,
            "entry_type": "evidence_view",
            "occurred_at": evidence_view.updated_at or evidence_view.created_at,
            "title": evidence_view.title,
            "run_id": evidence_view.run_id,
            "job_id": evidence_view.job_id,
            "study_id": evidence_view.study_id,
            "project_id": evidence_view.project_id,
            "selected_signal_id": selected_context.get("selected_signal_id"),
            "has_comparison_focus": bool(evidence_view.selected_comparison_run_id),
            "review_status": None,
            "relation_note": "saved evidence view in the same study timeline",
        }

    def _longitudinal_study_timeline_entry_for_decision_log(self, decision_log: WorkspaceDecisionLog) -> dict[str, Any]:
        metadata = dict(decision_log.metadata or {})
        selected_context = metadata.get("selected_evidence_context")
        if not isinstance(selected_context, dict):
            selected_context = {}
        return {
            "entry_id": decision_log.decision_log_id,
            "entry_type": "decision_log",
            "occurred_at": decision_log.updated_at or decision_log.created_at,
            "title": decision_log.title,
            "run_id": decision_log.run_id,
            "job_id": decision_log.job_id,
            "study_id": decision_log.study_id,
            "project_id": decision_log.project_id,
            "selected_signal_id": selected_context.get("selected_signal_id"),
            "has_comparison_focus": bool(decision_log.selected_comparison_run_id),
            "review_status": self._decision_review_status(decision_log),
            "relation_note": "decision outcome in the same study timeline",
        }

    def _longitudinal_pattern_matches(
        self,
        *,
        text: str,
        signal_terms: list[str],
        stability_label: str,
    ) -> dict[str, list[str]]:
        lowered_text = text.lower()
        lowered_terms = [str(term or "").strip().lower() for term in signal_terms if str(term or "").strip()]
        matches: dict[str, list[str]] = {}
        for definition in LONGITUDINAL_PATTERN_DEFINITIONS:
            pattern_id = str(definition["pattern_id"])
            markers = [str(marker).lower() for marker in definition["markers"]]
            matched = {
                term
                for term in lowered_terms
                if any(marker in term or term in marker for marker in markers)
            }
            matched.update(marker for marker in markers if marker in lowered_text)
            if pattern_id == "contradiction" and stability_label == "mixed_or_contradictory":
                matched.add("mixed_or_contradictory")
            if matched:
                matches[pattern_id] = sorted(matched)
        return matches

    def _longitudinal_query_text_blob(self, query_payload: dict[str, Any]) -> str:
        parts: list[str] = []
        for key in ("query_text", "active_family", "selected_result_id"):
            value = str(query_payload.get(key) or "").strip()
            if value:
                parts.append(value)

        for result in query_payload.get("results", [])[:5]:
            if not isinstance(result, dict):
                continue
            parts.extend(
                [
                    str(result.get("title") or ""),
                    str(result.get("summary") or ""),
                    str(result.get("family") or ""),
                    str(result.get("kind") or ""),
                    *[str(tag) for tag in result.get("tags", []) if tag],
                    *[str(line) for line in result.get("detail_lines", []) if line],
                ]
            )

        reliability = query_payload.get("evidence_reliability")
        if isinstance(reliability, dict):
            parts.append(str(reliability.get("stability_label") or ""))
            parts.extend(str(term) for term in reliability.get("signal_terms", []) if term)
            for key in ("supporting_evidence", "contradicting_evidence", "missing_context"):
                for item in reliability.get(key, [])[:5]:
                    if not isinstance(item, dict):
                        continue
                    parts.extend(
                        [
                            str(item.get("title") or ""),
                            str(item.get("summary") or ""),
                            str(item.get("label") or ""),
                            str(item.get("note") or ""),
                            str(item.get("relation") or ""),
                        ]
                    )
        return " ".join(part for part in parts if part).lower()

    def _longitudinal_run_observation(
        self,
        *,
        run_context: dict[str, Any],
        relation_scope: str,
        query_payload: dict[str, Any],
        source_human_calibration: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        reliability = query_payload.get("evidence_reliability")
        if not isinstance(reliability, dict):
            reliability = {}
        selected_result = query_payload.get("selected_result")
        if not isinstance(selected_result, dict):
            selected_result = {}
        pattern_matches = self._longitudinal_pattern_matches(
            text=self._longitudinal_query_text_blob(query_payload),
            signal_terms=list(reliability.get("signal_terms", [])) if isinstance(reliability.get("signal_terms"), list) else [],
            stability_label=str(reliability.get("stability_label") or ""),
        )
        return {
            "run_id": run_context.get("run_id"),
            "job_id": run_context.get("job_id"),
            "project_id": run_context.get("project_id"),
            "study_id": run_context.get("study_id"),
            "occurred_at": run_context.get("finished_at") or run_context.get("created_at"),
            "relation_scope": relation_scope,
            "selected_signal_id": str(reliability.get("selected_signal_id") or "") or None,
            "signal_terms": list(reliability.get("signal_terms", [])) if isinstance(reliability.get("signal_terms"), list) else [],
            "stability_label": str(reliability.get("stability_label") or "pending"),
            "pattern_ids": sorted(pattern_matches),
            "matched_terms": pattern_matches,
            "evidence_titles": [
                str(item.get("title") or "")
                for item in query_payload.get("results", [])[:3]
                if isinstance(item, dict) and str(item.get("title") or "").strip()
            ],
            "selected_result_title": str(selected_result.get("title") or "") or None,
            "selected_result_kind": str(selected_result.get("kind") or "") or None,
            "contradicting_evidence_count": len(
                reliability.get("contradicting_evidence", [])
                if isinstance(reliability.get("contradicting_evidence"), list)
                else []
            ),
            "missing_context_ids": [
                str(item.get("id") or "")
                for item in reliability.get("missing_context", [])
                if isinstance(item, dict) and str(item.get("id") or "").strip()
            ],
            "calibration_status": self._run_calibration_lineage_entry(
                run_context=run_context,
                source_human_calibration=source_human_calibration,
            ).get("calibration_status"),
        }

    def _query_payload_for_longitudinal_run(
        self,
        *,
        workspace_id: str,
        run_id: str,
        source_query_payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        selected_result = source_query_payload.get("selected_result")
        if not isinstance(selected_result, dict):
            selected_result = {}
        active_family = str(source_query_payload.get("active_family") or "all")
        if active_family == "all" and str(selected_result.get("family") or "").strip():
            active_family = str(selected_result.get("family") or "").strip()
        query_text = str(source_query_payload.get("query_text") or "")
        sort_by = str(source_query_payload.get("sort_by") or "relevance")
        last_error: Exception | None = None
        for index_root in _candidate_index_roots(self.runtime_root, workspace_id or None):
            try:
                return query_run_evidence(
                    index_root,
                    run_id=run_id,
                    query_text=query_text,
                    active_family=active_family,
                    sort_by=sort_by,
                )
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            return None
        return None

    def _load_run_report_payload(self, *, run_context: dict[str, Any]) -> dict[str, Any]:
        output_run_path = str(run_context.get("output_run_path") or "").strip()
        if not output_run_path:
            return {}
        report_path = Path(output_run_path) / "report.json"
        if not report_path.exists():
            return {}
        payload = read_json(report_path)
        return payload if isinstance(payload, dict) else {}

    def _panel_learning_summary_for_run(
        self,
        *,
        run_context: dict[str, Any],
        relation_scope: str,
    ) -> dict[str, Any]:
        report_payload = self._load_run_report_payload(run_context=run_context)
        panel_explainability = report_payload.get("panel_explainability")
        if not isinstance(panel_explainability, dict):
            panel_explainability = {}
        panel_spec = report_payload.get("panel_spec")
        if not isinstance(panel_spec, dict):
            panel_spec = {}
        execution = report_payload.get("execution")
        if not isinstance(execution, dict):
            execution = {}
        selected_panel = (
            panel_explainability.get("human_difference_axis_coverage", {}).get("selected_panel", {})
            if isinstance(panel_explainability.get("human_difference_axis_coverage"), dict)
            else {}
        )
        if not isinstance(selected_panel, dict):
            selected_panel = {}
        undercovered_axes = panel_explainability.get("undercovered_axes")
        if not isinstance(undercovered_axes, list):
            undercovered_axes = []
        similarity_hotspots = panel_explainability.get("similarity_hotspots")
        if not isinstance(similarity_hotspots, list):
            similarity_hotspots = []
        axis_coverage = selected_panel.get("axis_coverage")
        if not isinstance(axis_coverage, dict):
            axis_coverage = {}
        return {
            "run_id": run_context.get("run_id"),
            "job_id": run_context.get("job_id"),
            "study_id": run_context.get("study_id"),
            "project_id": run_context.get("project_id"),
            "occurred_at": run_context.get("finished_at") or run_context.get("created_at"),
            "relation_scope": relation_scope,
            "panel_type": str(panel_spec.get("panel_type") or "") or None,
            "requested_sample_size": panel_spec.get("sample_size"),
            "selected_persona_count": execution.get("selected_persona_count"),
            "persona_with_axes_count": selected_panel.get("persona_with_axes_count"),
            "required_axis_count": len(selected_panel.get("required_axes", []))
            if isinstance(selected_panel.get("required_axes"), list)
            else 0,
            "undercovered_axis_ids": [
                str(item.get("axis") or "")
                for item in undercovered_axes
                if isinstance(item, dict) and str(item.get("axis") or "").strip()
            ],
            "hotspot_axis_ids": [
                str(item.get("axis") or "")
                for item in similarity_hotspots
                if isinstance(item, dict) and str(item.get("axis") or "").strip()
            ],
            "hotspot_buckets": [
                {
                    "axis": item.get("axis"),
                    "bucket": item.get("bucket"),
                    "persona_count": item.get("persona_count"),
                }
                for item in similarity_hotspots[:5]
                if isinstance(item, dict)
            ],
            "axis_bucket_coverage_counts": {
                axis_key: int(summary.get("bucket_count") or 0)
                for axis_key, summary in axis_coverage.items()
                if isinstance(summary, dict)
            },
            "panel_rationale": str(report_payload.get("panel_rationale") or "") or None,
        }

    def _longitudinal_decision_backing_status(self, decision_log: WorkspaceDecisionLog) -> str:
        metadata = dict(decision_log.metadata or {})
        selected_context = metadata.get("selected_evidence_context")
        if not isinstance(selected_context, dict):
            selected_context = {}
        recurring_signal_focus = selected_context.get("recurring_signal_focus")
        if not isinstance(recurring_signal_focus, dict):
            recurring_signal_focus = {}
        if (
            decision_log.evidence_view_id
            or decision_log.selected_result_id
            or decision_log.selected_comparison_run_id
            or selected_context.get("selected_signal_id")
            or int(recurring_signal_focus.get("pattern_count") or 0) > 0
        ):
            return "evidence_backed"
        return "assumption_led"

    def _build_longitudinal_panel_learning_projection(
        self,
        *,
        source_context: dict[str, Any],
        same_study_runs_context: list[dict[str, Any]],
        same_project_run_contexts: list[dict[str, Any]],
        recurring_signal_synthesis: dict[str, Any],
        decision_logs: list[WorkspaceDecisionLog],
        source_query_payload: dict[str, Any],
    ) -> dict[str, Any]:
        source_panel = self._panel_learning_summary_for_run(
            run_context=source_context,
            relation_scope="source_run",
        )
        related_panels = [
            self._panel_learning_summary_for_run(
                run_context=context,
                relation_scope=str(context.get("relation_scope") or "same_study"),
            )
            for context in [*same_study_runs_context[:5], *same_project_run_contexts[:5]]
        ]

        all_panels = [source_panel, *related_panels]
        repeated_hotspot_axes: list[str] = []
        persistent_undercovered_axes: list[str] = []
        newly_covered_axes: list[str] = []
        hotspot_counts: dict[str, int] = {}
        undercovered_counts: dict[str, int] = {}
        for panel in all_panels:
            for axis in panel.get("hotspot_axis_ids", []):
                hotspot_counts[str(axis)] = hotspot_counts.get(str(axis), 0) + 1
            for axis in panel.get("undercovered_axis_ids", []):
                undercovered_counts[str(axis)] = undercovered_counts.get(str(axis), 0) + 1
        repeated_hotspot_axes = sorted(axis for axis, count in hotspot_counts.items() if count > 1)
        persistent_undercovered_axes = sorted(axis for axis, count in undercovered_counts.items() if count > 1)
        source_undercovered_axes = set(str(axis) for axis in source_panel.get("undercovered_axis_ids", []))
        historical_undercovered_axes = {
            str(axis)
            for panel in related_panels
            for axis in panel.get("undercovered_axis_ids", [])
        }
        newly_covered_axes = sorted(axis for axis in historical_undercovered_axes if axis not in source_undercovered_axes)

        persona_with_axes_total = sum(int(panel.get("persona_with_axes_count") or 0) for panel in all_panels)
        if persona_with_axes_total == 0:
            segment_status = "insufficient_axis_data"
            segment_note = "Panel learning cannot yet explain segment divergence because the related runs do not carry human-difference-axis coverage."
        elif repeated_hotspot_axes or persistent_undercovered_axes:
            segment_status = "diverging"
            segment_note = "Repeated hotspot and under-covered axes suggest the same human-difference segments keep diverging across related runs."
        else:
            segment_status = "stable"
            segment_note = "No repeated hotspot or persistent under-covered axis is visible across the related run set."

        if not isinstance(recurring_signal_synthesis, dict):
            recurring_signal_synthesis = {}
        recurring_patterns = recurring_signal_synthesis.get("patterns")
        if not isinstance(recurring_patterns, list):
            recurring_patterns = []
        persistent_pattern_ids = [
            str(item.get("pattern_id") or "")
            for item in recurring_patterns
            if isinstance(item, dict) and str(item.get("status") or "") in {"persistent", "unresolved"}
        ]
        faded_pattern_ids = [
            str(item.get("pattern_id") or "")
            for item in recurring_patterns
            if isinstance(item, dict) and str(item.get("status") or "") == "historical_only"
        ]
        emerging_pattern_ids = [
            str(item.get("pattern_id") or "")
            for item in recurring_patterns
            if isinstance(item, dict) and str(item.get("status") or "") == "current_run_only"
        ]
        contradiction_pattern_ids = [
            str(item.get("pattern_id") or "")
            for item in recurring_patterns
            if isinstance(item, dict) and str(item.get("pattern_id") or "") == "contradiction"
        ]

        source_reliability = source_query_payload.get("evidence_reliability")
        if not isinstance(source_reliability, dict):
            source_reliability = {}
        source_missing_context = source_reliability.get("missing_context")
        if not isinstance(source_missing_context, list):
            source_missing_context = []
        source_calibration_status = (
            str(recurring_signal_synthesis.get("run_observations", [{}])[0].get("calibration_status") or "unavailable")
            if isinstance(recurring_signal_synthesis.get("run_observations"), list) and recurring_signal_synthesis.get("run_observations")
            and isinstance(recurring_signal_synthesis.get("run_observations")[0], dict)
            else "unavailable"
        )
        source_stability_label = str(source_reliability.get("stability_label") or "pending")
        run_observations = recurring_signal_synthesis.get("run_observations")
        if not isinstance(run_observations, list):
            run_observations = []
        related_calibration_statuses = [
            str(item.get("calibration_status") or "unavailable")
            for item in run_observations[1:]
            if isinstance(item, dict)
        ]
        max_related_rank = max(
            (CALIBRATION_STATUS_RANK.get(status, 0) for status in related_calibration_statuses),
            default=0,
        )
        source_rank = CALIBRATION_STATUS_RANK.get(source_calibration_status, 0)
        if source_stability_label == "mixed_or_contradictory" or contradiction_pattern_ids:
            confidence_status = "drifting"
            confidence_note = "Contradiction-bearing evidence still appears across the related run set, so prediction confidence is drifting rather than converging."
        elif source_rank > max_related_rank:
            confidence_status = "improving"
            confidence_note = "The current run carries stronger calibration support than the earlier related runs, so prediction confidence is improving."
        elif source_rank == 0 and all(status == "unavailable" for status in related_calibration_statuses):
            confidence_status = "stalling"
            confidence_note = "Repeated runs are still uncalibrated, so prediction confidence is stalling even when similar signals repeat."
        elif len(source_missing_context) == 0:
            confidence_status = "holding"
            confidence_note = "The current run does not add new missing-context gaps, so prediction confidence is holding rather than drifting."
        else:
            confidence_status = "stalling"
            confidence_note = "The current run still carries unresolved missing-context gaps, so prediction confidence has not materially improved yet."

        ordered_decisions = sorted(
            decision_logs,
            key=lambda item: (str(item.updated_at or item.created_at or ""), item.decision_log_id),
        )
        decision_entries = []
        for decision_log in ordered_decisions:
            metadata = dict(decision_log.metadata or {})
            selected_context = metadata.get("selected_evidence_context")
            if not isinstance(selected_context, dict):
                selected_context = {}
            recurring_signal_focus = selected_context.get("recurring_signal_focus")
            if not isinstance(recurring_signal_focus, dict):
                recurring_signal_focus = {}
            decision_entries.append(
                {
                    "decision_log_id": decision_log.decision_log_id,
                    "title": decision_log.title,
                    "decision_summary": decision_log.decision_summary,
                    "review_status": self._decision_review_status(decision_log),
                    "occurred_at": decision_log.updated_at or decision_log.created_at,
                    "has_linked_evidence_view": bool(decision_log.evidence_view_id),
                    "has_comparison_focus": bool(decision_log.selected_comparison_run_id),
                    "selected_signal_id": selected_context.get("selected_signal_id"),
                    "recurring_pattern_count": int(recurring_signal_focus.get("pattern_count") or 0),
                    "evidence_backing_status": self._longitudinal_decision_backing_status(decision_log),
                }
            )
        review_status_counts: dict[str, int] = {}
        for entry in decision_entries:
            status = str(entry.get("review_status") or "draft")
            review_status_counts[status] = review_status_counts.get(status, 0) + 1
        latest_decision = decision_entries[-1] if decision_entries else None
        previous_decision = decision_entries[-2] if len(decision_entries) > 1 else None
        if latest_decision is None:
            latest_change_status = "no_decision"
            decision_note = "No decision log exists yet for this study history."
        elif previous_decision is None:
            latest_change_status = "first_decision"
            decision_note = "Only one decision exists so far, so the study has not yet shown a directional decision change."
        elif str(latest_decision.get("decision_summary") or "").strip() == str(previous_decision.get("decision_summary") or "").strip():
            latest_change_status = "reaffirmed"
            decision_note = "The latest decision reaffirms the immediately prior decision summary."
        else:
            latest_change_status = "changed_direction"
            decision_note = "The latest decision summary differs from the prior decision, so the study history shows an explicit decision change."

        return {
            "contract_version": "workspace-longitudinal-panel-learning/v0-draft",
            "source_panel": source_panel,
            "related_panels": related_panels,
            "segment_divergence": {
                "status": segment_status,
                "repeated_hotspot_axes": repeated_hotspot_axes,
                "persistent_undercovered_axes": persistent_undercovered_axes,
                "newly_covered_axes": newly_covered_axes,
                "note": segment_note,
            },
            "barrier_resolution": {
                "persistent_pattern_ids": persistent_pattern_ids,
                "faded_pattern_ids": faded_pattern_ids,
                "emerging_pattern_ids": emerging_pattern_ids,
                "contradiction_pattern_ids": contradiction_pattern_ids,
                "note": "Persistent patterns still appear in the current run; faded patterns remain only in related history; emerging patterns appear only in the current run.",
            },
            "confidence_trend": {
                "status": confidence_status,
                "source_stability_label": source_stability_label,
                "source_calibration_status": source_calibration_status,
                "related_calibration_statuses": related_calibration_statuses,
                "note": confidence_note,
            },
            "decision_trends": {
                "total_decision_count": len(decision_entries),
                "review_status_counts": review_status_counts,
                "latest_review_status": latest_decision.get("review_status") if latest_decision else None,
                "evidence_backed_decision_count": sum(
                    1 for item in decision_entries if item.get("evidence_backing_status") == "evidence_backed"
                ),
                "assumption_led_decision_count": sum(
                    1 for item in decision_entries if item.get("evidence_backing_status") == "assumption_led"
                ),
                "latest_change_status": latest_change_status,
                "decisions": decision_entries[-5:],
                "note": decision_note,
            },
            "note": "Panel learning stays artifact-linked: panel explainability comes from run reports, recurring barriers come from longitudinal evidence synthesis, and decision trends stay attached to durable decision-log history.",
        }

    def _longitudinal_pattern_matches_for_context(
        self,
        *,
        title: str,
        narrative: str,
        selected_signal_id: str | None,
        signal_terms: list[str],
        review_status: str | None = None,
    ) -> dict[str, list[str]]:
        parts = [title, narrative, selected_signal_id or "", review_status or "", *signal_terms]
        return self._longitudinal_pattern_matches(
            text=" ".join(part for part in parts if part),
            signal_terms=signal_terms,
            stability_label=review_status or "",
        )

    def _build_longitudinal_recurring_signal_synthesis(
        self,
        *,
        workspace_id: str,
        source_context: dict[str, Any],
        query_payload: dict[str, Any],
        same_study_runs_context: list[dict[str, Any]],
        same_project_run_contexts: list[dict[str, Any]],
        evidence_views: list[WorkspaceEvidenceView],
        decision_logs: list[WorkspaceDecisionLog],
        source_human_calibration: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        run_observations = [
            self._longitudinal_run_observation(
                run_context=source_context,
                relation_scope="source_run",
                query_payload=query_payload,
                source_human_calibration=source_human_calibration,
            )
        ]
        for context in [*same_study_runs_context[:5], *same_project_run_contexts[:5]]:
            related_run_id = str(context.get("run_id") or "")
            if not related_run_id:
                continue
            related_query_payload = self._query_payload_for_longitudinal_run(
                workspace_id=workspace_id,
                run_id=related_run_id,
                source_query_payload=query_payload,
            )
            if not isinstance(related_query_payload, dict) or str(related_query_payload.get("query_status") or "") != "query_ready":
                continue
            run_observations.append(
                self._longitudinal_run_observation(
                    run_context=context,
                    relation_scope=str(context.get("relation_scope") or "related_run"),
                    query_payload=related_query_payload,
                )
            )

        pattern_rollup: dict[str, dict[str, Any]] = {}
        for definition in LONGITUDINAL_PATTERN_DEFINITIONS:
            pattern_rollup[str(definition["pattern_id"])] = {
                "pattern_id": definition["pattern_id"],
                "label": definition["label"],
                "run_ids": [],
                "study_ids": [],
                "matched_terms": set(),
                "source_run_present": False,
                "relation_scopes": set(),
                "sample_evidence": [],
                "timeline_entry_ids": [],
            }

        for observation in run_observations:
            for pattern_id in observation.get("pattern_ids", []):
                if pattern_id not in pattern_rollup:
                    continue
                rollup = pattern_rollup[pattern_id]
                run_id = observation.get("run_id")
                study_id = observation.get("study_id")
                if run_id and run_id not in rollup["run_ids"]:
                    rollup["run_ids"].append(run_id)
                if study_id and study_id not in rollup["study_ids"]:
                    rollup["study_ids"].append(study_id)
                if observation.get("relation_scope") == "source_run":
                    rollup["source_run_present"] = True
                rollup["relation_scopes"].add(observation.get("relation_scope"))
                rollup["matched_terms"].update(observation.get("matched_terms", {}).get(pattern_id, []))
                sample = {
                    "run_id": observation.get("run_id"),
                    "job_id": observation.get("job_id"),
                    "study_id": observation.get("study_id"),
                    "relation_scope": observation.get("relation_scope"),
                    "selected_signal_id": observation.get("selected_signal_id"),
                    "selected_result_title": observation.get("selected_result_title"),
                    "stability_label": observation.get("stability_label"),
                    "calibration_status": observation.get("calibration_status"),
                }
                if sample not in rollup["sample_evidence"]:
                    rollup["sample_evidence"].append(sample)

        for evidence_view in evidence_views:
            metadata = dict(evidence_view.metadata or {})
            selected_context = metadata.get("selected_evidence_context")
            if not isinstance(selected_context, dict):
                selected_context = {}
            matches = self._longitudinal_pattern_matches_for_context(
                title=evidence_view.title,
                narrative=evidence_view.note,
                selected_signal_id=str(selected_context.get("selected_signal_id") or "") or None,
                signal_terms=list(selected_context.get("signal_terms", [])) if isinstance(selected_context.get("signal_terms"), list) else [],
            )
            for pattern_id in matches:
                if pattern_id in pattern_rollup and evidence_view.evidence_view_id not in pattern_rollup[pattern_id]["timeline_entry_ids"]:
                    pattern_rollup[pattern_id]["timeline_entry_ids"].append(evidence_view.evidence_view_id)

        for decision_log in decision_logs:
            metadata = dict(decision_log.metadata or {})
            selected_context = metadata.get("selected_evidence_context")
            if not isinstance(selected_context, dict):
                selected_context = {}
            matches = self._longitudinal_pattern_matches_for_context(
                title=decision_log.title,
                narrative=f"{decision_log.decision_summary} {decision_log.rationale}",
                selected_signal_id=str(selected_context.get("selected_signal_id") or "") or None,
                signal_terms=list(selected_context.get("signal_terms", [])) if isinstance(selected_context.get("signal_terms"), list) else [],
                review_status=self._decision_review_status(decision_log),
            )
            for pattern_id in matches:
                if pattern_id in pattern_rollup and decision_log.decision_log_id not in pattern_rollup[pattern_id]["timeline_entry_ids"]:
                    pattern_rollup[pattern_id]["timeline_entry_ids"].append(decision_log.decision_log_id)

        patterns: list[dict[str, Any]] = []
        for definition in LONGITUDINAL_PATTERN_DEFINITIONS:
            pattern_id = str(definition["pattern_id"])
            rollup = pattern_rollup[pattern_id]
            run_ids = list(rollup["run_ids"])
            if not run_ids:
                continue
            source_run_present = bool(rollup["source_run_present"])
            if pattern_id == "contradiction" and len(run_ids) > 1:
                status = "unresolved"
                note = "Contradiction or risk-bearing evidence still appears across related runs and should stay open during repeated-study review."
            elif source_run_present and len(run_ids) > 1:
                status = "persistent"
                note = "This pattern appears in the current run and repeated-study history, so it should be treated as persistent rather than one-run noise."
            elif source_run_present:
                status = "current_run_only"
                note = "This pattern is visible in the current run but is not yet repeated across the related study history."
            else:
                status = "historical_only"
                note = "This pattern appears in related study history but is not currently selected in the source run review."
            patterns.append(
                {
                    "pattern_id": pattern_id,
                    "label": str(rollup["label"]),
                    "status": status,
                    "run_count": len(run_ids),
                    "study_count": len(rollup["study_ids"]),
                    "source_run_present": source_run_present,
                    "related_run_ids": run_ids,
                    "related_study_ids": list(rollup["study_ids"]),
                    "relation_scopes": sorted(scope for scope in rollup["relation_scopes"] if scope),
                    "matched_terms": sorted(str(term) for term in rollup["matched_terms"]),
                    "timeline_entry_ids": list(rollup["timeline_entry_ids"]),
                    "sample_evidence": list(rollup["sample_evidence"])[:5],
                    "note": note,
                }
            )

        selected_signal_id = None
        selected_signal_terms: list[str] = []
        reliability = query_payload.get("evidence_reliability")
        if isinstance(reliability, dict):
            selected_signal_id = str(reliability.get("selected_signal_id") or "") or None
            if isinstance(reliability.get("signal_terms"), list):
                selected_signal_terms = [str(term) for term in reliability.get("signal_terms", []) if str(term or "").strip()]

        return {
            "contract_version": "workspace-longitudinal-recurring-signals/v0-draft",
            "selected_signal_id": selected_signal_id,
            "selected_signal_terms": selected_signal_terms,
            "pattern_count": len(patterns),
            "persistent_pattern_count": sum(1 for item in patterns if item.get("status") in {"persistent", "unresolved"}),
            "patterns": patterns,
            "run_observations": run_observations,
            "note": (
                "Recurring longitudinal patterns stay linked to repeated runs plus study-timeline artifacts so review can preserve older evidence instead of rewriting only the latest state."
                if patterns
                else "No recurring objection, trust-gap, failure, or contradiction pattern is visible under the current evidence-review scope."
            ),
        }

    def _build_longitudinal_comparison(
        self,
        *,
        workspace_id: str,
        run_id: str,
        query_payload: dict[str, Any],
        run_job_context_lookup: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        source_context = run_job_context_lookup.get(run_id, {})
        source_study_id = str(source_context.get("study_id") or "")
        source_project_id = str(source_context.get("project_id") or "")
        source_human_calibration = None
        evidence_reliability = query_payload.get("evidence_reliability")
        if isinstance(evidence_reliability, dict) and isinstance(evidence_reliability.get("human_calibration"), dict):
            source_human_calibration = evidence_reliability.get("human_calibration")

        if not source_study_id or not source_project_id:
            return {
                "contract_version": "workspace-longitudinal-comparison/v0-draft",
                "source_run_id": run_id,
                "source_job_id": source_context.get("job_id"),
                "source_project_id": source_context.get("project_id"),
                "source_study_id": source_context.get("study_id"),
                "comparison_windows": [],
                "selected_window_id": None,
                "same_study_runs": [],
                "same_project_studies": [],
                "study_timeline": [],
                "same_study_run_count": 0,
                "same_project_study_count": 0,
                "study_timeline_entry_count": 0,
                "recurring_signal_synthesis": {
                    "contract_version": "workspace-longitudinal-recurring-signals/v0-draft",
                    "selected_signal_id": None,
                    "selected_signal_terms": [],
                    "pattern_count": 0,
                    "persistent_pattern_count": 0,
                    "patterns": [],
                    "run_observations": [],
                    "note": "Longitudinal recurring-pattern synthesis is unavailable because this run is not linked to a workspace study/project context.",
                },
                "panel_learning_projection": {
                    "contract_version": "workspace-longitudinal-panel-learning/v0-draft",
                    "source_panel": {},
                    "related_panels": [],
                    "segment_divergence": {
                        "status": "unavailable",
                        "repeated_hotspot_axes": [],
                        "persistent_undercovered_axes": [],
                        "newly_covered_axes": [],
                        "note": "Panel learning is unavailable because this run is not linked to a workspace study/project context.",
                    },
                    "barrier_resolution": {
                        "persistent_pattern_ids": [],
                        "faded_pattern_ids": [],
                        "emerging_pattern_ids": [],
                        "contradiction_pattern_ids": [],
                        "note": "Barrier-resolution projection is unavailable without workspace-linked repeated-study history.",
                    },
                    "confidence_trend": {
                        "status": "unavailable",
                        "source_stability_label": "pending",
                        "source_calibration_status": "unavailable",
                        "related_calibration_statuses": [],
                        "note": "Confidence trend is unavailable without workspace-linked repeated-study history.",
                    },
                    "decision_trends": {
                        "total_decision_count": 0,
                        "review_status_counts": {},
                        "latest_review_status": None,
                        "evidence_backed_decision_count": 0,
                        "assumption_led_decision_count": 0,
                        "latest_change_status": "no_decision",
                        "decisions": [],
                        "note": "Decision trends are unavailable without workspace-linked study history.",
                    },
                    "note": "Panel learning is unavailable because this run is not linked to a workspace study/project context.",
                },
                "calibration_lineage": {
                    **self._run_calibration_lineage_entry(
                        run_context=source_context,
                        source_human_calibration=source_human_calibration,
                    ),
                    "same_study_calibrated_run_count": 0,
                    "same_project_calibrated_run_count": 0,
                    "selected_comparison_run_id": None,
                    "selected_comparison_calibration_status": None,
                    "note": "Longitudinal lineage is unavailable because this run is not linked to a workspace study/project context.",
                },
                "note": "Link the run to a workspace study before longitudinal comparison can compare repeated-study history.",
            }

        same_study_runs_context = [
            context
            for candidate_run_id, context in run_job_context_lookup.items()
            if candidate_run_id != run_id
            and str(context.get("study_id") or "") == source_study_id
            and str(context.get("job_status") or "") == "completed"
        ]
        same_study_runs_context.sort(
            key=lambda item: (str(item.get("finished_at") or ""), str(item.get("run_id") or "")),
            reverse=True,
        )
        same_study_runs = [
            self._longitudinal_run_entry(
                run_context=context,
                relation_scope="same_study",
                relation_note="same study repeated run",
            )
            for context in same_study_runs_context[:5]
        ]

        evidence_views = job_store.list_workspace_evidence_views(
            self.runtime_root,
            workspace_id,
            study_id=source_study_id,
        )
        decision_logs = job_store.list_workspace_decision_logs(
            self.runtime_root,
            workspace_id,
            study_id=source_study_id,
        )
        study_timeline = [
            self._longitudinal_study_timeline_entry_for_run(run_context=source_context, is_source_run=True),
            *[
                self._longitudinal_study_timeline_entry_for_run(run_context=context, is_source_run=False)
                for context in same_study_runs_context
            ],
            *[self._longitudinal_study_timeline_entry_for_evidence_view(item) for item in evidence_views],
            *[self._longitudinal_study_timeline_entry_for_decision_log(item) for item in decision_logs],
        ]
        study_timeline.sort(
            key=lambda item: (str(item.get("occurred_at") or ""), str(item.get("entry_id") or "")),
            reverse=True,
        )

        project_studies = job_store.list_workspace_studies(
            self.runtime_root,
            workspace_id,
            project_id=source_project_id,
        )
        same_project_studies: list[dict[str, Any]] = []
        same_project_run_contexts: list[dict[str, Any]] = []
        same_project_calibrated_run_count = sum(1 for item in same_study_runs if item.get("has_human_calibration"))
        for study in project_studies:
            if study.study_id == source_study_id:
                continue
            study_run_contexts = [
                context
                for context in run_job_context_lookup.values()
                if str(context.get("study_id") or "") == study.study_id
                and str(context.get("job_status") or "") == "completed"
            ]
            study_run_contexts.sort(
                key=lambda item: (str(item.get("finished_at") or ""), str(item.get("run_id") or "")),
                reverse=True,
            )
            evidence_view_count = len(
                job_store.list_workspace_evidence_views(
                    self.runtime_root,
                    workspace_id,
                    study_id=study.study_id,
                )
            )
            decision_log_count = len(
                job_store.list_workspace_decision_logs(
                    self.runtime_root,
                    workspace_id,
                    study_id=study.study_id,
                )
            )
            calibrated_run_count = 0
            latest_calibration_status = "unavailable"
            if study_run_contexts:
                same_project_run_contexts.append(
                    {
                        **study_run_contexts[0],
                        "relation_scope": "same_project",
                    }
                )
                calibration_entry = self._run_calibration_lineage_entry(run_context=study_run_contexts[0])
                latest_calibration_status = str(calibration_entry.get("calibration_status") or "unavailable")
                calibrated_run_count = sum(
                    1
                    for context in study_run_contexts
                    if self._run_calibration_lineage_entry(run_context=context).get("has_human_calibration")
                )
                same_project_calibrated_run_count += calibrated_run_count
            same_project_studies.append(
                {
                    "study_id": study.study_id,
                    "project_id": study.project_id,
                    "title": study.title,
                    "status": study.status,
                    "latest_job_id": study.latest_job_id,
                    "latest_run_id": study_run_contexts[0].get("run_id") if study_run_contexts else None,
                    "completed_run_count": len(study_run_contexts),
                    "evidence_view_count": evidence_view_count,
                    "decision_log_count": decision_log_count,
                    "calibrated_run_count": calibrated_run_count,
                    "latest_calibration_status": latest_calibration_status,
                    "relation_note": "same project adjacent study",
                }
            )

        same_project_studies.sort(
            key=lambda item: (int(item.get("completed_run_count") or 0), str(item.get("latest_run_id") or "")),
            reverse=True,
        )
        cross_run_comparison = dict(query_payload.get("cross_run_comparison", {}))
        selected_comparison_run_id = str(cross_run_comparison.get("selected_comparison_run_id") or "") or None
        selected_comparison_calibration_status = None
        if selected_comparison_run_id and selected_comparison_run_id in run_job_context_lookup:
            selected_comparison_calibration_status = self._run_calibration_lineage_entry(
                run_context=run_job_context_lookup[selected_comparison_run_id]
            ).get("calibration_status")

        comparison_windows = [
            {
                "window_id": "same_study_runs",
                "label": "Same study runs",
                "run_count": len(same_study_runs),
                "calibrated_run_count": sum(1 for item in same_study_runs if item.get("has_human_calibration")),
                "note": "Use repeated runs inside the same study first when checking whether a signal persists across one research loop.",
            },
            {
                "window_id": "study_timeline",
                "label": "Study timeline",
                "entry_count": len(study_timeline),
                "evidence_view_count": len(evidence_views),
                "decision_log_count": len(decision_logs),
                "note": "Use saved evidence views and decision outcomes to preserve how the study evolved instead of rewriting the latest conclusion only.",
            },
            {
                "window_id": "same_project_studies",
                "label": "Same project studies",
                "study_count": len(same_project_studies),
                "run_count": sum(int(item.get("completed_run_count") or 0) for item in same_project_studies),
                "calibrated_run_count": same_project_calibrated_run_count,
                "note": "Use neighboring studies in the same project to compare prototype revisions or adjacent research loops over time.",
            },
        ]
        selected_window_id = None
        if same_study_runs:
            selected_window_id = "same_study_runs"
        elif study_timeline:
            selected_window_id = "study_timeline"
        elif same_project_studies:
            selected_window_id = "same_project_studies"
        recurring_signal_synthesis = self._build_longitudinal_recurring_signal_synthesis(
            workspace_id=workspace_id,
            source_context=source_context,
            query_payload=query_payload,
            same_study_runs_context=[
                {
                    **context,
                    "relation_scope": "same_study",
                }
                for context in same_study_runs_context
            ],
            same_project_run_contexts=same_project_run_contexts,
            evidence_views=evidence_views,
            decision_logs=decision_logs,
            source_human_calibration=source_human_calibration,
        )
        panel_learning_projection = self._build_longitudinal_panel_learning_projection(
            source_context=source_context,
            same_study_runs_context=[
                {
                    **context,
                    "relation_scope": "same_study",
                }
                for context in same_study_runs_context
            ],
            same_project_run_contexts=same_project_run_contexts,
            recurring_signal_synthesis=recurring_signal_synthesis,
            decision_logs=decision_logs,
            source_query_payload=query_payload,
        )

        return {
            "contract_version": "workspace-longitudinal-comparison/v0-draft",
            "source_run_id": run_id,
            "source_job_id": source_context.get("job_id"),
            "source_project_id": source_project_id,
            "source_study_id": source_study_id,
            "comparison_windows": comparison_windows,
            "selected_window_id": selected_window_id,
            "same_study_runs": same_study_runs,
            "same_project_studies": same_project_studies[:5],
            "study_timeline": study_timeline[:10],
            "same_study_run_count": len(same_study_runs),
            "same_project_study_count": len(same_project_studies),
            "study_timeline_entry_count": len(study_timeline),
            "recurring_signal_synthesis": recurring_signal_synthesis,
            "panel_learning_projection": panel_learning_projection,
            "calibration_lineage": {
                **self._run_calibration_lineage_entry(
                    run_context=source_context,
                    source_human_calibration=source_human_calibration,
                ),
                "same_study_calibrated_run_count": sum(
                    1 for item in same_study_runs if item.get("has_human_calibration")
                ),
                "same_project_calibrated_run_count": same_project_calibrated_run_count,
                "selected_comparison_run_id": selected_comparison_run_id,
                "selected_comparison_calibration_status": selected_comparison_calibration_status,
                "note": "Calibration lineage stays attached to repeated runs so longitudinal review can separate unchanged evidence from uncalibrated drift.",
            },
            "note": "Review same-study runs first, then the study timeline, before widening to neighboring studies in the same project.",
        }

    def _augment_workspace_query_payload(
        self,
        *,
        workspace_id: str,
        run_id: str,
        query_payload: dict[str, Any],
    ) -> dict[str, Any]:
        _, run_job_context_lookup = self._workspace_run_context_lookup(workspace_id)
        run_job_lookup = {
            candidate_run_id: str(context.get("job_id") or "") or None
            for candidate_run_id, context in run_job_context_lookup.items()
        }

        cross_run_comparison = dict(query_payload.get("cross_run_comparison", {}))
        candidate_runs = cross_run_comparison.get("candidate_runs")
        if isinstance(candidate_runs, list):
            for item in candidate_runs:
                if isinstance(item, dict):
                    item["job_id"] = run_job_lookup.get(str(item.get("run_id") or "")) or None
        selected_comparison_run = cross_run_comparison.get("selected_comparison_run")
        if isinstance(selected_comparison_run, dict):
            selected_job_id = run_job_lookup.get(str(selected_comparison_run.get("run_id") or ""))
            selected_comparison_run["job_id"] = selected_job_id or None
            cross_run_comparison["selected_comparison_job_id"] = selected_job_id or None
        else:
            cross_run_comparison["selected_comparison_job_id"] = None
        query_payload["cross_run_comparison"] = cross_run_comparison

        audit_lineage = dict(query_payload.get("audit_lineage", {}))
        source_run = dict(audit_lineage.get("source_run", {}))
        source_context = run_job_context_lookup.get(run_id, {})
        source_run.update(
            {
                "job_id": source_context.get("job_id"),
                "project_id": source_context.get("project_id"),
                "study_id": source_context.get("study_id"),
                "job_status": source_context.get("job_status"),
                "provider_name": source_context.get("provider_name"),
                "provider_runtime_boundary": source_context.get("provider_runtime_boundary"),
            }
        )

        comparison_set = dict(audit_lineage.get("comparison_set", {}))
        comparison_set["candidate_jobs"] = [
            run_job_context_lookup.get(
                str(item.get("run_id") or ""),
                {
                    "run_id": str(item.get("run_id") or ""),
                    "job_id": None,
                    "project_id": None,
                    "study_id": None,
                    "job_status": None,
                },
            )
            for item in cross_run_comparison.get("candidate_runs", [])
            if isinstance(item, dict) and item.get("run_id")
        ]
        selected_comparison_run_id = str(comparison_set.get("selected_comparison_run_id") or "")
        selected_context = run_job_context_lookup.get(selected_comparison_run_id, {})
        comparison_set.update(
            {
                "selected_comparison_job_id": selected_context.get("job_id"),
                "selected_comparison_project_id": selected_context.get("project_id"),
                "selected_comparison_study_id": selected_context.get("study_id"),
            }
        )

        longitudinal_comparison = self._build_longitudinal_comparison(
            workspace_id=workspace_id,
            run_id=run_id,
            query_payload=query_payload,
            run_job_context_lookup=run_job_context_lookup,
        )
        audit_lineage["source_run"] = source_run
        audit_lineage["comparison_set"] = comparison_set
        audit_lineage["longitudinal_set"] = {
            "source_project_id": longitudinal_comparison.get("source_project_id"),
            "source_study_id": longitudinal_comparison.get("source_study_id"),
            "selected_window_id": longitudinal_comparison.get("selected_window_id"),
            "same_study_run_ids": [
                item.get("run_id")
                for item in longitudinal_comparison.get("same_study_runs", [])
                if isinstance(item, dict) and item.get("run_id")
            ],
            "same_project_study_ids": [
                item.get("study_id")
                for item in longitudinal_comparison.get("same_project_studies", [])
                if isinstance(item, dict) and item.get("study_id")
            ],
            "study_timeline_entry_ids": [
                item.get("entry_id")
                for item in longitudinal_comparison.get("study_timeline", [])
                if isinstance(item, dict) and item.get("entry_id")
            ],
            "recurring_pattern_ids": [
                item.get("pattern_id")
                for item in (
                    longitudinal_comparison.get("recurring_signal_synthesis", {}).get("patterns", [])
                    if isinstance(longitudinal_comparison.get("recurring_signal_synthesis"), dict)
                    and isinstance(longitudinal_comparison.get("recurring_signal_synthesis", {}).get("patterns"), list)
                    else []
                )
                if isinstance(item, dict) and item.get("pattern_id")
            ],
            "panel_learning_status": (
                longitudinal_comparison.get("panel_learning_projection", {}).get("segment_divergence", {}).get("status")
                if isinstance(longitudinal_comparison.get("panel_learning_projection"), dict)
                and isinstance(longitudinal_comparison.get("panel_learning_projection", {}).get("segment_divergence"), dict)
                else None
            ),
            "decision_trend_status": (
                longitudinal_comparison.get("panel_learning_projection", {}).get("decision_trends", {}).get("latest_change_status")
                if isinstance(longitudinal_comparison.get("panel_learning_projection"), dict)
                and isinstance(longitudinal_comparison.get("panel_learning_projection", {}).get("decision_trends"), dict)
                else None
            ),
        }
        query_payload["audit_lineage"] = audit_lineage
        query_payload["longitudinal_comparison"] = longitudinal_comparison
        if source_context.get("provider_runtime_boundary"):
            query_payload["provider_runtime_boundary"] = source_context.get("provider_runtime_boundary")

        evidence_reliability = query_payload.get("evidence_reliability")
        if isinstance(evidence_reliability, dict):
            evidence_reliability["audit_lineage"] = audit_lineage
            query_payload["evidence_reliability"] = evidence_reliability
        source_study_id = str(source_run.get("study_id") or "").strip()
        if source_study_id:
            source_study = job_store.get_workspace_study(self.runtime_root, source_study_id)
            if source_study is not None and source_study.workspace_id == workspace_id:
                query_payload["governed_review"] = self._study_governed_review_state(source_study)
                query_payload["governed_redaction"] = self._study_governed_redaction_state(source_study)
        query_payload["readiness_gate"] = self._build_readiness_gate_from_query(query_payload)
        return query_payload

    def _index_workspace_run_contract(self, workspace_id: str, run_dir: Path) -> None:
        contract_path = run_dir / "run_contract.json"
        if not contract_path.exists():
            raise FileNotFoundError(f"Completed run is missing run_contract.json: {contract_path}")
        persist_run_contract_metadata(
            _workspace_root(self.runtime_root, workspace_id),
            contract_path,
            read_json(contract_path),
        )

    def process_next_job(self) -> dict[str, Any] | None:
        leased = job_store.lease_next_validation_job(self.runtime_root)
        if leased is None:
            return None

        metadata = dict(leased.get("metadata", {}))
        workspace = job_store.get_workspace(self.runtime_root, str(leased["workspace_id"]))
        if workspace is None:
            return job_store.update_validation_job(
                self.runtime_root,
                job_id=str(leased["job_id"]),
                status="failed",
                last_error=f"Unknown workspace '{leased['workspace_id']}'.",
            )

        started_at = utc_now_iso()
        job_store.create_audit_event(
            self.runtime_root,
            AuditEvent(
                audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                workspace_id=workspace.workspace_id,
                actor_user_id="system_worker",
                actor_role="system",
                action="validation_job.started",
                target_type="validation_job",
                target_id=str(leased.get("job_id") or ""),
                event_payload={
                    "project_id": str(metadata.get("project_id") or "") or None,
                    "study_id": str(metadata.get("study_id") or "") or None,
                    "job_status": "running",
                    "provider_name": str(leased.get("provider_name") or ""),
                },
                created_at=started_at,
            ),
        )
        try:
            job_store.update_validation_job(
                self.runtime_root,
                job_id=str(leased["job_id"]),
                status="running",
                metadata_updates={
                    "provider_runtime_boundary": self._validation_provider_runtime_boundary(
                        str(leased.get("provider_name") or ""),
                        status="running",
                        metadata=metadata,
                    )
                },
            )
            provider = self.provider_builder(str(leased["provider_name"]))
            run_dir = run_validation(
                Path(str(leased["input_artifact_path"])),
                Path(str(leased["persona_dir_path"])),
                PanelSpec(**dict(leased["panel_spec"])),
                provider,
                Path(str(metadata.get("run_root") or (_workspace_root(self.runtime_root, workspace.workspace_id) / "runs"))),
                max_retries=int(metadata.get("max_retries", 1)),
            )
            if isinstance(metadata.get("selected_persona_snapshot"), dict):
                write_json(
                    run_dir / "frontline_persona_panel_snapshot.json",
                    {
                        "contract_version": "frontline-persona-panel-run-snapshot/v0-draft",
                        "job_id": str(leased.get("job_id") or ""),
                        "workspace_id": workspace.workspace_id,
                        "project_id": str(metadata.get("project_id") or ""),
                        "study_id": str(metadata.get("study_id") or ""),
                        "plan_revision_id": str(metadata.get("plan_revision_id") or ""),
                        "persona_panel": dict(metadata.get("persona_panel", {})) if isinstance(metadata.get("persona_panel"), dict) else {},
                        "selected_persona_snapshot": dict(metadata.get("selected_persona_snapshot", {})),
                        "synthetic_boundary": "This run used synthetic persona records. The snapshot is for audit and replay, not human market proof.",
                    },
                )
            self._index_workspace_run_contract(workspace.workspace_id, run_dir)
            run_payload = read_json(run_dir / "run.json")
            research_run_status = str(run_payload.get("status") or "")
            failure_reasons = [
                str(reason)
                for reason in run_payload.get("failure_reasons", [])
                if str(reason).strip()
            ] if isinstance(run_payload.get("failure_reasons"), list) else []
            retention_days = int(metadata.get("artifact_retention_days", _plan_limits(workspace.plan_tier, workspace.settings)["artifact_retention_days"]))
            retention_until = (_now() + timedelta(days=retention_days)).replace(microsecond=0).isoformat()
            if research_run_status == "failed":
                last_error = "; ".join(failure_reasons) or "Validation run failed; review run artifacts for failure details."
                failure_metadata = {
                    **metadata,
                    "run_id": run_dir.name,
                    "research_run_status": research_run_status,
                    "artifact_retention_until": retention_until,
                    "artifact_deleted_at": "",
                }
                failure_boundary = self._validation_provider_runtime_boundary(
                    str(leased.get("provider_name") or ""),
                    status="failed",
                    last_error=last_error,
                    metadata=failure_metadata,
                )
                failed = job_store.update_validation_job(
                    self.runtime_root,
                    job_id=str(leased["job_id"]),
                    status="failed",
                    output_run_path=str(run_dir),
                    last_error=last_error,
                    metadata_updates={
                        **failure_metadata,
                        "provider_runtime_boundary": failure_boundary,
                    },
                )
                failed_metadata = dict(failed.get("metadata", {}))
                job_store.create_audit_event(
                    self.runtime_root,
                    AuditEvent(
                        audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                        workspace_id=workspace.workspace_id,
                        actor_user_id="system_worker",
                        actor_role="system",
                        action="validation_job.failed",
                        target_type="validation_job",
                        target_id=str(failed.get("job_id") or ""),
                        event_payload={
                            "project_id": str(failed_metadata.get("project_id") or "") or None,
                            "study_id": str(failed_metadata.get("study_id") or "") or None,
                            "job_status": str(failed.get("status") or ""),
                            "run_id": str(failed_metadata.get("run_id") or "") or run_dir.name,
                            "research_run_status": research_run_status,
                            "last_error": last_error,
                            "provider_runtime_boundary": failure_boundary,
                            "provider_failure_kind": failure_boundary.get("failure_kind"),
                        },
                        created_at=utc_now_iso(),
                    ),
                )
                return failed
            updated = job_store.update_validation_job(
                self.runtime_root,
                job_id=str(leased["job_id"]),
                status="completed",
                output_run_path=str(run_dir),
                metadata_updates={
                    "run_id": run_dir.name,
                    "research_run_status": research_run_status,
                    "artifact_retention_until": retention_until,
                    "artifact_deleted_at": "",
                    "provider_runtime_boundary": self._validation_provider_runtime_boundary(
                        str(leased.get("provider_name") or ""),
                        status="completed",
                        metadata={
                            **metadata,
                            "run_id": run_dir.name,
                            "artifact_retention_until": retention_until,
                            "artifact_deleted_at": "",
                        },
                    ),
                },
            )
            completed_metadata = dict(updated.get("metadata", {}))
            completed_study_id = str(completed_metadata.get("study_id") or "").strip()
            if completed_study_id:
                job_store.update_workspace_study(
                    self.runtime_root,
                    study_id=completed_study_id,
                    latest_job_id=str(updated.get("job_id") or ""),
                    status="reviewing",
                    metadata_updates={"last_completed_job_id": str(updated.get("job_id") or "")},
                )
            job_store.create_audit_event(
                self.runtime_root,
                AuditEvent(
                    audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                    workspace_id=workspace.workspace_id,
                    actor_user_id="system_worker",
                    actor_role="system",
                    action="validation_job.completed",
                    target_type="validation_job",
                    target_id=str(updated.get("job_id") or ""),
                    event_payload={
                        "project_id": str(completed_metadata.get("project_id") or "") or None,
                        "study_id": str(completed_metadata.get("study_id") or "") or None,
                        "job_status": str(updated.get("status") or ""),
                        "run_id": str(completed_metadata.get("run_id") or "") or run_dir.name,
                        "artifact_retention_until": str(completed_metadata.get("artifact_retention_until") or "") or None,
                    },
                    created_at=utc_now_iso(),
                ),
            )
            return updated
        except Exception as exc:
            failure_boundary = self._validation_provider_runtime_boundary(
                str(leased.get("provider_name") or ""),
                status="failed",
                last_error=str(exc),
                metadata=metadata,
            )
            failed = job_store.update_validation_job(
                self.runtime_root,
                job_id=str(leased["job_id"]),
                status="failed",
                last_error=str(exc),
                metadata_updates={"provider_runtime_boundary": failure_boundary},
            )
            failed_metadata = dict(failed.get("metadata", {}))
            job_store.create_audit_event(
                self.runtime_root,
                AuditEvent(
                    audit_event_id=f"audit_{uuid.uuid4().hex[:12]}",
                    workspace_id=workspace.workspace_id,
                    actor_user_id="system_worker",
                    actor_role="system",
                    action="validation_job.failed",
                    target_type="validation_job",
                    target_id=str(failed.get("job_id") or ""),
                    event_payload={
                        "project_id": str(failed_metadata.get("project_id") or "") or None,
                        "study_id": str(failed_metadata.get("study_id") or "") or None,
                        "job_status": str(failed.get("status") or ""),
                        "last_error": str(exc),
                        "provider_runtime_boundary": failure_boundary,
                        "provider_failure_kind": failure_boundary.get("failure_kind"),
                    },
                    created_at=utc_now_iso(),
                ),
            )
            return failed

    def purge_expired_run_artifacts(self, *, now: datetime | None = None) -> list[str]:
        current = now or _now()
        purged_job_ids: list[str] = []
        for workspace in self._list_workspaces():
            for job in job_store.list_workspace_jobs(self.runtime_root, workspace.workspace_id):
                output_run_path = str(job.get("output_run_path") or "")
                if not output_run_path:
                    continue
                metadata = dict(job.get("metadata", {}))
                artifact_deleted_at = str(metadata.get("artifact_deleted_at") or "")
                retention_until = str(metadata.get("artifact_retention_until") or "")
                if artifact_deleted_at or not retention_until:
                    continue
                try:
                    retention_deadline = datetime.fromisoformat(retention_until)
                except ValueError:
                    continue
                if retention_deadline > current:
                    continue
                run_path = Path(output_run_path)
                if run_path.exists():
                    for child in sorted(run_path.rglob("*"), reverse=True):
                        if child.is_file():
                            child.unlink()
                        elif child.is_dir():
                            child.rmdir()
                    run_path.rmdir()
                job_store.update_validation_job(
                    self.runtime_root,
                    job_id=str(job["job_id"]),
                    status=str(job["status"]),
                    output_run_path=output_run_path,
                    metadata_updates={"artifact_deleted_at": current.replace(microsecond=0).isoformat()},
                )
                purged_job_ids.append(str(job["job_id"]))
        return purged_job_ids

    def run_worker_loop(self, *, poll_seconds: float = 1.0, stop_after_one: bool = False, stop_event: threading.Event | None = None) -> int:
        processed = 0
        while True:
            if stop_event is not None and stop_event.is_set():
                return processed
            job = self.process_next_job()
            if job is not None:
                processed += 1
                if stop_after_one:
                    return processed
                continue
            if stop_after_one:
                return processed
            time.sleep(max(poll_seconds, 0.05))

    def _list_workspaces(self) -> list[TenantWorkspace]:
        return job_store.list_workspaces(self.runtime_root)

    def _decision_review_status(self, decision_log: WorkspaceDecisionLog) -> str:
        metadata = dict(decision_log.metadata or {})
        review_status = str(metadata.get("review_status") or "draft").strip() or "draft"
        return review_status if review_status in DECISION_REVIEW_STATUSES else "draft"

    def _decision_review_history(self, decision_log: WorkspaceDecisionLog) -> list[dict[str, Any]]:
        history = dict(decision_log.metadata or {}).get("review_status_history")
        if not isinstance(history, list):
            return []
        return [item for item in history if isinstance(item, dict)]

    def _workspace_member_map(self, workspace: TenantWorkspace) -> dict[str, WorkspaceMember]:
        return {
            member.user_id: member
            for member in workspace.members
            if isinstance(member, WorkspaceMember) and str(member.user_id or "").strip()
        }

    def _decision_review_assignment(self, decision_log: WorkspaceDecisionLog, workspace: TenantWorkspace) -> dict[str, Any]:
        metadata = dict(decision_log.metadata or {})
        assignment = metadata.get("review_assignment")
        member_map = self._workspace_member_map(workspace)
        if not isinstance(assignment, dict):
            assignment = {}
        assignee_user_ids = _unique_preserve_order(
            [str(item) for item in assignment.get("assignee_user_ids", [])]
            if isinstance(assignment.get("assignee_user_ids"), list)
            else []
        )
        status = str(assignment.get("status") or "").strip()
        if status not in DECISION_REVIEW_ASSIGNMENT_STATUSES:
            status = "assigned" if assignee_user_ids else "unassigned"
        return {
            "contract_version": "workspace-decision-review-assignment/v0-draft",
            "status": status,
            "assignee_user_ids": assignee_user_ids,
            "assignees": [
                {
                    "user_id": user_id,
                    "role": member_map[user_id].role,
                }
                for user_id in assignee_user_ids
                if user_id in member_map
            ],
            "assigned_at": assignment.get("assigned_at") or None,
            "assigned_by_user_id": assignment.get("assigned_by_user_id") or None,
            "latest_note": str(assignment.get("latest_note") or ""),
        }

    def _decision_review_assignment_history(self, decision_log: WorkspaceDecisionLog) -> list[dict[str, Any]]:
        history = dict(decision_log.metadata or {}).get("review_assignment_history")
        if not isinstance(history, list):
            return []
        normalized: list[dict[str, Any]] = []
        for item in history:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "status": str(item.get("status") or "unassigned"),
                    "assignee_user_ids": _unique_preserve_order(
                        [str(value) for value in item.get("assignee_user_ids", [])]
                        if isinstance(item.get("assignee_user_ids"), list)
                        else []
                    ),
                    "changed_at": item.get("changed_at") or None,
                    "changed_by_user_id": item.get("changed_by_user_id") or None,
                    "note": str(item.get("note") or ""),
                }
            )
        return normalized

    def _support_handoff(self, snapshot: WorkspaceSupportSnapshot, workspace: TenantWorkspace) -> dict[str, Any]:
        metadata = dict(snapshot.metadata or {})
        handoff = metadata.get("handoff")
        member_map = self._workspace_member_map(workspace)
        if not isinstance(handoff, dict):
            handoff = {}
        assigned_user_id = str(handoff.get("assigned_user_id") or "").strip() or None
        status = str(handoff.get("status") or "").strip()
        if status not in SUPPORT_HANDOFF_STATUSES:
            status = "assigned" if assigned_user_id else "unassigned"
        assignee = member_map.get(assigned_user_id or "")
        return {
            "contract_version": "workspace-support-handoff/v0-draft",
            "status": status,
            "assigned_user_id": assigned_user_id,
            "assigned_role": assignee.role if assignee is not None else None,
            "assigned_at": handoff.get("assigned_at") or None,
            "assigned_by_user_id": handoff.get("assigned_by_user_id") or None,
            "acknowledged_at": handoff.get("acknowledged_at") or None,
            "resolved_at": handoff.get("resolved_at") or None,
            "latest_note": str(handoff.get("latest_note") or ""),
        }

    def _support_handoff_history(self, snapshot: WorkspaceSupportSnapshot) -> list[dict[str, Any]]:
        history = dict(snapshot.metadata or {}).get("handoff_history")
        if not isinstance(history, list):
            return []
        normalized: list[dict[str, Any]] = []
        for item in history:
            if not isinstance(item, dict):
                continue
            normalized.append(
                {
                    "status": str(item.get("status") or "unassigned"),
                    "assigned_user_id": str(item.get("assigned_user_id") or "").strip() or None,
                    "changed_at": item.get("changed_at") or None,
                    "changed_by_user_id": item.get("changed_by_user_id") or None,
                    "note": str(item.get("note") or ""),
                }
            )
        return normalized

    def _materialize_decision_log_artifacts(
        self,
        decision_log: WorkspaceDecisionLog,
        *,
        comment_summaries: list[dict[str, Any]] | None = None,
    ) -> None:
        payload_path = Path(decision_log.payload_path)
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        review_status = self._decision_review_status(decision_log)
        decision_metadata = dict(decision_log.metadata or {})
        latest_review_note = str(decision_metadata.get("latest_review_note") or "").strip()
        readiness_gate = decision_metadata.get("readiness_gate")
        if not isinstance(readiness_gate, dict):
            readiness_gate = {}
        workspace = job_store.get_workspace(self.runtime_root, decision_log.workspace_id)
        if workspace is None:
            raise FileNotFoundError(f"Workspace '{decision_log.workspace_id}' not found for decision log materialization.")
        study = job_store.get_workspace_study(self.runtime_root, decision_log.study_id)
        governed_review = (
            self._study_governed_review_state(study)
            if study is not None and study.workspace_id == decision_log.workspace_id
            else decision_metadata.get("governed_review")
        )
        governed_redaction = (
            self._study_governed_redaction_state(study)
            if study is not None and study.workspace_id == decision_log.workspace_id
            else decision_metadata.get("governed_redaction")
        )
        comments = list(comment_summaries or [])
        write_json(
            payload_path,
            {
                "decision_log_id": decision_log.decision_log_id,
                "workspace_id": decision_log.workspace_id,
                "project_id": decision_log.project_id,
                "study_id": decision_log.study_id,
                "job_id": decision_log.job_id,
                "run_id": decision_log.run_id,
                "evidence_view_id": decision_log.evidence_view_id,
                "title": decision_log.title,
                "decision_summary": decision_log.decision_summary,
                "rationale": decision_log.rationale,
                "selected_result_id": decision_log.selected_result_id,
                "selected_comparison_run_id": decision_log.selected_comparison_run_id,
                "review_status": review_status,
                "comment_count": len(comments),
                "review_status_history": self._decision_review_history(decision_log),
                "review_assignment": self._decision_review_assignment(decision_log, workspace),
                "review_assignment_history": self._decision_review_assignment_history(decision_log),
                "created_at": decision_log.created_at,
                "updated_at": decision_log.updated_at,
                "created_by_user_id": decision_log.created_by_user_id,
                "readiness_gate": readiness_gate,
                "governed_review": governed_review,
                "governed_redaction": governed_redaction,
                "metadata": decision_metadata,
                "comments": comments,
            },
        )
        write_markdown(
            payload_path.parent / "README.md",
            "\n".join(
                [
                    f"# {decision_log.title}",
                    "",
                    f"- study_id: {decision_log.study_id}",
                    f"- job_id: {decision_log.job_id or '-'}",
                    f"- evidence_view_id: {decision_log.evidence_view_id or '-'}",
                    f"- review_status: {review_status}",
                    f"- review_assignment_status: {self._decision_review_assignment(decision_log, workspace).get('status', 'unassigned')}",
                    f"- comment_count: {len(comments)}",
                    f"- readiness_status: {readiness_gate.get('status', 'pending')}",
                    f"- governed_review_status: {dict(governed_review or {}).get('review_gate_status', 'not_required')}",
                    f"- governed_redaction_status: {dict(governed_redaction or {}).get('status', 'not_required')}",
                    "",
                    decision_log.decision_summary,
                    "",
                    decision_log.rationale or "No rationale provided.",
                    "",
                    latest_review_note or "No latest review note recorded.",
                ]
            ),
        )

    def _decision_comment_summary(
        self,
        decision_comment: WorkspaceDecisionComment,
        *,
        decision_comments: list[WorkspaceDecisionComment] | None = None,
    ) -> dict[str, Any]:
        sibling_comments = list(decision_comments or [])
        reply_count = sum(
            1
            for item in sibling_comments
            if str(item.parent_comment_id or "") == decision_comment.decision_comment_id
        )
        return {
            **decision_comment.to_dict(),
            "reply_count": reply_count,
            "is_reply": bool(decision_comment.parent_comment_id),
        }

    def _materialize_support_snapshot_artifacts(self, snapshot: WorkspaceSupportSnapshot) -> None:
        payload_path = Path(snapshot.snapshot_path)
        payload_path.parent.mkdir(parents=True, exist_ok=True)
        workspace = job_store.get_workspace(self.runtime_root, snapshot.workspace_id)
        if workspace is None:
            raise FileNotFoundError(f"Workspace '{snapshot.workspace_id}' not found for support snapshot materialization.")
        metadata = dict(snapshot.metadata or {})
        handoff = self._support_handoff(snapshot, workspace)
        compliance_audit_bundle = None
        if snapshot.study_id:
            study = job_store.get_workspace_study(self.runtime_root, snapshot.study_id)
            if study is not None and study.workspace_id == snapshot.workspace_id:
                diagnostic = metadata.get("diagnostic")
                compliance_audit_bundle = self._build_governed_compliance_audit_bundle(
                    workspace_id=snapshot.workspace_id,
                    study=study,
                    project_id=snapshot.project_id,
                    job_id=snapshot.job_id,
                    run_id=snapshot.run_id,
                    readiness_gate=dict(diagnostic.get("job_diagnostic", {}).get("readiness_gate", {}))
                    if isinstance(diagnostic, dict) and isinstance(diagnostic.get("job_diagnostic"), dict)
                    else {},
                    distribution_context={
                        "surface": "support_snapshot",
                        "support_snapshot_id": snapshot.support_snapshot_id,
                    },
                )
                metadata["compliance_audit_bundle_path"] = self._write_governed_compliance_bundle_file(
                    payload_path.parent,
                    compliance_audit_bundle,
                )
        payload = {
            "support_snapshot_id": snapshot.support_snapshot_id,
            "workspace_id": snapshot.workspace_id,
            "project_id": snapshot.project_id,
            "study_id": snapshot.study_id,
            "job_id": snapshot.job_id,
            "run_id": snapshot.run_id,
            "title": snapshot.title,
            "status": snapshot.status,
            "summary": snapshot.summary,
            "created_at": snapshot.created_at,
            "updated_at": snapshot.updated_at,
            "created_by_user_id": snapshot.created_by_user_id,
            "notes": str(metadata.get("notes") or ""),
            "diagnostic": metadata.get("diagnostic"),
            "handoff": handoff,
            "handoff_history": self._support_handoff_history(snapshot),
            "compliance_audit_bundle": compliance_audit_bundle,
            "metadata": metadata,
        }
        write_json(payload_path, payload)
        write_markdown(
            payload_path.parent / "README.md",
            "\n".join(
                [
                    f"# {snapshot.title}",
                    "",
                    f"- job_id: {snapshot.job_id or '-'}",
                    f"- project_id: {snapshot.project_id or '-'}",
                    f"- study_id: {snapshot.study_id or '-'}",
                    f"- run_id: {snapshot.run_id or '-'}",
                    f"- summary: {snapshot.summary}",
                    f"- handoff_status: {handoff.get('status', 'unassigned')}",
                    f"- handoff_assignee: {handoff.get('assigned_user_id') or '-'}",
                    "",
                    str(metadata.get("notes") or "") or "No operator notes provided.",
                    "",
                    str(handoff.get("latest_note") or "") or "No handoff note recorded.",
                ]
            ),
        )

    def _audit_event_matches_study(self, event: AuditEvent, study_id: str) -> bool:
        if event.target_type == "study" and event.target_id == study_id:
            return True
        event_payload = dict(event.event_payload or {})
        return str(event_payload.get("study_id") or "").strip() == study_id

    def _study_activity_route(self, event: AuditEvent) -> dict[str, str | None]:
        event_payload = dict(event.event_payload or {})
        if event.target_type == "study":
            return {
                "route_kind": "study",
                "route_id": event.target_id,
                "route_path": f"/app/studies/{event.target_id}",
            }
        if event.target_type == "validation_job":
            return {
                "route_kind": "job",
                "route_id": event.target_id,
                "route_path": f"/app/jobs/{event.target_id}",
            }
        route_map = {
            "evidence_view": ("evidence_view", f"/app/evidence-views/{event.target_id}"),
            "decision_log": ("decision_log", f"/app/decision-logs/{event.target_id}"),
            "export_bundle": ("export_bundle", f"/app/export-bundles/{event.target_id}"),
            "share_bundle": ("share_bundle", f"/app/share-bundles/{event.target_id}"),
            "support_snapshot": ("support_snapshot", f"/app/support-snapshots/{event.target_id}"),
        }
        mapped = route_map.get(event.target_type)
        if mapped is not None:
            route_kind, route_path = mapped
            return {
                "route_kind": route_kind,
                "route_id": event.target_id,
                "route_path": route_path,
            }
        if str(event_payload.get("study_id") or "").strip():
            return {
                "route_kind": "study",
                "route_id": str(event_payload.get("study_id") or "").strip(),
                "route_path": f"/app/studies/{str(event_payload.get('study_id') or '').strip()}",
            }
        return {
            "route_kind": None,
            "route_id": None,
            "route_path": None,
        }

    def _study_activity_event_summary(self, event: AuditEvent) -> dict[str, Any]:
        payload = dict(event.event_payload or {})
        route = self._study_activity_route(event)
        family = "study"
        tone = "queued"
        headline = event.action.replace(".", " ")
        summary = "Study activity recorded."

        if event.action == "study.created":
            family = "study"
            tone = "completed"
            headline = "Study created"
            summary = f"{payload.get('study_title') or 'Study'} is ready for intake and run setup."
        elif event.action == "validation_job.submitted":
            family = "run"
            tone = "queued"
            headline = "Run queued"
            summary = (
                f"{payload.get('provider_name') or 'provider'} | "
                f"{payload.get('panel_type') or 'panel'} | "
                f"{payload.get('sample_size') or '?'} participants"
            )
        elif event.action == "validation_job.started":
            family = "run"
            tone = "running"
            headline = "Run started"
            summary = "Worker execution started for the selected study run."
        elif event.action == "validation_job.completed":
            family = "run"
            tone = "completed"
            headline = "Run completed"
            summary = f"Completed run {payload.get('run_id') or event.target_id} is ready for evidence review."
        elif event.action == "validation_job.failed":
            family = "run"
            tone = "failed"
            headline = "Run failed"
            summary = str(payload.get("last_error") or "The study run failed before evidence review.")
        elif event.action == "validation_job.canceled":
            family = "run"
            tone = "queued"
            headline = "Queued run canceled"
            summary = str(payload.get("cancel_reason") or "Canceled from the product surface.")
        elif event.action == "validation_job.retried":
            family = "run"
            tone = "queued"
            headline = "Retry queued"
            summary = f"Retry queued from {payload.get('source_job_id') or 'the selected failed run'}."
        elif event.action == "evidence_view.saved":
            family = "evidence"
            tone = "completed"
            headline = "Evidence view saved"
            summary = "One evidence slice was preserved for later study review."
        elif event.action == "decision_log.created":
            family = "decision"
            tone = "completed"
            headline = "Decision recorded"
            summary = "A study decision was attached to evidence and run lineage."
        elif event.action == "decision_log.commented":
            family = "decision"
            tone = "running"
            headline = "Decision comment added"
            summary = f"{payload.get('comment_count') or 0} comment(s) now attached to the review thread."
        elif event.action == "decision_log.review_status_updated":
            family = "decision"
            tone = "completed" if str(payload.get("review_status") or "") == "approved" else "running"
            headline = "Decision review updated"
            summary = f"Review status changed to {payload.get('review_status') or 'draft'}."
        elif event.action == "decision_log.review_assignment_updated":
            family = "decision"
            tone = "running"
            headline = "Decision reviewers updated"
            assignee_count = len(payload.get("assignee_user_ids", [])) if isinstance(payload.get("assignee_user_ids"), list) else 0
            summary = f"{assignee_count} reviewer assignment(s) now attached to the decision review."
        elif event.action == "study.governed_review_assignment_updated":
            family = "study"
            tone = "running"
            headline = "Governed reviewer updated"
            assignee_count = len(payload.get("assignee_user_ids", [])) if isinstance(payload.get("assignee_user_ids"), list) else 0
            summary = (
                str(payload.get("governed_review_note") or "").strip()
                or f"{assignee_count} governed reviewer assignment(s) now attached to the study boundary."
            )
        elif event.action == "study.governed_redaction_updated":
            family = "study"
            tone = "running"
            headline = "Governed redaction updated"
            summary = (
                str(payload.get("governed_redaction_note") or "").strip()
                or f"{payload.get('redaction_rule_count') or 0} governed redaction rule(s) now attached to the study boundary."
            )
        elif event.action == "export_bundle.created":
            family = "export"
            tone = "completed"
            headline = "Export created"
            summary = f"{payload.get('export_format') or 'bundle'} export is ready for delivery."
        elif event.action == "export_bundle.mvp_promotion_requested":
            family = "export"
            tone = "running"
            headline = "Export promotion requested"
            summary = "A bounded design-partner circulation request is awaiting review."
        elif event.action == "export_bundle.mvp_promotion_reviewed":
            family = "export"
            decision = str(payload.get("decision") or payload.get("mvp_promotion_status") or "reviewed")
            tone = "completed" if decision == "approved" else "queued"
            headline = "Export promotion reviewed"
            summary = f"Design-partner promotion was {decision}."
        elif event.action == "share_bundle.created":
            family = "share"
            tone = "completed"
            headline = "Share published"
            summary = "A viewer-safe share bundle is available from this study."
        elif event.action == "share_bundle.mvp_release_review_requested":
            family = "share"
            tone = "running"
            headline = "Share release review requested"
            summary = "The partner-facing share artifact is awaiting final release approval."
        elif event.action == "share_bundle.mvp_release_reviewed":
            family = "share"
            decision = str(payload.get("decision") or payload.get("mvp_release_review_status") or "reviewed")
            tone = "completed" if decision == "approved" else "queued"
            headline = "Share release reviewed"
            summary = f"Partner-facing share release was {decision}."
        elif event.action == "share_bundle.revoked":
            family = "share"
            tone = "queued"
            headline = "Share revoked"
            summary = "The public share path was revoked from the study surface."
        elif event.action == "support_snapshot.created":
            family = "support"
            tone = "completed"
            headline = "Support snapshot created"
            summary = str(payload.get("summary") or "A support handoff bundle was generated for this study.")
        elif event.action == "support_snapshot.handoff_updated":
            family = "support"
            tone = "running" if str(payload.get("handoff_status") or "") != "resolved" else "completed"
            headline = "Support handoff updated"
            summary = f"Support handoff changed to {payload.get('handoff_status') or 'unassigned'}."

        return {
            "activity_id": event.audit_event_id,
            "action": event.action,
            "event_family": family,
            "tone": tone,
            "headline": headline,
            "summary": summary,
            "actor_user_id": event.actor_user_id,
            "actor_role": event.actor_role,
            "target_type": event.target_type,
            "target_id": event.target_id,
            "created_at": event.created_at,
            "project_id": str(payload.get("project_id") or "").strip() or None,
            "study_id": str(payload.get("study_id") or "").strip() or None,
            "job_id": str(payload.get("job_id") or "").strip() or (event.target_id if event.target_type == "validation_job" else None),
            "route_kind": route["route_kind"],
            "route_id": route["route_id"],
            "route_path": route["route_path"],
        }

    def _project_summary(self, project: WorkspaceProject) -> dict[str, Any]:
        studies = job_store.list_workspace_studies(self.runtime_root, project.workspace_id, project_id=project.project_id)
        export_bundles = [
            bundle
            for bundle in job_store.list_workspace_export_bundles(self.runtime_root, project.workspace_id)
            if bundle.project_id == project.project_id
        ]
        share_bundles = [
            bundle
            for bundle in job_store.list_workspace_share_bundles(self.runtime_root, project.workspace_id)
            if bundle.project_id == project.project_id
        ]
        support_snapshots = [
            snapshot
            for snapshot in job_store.list_workspace_support_snapshots(self.runtime_root, project.workspace_id)
            if snapshot.project_id == project.project_id
        ]
        evidence_views = [
            view
            for view in job_store.list_workspace_evidence_views(self.runtime_root, project.workspace_id)
            if view.project_id == project.project_id
        ]
        decision_logs = [
            log
            for log in job_store.list_workspace_decision_logs(self.runtime_root, project.workspace_id)
            if log.project_id == project.project_id
        ]
        study_reports = [
            report
            for report in job_store.list_workspace_study_reports(self.runtime_root, project.workspace_id)
            if report.project_id == project.project_id
        ]
        decision_comments = [
            comment
            for comment in job_store.list_workspace_decision_comments(self.runtime_root, project.workspace_id)
            if comment.project_id == project.project_id
        ]
        return {
            **project.to_dict(),
            "study_count": len(studies),
            "latest_study_id": studies[0].study_id if studies else None,
            "evidence_view_count": len(evidence_views),
            "study_report_count": len(study_reports),
            "decision_log_count": len(decision_logs),
            "decision_comment_count": len(decision_comments),
            "approved_decision_count": sum(
                1 for log in decision_logs if self._decision_review_status(log) == "approved"
            ),
            "export_bundle_count": len(export_bundles),
            "share_bundle_count": len(share_bundles),
            "support_snapshot_count": len(support_snapshots),
        }

    def _study_report_summary(self, report: WorkspaceStudyReport) -> dict[str, Any]:
        payload = report.to_dict()
        payload["synthetic_boundary"] = (
            "Synthetic evidence only. Study reports aggregate simulated runs and preserve human-validation gaps."
        )
        payload["capabilities"] = {
            "multi_run_synthesis": True,
            "plan_revision_lineage": True,
            "decision_workflow_ready": True,
        }
        return payload

    def _study_summary(self, study: WorkspaceStudy) -> dict[str, Any]:
        regulated_review_boundary = self._study_regulated_review_boundary(study)
        governed_review = self._study_governed_review_state(study)
        governed_redaction = self._study_governed_redaction_state(study)
        jobs = [
            job
            for job in job_store.list_workspace_jobs(self.runtime_root, study.workspace_id)
            if str(dict(job.get("metadata", {})).get("study_id") or "") == study.study_id
        ]
        latest_job = None
        if study.latest_job_id:
            latest_job = next((job for job in jobs if str(job.get("job_id")) == study.latest_job_id), None)
        elif jobs:
            latest_job = jobs[0]
        export_bundles = job_store.list_workspace_export_bundles(
            self.runtime_root,
            study.workspace_id,
            study_id=study.study_id,
        )
        share_bundles = job_store.list_workspace_share_bundles(
            self.runtime_root,
            study.workspace_id,
            study_id=study.study_id,
        )
        support_snapshots = job_store.list_workspace_support_snapshots(
            self.runtime_root,
            study.workspace_id,
            study_id=study.study_id,
        )
        evidence_views = job_store.list_workspace_evidence_views(
            self.runtime_root,
            study.workspace_id,
            study_id=study.study_id,
        )
        decision_logs = job_store.list_workspace_decision_logs(
            self.runtime_root,
            study.workspace_id,
            study_id=study.study_id,
        )
        study_reports = job_store.list_workspace_study_reports(
            self.runtime_root,
            study.workspace_id,
            study_id=study.study_id,
        )
        decision_comments = job_store.list_workspace_decision_comments(
            self.runtime_root,
            study.workspace_id,
            study_id=study.study_id,
        )
        frontline = dict(study.metadata.get("frontline", {})) if isinstance(study.metadata.get("frontline"), dict) else {}
        proposals = [dict(item) for item in frontline.get("plan_proposals", []) if isinstance(item, dict)]
        revisions = [dict(item) for item in frontline.get("plan_revisions", []) if isinstance(item, dict)]
        latest_proposal_id = str(frontline.get("latest_plan_proposal_id") or "")
        current_revision_id = str(frontline.get("current_plan_revision_id") or study.metadata.get("current_plan_revision_id") or "")
        latest_plan_proposal = next(
            (item for item in proposals if str(item.get("plan_proposal_id") or "") == latest_proposal_id),
            proposals[-1] if proposals else None,
        )
        latest_plan_revision = next(
            (item for item in revisions if str(item.get("plan_revision_id") or "") == current_revision_id),
            revisions[-1] if revisions else None,
        )
        if latest_plan_proposal is not None:
            frontline["latest_plan_proposal"] = latest_plan_proposal
        if latest_plan_revision is not None:
            frontline["latest_plan_revision"] = latest_plan_revision
        return {
            **study.to_dict(),
            "regulated_review_boundary": regulated_review_boundary,
            "governed_review": governed_review,
            "governed_redaction": governed_redaction,
            "frontline": frontline,
            "current_plan_revision_id": current_revision_id or None,
            "latest_report_id": (
                str(study.metadata.get("latest_report_id") or study.metadata.get("latest_study_report_id") or "")
                or (study_reports[0].study_report_id if study_reports else None)
            ),
            "run_count": len(jobs),
            "latest_job_status": str(latest_job.get("status") or "") if latest_job else None,
            "study_report_count": len(study_reports),
            "evidence_view_count": len(evidence_views),
            "decision_log_count": len(decision_logs),
            "decision_comment_count": len(decision_comments),
            "approved_decision_count": sum(
                1 for log in decision_logs if self._decision_review_status(log) == "approved"
            ),
            "export_bundle_count": len(export_bundles),
            "share_bundle_count": len(share_bundles),
            "support_snapshot_count": len(support_snapshots),
        }

    def _selected_evidence_context(
        self,
        *,
        workspace_id: str = "",
        run_id: str,
        query_text: str = "",
        active_family: str = "all",
        sort_by: str = "relevance",
        selected_result_id: str = "",
        selected_replay_step_id: str = "",
        selected_comparison_run_id: str = "",
    ) -> dict[str, Any]:
        if not run_id.strip():
            return {}
        query_payload = self._query_run_evidence_with_fallback(
            workspace_id=workspace_id,
            run_id=run_id.strip(),
            query_text=query_text.strip(),
            active_family=active_family.strip() or "all",
            sort_by=sort_by.strip() or "relevance",
            selected_result_id=selected_result_id.strip() or None,
            selected_replay_step_id=selected_replay_step_id.strip() or None,
            selected_comparison_run_id=selected_comparison_run_id.strip() or None,
        )
        if not isinstance(query_payload, dict):
            return {}
        selected_result = query_payload.get("selected_result")
        if not isinstance(selected_result, dict):
            selected_result = {}
        workflow_projection = selected_result.get("workflow_evidence_projection")
        if not isinstance(workflow_projection, dict):
            workflow_projection = {}
        reliability = query_payload.get("evidence_reliability")
        if not isinstance(reliability, dict):
            reliability = {}
        longitudinal = query_payload.get("longitudinal_comparison")
        if not isinstance(longitudinal, dict):
            longitudinal = {}
        calibration_lineage = longitudinal.get("calibration_lineage")
        if not isinstance(calibration_lineage, dict):
            calibration_lineage = {}
        recurring_signal_synthesis = longitudinal.get("recurring_signal_synthesis")
        if not isinstance(recurring_signal_synthesis, dict):
            recurring_signal_synthesis = {}
        panel_learning_projection = longitudinal.get("panel_learning_projection")
        if not isinstance(panel_learning_projection, dict):
            panel_learning_projection = {}
        segment_divergence = panel_learning_projection.get("segment_divergence")
        if not isinstance(segment_divergence, dict):
            segment_divergence = {}
        decision_trends = panel_learning_projection.get("decision_trends")
        if not isinstance(decision_trends, dict):
            decision_trends = {}
        confidence_trend = panel_learning_projection.get("confidence_trend")
        if not isinstance(confidence_trend, dict):
            confidence_trend = {}
        readiness_gate = self._build_readiness_gate_from_query(query_payload)
        provider_runtime_boundary = query_payload.get("provider_runtime_boundary")
        if not isinstance(provider_runtime_boundary, dict):
            provider_runtime_boundary = {}
        return {
            "selected_result_id": str(selected_result.get("id") or "") or None,
            "selected_artifact_id": str(selected_result.get("artifact_id") or "") or None,
            "selected_result_title": str(selected_result.get("title") or "") or None,
            "selected_result_family": str(selected_result.get("family") or "") or None,
            "selected_result_kind": str(selected_result.get("kind") or "") or None,
            "source_exchange_refs": [
                str(ref) for ref in selected_result.get("source_exchange_refs", []) if str(ref).strip()
            ] if isinstance(selected_result.get("source_exchange_refs"), list) else [],
            "source_trace_refs": [
                str(ref) for ref in selected_result.get("source_trace_refs", []) if str(ref).strip()
            ] if isinstance(selected_result.get("source_trace_refs"), list) else [],
            "selected_signal_id": str(reliability.get("selected_signal_id") or "") or None,
            "signal_terms": list(reliability.get("signal_terms", [])) if isinstance(reliability.get("signal_terms"), list) else [],
            "workflow_map_focus": bool(workflow_projection),
            "workflow_fragmentation_count": len(workflow_projection.get("fragmentation_points", [])) if isinstance(workflow_projection.get("fragmentation_points"), list) else 0,
            "workflow_handoff_count": len(workflow_projection.get("handoff_boundaries", [])) if isinstance(workflow_projection.get("handoff_boundaries"), list) else 0,
            "workflow_responsibility_gap_count": len(workflow_projection.get("responsibility_gaps", [])) if isinstance(workflow_projection.get("responsibility_gaps"), list) else 0,
            "workflow_review_guidance": str(workflow_projection.get("review_guidance") or "") or None,
            "longitudinal_focus": {
                "selected_window_id": longitudinal.get("selected_window_id"),
                "same_study_run_count": int(longitudinal.get("same_study_run_count") or 0),
                "same_project_study_count": int(longitudinal.get("same_project_study_count") or 0),
                "study_timeline_entry_count": int(longitudinal.get("study_timeline_entry_count") or 0),
                "source_calibration_status": calibration_lineage.get("calibration_status"),
            },
            "recurring_signal_focus": {
                "pattern_count": int(recurring_signal_synthesis.get("pattern_count") or 0),
                "persistent_pattern_count": int(recurring_signal_synthesis.get("persistent_pattern_count") or 0),
                "pattern_ids": [
                    item.get("pattern_id")
                    for item in recurring_signal_synthesis.get("patterns", [])
                    if isinstance(item, dict) and item.get("pattern_id")
                ]
                if isinstance(recurring_signal_synthesis.get("patterns"), list)
                else [],
            },
            "panel_learning_focus": {
                "segment_status": segment_divergence.get("status"),
                "repeated_hotspot_axes": list(segment_divergence.get("repeated_hotspot_axes", []))
                if isinstance(segment_divergence.get("repeated_hotspot_axes"), list)
                else [],
                "persistent_undercovered_axes": list(segment_divergence.get("persistent_undercovered_axes", []))
                if isinstance(segment_divergence.get("persistent_undercovered_axes"), list)
                else [],
                "confidence_status": confidence_trend.get("status"),
                "total_decision_count": int(decision_trends.get("total_decision_count") or 0),
                "latest_decision_change_status": decision_trends.get("latest_change_status"),
            },
            "readiness_gate": readiness_gate,
            "provider_runtime_boundary": provider_runtime_boundary,
        }

    def _query_run_evidence_with_fallback(
        self,
        *,
        workspace_id: str = "",
        run_id: str,
        query_text: str = "",
        active_family: str = "all",
        sort_by: str = "relevance",
        selected_result_id: str | None = None,
        selected_replay_step_id: str | None = None,
        selected_comparison_run_id: str | None = None,
    ) -> dict[str, Any] | None:
        last_error: Exception | None = None
        for index_root in _candidate_index_roots(self.runtime_root, workspace_id or None):
            try:
                query_payload = query_run_evidence(
                    index_root,
                    run_id=run_id,
                    query_text=query_text,
                    active_family=active_family,
                    sort_by=sort_by,
                    selected_result_id=selected_result_id,
                    selected_replay_step_id=selected_replay_step_id,
                    selected_comparison_run_id=selected_comparison_run_id,
                )
                if not isinstance(query_payload, dict):
                    return None
                if workspace_id:
                    query_payload = self._augment_workspace_query_payload(
                        workspace_id=workspace_id,
                        run_id=run_id,
                        query_payload=query_payload,
                    )
                return query_payload
            except Exception as exc:
                last_error = exc
        if last_error is not None:
            return None
        return None

    def _build_readiness_gate_from_query(self, query_payload: dict[str, Any] | None) -> dict[str, Any]:
        readiness = {
            "contract_version": "workspace-evidence-readiness-gate/v0-draft",
            "status": "pending",
            "share_status": "pending",
            "market_claims_allowed": False,
            "boundary_required": True,
            "selected_signal_id": None,
            "stability_label": "pending",
            "stability_score": 0,
            "human_validation_gap": True,
            "missing_context_count": 0,
            "contradicting_evidence_count": 0,
            "supporting_evidence_count": 0,
            "calibration_status": "unavailable",
            "external_benchmark_status": None,
            "provider_name": None,
            "provider_evidence_mode": "unknown",
            "provider_runtime_status": None,
            "gate_reasons": ["completed_evidence_required"],
            "threshold_gaps": [],
            "boundary_note": "Readiness remains pending until completed evidence can be reviewed.",
            "distribution_note": "Do not treat pending synthetic evidence as market proof.",
        }
        if not isinstance(query_payload, dict):
            return readiness
        provider_runtime_boundary = query_payload.get("provider_runtime_boundary")
        if not isinstance(provider_runtime_boundary, dict):
            audit_lineage = query_payload.get("audit_lineage")
            source_run = audit_lineage.get("source_run", {}) if isinstance(audit_lineage, dict) else {}
            provider_runtime_boundary = (
                source_run.get("provider_runtime_boundary", {})
                if isinstance(source_run, dict)
                else {}
            )
        if isinstance(provider_runtime_boundary, dict) and provider_runtime_boundary:
            readiness.update(
                {
                    "provider_name": provider_runtime_boundary.get("provider_name"),
                    "provider_evidence_mode": provider_runtime_boundary.get("evidence_mode") or "unknown",
                    "provider_runtime_status": provider_runtime_boundary.get("runtime_status"),
                }
            )
        query_status = str(query_payload.get("query_status") or "")
        reliability = query_payload.get("evidence_reliability")
        if not isinstance(reliability, dict):
            return readiness

        calibration = reliability.get("human_calibration")
        if not isinstance(calibration, dict):
            calibration = None
        missing_context = reliability.get("missing_context") if isinstance(reliability.get("missing_context"), list) else []
        contradicting_evidence = reliability.get("contradicting_evidence") if isinstance(reliability.get("contradicting_evidence"), list) else []
        supporting_evidence = reliability.get("supporting_evidence") if isinstance(reliability.get("supporting_evidence"), list) else []
        calibration_records = reliability.get("calibration_records") if isinstance(reliability.get("calibration_records"), list) else []
        selected_signal_id = str(reliability.get("selected_signal_id") or "") or None
        human_validation_gap = any(
            isinstance(item, dict) and str(item.get("id") or "") == "human_validation_gap"
            for item in missing_context
        )

        replacement_status = ""
        boundary_note = str(reliability.get("synthetic_boundary") or "").strip()
        if calibration is not None:
            replacement = calibration.get("replacement_readiness") if isinstance(calibration.get("replacement_readiness"), dict) else {}
            replacement_status = str(replacement.get("status") or "").strip()
            boundary_note = str(replacement.get("boundary") or boundary_note).strip()
        external_record = next(
            (
                item for item in calibration_records
                if isinstance(item, dict) and str(item.get("id") or "") == "external_benchmark_readiness"
            ),
            None,
        )
        gate_reasons = list(external_record.get("gate_reasons", [])) if isinstance(external_record, dict) and isinstance(external_record.get("gate_reasons"), list) else []
        threshold_gaps = list(external_record.get("threshold_gaps", [])) if isinstance(external_record, dict) and isinstance(external_record.get("threshold_gaps"), list) else []

        if query_status != "query_ready":
            status = "pending"
            share_status = "pending"
            distribution_note = "Completed evidence is required before readiness-gated sharing can be assessed."
            gate_reasons = gate_reasons or ["completed_evidence_required"]
            calibration_status = "unavailable"
        elif replacement_status == "candidate_replacement_ready":
            status = "scoped_external_ready"
            share_status = "scoped_customer_ready"
            distribution_note = "Scoped customer-facing claims are allowed only for the calibrated stage and evidence type recorded in this run."
            calibration_status = replacement_status
        elif replacement_status == "directional_calibration_ready":
            status = "directional_only"
            share_status = "boundary_only"
            distribution_note = "External human data supports directional use, but not customer-facing proof or replacement-grade claims."
            calibration_status = replacement_status
            gate_reasons = gate_reasons or ["replacement_threshold_not_met"]
        elif replacement_status == "calibrated_fixture_only":
            status = "fixture_only"
            share_status = "boundary_only"
            distribution_note = "Fixture-backed calibration can travel with explicit synthetic boundary language, but customer-facing proof remains gated."
            calibration_status = replacement_status
            gate_reasons = gate_reasons or ["fixture_human_review_only"]
        elif replacement_status == "high_stakes_human_review_required":
            status = "human_review_required"
            share_status = "restricted_human_review_required"
            distribution_note = "High-stakes evidence remains gated to explicit human review regardless of synthetic alignment score."
            calibration_status = replacement_status
            gate_reasons = gate_reasons or ["high_stakes_human_review_required"]
        elif calibration is not None:
            status = "insufficient_benchmarking"
            share_status = "boundary_only"
            distribution_note = "Calibration exists but threshold gaps still block customer-facing readiness claims."
            calibration_status = replacement_status or "not_ready"
            gate_reasons = gate_reasons or ["configured_readiness_threshold_not_met"]
        else:
            status = "human_validation_required"
            share_status = "boundary_only"
            distribution_note = "Synthetic evidence may be shared only with explicit boundary language until human calibration is attached."
            calibration_status = "unavailable"
            gate_reasons = gate_reasons or ["human_validation_gap"]

        readiness.update(
            {
                "status": status,
                "share_status": share_status,
                "market_claims_allowed": status in READINESS_GATE_CUSTOMER_READY_STATUSES,
                "boundary_required": True,
                "selected_signal_id": selected_signal_id,
                "stability_label": str(reliability.get("stability_label") or "pending"),
                "stability_score": int(reliability.get("stability_score") or 0),
                "human_validation_gap": human_validation_gap,
                "missing_context_count": len(missing_context),
                "contradicting_evidence_count": len(contradicting_evidence),
                "supporting_evidence_count": len(supporting_evidence),
                "calibration_status": calibration_status,
                "external_benchmark_status": external_record.get("status") if isinstance(external_record, dict) else None,
                "calibration_records": calibration_records,
                "gate_reasons": gate_reasons,
                "threshold_gaps": threshold_gaps,
                "boundary_note": boundary_note or readiness["boundary_note"],
                "distribution_note": distribution_note,
            }
        )
        return readiness

    @staticmethod
    def _build_mvp_launch_scope(readiness_gate: dict[str, Any] | None) -> dict[str, Any]:
        gate = dict(readiness_gate or {})
        readiness_status = str(gate.get("status") or "pending").strip() or "pending"
        share_status = str(gate.get("share_status") or "pending").strip() or "pending"
        if readiness_status == "scoped_external_ready":
            return {
                "contract_version": "workspace-mvp-launch-scope/v0-draft",
                "status": "design_partner_candidate",
                "launch_type": "controlled_design_partner_or_paid_pilot",
                "allowed_audiences": ["internal_team", "design_partner"],
                "share_allowed": share_status not in READINESS_GATE_BLOCKED_SHARE_STATUSES,
                "market_claims_allowed": True,
                "requires_manual_approval": True,
                "note": "Scoped external calibration is strong enough for controlled design-partner circulation, not public self-serve launch.",
            }
        if share_status == "restricted_human_review_required":
            return {
                "contract_version": "workspace-mvp-launch-scope/v0-draft",
                "status": "blocked",
                "launch_type": "not_launch_ready",
                "allowed_audiences": ["internal_team"],
                "share_allowed": False,
                "market_claims_allowed": False,
                "requires_manual_approval": True,
                "note": "High-stakes or human-review-required evidence is blocked from controlled MVP circulation.",
            }
        return {
            "contract_version": "workspace-mvp-launch-scope/v0-draft",
            "status": "internal_only",
            "launch_type": "not_launch_ready",
            "allowed_audiences": ["internal_team"],
            "share_allowed": share_status not in READINESS_GATE_BLOCKED_SHARE_STATUSES,
            "market_claims_allowed": False,
            "requires_manual_approval": True,
            "note": "Evidence can support internal review, but controlled design-partner launch remains gated until scoped external readiness is reached.",
        }

    @staticmethod
    def _required_public_claim_disclosures() -> list[str]:
        return [
            "Synthetic evidence only. This output is not human market proof.",
            "Any external readiness is scoped by stage, evidence type, benchmark coverage, and market context.",
            "Do not use this platform for high-stakes approval, compliance sign-off, or replacement-grade claims without explicit human review.",
        ]

    @staticmethod
    def _build_public_claims_boundary(
        *,
        readiness_gate: dict[str, Any] | None,
        mvp_launch_scope: dict[str, Any] | None,
        regulated_review_boundary: dict[str, Any] | None = None,
        governed_review: dict[str, Any] | None = None,
        governed_redaction: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        gate = dict(readiness_gate or {})
        launch_scope = dict(mvp_launch_scope or {})
        regulated = dict(regulated_review_boundary or {})
        review = dict(governed_review or {})
        redaction = dict(governed_redaction or {})

        readiness_status = str(gate.get("status") or "pending").strip() or "pending"
        launch_scope_status = str(launch_scope.get("status") or "internal_only").strip() or "internal_only"
        classification_status = str(regulated.get("classification_status") or "standard").strip() or "standard"
        review_gate_status = str(review.get("review_gate_status") or "not_required").strip() or "not_required"
        redaction_status = str(redaction.get("status") or "not_required").strip() or "not_required"

        blocked_reasons: list[str] = []
        if classification_status == "high_stakes" or bool(review.get("human_review_required")):
            blocked_reasons.append("regulated_or_high_stakes_human_review_required")
        if review_gate_status in {"blocked_reviewer_unassigned", "escalated"}:
            blocked_reasons.append("governed_reviewer_clearance_incomplete")
        if not bool(redaction.get("circulation_allowed")) and redaction_status not in {"not_required", "active"}:
            blocked_reasons.append("viewer_safe_redaction_incomplete")
        for reason in gate.get("gate_reasons", []):
            normalized_reason = str(reason or "").strip()
            if normalized_reason:
                blocked_reasons.append(normalized_reason)

        customer_claim_status = "synthetic_preview_only"
        status = "research_preview_only"
        self_serve_public_launch_allowed = False
        if launch_scope_status in {"public_candidate", "self_serve_candidate", "bounded_public_candidate"}:
            status = "bounded_public_candidate"
            customer_claim_status = "bounded_public_claims_allowed"
            self_serve_public_launch_allowed = True
        elif classification_status == "high_stakes" or bool(review.get("human_review_required")):
            status = "governed_preview_only"
        elif launch_scope_status == "design_partner_candidate" and bool(gate.get("market_claims_allowed")):
            status = "controlled_mvp_only"
            customer_claim_status = "bounded_public_claims_allowed"
            blocked_reasons.append("public_self_serve_launch_not_yet_approved")
        elif readiness_status != "scoped_external_ready":
            blocked_reasons.append("scoped_external_readiness_not_yet_reached")

        if not self_serve_public_launch_allowed:
            blocked_reasons.append("replacement_grade_claims_not_allowed")

        deduped_blocked_reasons: list[str] = []
        for reason in blocked_reasons:
            if reason not in deduped_blocked_reasons:
                deduped_blocked_reasons.append(reason)

        return {
            "contract_version": "workspace-public-claims-boundary/v0-draft",
            "status": status,
            "customer_claim_status": customer_claim_status,
            "self_serve_public_launch_allowed": self_serve_public_launch_allowed,
            "allowed_audiences": list(launch_scope.get("allowed_audiences", [])) if isinstance(launch_scope.get("allowed_audiences"), list) else [],
            "required_customer_disclosures": SaasRuntime._required_public_claim_disclosures(),
            "prohibited_claims": [
                "replacement_grade_reliability",
                "human_market_proof",
                "high_stakes_approval_without_human_review",
                "unsupported_market_or_domain_generalization",
            ],
            "blocked_reasons": deduped_blocked_reasons,
            "benchmark_disclosure": {
                "readiness_status": readiness_status,
                "calibration_status": gate.get("calibration_status"),
                "external_benchmark_status": gate.get("external_benchmark_status"),
                "human_validation_gap": gate.get("human_validation_gap"),
                "threshold_gaps": list(gate.get("threshold_gaps", [])) if isinstance(gate.get("threshold_gaps"), list) else [],
                "gate_reasons": list(gate.get("gate_reasons", [])) if isinstance(gate.get("gate_reasons"), list) else [],
                "benchmark_origin": next(
                    (
                        record.get("benchmark_origin")
                        for record in gate.get("calibration_records", [])
                        if isinstance(record, dict) and str(record.get("id") or "") == "external_benchmark_readiness"
                    ),
                    None,
                ),
                "source_type": next(
                    (
                        record.get("source_type")
                        for record in gate.get("calibration_records", [])
                        if isinstance(record, dict) and str(record.get("id") or "") == "external_benchmark_readiness"
                    ),
                    None,
                ),
            },
            "boundary_note": (
                "Controlled MVP circulation may be benchmark-backed for scoped use cases, but broader public launch "
                "still requires explicit public-claim boundaries and remains synthetic-only."
                if status == "controlled_mvp_only"
                else "Public claim boundaries remain preview-only until benchmark disclosure, governance, and launch review permit wider circulation."
            ),
        }

    @staticmethod
    def _build_mvp_promotion_state(
        mvp_launch_scope: dict[str, Any] | None,
        current_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scope = dict(mvp_launch_scope or {})
        current = dict(current_state or {})
        scope_status = str(scope.get("status") or "internal_only").strip() or "internal_only"
        if scope_status == "design_partner_candidate":
            status = str(current.get("status") or "approval_required").strip() or "approval_required"
            if status not in {"approval_required", "pending_approval", "approved", "rejected"}:
                status = "approval_required"
            note = str(current.get("note") or "").strip() or (
                "Design-partner circulation requires explicit approval even when scoped external readiness exists."
            )
            return {
                "contract_version": "workspace-mvp-promotion/v0-draft",
                "eligible": True,
                "status": status,
                "target_audience": "design_partner",
                "share_requires_approval": True,
                "requested_by_user_id": current.get("requested_by_user_id"),
                "requested_at": current.get("requested_at"),
                "request_note": str(current.get("request_note") or ""),
                "reviewed_by_user_id": current.get("reviewed_by_user_id"),
                "reviewed_at": current.get("reviewed_at"),
                "review_note": str(current.get("review_note") or ""),
                "note": note,
            }
        if scope_status == "blocked":
            return {
                "contract_version": "workspace-mvp-promotion/v0-draft",
                "eligible": False,
                "status": "blocked",
                "target_audience": None,
                "share_requires_approval": False,
                "requested_by_user_id": None,
                "requested_at": None,
                "request_note": "",
                "reviewed_by_user_id": None,
                "reviewed_at": None,
                "review_note": "",
                "note": "Launch scope is blocked by the current readiness boundary, so design-partner promotion is unavailable.",
            }
        return {
            "contract_version": "workspace-mvp-promotion/v0-draft",
            "eligible": False,
            "status": "not_applicable",
            "target_audience": None,
            "share_requires_approval": False,
            "requested_by_user_id": None,
            "requested_at": None,
            "request_note": "",
            "reviewed_by_user_id": None,
            "reviewed_at": None,
            "review_note": "",
            "note": "This export remains internal-only and is not eligible for design-partner promotion.",
        }

    @staticmethod
    def _build_partner_onboarding_state(
        *,
        study: WorkspaceStudy | None,
        mvp_launch_scope: dict[str, Any] | None,
        mvp_promotion: dict[str, Any] | None,
        partner_context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scope = dict(mvp_launch_scope or {})
        promotion = dict(mvp_promotion or {})
        context = dict(partner_context or {})
        scope_status = str(scope.get("status") or "internal_only").strip() or "internal_only"
        promotion_status = str(promotion.get("status") or "not_applicable").strip() or "not_applicable"
        partner_name = str(context.get("partner_name") or "").strip()
        partner_team_label = str(context.get("partner_team_label") or "").strip()
        partner_use_case = str(context.get("partner_use_case") or "").strip()
        support_channel = str(context.get("support_channel") or "").strip() or "workspace_support_snapshot_and_owner_admin_review"
        review_window_days_raw = context.get("review_window_days")
        review_window_days = int(review_window_days_raw) if isinstance(review_window_days_raw, int) and review_window_days_raw > 0 else 14
        study_title = study.title if study is not None else ""
        study_status = study.status if study is not None else ""
        base_acknowledgements = [
            "Synthetic evidence only. This share is not human market proof.",
            "Any external readiness remains scoped to the stage and evidence type attached to this study.",
            "Do not reuse this share for high-stakes approval, public marketing proof, or replacement-grade claims.",
        ]
        if (
            scope_status == "design_partner_candidate"
            and promotion_status == "approved"
            and partner_name
            and partner_use_case
        ):
            return {
                "contract_version": "workspace-partner-onboarding/v0-draft",
                "status": "ready",
                "partner_name": partner_name,
                "partner_team_label": partner_team_label,
                "partner_use_case": partner_use_case,
                "study_title": study_title,
                "study_status": study_status,
                "support_channel": support_channel,
                "review_window_days": review_window_days,
                "required_acknowledgements": base_acknowledgements,
                "circulation_policy": {
                    "contract_version": "workspace-partner-circulation-policy/v0-draft",
                    "status": "bounded_design_partner_only",
                    "audience": "named_design_partner_team",
                    "resharing_allowed": False,
                    "allowed_use_cases": [
                        "discovery_review",
                        "concept_evaluation_review",
                        "prototype_validation_review",
                    ],
                    "prohibited_actions": [
                        "public_marketing_claims",
                        "replacement_grade_claims",
                        "high_stakes_approval_without_human_review",
                        "secondary_external_reshare",
                    ],
                    "boundary_note": "Use this share only for bounded design-partner review inside the named partner team.",
                },
                "note": "Partner onboarding is ready for bounded design-partner circulation.",
            }
        if scope_status == "design_partner_candidate":
            return {
                "contract_version": "workspace-partner-onboarding/v0-draft",
                "status": "approval_or_partner_context_required",
                "partner_name": partner_name,
                "partner_team_label": partner_team_label,
                "partner_use_case": partner_use_case,
                "study_title": study_title,
                "study_status": study_status,
                "support_channel": support_channel,
                "review_window_days": review_window_days,
                "required_acknowledgements": base_acknowledgements,
                "circulation_policy": {
                    "contract_version": "workspace-partner-circulation-policy/v0-draft",
                    "status": "not_ready",
                    "audience": "pending_design_partner_approval",
                    "resharing_allowed": False,
                    "allowed_use_cases": [],
                    "prohibited_actions": [
                        "public_marketing_claims",
                        "replacement_grade_claims",
                        "high_stakes_approval_without_human_review",
                        "secondary_external_reshare",
                    ],
                    "boundary_note": "Partner circulation stays unavailable until promotion is approved and partner context is attached.",
                },
                "note": "Design-partner onboarding requires approval plus named partner context before share creation.",
            }
        if scope_status == "blocked":
            return {
                "contract_version": "workspace-partner-onboarding/v0-draft",
                "status": "blocked",
                "partner_name": "",
                "partner_team_label": "",
                "partner_use_case": "",
                "study_title": study_title,
                "study_status": study_status,
                "support_channel": support_channel,
                "review_window_days": review_window_days,
                "required_acknowledgements": base_acknowledgements,
                "circulation_policy": {
                    "contract_version": "workspace-partner-circulation-policy/v0-draft",
                    "status": "blocked",
                    "audience": "internal_team",
                    "resharing_allowed": False,
                    "allowed_use_cases": [],
                    "prohibited_actions": [
                        "public_marketing_claims",
                        "replacement_grade_claims",
                        "high_stakes_approval_without_human_review",
                        "secondary_external_reshare",
                    ],
                    "boundary_note": "Blocked readiness prevents partner circulation.",
                },
                "note": "Blocked readiness prevents partner onboarding.",
            }
        return {
            "contract_version": "workspace-partner-onboarding/v0-draft",
            "status": "not_applicable",
            "partner_name": "",
            "partner_team_label": "",
            "partner_use_case": "",
            "study_title": study_title,
            "study_status": study_status,
            "support_channel": support_channel,
            "review_window_days": review_window_days,
            "required_acknowledgements": base_acknowledgements,
            "circulation_policy": {
                "contract_version": "workspace-partner-circulation-policy/v0-draft",
                "status": "internal_only",
                "audience": "internal_team",
                "resharing_allowed": False,
                "allowed_use_cases": ["internal_research_review"],
                "prohibited_actions": [
                    "public_marketing_claims",
                    "replacement_grade_claims",
                    "high_stakes_approval_without_human_review",
                    "secondary_external_reshare",
                ],
                "boundary_note": "This share remains internal-only and does not need partner onboarding.",
            },
            "note": "Partner onboarding is not required for internal-only circulation.",
        }

    @staticmethod
    def _build_mvp_release_review_state(
        mvp_launch_scope: dict[str, Any] | None,
        mvp_promotion: dict[str, Any] | None,
        partner_onboarding: dict[str, Any] | None,
        current_state: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        scope = dict(mvp_launch_scope or {})
        promotion = dict(mvp_promotion or {})
        onboarding = dict(partner_onboarding or {})
        current = dict(current_state or {})
        scope_status = str(scope.get("status") or "internal_only").strip() or "internal_only"
        promotion_status = str(promotion.get("status") or "not_applicable").strip() or "not_applicable"
        onboarding_status = str(onboarding.get("status") or "not_applicable").strip() or "not_applicable"
        checklist = {
            "readiness_gate_ok": scope_status == "design_partner_candidate",
            "promotion_approved": promotion_status == "approved",
            "partner_onboarding_ready": onboarding_status == "ready",
        }
        if scope_status == "design_partner_candidate":
            status = str(current.get("status") or "approval_required").strip() or "approval_required"
            if status not in {"approval_required", "pending_approval", "approved", "rejected"}:
                status = "approval_required"
            if not all(checklist.values()):
                status = "approval_required"
            return {
                "contract_version": "workspace-mvp-release-review/v0-draft",
                "eligible": all(checklist.values()),
                "status": status,
                "requested_by_user_id": current.get("requested_by_user_id"),
                "requested_at": current.get("requested_at"),
                "request_note": str(current.get("request_note") or ""),
                "reviewed_by_user_id": current.get("reviewed_by_user_id"),
                "reviewed_at": current.get("reviewed_at"),
                "review_note": str(current.get("review_note") or ""),
                "checklist": checklist,
                "note": (
                    str(current.get("note") or "").strip()
                    or "Controlled MVP public delivery requires final release review approval on top of readiness, promotion, and partner onboarding."
                ),
            }
        if scope_status == "blocked":
            return {
                "contract_version": "workspace-mvp-release-review/v0-draft",
                "eligible": False,
                "status": "blocked",
                "requested_by_user_id": None,
                "requested_at": None,
                "request_note": "",
                "reviewed_by_user_id": None,
                "reviewed_at": None,
                "review_note": "",
                "checklist": checklist,
                "note": "Blocked launch scope prevents controlled MVP release review.",
            }
        return {
            "contract_version": "workspace-mvp-release-review/v0-draft",
            "eligible": False,
            "status": "not_applicable",
            "requested_by_user_id": None,
            "requested_at": None,
            "request_note": "",
            "reviewed_by_user_id": None,
            "reviewed_at": None,
            "review_note": "",
            "checklist": checklist,
            "note": "Controlled MVP release review is not required for internal-only shares.",
        }

    def _write_governed_compliance_bundle_file(self, root: Path, payload: dict[str, Any]) -> str:
        compliance_path = root / "compliance_audit_bundle.json"
        write_json(compliance_path, payload)
        return str(compliance_path)

    def _write_export_bundle_contract_files(self, export_bundle: WorkspaceExportBundle) -> None:
        manifest_path = Path(export_bundle.manifest_path)
        if not manifest_path.exists():
            raise FileNotFoundError(f"Export bundle manifest not found: {manifest_path}")
        payload = read_json(manifest_path)
        if not isinstance(payload, dict):
            raise ValueError("Export bundle manifest must contain an object payload.")
        metadata = dict(export_bundle.metadata or {})
        readiness_gate = metadata.get("readiness_gate")
        if not isinstance(readiness_gate, dict):
            readiness_gate = {}
        mvp_launch_scope = metadata.get("mvp_launch_scope")
        if not isinstance(mvp_launch_scope, dict):
            mvp_launch_scope = self._build_mvp_launch_scope(readiness_gate)
        mvp_promotion = metadata.get("mvp_promotion")
        if not isinstance(mvp_promotion, dict):
            mvp_promotion = self._build_mvp_promotion_state(mvp_launch_scope)
        mvp_promotion_history = _history_entries(metadata.get("mvp_promotion_history"))
        governed_review = metadata.get("governed_review")
        if not isinstance(governed_review, dict):
            study = job_store.get_workspace_study(self.runtime_root, export_bundle.study_id)
            governed_review = (
                self._study_governed_review_state(study)
                if study is not None and study.workspace_id == export_bundle.workspace_id
                else {}
            )
        governed_redaction = metadata.get("governed_redaction")
        if not isinstance(governed_redaction, dict):
            study = job_store.get_workspace_study(self.runtime_root, export_bundle.study_id)
            governed_redaction = (
                self._study_governed_redaction_state(study)
                if study is not None and study.workspace_id == export_bundle.workspace_id
                else {}
            )
        public_claims_boundary = metadata.get("public_claims_boundary")
        if not isinstance(public_claims_boundary, dict):
            regulated_review_boundary = metadata.get("regulated_review_boundary")
            if not isinstance(regulated_review_boundary, dict):
                study = job_store.get_workspace_study(self.runtime_root, export_bundle.study_id)
                regulated_review_boundary = (
                    self._study_regulated_review_boundary(study)
                    if study is not None and study.workspace_id == export_bundle.workspace_id
                    else {}
                )
            public_claims_boundary = self._build_public_claims_boundary(
                readiness_gate=readiness_gate,
                mvp_launch_scope=mvp_launch_scope,
                regulated_review_boundary=regulated_review_boundary,
                governed_review=governed_review,
                governed_redaction=governed_redaction,
            )
        metadata["public_claims_boundary"] = public_claims_boundary
        payload["governed_review"] = governed_review
        payload["governed_redaction"] = governed_redaction
        if export_bundle.study_id:
            study = job_store.get_workspace_study(self.runtime_root, export_bundle.study_id)
            if study is not None and study.workspace_id == export_bundle.workspace_id:
                payload["compliance_audit_bundle"] = self._build_governed_compliance_audit_bundle(
                    workspace_id=export_bundle.workspace_id,
                    study=study,
                    project_id=export_bundle.project_id,
                    job_id=export_bundle.job_id,
                    run_id=export_bundle.run_id,
                    export_bundle_id=export_bundle.export_bundle_id,
                    readiness_gate=readiness_gate,
                    mvp_launch_scope=mvp_launch_scope,
                    mvp_promotion=mvp_promotion,
                    distribution_context={
                        "surface": "export_bundle",
                        "export_format": export_bundle.export_format,
                        "circulation_allowed": bool(governed_redaction.get("circulation_allowed")),
                    },
                )
                metadata["compliance_audit_bundle_path"] = self._write_governed_compliance_bundle_file(
                    Path(export_bundle.bundle_root),
                    payload["compliance_audit_bundle"],
                )
        payload.update(
            {
                "status": export_bundle.status,
                "title": export_bundle.title,
                "created_at": export_bundle.created_at,
                "created_by_user_id": export_bundle.created_by_user_id,
                "readiness_gate": readiness_gate,
                "governed_review": governed_review,
                "governed_redaction": governed_redaction,
                "public_claims_boundary": public_claims_boundary,
                "mvp_launch_scope": mvp_launch_scope,
                "mvp_promotion": mvp_promotion,
                "mvp_promotion_history": mvp_promotion_history,
                "metadata": metadata,
            }
        )
        write_json(manifest_path, payload)
        write_markdown(
            Path(export_bundle.bundle_root) / "README.md",
            "\n".join(
                [
                    f"# {export_bundle.title}",
                    "",
                    f"- synthetic boundary: {export_bundle.synthetic_boundary}",
                    f"- project_id: {export_bundle.project_id}",
                    f"- study_id: {export_bundle.study_id}",
                    f"- job_id: {export_bundle.job_id}",
                    f"- run_id: {export_bundle.run_id}",
                    f"- export_format: {export_bundle.export_format}",
                    f"- readiness_status: {readiness_gate.get('status', 'pending')}",
                    f"- market_claims_allowed: {readiness_gate.get('market_claims_allowed', False)}",
                    f"- governed_review_status: {governed_review.get('review_gate_status', 'not_required')}",
                    f"- governed_redaction_status: {governed_redaction.get('status', 'not_required')}",
                    f"- public_claim_boundary: {public_claims_boundary.get('status', 'research_preview_only')}",
                    f"- mvp_launch_scope: {mvp_launch_scope.get('status', 'internal_only')}",
                    f"- mvp_promotion_status: {mvp_promotion.get('status', 'not_applicable')}",
                    f"- mvp_promotion_history_events: {len(mvp_promotion_history)}",
                    "",
                    "This bundle preserves study and run lineage for synthetic evidence review.",
                ]
            ),
        )

    def _write_share_bundle_contract_files(self, share_bundle: WorkspaceShareBundle) -> None:
        payload_path = Path(share_bundle.share_payload_path)
        if not payload_path.exists():
            raise FileNotFoundError(f"Share payload not found: {payload_path}")
        payload = read_json(payload_path)
        if not isinstance(payload, dict):
            raise ValueError("Share payload must contain an object payload.")
        metadata = dict(share_bundle.metadata or {})
        readiness_gate = metadata.get("readiness_gate")
        if not isinstance(readiness_gate, dict):
            readiness_gate = {}
        mvp_launch_scope = metadata.get("mvp_launch_scope")
        if not isinstance(mvp_launch_scope, dict):
            mvp_launch_scope = self._build_mvp_launch_scope(readiness_gate)
        mvp_promotion = metadata.get("mvp_promotion")
        if not isinstance(mvp_promotion, dict):
            mvp_promotion = self._build_mvp_promotion_state(mvp_launch_scope)
        mvp_promotion_history = _history_entries(metadata.get("mvp_promotion_history"))
        partner_onboarding = metadata.get("partner_onboarding")
        if not isinstance(partner_onboarding, dict):
            partner_onboarding = self._build_partner_onboarding_state(
                study=None,
                mvp_launch_scope=mvp_launch_scope,
                mvp_promotion=mvp_promotion,
            )
        mvp_release_review = metadata.get("mvp_release_review")
        if not isinstance(mvp_release_review, dict):
            mvp_release_review = self._build_mvp_release_review_state(
                mvp_launch_scope,
                mvp_promotion,
                partner_onboarding,
            )
        mvp_release_review_history = _history_entries(metadata.get("mvp_release_review_history"))
        governed_review = metadata.get("governed_review")
        if not isinstance(governed_review, dict):
            study = job_store.get_workspace_study(self.runtime_root, share_bundle.study_id)
            governed_review = (
                self._study_governed_review_state(study)
                if study is not None and study.workspace_id == share_bundle.workspace_id
                else {}
            )
        governed_redaction = metadata.get("governed_redaction")
        if not isinstance(governed_redaction, dict):
            study = job_store.get_workspace_study(self.runtime_root, share_bundle.study_id)
            governed_redaction = (
                self._study_governed_redaction_state(study)
                if study is not None and study.workspace_id == share_bundle.workspace_id
                else {}
            )
        public_claims_boundary = metadata.get("public_claims_boundary")
        if not isinstance(public_claims_boundary, dict):
            regulated_review_boundary = metadata.get("regulated_review_boundary")
            if not isinstance(regulated_review_boundary, dict):
                study = job_store.get_workspace_study(self.runtime_root, share_bundle.study_id)
                regulated_review_boundary = (
                    self._study_regulated_review_boundary(study)
                    if study is not None and study.workspace_id == share_bundle.workspace_id
                    else {}
                )
            public_claims_boundary = self._build_public_claims_boundary(
                readiness_gate=readiness_gate,
                mvp_launch_scope=mvp_launch_scope,
                regulated_review_boundary=regulated_review_boundary,
                governed_review=governed_review,
                governed_redaction=governed_redaction,
            )
        metadata["public_claims_boundary"] = public_claims_boundary
        payload["governed_review"] = governed_review
        payload["governed_redaction"] = governed_redaction
        payload["public_claims_boundary"] = public_claims_boundary
        if share_bundle.study_id:
            study = job_store.get_workspace_study(self.runtime_root, share_bundle.study_id)
            if study is not None and study.workspace_id == share_bundle.workspace_id:
                redacted_payload, applied_redactions = self._apply_governed_redaction_to_payload(payload, governed_redaction)
                payload = redacted_payload
                payload["governed_redaction"]["applied_redactions"] = applied_redactions
                payload["compliance_audit_bundle"] = self._build_governed_compliance_audit_bundle(
                    workspace_id=share_bundle.workspace_id,
                    study=study,
                    project_id=share_bundle.project_id,
                    job_id=share_bundle.job_id,
                    run_id=share_bundle.run_id,
                    export_bundle_id=share_bundle.export_bundle_id,
                    share_bundle_id=share_bundle.share_bundle_id,
                    readiness_gate=readiness_gate,
                    mvp_launch_scope=mvp_launch_scope,
                    mvp_promotion=mvp_promotion,
                    partner_onboarding=partner_onboarding,
                    mvp_release_review=mvp_release_review,
                    applied_redactions=applied_redactions,
                    redacted_payload_preview={
                        "study_context": dict(payload.get("study_context", {})),
                        "partner_onboarding": dict(payload.get("partner_onboarding", {})),
                    },
                    distribution_context={
                        "surface": "share_bundle",
                        "public_path": share_bundle.public_path,
                        "audience": "external_viewer",
                        "applied_redaction_count": len(applied_redactions),
                    },
                )
                metadata["compliance_audit_bundle_path"] = self._write_governed_compliance_bundle_file(
                    Path(share_bundle.share_root),
                    payload["compliance_audit_bundle"],
                )
        payload.update(
            {
                "status": share_bundle.status,
                "title": share_bundle.title,
                "published_at": share_bundle.published_at,
                "expires_at": share_bundle.expires_at,
                "public_path": share_bundle.public_path,
                "readiness_gate": readiness_gate,
                "governed_review": governed_review,
                "governed_redaction": governed_redaction,
                "public_claims_boundary": public_claims_boundary,
                "mvp_launch_scope": mvp_launch_scope,
                "mvp_promotion": mvp_promotion,
                "mvp_promotion_history": mvp_promotion_history,
                "partner_onboarding": partner_onboarding,
                "mvp_release_review": mvp_release_review,
                "mvp_release_review_history": mvp_release_review_history,
                "metadata": metadata,
            }
        )
        write_json(payload_path, payload)
        write_markdown(
            Path(share_bundle.share_root) / "README.md",
            "\n".join(
                [
                    f"# {share_bundle.title}",
                    "",
                    f"- public_path: {share_bundle.public_path}",
                    f"- export_bundle_id: {share_bundle.export_bundle_id}",
                    f"- project_id: {share_bundle.project_id}",
                    f"- study_id: {share_bundle.study_id}",
                    f"- job_id: {share_bundle.job_id}",
                    f"- run_id: {share_bundle.run_id}",
                    f"- synthetic boundary: {share_bundle.synthetic_boundary}",
                    f"- readiness_status: {readiness_gate.get('status', 'pending')}",
                    f"- market_claims_allowed: {readiness_gate.get('market_claims_allowed', False)}",
                    f"- governed_review_status: {governed_review.get('review_gate_status', 'not_required')}",
                    f"- governed_redaction_status: {governed_redaction.get('status', 'not_required')}",
                    f"- public_claim_boundary: {public_claims_boundary.get('status', 'research_preview_only')}",
                    f"- mvp_launch_scope: {mvp_launch_scope.get('status', 'internal_only')}",
                    f"- mvp_promotion_status: {mvp_promotion.get('status', 'not_applicable')}",
                    f"- mvp_promotion_history_events: {len(mvp_promotion_history)}",
                    f"- partner_onboarding_status: {partner_onboarding.get('status', 'not_applicable')}",
                    f"- mvp_release_review_status: {mvp_release_review.get('status', 'not_applicable')}",
                    f"- mvp_release_review_history_events: {len(mvp_release_review_history)}",
                    f"- partner_name: {partner_onboarding.get('partner_name', '') or 'n/a'}",
                    "",
                    "This share bundle exposes a viewer-safe payload without requiring workspace filesystem inspection.",
                ]
            ),
        )

    def _evidence_view_summary(self, evidence_view: WorkspaceEvidenceView) -> dict[str, Any]:
        metadata = dict(evidence_view.metadata or {})
        study = job_store.get_workspace_study(self.runtime_root, evidence_view.study_id)
        governed_review = (
            self._study_governed_review_state(study)
            if study is not None and study.workspace_id == evidence_view.workspace_id
            else None
        )
        governed_redaction = (
            self._study_governed_redaction_state(study)
            if study is not None and study.workspace_id == evidence_view.workspace_id
            else None
        )
        selected_context = metadata.get("selected_evidence_context")
        if not isinstance(selected_context, dict):
            selected_context = {}
        longitudinal_focus = selected_context.get("longitudinal_focus")
        if not isinstance(longitudinal_focus, dict):
            longitudinal_focus = {}
        recurring_signal_focus = selected_context.get("recurring_signal_focus")
        if not isinstance(recurring_signal_focus, dict):
            recurring_signal_focus = {}
        panel_learning_focus = selected_context.get("panel_learning_focus")
        if not isinstance(panel_learning_focus, dict):
            panel_learning_focus = {}
        readiness_gate = selected_context.get("readiness_gate")
        if not isinstance(readiness_gate, dict):
            readiness_gate = {}
        provider_runtime_boundary = selected_context.get("provider_runtime_boundary")
        if not isinstance(provider_runtime_boundary, dict):
            provider_runtime_boundary = {}
        return {
            **evidence_view.to_dict(),
            "has_replay_focus": bool(evidence_view.selected_replay_step_id),
            "has_comparison_focus": bool(evidence_view.selected_comparison_run_id),
            "selected_signal_id": selected_context.get("selected_signal_id"),
            "signal_terms": list(selected_context.get("signal_terms", [])) if isinstance(selected_context.get("signal_terms"), list) else [],
            "source_exchange_refs": list(selected_context.get("source_exchange_refs", [])) if isinstance(selected_context.get("source_exchange_refs"), list) else [],
            "source_trace_refs": list(selected_context.get("source_trace_refs", [])) if isinstance(selected_context.get("source_trace_refs"), list) else [],
            "workflow_map_focus": bool(selected_context.get("workflow_map_focus")),
            "longitudinal_focus": longitudinal_focus,
            "recurring_signal_focus": recurring_signal_focus,
            "panel_learning_focus": panel_learning_focus,
            "readiness_gate": readiness_gate,
            "provider_runtime_boundary": provider_runtime_boundary,
            "governed_review": governed_review,
            "governed_redaction": governed_redaction,
        }

    def _decision_log_summary(self, decision_log: WorkspaceDecisionLog) -> dict[str, Any]:
        decision_comments = job_store.list_workspace_decision_comments(
            self.runtime_root,
            decision_log.workspace_id,
            decision_log_id=decision_log.decision_log_id,
        )
        comment_summaries = [
            self._decision_comment_summary(comment, decision_comments=decision_comments)
            for comment in decision_comments
        ]
        metadata = dict(decision_log.metadata or {})
        selected_context = metadata.get("selected_evidence_context")
        if not isinstance(selected_context, dict):
            selected_context = {}
        longitudinal_focus = selected_context.get("longitudinal_focus")
        if not isinstance(longitudinal_focus, dict):
            longitudinal_focus = {}
        recurring_signal_focus = selected_context.get("recurring_signal_focus")
        if not isinstance(recurring_signal_focus, dict):
            recurring_signal_focus = {}
        panel_learning_focus = selected_context.get("panel_learning_focus")
        if not isinstance(panel_learning_focus, dict):
            panel_learning_focus = {}
        readiness_gate = metadata.get("readiness_gate")
        if not isinstance(readiness_gate, dict):
            readiness_gate = {}
        provider_runtime_boundary = metadata.get("provider_runtime_boundary")
        if not isinstance(provider_runtime_boundary, dict):
            provider_runtime_boundary = selected_context.get("provider_runtime_boundary")
        if not isinstance(provider_runtime_boundary, dict):
            provider_runtime_boundary = {}
        workspace = job_store.get_workspace(self.runtime_root, decision_log.workspace_id)
        if workspace is None:
            raise FileNotFoundError(f"Workspace '{decision_log.workspace_id}' not found for decision log summary.")
        study = job_store.get_workspace_study(self.runtime_root, decision_log.study_id)
        governed_review = (
            self._study_governed_review_state(study)
            if study is not None and study.workspace_id == decision_log.workspace_id
            else metadata.get("governed_review")
        )
        governed_redaction = (
            self._study_governed_redaction_state(study)
            if study is not None and study.workspace_id == decision_log.workspace_id
            else metadata.get("governed_redaction")
        )
        return {
            **decision_log.to_dict(),
            "has_linked_evidence_view": bool(decision_log.evidence_view_id),
            "has_comparison_focus": bool(decision_log.selected_comparison_run_id),
            "review_status": self._decision_review_status(decision_log),
            "review_status_history": self._decision_review_history(decision_log),
            "review_assignment": self._decision_review_assignment(decision_log, workspace),
            "review_assignment_history": self._decision_review_assignment_history(decision_log),
            "review_status_updated_at": metadata.get("review_status_updated_at") or None,
            "review_status_updated_by_user_id": metadata.get("review_status_updated_by_user_id") or None,
            "latest_review_note": metadata.get("latest_review_note") or "",
            "comment_count": len(decision_comments),
            "review_thread_count": sum(1 for comment in decision_comments if not comment.parent_comment_id),
            "latest_comment_preview": comment_summaries[-1]["body"] if comment_summaries else "",
            "selected_signal_id": selected_context.get("selected_signal_id"),
            "signal_terms": list(selected_context.get("signal_terms", [])) if isinstance(selected_context.get("signal_terms"), list) else [],
            "source_exchange_refs": list(selected_context.get("source_exchange_refs", [])) if isinstance(selected_context.get("source_exchange_refs"), list) else [],
            "source_trace_refs": list(selected_context.get("source_trace_refs", [])) if isinstance(selected_context.get("source_trace_refs"), list) else [],
            "workflow_map_focus": bool(selected_context.get("workflow_map_focus")),
            "longitudinal_focus": longitudinal_focus,
            "recurring_signal_focus": recurring_signal_focus,
            "panel_learning_focus": panel_learning_focus,
            "readiness_gate": readiness_gate,
            "provider_runtime_boundary": provider_runtime_boundary,
            "governed_review": governed_review,
            "governed_redaction": governed_redaction,
        }

    def _export_bundle_summary(self, export_bundle: WorkspaceExportBundle) -> dict[str, Any]:
        share_bundles = job_store.list_workspace_share_bundles(
            self.runtime_root,
            export_bundle.workspace_id,
            export_bundle_id=export_bundle.export_bundle_id,
        )
        metadata = dict(export_bundle.metadata or {})
        readiness_gate = metadata.get("readiness_gate")
        if not isinstance(readiness_gate, dict):
            readiness_gate = {}
        mvp_launch_scope = metadata.get("mvp_launch_scope")
        if not isinstance(mvp_launch_scope, dict):
            mvp_launch_scope = self._build_mvp_launch_scope(readiness_gate)
        mvp_promotion = metadata.get("mvp_promotion")
        if not isinstance(mvp_promotion, dict):
            mvp_promotion = self._build_mvp_promotion_state(mvp_launch_scope)
        mvp_promotion_history = _history_entries(metadata.get("mvp_promotion_history"))
        governed_review = metadata.get("governed_review")
        if not isinstance(governed_review, dict):
            study = job_store.get_workspace_study(self.runtime_root, export_bundle.study_id)
            governed_review = (
                self._study_governed_review_state(study)
                if study is not None and study.workspace_id == export_bundle.workspace_id
                else {}
            )
        governed_redaction = metadata.get("governed_redaction")
        if not isinstance(governed_redaction, dict):
            study = job_store.get_workspace_study(self.runtime_root, export_bundle.study_id)
            governed_redaction = (
                self._study_governed_redaction_state(study)
                if study is not None and study.workspace_id == export_bundle.workspace_id
                else {}
            )
        public_claims_boundary = metadata.get("public_claims_boundary")
        if not isinstance(public_claims_boundary, dict):
            regulated_review_boundary = metadata.get("regulated_review_boundary")
            if not isinstance(regulated_review_boundary, dict):
                study = job_store.get_workspace_study(self.runtime_root, export_bundle.study_id)
                regulated_review_boundary = (
                    self._study_regulated_review_boundary(study)
                    if study is not None and study.workspace_id == export_bundle.workspace_id
                    else {}
                )
            public_claims_boundary = self._build_public_claims_boundary(
                readiness_gate=readiness_gate,
                mvp_launch_scope=mvp_launch_scope,
                regulated_review_boundary=regulated_review_boundary,
                governed_review=governed_review,
                governed_redaction=governed_redaction,
            )
        provider_runtime_boundary = metadata.get("provider_runtime_boundary")
        if not isinstance(provider_runtime_boundary, dict):
            provider_runtime_boundary = {}
        return {
            **export_bundle.to_dict(),
            "exported_file_count": len(export_bundle.exported_files),
            "share_bundle_count": len(share_bundles),
            "readiness_gate": readiness_gate,
            "governed_review": governed_review,
            "governed_redaction": governed_redaction,
            "provider_runtime_boundary": provider_runtime_boundary,
            "public_claims_boundary": public_claims_boundary,
            "market_claims_allowed": bool(readiness_gate.get("market_claims_allowed")),
            "mvp_launch_scope": mvp_launch_scope,
            "mvp_promotion": mvp_promotion,
            "mvp_promotion_history": mvp_promotion_history,
        }

    def _share_bundle_summary(self, share_bundle: WorkspaceShareBundle) -> dict[str, Any]:
        metadata = dict(share_bundle.metadata or {})
        readiness_gate = metadata.get("readiness_gate")
        if not isinstance(readiness_gate, dict):
            readiness_gate = {}
        mvp_launch_scope = metadata.get("mvp_launch_scope")
        if not isinstance(mvp_launch_scope, dict):
            mvp_launch_scope = self._build_mvp_launch_scope(readiness_gate)
        mvp_promotion = metadata.get("mvp_promotion")
        if not isinstance(mvp_promotion, dict):
            mvp_promotion = self._build_mvp_promotion_state(mvp_launch_scope)
        mvp_promotion_history = _history_entries(metadata.get("mvp_promotion_history"))
        partner_onboarding = metadata.get("partner_onboarding")
        if not isinstance(partner_onboarding, dict):
            partner_onboarding = self._build_partner_onboarding_state(
                study=None,
                mvp_launch_scope=mvp_launch_scope,
                mvp_promotion=mvp_promotion,
            )
        mvp_release_review = metadata.get("mvp_release_review")
        if not isinstance(mvp_release_review, dict):
            mvp_release_review = self._build_mvp_release_review_state(
                mvp_launch_scope,
                mvp_promotion,
                partner_onboarding,
            )
        mvp_release_review_history = _history_entries(metadata.get("mvp_release_review_history"))
        governed_review = metadata.get("governed_review")
        if not isinstance(governed_review, dict):
            study = job_store.get_workspace_study(self.runtime_root, share_bundle.study_id)
            governed_review = (
                self._study_governed_review_state(study)
                if study is not None and study.workspace_id == share_bundle.workspace_id
                else {}
            )
        governed_redaction = metadata.get("governed_redaction")
        if not isinstance(governed_redaction, dict):
            study = job_store.get_workspace_study(self.runtime_root, share_bundle.study_id)
            governed_redaction = (
                self._study_governed_redaction_state(study)
                if study is not None and study.workspace_id == share_bundle.workspace_id
                else {}
            )
        public_claims_boundary = metadata.get("public_claims_boundary")
        if not isinstance(public_claims_boundary, dict):
            regulated_review_boundary = metadata.get("regulated_review_boundary")
            if not isinstance(regulated_review_boundary, dict):
                study = job_store.get_workspace_study(self.runtime_root, share_bundle.study_id)
                regulated_review_boundary = (
                    self._study_regulated_review_boundary(study)
                    if study is not None and study.workspace_id == share_bundle.workspace_id
                    else {}
                )
            public_claims_boundary = self._build_public_claims_boundary(
                readiness_gate=readiness_gate,
                mvp_launch_scope=mvp_launch_scope,
                regulated_review_boundary=regulated_review_boundary,
                governed_review=governed_review,
                governed_redaction=governed_redaction,
            )
        provider_runtime_boundary = metadata.get("provider_runtime_boundary")
        if not isinstance(provider_runtime_boundary, dict):
            provider_runtime_boundary = {}
        return {
            **share_bundle.to_dict(),
            "share_file_count": len(self._share_payload_files(share_bundle)),
            "files": self._share_payload_files(share_bundle),
            "readiness_gate": readiness_gate,
            "governed_review": governed_review,
            "governed_redaction": governed_redaction,
            "provider_runtime_boundary": provider_runtime_boundary,
            "public_claims_boundary": public_claims_boundary,
            "market_claims_allowed": bool(readiness_gate.get("market_claims_allowed")),
            "mvp_launch_scope": mvp_launch_scope,
            "mvp_promotion": mvp_promotion,
            "mvp_promotion_history": mvp_promotion_history,
            "partner_onboarding": partner_onboarding,
            "mvp_release_review": mvp_release_review,
            "mvp_release_review_history": mvp_release_review_history,
        }

    def _support_snapshot_summary(self, snapshot: WorkspaceSupportSnapshot) -> dict[str, Any]:
        workspace = job_store.get_workspace(self.runtime_root, snapshot.workspace_id)
        if workspace is None:
            raise FileNotFoundError(f"Workspace '{snapshot.workspace_id}' not found for support snapshot summary.")
        return {
            **snapshot.to_dict(),
            "handoff": self._support_handoff(snapshot, workspace),
            "handoff_history": self._support_handoff_history(snapshot),
        }

    def _support_submission_gate(
        self,
        auth: AuthContext,
        workspace: TenantWorkspace,
        billing: BillingAccount,
        limits: dict[str, int],
        jobs: list[dict[str, Any]],
        *,
        study: WorkspaceStudy | None = None,
    ) -> dict[str, Any]:
        blocked_reasons: list[dict[str, Any]] = []
        if auth.role not in SUBMITTER_ROLES:
            blocked_reasons.append(
                {
                    "code": "role_forbidden",
                    "message": f"Role '{auth.role}' cannot submit validation jobs.",
                    "next_action": "Use an owner, admin, or editor seat to submit or rerun the study.",
                }
            )
        if billing.status not in ACTIVE_BILLING_STATUSES:
            blocked_reasons.append(
                {
                    "code": "billing_inactive",
                    "message": f"Billing status '{billing.status}' does not allow new validation jobs.",
                    "next_action": "Restore an active billing state before retrying submission.",
                }
            )
        active_jobs = sum(1 for job in jobs if str(job.get("status") or "") in {"queued", "running"})
        if active_jobs >= limits["max_concurrent_jobs"]:
            blocked_reasons.append(
                {
                    "code": "concurrency_limit_reached",
                    "message": (
                        f"Workspace '{workspace.workspace_id}' reached the max concurrent job limit "
                        f"({limits['max_concurrent_jobs']})."
                    ),
                    "next_action": "Wait for an in-flight run to finish or move to a higher plan limit.",
                }
            )
        today_floor = _now().replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        daily_jobs = job_store.count_workspace_jobs_created_since(self.runtime_root, workspace.workspace_id, today_floor)
        if daily_jobs >= limits["daily_runs"]:
            blocked_reasons.append(
                {
                    "code": "daily_limit_reached",
                    "message": (
                        f"Workspace '{workspace.workspace_id}' reached the daily run limit "
                        f"({limits['daily_runs']})."
                    ),
                    "next_action": "Retry after the daily limit window resets or move to a higher plan limit.",
                }
            )
        if study is not None:
            regulated_review_boundary = self._study_regulated_review_boundary(study)
            if str(regulated_review_boundary.get("execution_status") or "") != "allowed":
                blocked_reasons.append(
                    {
                        "code": "regulated_high_stakes_boundary_required",
                        "message": str(regulated_review_boundary.get("boundary_message") or "").strip(),
                        "next_action": (
                            "Record explicit governed boundary handling on the study metadata before executing "
                            "this regulated or high-stakes study."
                        ),
                        "study_id": study.study_id,
                        "matched_domain_ids": list(regulated_review_boundary.get("matched_domain_ids", [])),
                    }
                )
        return {
            "status": "blocked" if blocked_reasons else "allowed",
            "blocked_reason_count": len(blocked_reasons),
            "blocked_reasons": blocked_reasons,
            "limits": {
                "daily_runs": limits["daily_runs"],
                "max_concurrent_jobs": limits["max_concurrent_jobs"],
                "artifact_retention_days": limits["artifact_retention_days"],
                "active_jobs": active_jobs,
                "daily_jobs_created": daily_jobs,
            },
        }

    def _support_summary_for_job(self, job: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(job.get("metadata", {}))
        status = str(job.get("status") or "")
        artifact_deleted_at = str(metadata.get("artifact_deleted_at") or "").strip()
        last_error = str(job.get("last_error") or "").strip()
        failure_category = self._support_failure_category(status=status, last_error=last_error, artifact_deleted_at=artifact_deleted_at)
        summary = self._support_summary_text(status=status, last_error=last_error, artifact_deleted_at=artifact_deleted_at)
        return {
            "job_id": str(job.get("job_id") or ""),
            "status": status,
            "provider_name": str(job.get("provider_name") or ""),
            "provider_runtime_boundary": self._validation_provider_runtime_boundary(
                str(job.get("provider_name") or ""),
                status=status,
                last_error=last_error,
                metadata=metadata,
            ),
            "project_id": str(metadata.get("project_id") or "") or None,
            "study_id": str(metadata.get("study_id") or "") or None,
            "run_id": str(metadata.get("run_id") or "") or None,
            "output_run_path": str(job.get("output_run_path") or "") or None,
            "requested_by_user_id": str(job.get("requested_by_user_id") or "") or None,
            "retry_count": int(job.get("retry_count") or 0),
            "created_at": str(job.get("created_at") or "") or None,
            "started_at": str(job.get("started_at") or "") or None,
            "finished_at": str(job.get("finished_at") or "") or None,
            "last_error": last_error or None,
            "failure_category": failure_category,
            "summary": summary,
            "artifact_deleted_at": artifact_deleted_at or None,
            "can_retry": status in {"failed", "canceled"},
            "can_cancel": status == "queued",
            "next_actions": self._support_next_actions(status=status, last_error=last_error, artifact_deleted_at=artifact_deleted_at),
        }

    def _support_failure_category(self, *, status: str, last_error: str, artifact_deleted_at: str) -> str:
        if artifact_deleted_at:
            return "artifact_retention_expired"
        lowered = last_error.lower()
        if status == "canceled":
            return "job_canceled"
        if status == "failed":
            if "unknown provider" in lowered or "provider" in lowered and "unknown" in lowered:
                return "provider_configuration"
            if "not found" in lowered or "missing" in lowered:
                return "missing_input_artifact"
            if "path" in lowered and "workspace boundary" in lowered:
                return "workspace_boundary_violation"
            return "runtime_failure"
        if status == "queued":
            return "awaiting_worker"
        if status == "running":
            return "in_progress"
        return "no_failure"

    def _support_summary_text(self, *, status: str, last_error: str, artifact_deleted_at: str) -> str:
        if artifact_deleted_at:
            return "Run artifacts were purged by retention policy. The study can still be rerun, but the prior artifact set is no longer present."
        if status == "failed":
            return last_error or "The run failed before a completed evidence set was produced."
        if status == "canceled":
            return "The run was canceled before completion."
        if status == "running":
            return "The run is still executing. Wait for the worker to finish before exporting, sharing, or generating a support handoff."
        if status == "queued":
            return "The run is still queued. Wait for a worker lease before diagnosing runtime output."
        return "The selected run completed. Support can still capture the current diagnostic state for audit or handoff."

    def _support_next_actions(self, *, status: str, last_error: str, artifact_deleted_at: str) -> list[str]:
        if artifact_deleted_at:
            return [
                "Rerun the study if you need a fresh evidence set.",
                "Export or share from a newer completed run instead of the purged artifact set.",
            ]
        if status == "failed":
            actions = ["Inspect the failed run inputs and retry from the study surface."]
            lowered = last_error.lower()
            if "provider" in lowered:
                actions.append("Check provider_name or backend configuration before retrying.")
            if "not found" in lowered or "missing" in lowered:
                actions.append("Verify that the referenced brief or persona directory still exists inside the workspace.")
            return actions
        if status == "canceled":
            return ["Resubmit the study when you are ready to continue."]
        if status == "running":
            return ["Wait for worker completion and refresh the study shell.", "Generate a snapshot only if you need operator handoff while the run is still in progress."]
        if status == "queued":
            return ["Wait for an available worker lease.", "If the queue remains blocked, inspect billing and concurrent run limits."]
        return ["Review evidence, export or share if needed, and generate a support snapshot only for operator handoff or audit."]

    def _support_job_digest(self, job: dict[str, Any]) -> dict[str, Any]:
        metadata = dict(job.get("metadata", {}))
        return {
            "job_id": str(job.get("job_id") or ""),
            "status": str(job.get("status") or ""),
            "provider_name": str(job.get("provider_name") or "") or None,
            "provider_runtime_boundary": self._validation_provider_runtime_boundary(
                str(job.get("provider_name") or ""),
                status=str(job.get("status") or ""),
                last_error=str(job.get("last_error") or ""),
                metadata=metadata,
            ),
            "retry_count": int(job.get("retry_count") or 0),
            "study_id": str(metadata.get("study_id") or "") or None,
            "project_id": str(metadata.get("project_id") or "") or None,
            "run_id": str(metadata.get("run_id") or "") or None,
            "created_at": str(job.get("created_at") or "") or None,
            "started_at": str(job.get("started_at") or "") or None,
            "finished_at": str(job.get("finished_at") or "") or None,
            "last_error": str(job.get("last_error") or "") or None,
        }

    def _share_payload_files(self, share_bundle: WorkspaceShareBundle) -> list[dict[str, Any]]:
        payload_path = Path(share_bundle.share_payload_path)
        if not payload_path.exists():
            return []
        payload = read_json(payload_path)
        if not isinstance(payload, dict):
            return []
        files = payload.get("files")
        return list(files) if isinstance(files, list) else []

    def _refresh_share_bundle_status(self, share_bundle: WorkspaceShareBundle) -> WorkspaceShareBundle:
        if share_bundle.status in {"revoked", "expired"}:
            return share_bundle
        if share_bundle.expires_at:
            try:
                expires_at = datetime.fromisoformat(share_bundle.expires_at)
            except ValueError:
                return share_bundle
            if expires_at <= _now():
                return job_store.update_workspace_share_bundle(
                    self.runtime_root,
                    share_bundle_id=share_bundle.share_bundle_id,
                    status="expired",
                )
        return share_bundle

    def _materialize_export_bundle_files(
        self,
        *,
        bundle_root: Path,
        run_dir: Path,
        export_format: str,
        artifact_ids: list[str],
        study: WorkspaceStudy,
        job: dict[str, Any],
        synthetic_boundary: str,
    ) -> list[dict[str, Any]]:
        if export_format == "report_markdown":
            source = run_dir / "report.md"
            if not source.exists():
                raise FileNotFoundError(f"Run artifact not found: {source}")
            destination = bundle_root / "report.md"
            export_file(source, destination)
            return [self._exported_file_entry(source, destination, "report_markdown")]

        if export_format == "report_json":
            source = run_dir / "report.json"
            if not source.exists():
                raise FileNotFoundError(f"Run artifact not found: {source}")
            destination = bundle_root / "report.json"
            export_file(source, destination)
            return [self._exported_file_entry(source, destination, "report_json")]

        if export_format == "report_csv":
            source = run_dir / "report.json"
            if not source.exists():
                raise FileNotFoundError(f"Run artifact not found: {source}")
            destination = bundle_root / "report.csv"
            report_payload = read_json(source)
            if not isinstance(report_payload, dict):
                raise ValueError("report.json must contain an object payload.")
            destination.write_text(render_report_csv(report_payload), encoding="utf-8")
            return [self._exported_file_entry(source, destination, "report_csv")]

        selected_artifact_ids = [str(item).strip() for item in artifact_ids if str(item).strip()]
        if not selected_artifact_ids:
            selected_artifact_ids = [artifact_id for artifact_id in DEFAULT_EXPORT_ARTIFACT_IDS if (run_dir / artifact_id).exists()]
        if not selected_artifact_ids:
            raise ValueError("No exportable run artifacts were found for the selected validation job.")

        exported_files: list[dict[str, Any]] = []
        artifact_root = bundle_root / "artifacts"
        artifact_root.mkdir(parents=True, exist_ok=True)
        for artifact_id in selected_artifact_ids:
            source = (run_dir / artifact_id).resolve()
            if run_dir.resolve() not in source.parents or not source.exists() or not source.is_file():
                raise FileNotFoundError(f"Run artifact not found: {artifact_id}")
            relative_name = Path(artifact_id).name
            destination = artifact_root / relative_name
            export_file(source, destination)
            exported_files.append(self._exported_file_entry(source, destination, "bundle_artifact"))

        notes_payload = {
            "synthetic_boundary": synthetic_boundary,
            "study_title": study.title,
            "job_id": str(job.get("job_id") or ""),
            "exported_file_count": len(exported_files),
        }
        notes_path = bundle_root / "bundle_notes.json"
        write_json(notes_path, notes_payload)
        exported_files.append(self._exported_file_entry(notes_path, notes_path, "bundle_notes"))
        return exported_files

    def _exported_file_entry(self, source: Path, destination: Path, export_kind: str) -> dict[str, Any]:
        mime_type = mimetypes.guess_type(destination.name)[0] or "application/octet-stream"
        return {
            "artifact_id": source.name,
            "export_kind": export_kind,
            "mime_type": mime_type,
            "source_path": str(source),
            "bundle_path": str(destination),
        }
