from __future__ import annotations

import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.personas.llm import OpenAIPersonaEnricher, OpenAIPersonaJudge
from ai_validation_swarm.providers.openai_client import OpenAIResponsesClient, load_openai_provider_config
from ai_validation_swarm.storage.files import ensure_dir, save_persona, write_json

PERSONA_QUALITY_COMPARE_VERSION = "persona-quality-compare/v1"
AGNES_DEFAULT_BASE_URL = "https://apihub.agnes-ai.com/v1"
AGNES_DEFAULT_MODEL = "agnes-2.0-flash"


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def normalize_judge_score(value: Any) -> float | None:
    if not isinstance(value, (int, float)):
        return None
    numeric = float(value)
    if numeric > 10:
        numeric = numeric / 10.0
    return round(numeric, 2)


def _average(values: list[float | None]) -> float | None:
    usable = [value for value in values if value is not None]
    if not usable:
        return None
    return round(sum(usable) / len(usable), 2)


def _default_label(backend: str) -> str:
    return {"codex": "Codex", "agnes": "Agnes", "openai": "OpenAI"}.get(backend, backend)


def load_persona_quality_compare_config(backend: str):
    if backend == "codex":
        return load_openai_provider_config(prefer_codex_auth=True, force_transport="codex_cli")
    if backend == "codex-sdk":
        return load_openai_provider_config(prefer_codex_auth=True, force_transport="codex_sdk_node")
    if backend == "agnes":
        return load_openai_provider_config(
            force_transport="powershell_webrequest",
            force_provider_name="agnes",
            force_api_key_env="AGNES_API_KEY",
            default_model=AGNES_DEFAULT_MODEL,
            default_profile=AGNES_DEFAULT_MODEL,
            default_api_base=AGNES_DEFAULT_BASE_URL,
        )
    return load_openai_provider_config()


def judge_result_to_payload(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "verdict": result.get("verdict"),
        "plausibility_score": result.get("plausibility_score"),
        "stereotype_risk_score": result.get("stereotype_risk_score"),
        "panel_fit_score": result.get("panel_fit_score"),
        "normalized_scores": {
            "plausibility_score": normalize_judge_score(result.get("plausibility_score")),
            "stereotype_risk_score": normalize_judge_score(result.get("stereotype_risk_score")),
            "panel_fit_score": normalize_judge_score(result.get("panel_fit_score")),
        },
        "findings": result.get("findings", []),
        "revision_hints": result.get("revision_hints", []),
        "rationale": result.get("rationale", ""),
        "provider": result.get("provider"),
        "profile": result.get("profile"),
        "model": result.get("model"),
        "prompt_version": result.get("prompt_version"),
        "generated_at": result.get("generated_at"),
    }


def finalize_persona_quality_compare_report(report: dict[str, Any]) -> dict[str, Any]:
    baseline_runs = report.get("runs", [])
    candidate_delta_key = "deltas_candidate_minus_baseline"
    report["aggregates"] = {
        "baseline": {
            "average_plausibility_score_normalized": _average(
                [item["baseline"]["judge"]["normalized_scores"]["plausibility_score"] for item in baseline_runs]
            ),
            "average_stereotype_risk_score_normalized": _average(
                [item["baseline"]["judge"]["normalized_scores"]["stereotype_risk_score"] for item in baseline_runs]
            ),
            "average_panel_fit_score_normalized": _average(
                [item["baseline"]["judge"]["normalized_scores"]["panel_fit_score"] for item in baseline_runs]
            ),
        },
        "candidate": {
            "average_plausibility_score_normalized": _average(
                [item["candidate"]["judge"]["normalized_scores"]["plausibility_score"] for item in baseline_runs]
            ),
            "average_stereotype_risk_score_normalized": _average(
                [item["candidate"]["judge"]["normalized_scores"]["stereotype_risk_score"] for item in baseline_runs]
            ),
            "average_panel_fit_score_normalized": _average(
                [item["candidate"]["judge"]["normalized_scores"]["panel_fit_score"] for item in baseline_runs]
            ),
        },
        "reliability": {
            "baseline_successes": len(baseline_runs),
            "candidate_successes": len(baseline_runs),
            "baseline_total_attempts": sum(item["baseline"]["attempt_count"] for item in baseline_runs),
            "candidate_total_attempts": sum(item["candidate"]["attempt_count"] for item in baseline_runs),
            "baseline_pairs_using_fallback": sum(1 for item in baseline_runs if item["baseline"]["fallback_used"]),
            "candidate_pairs_using_fallback": sum(1 for item in baseline_runs if item["candidate"]["fallback_used"]),
        },
    }
    report["aggregates"][candidate_delta_key] = {
        "plausibility_score_normalized": round(
            (
                report["aggregates"]["candidate"]["average_plausibility_score_normalized"] or 0.0
            )
            - (
                report["aggregates"]["baseline"]["average_plausibility_score_normalized"] or 0.0
            ),
            2,
        ),
        "stereotype_risk_score_normalized": round(
            (
                report["aggregates"]["candidate"]["average_stereotype_risk_score_normalized"] or 0.0
            )
            - (
                report["aggregates"]["baseline"]["average_stereotype_risk_score_normalized"] or 0.0
            ),
            2,
        ),
        "panel_fit_score_normalized": round(
            (
                report["aggregates"]["candidate"]["average_panel_fit_score_normalized"] or 0.0
            )
            - (
                report["aggregates"]["baseline"]["average_panel_fit_score_normalized"] or 0.0
            ),
            2,
        ),
    }
    report["score_normalization_note"] = (
        "Judge outputs mixed 0-10 and 0-100 scales. Scores above 10 were normalized "
        "by dividing by 10 before aggregation."
    )
    return report


