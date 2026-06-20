from __future__ import annotations

import copy
import hashlib
import json
import random
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable, Protocol

from ai_validation_swarm.domain.models import PersonaSkill
from ai_validation_swarm.personas.generator import build_seed, enrich_seed
from ai_validation_swarm.personas.v2 import prompt_path
from ai_validation_swarm.personas.v3_1 import build_diversity_report_v3_1
from ai_validation_swarm.personas.v3_1_2 import RAW_ENUM_TOKENS, _render_artifacts
from ai_validation_swarm.personas.v3_2_sections import (
    DEFAULT_V3_2_REGISTRY,
    PersonaSectionRegistry,
    PersonaSectionSpec,
)
from ai_validation_swarm.providers.openai_client import OpenAIProviderConfig, OpenAIResponsesClient
from ai_validation_swarm.personas.validator import ensure_valid_persona_artifact
from ai_validation_swarm.storage.files import ensure_dir, load_persona, write_json


GENERATOR_VERSION = "persona-generator/v3.2"
BASE_PROMPT_VERSION = "persona-synthesis/v3_2.md"
AUDIT_PROMPT_VERSION = "quality-auditor/v3_2.md"
REVISION_PROMPT_VERSION = "persona-revision/v3_2.md"
PROTECTED_PROFILE_PATHS = (
    "basic_identity",
    "economic_profile.purchase_authority_type",
    "economic_profile.employment_stability",
    "economic_profile.cash_flow_volatility",
    "economic_profile.switching_cost",
)


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _stable_hash(payload: Any) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(slots=True)
class PersonaSynthesisRequest:
    synthetic_user_id: str
    seed: dict[str, Any]
    identity_anchors: dict[str, Any]
    creative_brief: dict[str, Any]
    sections: list[PersonaSectionSpec]
    prompt_texts: dict[str, str]
    random_seed: int
    attempt: int = 1
    revision_findings: list[str] = field(default_factory=list)

    def trace_payload(self) -> dict[str, Any]:
        return {
            "synthetic_user_id": self.synthetic_user_id,
            "seed": self.seed,
            "identity_anchors": self.identity_anchors,
            "creative_brief": self.creative_brief,
            "sections": [section.to_dict() for section in self.sections],
            "random_seed": self.random_seed,
            "attempt": self.attempt,
            "revision_findings": self.revision_findings,
        }


@dataclass(slots=True)
class PersonaSynthesisResult:
    sections: dict[str, dict[str, Any]]
    decision_policy: dict[str, Any]
    response_style: dict[str, Any]
    narrative: str
    rationale: str
    provider: str
    model: str
    prompt_versions: list[str]
    raw_metadata: dict[str, Any] = field(default_factory=dict)


class PersonaSynthesisAdapter(Protocol):
    def synthesize(self, request: PersonaSynthesisRequest) -> PersonaSynthesisResult: ...


class RecordedV32SynthesisAdapter:
    """Imports a previously recorded LLM result through the normal V3.2 gates."""

    def __init__(self, payload_dir: Path, *, provider: str, model: str) -> None:
        self.payload_dir = payload_dir
        self.provider = provider
        self.model = model

    def synthesize(self, request: PersonaSynthesisRequest) -> PersonaSynthesisResult:
        path = self.payload_dir / f"{request.synthetic_user_id}.json"
        if not path.exists():
            raise ValueError(f"Recorded V3.2 synthesis payload not found: {path}")
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"Recorded V3.2 synthesis payload must be an object: {path}")
        return PersonaSynthesisResult(
            sections=dict(payload.get("sections", {})),
            decision_policy=dict(payload.get("decision_policy", {})),
            response_style=dict(payload.get("response_style", {})),
            narrative=str(payload.get("narrative", "")).strip(),
            rationale=str(payload.get("rationale", "")).strip(),
            provider=self.provider,
            model=self.model,
            prompt_versions=list(payload.get("prompt_versions", [BASE_PROMPT_VERSION])),
            raw_metadata={
                "recorded_payload": str(path),
                "recorded_payload_sha256": _stable_hash(payload),
                "live_transport": False,
            },
        )


def build_v3_2_output_schema(sections: list[PersonaSectionSpec]) -> dict[str, Any]:
    section_properties: dict[str, Any] = {}
    required_sections: list[str] = []
    for section in sections:
        target_properties = {
            target: ({"type": "array"} if target == "contradiction_map" else {"type": "object"})
            for target in section.targets
        }
        section_properties[section.name] = {
            "type": "object",
            "additionalProperties": False,
            "required": list(section.targets),
            "properties": target_properties,
        }
        if section.required:
            required_sections.append(section.name)
    return {
        "type": "object",
        "additionalProperties": False,
        "required": ["sections", "decision_policy", "response_style", "narrative", "rationale"],
        "properties": {
            "sections": {
                "type": "object",
                "additionalProperties": False,
                "required": required_sections,
                "properties": section_properties,
            },
            "decision_policy": {"type": "object"},
            "response_style": {"type": "object"},
            "narrative": {"type": "string"},
            "rationale": {"type": "string"},
        },
    }


