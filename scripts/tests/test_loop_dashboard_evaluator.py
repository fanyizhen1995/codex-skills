import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _build_governance_repo_fixture(root: Path, *, expansion_phase: str = "stopped_budget") -> None:
    scenario_src = (
        Path(__file__).resolve().parents[2]
        / "docs"
        / "harness"
        / "evaluator-scenarios"
        / "ai-infra-loop-governance-dev-01.json"
    )
    scenario_dst = root / "docs" / "harness" / "evaluator-scenarios" / "ai-infra-loop-governance-dev-01.json"
    scenario_dst.parent.mkdir(parents=True, exist_ok=True)
    scenario_dst.write_text(scenario_src.read_text(encoding="utf-8"), encoding="utf-8")

    _write_json(
        root / ".codex" / "loop-runs" / "ai-infra-loop-governance-dev" / "run.json",
        {
            "run_id": "ai-infra-loop-governance-dev",
            "policy": "demand_development",
            "run_kind": "parent",
            "phase": "child_running",
            "child_run_ids": ["ai-infra-loop-governance-dev-child-001"],
            "current_child_run_id": "ai-infra-loop-governance-dev-child-001",
            "backlog": [
                {"task_id": "queue-001", "title": "queue item", "status": "queued"},
                {"task_id": "blocked-001", "title": "blocked item", "status": "blocked"},
            ],
            "reader_summary": {
                "purpose": "governance parent",
                "current_progress": "1 child running",
                "next_step": "Inspect blocked child and queued needs",
                "decision_needed": "Yes",
            },
        },
    )
    _write_json(
        root / ".codex" / "loop-runs" / "ai-infra-expansion-2026-07-07-r10" / "run.json",
        {
            "run_id": "ai-infra-expansion-2026-07-07-r10",
            "phase": expansion_phase,
        },
    )
    _write_json(
        root / ".codex" / "loop-runs" / "ai-infra-loop-governance-dev-child-001" / "evaluator-result.json",
        {
            "formal_verification": {"status": "pass", "required_counterexample_reruns": []},
            "formal_verification_artifact_paths": [
                ".codex/loop-runs/ai-infra-loop-governance-dev-child-001/formal-proof.txt"
            ],
            "verdict_reason": "No unresolved confirmed formal bug remains.",
        },
    )
    _write_json(
        root / "personal-wiki" / "domains" / "ai_infra" / "manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json",
        {
            "channels": [{"name": "vendor"}],
            "sources": [{"url": "https://example.com/spec"}],
        },
    )


