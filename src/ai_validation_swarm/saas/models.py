from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from ai_validation_swarm.domain.models import PanelSpec


WorkspaceStatus = Literal["active", "suspended", "archived"]
WorkspaceRole = Literal["owner", "admin", "editor", "viewer", "billing_admin"]
SubscriptionStatus = Literal["trialing", "active", "past_due", "canceled"]
JobStatus = Literal["queued", "running", "completed", "failed", "canceled"]
JobPriority = Literal["low", "normal", "high"]
CatalogScope = Literal["global", "workspace_overlay"]
SimilarityDecisionType = Literal["keep", "merge", "rewrite", "reject"]
ProjectStatus = Literal["active", "archived"]
StudyStatus = Literal[
    "draft",
    "planning",
    "ready",
    "ready_to_run",
    "running",
    "review_ready",
    "reviewing",
    "completed",
    "blocked",
    "archived",
]
ExportBundleStatus = Literal["draft", "published", "revoked", "expired"]
ExportBundleFormat = Literal["bundle_json", "report_markdown", "report_json", "report_csv"]
ShareBundleStatus = Literal["draft", "published", "revoked", "expired"]
SupportSnapshotStatus = Literal["generated"]
DecisionReviewStatus = Literal["draft", "in_review", "approved", "needs_revision"]
DecisionCommentAnchorKind = Literal["general", "decision_summary", "rationale", "evidence_view", "comparison"]


@dataclass(slots=True)
class WorkspaceMember:
    user_id: str
    role: WorkspaceRole
    joined_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class TenantWorkspace:
    workspace_id: str
    slug: str
    display_name: str
    region_code: str
    data_residency_region: str
    plan_tier: str
    status: WorkspaceStatus
    created_at: str
    settings: dict[str, Any] = field(default_factory=dict)
    members: list[WorkspaceMember] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class BillingAccount:
    workspace_id: str
    provider_name: str
    provider_customer_ref: str
    provider_subscription_ref: str
    price_book_id: str
    status: SubscriptionStatus
    seat_count: int
    renewal_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkspaceBrowserSession:
    session_id: str
    workspace_id: str
    user_id: str
    role: WorkspaceRole
    source_token: str | None
    created_at: str
    last_seen_at: str
    expires_at: str
    revoked_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class ValidationJob:
    job_id: str
    workspace_id: str
    brief_id: str
    requested_by_user_id: str
    panel_spec: PanelSpec
    provider_name: str
    status: JobStatus
    priority: JobPriority
    input_artifact_path: str
    output_run_path: str | None
    retry_count: int
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "panel_spec": self.panel_spec.to_dict(),
        }


@dataclass(slots=True)
class WorkspaceProject:
    project_id: str
    workspace_id: str
    slug: str
    name: str
    description: str
    created_by_user_id: str
    status: ProjectStatus
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkspaceStudy:
    study_id: str
    workspace_id: str
    project_id: str
    title: str
    created_by_user_id: str
    status: StudyStatus
    research_intent: str
    desired_output: str
    first_task: str
    artifact_refs: list[str]
    draft_plan: dict[str, Any]
    latest_job_id: str | None
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkspaceExportBundle:
    export_bundle_id: str
    workspace_id: str
    project_id: str
    study_id: str
    job_id: str
    run_id: str
    title: str
    status: ExportBundleStatus
    export_format: ExportBundleFormat
    created_by_user_id: str
    bundle_root: str
    manifest_path: str
    exported_files: list[dict[str, Any]]
    synthetic_boundary: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkspaceShareBundle:
    share_bundle_id: str
    workspace_id: str
    export_bundle_id: str
    project_id: str
    study_id: str
    job_id: str
    run_id: str
    title: str
    status: ShareBundleStatus
    share_key: str
    public_path: str
    share_root: str
    share_payload_path: str
    created_by_user_id: str
    synthetic_boundary: str
    published_at: str
    expires_at: str | None
    revoked_at: str | None
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkspaceSupportSnapshot:
    support_snapshot_id: str
    workspace_id: str
    project_id: str | None
    study_id: str | None
    job_id: str | None
    run_id: str | None
    title: str
    status: SupportSnapshotStatus
    summary: str
    support_root: str
    snapshot_path: str
    created_by_user_id: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkspaceEvidenceView:
    evidence_view_id: str
    workspace_id: str
    project_id: str
    study_id: str
    job_id: str | None
    run_id: str | None
    title: str
    note: str
    query_text: str
    active_family: str
    sort_by: str
    selected_result_id: str | None
    selected_replay_step_id: str | None
    selected_comparison_run_id: str | None
    payload_path: str
    created_by_user_id: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkspaceDecisionLog:
    decision_log_id: str
    workspace_id: str
    project_id: str
    study_id: str
    job_id: str | None
    run_id: str | None
    evidence_view_id: str | None
    title: str
    decision_summary: str
    rationale: str
    selected_result_id: str | None
    selected_comparison_run_id: str | None
    payload_path: str
    created_by_user_id: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkspaceStudyReport:
    study_report_id: str
    workspace_id: str
    project_id: str
    study_id: str
    title: str
    status: str
    included_job_ids: list[str]
    included_run_ids: list[str]
    included_plan_revision_ids: list[str]
    stable_patterns: list[dict[str, Any]]
    divergent_signals: list[dict[str, Any]]
    key_objections: list[dict[str, Any]]
    trust_gaps: list[dict[str, Any]]
    adoption_barriers: list[dict[str, Any]]
    prototype_confusions: list[dict[str, Any]]
    contradictions: list[dict[str, Any]]
    human_validation_gaps: list[dict[str, Any]]
    payload_path: str
    created_by_user_id: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class WorkspaceDecisionComment:
    decision_comment_id: str
    workspace_id: str
    project_id: str
    study_id: str
    decision_log_id: str
    parent_comment_id: str | None
    anchor_kind: DecisionCommentAnchorKind
    body: str
    created_by_user_id: str
    created_at: str
    updated_at: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AuditEvent:
    audit_event_id: str
    workspace_id: str
    actor_user_id: str
    actor_role: str
    action: str
    target_type: str
    target_id: str
    event_payload: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PersonaCatalogEntry:
    catalog_persona_id: str
    synthetic_user_id: str
    scope: CatalogScope
    locale_pack: str
    market_tags: list[str]
    panel_role: str
    seed_version: str
    generation_version: str
    audit_version: str
    quality_score: float
    uniqueness_score: float
    active: bool
    artifact_path: str
    created_at: str
    last_reviewed_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SimilarityDecision:
    source_persona_id: str
    target_persona_id: str
    similarity_score: float
    decision: SimilarityDecisionType
    rationale: str
    reviewed_at: str
    reviewer_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class MarketDistributionConfig:
    config_version: str
    market_id: str
    display_name: str
    default_locale: str
    target_population: str
    weights: dict[str, dict[str, float]]
    quota_rules: list[dict[str, Any]] = field(default_factory=list)
    exclusion_rules: list[dict[str, Any]] = field(default_factory=list)
    overlays: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
