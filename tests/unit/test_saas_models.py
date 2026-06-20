import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.domain.models import PanelSpec
from ai_validation_swarm.saas.models import TenantWorkspace, ValidationJob, WorkspaceMember


class SaasModelsTest(unittest.TestCase):
    def test_validation_job_to_dict_keeps_nested_panel_spec(self) -> None:
        job = ValidationJob(
            job_id="job_001",
            workspace_id="ws_001",
            brief_id="brief_001",
            requested_by_user_id="user_001",
            panel_spec=PanelSpec(panel_type="mainstream", sample_size=8, random_seed=11),
            provider_name="mock",
            status="queued",
            priority="normal",
            input_artifact_path="s3://bucket/input.json",
            output_run_path=None,
            retry_count=0,
            created_at="2026-06-18T00:00:00+00:00",
        )

        payload = job.to_dict()

        self.assertEqual(payload["panel_spec"]["panel_type"], "mainstream")
        self.assertEqual(payload["panel_spec"]["sample_size"], 8)

    def test_workspace_to_dict_keeps_members(self) -> None:
        workspace = TenantWorkspace(
            workspace_id="ws_001",
            slug="acme",
            display_name="Acme",
            region_code="HK",
            data_residency_region="ap-east-1",
            plan_tier="pro",
            status="active",
            created_at="2026-06-18T00:00:00+00:00",
            members=[
                WorkspaceMember(
                    user_id="user_001",
                    role="owner",
                    joined_at="2026-06-18T00:00:00+00:00",
                )
            ],
        )

        payload = workspace.to_dict()

        self.assertEqual(payload["members"][0]["role"], "owner")
        self.assertEqual(payload["slug"], "acme")