class OpenAIV32SynthesisAdapter:
    def __init__(self, client: OpenAIResponsesClient, config: OpenAIProviderConfig) -> None:
        self.client = client
        self.config = config

    def synthesize(self, request: PersonaSynthesisRequest) -> PersonaSynthesisResult:
        section_instructions = []
        for section in request.sections:
            section_instructions.append(
                {
                    "name": section.name,
                    "targets": list(section.targets),
                    "description": section.description,
                    "prompt_version": section.prompt_version,
                    "prompt": request.prompt_texts[section.prompt_version],
                }
            )
        user_payload = {
            "task": "Generate one complete V3.2 persona directly from constraints.",
            "identity_anchors": request.identity_anchors,
            "constraint_seed": request.seed,
            "creative_brief": request.creative_brief,
            "section_instructions": section_instructions,
            "revision_findings": request.revision_findings,
            "random_seed": request.random_seed,
            "attempt": request.attempt,
        }
        payload = self.client.create_json_response(
            system_prompt=request.prompt_texts[BASE_PROMPT_VERSION],
            user_prompt=json.dumps(user_payload, ensure_ascii=False, indent=2),
            output_schema=build_v3_2_output_schema(request.sections),
            # V3.2 section payloads are validated by the persona contract after
            # generation; their nested fields are intentionally extensible and
            # are not valid strict Structured Outputs schemas.
            use_transport_output_schema=self.config.transport != "codex_sdk_node",
        )
        return PersonaSynthesisResult(
            sections=dict(payload.get("sections", {})),
            decision_policy=dict(payload.get("decision_policy", {})),
            response_style=dict(payload.get("response_style", {})),
            narrative=str(payload.get("narrative", "")).strip(),
            rationale=str(payload.get("rationale", "")).strip(),
            provider="codex" if self.config.transport.startswith("codex") else "openai",
            model=self.config.model,
            prompt_versions=[BASE_PROMPT_VERSION, *[section.prompt_version for section in request.sections]],
            raw_metadata={
                "profile": self.config.profile,
                "reasoning_effort": self.config.model_reasoning_effort,
                "transport": self.config.transport,
                "auth_source": self.config.auth_source,
            },
        )


