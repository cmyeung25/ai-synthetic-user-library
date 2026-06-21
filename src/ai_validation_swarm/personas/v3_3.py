from __future__ import annotations

import copy
import json
import random
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

from ai_validation_swarm.domain.models import PersonaSkill
from ai_validation_swarm.personas.generator import build_seed, enrich_seed
from ai_validation_swarm.personas.v2 import prompt_path
from ai_validation_swarm.personas.v3_1 import build_diversity_report_v3_1
from ai_validation_swarm.personas.v3_1_2 import _render_artifacts
from ai_validation_swarm.personas.v3_2 import (
    BASE_PROMPT_VERSION as V32_BASE_PROMPT_VERSION,
    PersonaSectionRegistry,
    PersonaSectionSpec,
    PersonaSynthesisAdapter,
    PersonaSynthesisRequest,
    PersonaSynthesisResult,
    PROTECTED_PROFILE_PATHS,
    SectionBatchedV32SynthesisAdapter,
    _apply_result,
    _build_creative_brief,
    _build_constraint_report,
    _childhood_markdown,
    _childhood_runtime_markdown,
    _insert_markdown_section,
    _normalize_sections_payload,
    _quality_audit,
    _stable_hash,
    _timestamp,
    _validate_result,
    _prompt_fingerprints,
    build_v3_2_output_schema,
)
from ai_validation_swarm.personas.v3_2_sections import DEFAULT_V3_2_REGISTRY
from ai_validation_swarm.personas.validator import ensure_valid_persona_artifact
from ai_validation_swarm.providers.openai_client import OpenAIProviderConfig, OpenAIResponsesClient
from ai_validation_swarm.storage.files import ensure_dir, load_persona, write_json


GENERATOR_VERSION = "persona-generator/v3.3"
BASE_PROMPT_VERSION = "persona-synthesis/v3_3.md"
AUDIT_PROMPT_VERSION = "quality-auditor/v3_3.md"
REVISION_PROMPT_VERSION = "persona-revision/v3_3.md"

SECTION_FOCUS_GUIDANCE: dict[str, list[str]] = {
    "childhood_environment": [
        "Include at least 3 ordinary childhood scenes with concrete settings and adult echoes.",
        "Explain household dynamics, money norms, rules, repair patterns, and technology exposure.",
        "Add at least 4 adult decision links without claiming deterministic causality.",
    ],
    "biography": [
        "Write grounded decade chapters with specific scenes, product-relevant memories, and current reaction links.",
        "Include formative events, non-work purchase scenes, and lived routines rather than abstract summaries.",
        "Avoid stereotype shortcuts and raw enum leakage.",
    ],
    "behaviour_and_decisions": [
        "Make decision logic usable at runtime: blockers, proof requirements, buying behavior, willingness to try, willingness to pay.",
        "Differentiate curiosity, trial, payment, and longer-term adoption.",
    ],
    "economics_and_pricing": [
        "Explain spending trade-offs, purchase authority context, and pricing objections in local reality.",
        "Do not overwrite protected seed constraints.",
    ],
    "technology_and_products": [
        "Generate cross-domain product reactions with persona-specific first questions and objections.",
        "Avoid reusing generic workflow-skeptic phrasing unless it clearly fits the life story.",
    ],
    "local_grounding": [
        "Use city and market cues that affect trust, pricing, language choice, and discovery paths.",
        "Keep local detail specific but non-stereotyped.",
    ],
    "sensitive_scenarios": [
        "Write scenario-based reactions for privacy, identity disclosure, family assumptions, workplace visibility, finances, and wellbeing.",
        "Focus on trust, comfort, and disclosure control rather than identity labels alone.",
    ],
    "voiceprint": [
        "Give the persona a distinct speaking pattern, rejection style, and near-purchase question.",
        "Make voice specific enough that example responses do not sound interchangeable with other personas.",
    ],
    "lifestyle_and_hobbies": [
        "Generate interests with depth, ordinary routines, hidden habits, contradictions, and discovery behavior.",
        "Lifestyle detail must explain product reactions rather than act as filler.",
    ],
}


def _result_to_dict(result: PersonaSynthesisResult) -> dict[str, Any]:
    return {
        "sections": result.sections,
        "decision_policy": result.decision_policy,
        "response_style": result.response_style,
        "narrative": result.narrative,
        "rationale": result.rationale,
        "provider": result.provider,
        "model": result.model,
        "prompt_versions": result.prompt_versions,
        "raw_metadata": result.raw_metadata,
    }


