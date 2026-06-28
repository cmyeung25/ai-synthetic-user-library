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
            blocked_support = runtime.describe_workspace_support(blocked_auth)
            self.assertEqual(blocked_support["submission_gate"]["status"], "blocked")
            self.assertEqual(blocked_support["submission_gate"]["blocked_reasons"][0]["code"], "billing_inactive")

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
            active_support = runtime.describe_workspace_support(owner_auth)
            self.assertEqual(active_support["submission_gate"]["status"], "blocked")
            self.assertEqual(active_support["submission_gate"]["blocked_reasons"][0]["code"], "concurrency_limit_reached")

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

    def test_runtime_support_diagnostics_cover_queued_and_running_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_support",
                slug="support",
                display_name="Support",
                owner_user_id="owner_support",
                api_token="token-support",
                plan_tier="pro",
                billing_status="active",
                settings={"daily_runs": 5, "max_concurrent_jobs": 2},
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)
            auth = runtime.authenticate("token-support")

            queued_job = runtime.submit_validation_job(
                auth,
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    provider_name="mock",
                ),
            )

            queued_support = runtime.describe_workspace_support(auth, job_id=queued_job["job_id"])
            self.assertEqual(queued_support["job_diagnostic"]["status"], "queued")
            self.assertEqual(queued_support["job_diagnostic"]["failure_category"], "awaiting_worker")
            self.assertTrue(queued_support["job_diagnostic"]["can_cancel"])
            self.assertFalse(queued_support["job_diagnostic"]["can_retry"])
            self.assertTrue(queued_support["job_diagnostic"]["created_at"])
            self.assertIsNone(queued_support["job_diagnostic"]["started_at"])

            leased = job_store.lease_next_validation_job(runtime_root)
            self.assertIsNotNone(leased)

            running_support = runtime.describe_workspace_support(auth, job_id=queued_job["job_id"])
            self.assertEqual(running_support["job_diagnostic"]["status"], "running")
            self.assertEqual(running_support["job_diagnostic"]["failure_category"], "in_progress")
            self.assertFalse(running_support["job_diagnostic"]["can_cancel"])
            self.assertFalse(running_support["job_diagnostic"]["can_retry"])
            self.assertTrue(running_support["job_diagnostic"]["started_at"])
            self.assertIn("Wait for worker completion", running_support["job_diagnostic"]["next_actions"][0])

    def test_api_validation_job_cancel_and_retry_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_ops",
                slug="ops",
                display_name="Ops",
                owner_user_id="owner_ops",
                api_token="token-ops",
                plan_tier="pro",
                billing_status="active",
                settings={"daily_runs": 10, "max_concurrent_jobs": 2},
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)
            app = SaasApiApplication(runtime)

            def call_app(
                method: str,
                path: str,
                *,
                token: str = "",
                cookie: str = "",
                payload: dict | None = None,
                query: str = "",
            ):
                body = json.dumps(payload or {}).encode("utf-8")
                captured: dict[str, object] = {}

                def start_response(status: str, headers):
                    captured["status"] = status
                    captured["headers"] = headers

                environ = {
                    "REQUEST_METHOD": method,
                    "PATH_INFO": path,
                    "QUERY_STRING": query,
                    "CONTENT_LENGTH": str(len(body)),
                    "CONTENT_TYPE": "application/json",
                    "wsgi.input": io.BytesIO(body),
                    "HTTP_AUTHORIZATION": f"Bearer {token}" if token else "",
                }
                response_body = b"".join(app(environ, start_response))
                return str(captured["status"]), json.loads(response_body.decode("utf-8"))

            status, payload = call_app(
                "POST",
                "/api/v1/validation-jobs",
                token="token-ops",
                payload={
                    "brief_path": str(brief_path.relative_to(workspace_root)),
                    "persona_dir": str(persona_dir.relative_to(workspace_root)),
                    "panel_spec": {"panel_type": "mainstream", "sample_size": 1, "random_seed": 11},
                    "provider_name": "mock",
                },
            )
            self.assertEqual(status, "202 Accepted")
            queued_job_id = payload["job"]["job_id"]
            self.assertEqual(payload["job"]["status"], "queued")

            status, payload = call_app(
                "POST",
                f"/api/v1/validation-jobs/{queued_job_id}/cancel",
                token="token-ops",
                payload={"reason": "Canceled from API test"},
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["job"]["job_id"], queued_job_id)
            self.assertEqual(payload["job"]["status"], "canceled")
            self.assertEqual(payload["job"]["last_error"], "Canceled from API test")

            status, payload = call_app(
                "POST",
                "/api/v1/validation-jobs",
                token="token-ops",
                payload={
                    "brief_path": str(brief_path.relative_to(workspace_root)),
                    "persona_dir": str(persona_dir.relative_to(workspace_root)),
                    "panel_spec": {"panel_type": "mainstream", "sample_size": 1, "random_seed": 11},
                    "provider_name": "unknown-provider",
                },
            )
            self.assertEqual(status, "202 Accepted")
            failed_job_id = payload["job"]["job_id"]

            failed = runtime.process_next_job()
            self.assertEqual(failed["job_id"], failed_job_id)
            self.assertEqual(failed["status"], "failed")

            status, payload = call_app(
                "POST",
                f"/api/v1/validation-jobs/{failed_job_id}/retry",
                token="token-ops",
            )
            self.assertEqual(status, "202 Accepted")
            self.assertEqual(payload["source_job_id"], failed_job_id)
            self.assertEqual(payload["job"]["status"], "queued")
            self.assertEqual(payload["job"]["metadata"]["retry_of_job_id"], failed_job_id)

            status, payload = call_app("GET", "/api/v1/validation-jobs", token="token-ops")
            self.assertEqual(status, "200 OK")
            self.assertEqual(len(payload["jobs"]), 3)
            self.assertTrue(any(job["job_id"] == queued_job_id and job["status"] == "canceled" for job in payload["jobs"]))
            self.assertTrue(any(job["job_id"] == failed_job_id and job["status"] == "failed" for job in payload["jobs"]))
            self.assertTrue(any(job["metadata"].get("retry_of_job_id") == failed_job_id and job["status"] == "queued" for job in payload["jobs"]))
            self.assertIn("canceled", {job["status"] for job in payload["jobs"]})
            self.assertIn("failed", {job["status"] for job in payload["jobs"]})
            self.assertIn("queued", {job["status"] for job in payload["jobs"]})

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

            def call_app(
                method: str,
                path: str,
                *,
                token: str = "",
                cookie: str = "",
                payload: dict | None = None,
                query: str = "",
            ):
                body = json.dumps(payload or {}).encode("utf-8")
                captured: dict[str, object] = {}

                def start_response(status: str, headers):
                    captured["status"] = status
                    captured["headers"] = headers

                environ = {
                    "REQUEST_METHOD": method,
                    "PATH_INFO": path,
                    "QUERY_STRING": query,
                    "CONTENT_LENGTH": str(len(body)),
                    "CONTENT_TYPE": "application/json",
                    "wsgi.input": io.BytesIO(body),
                    "HTTP_AUTHORIZATION": f"Bearer {token}" if token else "",
                    "HTTP_COOKIE": cookie,
                }
                response_body = b"".join(app(environ, start_response))
                return str(captured["status"]), json.loads(response_body.decode("utf-8"))

            def call_app_raw(
                method: str,
                path: str,
                *,
                token: str = "",
                cookie: str = "",
                payload: dict | None = None,
                query: str = "",
            ):
                body = json.dumps(payload or {}).encode("utf-8")
                captured: dict[str, object] = {}

                def start_response(status: str, headers):
                    captured["status"] = status
                    captured["headers"] = headers

                environ = {
                    "REQUEST_METHOD": method,
                    "PATH_INFO": path,
                    "QUERY_STRING": query,
                    "CONTENT_LENGTH": str(len(body)),
                    "CONTENT_TYPE": "application/json",
                    "wsgi.input": io.BytesIO(body),
                    "HTTP_AUTHORIZATION": f"Bearer {token}" if token else "",
                    "HTTP_COOKIE": cookie,
                }
                response_body = b"".join(app(environ, start_response))
                return str(captured["status"]), list(captured["headers"]), response_body

            status, payload = call_app("GET", "/api/v1/validation-jobs")
            self.assertEqual(status, "401 Unauthorized")
            self.assertEqual(payload["error"], "unauthorized")

            status, payload = call_app("GET", "/api/v1/session")
            self.assertEqual(status, "401 Unauthorized")
            self.assertEqual(payload["error"], "unauthorized")

            status, payload = call_app("GET", "/api/v1/workspace-shell")
            self.assertEqual(status, "401 Unauthorized")
            self.assertEqual(payload["error"], "unauthorized")

            status, headers, body = call_app_raw("OPTIONS", "/api/v1/validation-jobs")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")
            header_map = {name: value for name, value in headers}
            self.assertEqual(header_map["Access-Control-Allow-Origin"], "*")
            self.assertIn("Authorization", header_map["Access-Control-Allow-Headers"])
            self.assertIn("OPTIONS", header_map["Access-Control-Allow-Methods"])

            status, headers, body = call_app_raw("OPTIONS", "/api/v1/session")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw("OPTIONS", "/api/v1/workspace-shell")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw("OPTIONS", "/api/v1/projects")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw("OPTIONS", "/api/v1/studies")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw("OPTIONS", "/api/v1/export-bundles")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw("OPTIONS", "/api/v1/share-bundles")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw("OPTIONS", "/public/v1/share-bundles/demo")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw("OPTIONS", "/api/v1/support-diagnostics")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw("OPTIONS", "/api/v1/support-snapshots")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw("OPTIONS", "/api/v1/evidence-views")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw("OPTIONS", "/api/v1/decision-logs")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw("OPTIONS", "/api/v1/workspace-settings")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw("OPTIONS", "/api/v1/workspace-billing")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw("OPTIONS", "/api/v1/workspace-members")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw("OPTIONS", "/api/v1/api-tokens")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw("GET", "/app/workspace")
            self.assertEqual(status, "401 Unauthorized")
            self.assertIn(b"unauthorized", body)

            status, headers, body = call_app_raw("GET", "/app/workspace", query="token=token-api")
            self.assertEqual(status, "302 Found")
            header_map = {name: value for name, value in headers}
            self.assertEqual(header_map["Location"], "/app/workspace")
            self.assertIn("ai_validation_swarm_session=", header_map["Set-Cookie"])
            self.assertEqual(body, b"")
            browser_cookie = header_map["Set-Cookie"].split(";", 1)[0]

            status, headers, body = call_app_raw("GET", "/app/workspace", cookie=browser_cookie)
            self.assertEqual(status, "200 OK")
            header_map = {name: value for name, value in headers}
            self.assertIn("text/html", header_map["Content-Type"])
            self.assertIn(b"window.__WORKSPACE_ROUTE_CONTEXT__", body)
            self.assertIn(b'"route_kind": "workspace"', body)
            self.assertIn(b"Moss Workspace Framework Host", body)
            self.assertIn(b"/app-static/frontend/workspace_shell_app/dist/assets/workspace-shell-app.js", body)

            status, headers, body = call_app_raw("GET", "/app/new-study", cookie=browser_cookie)
            self.assertEqual(status, "200 OK")
            header_map = {name: value for name, value in headers}
            self.assertIn("text/html", header_map["Content-Type"])
            self.assertIn(b'"route_kind": "new_study"', body)
            self.assertIn(b'"route_path": "/app/new-study"', body)

            status, headers, body = call_app_raw("GET", "/app-static/demo/workspace_ui_moss_stage15/index.html")
            self.assertEqual(status, "200 OK")
            header_map = {name: value for name, value in headers}
            self.assertIn("text/html", header_map["Content-Type"])
            self.assertIn(b"Workspace UI Moss Stage 15", body)

            status, headers, body = call_app_raw("GET", "/app/studies/study_001", cookie=browser_cookie)
            self.assertEqual(status, "200 OK")
            header_map = {name: value for name, value in headers}
            self.assertIn("text/html", header_map["Content-Type"])
            self.assertIn(b'"study_id": "study_001"', body)
            self.assertIn(b"/app-static/frontend/workspace_shell_app/dist/assets/workspace-shell-app.js", body)

            status, headers, body = call_app_raw("GET", "/app/evidence-views/evidence_view_001", cookie=browser_cookie)
            self.assertEqual(status, "200 OK")
            self.assertIn(b'"evidence_view_id": "evidence_view_001"', body)

            status, headers, body = call_app_raw("GET", "/app/decision-logs/decision_log_001", cookie=browser_cookie)
            self.assertEqual(status, "200 OK")
            self.assertIn(b'"decision_log_id": "decision_log_001"', body)

            status, headers, body = call_app_raw("GET", "/app/export-bundles/export_001", cookie=browser_cookie)
            self.assertEqual(status, "200 OK")
            self.assertIn(b'"export_bundle_id": "export_001"', body)

            status, headers, body = call_app_raw("GET", "/app/support-snapshots/support_001", cookie=browser_cookie)
            self.assertEqual(status, "200 OK")
            self.assertIn(b'"support_snapshot_id": "support_001"', body)

            status, headers, body = call_app_raw("GET", "/app-static/demo/workspace_ui_shared/workspace_shell_app.mjs")
            self.assertEqual(status, "200 OK")
            header_map = {name: value for name, value in headers}
            self.assertIn("javascript", header_map["Content-Type"])
            self.assertIn(b"createWorkspaceShellAppController", body)

            status, headers, body = call_app_raw(
                "GET",
                "/app-static/frontend/workspace_shell_app/dist/assets/workspace-shell-app.js",
            )
            self.assertEqual(status, "200 OK")
            header_map = {name: value for name, value in headers}
            self.assertIn("javascript", header_map["Content-Type"])
            self.assertIn(b"same-origin hosted route shell", body)

            status, headers, body = call_app_raw("GET", "/app-static/demo/workspace_ui_moss_stage15/workspace_shell_stage15_app.mjs")
            self.assertEqual(status, "200 OK")
            header_map = {name: value for name, value in headers}
            self.assertIn("javascript", header_map["Content-Type"])
            self.assertIn(b"mountStage15WorkspaceShell", body)

            status, payload = call_app("GET", "/app-static/../README.md")
            self.assertEqual(status, "404 Not Found")
            self.assertEqual(payload["error"], "not_found")

            status, payload = call_app(
                "POST",
                "/api/v1/projects",
                token="token-api",
                payload={
                    "name": "Inbox Coach Launch",
                    "description": "Operator-facing evidence workspace launch research.",
                    "slug": "inbox-coach-launch",
                },
            )
            self.assertEqual(status, "201 Created")
            project_id = payload["project"]["project_id"]
            self.assertEqual(payload["project"]["slug"], "inbox-coach-launch")
            self.assertEqual(payload["project"]["study_count"], 0)

            status, payload = call_app(
                "POST",
                "/api/v1/studies",
                token="token-api",
                payload={
                    "project_id": project_id,
                    "title": "Onboarding hesitation study",
                    "research_intent": "Find where new operators hesitate during onboarding.",
                    "desired_output": "task-friction and continuation risk",
                    "first_task": "complete the first onboarding task",
                    "artifact_refs": ["sample-onboarding-01.png", "sample-onboarding-02.png"],
                },
            )
            self.assertEqual(status, "201 Created")
            study_id = payload["study"]["study_id"]
            self.assertEqual(payload["study"]["project_id"], project_id)
            self.assertEqual(payload["study"]["run_count"], 0)

            status, payload = call_app(
                "POST",
                "/api/v1/validation-jobs",
                token="token-api",
                payload={
                    "brief_path": str(brief_path.relative_to(workspace_root)),
                    "persona_dir": str(persona_dir.relative_to(workspace_root)),
                    "panel_spec": {"panel_type": "mainstream", "sample_size": 1, "random_seed": 11},
                    "provider_name": "mock",
                    "metadata": {"project_id": project_id, "study_id": study_id},
                },
            )
            self.assertEqual(status, "202 Accepted")
            job_id = payload["job"]["job_id"]
            self.assertEqual(payload["job"]["metadata"]["project_id"], project_id)
            self.assertEqual(payload["job"]["metadata"]["study_id"], study_id)

            runtime.process_next_job()

            status, payload = call_app("GET", f"/api/v1/validation-jobs/{job_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["job"]["status"], "completed")
            run_id = payload["job"]["metadata"]["run_id"]

            status, payload = call_app("GET", "/api/v1/validation-jobs", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(len(payload["jobs"]), 1)

            status, payload = call_app("GET", "/api/v1/session", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["session"]["auth"]["workspace_id"], "ws_api")
            self.assertEqual(payload["session"]["auth"]["role"], "owner")
            self.assertEqual(payload["session"]["workspace"]["plan_tier"], "pro")
            self.assertEqual(payload["session"]["billing_account"]["status"], "active")
            self.assertEqual(payload["session"]["plan_limits"]["daily_runs"], 25)
            self.assertEqual(payload["session"]["job_counts"]["total"], 1)
            self.assertEqual(payload["session"]["product_counts"]["projects"], 1)
            self.assertEqual(payload["session"]["product_counts"]["studies"], 1)
            self.assertEqual(payload["session"]["product_counts"]["export_bundles"], 0)
            self.assertEqual(payload["session"]["product_counts"]["share_bundles"], 0)
            self.assertTrue(payload["session"]["capabilities"]["project_studies"])
            self.assertTrue(payload["session"]["capabilities"]["export_bundles"])
            self.assertTrue(payload["session"]["capabilities"]["share_bundles"])
            self.assertTrue(payload["session"]["capabilities"]["session_auth"])
            self.assertIn("synthetic", payload["session"]["synthetic_boundary"].lower())

            status, payload = call_app("GET", "/api/v1/session", cookie=browser_cookie)
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["session"]["auth"]["workspace_id"], "ws_api")
            self.assertEqual(payload["session"]["auth"]["auth_type"], "browser_session")

            status, payload = call_app("GET", "/api/v1/projects", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(len(payload["projects"]), 1)
            self.assertEqual(payload["projects"][0]["project_id"], project_id)
            self.assertEqual(payload["projects"][0]["study_count"], 1)

            status, payload = call_app("GET", f"/api/v1/projects/{project_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["project"]["project_id"], project_id)
            self.assertEqual(payload["project"]["study_count"], 1)

            status, payload = call_app("GET", "/api/v1/studies", token="token-api", query=f"project_id={project_id}")
            self.assertEqual(status, "200 OK")
            self.assertEqual(len(payload["studies"]), 1)
            self.assertEqual(payload["studies"][0]["study_id"], study_id)
            self.assertEqual(payload["studies"][0]["latest_job_status"], "completed")
            self.assertEqual(payload["studies"][0]["run_count"], 1)

            status, payload = call_app("GET", f"/api/v1/studies/{study_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["study"]["study_id"], study_id)
            self.assertEqual(payload["study"]["latest_job_id"], job_id)

            status, payload = call_app(
                "GET",
                "/api/v1/workspace-shell",
                token="token-api",
                query=f"project_id={project_id}&study_id={study_id}&query_text=hesitate&active_family=all&sort_by=relevance",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["snapshot"]["snapshot_version"], "workspace-shell/v0-draft")
            self.assertEqual(payload["snapshot"]["session"]["auth"]["workspace_id"], "ws_api")
            self.assertEqual(payload["snapshot"]["selected_project_id"], project_id)
            self.assertEqual(payload["snapshot"]["selected_project"]["project_id"], project_id)
            self.assertEqual(payload["snapshot"]["selected_study_id"], study_id)
            self.assertEqual(payload["snapshot"]["selected_study"]["study_id"], study_id)
            self.assertEqual(payload["snapshot"]["selected_job_id"], job_id)
            self.assertEqual(payload["snapshot"]["selected_job"]["job_id"], job_id)
            self.assertEqual(payload["snapshot"]["evidence_query"]["query_status"], "query_ready")
            self.assertTrue(payload["snapshot"]["capabilities"]["workspace_shell_snapshot"])
            self.assertEqual(payload["snapshot"]["runtime_sync"]["snapshot_endpoint"], "/api/v1/workspace-shell")

            status, payload = call_app(
                "GET",
                "/api/v1/workspace-shell",
                token="token-api",
                query="query_text=&active_family=trace&sort_by=relevance",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["snapshot"]["evidence_query"]["active_family"], "trace")
            self.assertGreaterEqual(payload["snapshot"]["evidence_query"]["result_count"], 1)
            self.assertEqual(payload["snapshot"]["evidence_query"]["selected_result"]["family"], "trace")
            self.assertGreaterEqual(len(payload["snapshot"]["evidence_query"]["replay_sequence"]), 1)
            self.assertIsNotNone(payload["snapshot"]["evidence_query"]["selected_replay_step_id"])
            self.assertTrue(payload["snapshot"]["evidence_query"]["replay_context"]["selected_result_has_replay"])
            self.assertGreaterEqual(payload["snapshot"]["evidence_query"]["replay_context"]["replay_result_count"], 1)
            self.assertGreaterEqual(
                len(payload["snapshot"]["evidence_query"]["comparison_context"]["comparison_candidates"]),
                1,
            )

            status, payload = call_app(
                "GET",
                "/api/v1/evidence-query",
                token="token-api",
                query=f"run_id={run_id}&query_text=report&active_family=output&sort_by=relevance",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["query"]["query_status"], "query_ready")
            self.assertGreaterEqual(payload["query"]["result_count"], 1)
            self.assertEqual(payload["query"]["active_family"], "output")
            self.assertEqual(payload["query"]["results"][0]["family"], "output")
            self.assertIn("synthetic", payload["query"]["boundary_warning"].lower())

            output_result_id = next(
                result["id"]
                for result in payload["query"]["results"]
                if result["family"] == "output"
            )
            status, payload = call_app(
                "GET",
                "/api/v1/evidence-query",
                token="token-api",
                query=(
                    f"run_id={run_id}&query_text=&active_family=all&sort_by=relevance"
                    f"&selected_result_id={output_result_id}"
                ),
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["query"]["selected_result_id"], output_result_id)
            self.assertFalse(payload["query"]["replay_context"]["selected_result_has_replay"])
            self.assertGreaterEqual(payload["query"]["replay_context"]["replay_result_count"], 1)
            self.assertGreaterEqual(
                len(payload["query"]["comparison_context"]["comparison_candidates"]),
                1,
            )
            self.assertIn(
                "replay",
                payload["query"]["comparison_context"]["comparison_candidates"][0]["relation_note"],
            )

            status, payload = call_app(
                "GET",
                "/api/v1/evidence-query",
                token="token-api",
                query=f"run_id={run_id}&query_text=&active_family=trace&sort_by=relevance",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["query"]["active_family"], "trace")
            self.assertGreaterEqual(payload["query"]["result_count"], 1)
            self.assertEqual(payload["query"]["selected_result"]["family"], "trace")
            self.assertGreaterEqual(len(payload["query"]["replay_sequence"]), 1)
            self.assertIsNotNone(payload["query"]["selected_replay_step_id"])
            self.assertTrue(payload["query"]["replay_context"]["selected_result_has_replay"])
            self.assertGreaterEqual(
                payload["query"]["comparison_context"]["selected_family_result_count"],
                1,
            )
            self.assertTrue(
                payload["query"]["replay_sequence"][0]["note"].startswith("Role:")
            )
            self.assertEqual(payload["query"]["cross_run_comparison"]["comparison_run_count"], 0)

            comparison_job = runtime.submit_validation_job(
                runtime.authenticate("token-api"),
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=23),
                    provider_name="mock",
                    metadata={"project_id": project_id, "study_id": study_id},
                ),
            )
            runtime.process_next_job()
            comparison_job_status = runtime.get_validation_job(runtime.authenticate("token-api"), comparison_job["job_id"])
            comparison_run_id = comparison_job_status["metadata"]["run_id"]
            self.assertNotEqual(comparison_run_id, run_id)

            status, payload = call_app(
                "GET",
                "/api/v1/evidence-query",
                token="token-api",
                query=(
                    f"run_id={run_id}&query_text=&active_family=trace&sort_by=relevance"
                    f"&selected_comparison_run_id={comparison_run_id}"
                ),
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["query"]["cross_run_comparison"]["comparison_run_count"], 1)
            self.assertEqual(
                payload["query"]["cross_run_comparison"]["selected_comparison_run_id"],
                comparison_run_id,
            )
            self.assertEqual(
                payload["query"]["cross_run_comparison"]["selected_comparison_job_id"],
                comparison_job["job_id"],
            )
            self.assertEqual(
                payload["query"]["cross_run_comparison"]["candidate_runs"][0]["job_id"],
                comparison_job["job_id"],
            )
            self.assertEqual(
                payload["query"]["cross_run_comparison"]["selected_comparison_run"]["run_id"],
                comparison_run_id,
            )
            self.assertGreaterEqual(
                len(payload["query"]["cross_run_comparison"]["selected_comparison_run"]["comparison_results"]),
                1,
            )
            self.assertIn(
                "same",
                payload["query"]["cross_run_comparison"]["selected_comparison_run"]["relation_note"],
            )
            reliability = payload["query"]["evidence_reliability"]
            self.assertEqual(reliability["contract_version"], "workspace-evidence-reliability/v0-draft")
            self.assertEqual(reliability["review_status"], "reliability_ready")
            self.assertIn(
                reliability["stability_label"],
                {"repeated_signal", "comparison_available", "mixed_or_contradictory"},
            )
            self.assertGreaterEqual(reliability["stability_score"], 1)
            self.assertGreaterEqual(len(reliability["supporting_evidence"]), 1)
            self.assertTrue(any(item["id"] == "synthetic_boundary" for item in reliability["calibration_records"]))
            self.assertTrue(any(item["id"] == "human_validation_gap" for item in reliability["missing_context"]))
            self.assertEqual(payload["query"]["audit_lineage"]["source_run"]["run_id"], run_id)
            self.assertEqual(payload["query"]["audit_lineage"]["source_run"]["job_id"], job_id)
            self.assertEqual(payload["query"]["audit_lineage"]["source_run"]["project_id"], project_id)
            self.assertEqual(payload["query"]["audit_lineage"]["source_run"]["study_id"], study_id)
            self.assertEqual(
                payload["query"]["audit_lineage"]["comparison_set"]["selected_comparison_run_id"],
                comparison_run_id,
            )
            self.assertEqual(
                payload["query"]["audit_lineage"]["comparison_set"]["selected_comparison_job_id"],
                comparison_job["job_id"],
            )
            self.assertEqual(
                payload["query"]["audit_lineage"]["comparison_set"]["candidate_jobs"][0]["study_id"],
                study_id,
            )

            status, payload = call_app(
                "POST",
                "/api/v1/evidence-views",
                token="token-api",
                payload={
                    "study_id": study_id,
                    "job_id": job_id,
                    "title": "Trust blockers review",
                    "note": "Preserve the comparison-focused evidence slice.",
                    "query_text": "trust",
                    "active_family": "trace",
                    "sort_by": "relevance",
                    "selected_result_id": output_result_id,
                    "selected_comparison_run_id": comparison_run_id,
                },
            )
            self.assertEqual(status, "201 Created")
            evidence_view_id = payload["evidence_view"]["evidence_view_id"]
            self.assertEqual(payload["evidence_view"]["study_id"], study_id)
            self.assertEqual(payload["evidence_view"]["job_id"], job_id)
            self.assertEqual(payload["evidence_view"]["selected_result_id"], output_result_id)
            self.assertEqual(payload["evidence_view"]["selected_comparison_run_id"], comparison_run_id)
            self.assertTrue(payload["evidence_view"]["has_comparison_focus"])
            evidence_view_path = Path(payload["evidence_view"]["payload_path"])
            self.assertTrue(evidence_view_path.exists())
            self.assertTrue((evidence_view_path.parent / "README.md").exists())

            status, payload = call_app(
                "GET",
                "/api/v1/evidence-views",
                token="token-api",
                query=f"study_id={study_id}&job_id={job_id}",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(len(payload["evidence_views"]), 1)
            self.assertEqual(payload["evidence_views"][0]["evidence_view_id"], evidence_view_id)

            status, payload = call_app("GET", f"/api/v1/evidence-views/{evidence_view_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["evidence_view"]["evidence_view_id"], evidence_view_id)

            status, payload = call_app(
                "POST",
                "/api/v1/decision-logs",
                token="token-api",
                payload={
                    "study_id": study_id,
                    "job_id": job_id,
                    "evidence_view_id": evidence_view_id,
                    "title": "Do not ship yet",
                    "decision_summary": "Trust blockers still dominate the study evidence.",
                    "rationale": "The same hesitation appears across replay and cross-run comparison.",
                    "selected_result_id": output_result_id,
                    "selected_comparison_run_id": comparison_run_id,
                },
            )
            self.assertEqual(status, "201 Created")
            decision_log_id = payload["decision_log"]["decision_log_id"]
            self.assertEqual(payload["decision_log"]["study_id"], study_id)
            self.assertEqual(payload["decision_log"]["evidence_view_id"], evidence_view_id)
            self.assertTrue(payload["decision_log"]["has_linked_evidence_view"])
            self.assertTrue(payload["decision_log"]["has_comparison_focus"])
            decision_log_path = Path(payload["decision_log"]["payload_path"])
            self.assertTrue(decision_log_path.exists())
            self.assertTrue((decision_log_path.parent / "README.md").exists())

            status, payload = call_app(
                "GET",
                "/api/v1/decision-logs",
                token="token-api",
                query=f"study_id={study_id}&job_id={job_id}&evidence_view_id={evidence_view_id}",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(len(payload["decision_logs"]), 1)
            self.assertEqual(payload["decision_logs"][0]["decision_log_id"], decision_log_id)

            status, payload = call_app("GET", f"/api/v1/decision-logs/{decision_log_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["decision_log"]["decision_log_id"], decision_log_id)
            self.assertEqual(payload["decision_log"]["review_status"], "draft")
            self.assertEqual(payload["decision_log"]["comment_count"], 0)
            self.assertEqual(payload["decision_comments"], [])

            status, payload = call_app(
                "POST",
                f"/api/v1/decision-logs/{decision_log_id}/review-status",
                token="token-api",
                payload={
                    "review_status": "in_review",
                    "note": "Need one explicit cross-run check before approval.",
                },
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["decision_log"]["review_status"], "in_review")
            self.assertEqual(
                payload["decision_log"]["latest_review_note"],
                "Need one explicit cross-run check before approval.",
            )

            status, payload = call_app(
                "POST",
                f"/api/v1/decision-logs/{decision_log_id}/comments",
                token="token-api",
                payload={
                    "anchor_kind": "general",
                    "body": "Please justify why this is not one-run noise.",
                },
            )
            self.assertEqual(status, "201 Created")
            decision_comment_id = payload["decision_comment"]["decision_comment_id"]
            self.assertEqual(payload["decision_comment"]["decision_log_id"], decision_log_id)
            self.assertEqual(payload["decision_log"]["comment_count"], 1)

            status, payload = call_app(
                "POST",
                f"/api/v1/decision-logs/{decision_log_id}/comments",
                token="token-api",
                payload={
                    "parent_comment_id": decision_comment_id,
                    "anchor_kind": "comparison",
                    "body": "The comparison run shows the same objection cluster.",
                },
            )
            self.assertEqual(status, "201 Created")
            self.assertEqual(payload["decision_comment"]["parent_comment_id"], decision_comment_id)

            status, payload = call_app(
                "GET",
                f"/api/v1/decision-logs/{decision_log_id}/comments",
                token="token-api",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(len(payload["decision_comments"]), 2)
            parent_comment = next(
                comment
                for comment in payload["decision_comments"]
                if comment["decision_comment_id"] == decision_comment_id
            )
            reply_comment = next(
                comment
                for comment in payload["decision_comments"]
                if comment["decision_comment_id"] != decision_comment_id
            )
            self.assertEqual(parent_comment["reply_count"], 1)
            self.assertTrue(reply_comment["is_reply"])

            status, payload = call_app(
                "POST",
                f"/api/v1/decision-logs/{decision_log_id}/review-status",
                token="token-api",
                payload={
                    "review_status": "approved",
                    "note": "Cross-run evidence is consistent enough to proceed.",
                },
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["decision_log"]["review_status"], "approved")

            persisted_decision_log = json.loads(decision_log_path.read_text(encoding="utf-8"))
            self.assertEqual(persisted_decision_log["review_status"], "approved")
            self.assertEqual(persisted_decision_log["comment_count"], 2)
            self.assertEqual(len(persisted_decision_log["comments"]), 2)

            status, payload = call_app("GET", f"/api/v1/studies/{study_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["study"]["evidence_view_count"], 1)
            self.assertEqual(payload["study"]["decision_log_count"], 1)
            self.assertEqual(payload["study"]["decision_comment_count"], 2)
            self.assertEqual(payload["study"]["approved_decision_count"], 1)

            status, payload = call_app("GET", f"/api/v1/projects/{project_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["project"]["evidence_view_count"], 1)
            self.assertEqual(payload["project"]["decision_log_count"], 1)
            self.assertEqual(payload["project"]["decision_comment_count"], 2)
            self.assertEqual(payload["project"]["approved_decision_count"], 1)

            status, payload = call_app("GET", "/api/v1/session", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertTrue(payload["session"]["capabilities"]["study_collaboration"])
            self.assertTrue(payload["session"]["capabilities"]["decision_review"])
            self.assertTrue(payload["session"]["capabilities"]["study_activity"])
            self.assertEqual(payload["session"]["product_counts"]["evidence_views"], 1)
            self.assertEqual(payload["session"]["product_counts"]["decision_logs"], 1)
            self.assertEqual(payload["session"]["product_counts"]["decision_comments"], 2)

            pending_job = runtime.submit_validation_job(
                runtime.authenticate("token-api"),
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=17),
                    provider_name="mock",
                ),
            )
            status, payload = call_app(
                "GET",
                "/api/v1/evidence-query",
                token="token-api",
                query=f"job_id={pending_job['job_id']}",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["query"]["query_status"], "query_pending")
            self.assertEqual(payload["query"]["result_count"], 0)
            self.assertEqual(payload["query"]["comparison_context"]["comparison_candidates"], [])
            self.assertFalse(payload["query"]["replay_context"]["selected_result_has_replay"])

            status, payload = call_app(
                "POST",
                "/api/v1/export-bundles",
                token="token-api",
                payload={
                    "study_id": study_id,
                    "job_id": job_id,
                    "title": "Exec review export",
                    "export_format": "report_csv",
                },
            )
            self.assertEqual(status, "201 Created")
            export_bundle_id = payload["export_bundle"]["export_bundle_id"]
            self.assertEqual(payload["export_bundle"]["study_id"], study_id)
            self.assertEqual(payload["export_bundle"]["job_id"], job_id)
            self.assertEqual(payload["export_bundle"]["run_id"], run_id)
            self.assertEqual(payload["export_bundle"]["export_format"], "report_csv")
            self.assertEqual(payload["export_bundle"]["exported_file_count"], 1)
            self.assertIn("synthetic", payload["export_bundle"]["synthetic_boundary"].lower())
            bundle_root = Path(payload["export_bundle"]["bundle_root"])
            self.assertTrue((bundle_root / "report.csv").exists())
            self.assertTrue((bundle_root / "README.md").exists())
            self.assertTrue((bundle_root / "export_manifest.json").exists())

            status, payload = call_app("GET", "/api/v1/export-bundles", token="token-api", query=f"study_id={study_id}")
            self.assertEqual(status, "200 OK")
            self.assertEqual(len(payload["export_bundles"]), 1)
            self.assertEqual(payload["export_bundles"][0]["export_bundle_id"], export_bundle_id)

            status, payload = call_app("GET", f"/api/v1/export-bundles/{export_bundle_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["export_bundle"]["export_bundle_id"], export_bundle_id)
            self.assertEqual(payload["export_bundle"]["manifest_path"], str(bundle_root / "export_manifest.json"))

            status, payload = call_app("GET", f"/api/v1/studies/{study_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["study"]["export_bundle_count"], 1)
            self.assertEqual(payload["study"]["share_bundle_count"], 0)

            status, payload = call_app("GET", f"/api/v1/projects/{project_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["project"]["export_bundle_count"], 1)
            self.assertEqual(payload["project"]["share_bundle_count"], 0)

            status, payload = call_app("GET", "/api/v1/session", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["session"]["product_counts"]["export_bundles"], 1)
            self.assertEqual(payload["session"]["product_counts"]["share_bundles"], 0)

            status, payload = call_app(
                "POST",
                "/api/v1/share-bundles",
                token="token-api",
                payload={
                    "export_bundle_id": export_bundle_id,
                    "title": "Board review share",
                    "expires_in_days": 7,
                },
            )
            self.assertEqual(status, "201 Created")
            share_bundle_id = payload["share_bundle"]["share_bundle_id"]
            share_key = payload["share_bundle"]["share_key"]
            self.assertEqual(payload["share_bundle"]["export_bundle_id"], export_bundle_id)
            self.assertEqual(payload["share_bundle"]["study_id"], study_id)
            self.assertEqual(payload["share_bundle"]["job_id"], job_id)
            self.assertEqual(payload["share_bundle"]["status"], "published")
            self.assertEqual(payload["share_bundle"]["share_file_count"], 1)
            self.assertIn("/public/v1/share-bundles/", payload["share_bundle"]["public_path"])
            self.assertIn("synthetic", payload["share_bundle"]["synthetic_boundary"].lower())
            share_root = Path(payload["share_bundle"]["share_root"])
            self.assertTrue((share_root / "README.md").exists())
            self.assertTrue((share_root / "share_payload.json").exists())

            status, payload = call_app(
                "GET",
                "/api/v1/share-bundles",
                token="token-api",
                query=f"export_bundle_id={export_bundle_id}",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(len(payload["share_bundles"]), 1)
            self.assertEqual(payload["share_bundles"][0]["share_bundle_id"], share_bundle_id)

            status, payload = call_app("GET", f"/api/v1/share-bundles/{share_bundle_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["share_bundle"]["share_bundle_id"], share_bundle_id)
            self.assertEqual(payload["share_bundle"]["share_payload_path"], str(share_root / "share_payload.json"))

            status, payload = call_app("GET", f"/public/v1/share-bundles/{share_key}")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["share_bundle"]["share_bundle_id"], share_bundle_id)
            self.assertEqual(payload["share_bundle"]["status"], "published")
            self.assertEqual(payload["share_bundle"]["source"]["export_bundle_id"], export_bundle_id)
            self.assertEqual(len(payload["share_bundle"]["files"]), 1)
            self.assertIn("synthetic", payload["share_bundle"]["synthetic_boundary"].lower())

            status, payload = call_app("GET", f"/api/v1/studies/{study_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["study"]["share_bundle_count"], 1)

            status, payload = call_app("GET", f"/api/v1/projects/{project_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["project"]["share_bundle_count"], 1)

            status, payload = call_app("GET", f"/api/v1/export-bundles/{export_bundle_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["export_bundle"]["share_bundle_count"], 1)

            status, payload = call_app("GET", "/api/v1/session", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["session"]["product_counts"]["share_bundles"], 1)
            self.assertEqual(payload["session"]["product_counts"]["support_snapshots"], 0)
            self.assertTrue(payload["session"]["capabilities"]["support_surface"])

            status, payload = call_app(
                "POST",
                f"/api/v1/share-bundles/{share_bundle_id}/revoke",
                token="token-api",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["share_bundle"]["status"], "revoked")
            self.assertTrue(payload["share_bundle"]["revoked_at"])

            status, payload = call_app("GET", f"/public/v1/share-bundles/{share_key}")
            self.assertEqual(status, "410 Gone")
            self.assertEqual(payload["error"], "gone")

            status, payload = call_app("GET", "/api/v1/support-diagnostics", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["support"]["submission_gate"]["status"], "allowed")
            self.assertEqual(payload["support"]["selected_job_id"], None)
            self.assertEqual(payload["support"]["recent_failed_jobs"], [])

            status, payload = call_app(
                "POST",
                "/api/v1/validation-jobs",
                token="token-api",
                payload={
                    "brief_path": str(brief_path.relative_to(workspace_root)),
                    "persona_dir": str(persona_dir.relative_to(workspace_root)),
                    "panel_spec": {"panel_type": "mainstream", "sample_size": 1, "random_seed": 9},
                    "provider_name": "unknown-provider",
                    "metadata": {"project_id": project_id, "study_id": study_id},
                },
            )
            self.assertEqual(status, "202 Accepted")
            failed_job_id = payload["job"]["job_id"]
            runtime.process_next_job()
            runtime.process_next_job()

            status, payload = call_app("GET", f"/api/v1/validation-jobs/{failed_job_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["job"]["status"], "failed")
            self.assertIn("provider", payload["job"]["last_error"].lower())

            status, payload = call_app(
                "GET",
                "/api/v1/support-diagnostics",
                token="token-api",
                query=f"job_id={failed_job_id}",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["support"]["selected_job_id"], failed_job_id)
            self.assertEqual(payload["support"]["job_diagnostic"]["status"], "failed")
            self.assertEqual(payload["support"]["job_diagnostic"]["failure_category"], "provider_configuration")
            self.assertTrue(payload["support"]["job_diagnostic"]["can_retry"])
            self.assertTrue(payload["support"]["job_diagnostic"]["created_at"])
            self.assertTrue(payload["support"]["job_diagnostic"]["started_at"])
            self.assertTrue(payload["support"]["job_diagnostic"]["finished_at"])
            self.assertEqual(len(payload["support"]["recent_failed_jobs"]), 1)
            self.assertEqual(payload["support"]["recent_failed_jobs"][0]["job_id"], failed_job_id)
            self.assertEqual(payload["support"]["recent_failed_jobs"][0]["provider_name"], "unknown-provider")

            status, payload = call_app(
                "POST",
                "/api/v1/support-snapshots",
                token="token-api",
                payload={
                    "job_id": failed_job_id,
                    "title": "Provider failure handoff",
                    "notes": "Capture the failed provider configuration before retrying.",
                },
            )
            self.assertEqual(status, "201 Created")
            support_snapshot_id = payload["support_snapshot"]["support_snapshot_id"]
            self.assertEqual(payload["support_snapshot"]["job_id"], failed_job_id)
            self.assertEqual(payload["support_snapshot"]["status"], "generated")
            support_root = Path(payload["support_snapshot"]["support_root"])
            self.assertTrue((support_root / "support_snapshot.json").exists())
            self.assertTrue((support_root / "README.md").exists())

            status, payload = call_app(
                "GET",
                "/api/v1/support-snapshots",
                token="token-api",
                query=f"job_id={failed_job_id}",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(len(payload["support_snapshots"]), 1)
            self.assertEqual(payload["support_snapshots"][0]["support_snapshot_id"], support_snapshot_id)

            status, payload = call_app("GET", f"/api/v1/support-snapshots/{support_snapshot_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["support_snapshot"]["support_snapshot_id"], support_snapshot_id)

            status, payload = call_app("GET", f"/api/v1/studies/{study_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["study"]["support_snapshot_count"], 1)

            status, payload = call_app("GET", f"/api/v1/projects/{project_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["project"]["support_snapshot_count"], 1)

            status, payload = call_app("GET", "/api/v1/session", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["session"]["product_counts"]["support_snapshots"], 1)
            self.assertTrue(payload["session"]["capabilities"]["study_activity"])

            status, payload = call_app(
                "GET",
                f"/api/v1/studies/{study_id}/activity",
                token="token-api",
                query="limit=20",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["study_activity"]["study_id"], study_id)
            self.assertEqual(payload["study_activity"]["project_id"], project_id)
            self.assertGreaterEqual(len(payload["study_activity"]["activity_events"]), 10)
            actions = [event["action"] for event in payload["study_activity"]["activity_events"]]
            self.assertIn("support_snapshot.created", actions)
            self.assertIn("share_bundle.revoked", actions)
            self.assertIn("share_bundle.created", actions)
            self.assertIn("export_bundle.created", actions)
            self.assertIn("decision_log.review_status_updated", actions)
            self.assertIn("decision_log.created", actions)
            self.assertIn("evidence_view.saved", actions)
            self.assertIn("validation_job.completed", actions)
            self.assertIn("validation_job.submitted", actions)
            self.assertIn("study.created", actions)
            support_activity = next(
                event
                for event in payload["study_activity"]["activity_events"]
                if event["action"] == "support_snapshot.created"
            )
            self.assertEqual(support_activity["route_kind"], "support_snapshot")
            self.assertEqual(support_activity["route_id"], support_snapshot_id)

            status, headers, body = call_app_raw("POST", "/api/v1/session/logout", cookie=browser_cookie)
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")
            header_map = {name: value for name, value in headers}
            self.assertIn("Max-Age=0", header_map["Set-Cookie"])

            status, payload = call_app("GET", "/api/v1/session", cookie=browser_cookie)
            self.assertEqual(status, "401 Unauthorized")

            status, headers, _ = call_app_raw("GET", "/app/workspace", query="token=token-api")
            bootstrap_header_map = {name: value for name, value in headers}
            refreshed_browser_cookie = bootstrap_header_map["Set-Cookie"].split(";", 1)[0]

            status, payload = call_app(
                "POST",
                "/api/v1/api-tokens/token-api/revoke",
                token="token-api",
            )
            self.assertEqual(status, "200 OK")
            self.assertFalse(payload["api_token"]["active"])

            status, payload = call_app("GET", "/api/v1/session", cookie=refreshed_browser_cookie)
            self.assertEqual(status, "401 Unauthorized")

    def test_api_workspace_settings_member_and_token_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            runtime.bootstrap_workspace(
                workspace_id="ws_settings",
                slug="settings",
                display_name="Settings Workspace",
                owner_user_id="owner_settings",
                api_token="token-settings",
                plan_tier="trial",
                billing_status="trialing",
                settings={"daily_runs": 3, "max_concurrent_jobs": 1, "artifact_retention_days": 7},
            )
            app = SaasApiApplication(runtime)

            def call_app(method: str, path: str, *, token: str = "", payload: dict | None = None, query: str = ""):
                body = json.dumps(payload or {}).encode("utf-8")
                captured: dict[str, object] = {}

                def start_response(status: str, headers):
                    captured["status"] = status
                    captured["headers"] = headers

                environ = {
                    "REQUEST_METHOD": method,
                    "PATH_INFO": path,
                    "QUERY_STRING": query,
                    "CONTENT_LENGTH": str(len(body)),
                    "CONTENT_TYPE": "application/json",
                    "wsgi.input": io.BytesIO(body),
                    "HTTP_AUTHORIZATION": f"Bearer {token}" if token else "",
                }
                response_body = b"".join(app(environ, start_response))
                return str(captured["status"]), json.loads(response_body.decode("utf-8"))

            status, payload = call_app("GET", "/api/v1/workspace-settings", token="token-settings")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["workspace_settings"]["workspace"]["workspace_id"], "ws_settings")
            self.assertEqual(payload["workspace_settings"]["members"][0]["role"], "owner")
            self.assertTrue(payload["workspace_settings"]["capabilities"]["workspace_settings"])
            self.assertTrue(payload["workspace_settings"]["capabilities"]["billing_mutation"])
            self.assertTrue(payload["workspace_settings"]["capabilities"]["audit_history"])

            status, payload = call_app(
                "POST",
                "/api/v1/workspace-billing",
                token="token-settings",
                payload={
                    "plan_tier": "pro",
                    "billing_status": "active",
                    "seat_count": 4,
                    "renewal_at": "2026-07-31T00:00:00+00:00",
                    "daily_runs": 25,
                    "max_concurrent_jobs": 3,
                    "artifact_retention_days": 30,
                },
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["billing"]["workspace"]["plan_tier"], "pro")
            self.assertEqual(payload["billing"]["billing_account"]["status"], "active")
            self.assertEqual(payload["billing"]["billing_account"]["seat_count"], 4)
            self.assertEqual(payload["billing"]["plan_limits"]["daily_runs"], 25)
            self.assertEqual(payload["workspace_settings"]["billing_account"]["price_book_id"], "pro")
            self.assertEqual(payload["workspace_settings"]["policies"]["artifact_retention_days"], 30)

            status, payload = call_app(
                "POST",
                "/api/v1/workspace-members",
                token="token-settings",
                payload={"user_id": "researcher_001", "role": "editor"},
            )
            self.assertEqual(status, "201 Created")
            self.assertEqual(payload["member"]["user_id"], "researcher_001")
            self.assertEqual(payload["member"]["role"], "editor")
            self.assertEqual(len(payload["workspace_settings"]["members"]), 2)

            status, payload = call_app(
                "POST",
                "/api/v1/api-tokens",
                token="token-settings",
                payload={"user_id": "researcher_001"},
            )
            self.assertEqual(status, "201 Created")
            issued_token = payload["api_token"]["token"]
            self.assertTrue(issued_token.startswith("token_"))
            self.assertEqual(payload["api_token"]["user_id"], "researcher_001")
            self.assertEqual(payload["api_token"]["role"], "editor")
            self.assertEqual(len(payload["workspace_settings"]["api_tokens"]), 2)
            self.assertTrue(any(token["active"] for token in payload["workspace_settings"]["api_tokens"] if token["user_id"] == "researcher_001"))

            status, payload = call_app(
                "POST",
                f"/api/v1/api-tokens/{issued_token}/revoke",
                token="token-settings",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["api_token"]["token_id"], issued_token)
            self.assertFalse(payload["api_token"]["active"])
            self.assertTrue(any((not token["active"]) for token in payload["workspace_settings"]["api_tokens"] if token["token_id"] == issued_token))

            status, payload = call_app(
                "GET",
                "/api/v1/audit-events",
                token="token-settings",
                query="target_type=api_token&action_prefix=api_token.&limit=5",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["audit_history"]["filters"]["target_type"], "api_token")
            self.assertEqual(payload["audit_history"]["filters"]["action_prefix"], "api_token.")
            self.assertEqual(payload["audit_history"]["filters"]["limit"], 5)
            self.assertEqual(len(payload["audit_history"]["audit_events"]), 2)
            self.assertEqual(
                {event["action"] for event in payload["audit_history"]["audit_events"]},
                {"api_token.issued", "api_token.revoked"},
            )

            status, payload = call_app("GET", "/api/v1/session", token="token-settings")
            self.assertEqual(status, "200 OK")
            self.assertTrue(payload["session"]["capabilities"]["workspace_settings"])
            self.assertTrue(payload["session"]["capabilities"]["billing_surface"])
            self.assertTrue(payload["session"]["capabilities"]["audit_history"])
            self.assertEqual(payload["session"]["workspace"]["plan_tier"], "pro")
            self.assertEqual(payload["session"]["plan_limits"]["max_concurrent_jobs"], 3)


if __name__ == "__main__":
    unittest.main()