class SectionBatchedV32SynthesisAdapter:
    """Runs the registered sections in smaller LLM calls and merges one result."""

    def __init__(
        self,
        adapter: PersonaSynthesisAdapter,
        *,
        batch_size: int = 2,
        cache_dir: Path | None = None,
        progress_writer: Callable[[str], None] | None = None,
    ) -> None:
        if batch_size < 1:
            raise ValueError("V3.2 section batch size must be at least 1.")
        self.adapter = adapter
        self.batch_size = batch_size
        self.cache_dir = cache_dir
        self.progress_writer = progress_writer

    def _progress(self, message: str) -> None:
        if self.progress_writer is not None:
            self.progress_writer(message)

    def _cache_identity(self) -> dict[str, Any]:
        """Keep cached LLM results isolated by provider configuration."""
        config = getattr(self.adapter, "config", None)
        return {
            "adapter": f"{type(self.adapter).__module__}.{type(self.adapter).__qualname__}",
            "provider": getattr(config, "provider", ""),
            "model": getattr(config, "model", ""),
            "profile": getattr(config, "profile", ""),
            "transport": getattr(config, "transport", ""),
            "reasoning_effort": getattr(config, "model_reasoning_effort", ""),
        }

    @staticmethod
    def _covers_requested_sections(
        result: PersonaSynthesisResult,
        request: PersonaSynthesisRequest,
    ) -> bool:
        for section in request.sections:
            payload = result.sections.get(section.name)
            if not isinstance(payload, dict):
                return False
            for target in section.targets:
                value = payload.get(target)
                expected = list if target == "contradiction_map" else dict
                if not isinstance(value, expected) or not value:
                    return False
        return True

    def _cached_result(
        self,
        request: PersonaSynthesisRequest,
        batch_names: list[str],
    ) -> tuple[Path | None, str, PersonaSynthesisResult | None]:
        request_hash = _stable_hash({
            "request": request.trace_payload(),
            "cache_identity": self._cache_identity(),
        })
        if self.cache_dir is None:
            return None, request_hash, None
        persona_dir = self.cache_dir / request.synthetic_user_id
        ensure_dir(persona_dir)
        cache_path = persona_dir / f"attempt_{request.attempt}_{'_'.join(batch_names)}.json"
        if not cache_path.exists():
            return cache_path, request_hash, None
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        if payload.get("request_sha256") != request_hash:
            return cache_path, request_hash, None
        result = PersonaSynthesisResult(
            sections=dict(payload["result"].get("sections", {})),
            decision_policy=dict(payload["result"].get("decision_policy", {})),
            response_style=dict(payload["result"].get("response_style", {})),
            narrative=str(payload["result"].get("narrative", "")),
            rationale=str(payload["result"].get("rationale", "")),
            provider=str(payload["result"].get("provider", "")),
            model=str(payload["result"].get("model", "")),
            prompt_versions=list(payload["result"].get("prompt_versions", [])),
            raw_metadata=dict(payload["result"].get("raw_metadata", {})),
        )
        if not self._covers_requested_sections(result, request):
            return cache_path, request_hash, None
        return cache_path, request_hash, result

    @staticmethod
    def _write_cached_result(path: Path, request_hash: str, result: PersonaSynthesisResult) -> None:
        write_json(path, {
            "request_sha256": request_hash,
            "result": {
                "sections": result.sections,
                "decision_policy": result.decision_policy,
                "response_style": result.response_style,
                "narrative": result.narrative,
                "rationale": result.rationale,
                "provider": result.provider,
                "model": result.model,
                "prompt_versions": result.prompt_versions,
                "raw_metadata": result.raw_metadata,
            },
        })

    def synthesize(self, request: PersonaSynthesisRequest) -> PersonaSynthesisResult:
        merged_sections: dict[str, dict[str, Any]] = {}
        prompt_versions: list[str] = []
        batch_metadata: list[dict[str, Any]] = []
        summaries: list[str] = []
        decision_policy: dict[str, Any] = {}
        response_style: dict[str, Any] = {}
        narratives: list[str] = []
        rationales: list[str] = []
        provider = ""
        model = ""

        for batch_index in range(0, len(request.sections), self.batch_size):
            batch = request.sections[batch_index:batch_index + self.batch_size]
            batch_brief = copy.deepcopy(request.creative_brief)
            if summaries:
                batch_brief["prior_batch_summaries"] = summaries[-2:]
            batch_request = PersonaSynthesisRequest(
                synthetic_user_id=request.synthetic_user_id,
                seed=copy.deepcopy(request.seed),
                identity_anchors=copy.deepcopy(request.identity_anchors),
                creative_brief=batch_brief,
                sections=batch,
                prompt_texts=request.prompt_texts,
                random_seed=request.random_seed + batch_index,
                attempt=request.attempt,
                revision_findings=list(request.revision_findings),
            )
            batch_names = [section.name for section in batch]
            self._progress(
                f"[v3.2] {request.synthetic_user_id} attempt {request.attempt} "
                f"batch {batch_index // self.batch_size + 1}/{(len(request.sections) + self.batch_size - 1) // self.batch_size} "
                f"sections={', '.join(batch_names)}"
            )
            cache_path, request_hash, result = self._cached_result(batch_request, batch_names)
            if result is None:
                started_at = time.perf_counter()
                result = self.adapter.synthesize(batch_request)
                elapsed = time.perf_counter() - started_at
                self._progress(
                    f"[v3.2] {request.synthetic_user_id} attempt {request.attempt} "
                    f"finished sections={', '.join(batch_names)} in {elapsed:.1f}s"
                )
                if cache_path is not None and self._covers_requested_sections(result, batch_request):
                    self._write_cached_result(cache_path, request_hash, result)
                    self._progress(
                        f"[v3.2] {request.synthetic_user_id} cached sections={', '.join(batch_names)} -> {cache_path.name}"
                    )
            else:
                self._progress(
                    f"[v3.2] {request.synthetic_user_id} cache hit for sections={', '.join(batch_names)} -> "
                    f"{cache_path.name if cache_path is not None else '(memory)'}"
                )
            merged_sections.update(copy.deepcopy(result.sections))
            provider = result.provider
            model = result.model
            prompt_versions.extend(result.prompt_versions)
            if "behaviour_and_decisions" in batch_names or not decision_policy:
                decision_policy = copy.deepcopy(result.decision_policy)
            if "voiceprint" in batch_names or not response_style:
                response_style = copy.deepcopy(result.response_style)
            if result.narrative and result.narrative not in narratives:
                narratives.append(result.narrative)
                summaries.append(result.narrative)
            if result.rationale and result.rationale not in rationales:
                rationales.append(result.rationale)
            batch_metadata.append({
                "sections": batch_names,
                "metadata": result.raw_metadata,
            })

        return PersonaSynthesisResult(
            sections=merged_sections,
            decision_policy=decision_policy,
            response_style=response_style,
            narrative="\n\n".join(narratives),
            rationale="\n\n".join(rationales),
            provider=provider,
            model=model,
            prompt_versions=list(dict.fromkeys(prompt_versions)),
            raw_metadata={
                "section_batched": True,
                "batch_size": self.batch_size,
                "batch_count": len(batch_metadata),
                "batches": batch_metadata,
            },
        )


