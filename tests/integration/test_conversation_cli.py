import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.cli.main import main
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.storage.files import read_json, save_persona


class ConversationCliTest(unittest.TestCase):
    def test_noninteractive_mock_chat_creates_closed_session(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            persona = generate_personas(count=1, random_seed=29)[0]
            save_persona(persona, root / "personas")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main([
                    "chat-with-persona", "--persona-id", persona.profile.synthetic_user_id,
                    "--data-dir", str(root / "personas"), "--session-dir", str(root / "conversations"),
                    "--backend", "mock", "--message", "Would you pay for this subscription?",
                ])
            self.assertEqual(exit_code, 0)
            self.assertIn("Synthetic user for AI pre-validation only", output.getvalue())
            sessions = list((root / "conversations").iterdir())
            self.assertEqual(len(sessions), 1)
            payload = read_json(sessions[0] / "session.json")
            self.assertEqual(payload["status"], "closed")
            self.assertEqual(payload["turn_count"], 2)


if __name__ == "__main__":
    unittest.main()
