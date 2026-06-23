from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


@dataclass(slots=True)
class PersonaSeed:
    seed_id: str
    panel_role: str
    age_band: str
    location_type: str
    household_structure: str
    occupation_band: str
    income_band: str
    education_band: str
    language: list[str]
    device_environment: str
    payment_environment: str
    schedule_pressure: str
    budget_flexibility: str
    caregiving_load: str
    trust_threshold: str
    switching_cost_level: str
    privacy_risk_tolerance: str
    digital_literacy_ceiling: str
    locale_pack: str = ""
    occupation_title: str = ""
    life_stage: str = ""
    purchase_authority_type: str = ""
    employment_stability: str = ""
    workflow_maturity: str = ""
    decision_speed: str = ""
    proof_threshold: str = ""
    cash_flow_volatility: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SyntheticUser:
    basic_identity: dict[str, Any]
    personality_belief: dict[str, Any]
    technology_profile: dict[str, Any]
    economic_profile: dict[str, Any]
    values: dict[str, Any]
    life_story: dict[str, Any]
    behavior_profile: dict[str, Any]
    problem_context: dict[str, Any]
    sensitive_reality_layer: dict[str, Any]
    audit_evidence_layer: dict[str, Any]
    canonical_biography: dict[str, Any] = field(default_factory=dict)
    childhood_environment: dict[str, Any] = field(default_factory=dict)
    domain_fit: dict[str, Any] = field(default_factory=dict)
    pricing_logic: dict[str, Any] = field(default_factory=dict)
    workflow_adoption_model: dict[str, Any] = field(default_factory=dict)
    product_reaction_rules: dict[str, Any] = field(default_factory=dict)
    identity_and_inclusion_reaction: dict[str, Any] = field(default_factory=dict)
    cross_domain_product_reaction_model: dict[str, Any] = field(default_factory=dict)
    interests_and_hobbies: dict[str, Any] = field(default_factory=dict)
    media_and_content_diet: dict[str, Any] = field(default_factory=dict)
    daily_micro_behaviours: dict[str, Any] = field(default_factory=dict)
    social_circle_and_communities: dict[str, Any] = field(default_factory=dict)
    taste_and_aesthetic_preferences: dict[str, Any] = field(default_factory=dict)
    spending_and_leisure_patterns: dict[str, Any] = field(default_factory=dict)
    personal_environment: dict[str, Any] = field(default_factory=dict)
    emotional_regulation_style: dict[str, Any] = field(default_factory=dict)
    hidden_habits: dict[str, Any] = field(default_factory=dict)
    identity_symbols: dict[str, Any] = field(default_factory=dict)
    cultural_texture: dict[str, Any] = field(default_factory=dict)
    product_discovery_paths: dict[str, Any] = field(default_factory=dict)
    objection_language_style: dict[str, Any] = field(default_factory=dict)
    contradiction_map: list[dict[str, Any]] = field(default_factory=list)
    deep_research_notes: dict[str, Any] = field(default_factory=dict)
    panel_role_profile: dict[str, Any] = field(default_factory=dict)
    local_grounding_layer: dict[str, Any] = field(default_factory=dict)
    sensitive_scenario_reactions: dict[str, Any] = field(default_factory=dict)
    sensitive_scenario_salience: dict[str, Any] = field(default_factory=dict)
    persona_voiceprint: dict[str, Any] = field(default_factory=dict)
    identity_language: dict[str, Any] = field(default_factory=dict)
    small_business_context: dict[str, Any] = field(default_factory=dict)
    human_difference_axes: dict[str, Any] = field(default_factory=dict)
    banking_context: dict[str, Any] = field(default_factory=dict)
    consistency_exceptions: list[dict[str, Any]] = field(default_factory=list)
    generation_status: dict[str, Any] = field(default_factory=dict)
    extensions: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def synthetic_user_id(self) -> str:
        return str(self.basic_identity["synthetic_user_id"])


@dataclass(slots=True)
class PersonaSkill:
    skill_version: str
    seed: PersonaSeed
    profile: SyntheticUser
    decision_policy: dict[str, Any]
    response_style: dict[str, Any]
    narrative: str
    audit: dict[str, Any]

    def to_audit_payload(self) -> dict[str, Any]:
        return {
            "skill_version": self.skill_version,
            "seed": self.seed.to_dict(),
            "decision_policy": self.decision_policy,
            "response_style": self.response_style,
            "audit": self.audit,
        }


@dataclass(slots=True)
class FounderBrief:
    brief_id: str
    project_name: str
    problem_statement: str
    target_market: str
    offered_solution: str
    validation_goal: str
    pricing_hypothesis: str = ""
    landing_page_text: str = ""
    mvp_scope: str = ""
    concierge_mvp_idea: str = ""
    assumptions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    known_risks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PanelSpec:
    panel_type: str
    sample_size: int
    random_seed: int | None = None
    filters: dict[str, Any] = field(default_factory=dict)
    preset_name: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class PersonaResponse:
    synthetic_user_id: str
    panel_role: str
    protocol_id: str
    first_impression: str
    pain_relevance: str
    solution_attractiveness: str
    trust_concern: str
    pricing_reaction: str
    likely_objection: str
    what_would_make_them_try: str
    what_would_make_them_reject: str
    sensitive_concern_if_any: str
    scorecard: dict[str, int]
    themes: dict[str, str]
    response_version: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AuditFinding:
    category: str
    severity: str
    observation: str
    evidence_refs: list[str]
    recommended_validation_question: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SkepticFinding:
    finding_id: str
    severity: str
    title: str
    observation: str
    evidence_refs: list[str]
    recommended_validation_question: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SkepticReview:
    review_version: str
    summary: str
    challenged_assumptions: list[SkepticFinding]

    def to_dict(self) -> dict[str, Any]:
        return {
            "review_version": self.review_version,
            "summary": self.summary,
            "challenged_assumptions": [finding.to_dict() for finding in self.challenged_assumptions],
        }


@dataclass(slots=True)
class ValidationRun:
    run_id: str
    brief_id: str
    panel_spec: PanelSpec
    selected_persona_ids: list[str]
    prompt_version: str
    model_version: str
    started_at: str
    finished_at: str | None
    token_estimate: int | None
    cost_estimate: float | None
    status: str
    successful_response_count: int
    failed_response_count: int
    error_count: int
    failure_reasons: list[str]
    artifact_paths: list[str]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
