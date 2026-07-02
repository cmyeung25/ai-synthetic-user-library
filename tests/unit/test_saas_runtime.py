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
from ai_validation_swarm.conversation.providers import ChatResult
from ai_validation_swarm.facilitator.models import FacilitatorDecision
from ai_validation_swarm.facilitator.runtime import FacilitatedInterviewRuntime
from ai_validation_swarm.personas.frontline_v5_generator import FrontlineLocalV5SynthesisAdapter, build_frontline_v5_generation_guide
from ai_validation_swarm.personas.generator import generate_personas
from ai_validation_swarm.personas.v5 import generate_v5_persona
from ai_validation_swarm.providers.base import BaseProvider
from ai_validation_swarm.saas import job_store
from ai_validation_swarm.saas.evidence_query import query_run_evidence
from ai_validation_swarm.saas.api import SaasApiApplication, SaasApiDeploymentProfile
from ai_validation_swarm.saas.models import TenantWorkspace, WorkspaceMember
from ai_validation_swarm.saas.runtime import AuthorizationError, SaasRuntime, ShareUnavailableError, ValidationJobRequest
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

    def test_frontline_persona_library_uses_v5_participants_and_separates_lenses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_v5_personas",
                slug="v5-personas",
                display_name="V5 Personas",
                owner_user_id="owner_legacy",
                api_token="token-legacy",
                plan_tier="trial",
                billing_status="trialing",
                settings={"daily_runs": 5, "max_concurrent_jobs": 2},
            )
            workspace_root = Path(bootstrap["workspace_root"])
            persona_dir = workspace_root / "personas"
            persona = generate_personas(count=1, random_seed=91)[0]
            persona.seed.panel_role = "general_research_participant"
            persona.profile.basic_identity.pop("locale_pack", None)
            persona.profile.economic_profile.pop("purchase_authority_type", None)
            save_persona(persona, persona_dir)
            adapter = FrontlineLocalV5SynthesisAdapter()
            guide = build_frontline_v5_generation_guide(panel_type="mainstream", target_audience={"summary": "Solo founders"})
            participant_folder = generate_v5_persona(
                persona_id="su_9001",
                output_dir=persona_dir,
                adapter=adapter,
                guide=guide,
                random_seed=91,
                max_transport_attempts=1,
            )
            lens_folder = generate_v5_persona(
                persona_id="su_9002",
                output_dir=persona_dir,
                adapter=adapter,
                guide=guide,
                random_seed=92,
                max_transport_attempts=1,
            )
            write_json(
                lens_folder / "persona_library_record.json",
                {
                    "contract_version": "persona-library-record/v0-draft",
                    "synthetic_user_id": "su_9002",
                    "persona_kind": "public_figure_lens",
                    "readiness_status": "ready",
                    "lens_boundary": "Simulated and unaffiliated public-figure lens, not participant evidence.",
                },
            )

            auth = runtime.authenticate("token-legacy")
            library = runtime.describe_frontline_persona_library(
                auth,
                panel_type="mainstream",
                sample_size=1,
                random_seed=17,
            )

            self.assertEqual(library["readiness"]["status"], "ready")
            self.assertEqual(library["readiness"]["active_panel_ready_count"], 1)
            self.assertEqual(library["readiness"]["legacy_participant_count"], 1)
            self.assertEqual(library["readiness"]["simulated_lens_count"], 1)
            self.assertEqual(len(library["personas"]), 1)
            self.assertEqual(library["personas"][0]["panel_role"], "mainstream")
            self.assertEqual(library["personas"][0]["source_schema_version"], "v5_1")
            self.assertEqual(library["personas"][0]["generator_version"], "persona-generator/v5.1")
            self.assertEqual(library["default_selection"]["selected_persona_ids"], ["su_9001"])
            self.assertEqual(len(library["simulated_lenses"]), 1)
            self.assertEqual(library["simulated_lenses"][0]["synthetic_user_id"], "su_9002")
            self.assertEqual(library["simulated_lenses"][0]["persona_kind"], "public_figure_lens")
            self.assertEqual(library["library_summary"]["library_size"], 1)
            self.assertTrue((participant_folder / "profile.json").exists())

            empty_skeptic = runtime.describe_frontline_persona_library(
                auth,
                panel_type="skeptic",
                sample_size=1,
                random_seed=17,
            )
            self.assertEqual(empty_skeptic["readiness"]["status"], "empty")
            self.assertEqual(empty_skeptic["readiness"]["active_panel_ready_count"], 0)
            self.assertEqual(empty_skeptic["readiness"]["alternative_panel_type"], "mainstream")
            self.assertEqual(empty_skeptic["readiness"]["alternative_panel_count"], 1)
            self.assertEqual(len(empty_skeptic["personas"]), 0)
            self.assertIn("Switch panel or generate Skeptic participants", empty_skeptic["readiness"]["message"])

            skeptic_guide = build_frontline_v5_generation_guide(
                panel_type="skeptic",
                target_audience={"summary": "Skeptical founders"},
            )
            skeptic_folder = generate_v5_persona(
                persona_id="su_9003",
                output_dir=persona_dir,
                adapter=adapter,
                guide=skeptic_guide,
                random_seed=93,
                max_transport_attempts=1,
            )
            skeptic_library = runtime.describe_frontline_persona_library(
                auth,
                panel_type="skeptic",
                sample_size=1,
                random_seed=17,
            )
            self.assertEqual(skeptic_library["readiness"]["status"], "ready")
            self.assertEqual(skeptic_library["readiness"]["active_panel_ready_count"], 1)
            self.assertEqual(skeptic_library["personas"][0]["synthetic_user_id"], "su_9003")
            self.assertEqual(skeptic_library["personas"][0]["panel_role"], "skeptic")
            self.assertEqual(skeptic_library["default_selection"]["selected_persona_ids"], ["su_9003"])
            self.assertTrue((skeptic_folder / "profile.json").exists())

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
            evidence_query = runtime.query_workspace_evidence(auth, job_id=job["job_id"])
            self.assertEqual(evidence_query["query_status"], "query_ready")
            self.assertGreaterEqual(evidence_query["result_count"], 1)

            purged = runtime.purge_expired_run_artifacts(now=datetime.now(UTC) + timedelta(seconds=1))

            self.assertEqual(purged, [job["job_id"]])
            self.assertFalse(run_dir.exists())
            reloaded = runtime.get_validation_job(auth, job["job_id"])
            self.assertTrue(reloaded["metadata"]["artifact_deleted_at"])

    def test_worker_marks_failed_research_run_as_failed_job(self) -> None:
        class BrokenProvider(BaseProvider):
            model_version = "broken:test"

            def persona_response(self, persona, brief, protocol_id):
                raise RuntimeError("simulated provider transport failure")

            def skeptic_review(self, brief, personas, responses):
                raise RuntimeError("not reached")

            def sensitive_audit(self, brief, personas, responses):
                raise RuntimeError("not reached")

            def planner(self, brief, summary, findings):
                raise RuntimeError("not reached")

        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root, provider_builder=lambda _: BrokenProvider())
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_failed_run",
                slug="failed-run",
                display_name="Failed Run",
                owner_user_id="owner_failed_run",
                api_token="token-failed-run",
                plan_tier="trial",
                billing_status="trialing",
                settings={"daily_runs": 5, "max_concurrent_jobs": 2},
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)
            auth = runtime.authenticate("token-failed-run")

            job = runtime.submit_validation_job(
                auth,
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    provider_name="codex",
                    max_retries=1,
                ),
            )

            failed = runtime.process_next_job()

            self.assertEqual(failed["job_id"], job["job_id"])
            self.assertEqual(failed["status"], "failed")
            self.assertIn("All persona responses failed", failed["last_error"])
            self.assertEqual(failed["metadata"]["research_run_status"], "failed")
            self.assertTrue(Path(str(failed["output_run_path"])).exists())
            self.assertEqual(failed["metadata"]["provider_runtime_boundary"]["provider_name"], "codex")
            self.assertEqual(failed["metadata"]["provider_runtime_boundary"]["runtime_status"], "runtime_failure")

    def test_workspace_shell_exposes_live_provider_runtime_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_codex_boundary",
                slug="codex-boundary",
                display_name="Codex Boundary",
                owner_user_id="owner_codex_boundary",
                api_token="token-codex-boundary",
                plan_tier="pro",
                billing_status="active",
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)
            auth = runtime.authenticate("token-codex-boundary")

            job = runtime.submit_validation_job(
                auth,
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    provider_name="codex",
                    max_retries=1,
                ),
            )

            snapshot = runtime.describe_workspace_shell(auth, job_id=str(job["job_id"]))
            provider_runtime = snapshot["provider_runtime"]
            selected_boundary = provider_runtime["selected_job_boundary"]
            catalog_names = {item["provider_name"] for item in snapshot["session"]["validation_provider_catalog"]}

            self.assertTrue(snapshot["session"]["capabilities"]["provider_runtime_boundary"])
            self.assertIn("mock", catalog_names)
            self.assertIn("codex", catalog_names)
            self.assertEqual(selected_boundary["provider_name"], "codex")
            self.assertEqual(selected_boundary["evidence_mode"], "live_synthetic")
            self.assertTrue(selected_boundary["is_live_provider"])
            self.assertTrue(selected_boundary["is_codex_provider"])
            self.assertIn(selected_boundary["auth_readiness"], {"ready", "missing_or_unverified"})
            self.assertIn(selected_boundary["runtime_status"], {"queued", "missing_auth"})
            self.assertEqual(snapshot["evidence_query"]["provider_runtime_boundary"]["provider_name"], "codex")
            self.assertEqual(snapshot["selected_job"]["metadata"]["provider_runtime_boundary"]["provider_name"], "codex")

    def test_support_and_operations_expose_unsupported_provider_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_provider_failure",
                slug="provider-failure",
                display_name="Provider Failure",
                owner_user_id="owner_provider_failure",
                api_token="token-provider-failure",
                plan_tier="pro",
                billing_status="active",
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)
            auth = runtime.authenticate("token-provider-failure")

            job = runtime.submit_validation_job(
                auth,
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    provider_name="unknown-provider",
                    max_retries=1,
                ),
            )

            failed = runtime.process_next_job()
            self.assertEqual(failed["job_id"], job["job_id"])
            self.assertEqual(failed["status"], "failed")
            failed_boundary = failed["metadata"]["provider_runtime_boundary"]
            self.assertEqual(failed_boundary["provider_name"], "unknown-provider")
            self.assertFalse(failed_boundary["is_supported"])
            self.assertEqual(failed_boundary["runtime_status"], "unsupported_provider")
            self.assertEqual(failed_boundary["failure_kind"], "unsupported_provider")

            support = runtime.describe_workspace_support(auth, job_id=str(job["job_id"]))
            diagnostic_boundary = support["job_diagnostic"]["provider_runtime_boundary"]
            recent_boundary = support["recent_failed_jobs"][0]["provider_runtime_boundary"]
            self.assertEqual(support["provider_runtime"]["selected_job_boundary"]["runtime_status"], "unsupported_provider")
            self.assertEqual(diagnostic_boundary["runtime_status"], "unsupported_provider")
            self.assertEqual(recent_boundary["evidence_mode"], "unsupported")
            self.assertEqual(support["job_diagnostic"]["failure_category"], "provider_configuration")

            operations = runtime.describe_workspace_operations_summary(auth)
            self.assertEqual(operations["provider_runtime"]["unsupported_job_count"], 1)
            self.assertEqual(operations["provider_runtime"]["runtime_status_counts"]["unsupported_provider"], 1)

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

    def test_workspace_study_regulated_boundary_blocks_submission_until_acknowledged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_governed",
                slug="governed",
                display_name="Governed",
                owner_user_id="owner_governed",
                api_token="token-governed",
                plan_tier="pro",
                billing_status="active",
                settings={"daily_runs": 5, "max_concurrent_jobs": 2},
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)
            auth = runtime.authenticate("token-governed")
            project = runtime.create_workspace_project(auth, name="Governed Program")
            study = runtime.create_workspace_study(
                auth,
                project_id=project["project_id"],
                title="Medical onboarding study",
                research_intent="Understand how clinic operators decide whether to trust a patient intake workflow.",
                desired_output="health workflow risk review",
                first_task="log in and review a patient record",
            )

            self.assertEqual(study["regulated_review_boundary"]["classification_status"], "high_stakes")
            self.assertIn("health", study["regulated_review_boundary"]["matched_domain_ids"])
            self.assertEqual(study["regulated_review_boundary"]["execution_status"], "blocked_pending_boundary_review")

            support = runtime.describe_workspace_support(auth, study_id=study["study_id"])
            self.assertEqual(support["selected_study_id"], study["study_id"])
            self.assertEqual(support["study_boundary"]["classification_status"], "high_stakes")
            self.assertEqual(support["submission_gate"]["status"], "blocked")
            self.assertEqual(
                support["submission_gate"]["blocked_reasons"][-1]["code"],
                "regulated_high_stakes_boundary_required",
            )

            with self.assertRaises(AuthorizationError):
                runtime.submit_validation_job(
                    auth,
                    ValidationJobRequest(
                        brief_path=str(brief_path.relative_to(workspace_root)),
                        persona_dir=str(persona_dir.relative_to(workspace_root)),
                        panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                        provider_name="mock",
                        metadata={"project_id": project["project_id"], "study_id": study["study_id"]},
                    ),
                )

    def test_workspace_study_regulated_boundary_does_not_match_911_inside_timestamp(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            runtime.bootstrap_workspace(
                workspace_id="ws_timestamp_boundary",
                slug="timestamp-boundary",
                display_name="Timestamp Boundary",
                owner_user_id="owner_timestamp_boundary",
                api_token="token-timestamp-boundary",
                plan_tier="pro",
                billing_status="active",
            )
            auth = runtime.authenticate("token-timestamp-boundary")
            project = runtime.create_workspace_project(auth, name="Timestamp Boundary Program")

            ordinary_study = runtime.create_workspace_study(
                auth,
                project_id=project["project_id"],
                title="Pain empathy insight discovery 1782732539119",
                research_intent=(
                    "Explore recurring product-discovery pain, root causes, current workaround behavior, "
                    "decision triggers, workflow fragmentation, and insight opportunities."
                ),
                desired_output="discovery insight review",
                first_task="describe a recent product-discovery workflow breakdown",
            )
            self.assertEqual(ordinary_study["regulated_review_boundary"]["classification_status"], "standard")
            self.assertEqual(ordinary_study["regulated_review_boundary"]["matched_domain_ids"], [])
            self.assertEqual(ordinary_study["regulated_review_boundary"]["execution_status"], "allowed")

            emergency_study = runtime.create_workspace_study(
                auth,
                project_id=project["project_id"],
                title="Emergency response concept",
                research_intent="Evaluate whether the workflow helps operators decide when to call 911.",
                desired_output="public safety review",
                first_task="review emergency escalation guidance",
            )
            self.assertEqual(emergency_study["regulated_review_boundary"]["classification_status"], "high_stakes")
            self.assertIn("public_safety", emergency_study["regulated_review_boundary"]["matched_domain_ids"])

    def test_workspace_study_regulated_boundary_can_be_acknowledged_and_propagates_to_export_and_share(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_governed_allowed",
                slug="governed-allowed",
                display_name="Governed Allowed",
                owner_user_id="owner_governed_allowed",
                api_token="token-governed-allowed",
                plan_tier="pro",
                billing_status="active",
                settings={"daily_runs": 5, "max_concurrent_jobs": 2},
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)
            auth = runtime.authenticate("token-governed-allowed")
            project = runtime.create_workspace_project(auth, name="Governed Program")
            study = runtime.create_workspace_study(
                auth,
                project_id=project["project_id"],
                title="Medical onboarding study",
                research_intent="Understand how clinic operators decide whether to trust a patient intake workflow.",
                desired_output="health workflow risk review",
                first_task="log in and review a patient record",
                metadata={
                    "regulated_review_boundary": {
                        "boundary_handling_status": "acknowledged",
                        "allow_execution": True,
                        "explicit_boundary_note": "Scoped operator review approved before synthetic execution.",
                        "explicit_boundary_acknowledged_at": "2026-06-29T00:00:00+00:00",
                        "explicit_boundary_acknowledged_by_user_id": "owner_governed_allowed",
                    }
                },
            )

            self.assertEqual(study["regulated_review_boundary"]["execution_status"], "allowed")
            self.assertTrue(study["regulated_review_boundary"]["explicit_boundary_acknowledged"])
            self.assertEqual(study["governed_review"]["review_gate_status"], "blocked_reviewer_unassigned")

            workspace = job_store.get_workspace(runtime_root, "ws_governed_allowed")
            workspace.members.append(WorkspaceMember(user_id="reviewer_001", role="editor", joined_at=workspace.created_at))
            job_store.upsert_workspace(runtime_root, workspace)
            job_store.register_api_token(
                runtime_root,
                token="token-governed-reviewer",
                workspace_id="ws_governed_allowed",
                user_id="reviewer_001",
                role="editor",
                issued_at=workspace.created_at,
            )
            reviewer_auth = runtime.authenticate("token-governed-reviewer")

            job = runtime.submit_validation_job(
                auth,
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    provider_name="mock",
                    metadata={"project_id": project["project_id"], "study_id": study["study_id"]},
                ),
            )
            self.assertEqual(job["metadata"]["regulated_review_boundary"]["classification_status"], "high_stakes")
            self.assertEqual(job["metadata"]["regulated_review_boundary"]["execution_status"], "allowed")

            completed = runtime.process_next_job()
            evidence_query = runtime.query_workspace_evidence(auth, job_id=job["job_id"])
            self.assertEqual(evidence_query["governed_review"]["review_gate_status"], "blocked_reviewer_unassigned")

            export_bundle = runtime.create_workspace_export_bundle(
                auth,
                study_id=study["study_id"],
                job_id=job["job_id"],
                title="Governed export",
                export_format="report_json",
            )
            export_manifest = json.loads(Path(export_bundle["manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(export_manifest["regulated_review_boundary"]["classification_status"], "high_stakes")
            self.assertIn("health", export_manifest["regulated_review_boundary"]["matched_domain_ids"])
            self.assertEqual(
                export_manifest["metadata"]["regulated_review_boundary"]["boundary_handling_status"],
                "acknowledged",
            )
            self.assertEqual(export_manifest["governed_review"]["review_gate_status"], "blocked_reviewer_unassigned")

            with self.assertRaises(AuthorizationError):
                runtime.create_workspace_share_bundle(
                    auth,
                    export_bundle_id=export_bundle["export_bundle_id"],
                    title="Governed share",
                    expires_in_days=7,
                )

            updated_study = runtime.update_workspace_study_governed_review_assignment(
                auth,
                study_id=study["study_id"],
                assignee_user_ids=["reviewer_001"],
                status="assigned",
                note="Assign governed reviewer before approval and circulation.",
            )
            self.assertEqual(updated_study["governed_review"]["review_gate_status"], "assigned_for_review")
            self.assertEqual(
                updated_study["governed_review"]["reviewer_handoff"]["assignee_user_ids"],
                ["reviewer_001"],
            )
            self.assertEqual(updated_study["governed_redaction"]["status"], "unconfigured")

            refreshed_export_manifest = json.loads(Path(export_bundle["manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(refreshed_export_manifest["governed_review"]["review_gate_status"], "assigned_for_review")
            self.assertEqual(
                refreshed_export_manifest["compliance_audit_bundle"]["status"],
                "pending_governed_redaction",
            )

            decision_log = runtime.create_workspace_decision_log(
                auth,
                study_id=study["study_id"],
                job_id=job["job_id"],
                title="Governed decision",
                decision_summary="Proceed only with named reviewer oversight.",
                rationale="The study is high-stakes and still bounded by governed human review.",
            )
            self.assertEqual(decision_log["governed_review"]["review_gate_status"], "assigned_for_review")
            self.assertEqual(decision_log["review_assignment"]["status"], "assigned")
            self.assertEqual(decision_log["review_assignment"]["assignee_user_ids"], ["reviewer_001"])

            approved_decision = runtime.update_workspace_decision_review_status(
                reviewer_auth,
                decision_log_id=decision_log["decision_log_id"],
                review_status="approved",
                note="Governed reviewer approved the bounded decision.",
            )
            self.assertEqual(approved_decision["review_status"], "approved")

            post_assignment_query = runtime.query_workspace_evidence(auth, job_id=job["job_id"])
            self.assertEqual(post_assignment_query["governed_review"]["review_gate_status"], "assigned_for_review")
            self.assertEqual(post_assignment_query["governed_redaction"]["status"], "unconfigured")

            with self.assertRaises(AuthorizationError):
                runtime.create_workspace_share_bundle(
                    auth,
                    export_bundle_id=export_bundle["export_bundle_id"],
                    title="Governed share",
                    expires_in_days=7,
                )

            redacted_study = runtime.update_workspace_study_governed_redaction(
                auth,
                study_id=study["study_id"],
                status="active",
                redaction_rules=[
                    {
                        "path": "study_context.research_intent",
                        "reason": "Protect sensitive clinic workflow detail.",
                        "replacement": "[REDACTED: research intent]",
                    },
                    {
                        "path": "study_context.first_task",
                        "reason": "Protect patient-record handling detail.",
                        "replacement": "[REDACTED: first task]",
                    },
                ],
                note="Activate viewer-safe circulation redactions for external delivery.",
            )
            self.assertEqual(redacted_study["governed_redaction"]["status"], "active")
            self.assertEqual(redacted_study["governed_redaction"]["rule_count"], 2)

            share_bundle = runtime.create_workspace_share_bundle(
                auth,
                export_bundle_id=export_bundle["export_bundle_id"],
                title="Governed share",
                expires_in_days=7,
            )
            share_payload = json.loads(Path(share_bundle["share_payload_path"]).read_text(encoding="utf-8"))
            self.assertEqual(share_payload["regulated_review_boundary"]["classification_status"], "high_stakes")
            self.assertEqual(
                share_payload["metadata"]["regulated_review_boundary"]["explicit_boundary_acknowledged_by_user_id"],
                "owner_governed_allowed",
            )
            self.assertEqual(share_payload["governed_review"]["review_gate_status"], "assigned_for_review")
            self.assertEqual(
                share_payload["governed_review"]["reviewer_handoff"]["assignee_user_ids"],
                ["reviewer_001"],
            )
            self.assertEqual(share_payload["governed_redaction"]["status"], "active")
            self.assertEqual(
                share_payload["study_context"]["research_intent"],
                "[REDACTED: research intent]",
            )
            self.assertEqual(
                share_payload["study_context"]["first_task"],
                "[REDACTED: first task]",
            )
            self.assertEqual(len(share_payload["governed_redaction"]["applied_redactions"]), 2)
            self.assertEqual(share_payload["compliance_audit_bundle"]["status"], "ready")
            self.assertEqual(len(share_payload["compliance_audit_bundle"]["applied_redactions"]), 2)
            self.assertTrue(
                Path(share_payload["metadata"]["compliance_audit_bundle_path"]).exists()
            )

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

    def test_frontline_studio_plan_revision_and_study_report_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_frontline",
                slug="frontline",
                display_name="Frontline",
                owner_user_id="owner_frontline",
                api_token="token-frontline",
                plan_tier="pro",
                billing_status="active",
                settings={"daily_runs": 10, "max_concurrent_jobs": 2},
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path = workspace_root / "briefs" / "brief.json"
            write_json(
                brief_path,
                FounderBrief(
                    brief_id="brief_frontline",
                    project_name="Frontline Concept",
                    problem_statement="Founders lose evidence context across follow-up work.",
                    target_market="Solo founders",
                    offered_solution="A workspace that keeps recommendation evidence inspectable.",
                    validation_goal="Check whether the concept creates trust and adoption objections.",
                ).to_dict(),
            )
            persona_dir = workspace_root / "personas"
            app = SaasApiApplication(runtime)

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

            def call_app(method: str, path: str, **kwargs):
                status, _headers, body = call_app_raw(method, path, **kwargs)
                return status, json.loads(body.decode("utf-8"))

            status, headers, _body = call_app_raw("GET", "/studio", query="token=token-frontline")
            self.assertEqual(status, "302 Found")
            browser_cookie = next(value for name, value in headers if name == "Set-Cookie").split(";", 1)[0]

            status, _headers, body = call_app_raw("GET", "/studio", cookie=browser_cookie)
            self.assertEqual(status, "200 OK")
            self.assertIn(b"__FRONTLINE_ROUTE_CONTEXT__", body)
            self.assertIn(b'"route_kind": "workspace"', body)
            self.assertIn(b"frontline-research-studio.js", body)

            def assert_frontline_route(path: str, route_kind: str, expected_pairs: dict[str, str] | None = None) -> None:
                status, _headers, route_body = call_app_raw("GET", path, cookie=browser_cookie)
                self.assertEqual(status, "200 OK", path)
                self.assertIn(f'"route_kind": "{route_kind}"'.encode("utf-8"), route_body)
                for key, value in (expected_pairs or {}).items():
                    self.assertIn(f'"{key}": "{value}"'.encode("utf-8"), route_body)

            assert_frontline_route("/studio/projects", "projects")
            assert_frontline_route("/studio/studies/new", "new_study")
            status, _headers, _body = call_app_raw("GET", "/studio/not-a-route", cookie=browser_cookie)
            self.assertEqual(status, "404 Not Found")

            status, _headers, body = call_app_raw(
                "GET",
                "/app-static/frontend/frontline_research_studio/dist/assets/frontline-research-studio.js",
            )
            self.assertEqual(status, "200 OK")
            self.assertIn(b"Frontline Studio", body)

            status, payload = call_app(
                "POST",
                "/api/v1/projects",
                token="token-frontline",
                payload={"name": "Frontline Concept"},
            )
            self.assertEqual(status, "201 Created")
            project_id = payload["project"]["project_id"]
            assert_frontline_route(
                f"/studio/projects/{project_id}",
                "project",
                {"project_id": project_id},
            )

            status, payload = call_app(
                "POST",
                "/api/v1/studies",
                token="token-frontline",
                payload={
                    "project_id": project_id,
                    "title": "Founder concept validation",
                    "research_intent": "Test whether founders understand and trust the concept.",
                    "desired_output": "objections, trust gaps, adoption barriers, and validation gaps",
                    "metadata": {"source": "frontline_research_studio"},
                },
            )
            self.assertEqual(status, "201 Created")
            study_id = payload["study"]["study_id"]
            for route_path, route_kind, expected in [
                (f"/studio/studies/{study_id}", "study", {"study_id": study_id}),
                (f"/studio/studies/{study_id}/setup", "study_setup", {"study_id": study_id}),
                (f"/studio/studies/{study_id}/runs", "study_runs", {"study_id": study_id}),
                (f"/studio/studies/{study_id}/runs/run_missing", "run", {"study_id": study_id, "run_id": "run_missing"}),
                (f"/studio/studies/{study_id}/evidence", "study_evidence", {"study_id": study_id}),
                (
                    f"/studio/studies/{study_id}/evidence-views/view_missing",
                    "evidence_view",
                    {"study_id": study_id, "evidence_view_id": "view_missing"},
                ),
            ]:
                assert_frontline_route(route_path, route_kind, expected)

            status, payload = call_app(
                "GET",
                "/api/v1/persona-library",
                token="token-frontline",
                query="panel_type=mainstream&sample_size=1&random_seed=17",
            )
            self.assertEqual(status, "200 OK")
            persona_library = payload["persona_library"]
            self.assertEqual(persona_library["active_panel_type"], "mainstream")
            self.assertEqual(persona_library["readiness"]["status"], "empty")
            self.assertGreaterEqual(len(persona_library["panel_options"]), 1)
            self.assertEqual(len(persona_library["personas"]), 0)
            self.assertEqual(persona_library["default_selection"]["selected_persona_ids"], [])

            status, payload = call_app(
                "POST",
                f"/api/v1/studies/{study_id}/frontline-plan-proposals",
                token="token-frontline",
                payload={
                    "user_message": "This should fail until a synthetic participant is selected.",
                    "persona_panel": {
                        "contract_version": "persona-panel-selection/v0-draft",
                        "panel_type": "mainstream",
                        "sample_size": 1,
                        "selected_persona_ids": [],
                    },
                },
            )
            self.assertEqual(status, "400 Bad Request")
            self.assertIn("Select at least one synthetic participant", payload["message"])

            status, payload = call_app(
                "POST",
                "/api/v1/persona-library/generation-jobs",
                token="token-frontline",
                payload={
                    "panel_type": "mainstream",
                    "requested_count": 2,
                    "random_seed": 41,
                    "target_audience": {"summary": "Solo founders evaluating evidence tools"},
                },
            )
            self.assertEqual(status, "201 Created")
            generation_job = payload["persona_generation_job"]["generation_job"]
            self.assertEqual(generation_job["status"], "completed")
            self.assertEqual(generation_job["panel_type"], "mainstream")
            self.assertEqual(len(payload["persona_generation_job"]["generated_persona_ids"]), 2)
            generation_lifecycle = generation_job["metadata"]["lifecycle"]
            self.assertIn("provisional", {entry["status"] for entry in generation_lifecycle})
            self.assertIn("ready", {entry["status"] for entry in generation_lifecycle})
            generation_job_artifact_path = workspace_root / generation_job["payload_path"]
            self.assertTrue(generation_job_artifact_path.exists())
            generation_job_artifact = json.loads(generation_job_artifact_path.read_text(encoding="utf-8"))
            self.assertEqual(generation_job_artifact["generation_job"]["generation_job_id"], generation_job["generation_job_id"])
            self.assertEqual(
                generation_job_artifact["promoted_persona_ids"],
                payload["persona_generation_job"]["promoted_persona_ids"],
            )

            status, payload = call_app(
                "GET",
                "/api/v1/persona-library",
                token="token-frontline",
                query="panel_type=mainstream&sample_size=1&random_seed=17",
            )
            self.assertEqual(status, "200 OK")
            persona_library = payload["persona_library"]
            self.assertEqual(persona_library["readiness"]["status"], "ready")
            self.assertGreaterEqual(len(persona_library["personas"]), 1)
            self.assertEqual(persona_library["personas"][0]["readiness_status"], "ready")
            self.assertEqual(persona_library["personas"][0]["source_schema_version"], "v5_1")
            self.assertEqual(persona_library["personas"][0]["generator_version"], "persona-generator/v5.1")
            self.assertEqual(persona_library["persona_groups"]["generated_personas"]["count"], 2)
            self.assertTrue(persona_library["personas"][0]["persona_version"])
            self.assertIn("profile.json", persona_library["personas"][0]["artifact_hashes"])
            self.assertIn("generation_job_id", persona_library["personas"][0])
            self.assertIn("public_figure_lens", persona_library["lens_boundary"]["excluded_from_participant_pool"])
            selected_persona_ids = persona_library["default_selection"]["selected_persona_ids"]
            self.assertEqual(len(selected_persona_ids), 1)
            self.assertTrue(
                (workspace_root / "personas" / selected_persona_ids[0] / "v5_1" / "profile.json").exists()
            )
            persona_panel = {
                **persona_library["default_selection"],
                "coverage_snapshot": persona_library["library_summary"]["human_difference_axis_summary"],
            }
            target_audience = {
                "summary": "Solo founders evaluating evidence tools",
                "inclusion_criteria": [
                    "Owns the decision to try early research tooling",
                    "Can compare synthetic research against current founder workflow",
                ],
                "excluded_context": "Do not treat this panel as recruited market proof.",
            }

            status, payload = call_app(
                "POST",
                f"/api/v1/studies/{study_id}/frontline-plan-proposals",
                token="token-frontline",
                payload={
                    "user_message": "I need to test a landing page headline, positioning copy, and value proposition.",
                    "target_persona": target_audience["summary"],
                    "target_audience": target_audience,
                    "persona_panel": persona_panel,
                    "moderator_questions": [
                        "What do you believe this message promises?",
                        "Which words feel credible, vague, exaggerated, or confusing?",
                    ],
                },
            )
            self.assertEqual(status, "201 Created")
            self.assertEqual(payload["plan_proposal"]["mode_inference"]["mode"], "messaging_validation")
            self.assertIn("message_comprehension", payload["plan_proposal"]["expected_evidence_types"])

            status, payload = call_app(
                "POST",
                f"/api/v1/studies/{study_id}/frontline-plan-proposals",
                token="token-frontline",
                payload={
                    "user_message": "I have a startup idea and need to know if the concept works.",
                    "target_persona": target_audience["summary"],
                    "target_audience": target_audience,
                    "persona_panel": persona_panel,
                    "moderator_questions": [
                        "What do you understand this evidence tool is meant to help with?",
                        "Where would trust or switching risk stop you from trying it?",
                    ],
                    "metadata": {"source": "frontline_research_studio"},
                },
            )
            self.assertEqual(status, "201 Created")
            proposal_id = payload["plan_proposal"]["plan_proposal_id"]
            self.assertEqual(payload["study"]["status"], "ready_to_run")
            self.assertEqual(payload["plan_proposal"]["mode_inference"]["mode"], "concept_validation")
            self.assertEqual(payload["plan_proposal"]["target_audience"]["summary"], target_audience["summary"])
            self.assertEqual(
                payload["plan_proposal"]["persona_panel"]["selected_persona_ids"],
                selected_persona_ids,
            )
            self.assertEqual(
                payload["plan_proposal"]["moderator_interview_guide"]["questions"][0],
                "What do you understand this evidence tool is meant to help with?",
            )

            status, payload = call_app(
                "POST",
                f"/api/v1/studies/{study_id}/frontline-plan-revisions",
                token="token-frontline",
                payload={
                    "plan_proposal_id": proposal_id,
                    "confirmation_note": "Approved for a first synthetic run.",
                },
            )
            self.assertEqual(status, "201 Created")
            plan_revision_id = payload["plan_revision"]["plan_revision_id"]
            self.assertEqual(payload["study"]["current_plan_revision_id"], plan_revision_id)
            self.assertEqual(payload["plan_revision"]["persona_panel"]["selected_persona_ids"], selected_persona_ids)
            self.assertEqual(payload["plan_revision"]["target_audience"]["inclusion_criteria"], target_audience["inclusion_criteria"])

            status, payload = call_app(
                "POST",
                f"/api/v1/studies/{study_id}/frontline-runs",
                token="token-frontline",
                payload={"metadata": {"acceptance": "m32_frontline_run_start"}},
            )
            self.assertEqual(status, "202 Accepted")
            self.assertEqual(payload["study"]["status"], "running")
            self.assertEqual(payload["job"]["metadata"]["plan_revision_id"], plan_revision_id)
            self.assertEqual(payload["job"]["metadata"]["frontline_plan_revision_id"], plan_revision_id)
            self.assertTrue(payload["job"]["metadata"]["hidden_execution_profile"])
            self.assertEqual(payload["job"]["metadata"]["source"], "frontline_research_studio")
            self.assertEqual(payload["job"]["metadata"]["selected_persona_ids"], selected_persona_ids)
            self.assertEqual(
                payload["job"]["metadata"]["persona_panel"]["filters"]["synthetic_user_id"],
                selected_persona_ids,
            )
            self.assertEqual(payload["research_run"]["status"], "started")
            queued_job_id = payload["job"]["job_id"]
            status, payload = call_app(
                "GET",
                f"/api/v1/studies/{study_id}/runs/{queued_job_id}/progress",
                token="token-frontline",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["run_progress"]["contract_version"], "frontline-run-progress/v1")
            self.assertEqual(payload["run_progress"]["phase"], "queued")
            self.assertEqual(payload["run_progress"]["observed_interview_contract"]["transport"], "polling_api")
            status, payload = call_app(
                "GET",
                f"/api/v1/studies/{study_id}/runs/{queued_job_id}/events",
                token="token-frontline",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["run_event_stream"]["contract_version"], "workspace-run-event-stream/v1")
            self.assertEqual(payload["run_event_stream"]["phase"], "queued")
            self.assertEqual(payload["run_event_stream"]["transport"]["current_transport"], "polling_api")
            completed_jobs = [runtime.process_next_job()]
            selected_personas_path = Path(completed_jobs[0]["output_run_path"]) / "selected_personas.json"
            selected_personas = json.loads(selected_personas_path.read_text(encoding="utf-8"))
            self.assertEqual(
                [persona["synthetic_user_id"] for persona in selected_personas],
                selected_persona_ids,
            )
            panel_snapshot_path = Path(completed_jobs[0]["output_run_path"]) / "frontline_persona_panel_snapshot.json"
            self.assertTrue(panel_snapshot_path.exists())
            panel_snapshot = json.loads(panel_snapshot_path.read_text(encoding="utf-8"))
            selected_snapshot = panel_snapshot["selected_persona_snapshot"]
            self.assertEqual(selected_snapshot["selected_persona_ids"], selected_persona_ids)
            self.assertFalse(selected_snapshot["has_provisional_personas"])
            self.assertEqual(
                sorted(selected_snapshot["selected_persona_versions"].keys()),
                sorted(selected_persona_ids),
            )
            self.assertIn(
                "profile.json",
                selected_snapshot["artifact_hashes_by_persona"][selected_persona_ids[0]],
            )
            self.assertIn("coverage_gaps", selected_snapshot["coverage_snapshot"])

            status, payload = call_app(
                "POST",
                "/api/v1/validation-jobs",
                token="token-frontline",
                payload={
                    "brief_path": str(brief_path.relative_to(workspace_root)),
                    "persona_dir": str(persona_dir.relative_to(workspace_root)),
                    "panel_spec": {"panel_type": "mainstream", "sample_size": 1, "random_seed": 23},
                    "provider_name": "mock",
                    "metadata": {
                        "project_id": project_id,
                        "study_id": study_id,
                        "frontline_requires_plan_revision": True,
                        "source": "frontline_research_studio",
                    },
                },
            )
            self.assertEqual(status, "202 Accepted")
            self.assertEqual(payload["job"]["metadata"]["plan_revision_id"], plan_revision_id)
            completed_jobs.append(runtime.process_next_job())

            run_ids = [job["metadata"]["run_id"] for job in completed_jobs]
            job_ids = [job["job_id"] for job in completed_jobs]
            self.assertEqual(len(run_ids), 2)
            status, payload = call_app("GET", f"/api/v1/studies/{study_id}", token="token-frontline")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["study"]["status"], "reviewing")
            self.assertEqual(payload["study"]["run_count"], 2)

            status, payload = call_app("GET", "/api/v1/research-playbooks", token="token-frontline")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["research_playbooks"]["contract_version"], "frontline-research-playbook-catalog/v1")
            self.assertTrue(any(item["playbook_id"] == "messaging_positioning" for item in payload["research_playbooks"]["playbooks"]))

            status, payload = call_app(
                "GET",
                f"/api/v1/studies/{study_id}/runs/{run_ids[0]}/progress",
                token="token-frontline",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["run_progress"]["phase"], "completed")
            self.assertGreaterEqual(payload["run_progress"]["participant_progress"]["completed_count"], 1)

            status, payload = call_app(
                "GET",
                f"/api/v1/studies/{study_id}/runs/{run_ids[0]}/transcript",
                token="token-frontline",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["run_transcript"]["contract_version"], "frontline-run-transcript/v1")
            self.assertGreaterEqual(payload["run_transcript"]["exchange_count"], 1)
            self.assertIn("synthetic interview transcript", payload["run_transcript"]["synthetic_boundary"])

            status, payload = call_app(
                "GET",
                f"/api/v1/studies/{study_id}/runs/{run_ids[0]}/trace",
                token="token-frontline",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["run_trace"]["contract_version"], "frontline-run-trace/v1")
            self.assertGreaterEqual(len(payload["run_trace"]["synthetic_participant_reasoning_trace"]), 1)
            self.assertEqual(payload["run_trace"]["provider_lineage"]["provider_name"], "mock")

            status, payload = call_app(
                "GET",
                f"/api/v1/studies/{study_id}/runs/{run_ids[0]}/events",
                token="token-frontline",
            )
            self.assertEqual(status, "200 OK")
            run_event_stream = payload["run_event_stream"]
            self.assertEqual(run_event_stream["contract_version"], "workspace-run-event-stream/v1")
            self.assertEqual(run_event_stream["phase"], "completed")
            self.assertEqual(run_event_stream["observed_interview_bridge"]["status"], "not_attached")
            self.assertTrue(run_event_stream["latest_safe_turn"]["source_refs"])
            self.assertIn(
                "run.synthetic_participant_turn_recorded",
                {event["event_type"] for event in run_event_stream["events"]},
            )
            self.assertIn("synthetic interview execution", run_event_stream["synthetic_boundary"])

            status, payload = call_app(
                "POST",
                f"/api/v1/studies/{study_id}/frontline-reruns",
                token="token-frontline",
                payload={
                    "source_run_id": run_ids[0],
                    "playbook_id": "messaging_positioning",
                    "change_set": {
                        "message_variant": "Rewrite the headline around concrete proof instead of broad AI promise.",
                        "guide_focus": "Compare comprehension, credibility, trust gaps, and misunderstanding separately.",
                    },
                    "metadata": {"source": "frontline_rerun_test"},
                },
            )
            self.assertEqual(status, "201 Created")
            self.assertEqual(payload["rerun_plan"]["contract_version"], "frontline-rerun-plan/v1")
            self.assertEqual(payload["rerun_plan"]["mode_inference"]["mode"], "messaging_validation")
            self.assertEqual(payload["rerun_plan"]["rerun_lineage"]["source_run_id"], run_ids[0])

            status, payload = call_app("GET", "/api/v1/calibration-observatory", token="token-frontline")
            self.assertEqual(status, "200 OK")
            observatory = payload["calibration_observatory"]
            self.assertEqual(observatory["contract_version"], "calibration-observatory/v1")
            self.assertEqual(observatory["health_summary"]["status"], "insufficient_benchmarking")
            self.assertIn("mock", observatory["segments"]["provider_counts"])

            status, payload = call_app(
                "GET",
                "/api/v1/evidence-query",
                token="token-frontline",
                query=f"job_id={job_ids[0]}&query_text=objection",
            )
            self.assertEqual(status, "200 OK")
            evidence_query = payload["query"]
            self.assertEqual(evidence_query["query_status"], "query_ready")
            self.assertEqual(evidence_query["audit_lineage"]["source_run"]["study_id"], study_id)
            self.assertEqual(evidence_query["provider_runtime_boundary"]["provider_name"], "mock")
            self.assertGreaterEqual(evidence_query["result_count"], 1)
            self.assertTrue(evidence_query["selected_result_id"])
            self.assertTrue(any(result.get("source_exchange_refs") for result in evidence_query["results"]))

            status, payload = call_app(
                "POST",
                "/api/v1/evidence-views",
                token="token-frontline",
                payload={
                    "study_id": study_id,
                    "job_id": job_ids[0],
                    "title": "Founder concept evidence view",
                    "note": "Saved from the Frontline evidence workspace.",
                    "query_text": evidence_query["query_text"],
                    "active_family": evidence_query["active_family"],
                    "sort_by": evidence_query["sort_by"],
                    "selected_result_id": evidence_query["selected_result_id"],
                    "selected_replay_step_id": evidence_query["selected_replay_step_id"] or "",
                    "selected_comparison_run_id": evidence_query["cross_run_comparison"]["selected_comparison_run_id"] or "",
                    "metadata": {"source": "frontline_research_studio"},
                },
            )
            self.assertEqual(status, "201 Created")
            evidence_view = payload["evidence_view"]
            self.assertEqual(evidence_view["job_id"], job_ids[0])
            self.assertEqual(evidence_view["run_id"], run_ids[0])
            self.assertEqual(evidence_view["selected_result_id"], evidence_query["selected_result_id"])
            self.assertTrue(evidence_view["selected_signal_id"])
            self.assertTrue(evidence_view["readiness_gate"]["boundary_required"])
            self.assertEqual(evidence_view["provider_runtime_boundary"]["provider_name"], "mock")
            self.assertTrue(evidence_view["source_exchange_refs"])
            evidence_view_id = evidence_view["evidence_view_id"]
            assert_frontline_route(
                f"/studio/studies/{study_id}/evidence-views/{evidence_view_id}",
                "evidence_view",
                {"study_id": study_id, "evidence_view_id": evidence_view_id},
            )

            status, payload = call_app("GET", f"/api/v1/evidence-views/{evidence_view_id}", token="token-frontline")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["evidence_view"]["selected_signal_id"], evidence_view["selected_signal_id"])
            self.assertEqual(payload["evidence_view"]["run_id"], run_ids[0])

            status, payload = call_app(
                "GET",
                "/api/v1/integration-events",
                token="token-frontline",
                query=f"study_id={study_id}&limit=20",
            )
            self.assertEqual(status, "200 OK")
            integration_events = payload["integration_events"]
            self.assertEqual(integration_events["contract_version"], "workspace-integration-events/v1")
            integration_event_types = {event["event_type"] for event in integration_events["events"]}
            self.assertIn("study.created", integration_event_types)
            self.assertIn("run.completed", integration_event_types)
            self.assertIn("evidence_view.saved", integration_event_types)
            self.assertIn("readiness.changed", integration_event_types)
            run_completed_event = next(event for event in integration_events["events"] if event["event_type"] == "run.completed")
            self.assertTrue(run_completed_event["payload"]["provenance"]["source_exchange_refs"])
            self.assertTrue(run_completed_event["payload"]["human_validation_required"])
            self.assertIn("privacy_export_controls", run_completed_event["payload"])

            status, payload = call_app(
                "POST",
                "/api/v1/integration-events/delivery-attempts",
                token="token-frontline",
                payload={
                    "event_id": run_completed_event["event_id"],
                    "consumer_id": "customer-review-feed",
                    "status": "failed",
                    "response_code": 503,
                    "note": "Simulated downstream retry visibility.",
                    "retry_after_seconds": 60,
                },
            )
            self.assertEqual(status, "201 Created")
            self.assertEqual(payload["delivery_attempt"]["status"], "failed")
            delivered_event = next(
                event for event in payload["integration_events"]["events"] if event["event_id"] == run_completed_event["event_id"]
            )
            self.assertEqual(delivered_event["delivery"]["status"], "failed")
            self.assertTrue(delivered_event["delivery"]["retry_visible"])

            status, payload = call_app(
                "POST",
                "/api/v1/study-reports",
                token="token-frontline",
                payload={
                    "study_id": study_id,
                    "included_run_ids": run_ids,
                    "title": "Founder concept study synthesis",
                    "metadata": {"source": "frontline_research_studio"},
                },
            )
            self.assertEqual(status, "201 Created")
            report = payload["study_report"]
            self.assertEqual(report["included_run_ids"], run_ids)
            self.assertEqual(report["included_plan_revision_ids"], [plan_revision_id])
            self.assertGreaterEqual(len(report["stable_patterns"]), 1)
            self.assertGreaterEqual(len(report["human_validation_gaps"]), 1)
            self.assertTrue(Path(report["payload_path"]).exists())
            report_id = report["study_report_id"]
            assert_frontline_route(
                f"/studio/studies/{study_id}/reports/{report_id}",
                "study_report",
                {"study_id": study_id, "study_report_id": report_id},
            )

            status, payload = call_app(
                "GET",
                "/api/v1/study-reports",
                token="token-frontline",
                query=f"study_id={study_id}",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["study_reports"][0]["study_report_id"], report_id)

            status, payload = call_app("GET", f"/api/v1/studies/{study_id}", token="token-frontline")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["study"]["status"], "completed")
            self.assertEqual(payload["study"]["latest_report_id"], report_id)

            status, payload = call_app(
                "POST",
                "/api/v1/decision-logs",
                token="token-frontline",
                payload={
                    "study_id": study_id,
                    "job_id": job_ids[0],
                    "evidence_view_id": evidence_view_id,
                    "selected_result_id": evidence_query["selected_result_id"],
                    "selected_comparison_run_id": evidence_query["cross_run_comparison"]["selected_comparison_run_id"] or "",
                    "title": "Founder concept decision",
                    "decision_summary": "Continue with guarded prototype validation.",
                    "rationale": "Synthetic evidence is directional and still requires human validation.",
                    "metadata": {
                        "study_report_id": report_id,
                        "plan_revision_id": plan_revision_id,
                        "confidence_boundary": "Directional synthetic signal only; not human market proof.",
                        "human_follow_up": "Interview real founders around the strongest trust gap before making a launch claim.",
                        "evidence_basis_label": "Saved evidence view with selected source slice and comparison context.",
                        "human_validation_gap_required": True,
                    },
                },
            )
            self.assertEqual(status, "201 Created")
            self.assertEqual(payload["decision_log"]["metadata"]["study_report_id"], report_id)
            self.assertEqual(payload["decision_log"]["metadata"]["plan_revision_id"], plan_revision_id)
            self.assertEqual(payload["decision_log"]["job_id"], job_ids[0])
            self.assertEqual(payload["decision_log"]["evidence_view_id"], evidence_view_id)
            self.assertTrue(payload["decision_log"]["has_linked_evidence_view"])
            self.assertTrue(payload["decision_log"]["selected_signal_id"])
            self.assertEqual(payload["decision_log"]["metadata"]["confidence_boundary"], "Directional synthetic signal only; not human market proof.")
            self.assertEqual(payload["decision_log"]["metadata"]["human_follow_up"], "Interview real founders around the strongest trust gap before making a launch claim.")
            decision_log_id = payload["decision_log"]["decision_log_id"]
            assert_frontline_route(
                f"/studio/studies/{study_id}/decisions/{decision_log_id}",
                "decision",
                {"study_id": study_id, "decision_log_id": decision_log_id},
            )

            status, payload = call_app(
                "GET",
                "/api/v1/integration-events",
                token="token-frontline",
                query=f"study_id={study_id}&event_type=decision.logged",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["integration_events"]["events"][0]["event_type"], "decision.logged")
            self.assertEqual(payload["integration_events"]["events"][0]["target_id"], decision_log_id)

            status, payload = call_app(
                "POST",
                "/api/v1/export-bundles",
                token="token-frontline",
                payload={
                    "study_id": study_id,
                    "job_id": job_ids[0],
                    "title": "Founder concept evidence package",
                    "export_format": "bundle_json",
                    "metadata": {
                        "source": "frontline_research_studio",
                        "decision_log_id": decision_log_id,
                        "study_report_id": report_id,
                        "evidence_view_id": evidence_view_id,
                    },
                },
            )
            self.assertEqual(status, "201 Created")
            export_bundle_id = payload["export_bundle"]["export_bundle_id"]
            self.assertEqual(payload["export_bundle"]["metadata"]["decision_log_id"], decision_log_id)
            self.assertGreaterEqual(payload["export_bundle"]["exported_file_count"], 1)

            status, payload = call_app(
                "POST",
                "/api/v1/share-bundles",
                token="token-frontline",
                payload={
                    "export_bundle_id": export_bundle_id,
                    "title": "Founder concept boundary share",
                    "expires_in_days": 14,
                    "metadata": {
                        "source": "frontline_research_studio",
                        "decision_log_id": decision_log_id,
                        "study_report_id": report_id,
                        "evidence_view_id": evidence_view_id,
                        "confidence_boundary": "Directional synthetic signal only; not human market proof.",
                        "human_follow_up": "Interview real founders around the strongest trust gap before making a launch claim.",
                    },
                },
            )
            self.assertEqual(status, "201 Created")
            share_bundle = payload["share_bundle"]
            self.assertEqual(share_bundle["export_bundle_id"], export_bundle_id)
            self.assertEqual(share_bundle["metadata"]["decision_log_id"], decision_log_id)
            self.assertEqual(share_bundle["metadata"]["study_report_id"], report_id)
            self.assertGreaterEqual(share_bundle["share_file_count"], 1)
            self.assertGreaterEqual(len(share_bundle["files"]), 1)
            self.assertIn("synthetic", share_bundle["synthetic_boundary"].lower())
            self.assertFalse(share_bundle["market_claims_allowed"])
            share_bundle_id = share_bundle["share_bundle_id"]
            assert_frontline_route(
                f"/studio/share/{share_bundle_id}",
                "share",
                {"share_bundle_id": share_bundle_id},
            )
            status, payload = call_app("GET", f"/api/v1/share-bundles/{share_bundle_id}", token="token-frontline")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["share_bundle"]["metadata"]["decision_log_id"], decision_log_id)
            self.assertGreaterEqual(len(payload["share_bundle"]["files"]), 1)

            status, payload = call_app(
                "GET",
                "/api/v1/audit-events",
                token="token-frontline",
                query="target_type=integration_event&action_prefix=integration_event.&limit=5",
            )
            self.assertEqual(status, "200 OK")
            self.assertIn(
                "integration_event.delivery_recorded",
                {event["action"] for event in payload["audit_history"]["audit_events"]},
            )

            assert_frontline_route("/studio/share", "share_collection")
            assert_frontline_route(
                "/studio/share/share_missing",
                "share",
                {"share_bundle_id": "share_missing"},
            )

    def test_api_study_governed_review_assignment_updates_high_stakes_study(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            runtime.bootstrap_workspace(
                workspace_id="ws_governed_api",
                slug="governed-api",
                display_name="Governed API",
                owner_user_id="owner_governed_api",
                api_token="token-governed-api",
                plan_tier="pro",
                billing_status="active",
            )
            workspace = job_store.get_workspace(runtime_root, "ws_governed_api")
            workspace.members.append(WorkspaceMember(user_id="reviewer_001", role="editor", joined_at=workspace.created_at))
            job_store.upsert_workspace(runtime_root, workspace)
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

            status, payload = call_app(
                "POST",
                "/api/v1/projects",
                token="token-governed-api",
                payload={"name": "Governed Program"},
            )
            self.assertEqual(status, "201 Created")
            project_id = payload["project"]["project_id"]

            status, payload = call_app(
                "POST",
                "/api/v1/studies",
                token="token-governed-api",
                payload={
                    "project_id": project_id,
                    "title": "Medical onboarding study",
                    "research_intent": "Understand clinic workflow trust and patient intake decisions.",
                    "desired_output": "health workflow risk review",
                    "first_task": "log in and review a patient record",
                    "metadata": {
                        "regulated_review_boundary": {
                            "boundary_handling_status": "acknowledged",
                            "allow_execution": True,
                            "explicit_boundary_note": "Scoped operator review approved before synthetic execution.",
                            "explicit_boundary_acknowledged_at": "2026-06-29T00:00:00+00:00",
                            "explicit_boundary_acknowledged_by_user_id": "owner_governed_api",
                        }
                    },
                },
            )
            self.assertEqual(status, "201 Created")
            study_id = payload["study"]["study_id"]
            self.assertEqual(payload["study"]["governed_review"]["review_gate_status"], "blocked_reviewer_unassigned")

            status, payload = call_app(
                "POST",
                f"/api/v1/studies/{study_id}/governed-review-assignment",
                token="token-governed-api",
                payload={
                    "assignee_user_ids": ["reviewer_001"],
                    "status": "assigned",
                    "note": "Assign the governed reviewer before decision approval.",
                },
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["study"]["governed_review"]["review_gate_status"], "assigned_for_review")
            self.assertEqual(
                payload["study"]["governed_review"]["reviewer_handoff"]["assignee_user_ids"],
                ["reviewer_001"],
            )

            status, payload = call_app(
                "POST",
                f"/api/v1/studies/{study_id}/governed-redaction",
                token="token-governed-api",
                payload={
                    "status": "active",
                    "redaction_rules": [
                        {
                            "path": "study_context.research_intent",
                            "reason": "Protect sensitive clinic workflow detail.",
                            "replacement": "[REDACTED: research intent]",
                        }
                    ],
                    "note": "Activate governed redaction before external circulation.",
                },
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["study"]["governed_redaction"]["status"], "active")
            self.assertEqual(payload["study"]["governed_redaction"]["rule_count"], 1)

            status, payload = call_app(
                "GET",
                f"/api/v1/studies/{study_id}/activity",
                token="token-governed-api",
                query="limit=10",
            )
            self.assertEqual(status, "200 OK")
            actions = [event["action"] for event in payload["study_activity"]["activity_events"]]
            self.assertIn("study.governed_review_assignment_updated", actions)
            self.assertIn("study.governed_redaction_updated", actions)

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
            self.assertEqual(payload["study"]["regulated_review_boundary"]["classification_status"], "standard")

            status, payload = call_app(
                "GET",
                "/api/v1/support-diagnostics",
                token="token-api",
                query=f"study_id={study_id}",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["support"]["selected_study_id"], study_id)
            self.assertEqual(payload["support"]["study_boundary"]["classification_status"], "standard")

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
            self.assertEqual(payload["study"]["regulated_review_boundary"]["execution_status"], "allowed")

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
            trace_result_id = payload["query"]["selected_result_id"]

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

            revision_study = runtime.create_workspace_study(
                runtime.authenticate("token-api"),
                project_id=project_id,
                title="Inbox Coach v2 revision",
                research_intent="Compare whether trust hesitation changes after the onboarding revision.",
            )
            revision_study_id = revision_study["study_id"]
            revision_job = runtime.submit_validation_job(
                runtime.authenticate("token-api"),
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=29),
                    provider_name="mock",
                    metadata={"project_id": project_id, "study_id": revision_study_id},
                ),
            )
            runtime.process_next_job()
            revision_job_status = runtime.get_validation_job(runtime.authenticate("token-api"), revision_job["job_id"])
            revision_run_id = revision_job_status["metadata"]["run_id"]
            self.assertNotEqual(revision_run_id, run_id)
            self.assertNotEqual(revision_run_id, comparison_run_id)

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
            self.assertEqual(payload["query"]["cross_run_comparison"]["comparison_run_count"], 2)
            self.assertEqual(
                payload["query"]["cross_run_comparison"]["selected_comparison_run_id"],
                comparison_run_id,
            )
            self.assertEqual(
                payload["query"]["cross_run_comparison"]["selected_comparison_job_id"],
                comparison_job["job_id"],
            )
            self.assertIn(
                comparison_job["job_id"],
                [item["job_id"] for item in payload["query"]["cross_run_comparison"]["candidate_runs"]],
            )
            self.assertIn(
                revision_job["job_id"],
                [item["job_id"] for item in payload["query"]["cross_run_comparison"]["candidate_runs"]],
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
            candidate_job_study_ids = [
                item["study_id"] for item in payload["query"]["audit_lineage"]["comparison_set"]["candidate_jobs"]
            ]
            self.assertIn(study_id, candidate_job_study_ids)
            self.assertIn(revision_study_id, candidate_job_study_ids)
            longitudinal = payload["query"]["longitudinal_comparison"]
            self.assertEqual(longitudinal["contract_version"], "workspace-longitudinal-comparison/v0-draft")
            self.assertEqual(longitudinal["source_run_id"], run_id)
            self.assertEqual(longitudinal["source_study_id"], study_id)
            self.assertEqual(longitudinal["source_project_id"], project_id)
            self.assertEqual(longitudinal["selected_window_id"], "same_study_runs")
            self.assertEqual(longitudinal["same_study_run_count"], 1)
            self.assertEqual(longitudinal["same_study_runs"][0]["run_id"], comparison_run_id)
            self.assertEqual(longitudinal["same_project_study_count"], 1)
            self.assertEqual(longitudinal["same_project_studies"][0]["study_id"], revision_study_id)
            self.assertEqual(longitudinal["same_project_studies"][0]["latest_run_id"], revision_run_id)
            panel_learning = longitudinal["panel_learning_projection"]
            self.assertEqual(panel_learning["contract_version"], "workspace-longitudinal-panel-learning/v0-draft")
            self.assertEqual(panel_learning["source_panel"]["run_id"], run_id)
            self.assertEqual(panel_learning["source_panel"]["selected_persona_count"], 1)
            self.assertEqual(len(panel_learning["related_panels"]), 2)
            self.assertEqual(panel_learning["decision_trends"]["total_decision_count"], 0)
            self.assertEqual(panel_learning["decision_trends"]["latest_change_status"], "no_decision")
            recurring = longitudinal["recurring_signal_synthesis"]
            self.assertEqual(recurring["contract_version"], "workspace-longitudinal-recurring-signals/v0-draft")
            self.assertGreaterEqual(recurring["pattern_count"], 1)
            self.assertEqual(len(recurring["run_observations"]), 3)
            objection_pattern = next(
                item for item in recurring["patterns"] if item["pattern_id"] == "objection"
            )
            self.assertEqual(objection_pattern["status"], "persistent")
            self.assertTrue(objection_pattern["source_run_present"])
            self.assertGreaterEqual(objection_pattern["run_count"], 2)
            self.assertIn(comparison_run_id, objection_pattern["related_run_ids"])
            self.assertIn(revision_run_id, objection_pattern["related_run_ids"])
            self.assertEqual(
                payload["query"]["audit_lineage"]["longitudinal_set"]["same_study_run_ids"],
                [comparison_run_id],
            )
            self.assertEqual(
                payload["query"]["audit_lineage"]["longitudinal_set"]["same_project_study_ids"],
                [revision_study_id],
            )
            self.assertIn(
                "objection",
                payload["query"]["audit_lineage"]["longitudinal_set"]["recurring_pattern_ids"],
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
                    "selected_result_id": trace_result_id,
                    "selected_comparison_run_id": comparison_run_id,
                },
            )
            self.assertEqual(status, "201 Created")
            evidence_view_id = payload["evidence_view"]["evidence_view_id"]
            self.assertEqual(payload["evidence_view"]["study_id"], study_id)
            self.assertEqual(payload["evidence_view"]["job_id"], job_id)
            self.assertEqual(payload["evidence_view"]["selected_result_id"], trace_result_id)
            self.assertEqual(payload["evidence_view"]["selected_comparison_run_id"], comparison_run_id)
            self.assertTrue(payload["evidence_view"]["has_comparison_focus"])
            self.assertEqual(payload["evidence_view"]["provider_runtime_boundary"]["provider_name"], "mock")
            self.assertEqual(payload["evidence_view"]["provider_runtime_boundary"]["evidence_mode"], "mock_demo")
            self.assertEqual(payload["evidence_view"]["longitudinal_focus"]["selected_window_id"], "same_study_runs")
            self.assertEqual(payload["evidence_view"]["longitudinal_focus"]["same_study_run_count"], 1)
            self.assertEqual(payload["evidence_view"]["longitudinal_focus"]["same_project_study_count"], 1)
            self.assertGreaterEqual(payload["evidence_view"]["recurring_signal_focus"]["pattern_count"], 1)
            self.assertGreaterEqual(len(payload["evidence_view"]["recurring_signal_focus"]["pattern_ids"]), 1)
            self.assertIn(
                payload["evidence_view"]["panel_learning_focus"]["segment_status"],
                {"insufficient_axis_data", "stable", "diverging"},
            )
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
                    "selected_result_id": trace_result_id,
                    "selected_comparison_run_id": comparison_run_id,
                },
            )
            self.assertEqual(status, "201 Created")
            decision_log_id = payload["decision_log"]["decision_log_id"]
            self.assertEqual(payload["decision_log"]["study_id"], study_id)
            self.assertEqual(payload["decision_log"]["evidence_view_id"], evidence_view_id)
            self.assertTrue(payload["decision_log"]["has_linked_evidence_view"])
            self.assertTrue(payload["decision_log"]["has_comparison_focus"])
            self.assertEqual(payload["decision_log"]["provider_runtime_boundary"]["provider_name"], "mock")
            self.assertEqual(payload["decision_log"]["provider_runtime_boundary"]["evidence_mode"], "mock_demo")
            self.assertEqual(payload["decision_log"]["longitudinal_focus"]["selected_window_id"], "same_study_runs")
            self.assertEqual(payload["decision_log"]["longitudinal_focus"]["study_timeline_entry_count"], 4)
            self.assertGreaterEqual(payload["decision_log"]["recurring_signal_focus"]["pattern_count"], 1)
            self.assertGreaterEqual(len(payload["decision_log"]["recurring_signal_focus"]["pattern_ids"]), 1)
            self.assertEqual(payload["decision_log"]["panel_learning_focus"]["total_decision_count"], 1)
            self.assertEqual(payload["decision_log"]["panel_learning_focus"]["latest_decision_change_status"], "first_decision")
            decision_log_path = Path(payload["decision_log"]["payload_path"])
            self.assertTrue(decision_log_path.exists())
            self.assertTrue((decision_log_path.parent / "README.md").exists())

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
            timeline_entries = payload["query"]["longitudinal_comparison"]["study_timeline"]
            entry_types = [item["entry_type"] for item in timeline_entries]
            self.assertIn("evidence_view", entry_types)
            self.assertIn("decision_log", entry_types)
            self.assertGreaterEqual(payload["query"]["longitudinal_comparison"]["study_timeline_entry_count"], 4)
            panel_learning = payload["query"]["longitudinal_comparison"]["panel_learning_projection"]
            self.assertEqual(panel_learning["decision_trends"]["total_decision_count"], 1)
            self.assertEqual(panel_learning["decision_trends"]["evidence_backed_decision_count"], 1)
            self.assertEqual(panel_learning["decision_trends"]["assumption_led_decision_count"], 0)
            self.assertEqual(panel_learning["decision_trends"]["latest_change_status"], "first_decision")
            timeline_pattern_entry_ids = {
                entry_id
                for pattern in payload["query"]["longitudinal_comparison"]["recurring_signal_synthesis"]["patterns"]
                for entry_id in pattern["timeline_entry_ids"]
            }
            self.assertIn(evidence_view_id, timeline_pattern_entry_ids)
            self.assertIn(decision_log_id, timeline_pattern_entry_ids)

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
            self.assertEqual(
                payload["query"]["longitudinal_comparison"]["panel_learning_projection"]["decision_trends"]["latest_review_status"],
                "approved",
            )

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
            self.assertEqual(payload["query"]["readiness_gate"]["status"], "pending")

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
            self.assertEqual(payload["export_bundle"]["readiness_gate"]["status"], "human_validation_required")
            self.assertEqual(payload["export_bundle"]["readiness_gate"]["provider_evidence_mode"], "mock_demo")
            self.assertEqual(payload["export_bundle"]["provider_runtime_boundary"]["provider_name"], "mock")
            self.assertEqual(payload["export_bundle"]["provider_runtime_boundary"]["evidence_mode"], "mock_demo")
            self.assertFalse(payload["export_bundle"]["market_claims_allowed"])
            self.assertEqual(payload["export_bundle"]["mvp_launch_scope"]["status"], "internal_only")
            self.assertEqual(payload["export_bundle"]["mvp_promotion"]["status"], "not_applicable")
            bundle_root = Path(payload["export_bundle"]["bundle_root"])
            self.assertTrue((bundle_root / "report.csv").exists())
            self.assertTrue((bundle_root / "README.md").exists())
            self.assertTrue((bundle_root / "export_manifest.json").exists())
            export_manifest = json.loads((bundle_root / "export_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(export_manifest["provider_runtime_boundary"]["evidence_mode"], "mock_demo")
            self.assertEqual(export_manifest["job_context"]["provider_runtime_boundary"]["provider_name"], "mock")

            status, payload = call_app("GET", "/api/v1/export-bundles", token="token-api", query=f"study_id={study_id}")
            self.assertEqual(status, "200 OK")
            self.assertEqual(len(payload["export_bundles"]), 1)
            self.assertEqual(payload["export_bundles"][0]["export_bundle_id"], export_bundle_id)

            status, payload = call_app("GET", f"/api/v1/export-bundles/{export_bundle_id}", token="token-api")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["export_bundle"]["export_bundle_id"], export_bundle_id)
            self.assertEqual(payload["export_bundle"]["manifest_path"], str(bundle_root / "export_manifest.json"))
            self.assertEqual(payload["export_bundle"]["readiness_gate"]["status"], "human_validation_required")
            self.assertEqual(payload["export_bundle"]["mvp_promotion"]["status"], "not_applicable")

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
            self.assertEqual(payload["share_bundle"]["readiness_gate"]["status"], "human_validation_required")
            self.assertEqual(payload["share_bundle"]["readiness_gate"]["provider_evidence_mode"], "mock_demo")
            self.assertEqual(payload["share_bundle"]["provider_runtime_boundary"]["provider_name"], "mock")
            self.assertEqual(payload["share_bundle"]["provider_runtime_boundary"]["evidence_mode"], "mock_demo")
            self.assertFalse(payload["share_bundle"]["market_claims_allowed"])
            self.assertEqual(payload["share_bundle"]["mvp_launch_scope"]["status"], "internal_only")
            self.assertEqual(payload["share_bundle"]["mvp_promotion"]["status"], "not_applicable")
            self.assertEqual(payload["share_bundle"]["partner_onboarding"]["status"], "not_applicable")
            self.assertEqual(payload["share_bundle"]["mvp_release_review"]["status"], "not_applicable")
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
            self.assertEqual(payload["share_bundle"]["readiness_gate"]["status"], "human_validation_required")
            self.assertEqual(payload["share_bundle"]["readiness_gate"]["provider_evidence_mode"], "mock_demo")
            self.assertEqual(payload["share_bundle"]["provider_runtime_boundary"]["evidence_mode"], "mock_demo")
            self.assertEqual(payload["share_bundle"]["mvp_launch_scope"]["status"], "internal_only")
            self.assertEqual(payload["share_bundle"]["mvp_promotion"]["status"], "not_applicable")
            self.assertEqual(payload["share_bundle"]["partner_onboarding"]["status"], "not_applicable")
            self.assertEqual(payload["share_bundle"]["mvp_release_review"]["status"], "not_applicable")

            status, payload = call_app("GET", f"/public/v1/share-bundles/{share_key}")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["share_bundle"]["share_bundle_id"], share_bundle_id)
            self.assertEqual(payload["share_bundle"]["status"], "published")
            self.assertEqual(payload["share_bundle"]["source"]["export_bundle_id"], export_bundle_id)
            self.assertEqual(len(payload["share_bundle"]["files"]), 1)
            self.assertIn("synthetic", payload["share_bundle"]["synthetic_boundary"].lower())
            self.assertEqual(payload["share_bundle"]["readiness_gate"]["status"], "human_validation_required")
            self.assertEqual(payload["share_bundle"]["provider_runtime_boundary"]["evidence_mode"], "mock_demo")
            self.assertEqual(payload["share_bundle"]["source"]["provider_runtime_boundary"]["provider_name"], "mock")
            self.assertFalse(payload["share_bundle"]["readiness_gate"]["market_claims_allowed"])
            self.assertEqual(payload["share_bundle"]["mvp_launch_scope"]["status"], "internal_only")
            self.assertEqual(payload["share_bundle"]["mvp_promotion"]["status"], "not_applicable")
            self.assertEqual(payload["share_bundle"]["partner_onboarding"]["status"], "not_applicable")
            self.assertEqual(payload["share_bundle"]["mvp_release_review"]["status"], "not_applicable")

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

    def test_api_operations_endpoints_and_deployment_profile_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            runtime.bootstrap_workspace(
                workspace_id="ws_ops_profile",
                slug="ops-profile",
                display_name="Ops Profile",
                owner_user_id="owner_ops_profile",
                api_token="token-ops-profile",
                plan_tier="pro",
                billing_status="active",
            )

            def call_app(
                app: SaasApiApplication,
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
                app: SaasApiApplication,
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

            local_app = SaasApiApplication(runtime)
            status, payload = call_app(local_app, "GET", "/api/v1/health")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["status"], "healthy")
            self.assertEqual(payload["runtime"]["workspace_count"], 1)

            status, payload = call_app(local_app, "GET", "/api/v1/ready")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["status"], "ready")
            self.assertEqual(payload["deployment_env"], "local")

            status, payload = call_app(local_app, "GET", "/api/v1/service-metadata")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["typed_contracts"]["workspace_shell"], "/api/v1/workspace-shell")
            self.assertTrue(payload["auth"]["hosted_route_query_token_bootstrap"])
            self.assertEqual(payload["operations"]["contract_manifest_endpoint"], "/api/v1/contract-manifest")
            self.assertEqual(payload["operations"]["workspace_operations_summary_endpoint"], "/api/v1/operations/summary")
            self.assertEqual(payload["operations"]["workspace_public_launch_readiness_endpoint"], "/api/v1/public-launch-readiness")

            status, payload = call_app(local_app, "GET", "/api/v1/contract-manifest")
            self.assertEqual(status, "200 OK")
            endpoint_ids = {endpoint["id"] for endpoint in payload["endpoints"]}
            self.assertIn("workspace_operations_summary", endpoint_ids)
            self.assertIn("workspace_public_launch_readiness", endpoint_ids)
            self.assertIn("evidence_query", endpoint_ids)

            status, headers, body = call_app_raw(local_app, "OPTIONS", "/api/v1/health")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")
            header_map = {name: value for name, value in headers}
            self.assertEqual(header_map["Access-Control-Allow-Origin"], "*")

            status, headers, body = call_app_raw(local_app, "OPTIONS", "/api/v1/contract-manifest")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            status, headers, body = call_app_raw(local_app, "OPTIONS", "/api/v1/public-launch-readiness")
            self.assertEqual(status, "204 No Content")
            self.assertEqual(body, b"")

            insecure_production_app = SaasApiApplication(
                runtime,
                deployment_profile=SaasApiDeploymentProfile(deployment_env="production"),
            )
            status, payload = call_app(insecure_production_app, "GET", "/api/v1/ready")
            self.assertEqual(status, "503 Service Unavailable")
            self.assertEqual(payload["status"], "not_ready")
            failed_checks = {check["name"] for check in payload["checks"] if check["status"] == "fail"}
            self.assertIn("public_base_url", failed_checks)
            self.assertIn("secret_source", failed_checks)
            self.assertIn("query_token_bootstrap_policy", failed_checks)

            hardened_production_app = SaasApiApplication(
                runtime,
                deployment_profile=SaasApiDeploymentProfile(
                    deployment_env="production",
                    public_base_url="https://synthetic-users.example.test",
                    secret_source="env_managed",
                    expected_backup_mode="daily_snapshot",
                    allow_query_token_bootstrap=False,
                ),
            )
            status, payload = call_app(hardened_production_app, "GET", "/api/v1/ready")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["status"], "ready")

            status, payload = call_app(
                hardened_production_app,
                "GET",
                "/app/workspace",
                query="token=token-ops-profile",
            )
            self.assertEqual(status, "403 Forbidden")
            self.assertEqual(payload["error"], "forbidden")
            self.assertIn("disabled", payload["message"])

    def test_api_workspace_operations_summary_observes_worker_evidence_decision_distribution_and_audit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_ops_summary",
                slug="ops-summary",
                display_name="Ops Summary",
                owner_user_id="owner_ops_summary",
                api_token="token-ops-summary",
                plan_tier="pro",
                billing_status="active",
                settings={"daily_runs": 5, "max_concurrent_jobs": 2},
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)
            auth = runtime.authenticate("token-ops-summary")
            project = runtime.create_workspace_project(auth, name="Operations Summary Project")
            study = runtime.create_workspace_study(
                auth,
                project_id=project["project_id"],
                title="Operations Summary Study",
                research_intent="Verify production observability coverage across the study lifecycle.",
            )
            job = runtime.submit_validation_job(
                auth,
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    provider_name="mock",
                    metadata={"project_id": project["project_id"], "study_id": study["study_id"]},
                ),
            )
            completed = runtime.process_next_job()
            query = runtime.query_workspace_evidence(auth, job_id=job["job_id"])
            selected_result_id = str(query["results"][0]["id"])
            evidence_view = runtime.create_workspace_evidence_view(
                auth,
                study_id=study["study_id"],
                job_id=job["job_id"],
                title="Ops evidence view",
                query_text="hesitate",
                selected_result_id=selected_result_id,
            )
            decision_log = runtime.create_workspace_decision_log(
                auth,
                study_id=study["study_id"],
                title="Ops decision",
                decision_summary="Hold current positioning until hesitation evidence is reviewed.",
                evidence_view_id=evidence_view["evidence_view_id"],
                job_id=job["job_id"],
                selected_result_id=selected_result_id,
            )
            runtime.update_workspace_decision_review_status(
                auth,
                decision_log_id=decision_log["decision_log_id"],
                review_status="approved",
                note="Operational review complete.",
            )
            runtime.create_workspace_export_bundle(
                auth,
                study_id=study["study_id"],
                job_id=job["job_id"],
                title="Ops export",
                export_format="bundle_json",
            )
            runtime.create_workspace_support_snapshot(
                auth,
                job_id=job["job_id"],
                title="Ops support snapshot",
                notes="Diagnostic snapshot for observability verification.",
            )
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

            status, payload = call_app("GET", "/api/v1/operations/summary")
            self.assertEqual(status, "401 Unauthorized")
            self.assertEqual(payload["error"], "unauthorized")

            status, payload = call_app("GET", "/api/v1/operations/summary", token="token-ops-summary")
            self.assertEqual(status, "200 OK")
            operations = payload["operations"]
            self.assertEqual(operations["contract_version"], "workspace-operations-summary/v0-draft")
            self.assertEqual(operations["worker_runtime"]["job_counts"]["completed"], 1)
            self.assertEqual(operations["evidence_review"]["evidence_view_count"], 1)
            self.assertGreaterEqual(operations["evidence_review"]["review_status_counts"]["reliability_ready"], 1)
            self.assertEqual(operations["decision_review"]["decision_log_count"], 1)
            self.assertEqual(operations["decision_review"]["review_status_counts"]["approved"], 1)
            self.assertEqual(operations["distribution"]["export_bundle_count"], 1)
            self.assertEqual(operations["support"]["support_snapshot_count"], 1)
            self.assertGreaterEqual(operations["audit"]["recent_event_count"], 5)
            self.assertIn("validation_job.completed", operations["audit"]["action_counts"])
            self.assertEqual(operations["public_launch_readiness"]["overall_status"], "research_preview_only")
            self.assertEqual(
                operations["public_launch_readiness"]["customer_operations_support_boundary"]["status"],
                "bounded_operator_ready",
            )
            self.assertIn(
                "scoped_external_readiness_not_yet_reached",
                operations["public_launch_readiness"]["customer_claim_boundary"]["blocked_reasons"],
            )
            self.assertEqual(completed["status"], "completed")

            status, payload = call_app("GET", "/api/v1/public-launch-readiness")
            self.assertEqual(status, "401 Unauthorized")

            status, payload = call_app("GET", "/api/v1/public-launch-readiness", token="token-ops-summary")
            self.assertEqual(status, "200 OK")
            launch_readiness = payload["launch_readiness"]
            self.assertEqual(launch_readiness["contract_version"], "workspace-public-launch-readiness/v0-draft")
            self.assertEqual(launch_readiness["overall_status"], "research_preview_only")
            self.assertFalse(launch_readiness["self_serve_public_launch_allowed"])
            self.assertEqual(launch_readiness["study_governance"]["study_count"], 1)
            self.assertEqual(launch_readiness["benchmark_disclosure"]["completed_job_count"], 1)
            self.assertEqual(launch_readiness["customer_operations_support_boundary"]["support_playbook"]["status"], "bounded_ready")
            self.assertEqual(launch_readiness["customer_operations_support_boundary"]["support_playbook"]["support_snapshot_count"], 1)
            self.assertEqual(
                launch_readiness["self_serve_onboarding_pricing_boundary"]["status"],
                "bounded_self_serve_ready",
            )
            self.assertEqual(
                launch_readiness["self_serve_onboarding_pricing_boundary"]["quota_boundary"]["status"],
                "ordinary_team_ready",
            )
            self.assertIn(
                "replacement_grade_claims_not_allowed",
                launch_readiness["customer_claim_boundary"]["blocked_reasons"],
            )
            self.assertIn(
                "replacement_grade_claims_not_allowed",
                launch_readiness["launch_blockers"],
            )

    def test_public_launch_readiness_exposes_support_boundary_blockers(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_launch_support",
                slug="launch-support",
                display_name="Launch Support",
                owner_user_id="owner_launch_support",
                api_token="token-launch-support",
                plan_tier="pro",
                billing_status="active",
                settings={"daily_runs": 5, "max_concurrent_jobs": 2},
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)
            auth = runtime.authenticate("token-launch-support")
            runtime.upsert_workspace_member(auth, user_id="reviewer_001", role="editor")
            project = runtime.create_workspace_project(auth, name="Launch Support Project")
            study = runtime.create_workspace_study(
                auth,
                project_id=project["project_id"],
                title="Launch Support Study",
                research_intent="Verify customer operations and support launch blockers.",
            )
            failed_job = runtime.submit_validation_job(
                auth,
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=13),
                    provider_name="unknown-provider",
                    metadata={"project_id": project["project_id"], "study_id": study["study_id"]},
                ),
            )
            runtime.process_next_job()

            launch_readiness = runtime.describe_workspace_public_launch_readiness(auth)
            self.assertEqual(
                launch_readiness["customer_operations_support_boundary"]["status"],
                "manual_operator_review_required",
            )
            self.assertIn(
                "failed_jobs_missing_support_snapshot",
                launch_readiness["customer_operations_support_boundary"]["blocked_reasons"],
            )
            self.assertEqual(
                launch_readiness["customer_operations_support_boundary"]["support_playbook"]["status"],
                "not_exercised",
            )
            self.assertEqual(
                launch_readiness["customer_operations_support_boundary"]["support_playbook"]["failed_job_count"],
                1,
            )

            snapshot = runtime.create_workspace_support_snapshot(
                auth,
                job_id=failed_job["job_id"],
                title="Failed job handoff",
                notes="Launch support needs explicit handoff coverage.",
            )
            runtime.update_workspace_support_snapshot_handoff(
                auth,
                support_snapshot_id=snapshot["support_snapshot_id"],
                status="assigned",
                assigned_user_id="reviewer_001",
                note="Investigate provider configuration before retry.",
            )

            refreshed_launch_readiness = runtime.describe_workspace_public_launch_readiness(auth)
            boundary = refreshed_launch_readiness["customer_operations_support_boundary"]
            self.assertEqual(boundary["status"], "manual_operator_review_required")
            self.assertNotIn("failed_jobs_missing_support_snapshot", boundary["blocked_reasons"])
            self.assertIn("support_handoffs_unresolved", boundary["blocked_reasons"])
            self.assertEqual(boundary["support_playbook"]["status"], "active_handoffs")
            self.assertEqual(boundary["support_playbook"]["support_snapshot_count"], 1)
            self.assertEqual(boundary["support_playbook"]["open_handoff_count"], 1)

    def test_public_launch_readiness_exposes_self_serve_onboarding_and_pricing_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            runtime.bootstrap_workspace(
                workspace_id="ws_self_serve_boundary",
                slug="self-serve-boundary",
                display_name="Self Serve Boundary",
                owner_user_id="owner_self_serve",
                api_token="token-self-serve",
                plan_tier="trial",
                billing_status="trialing",
                settings={"daily_runs": 3, "max_concurrent_jobs": 1, "artifact_retention_days": 7},
            )
            auth = runtime.authenticate("token-self-serve")

            launch_readiness = runtime.describe_workspace_public_launch_readiness(auth)
            boundary = launch_readiness["self_serve_onboarding_pricing_boundary"]
            self.assertEqual(boundary["contract_version"], "workspace-self-serve-launch-boundary/v0-draft")
            self.assertEqual(boundary["status"], "self_serve_setup_required")
            self.assertEqual(boundary["onboarding_boundary"]["status"], "ready")
            self.assertEqual(boundary["pricing_boundary"]["status"], "billing_action_required")
            self.assertEqual(boundary["quota_boundary"]["status"], "insufficient_for_ordinary_team")
            self.assertIn("trial_plan_not_self_serve_launch_ready", boundary["blocked_reasons"])
            self.assertIn("active_billing_required_for_self_serve", boundary["blocked_reasons"])
            self.assertIn("retention_window_too_short_for_customer_review", boundary["blocked_reasons"])
            self.assertIn("trial_plan_not_self_serve_launch_ready", launch_readiness["launch_blockers"])

            runtime.update_workspace_billing(
                auth,
                plan_tier="pro",
                billing_status="active",
                seat_count=3,
                renewal_at="2026-07-31T00:00:00+00:00",
                daily_runs=25,
                max_concurrent_jobs=3,
                artifact_retention_days=30,
                note="Move workspace into bounded self-serve launch posture.",
            )

            refreshed_launch_readiness = runtime.describe_workspace_public_launch_readiness(auth)
            refreshed_boundary = refreshed_launch_readiness["self_serve_onboarding_pricing_boundary"]
            self.assertEqual(refreshed_boundary["status"], "bounded_self_serve_ready")
            self.assertEqual(refreshed_boundary["pricing_boundary"]["status"], "active_paid_plan")
            self.assertEqual(refreshed_boundary["quota_boundary"]["status"], "ordinary_team_ready")
            self.assertEqual(refreshed_boundary["blocked_reasons"], [])
            self.assertNotIn("trial_plan_not_self_serve_launch_ready", refreshed_launch_readiness["launch_blockers"])

    def test_api_decision_review_assignment_and_support_handoff_enforce_team_governance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_team_governance",
                slug="team-governance",
                display_name="Team Governance",
                owner_user_id="owner_team_governance",
                api_token="token-team-governance-owner",
                plan_tier="pro",
                billing_status="active",
                settings={"daily_runs": 10, "max_concurrent_jobs": 2},
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)
            owner_auth = runtime.authenticate("token-team-governance-owner")
            runtime.upsert_workspace_member(owner_auth, user_id="reviewer_001", role="editor")
            reviewer_token = runtime.issue_workspace_api_token(owner_auth, user_id="reviewer_001")["token"]
            project = runtime.create_workspace_project(owner_auth, name="Team Governance Project")
            study = runtime.create_workspace_study(
                owner_auth,
                project_id=project["project_id"],
                title="Team governance study",
                research_intent="Verify reviewer assignment and support handoff governance.",
            )
            job = runtime.submit_validation_job(
                owner_auth,
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    provider_name="mock",
                    metadata={"project_id": project["project_id"], "study_id": study["study_id"]},
                ),
            )
            runtime.process_next_job()
            query = runtime.query_workspace_evidence(owner_auth, job_id=job["job_id"])
            selected_result_id = str(query["results"][0]["id"])
            evidence_view = runtime.create_workspace_evidence_view(
                owner_auth,
                study_id=study["study_id"],
                job_id=job["job_id"],
                title="Governance evidence view",
                query_text="hesitate",
                selected_result_id=selected_result_id,
            )
            decision_log = runtime.create_workspace_decision_log(
                owner_auth,
                study_id=study["study_id"],
                title="Governance decision",
                decision_summary="Do not ship until review assignment is explicit.",
                rationale="The team needs a named reviewer before approval.",
                evidence_view_id=evidence_view["evidence_view_id"],
                job_id=job["job_id"],
                selected_result_id=selected_result_id,
            )
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

            status, payload = call_app("GET", f"/api/v1/decision-logs/{decision_log['decision_log_id']}", token="token-team-governance-owner")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["decision_log"]["review_assignment"]["status"], "unassigned")

            status, payload = call_app(
                "POST",
                f"/api/v1/decision-logs/{decision_log['decision_log_id']}/review-status",
                token=reviewer_token,
                payload={"review_status": "approved", "note": "Approving without assignment should fail."},
            )
            self.assertEqual(status, "403 Forbidden")
            self.assertEqual(payload["error"], "forbidden")

            status, payload = call_app(
                "POST",
                f"/api/v1/decision-logs/{decision_log['decision_log_id']}/review-assignment",
                token="token-team-governance-owner",
                payload={"assignee_user_ids": ["reviewer_001"], "note": "Please take the first decision review pass."},
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["decision_log"]["review_assignment"]["status"], "assigned")
            self.assertEqual(payload["decision_log"]["review_assignment"]["assignee_user_ids"], ["reviewer_001"])
            self.assertEqual(len(payload["decision_log"]["review_assignment_history"]), 1)

            status, payload = call_app(
                "POST",
                f"/api/v1/decision-logs/{decision_log['decision_log_id']}/review-status",
                token=reviewer_token,
                payload={"review_status": "approved", "note": "Assigned reviewer approval is now allowed."},
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["decision_log"]["review_status"], "approved")

            failed_job = runtime.submit_validation_job(
                owner_auth,
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=19),
                    provider_name="unknown-provider",
                    metadata={"project_id": project["project_id"], "study_id": study["study_id"]},
                ),
            )
            runtime.process_next_job()
            support_snapshot = runtime.create_workspace_support_snapshot(
                owner_auth,
                job_id=failed_job["job_id"],
                title="Provider failure handoff",
                notes="Route the provider failure to the named reviewer.",
            )

            status, payload = call_app(
                "POST",
                f"/api/v1/support-snapshots/{support_snapshot['support_snapshot_id']}/handoff",
                token=reviewer_token,
                payload={"status": "acknowledged", "note": "Cannot acknowledge before assignment."},
            )
            self.assertEqual(status, "400 Bad Request")
            self.assertEqual(payload["error"], "bad_request")

            status, payload = call_app(
                "POST",
                f"/api/v1/support-snapshots/{support_snapshot['support_snapshot_id']}/handoff",
                token="token-team-governance-owner",
                payload={
                    "status": "assigned",
                    "assigned_user_id": "reviewer_001",
                    "note": "Please triage the failed provider configuration.",
                },
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["support_snapshot"]["handoff"]["status"], "assigned")
            self.assertEqual(payload["support_snapshot"]["handoff"]["assigned_user_id"], "reviewer_001")

            status, payload = call_app(
                "POST",
                f"/api/v1/support-snapshots/{support_snapshot['support_snapshot_id']}/handoff",
                token=reviewer_token,
                payload={"status": "acknowledged", "note": "Taking first-pass support ownership."},
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["support_snapshot"]["handoff"]["status"], "acknowledged")

            status, payload = call_app(
                "POST",
                f"/api/v1/support-snapshots/{support_snapshot['support_snapshot_id']}/handoff",
                token=reviewer_token,
                payload={"status": "resolved", "note": "Updated provider configuration and resolved the handoff."},
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["support_snapshot"]["handoff"]["status"], "resolved")
            self.assertEqual(len(payload["support_snapshot"]["handoff_history"]), 3)

            status, payload = call_app(
                "GET",
                f"/api/v1/support-snapshots/{support_snapshot['support_snapshot_id']}",
                token="token-team-governance-owner",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["support_snapshot"]["handoff"]["status"], "resolved")
            self.assertEqual(payload["support_snapshot"]["handoff"]["assigned_user_id"], "reviewer_001")

            status, payload = call_app(
                "GET",
                f"/api/v1/studies/{study['study_id']}/activity",
                token="token-team-governance-owner",
                query="limit=30",
            )
            self.assertEqual(status, "200 OK")
            actions = [event["action"] for event in payload["study_activity"]["activity_events"]]
            self.assertIn("decision_log.review_assignment_updated", actions)
            self.assertIn("support_snapshot.handoff_updated", actions)

    def test_api_export_bundle_mvp_promotion_request_review_and_share_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_mvp_api",
                slug="mvp-api",
                display_name="MVP API",
                owner_user_id="owner_mvp_api",
                api_token="token-mvp-api",
                plan_tier="pro",
                billing_status="active",
                settings={"daily_runs": 5, "max_concurrent_jobs": 2},
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)
            auth = runtime.authenticate("token-mvp-api")
            project = runtime.create_workspace_project(auth, name="Design Partner Program")
            study = runtime.create_workspace_study(
                auth,
                project_id=project["project_id"],
                title="Controlled MVP study",
                research_intent="Verify design-partner promotion approval before public circulation.",
            )
            job = runtime.submit_validation_job(
                auth,
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    provider_name="mock",
                    metadata={"project_id": project["project_id"], "study_id": study["study_id"]},
                ),
            )
            completed = runtime.process_next_job()
            run_dir = Path(str(completed["output_run_path"]))
            write_json(
                run_dir / "human_calibration.json",
                {
                    "contract_version": "human-calibration/v1",
                    "benchmark_id": "benchmark_mvp_api_001",
                    "prediction_accuracy": {
                        "alignment_score": 92.0,
                        "precision": 0.9,
                        "recall": 0.91,
                    },
                    "human_benchmark": {
                        "source_type": "real_human_study",
                    },
                    "replacement_readiness": {
                        "status": "candidate_replacement_ready",
                        "high_stakes_gate": False,
                        "boundary": "Human outcome data is attached; replacement readiness remains scoped to this stage and evidence type.",
                    },
                    "readiness_projection": {
                        "status": "candidate_scope_ready",
                        "gate_reasons": [],
                        "threshold_gaps": [],
                        "coverage": {
                            "benchmark_origin": "external_definition",
                            "source_type": "real_human_study",
                            "human_participant_count": 10,
                            "human_outcome_count": 10,
                        },
                        "boundary": "External benchmark coverage is sufficient only for the scoped stage and evidence type recorded here.",
                    },
                },
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

            status, payload = call_app(
                "POST",
                "/api/v1/export-bundles",
                token="token-mvp-api",
                payload={
                    "study_id": study["study_id"],
                    "job_id": job["job_id"],
                    "title": "MVP export",
                    "export_format": "report_json",
                },
            )
            self.assertEqual(status, "201 Created")
            export_bundle_id = payload["export_bundle"]["export_bundle_id"]
            self.assertEqual(payload["export_bundle"]["mvp_launch_scope"]["status"], "design_partner_candidate")
            self.assertEqual(payload["export_bundle"]["mvp_promotion"]["status"], "approval_required")
            self.assertEqual(payload["export_bundle"]["public_claims_boundary"]["status"], "controlled_mvp_only")

            status, payload = call_app(
                "POST",
                "/api/v1/share-bundles",
                token="token-mvp-api",
                payload={
                    "export_bundle_id": export_bundle_id,
                    "title": "Blocked until approval",
                    "expires_in_days": 7,
                },
            )
            self.assertEqual(status, "403 Forbidden")

            status, payload = call_app(
                "POST",
                f"/api/v1/export-bundles/{export_bundle_id}/mvp-promotion-request",
                token="token-mvp-api",
                payload={"note": "Request approval for bounded design-partner circulation."},
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["export_bundle"]["mvp_promotion"]["status"], "pending_approval")
            self.assertEqual(len(payload["export_bundle"]["mvp_promotion_history"]), 1)
            self.assertEqual(payload["export_bundle"]["mvp_promotion_history"][0]["event"], "requested")

            status, payload = call_app(
                "POST",
                f"/api/v1/export-bundles/{export_bundle_id}/mvp-promotion-review",
                token="token-mvp-api",
                payload={"decision": "approved", "note": "Approved for controlled MVP circulation."},
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["export_bundle"]["mvp_promotion"]["status"], "approved")
            self.assertEqual(len(payload["export_bundle"]["mvp_promotion_history"]), 2)
            self.assertEqual(payload["export_bundle"]["mvp_promotion_history"][-1]["event"], "reviewed")
            self.assertEqual(payload["export_bundle"]["mvp_promotion_history"][-1]["status"], "approved")

            status, payload = call_app(
                "POST",
                "/api/v1/share-bundles",
                token="token-mvp-api",
                payload={
                    "export_bundle_id": export_bundle_id,
                    "title": "Approved design-partner share without onboarding",
                    "expires_in_days": 7,
                },
            )
            self.assertEqual(status, "400 Bad Request")

            status, payload = call_app(
                "POST",
                "/api/v1/share-bundles",
                token="token-mvp-api",
                payload={
                    "export_bundle_id": export_bundle_id,
                    "title": "Approved design-partner share",
                    "expires_in_days": 7,
                    "partner_name": "Acme Design Partner",
                    "partner_team_label": "Research Ops",
                    "partner_use_case": "prototype_validation_review",
                    "support_channel": "partner-success@acme.test",
                    "review_window_days": 10,
                },
            )
            self.assertEqual(status, "201 Created")
            share_bundle_id = payload["share_bundle"]["share_bundle_id"]
            share_key = payload["share_bundle"]["share_key"]
            self.assertEqual(payload["share_bundle"]["mvp_promotion"]["status"], "approved")
            self.assertEqual(payload["share_bundle"]["mvp_launch_scope"]["status"], "design_partner_candidate")
            self.assertEqual(len(payload["share_bundle"]["mvp_promotion_history"]), 2)
            self.assertEqual(payload["share_bundle"]["partner_onboarding"]["status"], "ready")
            self.assertEqual(payload["share_bundle"]["partner_onboarding"]["partner_name"], "Acme Design Partner")
            self.assertEqual(payload["share_bundle"]["mvp_release_review"]["status"], "approval_required")
            self.assertEqual(payload["share_bundle"]["mvp_release_review_history"], [])
            self.assertEqual(payload["share_bundle"]["public_claims_boundary"]["status"], "controlled_mvp_only")

            status, payload = call_app("GET", f"/public/v1/share-bundles/{share_key}")
            self.assertEqual(status, "410 Gone")

            status, payload = call_app(
                "POST",
                f"/api/v1/share-bundles/{share_bundle_id}/mvp-release-review-request",
                token="token-mvp-api",
                payload={"note": "Request final controlled MVP release approval."},
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["share_bundle"]["mvp_release_review"]["status"], "pending_approval")
            self.assertEqual(len(payload["share_bundle"]["mvp_release_review_history"]), 1)
            self.assertEqual(payload["share_bundle"]["mvp_release_review_history"][0]["event"], "requested")

            status, payload = call_app(
                "POST",
                f"/api/v1/share-bundles/{share_bundle_id}/mvp-release-review",
                token="token-mvp-api",
                payload={"decision": "approved", "note": "Approved for bounded partner-facing delivery."},
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["share_bundle"]["mvp_release_review"]["status"], "approved")
            self.assertEqual(len(payload["share_bundle"]["mvp_release_review_history"]), 2)
            self.assertEqual(payload["share_bundle"]["mvp_release_review_history"][-1]["event"], "reviewed")
            self.assertEqual(payload["share_bundle"]["mvp_release_review_history"][-1]["status"], "approved")

            status, payload = call_app("GET", f"/public/v1/share-bundles/{share_key}")
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["share_bundle"]["mvp_promotion"]["status"], "approved")
            self.assertEqual(payload["share_bundle"]["mvp_launch_scope"]["status"], "design_partner_candidate")
            self.assertEqual(len(payload["share_bundle"]["mvp_promotion_history"]), 2)
            self.assertEqual(payload["share_bundle"]["partner_onboarding"]["status"], "ready")
            self.assertEqual(payload["share_bundle"]["mvp_release_review"]["status"], "approved")
            self.assertEqual(len(payload["share_bundle"]["mvp_release_review_history"]), 2)
            self.assertEqual(payload["share_bundle"]["partner_onboarding"]["circulation_policy"]["status"], "bounded_design_partner_only")
            self.assertEqual(payload["share_bundle"]["public_claims_boundary"]["status"], "controlled_mvp_only")

            status, payload = call_app("GET", f"/api/v1/studies/{study['study_id']}/activity", token="token-mvp-api")
            self.assertEqual(status, "200 OK")
            actions = [event["action"] for event in payload["study_activity"]["activity_events"]]
            self.assertIn("export_bundle.mvp_promotion_requested", actions)
            self.assertIn("export_bundle.mvp_promotion_reviewed", actions)
            self.assertIn("share_bundle.mvp_release_review_requested", actions)
            self.assertIn("share_bundle.mvp_release_reviewed", actions)

    def test_workflow_mapping_evidence_context_links_into_saved_views_and_decisions(self) -> None:
        class WorkflowMappingFacilitator:
            provider_name = "workflow-mapping"
            model_name = "workflow-mapping/v1"

            def __init__(self):
                self.decisions = [
                    FacilitatorDecision(
                        interview_phase="recent_event",
                        probing_strategy="critical_incident",
                        decision_rationale="Anchor workflow mapping in one recent real episode.",
                        message_to_persona="Tell me about the last messy workflow episode.",
                        evidence_updates=[],
                        root_cause_hypotheses=[],
                        open_questions=["Which workflow episode should we map?"],
                        should_end=False,
                        end_reason="",
                        provider_session_id="workflow-thread-1",
                    ),
                    FacilitatorDecision(
                        interview_phase="workflow_sequence",
                        probing_strategy="sequence_probe",
                        decision_rationale="Map the concrete sequence.",
                        message_to_persona="What happened first, next, and after that?",
                        evidence_updates=[],
                        root_cause_hypotheses=[],
                        open_questions=["What is the workflow sequence?"],
                        should_end=False,
                        end_reason="",
                        provider_session_id="workflow-thread-1",
                    ),
                    FacilitatorDecision(
                        interview_phase="handoff_boundary",
                        probing_strategy="handoff_probe",
                        decision_rationale="Identify the handoff.",
                        message_to_persona="Where did the work hand off?",
                        evidence_updates=[],
                        root_cause_hypotheses=[],
                        open_questions=["Which handoff mattered?"],
                        should_end=False,
                        end_reason="",
                        provider_session_id="workflow-thread-1",
                    ),
                    FacilitatorDecision(
                        interview_phase="fragmentation_point",
                        probing_strategy="fragmentation_probe",
                        decision_rationale="Find the fragmentation point.",
                        message_to_persona="Where did the workflow fragment across tools?",
                        evidence_updates=[],
                        root_cause_hypotheses=[],
                        open_questions=["Where did fragmentation show up?"],
                        should_end=False,
                        end_reason="",
                        provider_session_id="workflow-thread-1",
                    ),
                    FacilitatorDecision(
                        interview_phase="current_workaround",
                        probing_strategy="workaround_probe",
                        decision_rationale="Capture the workaround.",
                        message_to_persona="What workaround kept it moving?",
                        evidence_updates=[],
                        root_cause_hypotheses=[],
                        open_questions=["What workaround held things together?"],
                        should_end=False,
                        end_reason="",
                        provider_session_id="workflow-thread-1",
                    ),
                    FacilitatorDecision(
                        interview_phase="switching_cost",
                        probing_strategy="switching_cost_probe",
                        decision_rationale="Measure switching cost.",
                        message_to_persona="What cost shows up when you rebuild context?",
                        evidence_updates=[],
                        root_cause_hypotheses=[],
                        open_questions=["What switching cost appears?"],
                        should_end=False,
                        end_reason="",
                        provider_session_id="workflow-thread-1",
                    ),
                    FacilitatorDecision(
                        interview_phase="responsibility_gap",
                        probing_strategy="responsibility_gap_probe",
                        decision_rationale="Capture the ownership gap.",
                        message_to_persona="Where does ownership become unclear?",
                        evidence_updates=[],
                        root_cause_hypotheses=[],
                        open_questions=["Where is ownership unclear?"],
                        should_end=False,
                        end_reason="",
                        provider_session_id="workflow-thread-1",
                    ),
                ]

            def next_turn(self, **kwargs):
                return self.decisions.pop(0)

            def synthesize(self, **kwargs):
                return ({
                    "executive_summary": "The workflow breaks at cross-tool handoffs, then survives through manual workaround and ownership chasing.",
                    "insights": [{
                        "insight": "The workflow slows down when context has to be rebuilt across Slack, a spreadsheet, and the task board.",
                        "evidence_refs": ["exchange_2.persona", "exchange_4.persona", "exchange_6.persona"],
                        "confidence": "medium",
                        "implication": "Review fragmentation and handoff evidence before discussing solutions.",
                    }],
                    "root_cause_hypotheses": [],
                    "how_might_we_questions": ["How might we reduce cross-tool handoff rebuild without another tracking layer?"],
                    "evidence_gaps": ["Human interviews are still needed to confirm how common this fragmentation pattern is across teams."],
                    "synthetic_only_disclaimer": "Synthetic-user interview for AI pre-validation only; not human market evidence.",
                }, "workflow-thread-1")

        class WorkflowMappingPersona:
            provider_name = "workflow-mapping"
            model_name = "workflow-mapping-persona/v1"

            def __init__(self):
                self.responses = [
                    "Last Thursday I had to coordinate notes, a spreadsheet, and the task board just to see what was done.",
                    "First I checked Slack, then the spreadsheet, then the task board, and then I went back to Slack because the board was stale.",
                    "The main handoff was from the account manager's Slack update into the shared task board.",
                    "It fragmented when the board, spreadsheet, and message thread stopped matching, so I had to compare all three.",
                    "I copied the missing note into the board and left myself a reminder in the spreadsheet.",
                    "It costs about twenty minutes and a lot of rechecking because I have to rebuild the same context every time the tools drift apart.",
                    "Ownership gets fuzzy right after the client note lands because nobody is sure who updates the board first.",
                ]

            def respond(self, **kwargs):
                return ChatResult(
                    reply=self.responses.pop(0),
                    intent_level="unclear",
                    confidence="high",
                    provider_session_id="workflow-persona-thread-1",
                )

            def generate_persona_driver_trace(self, **kwargs):
                return type("TraceResult", (), {
                    "payload": {
                        "synthetic_only_disclaimer": "Synthetic persona post-interview reflection only; not human market evidence.",
                        "surface_read": {
                            "what_the_persona_explicitly_said": [
                                "The workflow broke across Slack, a spreadsheet, and the task board.",
                                "They manually copied missing notes to keep the handoff moving.",
                            ],
                            "what_they_seemed_to_optimize_for": "Keep cross-team follow-up moving without losing context.",
                            "what_stayed_implicit": [
                                "Whether the same ownership confusion appears in every client follow-up or only the messy ones.",
                            ],
                        },
                        "likely_drivers": [{
                            "driver": "Reduce cross-tool context rebuild during handoffs",
                            "driver_type": "workflow_pattern",
                            "why_it_matters_here": "The participant spends effort restoring shared context when ownership and tool state diverge.",
                            "evidence_refs": ["exchange_2.persona", "exchange_4.persona", "exchange_6.persona", "exchange_7.persona"],
                            "profile_source_refs": ["workflow_adoption_model"],
                            "confidence": "medium",
                            "observed_vs_inferred": "mixed",
                        }],
                        "unspoken_constraints": [],
                        "value_tensions": [],
                        "missed_follow_up_questions": [],
                    },
                    "provider_session_id": "workflow-trace-thread-1",
                })()

        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_workflow",
                slug="workflow",
                display_name="Workflow",
                owner_user_id="owner_workflow",
                api_token="token-workflow",
                plan_tier="pro",
                billing_status="active",
                settings={"daily_runs": 5, "max_concurrent_jobs": 2},
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)
            auth = runtime.authenticate("token-workflow")
            project = runtime.create_workspace_project(auth, name="Discovery Program")
            study = runtime.create_workspace_study(
                auth,
                project_id=project["project_id"],
                title="Workflow fragmentation study",
                research_intent="Map the current workflow and fragmentation points.",
            )

            persona = generate_personas(count=1, random_seed=741)[0]
            persona_root = runtime_root / "workflow_personas"
            save_persona(persona, persona_root)
            interview_runtime = FacilitatedInterviewRuntime(
                data_dir=persona_root,
                session_dir=runtime_root,
                facilitator_provider=WorkflowMappingFacilitator(),
                persona_provider=WorkflowMappingPersona(),
            )
            interview_output = interview_runtime.run(
                persona_id=persona.profile.synthetic_user_id,
                research_goal="Map the current follow-up workflow, handoffs, and fragmentation points.",
                interview_mode="workflow_mapping",
                soft_turn_limit=7,
                hard_turn_limit=8,
            )
            interview_session = json.loads((interview_output / "interview.json").read_text(encoding="utf-8"))
            run_id = interview_session["interview_id"]

            queued_job = runtime.submit_validation_job(
                auth,
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    provider_name="mock",
                    metadata={"project_id": project["project_id"], "study_id": study["study_id"]},
                ),
            )
            job_store.update_validation_job(
                runtime_root,
                job_id=queued_job["job_id"],
                status="completed",
                output_run_path=str(interview_output),
                metadata_updates={
                    "project_id": project["project_id"],
                    "study_id": study["study_id"],
                    "run_id": run_id,
                },
            )

            query_payload = query_run_evidence(
                runtime_root,
                run_id=run_id,
                query_text="fragmentation",
                active_family="analysis",
                sort_by="relevance",
            )
            workflow_result = next(
                item for item in query_payload["results"] if item["kind"] == "workflow_map_evidence"
            )

            evidence_view = runtime.create_workspace_evidence_view(
                auth,
                study_id=study["study_id"],
                job_id=queued_job["job_id"],
                title="Workflow fragmentation evidence",
                note="Preserve the workflow fragmentation slice for discovery review.",
                query_text="fragmentation",
                active_family="analysis",
                sort_by="relevance",
                selected_result_id=workflow_result["id"],
            )
            self.assertTrue(evidence_view["workflow_map_focus"])
            self.assertEqual(evidence_view["selected_signal_id"], "analysis:workflow_map_evidence")
            self.assertIn("workflow", evidence_view["signal_terms"])
            self.assertEqual(evidence_view["readiness_gate"]["status"], "human_validation_required")
            evidence_view_payload = json.loads(Path(evidence_view["payload_path"]).read_text(encoding="utf-8"))
            saved_context = evidence_view_payload["metadata"]["selected_evidence_context"]
            self.assertTrue(saved_context["workflow_map_focus"])
            self.assertGreaterEqual(saved_context["workflow_fragmentation_count"], 1)

            decision_log = runtime.create_workspace_decision_log(
                auth,
                study_id=study["study_id"],
                job_id=queued_job["job_id"],
                evidence_view_id=evidence_view["evidence_view_id"],
                title="Do not change the process blindly",
                decision_summary="The current workflow still breaks at cross-tool handoffs.",
                rationale="The saved workflow evidence shows fragmentation, switching cost, and ownership gaps before any solution evaluation.",
                selected_result_id=workflow_result["id"],
            )
            self.assertTrue(decision_log["workflow_map_focus"])
            self.assertEqual(decision_log["selected_signal_id"], "analysis:workflow_map_evidence")
            self.assertEqual(decision_log["readiness_gate"]["status"], "human_validation_required")
            decision_payload = json.loads(Path(decision_log["payload_path"]).read_text(encoding="utf-8"))
            self.assertTrue(decision_payload["metadata"]["selected_evidence_context"]["workflow_map_focus"])
            self.assertEqual(decision_payload["readiness_gate"]["status"], "human_validation_required")
            self.assertGreaterEqual(
                decision_payload["metadata"]["selected_evidence_context"]["workflow_responsibility_gap_count"],
                1,
            )

    def test_export_and_share_bundles_surface_scoped_readiness_when_external_calibration_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_ready",
                slug="ready",
                display_name="Ready",
                owner_user_id="owner_ready",
                api_token="token-ready",
                plan_tier="pro",
                billing_status="active",
                settings={"daily_runs": 5, "max_concurrent_jobs": 2},
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)
            auth = runtime.authenticate("token-ready")
            project = runtime.create_workspace_project(auth, name="Pilot Program")
            study = runtime.create_workspace_study(
                auth,
                project_id=project["project_id"],
                title="Calibrated prototype study",
                research_intent="Check whether evidence gates can surface scoped external readiness.",
            )

            job = runtime.submit_validation_job(
                auth,
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    provider_name="mock",
                    metadata={"project_id": project["project_id"], "study_id": study["study_id"]},
                ),
            )
            completed = runtime.process_next_job()
            run_dir = Path(str(completed["output_run_path"]))
            write_json(
                run_dir / "human_calibration.json",
                {
                    "contract_version": "human-calibration/v1",
                    "benchmark_id": "benchmark_ready_001",
                    "prediction_accuracy": {
                        "alignment_score": 91.0,
                        "precision": 0.91,
                        "recall": 0.9,
                    },
                    "human_benchmark": {
                        "source_type": "real_human_study",
                    },
                    "replacement_readiness": {
                        "status": "candidate_replacement_ready",
                        "high_stakes_gate": False,
                        "boundary": "Human outcome data is attached; replacement readiness remains scoped to this stage and evidence type.",
                    },
                    "readiness_projection": {
                        "status": "candidate_scope_ready",
                        "gate_reasons": [],
                        "threshold_gaps": [],
                        "coverage": {
                            "benchmark_origin": "external_definition",
                            "source_type": "real_human_study",
                            "human_participant_count": 12,
                            "human_outcome_count": 12,
                        },
                        "boundary": "External benchmark coverage is sufficient only for the scoped stage and evidence type recorded here.",
                    },
                },
            )

            export_bundle = runtime.create_workspace_export_bundle(
                auth,
                study_id=study["study_id"],
                job_id=job["job_id"],
                title="Calibrated export",
                export_format="report_json",
            )
            self.assertEqual(export_bundle["readiness_gate"]["status"], "scoped_external_ready")
            self.assertTrue(export_bundle["market_claims_allowed"])
            self.assertEqual(export_bundle["mvp_launch_scope"]["status"], "design_partner_candidate")
            self.assertEqual(export_bundle["mvp_promotion"]["status"], "approval_required")
            export_manifest = json.loads(Path(export_bundle["manifest_path"]).read_text(encoding="utf-8"))
            self.assertEqual(export_manifest["readiness_gate"]["status"], "scoped_external_ready")
            self.assertTrue(export_manifest["readiness_gate"]["market_claims_allowed"])
            self.assertEqual(export_manifest["mvp_launch_scope"]["status"], "design_partner_candidate")
            self.assertEqual(export_manifest["mvp_promotion"]["status"], "approval_required")

            with self.assertRaises(AuthorizationError):
                runtime.create_workspace_share_bundle(
                    auth,
                    export_bundle_id=export_bundle["export_bundle_id"],
                    title="Calibrated share without approval",
                    expires_in_days=7,
                )

            pending_export_bundle = runtime.request_workspace_export_bundle_mvp_promotion(
                auth,
                export_bundle["export_bundle_id"],
                note="Ready for bounded design-partner pilot review.",
            )
            self.assertEqual(pending_export_bundle["mvp_promotion"]["status"], "pending_approval")
            self.assertEqual(pending_export_bundle["mvp_promotion"]["requested_by_user_id"], auth.user_id)

            approved_export_bundle = runtime.review_workspace_export_bundle_mvp_promotion(
                auth,
                export_bundle["export_bundle_id"],
                decision="approved",
                note="Approved for bounded design-partner circulation.",
            )
            self.assertEqual(approved_export_bundle["mvp_promotion"]["status"], "approved")
            self.assertEqual(approved_export_bundle["mvp_promotion"]["reviewed_by_user_id"], auth.user_id)

            with self.assertRaises(ValueError):
                runtime.create_workspace_share_bundle(
                    auth,
                    export_bundle_id=export_bundle["export_bundle_id"],
                    title="Calibrated share missing partner onboarding",
                    expires_in_days=7,
                )

            share_bundle = runtime.create_workspace_share_bundle(
                auth,
                export_bundle_id=export_bundle["export_bundle_id"],
                title="Calibrated share",
                expires_in_days=7,
                partner_name="Pilot Design Partner",
                partner_team_label="Product Research",
                partner_use_case="prototype_validation_review",
                support_channel="partner-success@pilot.test",
                review_window_days=14,
            )
            self.assertEqual(share_bundle["readiness_gate"]["status"], "scoped_external_ready")
            self.assertTrue(share_bundle["market_claims_allowed"])
            self.assertEqual(share_bundle["mvp_launch_scope"]["status"], "design_partner_candidate")
            self.assertEqual(share_bundle["mvp_promotion"]["status"], "approved")
            self.assertEqual(share_bundle["partner_onboarding"]["status"], "ready")
            self.assertEqual(share_bundle["partner_onboarding"]["partner_name"], "Pilot Design Partner")
            self.assertEqual(share_bundle["mvp_release_review"]["status"], "approval_required")
            share_payload = json.loads(Path(share_bundle["share_payload_path"]).read_text(encoding="utf-8"))
            self.assertEqual(share_payload["readiness_gate"]["status"], "scoped_external_ready")
            self.assertTrue(share_payload["readiness_gate"]["market_claims_allowed"])
            self.assertEqual(share_payload["mvp_launch_scope"]["status"], "design_partner_candidate")
            self.assertEqual(share_payload["mvp_promotion"]["status"], "approved")
            self.assertEqual(share_payload["partner_onboarding"]["status"], "ready")
            self.assertEqual(share_payload["mvp_release_review"]["status"], "approval_required")
            self.assertEqual(share_payload["partner_onboarding"]["circulation_policy"]["status"], "bounded_design_partner_only")

            with self.assertRaises(ShareUnavailableError):
                runtime.get_public_share_bundle(share_bundle["share_key"])

            pending_share_bundle = runtime.request_workspace_share_bundle_mvp_release_review(
                auth,
                share_bundle["share_bundle_id"],
                note="Request final bounded MVP release review.",
            )
            self.assertEqual(pending_share_bundle["mvp_release_review"]["status"], "pending_approval")

            approved_share_bundle = runtime.review_workspace_share_bundle_mvp_release_review(
                auth,
                share_bundle["share_bundle_id"],
                decision="approved",
                note="Approved for bounded partner-facing delivery.",
            )
            self.assertEqual(approved_share_bundle["mvp_release_review"]["status"], "approved")

            public_share = runtime.get_public_share_bundle(share_bundle["share_key"])
            self.assertEqual(public_share["mvp_release_review"]["status"], "approved")

    def test_high_stakes_readiness_blocks_public_share_creation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            runtime_root = Path(tmp) / "runtime"
            runtime = SaasRuntime(runtime_root)
            bootstrap = runtime.bootstrap_workspace(
                workspace_id="ws_high_stakes",
                slug="high-stakes",
                display_name="High Stakes",
                owner_user_id="owner_high_stakes",
                api_token="token-high-stakes",
                plan_tier="pro",
                billing_status="active",
                settings={"daily_runs": 5, "max_concurrent_jobs": 2},
            )
            workspace_root = Path(bootstrap["workspace_root"])
            brief_path, persona_dir = self._workspace_inputs(workspace_root)
            auth = runtime.authenticate("token-high-stakes")
            project = runtime.create_workspace_project(auth, name="High Stakes Program")
            study = runtime.create_workspace_study(
                auth,
                project_id=project["project_id"],
                title="High-stakes calibrated study",
                research_intent="Keep high-stakes evidence out of public share until human review clears it.",
            )

            job = runtime.submit_validation_job(
                auth,
                ValidationJobRequest(
                    brief_path=str(brief_path.relative_to(workspace_root)),
                    persona_dir=str(persona_dir.relative_to(workspace_root)),
                    panel_spec=PanelSpec(panel_type="mainstream", sample_size=1, random_seed=11),
                    provider_name="mock",
                    metadata={"project_id": project["project_id"], "study_id": study["study_id"]},
                ),
            )
            completed = runtime.process_next_job()
            run_dir = Path(str(completed["output_run_path"]))
            write_json(
                run_dir / "human_calibration.json",
                {
                    "contract_version": "human-calibration/v1",
                    "benchmark_id": "benchmark_high_stakes_001",
                    "prediction_accuracy": {
                        "alignment_score": 96.0,
                        "precision": 0.95,
                        "recall": 0.94,
                    },
                    "human_benchmark": {
                        "source_type": "real_human_study",
                    },
                    "replacement_readiness": {
                        "status": "high_stakes_human_review_required",
                        "high_stakes_gate": True,
                        "boundary": "High-stakes evidence requires explicit human review regardless of synthetic alignment score.",
                    },
                    "readiness_projection": {
                        "status": "high_stakes_gate",
                        "gate_reasons": ["high_stakes_human_review_required"],
                        "threshold_gaps": [],
                        "coverage": {
                            "benchmark_origin": "external_definition",
                            "source_type": "real_human_study",
                            "human_participant_count": 8,
                            "human_outcome_count": 8,
                        },
                        "boundary": "High-stakes evidence requires explicit human review before broader circulation.",
                    },
                },
            )

            export_bundle = runtime.create_workspace_export_bundle(
                auth,
                study_id=study["study_id"],
                job_id=job["job_id"],
                title="High-stakes export",
                export_format="report_json",
            )
            self.assertEqual(export_bundle["readiness_gate"]["status"], "human_review_required")
            self.assertEqual(export_bundle["readiness_gate"]["share_status"], "restricted_human_review_required")
            self.assertEqual(export_bundle["mvp_launch_scope"]["status"], "blocked")

            with self.assertRaises(AuthorizationError):
                runtime.create_workspace_share_bundle(
                    auth,
                    export_bundle_id=export_bundle["export_bundle_id"],
                    title="Blocked high-stakes share",
                    expires_in_days=7,
                )

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
            self.assertTrue(payload["workspace_settings"]["capabilities"]["billing_governance_history"])
            self.assertEqual(payload["workspace_settings"]["billing_governance"]["billing_history"], [])
            self.assertEqual(payload["workspace_settings"]["billing_governance"]["policy_history"], [])

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
                    "note": "Upgrade pilot limits for the active design-partner workspace.",
                },
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["billing"]["workspace"]["plan_tier"], "pro")
            self.assertEqual(payload["billing"]["billing_account"]["status"], "active")
            self.assertEqual(payload["billing"]["billing_account"]["seat_count"], 4)
            self.assertEqual(payload["billing"]["plan_limits"]["daily_runs"], 25)
            self.assertEqual(len(payload["billing"]["billing_governance"]["billing_history"]), 1)
            self.assertEqual(len(payload["billing"]["billing_governance"]["policy_history"]), 1)
            self.assertEqual(
                payload["billing"]["billing_governance"]["billing_history"][0]["changes"]["plan_tier"]["next"],
                "pro",
            )
            self.assertEqual(
                payload["billing"]["billing_governance"]["policy_history"][0]["changes"]["artifact_retention_days"]["next"],
                30,
            )
            self.assertEqual(
                payload["billing"]["billing_governance"]["latest_policy_change"]["note"],
                "Upgrade pilot limits for the active design-partner workspace.",
            )
            self.assertEqual(payload["workspace_settings"]["billing_account"]["price_book_id"], "pro")
            self.assertEqual(payload["workspace_settings"]["policies"]["artifact_retention_days"], 30)
            self.assertEqual(len(payload["workspace_settings"]["billing_governance"]["billing_history"]), 1)
            self.assertEqual(len(payload["workspace_settings"]["billing_governance"]["policy_history"]), 1)

            status, payload = call_app(
                "POST",
                "/api/v1/workspace-billing",
                token="token-settings",
                payload={
                    "artifact_retention_days": 45,
                    "daily_runs": 40,
                    "note": "Extend retention while keeping the partner pilot under review.",
                },
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(payload["billing"]["plan_limits"]["artifact_retention_days"], 45)
            self.assertEqual(payload["billing"]["plan_limits"]["daily_runs"], 40)
            self.assertEqual(len(payload["billing"]["billing_governance"]["billing_history"]), 1)
            self.assertEqual(len(payload["billing"]["billing_governance"]["policy_history"]), 2)
            self.assertEqual(
                payload["billing"]["billing_governance"]["latest_policy_change"]["changes"]["artifact_retention_days"]["next"],
                45,
            )
            self.assertEqual(
                payload["billing"]["billing_governance"]["latest_policy_change"]["note"],
                "Extend retention while keeping the partner pilot under review.",
            )

            status, payload = call_app("GET", "/api/v1/privacy-export-controls", token="token-settings")
            self.assertEqual(status, "200 OK")
            privacy_controls = payload["privacy_export_controls"]
            self.assertEqual(privacy_controls["contract_version"], "workspace-privacy-export-controls/v1")
            self.assertEqual(privacy_controls["retention_controls"]["artifact_retention_days"], 45)
            self.assertEqual(privacy_controls["export_share_controls"]["export_bundle_count"], 0)
            self.assertIn(
                "deletion_request_policy_missing",
                privacy_controls["privacy_readiness"]["blocked_reasons"],
            )

            status, payload = call_app(
                "POST",
                "/api/v1/privacy-export-controls/policy",
                token="token-settings",
                payload={
                    "data_residency_region": "us-east-1",
                    "artifact_retention_days": 60,
                    "deletion_request_policy": "owner_review_required",
                    "export_review_required": True,
                    "share_default_expiry_days": 21,
                    "note": "Prepare customer-grade privacy controls for broader pilot review.",
                },
            )
            self.assertEqual(status, "200 OK")
            privacy_controls = payload["privacy_export_controls"]
            self.assertEqual(privacy_controls["data_residency"]["data_residency_region"], "us-east-1")
            self.assertEqual(privacy_controls["retention_controls"]["artifact_retention_days"], 60)
            self.assertEqual(privacy_controls["deletion_controls"]["deletion_request_policy"], "owner_review_required")
            self.assertEqual(privacy_controls["export_share_controls"]["share_default_expiry_days"], 21)
            self.assertEqual(privacy_controls["privacy_readiness"]["status"], "ready_for_customer_review")
            self.assertEqual(
                privacy_controls["downstream_lineage"]["latest_policy_change"]["changes"]["artifact_retention_days"]["next"],
                60,
            )

            status, payload = call_app(
                "POST",
                "/api/v1/privacy-export-controls/deletion-requests",
                token="token-settings",
                payload={
                    "scope_type": "workspace",
                    "scope_id": "ws_settings",
                    "reason": "Customer requested review of retained uploaded artifacts before wider pilot.",
                    "requested_action": "record_for_review",
                    "approval_note": "Keep lineage while privacy owner reviews payload deletion.",
                },
            )
            self.assertEqual(status, "201 Created")
            deletion_request = payload["deletion_request"]
            self.assertTrue(deletion_request["deletion_request_id"].startswith("privacy_delete_"))
            self.assertEqual(deletion_request["scope_type"], "workspace")
            self.assertTrue(deletion_request["lineage_retained"])
            self.assertEqual(
                payload["privacy_export_controls"]["deletion_controls"]["latest_request"]["deletion_request_id"],
                deletion_request["deletion_request_id"],
            )

            status, payload = call_app(
                "GET",
                "/api/v1/audit-events",
                token="token-settings",
                query="action_prefix=workspace.privacy&limit=10",
            )
            self.assertEqual(status, "200 OK")
            self.assertEqual(
                {event["action"] for event in payload["audit_history"]["audit_events"]},
                {"workspace.privacy_policy_updated", "workspace.privacy_deletion_requested"},
            )

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

            status, payload = call_app(
                "GET",
                "/api/v1/audit-events",
                token="token-settings",
                query="action_prefix=workspace_&limit=10",
            )
            self.assertEqual(status, "200 OK")
            self.assertIn("workspace_billing.updated", {event["action"] for event in payload["audit_history"]["audit_events"]})
            self.assertIn("workspace_policy.updated", {event["action"] for event in payload["audit_history"]["audit_events"]})

            status, payload = call_app("GET", "/api/v1/session", token="token-settings")
            self.assertEqual(status, "200 OK")
            self.assertTrue(payload["session"]["capabilities"]["workspace_settings"])
            self.assertTrue(payload["session"]["capabilities"]["billing_surface"])
            self.assertTrue(payload["session"]["capabilities"]["audit_history"])
            self.assertEqual(payload["session"]["workspace"]["plan_tier"], "pro")
            self.assertEqual(payload["session"]["plan_limits"]["max_concurrent_jobs"], 3)


if __name__ == "__main__":
    unittest.main()