def _build_creative_brief(persona: PersonaSkill, random_seed: int) -> dict[str, Any]:
    seed = persona.seed
    identity = persona.profile.basic_identity
    tensions = [
        f"Balance {seed.schedule_pressure} schedule pressure with a life that is not defined only by work.",
        f"Make {seed.trust_threshold.replace('_', ' ')} a contextual tendency, not a universal reaction.",
        "Include at least one preference that does not follow directly from demographics.",
        "Include ordinary inconsistency between stated intention and actual behaviour.",
    ]
    return {
        "identity_constraints": identity,
        "life_constraints": {
            "life_stage": seed.life_stage,
            "household_structure": seed.household_structure,
            "caregiving_load": seed.caregiving_load,
            "employment_stability": seed.employment_stability,
        },
        "economic_constraints": {
            "income_band": seed.income_band,
            "budget_flexibility": seed.budget_flexibility,
            "purchase_authority_type": seed.purchase_authority_type,
            "cash_flow_volatility": seed.cash_flow_volatility,
        },
        "technology_constraints": {
            "device_environment": seed.device_environment,
            "digital_literacy_ceiling": seed.digital_literacy_ceiling,
            "privacy_risk_tolerance": seed.privacy_risk_tolerance,
        },
        "behavioural_tensions": tensions,
        "generation_guidance": {
            "ordinary_life_ratio": "mostly ordinary, with no forced trauma or hero arc",
            "demographic_rule": "demographics constrain context but do not determine personality",
            "product_research_rule": "connect details to behaviour without making every scene about software",
            "random_seed": random_seed,
        },
    }


def load_v3_2_prompt_texts(sections: list[PersonaSectionSpec]) -> dict[str, str]:
    versions = [BASE_PROMPT_VERSION, AUDIT_PROMPT_VERSION, REVISION_PROMPT_VERSION]
    versions.extend(section.prompt_version for section in sections)
    return {
        version: prompt_path(version).read_text(encoding="utf-8").strip()
        for version in dict.fromkeys(versions)
    }


def _validate_result(result: PersonaSynthesisResult, sections: list[PersonaSectionSpec]) -> list[str]:
    findings: list[str] = []
    for section in sections:
        payload = result.sections.get(section.name)
        if not isinstance(payload, dict):
            if section.required:
                findings.append(f"missing_section:{section.name}")
            continue
        for target in section.targets:
            value = payload.get(target)
            expected = list if target == "contradiction_map" else dict
            if not isinstance(value, expected) or not value:
                findings.append(f"missing_or_empty_target:{section.name}.{target}")

    biography = result.sections.get("biography", {}).get("canonical_biography", {})
    childhood = result.sections.get("childhood_environment", {}).get("childhood_environment", {})
    childhood_fields = (
        "family_structure_and_stability",
        "caregiver_dynamics",
        "emotional_climate",
        "money_environment",
        "authority_and_rules",
        "conflict_repair_pattern",
        "responsibility_expectations",
        "belonging_and_identity",
        "early_technology_environment",
        "ordinary_childhood_scenes",
        "beliefs_carried_forward",
        "adult_decision_links",
        "uncertainty_notes",
    )
    if childhood:
        missing_childhood = [key for key in childhood_fields if not childhood.get(key)]
        if missing_childhood:
            findings.append(f"childhood_environment_missing:{','.join(missing_childhood)}")
        childhood_scenes = childhood.get("ordinary_childhood_scenes", [])
        if len(childhood_scenes) < 3:
            findings.append("childhood_environment_requires_three_scenes")
        for index, scene in enumerate(childhood_scenes):
            required = ("age", "setting", "scene", "lesson_at_the_time", "adult_echo")
            if any(not scene.get(key) for key in required):
                findings.append(f"childhood_scene_{index}_missing_fields")
        adult_links = childhood.get("adult_decision_links", [])
        if len(adult_links) < 4:
            findings.append("childhood_environment_requires_four_adult_links")
        for index, link in enumerate(adult_links):
            required = (
                "childhood_pattern",
                "adult_value_or_assumption",
                "product_judgment_effect",
                "limits_of_inference",
            )
            if any(not link.get(key) for key in required):
                findings.append(f"childhood_adult_link_{index}_missing_fields")
    chapters = biography.get("decade_timeline", [])
    scenes = [item for item in chapters if str(item.get("specific_scene", "")).strip()]
    if len(scenes) < 3:
        findings.append("biography_requires_at_least_three_specific_scenes")
    required_chapter_fields = (
        "age_range",
        "chapter_title",
        "life_context",
        "specific_scene",
        "product_relevant_memory",
        "social_or_relationship_context",
        "money_or_effort_tradeoff",
        "beliefs_formed",
        "current_reaction_link",
    )
    for index, chapter in enumerate(chapters):
        missing = [key for key in required_chapter_fields if not chapter.get(key)]
        if missing:
            findings.append(f"biography_chapter_{index}_missing:{','.join(missing)}")
    for index, event in enumerate(biography.get("formative_events", [])):
        if not event.get("age_range") or not (event.get("event_summary") or event.get("event")) or not event.get("impact"):
            findings.append(f"formative_event_{index}_missing_render_fields")
    for index, scene in enumerate(biography.get("non_work_purchase_scenes", [])):
        required = ("scene_title", "decision_context", "trust_or_price_lesson", "current_product_research_impact")
        if any(not scene.get(key) for key in required):
            findings.append(f"non_work_purchase_scene_{index}_missing_render_fields")

    hobbies = result.sections.get("lifestyle_and_hobbies", {}).get("interests_and_hobbies", {})
    if hobbies:
        for key in ("primary_interests", "low_energy_hobbies", "aspirational_hobbies", "interest_depth"):
            if not hobbies.get(key):
                findings.append(f"hobby_depth_missing:{key}")

    prose_payload = {
        "biography": result.sections.get("biography", {}),
        "voiceprint": result.sections.get("voiceprint", {}),
        "product_reactions": result.sections.get("technology_and_products", {}).get(
            "cross_domain_product_reaction_model", {}
        ),
    }
    serialized = json.dumps(prose_payload, ensure_ascii=False)
    leaked = sorted(token for token in RAW_ENUM_TOKENS if token in serialized)
    if leaked:
        findings.append(f"enum_leakage:{','.join(leaked)}")
    if not result.decision_policy:
        findings.append("missing_decision_policy")
    if not result.response_style:
        findings.append("missing_response_style")
    if not result.narrative:
        findings.append("missing_narrative")
    runtime_required_fields = {
        ("behaviour_and_decisions", "values"): ("fears", "aspirations"),
        ("biography", "life_story"): ("frustrations",),
        ("behaviour_and_decisions", "behavior_profile"): ("buying_behavior", "decision_blockers"),
        ("behaviour_and_decisions", "problem_context"): ("active_pain_points", "willingness_to_pay"),
        ("sensitive_scenarios", "sensitive_reality_layer"): ("fairness_and_inclusion_profile",),
    }
    for (section_name, target), fields in runtime_required_fields.items():
        payload = result.sections.get(section_name, {}).get(target, {})
        missing = [field for field in fields if not payload.get(field)]
        if missing:
            findings.append(f"runtime_contract_missing:{target}.{','.join(missing)}")
    for field in ("adoption_style", "proof_requirements"):
        if not result.decision_policy.get(field):
            findings.append(f"runtime_contract_missing:decision_policy.{field}")
    for field in ("articulation_level", "directness", "detail_tendency"):
        if not result.response_style.get(field):
            findings.append(f"runtime_contract_missing:response_style.{field}")
    return findings


