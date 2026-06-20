from __future__ import annotations

from collections import Counter, defaultdict

from ai_validation_swarm.domain.models import AuditFinding, FounderBrief, PersonaResponse, PersonaSkill, SkepticReview

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3}


def _cluster_responses(
    responses: list[PersonaResponse],
    *,
    key_getter,
    label: str,
) -> list[dict[str, object]]:
    grouped: dict[str, list[PersonaResponse]] = defaultdict(list)
    for response in responses:
        grouped[str(key_getter(response))].append(response)

    ordered = sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0]))
    total = len(responses) or 1
    clusters: list[dict[str, object]] = []
    for theme, cluster_responses in ordered:
        clusters.append(
            {
                label: theme,
                "count": len(cluster_responses),
                "share_pct": round((len(cluster_responses) / total) * 100, 2),
                "persona_ids": [response.synthetic_user_id for response in cluster_responses],
                "panel_roles": sorted({response.panel_role for response in cluster_responses}),
                "examples": sorted(
                    {
                        getattr(response, "what_would_make_them_try")
                        if label == "trigger"
                        else getattr(response, "likely_objection")
                        for response in cluster_responses
                    }
                )[:3],
            }
        )
    return clusters


def _build_segment_summary(responses: list[PersonaResponse]) -> dict[str, dict[str, object]]:
    grouped: dict[str, list[PersonaResponse]] = defaultdict(list)
    for response in responses:
        grouped[response.panel_role].append(response)

    segment_summary: dict[str, dict[str, object]] = {}
    for panel_role, panel_responses in grouped.items():
        scorecards = [response.scorecard for response in panel_responses]
        objection_counts = Counter(response.likely_objection for response in panel_responses)
        trigger_counts = Counter(response.what_would_make_them_try for response in panel_responses)
        trust_signal_counts = Counter(response.trust_concern for response in panel_responses)

        segment_summary[panel_role] = {
            "count": len(panel_responses),
            "problem_resonance": round(sum(s["problem_resonance"] for s in scorecards) / len(scorecards), 2),
            "solution_attractiveness": round(sum(s["solution_attractiveness"] for s in scorecards) / len(scorecards), 2),
            "willingness_to_pay": round(sum(s["willingness_to_pay"] for s in scorecards) / len(scorecards), 2),
            "top_objections": [
                {"objection": theme, "count": count}
                for theme, count in objection_counts.most_common(3)
            ],
            "top_triggers": [
                {"trigger": theme, "count": count}
                for theme, count in trigger_counts.most_common(3)
            ],
            "top_trust_concerns": [
                {"trust_concern": theme, "count": count}
                for theme, count in trust_signal_counts.most_common(3)
            ],
        }
    return segment_summary


def _build_risk_map(findings: list[AuditFinding]) -> list[dict[str, object]]:
    grouped: dict[str, list[AuditFinding]] = defaultdict(list)
    for finding in findings:
        grouped[finding.category].append(finding)

    risk_map: list[dict[str, object]] = []
    for category, category_findings in sorted(
        grouped.items(),
        key=lambda item: (-max(SEVERITY_ORDER.get(f.severity, 0) for f in item[1]), item[0]),
    ):
        highest = max(category_findings, key=lambda finding: SEVERITY_ORDER.get(finding.severity, 0))
        risk_map.append(
            {
                "category": category,
                "highest_severity": highest.severity,
                "finding_count": len(category_findings),
                "affected_persona_ids": sorted(
                    {
                        ref
                        for finding in category_findings
                        for ref in finding.evidence_refs
                        if isinstance(ref, str) and ref.startswith("su_")
                    }
                ),
                "observations": [finding.observation for finding in category_findings],
                "recommended_validation_questions": [
                    finding.recommended_validation_question for finding in category_findings
                ],
            }
        )
    return risk_map


def build_summary(
    brief: FounderBrief,
    personas: list[PersonaSkill],
    responses: list[PersonaResponse],
    findings: list[AuditFinding],
    skeptic_review: SkepticReview,
    *,
    run_status: str = "completed",
    failure_reasons: list[str] | None = None,
) -> dict[str, object]:
    count = len(responses)
    avg_problem = round(sum(r.scorecard["problem_resonance"] for r in responses) / count, 2)
    avg_solution = round(sum(r.scorecard["solution_attractiveness"] for r in responses) / count, 2)
    avg_wtp = round(sum(r.scorecard["willingness_to_pay"] for r in responses) / count, 2)

    trigger_clusters = _cluster_responses(
        responses,
        key_getter=lambda response: response.what_would_make_them_try,
        label="trigger",
    )
    objection_clusters = _cluster_responses(
        responses,
        key_getter=lambda response: response.likely_objection,
        label="objection",
    )
    segment_summary = _build_segment_summary(responses)
    risk_map = _build_risk_map(findings)
    skeptic_payload = skeptic_review.to_dict()
    assumption_risk_map = skeptic_payload["challenged_assumptions"]

    return {
        "aggregation_version": "aggregator/v1",
        "project_name": brief.project_name,
        "persona_count": len(personas),
        "selected_persona_count": len(personas),
        "successful_response_count": len(responses),
        "failed_response_count": len(personas) - len(responses),
        "response_coverage_pct": round((len(responses) / len(personas)) * 100, 2) if personas else 0.0,
        "run_status": run_status,
        "failure_reasons": failure_reasons or [],
        "average_scores": {
            "problem_resonance": avg_problem,
            "solution_attractiveness": avg_solution,
            "willingness_to_pay": avg_wtp,
        },
        "top_buying_triggers": trigger_clusters[:5],
        "top_objections": objection_clusters[:5],
        "trigger_clusters": trigger_clusters,
        "objection_clusters": objection_clusters,
        "segment_summary": segment_summary,
        "risk_map": risk_map,
        "audit_categories": [finding.to_dict() for finding in findings],
        "skeptic_review": skeptic_payload,
        "assumption_risk_map": assumption_risk_map,
    }