def _scenario_statuses(payload: dict) -> dict[str, str]:
    return {item["scenario_id"]: item["status"] for item in payload["scenario_results"]}


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

    def test_governance_e2e_0_tracks_preflight_artifact_gate(self) -> None:
        from scripts.loop_dashboard_evaluator import evaluate_governance_repo

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _build_governance_repo_fixture(repo_root)
            with patch(
                "scripts.loop_dashboard_evaluator.validate_governance_preflight_evidence",
                return_value={
                    "status": "blocked",
                    "artifact_paths": [".codex/loop-runs/ai-infra-loop-governance-dev/identity-key-audit.json"],
                    "missing_artifacts": [".codex/loop-runs/ai-infra-loop-governance-dev/egress-proof.json"],
                    "findings": ["identity-key-audit.json status must be pass"],
                },
            ), patch(
                "scripts.loop_dashboard_evaluator.read_json_url",
                return_value={
                    "children": [
                        {
                            "run_id": "ai-infra-loop-governance-dev-child-001",
                            "phase": "repair_needed",
                            "reader_summary": {"acceptance_result": "Repair needed"},
                        }
                    ],
                    "children_summary": {"total": 1, "blocked": 1, "passed": 0, "pending": 0},
                    "governance_artifacts": {
                        "source_profile_snapshots": [
                            "personal-wiki/domains/ai_infra/manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json"
                        ]
                    },
                },
            ), patch("scripts.loop_dashboard_evaluator.check_health_endpoint", return_value=True), patch(
                "scripts.loop_dashboard_evaluator.check_frontend", return_value=True
            ):
                payload = evaluate_governance_repo(
                    repo_root,
                    dashboard_url="http://127.0.0.1:8766",
                    crawler_health_url="http://127.0.0.1:8765/api/health",
                    frontend_url="http://127.0.0.1:5173/",
                )

        self.assertEqual(_scenario_statuses(payload)["E2E-0"], "fail")

    def test_governance_e2e_1_tracks_stopped_budget_takeover(self) -> None:
        from scripts.loop_dashboard_evaluator import evaluate_governance_repo

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _build_governance_repo_fixture(repo_root, expansion_phase="child_running")
            with patch(
                "scripts.loop_dashboard_evaluator.validate_governance_preflight_evidence",
                return_value={
                    "status": "pass",
                    "artifact_paths": [
                        ".codex/loop-runs/ai-infra-loop-governance-dev/egress-proof.json",
                        ".codex/loop-runs/ai-infra-loop-governance-dev/identity-key-audit.json",
                        ".codex/loop-runs/ai-infra-loop-governance-dev/depth-acquisition-smoke.json",
                        ".codex/loop-runs/ai-infra-loop-governance-dev/candidate-scoring/top.json",
                    ],
                    "missing_artifacts": [],
                    "findings": [],
                },
            ), patch(
                "scripts.loop_dashboard_evaluator.read_json_url",
                return_value={
                    "children": [
                        {
                            "run_id": "ai-infra-loop-governance-dev-child-001",
                            "phase": "repair_needed",
                            "reader_summary": {"acceptance_result": "Repair needed"},
                        }
                    ],
                    "children_summary": {"total": 1, "blocked": 1, "passed": 0, "pending": 0},
                    "governance_artifacts": {
                        "source_profile_snapshots": [
                            "personal-wiki/domains/ai_infra/manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json"
                        ]
                    },
                },
            ), patch("scripts.loop_dashboard_evaluator.check_health_endpoint", return_value=True), patch(
                "scripts.loop_dashboard_evaluator.check_frontend", return_value=True
            ):
                payload = evaluate_governance_repo(
                    repo_root,
                    dashboard_url="http://127.0.0.1:8766",
                    crawler_health_url="http://127.0.0.1:8765/api/health",
                    frontend_url="http://127.0.0.1:5173/",
                )

        self.assertEqual(_scenario_statuses(payload)["E2E-1"], "fail")

    def test_governance_e2e_2_requires_dashboard_parent_child_queue_visibility(self) -> None:
        from scripts.loop_dashboard_evaluator import evaluate_governance_repo

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _build_governance_repo_fixture(repo_root)
            with patch(
                "scripts.loop_dashboard_evaluator.validate_governance_preflight_evidence",
                return_value={
                    "status": "pass",
                    "artifact_paths": [
                        ".codex/loop-runs/ai-infra-loop-governance-dev/egress-proof.json",
                        ".codex/loop-runs/ai-infra-loop-governance-dev/identity-key-audit.json",
                        ".codex/loop-runs/ai-infra-loop-governance-dev/depth-acquisition-smoke.json",
                        ".codex/loop-runs/ai-infra-loop-governance-dev/candidate-scoring/top.json",
                    ],
                    "missing_artifacts": [],
                    "findings": [],
                },
            ), patch(
                "scripts.loop_dashboard_evaluator.read_json_url",
                return_value={
                    "children": [
                        {
                            "run_id": "ai-infra-loop-governance-dev-child-001",
                            "phase": "repair_needed",
                            "reader_summary": {"acceptance_result": "Repair needed"},
                        }
                    ],
                    "governance_artifacts": {
                        "source_profile_snapshots": [
                            "personal-wiki/domains/ai_infra/manifest-ai-infra-loop-governance-dev-source-profile-snapshot.json"
                        ]
                    },
                },
            ), patch("scripts.loop_dashboard_evaluator.check_health_endpoint", return_value=True), patch(
                "scripts.loop_dashboard_evaluator.check_frontend", return_value=True
            ):
                payload = evaluate_governance_repo(
                    repo_root,
                    dashboard_url="http://127.0.0.1:8766",
                    crawler_health_url="http://127.0.0.1:8765/api/health",
                    frontend_url="http://127.0.0.1:5173/",
                )

        self.assertEqual(_scenario_statuses(payload)["E2E-2"], "fail")

    def test_governance_evaluator_writes_result_json_on_governance_exception(self) -> None:
        from scripts import loop_dashboard_evaluator

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            output_dir = repo_root / ".codex" / "loop-dashboard-eval" / "ai-infra-loop-governance-dev-01"
            argv = [
                "loop_dashboard_evaluator.py",
                "--repo-root",
                str(repo_root),
                "--output-dir",
                str(output_dir),
            ]
            with patch.object(sys, "argv", argv), patch(
                "scripts.loop_dashboard_evaluator.evaluate_governance_repo",
                side_effect=RuntimeError("boom"),
            ):
                exit_code = loop_dashboard_evaluator.main()

            self.assertEqual(exit_code, 1)
            result_path = output_dir / "result.json"
            self.assertTrue(result_path.exists())
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["status"], "fail")
            self.assertEqual(payload["scenario_results"][0]["scenario_id"], "E2E-7")
            self.assertIn("boom", payload["diagnostics"][0])
            self.assertIn("generated_at", payload)


if __name__ == "__main__":
    unittest.main()