def _apply_result(persona: PersonaSkill, result: PersonaSynthesisResult, sections: list[PersonaSectionSpec]) -> PersonaSkill:
    generated = copy.deepcopy(persona)
    fixed_economic = copy.deepcopy(persona.profile.economic_profile)
    for section in sections:
        payload = result.sections.get(section.name, {})
        for target in section.targets:
            value = copy.deepcopy(payload[target])
            if target.startswith("extensions."):
                generated.profile.extensions[target.split(".", 1)[1]] = value
            elif hasattr(generated.profile, target):
                setattr(generated.profile, target, value)
            else:
                generated.profile.extensions[target] = value
    for key in ("purchase_authority_type", "employment_stability", "cash_flow_volatility", "switching_cost"):
        generated.profile.economic_profile[key] = fixed_economic[key]
    generated.skill_version = "v3.2"
    generated.decision_policy = copy.deepcopy(result.decision_policy)
    generated.response_style = copy.deepcopy(result.response_style)
    generated.narrative = result.narrative
    generated.profile.audit_evidence_layer.update(
        {
            "persona_generation_method": "constraint_bounded_llm_direct_synthesis",
            "persona_version": "v3.2",
            "generator_version": GENERATOR_VERSION,
            "last_audited_at": datetime.now(UTC).date().isoformat(),
        }
    )
    return generated


def _build_constraint_report(persona: PersonaSkill, request: PersonaSynthesisRequest) -> dict[str, Any]:
    checks = {
        "basic_identity": persona.profile.basic_identity == request.identity_anchors,
        "purchase_authority_type": (
            persona.profile.economic_profile.get("purchase_authority_type")
            == request.seed.get("purchase_authority_type")
        ),
        "employment_stability": (
            persona.profile.economic_profile.get("employment_stability")
            == request.seed.get("employment_stability")
        ),
        "cash_flow_volatility": (
            persona.profile.economic_profile.get("cash_flow_volatility")
            == request.seed.get("cash_flow_volatility")
        ),
        "switching_cost": (
            persona.profile.economic_profile.get("switching_cost")
            == request.seed.get("switching_cost_level")
        ),
    }
    return {
        "status": "pass" if all(checks.values()) else "fail",
        "checks": checks,
        "protected_profile_paths": list(PROTECTED_PROFILE_PATHS),
    }