def render_persona_quality_compare_markdown(report: dict[str, Any]) -> str:
    baseline_label = str(report["setup"]["baseline_label"])
    candidate_label = str(report["setup"]["candidate_label"])
    delta = report["aggregates"]["deltas_candidate_minus_baseline"]
    lines = [
        f"# {report['experiment_id']}",
        "",
        "## Setup",
        f"- Date: {report['generated_at']}",
        f"- Seeds: {', '.join(str(seed) for seed in report['seeds'])}",
        f"- Baseline: {baseline_label} with `{report['setup']['baseline_prompt_version']}`",
        f"- Candidate: {candidate_label} with `{report['setup']['candidate_prompt_version']}`",
        f"- Judge: {report['setup']['judge_label']} (`{report['setup']['judge_prompt_version']}`)",
        f"- Note: {report['score_normalization_note']}",
        "",
        "## Quality Averages",
        f"- {baseline_label} plausibility: {report['aggregates']['baseline']['average_plausibility_score_normalized']}",
        f"- {candidate_label} plausibility: {report['aggregates']['candidate']['average_plausibility_score_normalized']}",
        f"- Delta plausibility: {delta['plausibility_score_normalized']}",
        f"- {baseline_label} stereotype risk: {report['aggregates']['baseline']['average_stereotype_risk_score_normalized']}",
        f"- {candidate_label} stereotype risk: {report['aggregates']['candidate']['average_stereotype_risk_score_normalized']}",
        f"- Delta stereotype risk: {delta['stereotype_risk_score_normalized']}",
        f"- {baseline_label} panel fit: {report['aggregates']['baseline']['average_panel_fit_score_normalized']}",
        f"- {candidate_label} panel fit: {report['aggregates']['candidate']['average_panel_fit_score_normalized']}",
        f"- Delta panel fit: {delta['panel_fit_score_normalized']}",
        "",
        "## Reliability",
        f"- {baseline_label} total attempts: {report['aggregates']['reliability']['baseline_total_attempts']}",
        f"- {candidate_label} total attempts: {report['aggregates']['reliability']['candidate_total_attempts']}",
        f"- {baseline_label} pairs using fallback: {report['aggregates']['reliability']['baseline_pairs_using_fallback']}",
        f"- {candidate_label} pairs using fallback: {report['aggregates']['reliability']['candidate_pairs_using_fallback']}",
        "",
        "## Seed Notes",
    ]
    for item in report["runs"]:
        baseline = item["baseline"]
        candidate = item["candidate"]
        lines.append(
            f"- Seed {item['seed']}: "
            f"{baseline_label} P{baseline['judge']['normalized_scores']['plausibility_score']} / "
            f"S{baseline['judge']['normalized_scores']['stereotype_risk_score']} / "
            f"F{baseline['judge']['normalized_scores']['panel_fit_score']}; "
            f"{candidate_label} P{candidate['judge']['normalized_scores']['plausibility_score']} / "
            f"S{candidate['judge']['normalized_scores']['stereotype_risk_score']} / "
            f"F{candidate['judge']['normalized_scores']['panel_fit_score']} "
            f"({candidate_label} attempts={candidate['attempt_count']}, fallback_used={candidate['fallback_used']})"
        )
    return "\n".join(lines) + "\n"


