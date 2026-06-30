import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.domain.models import AuditFinding, FounderBrief, PanelSpec, SkepticReview
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.providers.factory import build_provider
from ai_validation_swarm.providers.openai_validation import OpenAIValidationProvider
from ai_validation_swarm.storage.files import save_persona, write_json
from ai_validation_swarm.validation.runner import run_validation


class FakeOpenAIResponsesClient:
    def __init__(self, payloads: list[dict]) -> None:
        self.payloads = list(payloads)
        self.calls: list[dict] = []
        self.config = SimpleNamespace(
            model="fake-live-model",
            transport="codex_cli",
            auth_source="codex_auth_file:test",
            provider_name="codex",
        )
        self.last_transport_metadata = {}

    def create_json_response(self, **kwargs):
        self.calls.append(kwargs)
        if not self.payloads:
            raise AssertionError("Fake client has no payloads left.")
        return self.payloads.pop(0)


def _payloads() -> list[dict]:
    return [
        {
            "first_impression": "The idea is useful if it removes real admin effort.",
            "pain_relevance": "The pain is real because follow-up work already fragments the week.",
            "solution_attractiveness": "The solution is attractive if the first setup is light.",
            "trust_concern": "I need proof that the workflow will not expose private data.",
            "pricing_reaction": "I would pay after a short proof period.",
            "likely_objection": "unclear setup effort",
            "what_would_make_them_try": "a low-risk trial with visible time savings",
            "what_would_make_them_reject": "too much setup before value",
            "sensitive_concern_if_any": "privacy expectations need to be explicit",
            "scorecard": {
                "problem_resonance": 4,
                "solution_attractiveness": 3,
                "willingness_to_pay": 3,
            },
            "themes": {"top_objection": "setup effort", "top_trigger": "visible time savings"},
        },
        {
            "summary": "The concept has promise but still depends on proof of setup effort and trust.",
            "challenged_assumptions": [
                {
                    "finding_id": "skeptic_setup_effort",
                    "severity": "medium",
                    "title": "Setup effort may be understated",
                    "observation": "The response supports value only if setup is light.",
                    "evidence_refs": ["raw_responses"],
                    "recommended_validation_question": "What setup step creates the first drop-off?",
                }
            ],
        },
        {
            "findings": [
                {
                    "category": "privacy_risk",
                    "severity": "medium",
                    "observation": "The study depends on workflow data and needs explicit trust boundaries.",
                    "evidence_refs": ["brief", "raw_responses"],
                    "recommended_validation_question": "Which fields can be omitted in the first trial?",
                }
            ]
        },
        {
            "next_steps": [
                "Run a concierge trial with one user and record setup friction.",
                "Test trust copy before asking for sensitive workflow data.",
            ]
        },
    ]


class OpenAIValidationProviderTest(unittest.TestCase):
    def test_maps_live_llm_json_into_validation_domain_models(self) -> None:
        client = FakeOpenAIResponsesClient(_payloads())
        provider = OpenAIValidationProvider(client, provider_name="codex")
        persona = generate_personas(count=1, random_seed=19)[0]
        brief = FounderBrief(
            brief_id="brief_001",
            project_name="Solo MVP",
            problem_statement="Founders lose time following up after user interviews.",
            target_market="solo founders",
            offered_solution="A research assistant that turns interview intent into evidence-backed next steps.",
            validation_goal="Find trust gaps and adoption barriers.",
        )

        response = provider.persona_response(persona, brief, "problem_validation/v1")
        review = provider.skeptic_review(brief, [persona], [response])
        audit = provider.sensitive_audit(brief, [persona], [response])
        plan = provider.planner(brief, {"top_objection": "setup effort"}, audit)

        self.assertEqual(provider.provider_name, "codex")
        self.assertEqual(provider.model_version, "codex:fake-live-model")
        self.assertEqual(response.synthetic_user_id, persona.profile.synthetic_user_id)
        self.assertEqual(response.scorecard["problem_resonance"], 4)
        self.assertIsInstance(review, SkepticReview)
        self.assertEqual(review.challenged_assumptions[0].finding_id, "skeptic_setup_effort")
        self.assertIsInstance(audit[0], AuditFinding)
        self.assertIn("concierge trial", plan[0])
        self.assertEqual(len(client.calls), 4)
        self.assertEqual(client.calls[0]["output_schema"]["required"][0], "first_impression")

    def test_factory_routes_codex_to_live_validation_provider_with_injected_client(self) -> None:
        client = FakeOpenAIResponsesClient(_payloads())
        provider = build_provider("codex", client_builder=lambda provider_name: client)

        self.assertIsInstance(provider, OpenAIValidationProvider)
        self.assertEqual(provider.provider_name, "codex")
        self.assertEqual(provider.transport, "codex_cli")

    def test_validation_run_contract_preserves_requested_provider_name(self) -> None:
        class NamedMockProvider:
            provider_name = "codex"
            model_version = "codex:fake-live-model"

            def __init__(self) -> None:
                from ai_validation_swarm.providers.mock import MockProvider

                self.delegate = MockProvider()

            def persona_response(self, persona, brief, protocol_id):
                return self.delegate.persona_response(persona, brief, protocol_id)

            def skeptic_review(self, brief, personas, responses):
                return self.delegate.skeptic_review(brief, personas, responses)

            def sensitive_audit(self, brief, personas, responses):
                return self.delegate.sensitive_audit(brief, personas, responses)

            def planner(self, brief, summary, findings):
                return self.delegate.planner(brief, summary, findings)

        personas = generate_personas(count=4, random_seed=23)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona_dir = root / "personas"
            run_root = root / "runs"
            brief_path = root / "brief.json"
            for persona in personas:
                save_persona(persona, persona_dir)
            write_json(
                brief_path,
                {
                    "brief_id": "brief_contract_provider",
                    "project_name": "Provider lineage",
                    "problem_statement": "Founders cannot see whether a run used mock or Codex.",
                    "target_market": "solo founders",
                    "offered_solution": "Expose provider lineage in evidence artifacts.",
                    "validation_goal": "Verify provider lineage.",
                },
            )

            archived = run_validation(
                brief_path=brief_path,
                persona_dir=persona_dir,
                panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=7),
                provider=NamedMockProvider(),
                run_root=run_root,
            )

            run_contract = json.loads((archived / "run_contract.json").read_text(encoding="utf-8"))
            self.assertEqual(run_contract["result"]["provider_name"], "codex")
            self.assertEqual(run_contract["result"]["model_name"], "codex:fake-live-model")


if __name__ == "__main__":
    unittest.main()
