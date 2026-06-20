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