def _result_from_dict(payload: dict[str, Any]) -> PersonaSynthesisResult:
    return PersonaSynthesisResult(
        sections=dict(payload.get("sections", {})),
        decision_policy=dict(payload.get("decision_policy", {})),
        response_style=dict(payload.get("response_style", {})),
        narrative=str(payload.get("narrative", "")),
        rationale=str(payload.get("rationale", "")),
        provider=str(payload.get("provider", "")),
        model=str(payload.get("model", "")),
        prompt_versions=list(payload.get("prompt_versions", [])),
        raw_metadata=dict(payload.get("raw_metadata", {})),
    )


def load_v3_3_prompt_texts(sections: list[PersonaSectionSpec]) -> dict[str, str]:
    versions = [BASE_PROMPT_VERSION, AUDIT_PROMPT_VERSION, REVISION_PROMPT_VERSION, V32_BASE_PROMPT_VERSION]
    versions.extend(section.prompt_version for section in sections)
    return {
        version: prompt_path(version).read_text(encoding="utf-8").strip()
        for version in dict.fromkeys(versions)
    }


class OpenAIV33SynthesisAdapter:
    def __init__(self, client: OpenAIResponsesClient, config: OpenAIProviderConfig) -> None:
        self.client = client
        self.config = config

    def synthesize(self, request: PersonaSynthesisRequest) -> PersonaSynthesisResult:
        system_prompt_version = (
            REVISION_PROMPT_VERSION
            if request.revision_findings
            else BASE_PROMPT_VERSION
        )
        section_instructions = []
        for section in request.sections:
            section_instructions.append(
                {
                    "name": section.name,
                    "targets": list(section.targets),
                    "description": section.description,
                    "prompt_version": section.prompt_version,
                    "focus_guidance": SECTION_FOCUS_GUIDANCE.get(section.name, []),
                }
            )
        user_payload = {
            "task": (
                "Generate one complete V3.3 persona JSON result."
                if not request.revision_findings
                else "Repair the missing or weak parts of one V3.3 persona JSON result without changing protected identity anchors."
            ),
            "identity_anchors": request.identity_anchors,
            "constraint_seed": request.seed,
            "creative_brief": request.creative_brief,
            "section_instructions": section_instructions,
            "revision_findings": request.revision_findings,
            "required_contract": {
                "sections": [section.name for section in request.sections],
                "must_return_decision_policy": True,
                "must_return_response_style": True,
                "must_return_narrative": True,
                "must_return_rationale": True,
                "forbidden": [
                    "raw enum leakage",
                    "demographic stereotype shortcuts",
                    "placeholder prose",
                    "empty objects",
                ],
            },
            "random_seed": request.random_seed,
            "attempt": request.attempt,
        }
        payload = self.client.create_json_response(
            system_prompt=request.prompt_texts[system_prompt_version],
            user_prompt=json.dumps(user_payload, ensure_ascii=False, indent=2),
            output_schema=build_v3_2_output_schema(request.sections),
            use_transport_output_schema=self.config.transport != "codex_sdk_node",
        )
        return PersonaSynthesisResult(
            sections=_normalize_sections_payload(payload, request.sections),
            decision_policy=dict(payload.get("decision_policy", {})),
            response_style=dict(payload.get("response_style", {})),
            narrative=str(payload.get("narrative", "")).strip(),
            rationale=str(payload.get("rationale", "")).strip(),
            provider="codex" if self.config.transport.startswith("codex") else "openai",
            model=self.config.model,
            prompt_versions=[system_prompt_version, *[section.prompt_version for section in request.sections]],
            raw_metadata={
                "profile": self.config.profile,
                "reasoning_effort": self.config.model_reasoning_effort,
                "transport": self.config.transport,
                "auth_source": self.config.auth_source,
                "generation_mode": "single_pass_primary",
                "repair_mode": bool(request.revision_findings),
                "requested_sections": [section.name for section in request.sections],
                "transport_metadata": copy.deepcopy(self.client.last_transport_metadata),
            },
        )


def _section_by_name(registry: PersonaSectionRegistry, name: str) -> PersonaSectionSpec:
    return registry.get(name)


