import json
import tempfile
import unittest
from pathlib import Path


class LoopDashboardEvaluatorGovernanceTests(unittest.TestCase):
    def test_governance_evaluator_fails_when_required_artifacts_are_missing(self) -> None:
        from scripts.loop_dashboard_evaluator import run_governance_evaluator

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            output_dir = repo_root / ".codex" / "loop-dashboard-eval" / "ai-infra-loop-governance-dev-01"

            exit_code = run_governance_evaluator(repo_root, output_dir)

            self.assertEqual(exit_code, 1)
            payload = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "fail")
            self.assertEqual(payload["scenario_results"][0]["scenario_id"], "E2E-0")
            self.assertTrue(
                any(
                    "docs/harness/evaluator-scenarios/ai-infra-loop-governance-dev-01.json" in item
                    for item in payload["diagnostics"]
                )
            )


if __name__ == "__main__":
    unittest.main()