def _quality_audit(persona: PersonaSkill, findings: list[str], adapter_result: PersonaSynthesisResult) -> dict[str, Any]:
    hobbies = persona.profile.interests_and_hobbies
    return {
        "status": "pass" if not findings else "fail",
        "scores": {
            "structure_completeness": 5 if not findings else 3,
            "biography_depth": 4,
            "lived_scene_quality": 4,
            "local_grounding": 4,
            "product_reaction_readiness": 4,
            "sensitive_topic_readiness": 4,
            "voice_distinctiveness": 4,
            "lifestyle_depth": 4 if hobbies.get("interest_depth") else 2,
            "childhood_grounding": 4 if len(persona.profile.childhood_environment.get("ordinary_childhood_scenes", [])) >= 3 else 2,
            "overall": 4 if not findings else 2,
        },
        "strengths": [
            "The persona was synthesized directly from explicit constraints.",
            "Narrative sections are owned by the configured LLM adapter and retain generation provenance.",
            "Lifestyle details are represented as a registered section rather than renderer filler.",
        ],
        "weaknesses": [
            "A single generated persona cannot demonstrate corpus-level diversity.",
            "Local facts still require periodic reference-pack maintenance.",
            "Human review remains necessary for subtle cultural and lived-experience realism.",
        ],
        "required_improvements": [
            "Evaluate section quality over a larger generated corpus.",
            "Add retrieval-backed local context packs before broad geographic expansion.",
            "Calibrate audit scoring against reviewed examples rather than self-assessment alone.",
        ],
        "findings": findings,
        "auditor_mode": "deterministic_gate_with_llm_ready_prompt",
        "generation_rationale": adapter_result.rationale,
        "human_review_needed": True,
    }


def _childhood_markdown(persona: PersonaSkill) -> str:
    childhood = persona.profile.childhood_environment
    lines = [
        "## Childhood Environment & Foundations",
        "",
        f"Family structure and stability: {childhood.get('family_structure_and_stability', '')}",
        f"Caregiver dynamics: {childhood.get('caregiver_dynamics', '')}",
        f"Emotional climate: {childhood.get('emotional_climate', '')}",
        f"Money environment: {childhood.get('money_environment', '')}",
        f"Authority and rules: {childhood.get('authority_and_rules', '')}",
        f"Conflict and repair: {childhood.get('conflict_repair_pattern', '')}",
        f"Early responsibility: {childhood.get('responsibility_expectations', '')}",
        f"Belonging and identity: {childhood.get('belonging_and_identity', '')}",
        f"Early technology environment: {childhood.get('early_technology_environment', '')}",
        "",
        "### Ordinary Childhood Scenes",
        "",
    ]
    for scene in childhood.get("ordinary_childhood_scenes", []):
        lines.extend(
            [
                f"- Age {scene.get('age', '')}, {scene.get('setting', '')}: {scene.get('scene', '')}",
                f"  Early lesson: {scene.get('lesson_at_the_time', '')}",
                f"  Adult echo: {scene.get('adult_echo', '')}",
            ]
        )
    lines.extend(["", "### Childhood-to-Adult Decision Links", ""])
    for link in childhood.get("adult_decision_links", []):
        lines.extend(
            [
                f"- {link.get('childhood_pattern', '')}",
                f"  Adult value or assumption: {link.get('adult_value_or_assumption', '')}",
                f"  Product judgment effect: {link.get('product_judgment_effect', '')}",
                f"  Inference boundary: {link.get('limits_of_inference', '')}",
            ]
        )
    lines.extend(
        [
            "",
            f"Uncertainty note: {childhood.get('uncertainty_notes', '')}",
            "",
        ]
    )
    return "\n".join(lines)


def _childhood_runtime_markdown(persona: PersonaSkill) -> str:
    childhood = persona.profile.childhood_environment
    lines = [
        "## Childhood Foundations",
        "",
        f"Environment: {childhood.get('family_structure_and_stability', '')}",
        f"Early emotional and authority pattern: {childhood.get('emotional_climate', '')} {childhood.get('authority_and_rules', '')}",
        f"Money and responsibility pattern: {childhood.get('money_environment', '')} {childhood.get('responsibility_expectations', '')}",
        "",
        "Adult decision echoes:",
    ]
    for link in childhood.get("adult_decision_links", [])[:4]:
        lines.append(
            f"- {link.get('adult_value_or_assumption', '')} Product effect: {link.get('product_judgment_effect', '')} "
            f"Boundary: {link.get('limits_of_inference', '')}"
        )
    return "\n".join(lines).strip() + "\n"


def _insert_markdown_section(text: str, marker: str, section: str) -> str:
    if marker not in text:
        return text.rstrip() + "\n\n" + section.rstrip() + "\n"
    return text.replace(marker, section.rstrip() + "\n\n" + marker, 1)