def _repair_section_names(findings: list[str], registry: PersonaSectionRegistry) -> list[str]:
    ordered: list[str] = []

    def add(name: str) -> None:
        if name not in ordered:
            ordered.append(name)

    for finding in findings:
        if finding.startswith("missing_section:"):
            add(finding.split(":", 1)[1])
            continue
        if finding.startswith("missing_or_empty_target:"):
            add(finding.split(":", 1)[1].split(".", 1)[0])
            continue
        if finding.startswith("childhood_"):
            add("childhood_environment")
            continue
        if (
            finding.startswith("biography_")
            or finding.startswith("formative_event_")
            or finding.startswith("non_work_purchase_scene_")
            or finding == "missing_narrative"
        ):
            add("biography")
            continue
        if finding.startswith("hobby_depth_"):
            add("lifestyle_and_hobbies")
            continue
        if finding.startswith("enum_leakage:"):
            add("biography")
            add("technology_and_products")
            add("voiceprint")
            continue
        if finding == "missing_decision_policy":
            add("behaviour_and_decisions")
            continue
        if finding == "missing_response_style":
            add("voiceprint")
            continue
        if finding.startswith("runtime_contract_missing:"):
            tail = finding.split(":", 1)[1]
            if tail.startswith("life_story."):
                add("biography")
            elif tail.startswith("decision_policy."):
                add("behaviour_and_decisions")
            elif tail.startswith("response_style."):
                add("voiceprint")
            elif tail.startswith("sensitive_reality_layer."):
                add("sensitive_scenarios")
            else:
                add("behaviour_and_decisions")
            continue
        if "pricing" in finding or "economic" in finding:
            add("economics_and_pricing")
            continue
        if "local" in finding or "cultural" in finding:
            add("local_grounding")
            continue
        if "sensitive" in finding or "identity" in finding or "privacy" in finding:
            add("sensitive_scenarios")
            continue
        if "voice" in finding or "objection" in finding or "response_style" in finding:
            add("voiceprint")
            continue
    valid = {section.name for section in registry.enabled()}
    return [name for name in ordered if name in valid]


def _merge_results(
    primary: PersonaSynthesisResult,
    repair: PersonaSynthesisResult,
    repaired_section_names: set[str],
) -> PersonaSynthesisResult:
    merged_sections = copy.deepcopy(primary.sections)
    for name in repaired_section_names:
        if name in repair.sections:
            merged_sections[name] = copy.deepcopy(repair.sections[name])
    decision_policy = copy.deepcopy(primary.decision_policy)
    if "behaviour_and_decisions" in repaired_section_names and repair.decision_policy:
        decision_policy = copy.deepcopy(repair.decision_policy)
    response_style = copy.deepcopy(primary.response_style)
    if "voiceprint" in repaired_section_names and repair.response_style:
        response_style = copy.deepcopy(repair.response_style)
    narrative = primary.narrative
    if "biography" in repaired_section_names and repair.narrative:
        narrative = repair.narrative
    rationale = "\n\n".join(item for item in [primary.rationale, repair.rationale] if item)
    prompt_versions = list(dict.fromkeys([*primary.prompt_versions, *repair.prompt_versions]))
    raw_metadata = {
        **copy.deepcopy(primary.raw_metadata),
        "repair_fallback": {
            "applied": True,
            "repaired_sections": sorted(repaired_section_names),
            "primary_metadata": copy.deepcopy(primary.raw_metadata),
            "repair_metadata": copy.deepcopy(repair.raw_metadata),
        },
    }
    return PersonaSynthesisResult(
        sections=merged_sections,
        decision_policy=decision_policy,
        response_style=response_style,
        narrative=narrative,
        rationale=rationale,
        provider=primary.provider or repair.provider,
        model=primary.model or repair.model,
        prompt_versions=prompt_versions,
        raw_metadata=raw_metadata,
    )


