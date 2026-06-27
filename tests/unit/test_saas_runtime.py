import io
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.domain.models import FounderBrief, PanelSpec
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.saas import job_store
from ai_validation_swarm.saas.api import SaasApiApplication
from ai_validation_swarm.saas.models import TenantWorkspace, WorkspaceMember
from ai_validation_swarm.saas.runtime import AuthorizationError, SaasRuntime, ValidationJobRequest
from ai_validation_swarm.storage.files import save_persona, write_json


class SaasRuntimeTest(unittest.TestCase):
    def _workspace_inputs(self, workspace_root: Path) -> tuple[Path, Path]:
        brief_path = workspace_root / "briefs" / "brief.json"
        write_json(
            brief_path,
            FounderBrief(
                brief_id="brief_001",
                project_name="Evidence Workspace",
                problem_statement="Founders lose evidence context across follow-up work.",
                target_market="HK SMB operators",
                offered_solution="A workspace that keeps recommendation evidence inspectable.",
                validation_goal="Check whether the concept solves a painful follow-up problem.",
            ).to_dict(),
        )
        persona_dir = workspace_root / "personas"
        save_persona(generate_personas(count=1, random_seed=41)[0], persona_dir)
        return brief_path, persona_dir

    def test_runtime_submit_process_and_purge_job_with_retention(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_001",
                slug="acme",
                display_name="Acme",
                owner_user_id="user_owner",
                api_token="token-owner",
                plan_tier="trial",
                billing_status="trialing",
                settings={"artifact_retention_days": 0, "daily_runs": 5, "max_concurrent_jobs": 2},
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)

            auth = runtime.authenticate("token-owner")
            job = runtime.submit_validation_job(
                auth,
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    provider_name="mock",
                    max_retries=1,
                ),
            )

            completed = runtime.process_next_job()

            self.assertEqual(completed["job_id"], job["job_id"])
            self.assertEqual(completed["status"], "completed")
            run_dir = Path(str(completed["output_run_path"]))
            self.assertTrue((run_dir / "run_contract.json").exists())
            self.assertTrue((run_dir / "report.json").exists())
            self.assertIn("artifact_retention_until", completed["metadata"])

            purged = runtime.purge_expired_run_artifacts(now=datetime.now(UTC) + timedelta(seconds=1))

            self.assertEqual(purged, [job["job_id"]])
            self.assertFalse(run_dir.exists())
            reloaded = runtime.get_validation_job(auth, job["job_id"])
            self.assertTrue(reloaded["metadata"]["artifact_deleted_at"])

    def test_runtime_enforces_role_billing_quota_and_workspace_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)

            blocked = runtime.bootstrap_workspace(
                workspace_id="ws_blocked",
                slug="blocked",
                display_name="Blocked",
                owner_user_id="owner_blocked",
                api_token="token-blocked",
                plan_tier="trial",
                billing_status="past_due",
            )
            blocked_root = Path(blocked["workspace_root"])
            blocked_brief, blocked_personas = self._workspace_inputs(blocked_root)
            blocked_auth = runtime.authenticate("token-blocked")
            with self.assertRaises(AuthorizationError):
                runtime.submit_validation_job(
                    blocked_auth,
                    ValidationJobRequest(
                        brief_path=str(blocked_brief.relative_to(blocked_root)),
                        persona_dir=str(blocked_personas.relative_to(blocked_root)),
                        panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    ),
                )

            active = runtime.bootstrap_workspace(
                workspace_id="ws_active",
                slug="active",
                display_name="Active",
                owner_user_id="owner_active",
                api_token="token-active",
                plan_tier="trial",
                billing_status="active",
                settings={"daily_runs": 5, "max_concurrent_jobs": 1},
            )
            active_root = Path(active["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(active_root)

            workspace = job_store.get_workspace(runtime_root, "ws_active")
            workspace.members.append(WorkspaceMember(user_id="user_viewer", role="viewer", joined_at=workspace.created_at))
            job_store.upsert_workspace(runtime_root, workspace)
            job_store.register_api_token(
                runtime_root,
                token="token-active",
                workspace_id="ws_active",
                user_id="owner_active",
                role="owner",
                issued_at=workspace.created_at,
            )
            job_store.register_api_token(
                runtime_root,
                token="token-viewer",
                workspace_id="ws_active",
                user_id="user_viewer",
                role="viewer",
                issued_at=workspace.created_at,
            )

            viewer_auth = runtime.authenticate("token-viewer")
            with self.assertRaises(AuthorizationError):
                runtime.submit_validation_job(
                    viewer_auth,
                    ValidationJobRequest(
                        brief_path=str(brief_path.relative_to(active_root)),
                        persona_dir=str(persona_dir.relative_to(active_root)),
                        panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    ),
                )

            owner_auth = runtime.authenticate("token-active")
            first_job = runtime.submit_validation_job(
                owner_auth,
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(active_root)),
                    persona_dir=str(persona_dir.relative_to(active_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                ),
            )
            self.assertEqual(first_job["status"], "queued")

            with self.assertRaises(AuthorizationError):
                runtime.submit_validation_job(
                    owner_auth,
                    ValidationJobRequest(
                        brief_path=str(brief_path.relative_to(active_root)),
                        persona_dir=str(persona_dir.relative_to(active_root)),
                        panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    ),
                )

            with self.assertRaises(AuthorizationError):
                runtime.submit_validation_job(
                    owner_auth,
                    ValidationJobRequest(
                        brief_path="../outside/brief.json",
                        persona_dir=str(persona_dir.relative_to(active_root)),
                        panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    ),
                )

    def test_api_submit_and_list_jobs_require_bearer_token(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_api",
                slug="api",
                display_name="API",
                owner_user_id="owner_api",
                api_token="token-api",
                plan_tier="pro",
                billing_status="active",
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)
            app = SaasApiApplication(runtime)

            def call_app(method: str, path: str, *, token: str = "", payload: dict | None = None):
                body = json.dumps(payload or {}).encode("utf-8")
                captured: dict[str, object] = {}

                def start_response(status: str, headers):
                    captured["status"] = status
                    captured["headers"] = headers

                environ = {
                    "REQUEST_METHOD": method,
                    "PATH_INFO": path,
                    "CONTENT_LENGTH": str(len(body)),
                    "CONTENT_TYPE": "application/json",
                    "wsgi.input": io.BytesIO(body),
                    "HTTP_AUTHORIZATION": f"Bearer {token}" if token else "",
                }
                response_body = b"".join(app(environ, start_response))
                return str(captured["status"]), json.loads(response_body.decode("utf-8"))

            status, payload = call_app("GET", "/api/v1/validation-jobs")
            self.assertEqual(status, "401 Unauthorized")
            self.assertEqual(payload["error"], "unauthorized")

            status, payload = call_app(
                "POST",
                "/api/v1/validation-jobs",
                token="token-api",
                payload={
                    "brief_path": str(brief_path.relative_to(workspace_root)),
                    "persona_dir": str(persona_dir.relative_to(workspace_root)),
                    "panel_spec": {"panel_type": "mainstream", "sample_size": 1, "random_seed": 11},
                    "provider_name": "mock",
                },
            )
            self.assertEqual(status, "202 Accepted")
            job_id = payload["job"]["job_id"]

            runtime.process_next_job()

            status, payload = call_app("GET", f"/api/v1/validation-jobs/{job_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["job"]["status"], "completed")

            status, payload = call_app("GET", "/api/v1/validation-jobs", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(len(payload["jobs"]), 1)


if __name__ == "__main__":
    unittest.main()
