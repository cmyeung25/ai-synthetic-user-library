from __future__ import annotations

from ai_validation_swarm.domain.models import AuditFinding, FounderBrief, PersonaResponse

DISCLAIMER = (
    "This result is AI pre-validation only. It should not replace real user interviews, "
    "market tests, professional advice, or compliance review."
)


def render_report(
    brief: FounderBrief,
    summary: dict[str, object],
    findings: list[AuditFinding],
    planner_steps: list[str],
    responses: list[PersonaResponse],
) -> str:
    top_triggers = summary["top_buying_triggers"]
    top_objections = summary["top_objections"]
    segment_summary = summary["segment_summary"]
    avg_scores = summary["average_scores"]
    skeptic = summary["skeptic_review"]
    assumption_risk_map = summary.get("assumption_risk_map", skeptic["challenged_assumptions"])
    risk_map = summary.get("risk_map", [])
    selected_count = int(summary.get("selected_persona_count", summary["persona_count"]))
    successful_count = int(summary.get("successful_response_count", len(responses)))
    failed_count = int(summary.get("failed_response_count", selected_count - successful_count))
    run_status = str(summary.get("run_status", "completed"))
    execution_note = ""
    if failed_count > 0:
        execution_note = (
            f"This run completed with partial failures: {successful_count} successful responses out of "
            f"{selected_count} selected personas, with {failed_count} failures after retries."
        )

    segment_lines = [
        f"- {panel}: {scores['count']} responses, problem {scores['problem_resonance']}/5, solution {scores['solution_attractiveness']}/5, willingness to pay {scores['willingness_to_pay']}/5, top objection: {scores['top_objections'][0]['objection'] if scores['top_objections'] else 'n/a'}, top trigger: {scores['top_triggers'][0]['trigger'] if scores['top_triggers'] else 'n/a'}"
        for panel, scores in segment_summary.items()
    ]
    risk_lines = [
        f"- {entry['category']} ({entry['highest_severity']}): {entry['observations'][0]}"
        for entry in risk_map
    ]
    interview_script = [
        "Walk me through the last time this problem showed up.",
        "What did you do instead of buying a new tool?",
        "What would you need to trust this workflow enough to try it?",
        "Which part of the pitch feels too vague or too risky?",
        "What would make the price feel justified in week one?",
    ]

    return "\n".join(
        [
            f"# Validation Report: {brief.project_name}",
            "",
            "## 1. Executive Summary",
            f"The concept shows problem resonance at {avg_scores['problem_resonance']}/5, solution attractiveness at {avg_scores['solution_attractiveness']}/5, and willingness to pay at {avg_scores['willingness_to_pay']}/5 across this synthetic panel.",
            *(["", execution_note] if execution_note else []),
            "",
            "## 2. Concept Understanding",
            f"Problem: {brief.problem_statement}",
            f"Solution: {brief.offered_solution}",
            "",
            "## 3. Target Segment Fit",
            f"This run selected {selected_count} personas and received {successful_count} successful responses.",
            *(["Failures after retries: " + str(failed_count)] if failed_count > 0 else []),
            *(["Run status: " + run_status] if run_status != "completed" else []),
            "",
            "## 4. Problem Resonance Score",
            f"{avg_scores['problem_resonance']}/5",
            "",
            "## 5. Solution Attractiveness Score",
            f"{avg_scores['solution_attractiveness']}/5",
            "",
            "## 6. Willingness to Pay Signals",
            f"{avg_scores['willingness_to_pay']}/5",
            "",
            "## 7. Top Buying Triggers",
            *[f"- {item['trigger']} ({item['count']} personas, {item['share_pct']}%)" for item in top_triggers],
            "",
            "## 8. Top Objections",
            *[f"- {item['objection']} ({item['count']} personas, {item['share_pct']}%)" for item in top_objections],
            "",
            "## 9. Segment-by-Segment Reaction",
            *segment_lines,
            "",
            "## 10. Sensitive Topic Risk",
            *risk_lines,
            "",
            "## 11. Privacy / Fairness / Inclusion Risk",
            *[
                f"- {entry['category']}: {entry['observations'][0]}"
                for entry in risk_map
                if entry["category"] in {"privacy_risk", "discrimination_risk", "inclusion_risk", "reporting_risk"}
            ],
            "",
            "## 12. Assumption Risk Map",
            *[
                f"- {item['title']} ({item['severity']}): {item['observation']} Next question: {item['recommended_validation_question']}"
                for item in assumption_risk_map
            ],
            "",
            "## 13. Recommended Repositioning",
            "Lead with a specific workflow outcome and reduce broad AI claims unless proof can be shown immediately.",
            "",
            "## 14. Suggested Landing Page Message",
            "Turn messy follow-up into a short, reviewable action list without adding another heavy workflow.",
            "",
            "## 15. Suggested Concierge MVP",
            "Offer a manual or semi-manual concierge setup that proves the follow-up outcome before full automation.",
            "",
            "## 16. Suggested 7-Day No-Code Validation Plan",
            *[f"- {step}" for step in planner_steps],
            "",
            "## 17. Suggested Real User Interview Script",
            *[f"- {question}" for question in interview_script],
            "",
            "## 18. What This AI Validation Cannot Prove",
            "- It cannot prove real willingness to buy.",
            "- It cannot replace real switching behaviour, retention, or trust formation.",
            "- It cannot replace expert review in high-stakes or regulated contexts.",
            "",
            "## 19. Disclaimer",
            DISCLAIMER,
            "",
            "## Response Appendix",
            *[
                f"- {response.synthetic_user_id}: {response.likely_objection}; try signal: {response.what_would_make_them_try}"
                for response in responses
            ],
        ]
    )


def render_failure_report(
    brief: FounderBrief,
    *,
    selected_persona_count: int,
    failure_reasons: list[str],
    error_count: int,
) -> str:
    return "\n".join(
        [
            f"# Validation Run Failed: {brief.project_name}",
            "",
            "## 1. Run Outcome",
            f"No persona responses were completed successfully. Selected personas: {selected_persona_count}. Logged errors: {error_count}.",
            "",
            "## 2. Failure Reasons",
            *([f"- {reason}" for reason in failure_reasons] if failure_reasons else ["- Unknown failure."]),
            "",
            "## 3. Next Step",
            "- Review `raw_responses.json`, `stage_results.json`, and `errors.json` before retrying.",
            "- Confirm provider stability and whether the selected panel or filters are too restrictive.",
            "",
            "## 4. Disclaimer",
            DISCLAIMER,
        ]
    )