class FullPassRepairV33SynthesisAdapter:
    def __init__(
        self,
        primary_adapter: PersonaSynthesisAdapter,
        repair_adapter: PersonaSynthesisAdapter,
        *,
        registry: PersonaSectionRegistry = DEFAULT_V3_2_REGISTRY,
        progress_writer: Callable[[str], None] | None = None,
        state_dir: Path | None = None,
    ) -> None:
        self.primary_adapter = primary_adapter
        self.repair_adapter = repair_adapter
        self.registry = registry
        self.progress_writer = progress_writer
        self.config = getattr(primary_adapter, "config", None)
        self.state_dir = state_dir

    def _progress(self, message: str) -> None:
        if self.progress_writer is not None:
            self.progress_writer(message)

    def _state_path(self, request: PersonaSynthesisRequest) -> tuple[Path | None, str]:
        request_hash = _stable_hash({
            "request": request.trace_payload(),
            "prompt_fingerprints": _prompt_fingerprints(request.prompt_texts),
            "generator_version": GENERATOR_VERSION,
            "mode": "v3_3_fullpass_repair",
            "registry": [section.to_dict() for section in self.registry.enabled()],
        })
        if self.state_dir is None:
            return None, request_hash
        persona_dir = self.state_dir / request.synthetic_user_id
        ensure_dir(persona_dir)
        return persona_dir / f"attempt_{request.attempt}.json", request_hash

    def _load_state(self, request: PersonaSynthesisRequest) -> tuple[Path | None, str, dict[str, Any] | None]:
        path, request_hash = self._state_path(request)
        if path is None or not path.exists():
            return path, request_hash, None
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("request_sha256") != request_hash:
            return path, request_hash, None
        return path, request_hash, payload

    def _write_state(self, path: Path | None, request_hash: str, payload: dict[str, Any]) -> None:
        if path is None:
            return
        write_json(path, {"request_sha256": request_hash, **payload})

    def _record_repair_batch(
        self,
        state_path: Path | None,
        request_hash: str,
        state: dict[str, Any],
        batch_request: PersonaSynthesisRequest,
        batch_result: PersonaSynthesisResult,
    ) -> None:
        repaired_sections = dict(state.get("repaired_sections", {}))
        for section in batch_request.sections:
            if section.name in batch_result.sections:
                repaired_sections[section.name] = copy.deepcopy(batch_result.sections[section.name])
        state["repaired_sections"] = repaired_sections
        self._write_state(state_path, request_hash, state)

    def synthesize(self, request: PersonaSynthesisRequest) -> PersonaSynthesisResult:
        state_path, request_hash, state = self._load_state(request)
        resume_primary = bool(state and state.get("primary_result"))
        if resume_primary:
            primary_result = _result_from_dict(dict(state["primary_result"]))
            findings = list(state.get("primary_findings", []))
            if not primary_result.sections and not (state or {}).get("repaired_sections"):
                self._progress(
                    f"[v3.3] {request.synthetic_user_id} ignored stale empty primary checkpoint and is rerunning full-pass"
                )
                resume_primary = False
        if not resume_primary:
            self._progress(f"[v3.3] {request.synthetic_user_id} full-pass attempt {request.attempt} begin")
            primary_result = self.primary_adapter.synthesize(request)
            findings = _validate_result(primary_result, request.sections)
            state = {
                "primary_result": _result_to_dict(primary_result),
                "primary_findings": findings,
                "repaired_sections": {},
            }
            self._write_state(state_path, request_hash, state)
        else:
            self._progress(f"[v3.3] {request.synthetic_user_id} resumed primary result from checkpoint")
        if not findings:
            self._progress(f"[v3.3] {request.synthetic_user_id} full-pass attempt {request.attempt} passed")
            metadata = copy.deepcopy(primary_result.raw_metadata)
            metadata["repair_fallback"] = {"applied": False, "repaired_sections": []}
            primary_result.raw_metadata = metadata
            return primary_result

        repair_section_names = _repair_section_names(findings, self.registry)
        if not repair_section_names:
            self._progress(
                f"[v3.3] {request.synthetic_user_id} full-pass attempt {request.attempt} had findings but no repair mapping"
            )
            metadata = copy.deepcopy(primary_result.raw_metadata)
            metadata["repair_fallback"] = {"applied": False, "repaired_sections": [], "unmapped_findings": findings}
            primary_result.raw_metadata = metadata
            return primary_result

        completed_sections = set((state or {}).get("repaired_sections", {}).keys())
        pending_section_names = [name for name in repair_section_names if name not in completed_sections]
        if not pending_section_names:
            self._progress(f"[v3.3] {request.synthetic_user_id} resumed with all repair sections already checkpointed")
            pending_section_names = []
        else:
            self._progress(
                f"[v3.3] {request.synthetic_user_id} repair fallback sections={', '.join(pending_section_names)}"
            )
        repair_request = PersonaSynthesisRequest(
            synthetic_user_id=request.synthetic_user_id,
            seed=copy.deepcopy(request.seed),
            identity_anchors=copy.deepcopy(request.identity_anchors),
            creative_brief=copy.deepcopy(request.creative_brief),
            sections=[_section_by_name(self.registry, name) for name in pending_section_names],
            prompt_texts=request.prompt_texts,
            random_seed=request.random_seed,
            attempt=request.attempt,
            revision_findings=list(findings),
        )
        repaired_sections = dict((state or {}).get("repaired_sections", {}))
        if pending_section_names:
            batch_hook = getattr(self.repair_adapter, "batch_result_hook", None)
            if hasattr(self.repair_adapter, "batch_result_hook"):
                self.repair_adapter.batch_result_hook = lambda batch_request, batch_result: self._record_repair_batch(
                    state_path, request_hash, state or {}, batch_request, batch_result
                )
            try:
                repair_result = self.repair_adapter.synthesize(repair_request)
            finally:
                if hasattr(self.repair_adapter, "batch_result_hook"):
                    self.repair_adapter.batch_result_hook = batch_hook
            repaired_sections.update(copy.deepcopy(repair_result.sections))
            self._progress(
                f"[v3.3] {request.synthetic_user_id} repair fallback finished sections={', '.join(pending_section_names)}"
            )
        else:
            repair_result = PersonaSynthesisResult(
                sections=repaired_sections,
                decision_policy={},
                response_style={},
                narrative="",
                rationale="",
                provider=primary_result.provider,
                model=primary_result.model,
                prompt_versions=[],
                raw_metadata={"resumed_from_checkpoint": True},
            )
        if state is not None:
            state["repaired_sections"] = repaired_sections
            self._write_state(state_path, request_hash, state)
        merged = _merge_results(primary_result, repair_result, set(repair_section_names))
        return merged


