from __future__ import annotations

import csv
import io


def render_report_csv(report_payload: dict[str, object]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["section", "key", "value", "severity", "reference"])
    writer.writeheader()

    scores = report_payload.get("scores", {})
    for key, value in scores.items():
        writer.writerow({"section": "scores", "key": key, "value": value, "severity": "", "reference": ""})

    for cluster in report_payload.get("trigger_clusters", []):
        writer.writerow(
            {
                "section": "trigger_cluster",
                "key": cluster.get("trigger", ""),
                "value": f"{cluster.get('count', 0)} personas ({cluster.get('share_pct', 0)}%)",
                "severity": "",
                "reference": ",".join(cluster.get("persona_ids", [])),
            }
        )

    for cluster in report_payload.get("objection_clusters", []):
        writer.writerow(
            {
                "section": "objection_cluster",
                "key": cluster.get("objection", ""),
                "value": f"{cluster.get('count', 0)} personas ({cluster.get('share_pct', 0)}%)",
                "severity": "",
                "reference": ",".join(cluster.get("persona_ids", [])),
            }
        )

    for panel_role, segment in report_payload.get("segment_summary", {}).items():
        writer.writerow(
            {
                "section": "segment_summary",
                "key": panel_role,
                "value": (
                    f"problem={segment.get('problem_resonance')}, "
                    f"solution={segment.get('solution_attractiveness')}, "
                    f"wtp={segment.get('willingness_to_pay')}"
                ),
                "severity": "",
                "reference": "",
            }
        )

    for risk in report_payload.get("risk_map", []):
        writer.writerow(
            {
                "section": "risk_map",
                "key": risk.get("category", ""),
                "value": risk.get("observations", [""])[0],
                "severity": risk.get("highest_severity", ""),
                "reference": ",".join(risk.get("affected_persona_ids", [])),
            }
        )

    for finding in report_payload.get("assumption_risk_map", []):
        writer.writerow(
            {
                "section": "assumption_risk_map",
                "key": finding.get("title", ""),
                "value": finding.get("observation", ""),
                "severity": finding.get("severity", ""),
                "reference": ",".join(finding.get("evidence_refs", [])),
            }
        )

    for index, step in enumerate(report_payload.get("planner_steps", []), start=1):
        writer.writerow(
            {
                "section": "planner",
                "key": f"step_{index}",
                "value": step,
                "severity": "",
                "reference": "",
            }
        )

    return output.getvalue()
