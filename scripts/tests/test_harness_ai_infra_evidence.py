import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from scripts.harness_ai_infra_evidence import (
    canonicalize_url,
    check_service_availability,
    identity_key_for_candidate,
    validate_required_evidence_manifest,
    validate_gap_proof_payload,
)


class HarnessAiInfraEvidenceTests(unittest.TestCase):
    def test_canonicalize_url_normalizes_tracking_noise_and_case(self) -> None:
        self.assertEqual(
            canonicalize_url("HTTPS://Docs.VLLM.AI/en/latest/foo/?utm_source=x#section"),
            "https://docs.vllm.ai/en/latest/foo/#section",
        )

    def test_identity_key_for_candidate_normalizes_supported_sources(self) -> None:
        self.assertEqual(
            identity_key_for_candidate(
                {
                    "source_type": "github_issue",
                    "owner": "kubernetes",
                    "repo": "kubernetes",
                    "number": 123,
                }
            ),
            "github:kubernetes/kubernetes#123",
        )
        self.assertEqual(
            identity_key_for_candidate({"source_type": "paper", "arxiv_id": "2401.01234v2"}),
            "arxiv:2401.01234",
        )
        self.assertEqual(
            identity_key_for_candidate(
                {
                    "source_type": "hardware",
                    "vendor": "NVIDIA",
                    "model": "H200 SXM",
                    "sku_or_memory_variant": "141GB",
                }
            ),
            "hardware:nvidia:h200-sxm:141gb",
        )

    def test_validate_gap_proof_requires_duplicate_checks(self) -> None:
        findings = validate_gap_proof_payload({})

        self.assertIn("missing task_id", findings)
        self.assertIn("missing layer", findings)
        self.assertIn("missing candidate.title", findings)
        self.assertIn("missing candidate.source_type", findings)
        self.assertIn("missing candidate.identity_key", findings)
        self.assertIn("missing local_checks.raw_manifest_scan", findings)
        self.assertIn("missing local_checks.wiki_search", findings)
        self.assertIn("missing local_checks.domain_index_scan", findings)
        self.assertIn("missing gap_reason", findings)
        self.assertIn("planned_outputs must be a non-empty list", findings)

    def test_required_evidence_manifest_blocks_missing_items(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "gap-proofs" / "task.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text("{}", encoding="utf-8")

            findings = validate_required_evidence_manifest(
                [
                    "gap proof with duplicate checks before each task",
                    "service availability evidence for crawler backend, crawler frontend, and loop dashboard during each round",
                ],
                {
                    "items": [
                        {
                            "evidence_id": "gap-proof",
                            "status": "pass",
                            "summary": "gap proof validated",
                            "artifacts": [".codex/loop-runs/demo/gap-proofs/task.json"],
                        }
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertTrue(
                any("service availability evidence" in finding for finding in findings),
                findings,
            )

    def test_required_evidence_manifest_accepts_stable_evidence_id_aliases(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)

            aliases = [
                ("confirmed-preflight", "artifacts/confirmed-preflight.json"),
                ("policy-run-limits", "artifacts/policy-run-limits.json"),
                ("gap-proof", "gap-proofs/demo-task.json"),
                ("service-availability", "artifacts/service-availability.json"),
                ("search-api-visibility", "artifacts/search-api-visibility.json"),
            ]
            for _, relative_path in aliases:
                artifact_path = run_dir / relative_path
                artifact_path.parent.mkdir(parents=True, exist_ok=True)
                artifact_path.write_text("{}", encoding="utf-8")

            findings = validate_required_evidence_manifest(
                [
                    "confirmed ai_infra autonomous expansion preflight",
                    "policy_file and expanded limits recorded in run.json",
                    "gap proof with duplicate checks before each task",
                    "service availability evidence for crawler backend, crawler frontend, and loop dashboard during each round",
                    "search API visibility after ingestion",
                ],
                {
                    "items": [
                        {
                            "evidence_id": evidence_id,
                            "status": "pass",
                            "summary": "validated",
                            "artifacts": [relative_path],
                        }
                        for evidence_id, relative_path in aliases
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertEqual(findings, [])

    def test_required_evidence_manifest_reports_non_object_entries(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "confirmed-preflight.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text("{}", encoding="utf-8")

            findings = validate_required_evidence_manifest(
                ["confirmed ai_infra autonomous expansion preflight"],
                {
                    "items": [
                        "not-an-object",
                        {
                            "evidence_id": "confirmed-preflight",
                            "status": "pass",
                            "summary": "preflight captured",
                            "artifacts": ["artifacts/confirmed-preflight.json"],
                        },
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertIn("required-evidence-manifest.json items[0] must be an object", findings)

    def test_required_evidence_manifest_blocks_missing_service_availability_alias(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)

            for relative_path in ("gap-proofs/demo-task.json", "artifacts/unrelated.json"):
                artifact_path = run_dir / relative_path
                artifact_path.parent.mkdir(parents=True, exist_ok=True)
                artifact_path.write_text("{}", encoding="utf-8")

            findings = validate_required_evidence_manifest(
                [
                    "gap proof with duplicate checks before each task",
                    "service availability evidence for crawler backend, crawler frontend, and loop dashboard during each round",
                ],
                {
                    "items": [
                        {
                            "evidence_id": "gap-proof",
                            "status": "pass",
                            "summary": "validated",
                            "artifacts": ["gap-proofs/demo-task.json"],
                        },
                        {
                            "evidence_id": "link-probe",
                            "status": "pass",
                            "summary": "service availability evidence captured elsewhere",
                            "artifacts": ["artifacts/unrelated.json"],
                        },
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertIn(
                "missing required evidence manifest item for: service availability evidence for crawler backend, crawler frontend, and loop dashboard during each round",
                findings,
            )

    def test_required_evidence_manifest_blocks_prose_slug_evidence_id_for_known_requirement(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)

            artifact_path = run_dir / "artifacts" / "service-availability.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text("{}", encoding="utf-8")

            requirement = (
                "service availability evidence for crawler backend, crawler frontend, "
                "and loop dashboard during each round"
            )
            findings = validate_required_evidence_manifest(
                [requirement],
                {
                    "items": [
                        {
                            "evidence_id": (
                                "service-availability-evidence-for-crawler-backend-"
                                "crawler-frontend-and-loop-dashboard-during-each-round"
                            ),
                            "status": "pass",
                            "summary": "validated",
                            "artifacts": ["artifacts/service-availability.json"],
                        }
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertIn(
                f"missing required evidence manifest item for: {requirement}",
                findings,
            )

    def test_check_service_availability_records_http_status(self) -> None:
        class _Response:
            def __init__(self, status: int) -> None:
                self.status = status

            def __enter__(self) -> "_Response":
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        with patch("scripts.harness_ai_infra_evidence.urlopen", return_value=_Response(204)):
            result = check_service_availability(
                [
                    {"service": "crawler backend", "url": "http://127.0.0.1:8765/api/health"},
                ]
            )

        self.assertEqual(result["overall_status"], "pass")
        self.assertEqual(
            result["services"],
            [
                {
                    "service": "crawler backend",
                    "url": "http://127.0.0.1:8765/api/health",
                    "status": "pass",
                    "http_status": 204,
                    "error": "",
                }
            ],
        )

    def test_check_service_availability_returns_fail_result_for_http_error(self) -> None:
        with patch(
            "scripts.harness_ai_infra_evidence.urlopen",
            side_effect=HTTPError("http://127.0.0.1:8765/api/health", 500, "Internal Server Error", hdrs=None, fp=None),
        ):
            result = check_service_availability(
                [{"service": "crawler backend", "url": "http://127.0.0.1:8765/api/health"}]
            )

        self.assertEqual(result["overall_status"], "fail")
        self.assertEqual(result["services"][0]["status"], "fail")
        self.assertEqual(result["services"][0]["http_status"], 500)
        self.assertIn("500", result["services"][0]["error"])

    def test_check_service_availability_returns_fail_result_for_unreachable_service(self) -> None:
        with patch(
            "scripts.harness_ai_infra_evidence.urlopen",
            side_effect=URLError("connection refused"),
        ):
            result = check_service_availability(
                [{"service": "loop dashboard", "url": "http://127.0.0.1:8766/api/health"}]
            )

        self.assertEqual(result["overall_status"], "fail")
        self.assertEqual(result["services"][0]["status"], "fail")
        self.assertIsNone(result["services"][0]["http_status"])
        self.assertIn("connection refused", result["services"][0]["error"])