def _write_v3_3_persona(
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
    target_dir = output_dir / persona.profile.synthetic_user_id / "v3_3"
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
    constraint_report = {
        **_build_constraint_report(persona, request),
    }
    if constraint_report["status"] != "pass":
        raise ValueError(f"Protected V3.3 constraints changed for {persona.profile.synthetic_user_id}.")
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
        "generation_mode": "single_pass_primary_with_targeted_repair_fallback",
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
    write_json(target_dir / "profile.json", persona.profile.to_dict())
    write_json(target_dir / "audit.json", persona.to_audit_payload())
    write_json(target_dir / "generation_notes.json", generation_notes)
    write_json(target_dir / "section_manifest.json", {"sections": registry.manifest(section.name for section in sections)})
    write_json(target_dir / "duplicate_report.json", duplicate_report)
    write_json(target_dir / "constraint_report.json", constraint_report)
    for filename, content in rendered.items():
        (target_dir / filename).write_text(content, encoding="utf-8")
    return target_dir


def generate_v3_3_personas(
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
    prompt_texts = load_v3_3_prompt_texts(sections)
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
                f"[v3.3] start {persona_id} seed={random_seed} sections={len(sections)} max_attempts={max_attempts}"
            )
        for attempt in range(1, max_attempts + 1):
            if progress_writer is not None:
                progress_writer(f"[v3.3] {persona_id} attempt {attempt} begin")
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
                    progress_writer(f"[v3.3] {persona_id} attempt {attempt} findings: {', '.join(findings)}")
                else:
                    progress_writer(f"[v3.3] {persona_id} attempt {attempt} passed validation")
            if not findings:
                break
        if final_result is None or final_request is None or findings:
            details = ", ".join(findings) or "adapter returned no result"
            if progress_writer is not None:
                progress_writer(f"[v3.3] {persona_id} failed: {details}")
            raise ValueError(f"V3.3 synthesis failed for {persona_id}: {details}")
        persona = _apply_result(baseline, final_result, sections)
        persona.skill_version = "v3.3"
        persona.profile.audit_evidence_layer.update(
            {
                "persona_generation_method": "single_pass_llm_synthesis_with_targeted_repair",
                "persona_version": "v3.3",
                "generator_version": GENERATOR_VERSION,
                "last_audited_at": datetime.now(UTC).date().isoformat(),
            }
        )
        target = _write_v3_3_persona(
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
            progress_writer(f"[v3.3] wrote {persona_id} -> {target}")
        comparisons.append(persona)
    return written


def validate_v3_3_persona_folder(folder: Path) -> dict[str, Any]:
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
        if notes.get("generator_version") != GENERATOR_VERSION:
            warnings.append(f"Unexpected generator version: {notes.get('generator_version')}")
        if constraint_report.get("status") != "pass":
            warnings.append("Constraint report did not pass.")
    return {"valid": not missing and not warnings, "missing_fields": missing, "warnings": warnings}
