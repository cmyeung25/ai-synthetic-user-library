from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

from ai_validation_swarm.domain.models import PanelSpec
from ai_validation_swarm.saas.metadata_store import persist_run_contract_metadata
from ai_validation_swarm.storage.files import write_json


RunKind = Literal[
    "validation_run",
    "facilitated_interview",
    "observer_controlled_interview",
    "concept_panel",
]

RUN_CONTRACT_VERSION = "shared-run-contract/v1"


class InterviewSessionLike(Protocol):
    interview_id: str
    persona_id: str
    research_goal: str
    interview_mode: str
    hypothesis: str
    product_context: str
    concept_label: str
    concept_protocol_version: str
    stimulus_type: str
    stimulus_artifact: str
    prototype_task: str
    output_language: str
    created_at: str
    updated_at: str
    status: str
    facilitator_provider: str
    facilitator_model: str
    synthetic_only_disclaimer: str
    coverage_status: dict[str, Any]
    exchanges: list[Any]
    facilitator_decisions: list[dict[str, Any]]
    insight_report: dict[str, Any]
    persona_driver_trace: dict[str, Any]
    quality_provider: str
    hypothesis_evidence_judgment: dict[str, Any]
    observed_action_trace: dict[str, Any]
    stimulus_analysis: dict[str, Any]
    last_error: str


@dataclass(slots=True)
class SharedRunRequest:
    run_id: str
    run_kind: RunKind
    entrypoint: str
    created_at: str
    brief_id: str = ""
    persona_id: str = ""
    persona_ids: list[str] = field(default_factory=list)
    research_goal: str = ""
    interview_mode: str = ""
    panel_spec: dict[str, Any] = field(default_factory=dict)
    hypothesis: str = ""
    product_context: str = ""
    concept_label: str = ""
    concept_protocol: str = ""
    stimulus_type: str = ""
    stimulus_artifact: str = ""
    prototype_task: str = ""
    output_language: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SharedRunResult:
    run_id: str
    run_kind: RunKind
    status: str
    started_at: str
    output_path: str
    finished_at: str | None = None
    primary_artifact_path: str = ""
    artifact_paths: list[str] = field(default_factory=list)
    selected_persona_ids: list[str] = field(default_factory=list)
    successful_response_count: int | None = None
    failed_response_count: int | None = None
    error_count: int | None = None
    provider_name: str = ""
    model_name: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class SharedRunContract:
    contract_version: str
    request: SharedRunRequest
    result: SharedRunResult

    def to_dict(self) -> dict[str, Any]:
        return {
            "contract_version": self.contract_version,
            "request": self.request.to_dict(),
            "result": self.result.to_dict(),
        }


def write_shared_run_contract(path: Path, contract: SharedRunContract) -> None:
    payload = contract.to_dict()
    write_json(path, payload)
    persist_run_contract_metadata(path.parent.parent, path, payload)


def build_validation_run_contract(
    *,
    run_id: str,
    brief_id: str,
    panel_spec: PanelSpec,
    created_at: str,
    started_at: str,
    status: str,
    output_path: Path,
    artifact_paths: list[str],
    selected_persona_ids: list[str],
    successful_response_count: int,
    failed_response_count: int,
    error_count: int,
    provider_name: str,
    model_name: str,
    finished_at: str | None = None,
) -> SharedRunContract:
    return SharedRunContract(
        contract_version=RUN_CONTRACT_VERSION,
        request=SharedRunRequest(
            run_id=run_id,
            run_kind="validation_run",
            entrypoint="run",
            created_at=created_at,
            brief_id=brief_id,
            panel_spec=panel_spec.to_dict(),
            metadata={"system_of_record": "json_artifacts"},
        ),
        result=SharedRunResult(
            run_id=run_id,
            run_kind="validation_run",
            status=status,
            started_at=started_at,
            finished_at=finished_at,
            output_path=str(output_path),
            primary_artifact_path=str(output_path / "run.json"),
            artifact_paths=artifact_paths,
            selected_persona_ids=selected_persona_ids,
            successful_response_count=successful_response_count,
            failed_response_count=failed_response_count,
            error_count=error_count,
            provider_name=provider_name,
            model_name=model_name,
            metadata={"report_artifact": "report.json"},
        ),
    )


