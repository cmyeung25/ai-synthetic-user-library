import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_validation_swarm.evaluation.persona_quality_compare import (
    finalize_persona_quality_compare_report,
    normalize_judge_score,
    render_persona_quality_compare_markdown,
)


class PersonaQualityCompareTest(unittest.TestCase):
    def test_normalize_judge_score_handles_mixed_scale(self) -> None:
        self.assertEqual(normalize_judge_score(8), 8.0)
        self.assertEqual(normalize_judge_score(76), 7.6)
        self.assertIsNone(normalize_judge_score("n/a"))

    def test_finalize_persona_quality_compare_report_aggregates_scores(self) -> None:
        report = {
            "experiment_id": "demo",
            "generated_at": "2026-06-25T14:00:00+00:00",
            "seeds": [101, 202],
            "setup": {
                "baseline_label": "Codex",
                "candidate_label": "Agnes",
                "judge_label": "Codex",
                "baseline_prompt_version": "persona-enrichment/v1",
                "candidate_prompt_version": "persona-enrichment/v2",
                "judge_prompt_version": "persona-judge/v1",
            },
            "runs": [
                {
                    "seed": 101,
                    "baseline": {
                        "judge": {
                            "normalized_scores": {
                                "plausibility_score": 7.8,
                                "stereotype_risk_score": 3.4,
                                "panel_fit_score": 6.9,
                            }
                        },
                        "attempt_count": 1,
                        "fallback_used": False,
                    },
                    "candidate": {
                        "judge": {
                            "normalized_scores": {
                                "plausibility_score": 7.2,
                                "stereotype_risk_score": 4.1,
                                "panel_fit_score": 6.4,
                            }
                        },
                        "attempt_count": 2,
                        "fallback_used": True,
                    },
                },
                {
                    "seed": 202,
                    "baseline": {
                        "judge": {
                            "normalized_scores": {
                                "plausibility_score": 8.2,
                                "stereotype_risk_score": 2.4,
                                "panel_fit_score": 7.4,
                            }
                        },
                        "attempt_count": 1,
                        "fallback_used": False,
                    },
                    "candidate": {
                        "judge": {
                            "normalized_scores": {
                                "plausibility_score": 7.6,
                                "stereotype_risk_score": 3.4,
                                "panel_fit_score": 7.9,
                            }
                        },
                        "attempt_count": 1,
                        "fallback_used": False,
                    },
                },
            ],
        }

        finalize_persona_quality_compare_report(report)

        self.assertEqual(report["aggregates"]["baseline"]["average_plausibility_score_normalized"], 8.0)
        self.assertEqual(report["aggregates"]["candidate"]["average_plausibility_score_normalized"], 7.4)
        self.assertEqual(report["aggregates"]["deltas_candidate_minus_baseline"]["panel_fit_score_normalized"], 0.0)
        self.assertEqual(report["aggregates"]["reliability"]["candidate_total_attempts"], 3)
        self.assertEqual(report["aggregates"]["reliability"]["candidate_pairs_using_fallback"], 1)

    def test_render_persona_quality_compare_markdown_mentions_labels(self) -> None:
        report = {
            "experiment_id": "demo",
            "generated_at": "2026-06-25T14:00:00+00:00",
            "seeds": [101],
            "setup": {
                "baseline_label": "Codex",
                "candidate_label": "Agnes",
                "judge_label": "Codex",
                "baseline_prompt_version": "persona-enrichment/v1",
                "candidate_prompt_version": "persona-enrichment/v2",
                "judge_prompt_version": "persona-judge/v1",
            },
            "runs": [
                {
                    "seed": 101,
                    "baseline": {
                        "judge": {
                            "normalized_scores": {
                                "plausibility_score": 7.8,
                                "stereotype_risk_score": 3.4,
                                "panel_fit_score": 6.9,
                            }
                        },
                        "attempt_count": 1,
                        "fallback_used": False,
                    },
                    "candidate": {
                        "judge": {
                            "normalized_scores": {
                                "plausibility_score": 7.2,
                                "stereotype_risk_score": 4.1,
                                "panel_fit_score": 6.4,
                            }
                        },
                        "attempt_count": 2,
                        "fallback_used": True,
                    },
                }
            ],
        }

        finalize_persona_quality_compare_report(report)
        markdown = render_persona_quality_compare_markdown(report)

        self.assertIn("Baseline: Codex", markdown)
        self.assertIn("Candidate: Agnes", markdown)
        self.assertIn("Agnes attempts=2, fallback_used=True", markdown)


if __name__ == "__main__":
    unittest.main()
