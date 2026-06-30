from __future__ import annotations

import re
from collections import Counter

from ai_validation_swarm.domain.models import (
    AuditFinding,
    FounderBrief,
    PersonaResponse,
    PersonaSkill,
    SkepticFinding,
    SkepticReview,
)
from ai_validation_swarm.providers.base import BaseProvider


def _contains_any_keyword(text: str, keywords: list[str]) -> bool:
    for keyword in keywords:
        if any(character.isalnum() for character in keyword):
            pattern = rf"(?<!\w){re.escape(keyword)}(?!\w)"
            if re.search(pattern, text):
                return True
        elif keyword in text:
            return True
    return False


class MockProvider(BaseProvider):
    provider_name = "mock"
    model_version = "mock-provider/v1"

    def persona_response(self, persona: PersonaSkill, brief: FounderBrief, protocol_id: str) -> PersonaResponse:
        text = " ".join(
            [
                brief.problem_statement,
                brief.offered_solution,
                brief.validation_goal,
                brief.pricing_hypothesis,
                brief.landing_page_text,
            ]
        ).lower()

        privacy_flag = _contains_any_keyword(text, ["ai", "data", "personal", "automated"])
        subscription_flag = _contains_any_keyword(text, ["subscription", "monthly", "$", "trial"])
        admin_flag = _contains_any_keyword(text, ["follow-up", "admin", "notes", "tasks", "workflow"])
        high_stakes_flag = _contains_any_keyword(text, ["medical", "legal", "finance", "education", "parent"])

        panel_role = persona.seed.panel_role
        budget = persona.seed.budget_flexibility
        privacy_tolerance = persona.seed.privacy_risk_tolerance
        digital_literacy = persona.seed.digital_literacy_ceiling

        problem_resonance = 4 if admin_flag else 3
        solution_attractiveness = 4 if panel_role == "extreme_user" else 3
        willingness_to_pay = 4 if budget == "high" else 2 if budget == "low" else 3

        if panel_role == "skeptic":
            solution_attractiveness -= 1
        if panel_role == "low_tech":
            solution_attractiveness -= 1
        if privacy_flag and privacy_tolerance == "low":
            willingness_to_pay -= 1
        if subscription_flag and budget == "low":
            willingness_to_pay -= 1

        problem_resonance = max(1, min(problem_resonance, 5))
        solution_attractiveness = max(1, min(solution_attractiveness, 5))
        willingness_to_pay = max(1, min(willingness_to_pay, 5))

        trigger = "clear time savings"
        objection = "uncertain ROI"
        if budget == "low":
            objection = "subscription creep"
        elif panel_role == "privacy_sensitive":
            objection = "unclear data handling"
        elif panel_role == "low_tech":
            objection = "setup looks too fiddly"
        elif panel_role == "skeptic":
            objection = "claims feel under-proven"

        if privacy_flag and privacy_tolerance == "low":
            trigger = "a privacy-light workflow with minimal sensitive data"
        elif digital_literacy == "low":
            trigger = "proof that setup takes almost no effort"
        elif panel_role == "extreme_user":
            trigger = "evidence that it replaces several manual follow-up steps"

        first_impression = (
            f"As a {persona.profile.basic_identity['occupation']}, I can see the promise if this reduces follow-up friction "
            f"without adding another messy layer to my week."
        )
        pain_relevance = (
            f"The pain feels {['weak', 'light', 'real', 'strong', 'urgent'][problem_resonance - 1]} because "
            f"{persona.profile.problem_context['active_pain_points'][0]} already shows up in my routine."
        )
        solution_copy = "The workflow sounds useful but still needs proof." if solution_attractiveness <= 3 else "The workflow sounds attractive if it works as advertised."
        trust_concern = "I would need clearer proof on privacy and data boundaries." if privacy_flag and privacy_tolerance == "low" else "I would need proof that this fits smoothly into existing habits."
        pricing_reaction = (
            "I would resist a subscription unless the value becomes obvious in the first week."
            if willingness_to_pay <= 2
            else "I could justify a subscription if it reliably saves time."
        )
        sensitive_concern = ""
        if high_stakes_flag:
            sensitive_concern = "This touches a high-stakes domain, so mistakes or over-automation would feel riskier."
        elif panel_role in {"privacy_sensitive", "political_risk"} and privacy_flag:
            sensitive_concern = "The positioning could create trust issues if it sounds too intrusive or too eager to profile people."

        return PersonaResponse(
            synthetic_user_id=persona.profile.synthetic_user_id,
            panel_role=panel_role,
            protocol_id=protocol_id,
            first_impression=first_impression,
            pain_relevance=pain_relevance,
            solution_attractiveness=solution_copy,
            trust_concern=trust_concern,
            pricing_reaction=pricing_reaction,
            likely_objection=objection,
            what_would_make_them_try=trigger,
            what_would_make_them_reject=persona.decision_policy["rejection_triggers"][0],
            sensitive_concern_if_any=sensitive_concern,
            scorecard={
                "problem_resonance": problem_resonance,
                "solution_attractiveness": solution_attractiveness,
                "willingness_to_pay": willingness_to_pay,
            },
            themes={"top_trigger": trigger, "top_objection": objection},
            response_version="persona-response/v1",
        )

    def skeptic_review(
        self, brief: FounderBrief, personas: list[PersonaSkill], responses: list[PersonaResponse]
    ) -> SkepticReview:
        avg_problem = sum(r.scorecard["problem_resonance"] for r in responses) / len(responses)
        avg_solution = sum(r.scorecard["solution_attractiveness"] for r in responses) / len(responses)
        avg_wtp = sum(r.scorecard["willingness_to_pay"] for r in responses) / len(responses)
        objections = Counter(response.likely_objection for response in responses)

        challenged: list[SkepticFinding] = []
        if avg_problem < 3.2:
            challenged.append(
                SkepticFinding(
                    finding_id="skeptic_problem_urgency",
                    severity="medium",
                    title="Problem urgency may be overstated",
                    observation="The problem does not appear consistently urgent enough across the current response set.",
                    evidence_refs=["raw_responses"],
                    recommended_validation_question="Which target users feel this pain often enough to switch behavior in the next 30 days?",
                )
            )
        if avg_solution < 3.2:
            challenged.append(
                SkepticFinding(
                    finding_id="skeptic_solution_clarity",
                    severity="medium",
                    title="Solution story may still be too abstract",
                    observation="The proposed workflow benefit still looks conditional on execution details that the current pitch does not yet prove.",
                    evidence_refs=["raw_responses", "summary"],
                    recommended_validation_question="Which exact before-and-after workflow improvement can the founder demonstrate in a short trial?",
                )
            )
        if avg_wtp < 3.0:
            challenged.append(
                SkepticFinding(
                    finding_id="skeptic_pricing_readiness",
                    severity="high",
                    title="Pricing may be ahead of proven value",
                    observation="A meaningful slice of the current panel does not yet show enough willingness to pay at the proposed stage.",
                    evidence_refs=["raw_responses"],
                    recommended_validation_question="What proof or trial experience would make the initial price feel justified within the first week?",
                )
            )
        if "uncertain ROI" in objections:
            challenged.append(
                SkepticFinding(
                    finding_id="skeptic_roi_gap",
                    severity="high",
                    title="Messaging still leans on implied ROI",
                    observation="The strongest objection cluster suggests the concept still lacks concrete proof of measurable payoff.",
                    evidence_refs=["raw_responses", "objection_clusters"],
                    recommended_validation_question="What metric or visible output can the founder show to reduce ROI ambiguity?",
                )
            )
        if not challenged:
            challenged.append(
                SkepticFinding(
                    finding_id="skeptic_switching_behavior",
                    severity="low",
                    title="Switching behavior still needs real-world proof",
                    observation="The concept shows promise in this run, but synthetic agreement does not prove real habit change or retention.",
                    evidence_refs=["summary"],
                    recommended_validation_question="What small real-world behavior change would most quickly test whether users truly adopt this workflow?",
                )
            )

        return SkepticReview(
            review_version="skeptic-review/v1",
            summary="Skeptic review focuses on weak proof, habit-change friction, pricing readiness, and value-capture gaps.",
            challenged_assumptions=challenged,
        )

    def sensitive_audit(
        self, brief: FounderBrief, personas: list[PersonaSkill], responses: list[PersonaResponse]
    ) -> list[AuditFinding]:
        findings: list[AuditFinding] = []
        text = " ".join(
            [
                brief.problem_statement,
                brief.offered_solution,
                brief.validation_goal,
                brief.pricing_hypothesis,
                brief.landing_page_text,
            ]
        ).lower()

        if _contains_any_keyword(text, ["ai", "data", "personal", "automated"]):
            findings.append(
                AuditFinding(
                    category="privacy_risk",
                    severity="medium",
                    observation="The concept appears to depend on personal or workflow data, so trust language and data-minimisation choices will materially affect adoption.",
                    evidence_refs=["brief", "persona_responses"],
                    recommended_validation_question="Which minimum data fields are truly necessary for the first useful experience?",
                )
            )

        if _contains_any_keyword(text, ["best customer", "ideal customer only", "high value users only"]):
            findings.append(
                AuditFinding(
                    category="discrimination_risk",
                    severity="medium",
                    observation="The positioning language risks sounding exclusionary and should be reframed around use cases rather than identity labels.",
                    evidence_refs=["landing_page_text"],
                    recommended_validation_question="Can the segmentation be expressed in terms of workflow needs rather than demographic identity?",
                )
            )

        if _contains_any_keyword(text, ["medical", "legal", "finance", "education", "parent"]):
            findings.append(
                AuditFinding(
                    category="high_stakes_decision_risk",
                    severity="high",
                    observation="This concept touches a high-stakes domain and should not rely on AI validation alone for product, compliance, or messaging decisions.",
                    evidence_refs=["brief"],
                    recommended_validation_question="What expert or compliance review must happen before broader rollout?",
                )
            )

        privacy_reactions = [
            response.synthetic_user_id
            for response in responses
            if "privacy" in response.trust_concern.lower() or "intrusive" in response.sensitive_concern_if_any.lower()
        ]
        if privacy_reactions:
            findings.append(
                AuditFinding(
                    category="reporting_risk",
                    severity="low",
                    observation="Some personas signal trust concerns that should be reported as design risks rather than as fixed segment truths.",
                    evidence_refs=privacy_reactions[:5],
                    recommended_validation_question="Which trust concerns repeat across real user interviews, and how should the product present those trade-offs?",
                )
            )

        if not findings:
            findings.append(
                AuditFinding(
                    category="reporting_risk",
                    severity="low",
                    observation="No major sensitive-topic trigger was detected in this run, but the result should still be treated as pre-validation only.",
                    evidence_refs=["run_summary"],
                    recommended_validation_question="What real-user checks would most quickly falsify the strongest assumption in this concept?",
                )
            )
        return findings

    def planner(self, brief: FounderBrief, summary: dict[str, object], findings: list[AuditFinding]) -> list[str]:
        privacy_open_question = any(f.category == "privacy_risk" for f in findings)
        steps = [
            "Day 1: Rewrite the landing page headline around the most concrete workflow outcome rather than broad AI promise.",
            "Day 2: Interview 3 target users about current follow-up and coordination workarounds before showing the solution.",
            "Day 3: Show a low-fidelity concierge workflow and ask what data they would or would not share.",
            "Day 4: Test one pricing anchor with a trial-first option and capture resistance in plain language.",
            "Day 5: Compare reactions between one likely early adopter and one skeptical buyer in the same target segment.",
            "Day 6: Rewrite copy using the top objection and top trigger found in this run.",
            "Day 7: Decide whether to narrow the target workflow, change the proof requirement, or delay pricing pressure.",
        ]
        if privacy_open_question:
            steps.insert(3, "Day 3b: Validate a minimum-data experience and document which requested fields feel excessive.")
        return steps