def _generate_seed_result(
    *,
    backend: str,
    label: str,
    seed: int,
    enricher: OpenAIPersonaEnricher,
    judge: OpenAIPersonaJudge,
    output_dir: Path,
    max_attempts: int,
    pause_seconds: float,
) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    persona = None
    last_error = ""
    for attempt in range(1, max_attempts + 1):
        attempt_start = time.perf_counter()
        try:
            persona = generate_personas(count=1, random_seed=seed, enricher=enricher, judge=None)[0]
            judge_result = judge.judge(persona)
            transport_meta = dict(getattr(enricher.client, "last_transport_metadata", {}) or {})
            elapsed_seconds = round(time.perf_counter() - attempt_start, 1)
            attempts.append(
                {
                    "attempt": attempt,
                    "status": "success",
                    "elapsed_seconds": elapsed_seconds,
                    "transport": transport_meta.get("transport", enricher.config.transport),
                    "fallback_transport": transport_meta.get("fallback_transport"),
                    "usage": transport_meta.get("usage"),
                }
            )
            save_persona(persona, output_dir / f"seed_{seed}")
            return {
                "label": label,
                "backend": backend,
                "elapsed_seconds": round(sum(item["elapsed_seconds"] for item in attempts), 1),
                "persona_generation_method": persona.audit.get("persona_generation_method"),
                "llm_enrichment": persona.audit.get("llm_enrichment"),
                "judge": judge_result_to_payload(judge_result),
                "attempt_count": len(attempts),
                "fallback_used": any(item.get("fallback_transport") for item in attempts if item["status"] == "success"),
                "attempts": attempts,
            }
        except Exception as exc:
            last_error = str(exc)
            attempts.append(
                {
                    "attempt": attempt,
                    "status": "failed",
                    "elapsed_seconds": round(time.perf_counter() - attempt_start, 1),
                    "error": last_error,
                }
            )
            if attempt < max_attempts:
                time.sleep(pause_seconds)

    raise RuntimeError(f"{label} failed for seed {seed}: {last_error}")


def run_persona_quality_compare(
    *,
    seeds: list[int],
    output_root: Path,
    experiment_id: str = "",
    baseline_backend: str = "codex",
    candidate_backend: str = "agnes",
    judge_backend: str = "codex",
    baseline_label: str = "",
    candidate_label: str = "",
    judge_label: str = "",
    max_baseline_retries: int = 1,
    max_candidate_retries: int = 3,
    pause_seconds: float = 6.0,
) -> dict[str, Any]:
    resolved_seeds = list(seeds) or [101, 202, 303]
    resolved_experiment_id = experiment_id or (
        f"persona_ab_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}_{candidate_backend}_vs_{baseline_backend}_matched_pairs"
    )
    experiment_dir = output_root / resolved_experiment_id
    baseline_dir = experiment_dir / "baseline_personas"
    candidate_dir = experiment_dir / "candidate_personas"
    ensure_dir(baseline_dir)
    ensure_dir(candidate_dir)

    baseline_config = load_persona_quality_compare_config(baseline_backend)
    candidate_config = load_persona_quality_compare_config(candidate_backend)
    judge_config = load_persona_quality_compare_config(judge_backend)

    baseline_enricher = OpenAIPersonaEnricher(OpenAIResponsesClient(baseline_config), baseline_config)
    candidate_enricher = OpenAIPersonaEnricher(OpenAIResponsesClient(candidate_config), candidate_config)
    judge = OpenAIPersonaJudge(OpenAIResponsesClient(judge_config), judge_config)

    report = {
        "comparison_version": PERSONA_QUALITY_COMPARE_VERSION,
        "experiment_id": resolved_experiment_id,
        "generated_at": _timestamp(),
        "seeds": resolved_seeds,
        "setup": {
            "baseline_backend": baseline_backend,
            "candidate_backend": candidate_backend,
            "judge_backend": judge_backend,
            "baseline_label": baseline_label or _default_label(baseline_backend),
            "candidate_label": candidate_label or _default_label(candidate_backend),
            "judge_label": judge_label or _default_label(judge_backend),
            "baseline_prompt_version": baseline_enricher.prompt_version,
            "candidate_prompt_version": candidate_enricher.prompt_version,
            "judge_prompt_version": judge.prompt_version,
            "baseline_model": baseline_config.model,
            "candidate_model": candidate_config.model,
            "judge_model": judge_config.model,
            "quality_only": True,
            "matched_pairs": True,
            "sample_size": len(resolved_seeds),
            "pause_seconds": pause_seconds,
        },
        "runs": [],
        "output_paths": {
            "experiment_dir": str(experiment_dir),
            "report_json": str(experiment_dir / "comparison_report.json"),
            "report_md": str(experiment_dir / "comparison_report.md"),
        },
    }

    for index, seed in enumerate(resolved_seeds):
        baseline_result = _generate_seed_result(
            backend=baseline_backend,
            label=report["setup"]["baseline_label"],
            seed=seed,
            enricher=baseline_enricher,
            judge=judge,
            output_dir=baseline_dir,
            max_attempts=max_baseline_retries,
            pause_seconds=pause_seconds,
        )
        candidate_result = _generate_seed_result(
            backend=candidate_backend,
            label=report["setup"]["candidate_label"],
            seed=seed,
            enricher=candidate_enricher,
            judge=judge,
            output_dir=candidate_dir,
            max_attempts=max_candidate_retries,
            pause_seconds=pause_seconds,
        )
        report["runs"].append(
            {
                "seed": seed,
                "baseline": baseline_result,
                "candidate": candidate_result,
            }
        )
        if index < len(resolved_seeds) - 1:
            time.sleep(pause_seconds)

    finalize_persona_quality_compare_report(report)
    write_json(experiment_dir / "comparison_report.json", report)
    (experiment_dir / "comparison_report.md").write_text(
        render_persona_quality_compare_markdown(report),
        encoding="utf-8",
    )
    return report