def build_interview_run_contract(
    session: InterviewSessionLike,
    *,
    output_path: Path,
    artifact_paths: list[str],
    run_kind: RunKind,
) -> SharedRunContract:
    entrypoint = "observe-facilitated-interview" if run_kind == "observer_controlled_interview" else "run-facilitated-interview"
    primary_artifact = "interview.json"
    metadata: dict[str, Any] = {
        "system_of_record": "json_artifacts",
        "exchange_count": len(session.exchanges),
        "facilitator_decision_count": len(session.facilitator_decisions),
    }
    if session.coverage_status:
        metadata["coverage_status"] = session.coverage_status
    return SharedRunContract(
        contract_version=RUN_CONTRACT_VERSION,
        request=SharedRunRequest(
            run_id=session.interview_id,
            run_kind=run_kind,
            entrypoint=entrypoint,
            created_at=session.created_at,
            persona_id=session.persona_id,
            persona_ids=[session.persona_id],
            research_goal=session.research_goal,
            interview_mode=session.interview_mode,
            hypothesis=session.hypothesis,
            product_context=session.product_context,
            concept_label=session.concept_label,
            concept_protocol=session.concept_protocol_version,
            stimulus_type=session.stimulus_type,
            stimulus_artifact=session.stimulus_artifact,
            prototype_task=session.prototype_task,
            output_language=session.output_language,
            metadata={"synthetic_only_disclaimer": session.synthetic_only_disclaimer},
        ),
        result=SharedRunResult(
            run_id=session.interview_id,
            run_kind=run_kind,
            status=session.status,
            started_at=session.created_at,
            finished_at=session.updated_at if session.status in {"completed", "failed"} else None,
            output_path=str(output_path),
            primary_artifact_path=str(output_path / primary_artifact),
            artifact_paths=artifact_paths,
            selected_persona_ids=[session.persona_id],
            error_count=1 if session.last_error else 0,
            provider_name=session.facilitator_provider,
            model_name=session.facilitator_model,
            metadata=metadata,
        ),
    )


def build_concept_panel_run_contract(
    *,
    run_id: str,
    created_at: str,
    output_path: Path,
    research_goal: str,
    product_context: str,
    topic_label: str,
    concept_protocol: str,
    concept_label: str,
    persona_ids: list[str],
    output_language: str,
    status: str,
    interview_count: int,
    completed_interview_count: int,
    failed_interview_count: int,
    artifact_paths: list[str],
    finished_at: str | None = None,
) -> SharedRunContract:
    return SharedRunContract(
        contract_version=RUN_CONTRACT_VERSION,
        request=SharedRunRequest(
            run_id=run_id,
            run_kind="concept_panel",
            entrypoint="run-concept-panel",
            created_at=created_at,
            persona_ids=persona_ids,
            research_goal=research_goal,
            interview_mode="concept_validation",
            product_context=product_context,
            concept_label=concept_label or topic_label,
            concept_protocol=concept_protocol,
            output_language=output_language,
            metadata={"topic_label": topic_label, "synthetic_only": True},
        ),
        result=SharedRunResult(
            run_id=run_id,
            run_kind="concept_panel",
            status=status,
            started_at=created_at,
            finished_at=finished_at,
            output_path=str(output_path),
            primary_artifact_path=str(output_path / "manifest.json"),
            artifact_paths=artifact_paths,
            selected_persona_ids=persona_ids,
            successful_response_count=completed_interview_count,
            failed_response_count=failed_interview_count,
            error_count=failed_interview_count,
            metadata={
                "interview_count": interview_count,
                "panel_summary_artifact": "panel_summary.json",
            },
        ),
    )
