import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class WikiCrawlerE2EEvaluatorTests(unittest.TestCase):
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
            self.assertEqual(result_payload["scenario_results"][0]["scenario_id"], "wiki-crawler-e2e-user-flow")
            self.assertEqual(result_payload["scenario_results"][0]["status"], "pass")
            self.assertTrue((output_dir / "summary.md").exists())
            self.assertTrue((output_dir / "evidence.json").exists())

            evidence = json.loads((output_dir / "evidence.json").read_text(encoding="utf-8"))
            self.assertEqual(evidence["fetch_result"]["changed_count"], 1)
            self.assertEqual(evidence["ingest_task"]["status"], "succeeded")
            self.assertTrue(evidence["raw_paths"])
            self.assertTrue(evidence["wiki_pages"])
            self.assertEqual(evidence["domain_validate"]["returncode"], 0)
            self.assertEqual(evidence["full_validate"]["returncode"], 0)

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
