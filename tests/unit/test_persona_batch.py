import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.cli.main import main
from ai_validation_swarm.personas.batch import enrich_persona_library, enrich_persona_library_to_target, list_valid_persona_ids
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.storage.files import load_persona, save_persona


class _FakeEnricher:
    def enrich(self, persona):
        persona.profile.audit_evidence_layer["persona_generation_method"] = "fake_llm_enrichment"
        persona.audit["persona_generation_method"] = "fake_llm_enrichment"
        persona.audit["llm_enrichment"] = {"provider": "fake"}
        return persona


class _FakeJudge:
    def judge(self, persona):
        return {"verdict": "pass", "provider": "fake"}


class PersonaBatchTest(unittest.TestCase):
    def test_enrich_persona_library_writes_enriched_outputs(self) -> None:
        personas = generate_personas(count=3, random_seed=17)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            for persona in personas:
                save_persona(persona, input_dir)

            result = enrich_persona_library(
                input_dir=input_dir,
                output_dir=output_dir,
                enricher=_FakeEnricher(),
                judge=_FakeJudge(),
                limit=None,
                resume=True,
            )

            self.assertEqual(result.processed_count, 3)
            self.assertEqual(result.succeeded_count, 3)
            self.assertEqual(result.failed_count, 0)
            loaded = load_persona(output_dir / "su_0001")
            self.assertEqual(loaded.audit["persona_generation_method"], "fake_llm_enrichment")
            self.assertEqual(loaded.audit["judge_review"]["verdict"], "pass")

    def test_enrich_persona_library_resume_skips_valid_existing_outputs(self) -> None:
        personas = generate_personas(count=2, random_seed=19)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            for persona in personas:
                save_persona(persona, input_dir)
            save_persona(personas[0], output_dir)

            result = enrich_persona_library(
                input_dir=input_dir,
                output_dir=output_dir,
                enricher=_FakeEnricher(),
                judge=None,
                limit=None,
                resume=True,
            )

            self.assertEqual(result.processed_count, 2)
            self.assertEqual(result.skipped_count, 1)
            self.assertEqual(result.succeeded_count, 1)

    def test_enrich_persona_library_limit_advances_past_resumed_outputs(self) -> None:
        personas = generate_personas(count=4, random_seed=23)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            for persona in personas:
                save_persona(persona, input_dir)

            first_batch = enrich_persona_library(
                input_dir=input_dir,
                output_dir=output_dir,
                enricher=_FakeEnricher(),
                judge=None,
                limit=2,
                resume=True,
                workers=2,
            )
            second_batch = enrich_persona_library(
                input_dir=input_dir,
                output_dir=output_dir,
                enricher=_FakeEnricher(),
                judge=None,
                limit=2,
                resume=True,
                workers=2,
            )

            self.assertEqual(first_batch.succeeded_count, 2)
            self.assertEqual(second_batch.succeeded_count, 2)
            self.assertEqual(second_batch.skipped_count, 2)
            self.assertTrue((output_dir / "su_0003").exists())
            self.assertTrue((output_dir / "su_0004").exists())

    def test_enrich_persona_library_parallel_workers_still_write_outputs(self) -> None:
        personas = generate_personas(count=3, random_seed=29)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            for persona in personas:
                save_persona(persona, input_dir)

            result = enrich_persona_library(
                input_dir=input_dir,
                output_dir=output_dir,
                enricher=_FakeEnricher(),
                judge=_FakeJudge(),
                limit=None,
                resume=True,
                workers=3,
            )

            self.assertEqual(result.succeeded_count, 3)
            self.assertEqual(result.failed_count, 0)
            self.assertTrue((output_dir / "su_0002" / "audit.json").exists())

    def test_list_valid_persona_ids_ignores_invalid_output_folders(self) -> None:
        personas = generate_personas(count=2, random_seed=31)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "output"
            save_persona(personas[0], output_dir)
            (output_dir / "broken").mkdir(parents=True, exist_ok=True)
            (output_dir / "broken" / "profile.json").write_text("{}", encoding="utf-8")

            valid_ids = list_valid_persona_ids(output_dir)

            self.assertEqual(valid_ids, ["su_0001"])

    def test_enrich_persona_library_to_target_reaches_requested_count(self) -> None:
        personas = generate_personas(count=5, random_seed=37)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            for persona in personas:
                save_persona(persona, input_dir)

            result = enrich_persona_library_to_target(
                input_dir=input_dir,
                output_dir=output_dir,
                enricher=_FakeEnricher(),
                judge=None,
                target_count=4,
                batch_size=2,
                resume=True,
                workers=1,
            )

            self.assertEqual(result.initial_valid_count, 0)
            self.assertEqual(result.final_valid_count, 4)
            self.assertEqual(result.target_count, 4)
            self.assertEqual(len(result.rounds), 2)
            self.assertEqual(result.stopped_reason, "target_reached")
            self.assertTrue(result.completed)
            self.assertEqual(result.excluded_persona_ids, [])

    def test_enrich_persona_library_to_target_stops_when_no_progress(self) -> None:
        personas = generate_personas(count=3, random_seed=41)

        class _AlwaysFailEnricher:
            def enrich(self, persona):
                raise RuntimeError("llm failed")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            for persona in personas:
                save_persona(persona, input_dir)

            result = enrich_persona_library_to_target(
                input_dir=input_dir,
                output_dir=output_dir,
                enricher=_AlwaysFailEnricher(),
                judge=None,
                target_count=2,
                batch_size=2,
                resume=True,
                workers=1,
                max_rounds=3,
                max_stall_rounds=1,
                max_persona_failures=1,
            )

            self.assertEqual(result.final_valid_count, 0)
            self.assertEqual(len(result.rounds), 2)
            self.assertEqual(result.stopped_reason, "no_remaining_eligible_personas")
            self.assertEqual(result.excluded_persona_ids, ["su_0001", "su_0002", "su_0003"])
            self.assertFalse(result.completed)

    def test_enrich_persona_library_to_target_retries_after_transient_failure(self) -> None:
        personas = generate_personas(count=2, random_seed=47)

        class _RetryOnceEnricher:
            def __init__(self) -> None:
                self.calls: dict[str, int] = {}

            def enrich(self, persona):
                persona_id = persona.profile.synthetic_user_id
                self.calls[persona_id] = self.calls.get(persona_id, 0) + 1
                if persona_id == "su_0001" and self.calls[persona_id] == 1:
                    raise RuntimeError("temporary timeout")
                persona.profile.audit_evidence_layer["persona_generation_method"] = "retry_once"
                persona.audit["persona_generation_method"] = "retry_once"
                return persona

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            for persona in personas:
                save_persona(persona, input_dir)

            result = enrich_persona_library_to_target(
                input_dir=input_dir,
                output_dir=output_dir,
                enricher=_RetryOnceEnricher(),
                judge=None,
                target_count=2,
                batch_size=1,
                resume=True,
                workers=1,
                max_stall_rounds=2,
            )

            self.assertTrue(result.completed)
            self.assertEqual(result.final_valid_count, 2)
            self.assertEqual(len(result.rounds), 3)
            self.assertEqual(result.rounds[0].batch.failed_count, 1)
            self.assertEqual(result.stopped_reason, "target_reached")

    def test_enrich_persona_library_to_target_skips_hard_failed_persona_and_continues(self) -> None:
        personas = generate_personas(count=4, random_seed=49)

        class _FirstPersonaAlwaysFails:
            def enrich(self, persona):
                if persona.profile.synthetic_user_id == "su_0001":
                    raise RuntimeError("persistent backend failure")
                persona.profile.audit_evidence_layer["persona_generation_method"] = "success_after_skip"
                persona.audit["persona_generation_method"] = "success_after_skip"
                return persona

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            for persona in personas:
                save_persona(persona, input_dir)

            result = enrich_persona_library_to_target(
                input_dir=input_dir,
                output_dir=output_dir,
                enricher=_FirstPersonaAlwaysFails(),
                judge=None,
                target_count=2,
                batch_size=1,
                resume=True,
                workers=1,
                max_stall_rounds=2,
                max_persona_failures=1,
            )

            self.assertTrue(result.completed)
            self.assertEqual(result.final_valid_count, 2)
            self.assertEqual(result.excluded_persona_ids, ["su_0001"])
            self.assertEqual(result.rounds[0].newly_excluded_persona_ids, ["su_0001"])
            self.assertEqual(result.stopped_reason, "target_reached")

    def test_inspect_openai_auth_cli_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "auth_summary.json"
            with patch(
                "ai_validation_swarm.cli.main._load_openai_runtime_config",
                return_value=type(
                    "FakeConfig",
                    (),
                    {
                        "api_key": "header.eyJzY3AiOlsiYXBpLnJlc3BvbnNlcy53cml0ZSJdLCJleHAiOjEyMzQ1Nn0.signature",
                        "auth_source": "fake",
                        "transport": "node_https",
                        "model": "gpt-5.4",
                        "profile": "chatgpt-5.4-high",
                        "model_reasoning_effort": "high",
                        "timeout_seconds": 120,
                        "codex_home_mode": "global",
                        "codex_home_path": "C:\\Users\\user\\.codex",
                        "codex_ignore_user_config": True,
                        "codex_ignore_rules": True,
                        "codex_cli_retries": 2,
                        "codex_cli_retry_backoff_seconds": 5,
                    },
                )(),
            ):
                stream = io.StringIO()
                with redirect_stdout(stream):
                    exit_code = main(["inspect-openai-auth", "--output", str(output_path)])

            self.assertEqual(exit_code, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["auth_source"], "fake")
            self.assertEqual(payload["has_api_responses_write_scope"], True)

    def test_probe_codex_auth_cli_writes_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "codex_probe.json"
            fake_client = type(
                "FakeClient",
                (),
                {
                    "create_json_response": staticmethod(
                        lambda **_: {"ok": True, "message": "codex probe succeeded"}
                    )
                },
            )()
            fake_config = type(
                "FakeConfig",
                (),
                {
                    "api_key": "header.eyJzY3AiOlsiYXBpLnJlc3BvbnNlcy53cml0ZSJdLCJleHAiOjEyMzQ1Nn0.signature",
                    "auth_source": "codex_auth_file:C:\\Users\\user\\.codex\\auth.json",
                    "transport": "codex_cli",
                    "model": "gpt-5.4",
                    "profile": "chatgpt-5.4-high",
                    "model_reasoning_effort": "high",
                    "timeout_seconds": 240,
                    "codex_home_mode": "global",
                    "codex_home_path": "C:\\Users\\user\\.codex",
                    "codex_ignore_user_config": True,
                    "codex_ignore_rules": True,
                    "codex_cli_retries": 2,
                    "codex_cli_retry_backoff_seconds": 5,
                },
            )()
            with patch(
                "ai_validation_swarm.cli.main._build_codex_probe_components",
                return_value=(fake_client, fake_config, Path("C:/codex.exe"), Path("C:/Users/user/.codex")),
            ):
                stream = io.StringIO()
                with redirect_stdout(stream):
                    exit_code = main(["probe-codex-auth", "--output", str(output_path)])

            self.assertEqual(exit_code, 0)
            payload = json.loads(output_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["ok"], True)
            self.assertEqual(payload["result"]["message"], "codex probe succeeded")

    def test_enrich_personas_cli_target_mode_writes_target_report(self) -> None:
        personas = generate_personas(count=4, random_seed=43)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            input_dir = root / "input"
            output_dir = root / "output"
            report_path = root / "report.json"
            for persona in personas:
                save_persona(persona, input_dir)

            with patch(
                "ai_validation_swarm.cli.main._build_persona_generation_components",
                return_value=(_FakeEnricher(), None),
            ):
                stream = io.StringIO()
                with redirect_stdout(stream):
                    exit_code = main(
                        [
                            "enrich-personas",
                            "--backend",
                            "codex",
                            "--input-dir",
                            str(input_dir),
                            "--output-dir",
                            str(output_dir),
                            "--target-count",
                            "3",
                            "--batch-size",
                            "2",
                            "--report",
                            str(report_path),
                        ]
                    )

            self.assertEqual(exit_code, 0)
            payload = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["mode"], "target")
            self.assertEqual(payload["final_valid_count"], 3)
            self.assertEqual(payload["completed"], True)
            self.assertEqual(len(payload["rounds"]), 2)
            self.assertEqual(payload["excluded_persona_ids"], [])


if __name__ == "__main__":
    unittest.main()