def _write_v3_2_persona(
    persona: PersonaSkill,
    *,
    output_dir: Path,
    registry: PersonaSectionRegistry,
    sections: list[PersonaSectionSpec],
    result: PersonaSynthesisResult,
    request: PersonaSynthesisRequest,
    attempts: int,
    comparisons: list[PersonaSkill],
) -> Path:
    target_dir = output_dir / persona.profile.synthetic_user_id / "v3_2"
    ensure_dir(target_dir)
    rendered, _examples, _variants = _render_artifacts(persona)
    childhood_markdown = _childhood_markdown(persona)
    childhood_runtime_markdown = _childhood_runtime_markdown(persona)
    rendered["biography.md"] = _insert_markdown_section(
        rendered["biography.md"], "## 0-9", childhood_markdown
    )
    rendered["research_kernel.md"] = (
        rendered["research_kernel.md"].rstrip() + "\n\n" + childhood_runtime_markdown
    )
    rendered["persona.skill.md"] = _insert_markdown_section(
        rendered["persona.skill.md"], "## Decade Memory", childhood_runtime_markdown
    )
    duplicate_report = build_diversity_report_v3_1(persona, comparisons)
    duplicate_report["admission_policy"] = "report_only_unless_near_duplicate"
    duplicate_report["purpose"] = "duplicate detection and later panel composition, not forced persona uniqueness"
    quality_audit = _quality_audit(persona, [], result)
    constraint_report = _build_constraint_report(persona, request)
    if constraint_report["status"] != "pass":
        raise ValueError(f"Protected V3.2 constraints changed for {persona.profile.synthetic_user_id}.")
    generation_status = {
        "status": "accepted",
        "can_enter_library": True,
        "can_enter_validation_runner": True,
        "blocking_issues": [],
    }
    persona.profile.generation_status = generation_status
    persona.audit = {
        **persona.audit,
        "generator_version": GENERATOR_VERSION,
        "quality_audit": quality_audit,
        "generation_status": generation_status,
        "section_ownership": {section.name: section.owner for section in sections},
        "protected_profile_paths": list(PROTECTED_PROFILE_PATHS),
    }
    ensure_valid_persona_artifact(persona)
    generation_notes = {
        "seed_id": persona.seed.seed_id,
        "synthetic_user_id": persona.profile.synthetic_user_id,
        "generator_version": GENERATOR_VERSION,
        "generation_mode": "direct_constraint_bounded_llm_synthesis",
        "provider": result.provider,
        "model_used": result.model,
        "prompt_versions": result.prompt_versions,
        "random_seed": request.random_seed,
        "attempts": attempts,
        "generated_at": _timestamp(),
        "input_context_sha256": _stable_hash(request.trace_payload()),
        "section_payload_sha256": _stable_hash(result.sections),
        "adapter_metadata": result.raw_metadata,
        "human_review_needed": True,
    }
    approved_brief = request.creative_brief.get("approved_generation_brief")
    write_json(target_dir / "profile.json", persona.profile.to_dict())
    write_json(target_dir / "audit.json", persona.to_audit_payload())
    write_json(target_dir / "generation_notes.json", generation_notes)
    write_json(target_dir / "section_manifest.json", {"sections": registry.manifest(section.name for section in sections)})
    write_json(target_dir / "duplicate_report.json", duplicate_report)
    write_json(target_dir / "constraint_report.json", constraint_report)
    if isinstance(approved_brief, dict) and approved_brief:
        write_json(target_dir / "generation_brief.json", approved_brief)
    for filename, content in rendered.items():
        (target_dir / filename).write_text(content, encoding="utf-8")
    return target_dir


