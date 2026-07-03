import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import wiki_crawler_e2e_evaluator


class WikiCrawlerE2EEvaluatorTests(unittest.TestCase):
    def test_domain_channel_secret_literal_is_deterministic_and_unique(self) -> None:
        self.assertEqual(
            wiki_crawler_e2e_evaluator.DOMAIN_CHANNEL_SECRET,
            "domain-channel-e2e-synthetic-token-7c0f6a",
        )
        self.assertNotIn(
            wiki_crawler_e2e_evaluator.DOMAIN_CHANNEL_SECRET,
            wiki_crawler_e2e_evaluator.DOMAIN_CHANNEL_REPLACEMENT_SECRET,
        )

    def test_domain_channel_ui_env_allocates_isolated_ports_and_ignores_ambient_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = wiki_crawler_e2e_evaluator._domain_channel_ui_env(
                Path(tmp),
                base_env={
                    "PW_WORKBENCH_E2E_BACKEND_PORT": "19333",
                    "PW_WORKBENCH_E2E_BACKEND_URL": "http://127.0.0.1:8765",
                },
            )

            self.assertEqual(env["PW_WORKBENCH_E2E_BACKEND_URL"], "http://127.0.0.1:19333")
            self.assertNotEqual(env["PW_WORKBENCH_E2E_FRONTEND_PORT"], "5174")
            self.assertEqual(env["PW_WORKBENCH_E2E_DOMAIN_CHANNELS"], "1")
            self.assertEqual(
                env["PW_WORKBENCH_E2E_DOMAIN_CHANNEL_SECRET"],
                wiki_crawler_e2e_evaluator.DOMAIN_CHANNEL_REPLACEMENT_SECRET,
            )

    def test_secret_plaintext_scan_reports_retained_artifact_leaks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            output_dir.mkdir()
            (output_dir / "leak.json").write_text(
                wiki_crawler_e2e_evaluator.DOMAIN_CHANNEL_SECRET,
                encoding="utf-8",
            )

            result = wiki_crawler_e2e_evaluator._scan_for_forbidden_plaintext(
                output_dir,
                [wiki_crawler_e2e_evaluator.DOMAIN_CHANNEL_SECRET],
            )

            self.assertFalse(result["passed"])
            self.assertEqual(result["leaks"][0]["path"], "leak.json")

    def test_source_subscription_ui_env_allocates_isolated_ports_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = wiki_crawler_e2e_evaluator._source_subscription_ui_env(
                Path(tmp),
                base_env={},
            )

            self.assertNotEqual(env["PW_WORKBENCH_E2E_BACKEND_PORT"], "18765")
            self.assertNotEqual(env["PW_WORKBENCH_E2E_FRONTEND_PORT"], "5174")
            self.assertNotEqual(
                env["PW_WORKBENCH_E2E_BACKEND_PORT"],
                env["PW_WORKBENCH_E2E_FRONTEND_PORT"],
            )
            self.assertEqual(
                env["PW_WORKBENCH_E2E_BACKEND_URL"],
                f"http://127.0.0.1:{env['PW_WORKBENCH_E2E_BACKEND_PORT']}",
            )

    def test_source_subscription_ui_env_ignores_ambient_backend_url(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env = wiki_crawler_e2e_evaluator._source_subscription_ui_env(
                Path(tmp),
                base_env={
                    "PW_WORKBENCH_E2E_BACKEND_PORT": "19222",
                    "PW_WORKBENCH_E2E_BACKEND_URL": "http://127.0.0.1:8765",
                },
            )

            self.assertEqual(env["PW_WORKBENCH_E2E_BACKEND_URL"], "http://127.0.0.1:19222")

    def test_source_subscription_ui_failure_preserves_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            original = wiki_crawler_e2e_evaluator._run_source_subscription_ui_flow

            def failing_ui_flow(_source_repo: Path, _output_dir: Path) -> dict[str, object]:
                return {
                    "playwright": {
                        "command": ["npm", "run", "test:ui:live"],
                        "returncode": 1,
                        "stdout": "ui stdout",
                        "stderr": "ui stderr",
                    },
                    "json_report": "source-subscriptions-ui/source-subscriptions-live.json",
                    "report_dir": "source-subscriptions-ui/playwright-report",
                }

            try:
                wiki_crawler_e2e_evaluator._run_source_subscription_ui_flow = failing_ui_flow
                with self.assertRaises(wiki_crawler_e2e_evaluator.EvaluatorRunError) as raised:
                    wiki_crawler_e2e_evaluator.run_e2e(Path("."), output_dir)
            finally:
                wiki_crawler_e2e_evaluator._run_source_subscription_ui_flow = original

            evidence = raised.exception.evidence
            self.assertEqual(evidence["source_subscription_ui"]["playwright"]["returncode"], 1)
            self.assertIn("ui stderr", str(raised.exception))
            result_payload = wiki_crawler_e2e_evaluator._blocked_result(str(raised.exception), evidence)
            scenario_results = {
                scenario["scenario_id"]: scenario
                for scenario in result_payload["scenario_results"]
            }
            self.assertIn(
                "source-subscriptions-ui/source-subscriptions-live.json",
                scenario_results["source-subscriptions-user-flow"]["evidence"],
            )

    def test_evaluator_helper_runs_workflow_and_writes_pass_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            result = subprocess.run(
                [
                    "python3",
                    "scripts/wiki_crawler_e2e_evaluator.py",
                    "--repo-root",
                    ".",
                    "--output-dir",
                    str(output_dir),
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            result_payload = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(result_payload["status"], "pass")
            scenario_results = {
                scenario["scenario_id"]: scenario
                for scenario in result_payload["scenario_results"]
            }
            self.assertEqual(scenario_results["wiki-crawler-e2e-user-flow"]["status"], "pass")
            self.assertEqual(scenario_results["source-subscriptions-user-flow"]["status"], "pass")
            self.assertEqual(scenario_results["domain-channels-live-user-flow"]["status"], "pass")
            self.assertTrue((output_dir / "summary.md").exists())
            self.assertTrue((output_dir / "evidence.json").exists())

            evidence = json.loads((output_dir / "evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["fetch_result"]["changed_count"], 1)
            self.assertEqual(evidence["ingest_task"]["status"], "succeeded")
            self.assertTrue(evidence["raw_paths"])
            self.assertTrue(evidence["wiki_pages"])
            self.assertEqual(evidence["domain_validate"]["returncode"], 0)
            self.assertEqual(evidence["full_validate"]["returncode"], 0)
            self.assertEqual(evidence["source_subscription_ui"]["playwright"]["returncode"], 0)
            self.assertEqual(evidence["domain_channel_api"]["secret_configured"], True)
            self.assertEqual(evidence["domain_channel_api"]["probe_history_count"], 1)
            self.assertEqual(evidence["domain_channel_ui"]["playwright"]["returncode"], 0)
            self.assertTrue(evidence["secret_plaintext_scan"]["passed"])
            self.assertTrue((output_dir / evidence["source_subscription_ui"]["json_report"]).exists())
            self.assertTrue((output_dir / evidence["source_subscription_ui"]["report_dir"]).exists())
            self.assertTrue((output_dir / evidence["domain_channel_ui"]["json_report"]).exists())
            self.assertTrue((output_dir / evidence["domain_channel_ui"]["report_dir"]).exists())
            for evidence_path in [*evidence["raw_paths"], *evidence["wiki_pages"]]:
                self.assertTrue((output_dir / evidence_path).exists(), evidence_path)

    def test_evaluator_helper_is_repeatable_for_same_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "out"
            command = [
                "python3",
                "scripts/wiki_crawler_e2e_evaluator.py",
                "--repo-root",
                ".",
                "--output-dir",
                str(output_dir),
            ]

            first = subprocess.run(command, capture_output=True, text=True, check=False)
            second = subprocess.run(command, capture_output=True, text=True, check=False)

            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertEqual(second.returncode, 0, second.stderr)
            result_payload = json.loads((output_dir / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(result_payload["status"], "pass")


if __name__ == "__main__":
    unittest.main()
