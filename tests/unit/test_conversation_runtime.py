import tempfile
import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.conversation.providers import ChatResult, MockConversationProvider
from ai_validation_swarm.conversation.providers import OpenAIConversationProvider
from ai_validation_swarm.providers.openai_client import OpenAIProviderConfig
from ai_validation_swarm.conversation.runtime import ConversationRuntime, resolve_persona_folder
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.storage.files import read_json, save_persona


class FailingConversationProvider:
    provider_name = "failure-fixture"
    model_name = "failure-fixture/v1"

    def respond(self, **kwargs):
        raise RuntimeError("provider unavailable")


class RecordingConversationProvider:
    provider_name = "recording-fixture"
    model_name = "recording-fixture/v1"

    def __init__(self):
        self.calls = []

    def respond(self, **kwargs):
        self.calls.append(kwargs)
        return ChatResult(
            "I understand it, but that is not payment intent.",
            "understands",
            "high",
            "thread-fixture-1",
        )


class ConversationRuntimeTest(unittest.TestCase):
    def _persona_library(self, root: Path) -> str:
        persona = generate_personas(count=1, random_seed=17)[0]
        save_persona(persona, root / "personas")
        return persona.profile.synthetic_user_id

    def test_chat_persists_turns_transcript_and_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona_id = self._persona_library(root)
            provider = RecordingConversationProvider()
            runtime = ConversationRuntime(data_dir=root / "personas", session_dir=root / "conversations", provider=provider)
            session, persona, folder = runtime.start(persona_id)
            reply = runtime.send(session, persona, folder, "Would you pay HKD 80 each month?")
            self.assertIn("not payment intent", reply)
            payload = read_json(root / "conversations" / session.session_id / "session.json")
            self.assertEqual(payload["turn_count"], 2)
            self.assertEqual(payload["prompt_version"], "persona-conversation/v1")
            self.assertEqual(payload["turns"][1]["intent_level"], "understands")
            self.assertEqual(payload["provider_session_id"], "thread-fixture-1")
            transcript = (root / "conversations" / session.session_id / "transcript.md").read_text(encoding="utf-8")
            self.assertIn("not human market evidence", transcript)
            self.assertIn("Would you pay", transcript)
            self.assertIn("PERSONA RUNTIME ARTIFACT", provider.calls[0]["system_prompt"])

            runtime.send(session, persona, folder, "What would change your mind?")
            self.assertEqual(provider.calls[1]["provider_session_id"], "thread-fixture-1")
            self.assertNotIn("USER:", provider.calls[1]["user_prompt"])

    def test_provider_failure_does_not_pollute_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona_id = self._persona_library(root)
            runtime = ConversationRuntime(data_dir=root / "personas", session_dir=root / "conversations", provider=FailingConversationProvider())
            session, persona, folder = runtime.start(persona_id)
            with self.assertRaisesRegex(RuntimeError, "provider unavailable"):
                runtime.send(session, persona, folder, "Tell me what you dislike.")
            self.assertEqual(session.turns, [])

    def test_resume_and_reset_preserve_session_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona_id = self._persona_library(root)
            runtime = ConversationRuntime(data_dir=root / "personas", session_dir=root / "conversations", provider=MockConversationProvider())
            session, persona, folder = runtime.start(persona_id)
            runtime.send(session, persona, folder, "Would you try this workflow product?")
            resumed, _, _ = runtime.resume(session.session_id)
            self.assertEqual(resumed.session_id, session.session_id)
            self.assertEqual(len(resumed.turns), 2)
            runtime.reset(resumed)
            self.assertEqual(read_json(root / "conversations" / session.session_id / "session.json")["turns"], [])

    def test_version_resolution_prefers_v3_3(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp) / "personas" / "su_0001"
            (base / "v3").mkdir(parents=True)
            (base / "v3_3").mkdir()
            (base / "v3_2").mkdir()
            (base / "v3" / "profile.json").write_text("{}", encoding="utf-8")
            (base / "v3_3" / "profile.json").write_text("{}", encoding="utf-8")
            (base / "v3_2" / "profile.json").write_text("{}", encoding="utf-8")
            self.assertEqual(resolve_persona_folder(base.parent, "su_0001"), base / "v3_3")

    def test_live_provider_removes_object_replacement_format_character(self):
        class StubClient:
            config = OpenAIProviderConfig(api_key="fixture", model="fixture-model")

            def create_json_response(self, **kwargs):
                return {"reply": "可以\ufffc試用", "intent_level": "curious", "confidence": "high"}

        result = OpenAIConversationProvider(StubClient()).respond(
            system_prompt="rules", user_prompt="question", persona=generate_personas(count=1)[0]
        )
        self.assertEqual(result.reply, "可以試用")


if __name__ == "__main__":
    unittest.main()