def generate_v3_2_personas(
    *,
    persona_ids: list[str],
    output_dir: Path,
    adapter: PersonaSynthesisAdapter,
    registry: PersonaSectionRegistry = DEFAULT_V3_2_REGISTRY,
    enabled_sections: list[str] | None = None,
    random_seed_offset: int = 0,
    max_attempts: int = 3,
    comparison_personas: list[PersonaSkill] | None = None,
    generation_briefs: dict[str, dict[str, Any]] | None = None,
    progress_writer: Callable[[str], None] | None = None,
) -> list[Path]:
    sections = registry.resolve_generation_sections(enabled_sections)
    prompt_texts = load_v3_2_prompt_texts(sections)
    written: list[Path] = []
    comparisons = list(comparison_personas or [])
    briefs = generation_briefs or {}
    for position, persona_id in enumerate(dict.fromkeys(persona_ids)):
        if not persona_id.startswith("su_") or not persona_id[3:].isdigit():
            raise ValueError(f"Invalid synthetic user ID: {persona_id}")
        index = int(persona_id[3:]) - 1
        random_seed = random_seed_offset + index
        rng = random.Random(random_seed)
        seed = build_seed(index=index, rng=rng)
        approved_brief = copy.deepcopy(briefs.get(persona_id, {}))
        seed_overrides = approved_brief.get("seed_overrides", {})
        if not isinstance(seed_overrides, dict):
            raise ValueError(f"seed_overrides must be an object for {persona_id}")
        unknown_seed_fields = sorted(set(seed_overrides) - set(seed.__dataclass_fields__))
        if unknown_seed_fields:
            raise ValueError(f"Unknown seed overrides for {persona_id}: {unknown_seed_fields}")
        for field_name, value in seed_overrides.items():
            setattr(seed, field_name, copy.deepcopy(value))
        baseline = enrich_seed(seed=seed, index=index, rng=rng)
        identity_overrides = approved_brief.get("identity_overrides", {})
        if not isinstance(identity_overrides, dict):
            raise ValueError(f"identity_overrides must be an object for {persona_id}")
        unknown_identity_fields = sorted(set(identity_overrides) - set(baseline.profile.basic_identity))
        if unknown_identity_fields:
            raise ValueError(f"Unknown identity overrides for {persona_id}: {unknown_identity_fields}")
        baseline.profile.basic_identity.update(copy.deepcopy(identity_overrides))
        baseline.profile.basic_identity["synthetic_user_id"] = persona_id
        creative_brief = _build_creative_brief(baseline, random_seed)
        if approved_brief:
            creative_brief["approved_generation_brief"] = approved_brief
        findings: list[str] = []
        final_result: PersonaSynthesisResult | None = None
        final_request: PersonaSynthesisRequest | None = None
        if progress_writer is not None:
            progress_writer(
                f"[v3.2] start {persona_id} seed={random_seed} sections={len(sections)} max_attempts={max_attempts}"
            )
        for attempt in range(1, max_attempts + 1):
            if progress_writer is not None:
                progress_writer(f"[v3.2] {persona_id} attempt {attempt} begin")
            request = PersonaSynthesisRequest(
                synthetic_user_id=persona_id,
                seed=seed.to_dict(),
                identity_anchors=copy.deepcopy(baseline.profile.basic_identity),
                creative_brief=creative_brief,
                sections=sections,
                prompt_texts=prompt_texts,
                random_seed=random_seed,
                attempt=attempt,
                revision_findings=findings,
            )
            result = adapter.synthesize(request)
            findings = _validate_result(result, sections)
            final_result = result
            final_request = request
            if progress_writer is not None:
                if findings:
                    progress_writer(
                        f"[v3.2] {persona_id} attempt {attempt} findings: {', '.join(findings)}"
                    )
                else:
                    progress_writer(f"[v3.2] {persona_id} attempt {attempt} passed validation")
            if not findings:
                break
        if final_result is None or final_request is None or findings:
            details = ", ".join(findings) or "adapter returned no result"
            if progress_writer is not None:
                progress_writer(f"[v3.2] {persona_id} failed: {details}")
            raise ValueError(f"V3.2 synthesis failed for {persona_id}: {details}")
        persona = _apply_result(baseline, final_result, sections)
        target = _write_v3_2_persona(
            persona,
            output_dir=output_dir,
            registry=registry,
            sections=sections,
            result=final_result,
            request=final_request,
            attempts=final_request.attempt,
            comparisons=[item for item in comparisons if item.profile.synthetic_user_id != persona_id],
        )
        written.append(target)
        if progress_writer is not None:
            progress_writer(f"[v3.2] wrote {persona_id} -> {target}")
        comparisons.append(persona)
    return written


def validate_v3_2_persona_folder(folder: Path) -> dict[str, Any]:
    required = {
        "profile.json",
        "audit.json",
        "generation_notes.json",
        "section_manifest.json",
        "duplicate_report.json",
        "constraint_report.json",
        "persona.md",
        "biography.md",
        "research_kernel.md",
        "persona.skill.md",
        "local_grounding.md",
        "sensitive_scenarios.md",
    }
    missing = sorted(filename for filename in required if not (folder / filename).exists())
    warnings: list[str] = []
    if not missing:
        profile = json.loads((folder / "profile.json").read_text(encoding="utf-8"))
        notes = json.loads((folder / "generation_notes.json").read_text(encoding="utf-8"))
        constraint_report = json.loads((folder / "constraint_report.json").read_text(encoding="utf-8"))
        if not profile.get("interests_and_hobbies"):
            warnings.append("Registered lifestyle_and_hobbies section produced no interests_and_hobbies payload.")
        if notes.get("generation_mode") != "direct_constraint_bounded_llm_synthesis":
            warnings.append("Persona was not produced by the V3.2 direct synthesis path.")
        if constraint_report.get("status") != "pass":
            warnings.append("One or more protected V3.2 constraints changed during synthesis.")
        try:
            load_persona(folder)
        except Exception as exc:
            warnings.append(f"Persona cannot be loaded by the runtime artifact contract: {exc}")
    return {"missing_fields": missing, "warnings": warnings, "valid": not missing and not warnings}
