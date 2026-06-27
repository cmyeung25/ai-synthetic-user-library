import unittest
import base64
import io
import json
import os
from pathlib import Path
import sys
from contextlib import redirect_stdout
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.cli.main import _load_live_llm_config, _load_openai_runtime_config, main
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.personas.llm import OpenAIPersonaEnricher, OpenAIPersonaJudge, _build_enrichment_payload
from ai_validation_swarm.providers.openai_client import (
    OpenAIProviderConfig,
    OpenAIProviderError,
    OpenAIResponsesClient,
    codex_exec_timeout_seconds,
    decode_codex_json_payload,
    extract_json_object,
    extract_codex_session_id,
    extract_output_text,
    is_retryable_codex_failure,
    load_codex_access_token,
    load_openai_provider_config,
    resolve_codex_cli_path,
    resolve_codex_home,
)


class _StubClient:
    def __init__(self, responses: list[dict[str, object]]) -> None:
        self.responses = responses
        self.calls: list[dict[str, str]] = []

    def create_json_response(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
        output_schema=None,
    ) -> dict[str, object]:
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "has_output_schema": str(output_schema is not None),
            }
        )
        if not self.responses:
            raise AssertionError("Stub client ran out of responses")
        return self.responses.pop(0)


class OpenAIPersonaToolsTest(unittest.TestCase):
    def test_extract_json_object_accepts_wrapped_text(self) -> None:
        payload = extract_json_object("prefix {\"ok\": true, \"score\": 3} suffix")
        self.assertEqual(payload["ok"], True)
        self.assertEqual(payload["score"], 3)

    def test_extract_output_text_supports_nested_response_shape(self) -> None:
        payload = {
            "output": [
                {
                    "content": [
                        {"type": "output_text", "text": "{\"hello\": \"world\"}"},
                    ]
                }
            ]
        }
        self.assertEqual(extract_output_text(payload), "{\"hello\": \"world\"}")

    def test_openai_persona_enricher_merges_content_and_marks_audit(self) -> None:
        personas = generate_personas(count=1, random_seed=41)
        persona = personas[0]
        client = _StubClient(
            [
                {
                    "values": {"core_values": ["clarity", "reliability", "calm execution"]},
                    "life_story": {"career_path": "Built a reputation by cleaning up messy operating processes."},
                    "behavior_profile": {"decision_blockers": ["unclear owner", "weak proof", "team retraining burden"]},
                    "problem_context": {"active_pain_points": ["handoff gaps", "follow-up drift", "tool sprawl"]},
                    "sensitive_reality_layer": {"public_explanation_preference": "brief, concrete, and respectful"},
                    "decision_policy": {"proof_requirements": ["a short trial workflow", "proof from similar operators"]},
                    "response_style": {"detail_tendency": "high"},
                    "narrative": "# Revised persona narrative",
                    "rationale": "Added more operational texture while keeping fixed facts intact.",
                }
            ]
        )
        config = OpenAIProviderConfig(api_key="test-key")

        enriched = OpenAIPersonaEnricher(client, config).enrich(persona)

        self.assertEqual(enriched.profile.values["core_values"][0], "clarity")
        self.assertEqual(enriched.profile.life_story["career_path"], "Built a reputation by cleaning up messy operating processes.")
        self.assertEqual(enriched.response_style["detail_tendency"], "high")
        self.assertEqual(enriched.narrative, "# Revised persona narrative")
        self.assertEqual(enriched.audit["llm_enrichment"]["provider"], "openai")
        self.assertEqual(enriched.profile.audit_evidence_layer["persona_generation_method"], "deterministic_seed_plus_openai_enrichment_v1")

    def test_openai_persona_enricher_uses_compact_prompt_payload(self) -> None:
        persona = generate_personas(count=1, random_seed=47)[0]
        client = _StubClient(
            [
                {
                    "values": {},
                    "life_story": {},
                    "behavior_profile": {},
                    "problem_context": {},
                    "sensitive_reality_layer": {},
                    "decision_policy": {},
                    "response_style": {},
                    "narrative": persona.narrative,
                    "rationale": "No-op response for prompt inspection.",
                }
            ]
        )
        config = OpenAIProviderConfig(api_key="test-key")

        OpenAIPersonaEnricher(client, config).enrich(persona)

        prompt = client.calls[0]["user_prompt"]
        payload = json.loads(prompt[prompt.index("{") :])
        legacy_payload = {
            "seed": persona.seed.to_dict(),
            "profile": persona.profile.to_dict(),
            "decision_policy": persona.decision_policy,
            "response_style": persona.response_style,
            "narrative": persona.narrative,
        }

        self.assertIn("identity_anchors", payload)
        self.assertIn("fixed_signals", payload)
        self.assertNotIn("profile", payload)
        self.assertNotIn("narrative", payload)
        self.assertLess(
            len(json.dumps(payload, ensure_ascii=False)),
            len(json.dumps(legacy_payload, ensure_ascii=False)),
        )

    def test_openai_persona_judge_records_scores(self) -> None:
        persona = generate_personas(count=1, random_seed=43)[0]
        client = _StubClient(
            [
                {
                    "verdict": "pass_with_minor_revisions",
                    "plausibility_score": 4,
                    "stereotype_risk_score": 2,
                    "panel_fit_score": 4,
                    "findings": ["Narrative is coherent but could use one stronger concrete frustration."],
                    "revision_hints": ["Tighten one daily workflow bottleneck."],
                    "rationale": "Mostly plausible with low stereotype risk.",
                }
            ]
        )
        config = OpenAIProviderConfig(api_key="test-key")

        result = OpenAIPersonaJudge(client, config).judge(persona)

        self.assertEqual(result["provider"], "openai")
        self.assertEqual(result["model"], "gpt-5.4")
        self.assertEqual(persona.audit["stereotype_risk_score"], 2)
        self.assertEqual(persona.profile.audit_evidence_layer["stereotype_risk_score"], 2)

    def test_codex_transport_updates_audit_provider_labels(self) -> None:
        persona = generate_personas(count=1, random_seed=45)[0]
        client = _StubClient(
            [
                {
                    "values": {"core_values": ["clarity"]},
                    "life_story": {"career_path": "Moved into operations after a customer support start."},
                    "behavior_profile": {"decision_blockers": ["unclear owner"]},
                    "problem_context": {"active_pain_points": ["handoff gaps"]},
                    "sensitive_reality_layer": {"public_explanation_preference": "direct"},
                    "decision_policy": {"proof_requirements": ["one small live trial"]},
                    "response_style": {"detail_tendency": "medium"},
                    "narrative": "# Codex persona narrative",
                    "rationale": "Codex enrichment probe.",
                },
                {
                    "verdict": "pass",
                    "plausibility_score": 4,
                    "stereotype_risk_score": 2,
                    "panel_fit_score": 4,
                    "findings": [],
                    "revision_hints": [],
                    "rationale": "Codex judge probe.",
                },
            ]
        )
        config = OpenAIProviderConfig(api_key="test-key", transport="codex_cli")

        enriched = OpenAIPersonaEnricher(client, config).enrich(persona)
        result = OpenAIPersonaJudge(client, config).judge(enriched)

        self.assertEqual(enriched.audit["llm_enrichment"]["provider"], "codex")
        self.assertEqual(enriched.audit["persona_generation_method"], "deterministic_seed_plus_codex_enrichment_v1")
        self.assertEqual(result["provider"], "codex")

    def test_agnes_transport_updates_audit_provider_labels(self) -> None:
        persona = generate_personas(count=1, random_seed=49)[0]
        client = _StubClient(
            [
                {
                    "values": {"core_values": ["clarity"]},
                    "life_story": {"career_path": "Built trust through practical fixes instead of big promises."},
                    "behavior_profile": {"decision_blockers": ["unclear proof"]},
                    "problem_context": {"active_pain_points": ["workflow drift"]},
                    "sensitive_reality_layer": {"public_explanation_preference": "specific"},
                    "decision_policy": {"proof_requirements": ["one live example"]},
                    "response_style": {"detail_tendency": "medium"},
                    "narrative": "# Agnes persona narrative",
                    "rationale": "Agnes enrichment probe.",
                }
            ]
        )
        config = OpenAIProviderConfig(api_key="test-key", provider_name="agnes", model="agnes-2.0-flash", profile="agnes-2.0-flash")

        enriched = OpenAIPersonaEnricher(client, config).enrich(persona)

        self.assertEqual(enriched.audit["llm_enrichment"]["provider"], "agnes")
        self.assertEqual(enriched.audit["persona_generation_method"], "deterministic_seed_plus_agnes_enrichment_v2")
        self.assertEqual(enriched.audit["llm_enrichment"]["prompt_version"], "persona-enrichment/v2")

    def test_non_agnes_enrichment_stays_on_v1_prompt(self) -> None:
        persona = generate_personas(count=1, random_seed=51)[0]
        client = _StubClient(
            [
                {
                    "values": {},
                    "life_story": {},
                    "behavior_profile": {},
                    "problem_context": {},
                    "sensitive_reality_layer": {},
                    "decision_policy": {},
                    "response_style": {},
                    "narrative": persona.narrative,
                    "rationale": "Prompt version probe.",
                }
            ]
        )
        config = OpenAIProviderConfig(api_key="test-key", transport="codex_cli")

        enriched = OpenAIPersonaEnricher(client, config).enrich(persona)

        self.assertEqual(enriched.audit["persona_generation_method"], "deterministic_seed_plus_codex_enrichment_v1")
        self.assertEqual(enriched.audit["llm_enrichment"]["prompt_version"], "persona-enrichment/v1")

    def test_load_codex_access_token_reads_chatgpt_auth_file(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            auth_path = Path(tmp) / "auth.json"
            auth_path.write_text(
                (
                    "{"
                    "\"auth_mode\":\"chatgpt\","
                    "\"tokens\":{\"access_token\":\"abc123\",\"refresh_token\":\"rt\"}"
                    "}"
                ),
                encoding="utf-8",
            )
            self.assertEqual(load_codex_access_token(auth_path), "abc123")

    def test_load_openai_provider_config_falls_back_to_codex_auth_file(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            auth_path = Path(tmp) / "auth.json"
            auth_path.write_text(
                (
                    "{"
                    "\"auth_mode\":\"chatgpt\","
                    "\"tokens\":{\"access_token\":\"abc123\"}"
                    "}"
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "AI_VALIDATION_CODEX_AUTH_FILE": str(auth_path),
                    "AI_VALIDATION_OPENAI_MODEL": "gpt-5.4",
                },
                clear=True,
            ):
                config = load_openai_provider_config()

        self.assertEqual(config.api_key, "abc123")
        self.assertTrue(config.auth_source.startswith("codex_auth_file:"))
        self.assertEqual(config.transport, "codex_cli")
        self.assertEqual(config.model_reasoning_effort, "high")
        self.assertEqual(config.timeout_seconds, 240)
        self.assertEqual(config.codex_home_mode, "global")
        self.assertEqual(config.codex_ignore_user_config, True)
        self.assertEqual(config.codex_ignore_rules, True)
        self.assertEqual(config.codex_cli_retries, 2)
        self.assertEqual(config.codex_cli_retry_backoff_seconds, 5)

    def test_load_openai_provider_config_prefers_codex_auth_for_codex_backend(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            auth_path = Path(tmp) / "auth.json"
            auth_path.write_text(
                (
                    "{"
                    "\"auth_mode\":\"chatgpt\","
                    "\"tokens\":{\"access_token\":\"codex_auth_token\"}"
                    "}"
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "OPENAI_API_KEY": "sk-openai-key",
                    "AI_VALIDATION_CODEX_AUTH_FILE": str(auth_path),
                },
                clear=True,
            ):
                config = load_openai_provider_config(
                    prefer_codex_auth=True,
                    force_transport="codex_cli",
                )

        self.assertEqual(config.api_key, "codex_auth_token")
        self.assertEqual(config.transport, "codex_cli")
        self.assertTrue(config.auth_source.startswith("codex_auth_file:"))
        self.assertEqual(config.codex_home_mode, "global")
        self.assertEqual(config.timeout_seconds, 240)

    def test_load_openai_provider_config_honors_custom_timeout_default_when_env_unset(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            auth_path = Path(tmp) / "auth.json"
            auth_path.write_text(
                (
                    "{"
                    "\"auth_mode\":\"chatgpt\","
                    "\"tokens\":{\"access_token\":\"codex_auth_token\"}"
                    "}"
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "AI_VALIDATION_CODEX_AUTH_FILE": str(auth_path),
                },
                clear=True,
            ):
                config = load_openai_provider_config(
                    prefer_codex_auth=True,
                    force_transport="codex_sdk_node",
                    timeout_default=360,
                )

        self.assertEqual(config.timeout_seconds, 360)

    def test_load_openai_provider_config_supports_agnes_overrides(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AGNES_API_KEY": "sk-agnes-key",
                "AI_VALIDATION_LLM_MODEL": "agnes-2.0-flash",
            },
            clear=True,
        ):
            config = load_openai_provider_config(
                force_transport="node_https",
                force_provider_name="agnes",
                force_api_key_env="AGNES_API_KEY",
                default_model="agnes-2.0-flash",
                default_profile="agnes-2.0-flash",
                default_api_base="https://apihub.agnes-ai.com/v1",
            )

        self.assertEqual(config.api_key, "sk-agnes-key")
        self.assertEqual(config.provider_name, "agnes")
        self.assertEqual(config.model, "agnes-2.0-flash")
        self.assertEqual(config.profile, "agnes-2.0-flash")
        self.assertEqual(config.api_base, "https://apihub.agnes-ai.com/v1")
        self.assertEqual(config.auth_source, "api_key_env:AGNES_API_KEY")

    def test_load_live_llm_config_uses_agnes_defaults_for_agnes_backend(self) -> None:
        with patch.dict(
            os.environ,
            {
                "AGNES_API_KEY": "sk-agnes-key",
            },
            clear=True,
        ):
            config = _load_live_llm_config("agnes")

        self.assertEqual(config.provider_name, "agnes")
        self.assertEqual(config.model, "agnes-2.0-flash")
        self.assertEqual(config.profile, "agnes-2.0-flash")
        self.assertEqual(config.api_base, "https://apihub.agnes-ai.com/v1")
        self.assertEqual(config.transport, "powershell_webrequest")
        self.assertEqual(config.auth_source, "api_key_env:AGNES_API_KEY")

    def test_load_openai_runtime_config_now_defaults_to_codex_from_repo_config(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            auth_path = Path(tmp) / "auth.json"
            auth_path.write_text(
                (
                    "{"
                    "\"auth_mode\":\"chatgpt\","
                    "\"tokens\":{\"access_token\":\"codex_auth_token\"}"
                    "}"
                ),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "AI_VALIDATION_CODEX_AUTH_FILE": str(auth_path),
                },
                clear=True,
            ):
                config = _load_openai_runtime_config()

        self.assertEqual(config.transport, "codex_cli")
        self.assertEqual(config.api_key, "codex_auth_token")
        self.assertTrue(config.auth_source.startswith("codex_auth_file:"))

    def test_build_parser_uses_repo_runtime_defaults_for_live_commands(self) -> None:
        from ai_validation_swarm.cli.main import _build_parser

        parser = _build_parser()
        parsed = parser.parse_args([
            "run-facilitated-interview",
            "--persona-id", "su_0001",
            "--research-goal", "Understand a problem",
        ])

        self.assertEqual(parsed.backend, "codex")
        self.assertIsNone(parsed.model)

    def test_agnes_responses_requests_attach_enable_thinking(self) -> None:
        config = OpenAIProviderConfig(
            api_key="test-key",
            provider_name="agnes",
            model="agnes-2.0-flash",
            transport="python_urllib",
            agnes_enable_thinking=True,
        )
        client = OpenAIResponsesClient(config)
        captured: dict[str, object] = {}

        def fake_response(body):
            captured.update(body)
            return {"output_text": '{"ok": true}'}

        with patch.object(client, "_create_response_via_python", side_effect=fake_response):
            result = client.create_json_response(
                system_prompt="Return JSON only.",
                user_prompt="Set ok=true.",
                output_schema={
                    "type": "object",
                    "required": ["ok"],
                    "properties": {"ok": {"type": "boolean"}},
                },
            )

        self.assertEqual(result, {"ok": True})
        self.assertEqual(
            captured.get("chat_template_kwargs"),
            {"enable_thinking": True},
        )

    def test_agnes_chat_completions_attach_enable_thinking(self) -> None:
        config = OpenAIProviderConfig(
            api_key="test-key",
            provider_name="agnes",
            model="agnes-2.0-flash",
            transport="python_urllib",
            agnes_enable_thinking=True,
        )
        client = OpenAIResponsesClient(config)
        captured: dict[str, object] = {}

        def fake_chat(body):
            captured.update(body)
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"ok": true, "path": "chat_completions"}',
                        }
                    }
                ]
            }

        with patch.object(
            client,
            "_create_response_via_python",
            side_effect=OpenAIProviderError("OpenAI Responses API request failed: Remote end closed connection without response"),
        ):
            with patch.object(client, "_create_chat_completion_via_python", side_effect=fake_chat):
                result = client.create_json_response(
                    system_prompt="Return JSON only.",
                    user_prompt="Set ok=true and path=chat_completions.",
                    output_schema={
                        "type": "object",
                        "required": ["ok", "path"],
                        "properties": {
                            "ok": {"type": "boolean"},
                            "path": {"type": "string"},
                        },
                    },
                )

        self.assertEqual(result, {"ok": True, "path": "chat_completions"})
        self.assertEqual(
            captured.get("chat_template_kwargs"),
            {"enable_thinking": True},
        )

    def test_agnes_falls_back_to_chat_completions_after_responses_failure(self) -> None:
        config = OpenAIProviderConfig(
            api_key="test-key",
            provider_name="agnes",
            model="agnes-2.0-flash",
            transport="python_urllib",
        )
        client = OpenAIResponsesClient(config)
        with patch.object(
            client,
            "_create_response_via_python",
            side_effect=OpenAIProviderError("OpenAI Responses API request failed: Remote end closed connection without response"),
        ):
            with patch.object(
                client,
                "_create_chat_completion_via_python",
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": '{"ok": true, "path": "chat_completions"}',
                            }
                        }
                    ],
                    "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15},
                },
            ) as chat_mock:
                result = client.create_json_response(
                    system_prompt="Return JSON only.",
                    user_prompt="Set ok=true and path=chat_completions.",
                    output_schema={
                        "type": "object",
                        "required": ["ok", "path"],
                        "properties": {
                            "ok": {"type": "boolean"},
                            "path": {"type": "string"},
                        },
                    },
                )

        self.assertEqual(result, {"ok": True, "path": "chat_completions"})
        self.assertEqual(client.last_transport_metadata["fallback_transport"], "chat_completions")
        self.assertEqual(client.last_transport_metadata["usage"]["total_tokens"], 15)
        chat_mock.assert_called_once()

    def test_multimodal_json_response_attaches_input_image(self) -> None:
        config = OpenAIProviderConfig(
            api_key="test-key",
            transport="python_urllib",
        )
        client = OpenAIResponsesClient(config)
        captured: dict[str, object] = {}

        def fake_response(body):
            captured.update(body)
            return {"output_text": '{"ok": true, "mode": "image"}'}

        image_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO6p8s8AAAAASUVORK5CYII="
        )
        with tempfile.TemporaryDirectory() as tmp:
            image_path = Path(tmp) / "stimulus.png"
            image_path.write_bytes(image_bytes)
            with patch.object(client, "_create_response_via_python", side_effect=fake_response):
                result = client.create_json_response_from_input_items(
                    input_items=[
                        {"role": "system", "content": [{"type": "input_text", "text": "Return JSON only."}]},
                        {
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": "Inspect the screenshot."},
                                {
                                    "type": "input_image",
                                    "image_url": f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}",
                                },
                            ],
                        },
                    ],
                    output_schema={
                        "type": "object",
                        "required": ["ok", "mode"],
                        "properties": {
                            "ok": {"type": "boolean"},
                            "mode": {"type": "string"},
                        },
                    },
                )

        self.assertEqual(result, {"ok": True, "mode": "image"})
        self.assertEqual(captured["input"][1]["content"][1]["type"], "input_image")
        self.assertTrue(captured["input"][1]["content"][1]["image_url"].startswith("data:image/png;base64,"))

    def test_codex_transport_rejects_multimodal_json_response(self) -> None:
        config = OpenAIProviderConfig(
            api_key="test-key",
            transport="codex_cli",
            workspace_root=str(ROOT),
            codex_home_mode="global",
            codex_home_path=str(ROOT),
            codex_cli_path="codex",
        )
        client = OpenAIResponsesClient(config)

        with self.assertRaises(OpenAIProviderError) as ctx:
            client.create_json_response_from_input_items(
                input_items=[
                    {"role": "system", "content": [{"type": "input_text", "text": "Return JSON only."}]},
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": "Inspect the screenshot."},
                            {"type": "input_image", "image_url": "data:image/png;base64,abc"},
                        ],
                    },
                ],
                output_schema={"type": "object"},
            )

        self.assertIn("Multimodal inputs are not supported for codex transports", str(ctx.exception))

    def test_multimodal_json_response_supports_multiple_input_images(self) -> None:
        config = OpenAIProviderConfig(
            api_key="test-key",
            transport="python_urllib",
        )
        client = OpenAIResponsesClient(config)
        captured: dict[str, object] = {}

        def fake_response(body):
            captured.update(body)
            return {"output_text": '{"ok": true, "mode": "flow"}'}

        image_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO6p8s8AAAAASUVORK5CYII="
        )
        with patch.object(client, "_create_response_via_python", side_effect=fake_response):
            result = client.create_json_response_from_input_items(
                input_items=[
                    {"role": "system", "content": [{"type": "input_text", "text": "Return JSON only."}]},
                    {
                        "role": "user",
                        "content": [
                            {"type": "input_text", "text": "Inspect the flow."},
                            {
                                "type": "input_image",
                                "image_url": f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}",
                            },
                            {"type": "input_text", "text": "SCREEN 2"},
                            {
                                "type": "input_image",
                                "image_url": f"data:image/png;base64,{base64.b64encode(image_bytes).decode('ascii')}",
                            },
                        ],
                    },
                ],
                output_schema={
                    "type": "object",
                    "required": ["ok", "mode"],
                    "properties": {
                        "ok": {"type": "boolean"},
                        "mode": {"type": "string"},
                    },
                },
            )

        self.assertEqual(result, {"ok": True, "mode": "flow"})
        image_items = [
            item for item in captured["input"][1]["content"]
            if item.get("type") == "input_image"
        ]
        self.assertEqual(len(image_items), 2)

    def test_agnes_responses_transport_retries_retryable_failure_then_succeeds(self) -> None:
        config = OpenAIProviderConfig(
            api_key="test-key",
            provider_name="agnes",
            model="agnes-2.0-flash",
            transport="python_urllib",
            agnes_transport_retries=1,
            agnes_transport_retry_backoff_seconds=1,
        )
        client = OpenAIResponsesClient(config)
        calls = {"count": 0}

        def fake_response(body):
            del body
            calls["count"] += 1
            if calls["count"] == 1:
                raise OpenAIProviderError(
                    "OpenAI Responses API request failed: Remote end closed connection without response"
                )
            return {"output_text": '{"ok": true, "attempt": 2}'}

        with patch.object(client, "_create_response_via_python", side_effect=fake_response):
            with patch("time.sleep") as sleep_mock:
                result = client.create_json_response(
                    system_prompt="Return JSON only.",
                    user_prompt="Set ok=true and attempt=2.",
                    output_schema={
                        "type": "object",
                        "required": ["ok", "attempt"],
                        "properties": {
                            "ok": {"type": "boolean"},
                            "attempt": {"type": "integer"},
                        },
                    },
                )

        self.assertEqual(result, {"ok": True, "attempt": 2})
        self.assertEqual(calls["count"], 2)
        sleep_mock.assert_called_once_with(1)

    def test_agnes_chat_completions_transport_retries_after_fallback(self) -> None:
        config = OpenAIProviderConfig(
            api_key="test-key",
            provider_name="agnes",
            model="agnes-2.0-flash",
            transport="python_urllib",
            agnes_transport_retries=1,
            agnes_transport_retry_backoff_seconds=1,
        )
        client = OpenAIResponsesClient(config)
        chat_calls = {"count": 0}

        def fake_chat(body):
            del body
            chat_calls["count"] += 1
            if chat_calls["count"] == 1:
                raise OpenAIProviderError("OpenAI Chat Completions API request failed: socket hang up")
            return {
                "choices": [
                    {
                        "message": {
                            "content": '{"ok": true, "path": "chat_completions_retry"}',
                        }
                    }
                ]
            }

        with patch.object(
            client,
            "_create_response_via_python",
            side_effect=OpenAIProviderError("OpenAI Responses API request failed: response body was not a JSON object"),
        ):
            with patch.object(client, "_create_chat_completion_via_python", side_effect=fake_chat):
                with patch("time.sleep") as sleep_mock:
                    result = client.create_json_response(
                        system_prompt="Return JSON only.",
                        user_prompt="Set ok=true and path=chat_completions_retry.",
                        output_schema={
                            "type": "object",
                            "required": ["ok", "path"],
                            "properties": {
                                "ok": {"type": "boolean"},
                                "path": {"type": "string"},
                            },
                        },
                    )

        self.assertEqual(result, {"ok": True, "path": "chat_completions_retry"})
        self.assertEqual(chat_calls["count"], 2)
        self.assertEqual(client.last_transport_metadata["fallback_transport"], "chat_completions")
        sleep_mock.assert_called_once_with(1)

    def test_agnes_can_request_plain_text_after_responses_failure(self) -> None:
        config = OpenAIProviderConfig(
            api_key="test-key",
            provider_name="agnes",
            model="agnes-2.0-flash",
            transport="python_urllib",
        )
        client = OpenAIResponsesClient(config)
        with patch.object(
            client,
            "_create_response_via_python",
            side_effect=OpenAIProviderError("OpenAI Responses API request failed: Remote end closed connection without response"),
        ):
            with patch.object(
                client,
                "_create_chat_completion_via_python",
                return_value={
                    "choices": [
                        {
                            "message": {
                                "content": "我通常到對數先發現漏記。",
                            }
                        }
                    ],
                    "usage": {"input_tokens": 8, "output_tokens": 4, "total_tokens": 12},
                },
            ) as chat_mock:
                result = client.create_text_response(
                    system_prompt="Reply naturally.",
                    user_prompt="What happens in real life?",
                )

        self.assertEqual(result, "我通常到對數先發現漏記。")
        self.assertEqual(client.last_transport_metadata["fallback_transport"], "chat_completions")
        self.assertEqual(client.last_transport_metadata["response_format"], "text")
        self.assertEqual(client.last_transport_metadata["usage"]["total_tokens"], 12)
        chat_mock.assert_called_once()

    def test_is_retryable_codex_failure_matches_models_refresh_errors(self) -> None:
        self.assertTrue(
            is_retryable_codex_failure(
                "ERROR codex_models_manager::manager: failed to refresh available models: stream disconnected before completion"
            )
        )
        self.assertFalse(is_retryable_codex_failure("Codex CLI transport timed out after 270 seconds."))

    def test_build_enrichment_payload_preserves_anchor_shape(self) -> None:
        persona = generate_personas(count=1, random_seed=53)[0]

        payload = _build_enrichment_payload(persona)

        self.assertIn("identity_anchors", payload)
        self.assertIn("fixed_signals", payload)
        self.assertEqual(payload["identity_anchors"]["name"], persona.profile.basic_identity["name"])
        self.assertEqual(payload["current_decision_policy"], persona.decision_policy)
        self.assertEqual(payload["current_response_style"], persona.response_style)

    def test_codex_exec_timeout_seconds_adds_buffer(self) -> None:
        config = OpenAIProviderConfig(api_key="test-key", timeout_seconds=240)
        self.assertEqual(codex_exec_timeout_seconds(config), 270)

    def test_resolve_codex_home_uses_workspace_candidate_in_global_mode(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            workspace_root = Path(tmp) / "workspace"
            auth_path = workspace_root / ".codex" / "auth.json"
            auth_path.parent.mkdir(parents=True, exist_ok=True)
            auth_path.write_text("{}", encoding="utf-8")
            config = OpenAIProviderConfig(
                api_key="test-key",
                workspace_root=str(workspace_root),
                codex_auth_file=str(auth_path),
                codex_home_mode="global",
            )

            resolved = resolve_codex_home(config)

        self.assertEqual(resolved, auth_path.parent)

    def test_resolve_codex_home_falls_back_to_local_when_global_home_not_writable(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            workspace_root = Path(tmp) / "workspace"
            workspace_root.mkdir(parents=True, exist_ok=True)
            auth_path = Path(tmp) / ".codex" / "auth.json"
            auth_path.parent.mkdir(parents=True, exist_ok=True)
            auth_path.write_text(
                (
                    "{"
                    "\"auth_mode\":\"chatgpt\","
                    "\"tokens\":{\"access_token\":\"abc123\"}"
                    "}"
                ),
                encoding="utf-8",
            )
            config = OpenAIProviderConfig(
                api_key="test-key",
                workspace_root=str(workspace_root),
                codex_auth_file=str(auth_path),
                codex_home_mode="global",
            )

            resolved = resolve_codex_home(config)

        self.assertEqual(resolved, workspace_root / ".codex-cli-home")

    def test_resolve_codex_home_local_mode_allows_existing_local_auth_file(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            workspace_root = Path(tmp) / "workspace"
            local_home = workspace_root / ".codex-cli-home"
            local_home.mkdir(parents=True, exist_ok=True)
            auth_path = local_home / "auth.json"
            auth_path.write_text(
                (
                    "{"
                    "\"auth_mode\":\"chatgpt\","
                    "\"tokens\":{\"access_token\":\"abc123\"}"
                    "}"
                ),
                encoding="utf-8",
            )
            config = OpenAIProviderConfig(
                api_key="test-key",
                workspace_root=str(workspace_root),
                codex_auth_file=str(auth_path),
                codex_home_mode="local",
            )

            resolved = resolve_codex_home(config)

        self.assertEqual(resolved, local_home)

    def test_resolve_codex_cli_path_prefers_windows_install_location(self) -> None:
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            codex_exe = Path(tmp) / "OpenAI" / "Codex" / "bin" / "stable-build" / "codex.exe"
            codex_exe.parent.mkdir(parents=True, exist_ok=True)
            codex_exe.write_text("", encoding="utf-8")
            config = OpenAIProviderConfig(api_key="test-key")

            with patch.dict(os.environ, {"LOCALAPPDATA": tmp}, clear=False):
                with patch("shutil.which", return_value="C:\\stub\\codex.cmd"):
                    resolved = resolve_codex_cli_path(config)

        self.assertEqual(resolved, str(codex_exe))

    def test_codex_cli_timeout_error_is_compact(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as tmp:
            config = OpenAIProviderConfig(
                api_key="test-key",
                transport="codex_cli",
                timeout_seconds=240,
                workspace_root=tmp,
                codex_home_mode="global",
                codex_home_path=tmp,
                codex_cli_path="codex",
            )
            client = OpenAIResponsesClient(config)
            with patch(
                "subprocess.run",
                side_effect=subprocess.TimeoutExpired(cmd=["codex", "exec", "huge prompt"], timeout=270),
            ):
                with self.assertRaises(OpenAIProviderError) as ctx:
                    client.create_json_response(
                        system_prompt="Return JSON only.",
                        user_prompt="Generate a structured persona.",
                        output_schema={"type": "object"},
                    )

        message = str(ctx.exception)
        self.assertIn("timed out after 270 seconds", message)
        self.assertNotIn("huge prompt", message)
        self.assertNotIn("Transport requirement", message)

    def test_codex_cli_retries_retryable_failure_once_then_succeeds(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as tmp:
            workspace_root = Path(tmp)
            auth_path = workspace_root / ".codex-cli-home" / "auth.json"
            auth_path.parent.mkdir(parents=True, exist_ok=True)
            auth_path.write_text(
                (
                    "{"
                    "\"auth_mode\":\"chatgpt\","
                    "\"tokens\":{\"access_token\":\"abc123\"}"
                    "}"
                ),
                encoding="utf-8",
            )
            config = OpenAIProviderConfig(
                api_key="test-key",
                transport="codex_cli",
                timeout_seconds=90,
                workspace_root=str(workspace_root),
                codex_auth_file=str(auth_path),
                codex_home_mode="local",
                codex_cli_path="codex",
                codex_cli_retries=1,
                codex_cli_retry_backoff_seconds=0,
            )
            client = OpenAIResponsesClient(config)
            calls = {"count": 0}

            def _fake_run(command, **kwargs):
                calls["count"] += 1
                if calls["count"] == 1:
                    return subprocess.CompletedProcess(
                        command,
                        returncode=1,
                        stdout="",
                        stderr=(
                            "2026-06-18T01:06:57.150294Z ERROR codex_models_manager::manager: "
                            "failed to refresh available models: stream disconnected before completion: "
                            "error sending request for url (https://chatgpt.com/backend-api/codex/models?client_version=0.140.0)"
                        ),
                    )
                output_path = Path(command[command.index("-o") + 1])
                output_path.write_text('{"json_payload_b64":"eyJvayI6dHJ1ZX0="}', encoding="utf-8")
                return subprocess.CompletedProcess(command, returncode=0, stdout="", stderr="")

            with patch("subprocess.run", side_effect=_fake_run):
                result = client.create_json_response(
                    system_prompt="Return exactly one JSON object that matches the schema.",
                    user_prompt="Set ok=true.",
                    output_schema={
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["ok"],
                        "properties": {"ok": {"type": "boolean"}},
                    },
                )

        self.assertEqual(calls["count"], 2)
        self.assertEqual(result, {"ok": True})

    def test_codex_cli_auto_mode_accepts_direct_json_for_ephemeral_turn(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as tmp:
            config = OpenAIProviderConfig(
                api_key="test-key",
                transport="codex_cli",
                workspace_root=tmp,
                codex_home_mode="global",
                codex_home_path=tmp,
                codex_cli_path="codex",
                codex_cli_output_mode="auto",
            )
            client = OpenAIResponsesClient(config)
            commands = []

            def _fake_run(command, **kwargs):
                commands.append(command)
                output_path = Path(command[command.index("-o") + 1])
                output_path.write_text('{"json_payload":"{\\"ok\\":true,\\"mode\\":\\"direct\\"}"}', encoding="utf-8")
                return subprocess.CompletedProcess(command, returncode=0, stdout="", stderr="")

            with patch("subprocess.run", side_effect=_fake_run):
                result = client.create_json_response(
                    system_prompt="Return JSON only.",
                    user_prompt="Set ok=true and mode=direct.",
                    output_schema={
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["ok", "mode"],
                        "properties": {
                            "ok": {"type": "boolean"},
                            "mode": {"type": "string"},
                        },
                    },
                )

        self.assertEqual(result, {"ok": True, "mode": "direct"})
        self.assertIn("schema-direct.json", commands[0][commands[0].index("--output-schema") + 1])

    def test_codex_cli_auto_mode_falls_back_to_wrapper_after_direct_parse_failure(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as tmp:
            config = OpenAIProviderConfig(
                api_key="test-key",
                transport="codex_cli",
                workspace_root=tmp,
                codex_home_mode="global",
                codex_home_path=tmp,
                codex_cli_path="codex",
                codex_cli_output_mode="auto",
            )
            client = OpenAIResponsesClient(config)
            commands = []

            def _fake_run(command, **kwargs):
                commands.append(command)
                output_path = Path(command[command.index("-o") + 1])
                schema_path = str(command[command.index("--output-schema") + 1]).replace("\\", "/")
                if "schema-direct.json" in schema_path:
                    output_path.write_text("not json", encoding="utf-8")
                else:
                    output_path.write_text('{"json_payload_b64":"eyJvayI6dHJ1ZSwibW9kZSI6IndyYXBwZXIifQ=="}', encoding="utf-8")
                return subprocess.CompletedProcess(command, returncode=0, stdout="", stderr="")

            with patch("subprocess.run", side_effect=_fake_run):
                result = client.create_json_response(
                    system_prompt="Return JSON only.",
                    user_prompt="Set ok=true and mode=wrapper.",
                    output_schema={
                        "type": "object",
                        "additionalProperties": False,
                        "required": ["ok", "mode"],
                        "properties": {
                            "ok": {"type": "boolean"},
                            "mode": {"type": "string"},
                        },
                    },
                )

        self.assertEqual(result, {"ok": True, "mode": "wrapper"})
        self.assertEqual(len(commands), 2)

    def test_codex_cli_persistent_turn_captures_and_resumes_exact_thread(self) -> None:
        import subprocess

        with tempfile.TemporaryDirectory() as tmp:
            config = OpenAIProviderConfig(
                api_key="test-key",
                transport="codex_cli",
                workspace_root=tmp,
                codex_home_mode="global",
                codex_home_path=tmp,
                codex_cli_path="codex",
            )
            client = OpenAIResponsesClient(config)
            commands = []

            def _fake_run(command, **kwargs):
                commands.append(command)
                output_path = Path(command[command.index("-o") + 1])
                output_path.write_text('{"ok":true}', encoding="utf-8")
                return subprocess.CompletedProcess(
                    command,
                    returncode=0,
                    stdout='{"type":"thread.started","thread_id":"thread-123"}\n',
                    stderr="",
                )

            with patch("subprocess.run", side_effect=_fake_run):
                client.create_json_response(
                    system_prompt="Persona context",
                    user_prompt="First turn",
                    persist_codex_session=True,
                )
                self.assertEqual(client.last_transport_metadata["codex_session_id"], "thread-123")
                client.create_json_response(
                    system_prompt="Continue",
                    user_prompt="Second turn",
                    codex_session_id="thread-123",
                    persist_codex_session=True,
                )

        self.assertNotIn("--ephemeral", commands[0])
        self.assertIn("--json", commands[0])
        self.assertNotIn("resume", commands[0])
        self.assertEqual(commands[1][1:3], ["exec", "resume"])
        self.assertIn("thread-123", commands[1])
        self.assertNotIn("-C", commands[1])

    def test_generate_personas_openai_backend_fails_cleanly_without_credentials(self) -> None:
        stream = io.StringIO()
        with patch.dict(os.environ, {}, clear=True):
            with redirect_stdout(stream):
                exit_code = main(["generate-personas", "--count", "1", "--backend", "openai"])

        self.assertEqual(exit_code, 1)
        self.assertIn("LLM credentials are missing for provider 'openai'", stream.getvalue())

    def test_codex_payload_decoder_accepts_missing_padding_and_whitespace(self) -> None:
        encoded = base64.b64encode('{"reply":"繁體中文","ok":true}'.encode("utf-8")).decode("ascii").rstrip("=")
        wrapped = f"\n{encoded[:8]} \n{encoded[8:]}\n"
        self.assertEqual(decode_codex_json_payload(wrapped), {"reply": "繁體中文", "ok": True})

    def test_codex_payload_decoder_accepts_direct_json_fallback(self) -> None:
        self.assertEqual(decode_codex_json_payload('{"ok":true}'), {"ok": True})

    def test_extract_codex_session_id_from_jsonl(self) -> None:
        output = '\n'.join([
            '{"type":"thread.started","thread_id":"019-test-thread"}',
            '{"type":"turn.completed"}',
        ])
        self.assertEqual(extract_codex_session_id(output), "019-test-thread")


if __name__ == "__main__":
    unittest.main()
