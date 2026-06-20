from __future__ import annotations


def render_manual_rubric(evaluation_payload: dict[str, object]) -> str:
    fixtures = evaluation_payload.get("fixtures", [])
    lines = [
        "# Manual Review Rubric",
        "",
        "Use this rubric after the automatic gates pass.",
        "Score each dimension from 1 (weak) to 5 (strong).",
        "",
        "## Dimensions",
        "- Concept understanding: Does the report show a concrete grasp of the founder concept?",
        "- Objection quality: Are the objections specific and decision-relevant?",
        "- Trigger usefulness: Do the buying triggers help the founder reposition or test the concept?",
        "- Risk quality: Are privacy, fairness, trust, or high-stakes risks stated clearly?",
        "- Next-step plan quality: Is the suggested plan concrete enough to execute in the next 7 days?",
        "",
    ]

    for fixture in fixtures:
        if not isinstance(fixture, dict):
            continue
        lines.extend(
            [
                f"## Fixture: {fixture.get('fixture_id', 'unknown')}",
                f"Name: {fixture.get('name', '')}",
                f"Status: {fixture.get('status', '')}",
                f"Run directory: {fixture.get('canonical_run_dir', '')}",
                "",
                "| Dimension | Score (1-5) | Notes |",
                "| --- | --- | --- |",
                "| Concept understanding |  |  |",
                "| Objection quality |  |  |",
                "| Trigger usefulness |  |  |",
                "| Risk quality |  |  |",
                "| Next-step plan quality |  |  |",
                "",
                "Reviewer summary:",
                "",
                "",
            ]
        )

    return "\n".join(lines)

