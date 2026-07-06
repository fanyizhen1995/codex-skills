import json
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

TRUSTED_EVIDENCE_CREATED_BY = "harness_loop_orchestrator"


class HarnessAiInfraEvidenceTests(unittest.TestCase):
    def _service_availability_payload(
        self,
        *,
        statuses: dict[str, tuple[str, int | None]],
        synthetic_smoke: bool = False,
    ) -> dict:
        payload = {
            "overall_status": "pass"
            if all(
                status == "pass" and isinstance(http_status, int) and 200 <= http_status < 400
                for status, http_status in statuses.values()
            )
            else "fail",
            "services": [
                {
                    "service": service,
                    "url": f"http://127.0.0.1/{service}",
                    "status": status,
                    "http_status": http_status,
                    "error": "" if status == "pass" else "service unavailable",
                }
                for service, (status, http_status) in statuses.items()
            ],
        }
        if synthetic_smoke:
            payload["synthetic_smoke"] = True
        return payload

    def _freshness_payload(
        self,
        *,
        status: str,
        evidence_id: str = "crawler-workbench-freshness",
        synthetic_smoke: bool = False,
        details: dict[str, object] | None = None,
    ) -> dict:
        payload = {
            "status": status,
            "summary": "freshness verified" if status == "pass" else "freshness blocked",
            "details": details or self._valid_freshness_details(evidence_id),
        }
        if synthetic_smoke:
            payload["synthetic_smoke"] = True
        return payload

    def _valid_freshness_details(self, evidence_id: str) -> dict[str, object]:
        if evidence_id == "crawler-workbench-freshness":
            return {
                "sources": {"status": "pass"},
                "channels": {"status": "pass"},
                "queue": {"status": "pass"},
                "wiki": {"status": "pass"},
                "search": {"status": "pass"},
            }
        return {
            "current_run": {"status": "pass"},
            "child_tasks": {"status": "pass"},
            "agent_actions": {"status": "pass"},
            "evaluator_scenarios": {"status": "pass"},
            "completed_history": {"status": "pass"},
        }

    def _search_visibility_payload(
        self,
        *,
        status: str,
        query: str = "vllm runtime",
        visible_results: int = 1,
        synthetic_smoke: bool = False,
    ) -> dict:
        payload = {
            "status": status,
            "query": query,
            "visible_results": visible_results,
        }
        if synthetic_smoke:
            payload["synthetic_smoke"] = True
        return payload

    def _frontend_visibility_payload(
        self,
        *,
        status: str,
        page_url: str = "http://127.0.0.1:5173/wiki",
        visible_text: list[str] | None = None,
        synthetic_smoke: bool = False,
    ) -> dict:
        payload = {
            "status": status,
            "page_url": page_url,
            "visible_text": visible_text or ["AI infra runtime smoke"],
        }
        if synthetic_smoke:
            payload["synthetic_smoke"] = True
        return payload

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
                ("crawler-workbench-freshness", "artifacts/crawler-workbench-freshness.json"),
                ("loop-dashboard-freshness", "artifacts/loop-dashboard-freshness.json"),
                ("search-api-visibility", "artifacts/search-api-visibility.json"),
                ("frontend-visibility", "artifacts/frontend-visibility.json"),
            ]
            for evidence_id, relative_path in aliases:
                artifact_path = run_dir / relative_path
                artifact_path.parent.mkdir(parents=True, exist_ok=True)
                if evidence_id == "service-availability":
                    artifact_path.write_text(
                        json.dumps(
                            self._service_availability_payload(
                                statuses={
                                    "crawler-backend": ("pass", 200),
                                    "crawler-frontend": ("pass", 200),
                                    "loop-dashboard": ("pass", 200),
                                }
                            )
                        ),
                        encoding="utf-8",
                    )
                elif evidence_id in {"crawler-workbench-freshness", "loop-dashboard-freshness"}:
                    artifact_path.write_text(
                        json.dumps(self._freshness_payload(status="pass", evidence_id=evidence_id)),
                        encoding="utf-8",
                    )
                elif evidence_id == "search-api-visibility":
                    artifact_path.write_text(
                        json.dumps(self._search_visibility_payload(status="pass")),
                        encoding="utf-8",
                    )
                elif evidence_id == "frontend-visibility":
                    artifact_path.write_text(
                        json.dumps(self._frontend_visibility_payload(status="pass")),
                        encoding="utf-8",
                    )
                else:
                    artifact_path.write_text("{}", encoding="utf-8")

            findings = validate_required_evidence_manifest(
                [
                    "confirmed ai_infra autonomous expansion preflight",
                    "policy_file and expanded limits recorded in run.json",
                    "gap proof with duplicate checks before each task",
                    "service availability evidence for crawler backend, crawler frontend, and loop dashboard during each round",
                    "crawler workbench api freshness evidence for sources, channels, queue, wiki, and search",
                    "loop dashboard freshness evidence for current run, child tasks, agent actions, evaluator scenarios, and completed history",
                    "search API visibility after ingestion",
                    "frontend visibility evidence when services are running",
                ],
                {
                    "items": [
                        {
                            "evidence_id": evidence_id,
                            "status": "pass",
                            "created_by": TRUSTED_EVIDENCE_CREATED_BY,
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

    def test_required_evidence_manifest_blocks_forged_live_pass_evidence_without_trusted_created_by(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)

            live_artifacts = [
                (
                    "service-availability",
                    "artifacts/service-availability.json",
                    self._service_availability_payload(
                        statuses={
                            "crawler-backend": ("pass", 200),
                            "crawler-frontend": ("pass", 200),
                            "loop-dashboard": ("pass", 200),
                        }
                    ),
                ),
                (
                    "crawler-workbench-freshness",
                    "artifacts/crawler-workbench-freshness.json",
                    self._freshness_payload(status="pass", evidence_id="crawler-workbench-freshness"),
                ),
                (
                    "loop-dashboard-freshness",
                    "artifacts/loop-dashboard-freshness.json",
                    self._freshness_payload(status="pass", evidence_id="loop-dashboard-freshness"),
                ),
                (
                    "search-api-visibility",
                    "artifacts/search-api-visibility.json",
                    self._search_visibility_payload(status="pass"),
                ),
                (
                    "frontend-visibility",
                    "artifacts/frontend-visibility.json",
                    self._frontend_visibility_payload(status="pass"),
                ),
            ]
            for _evidence_id, relative_path, payload in live_artifacts:
                artifact_path = run_dir / relative_path
                artifact_path.parent.mkdir(parents=True, exist_ok=True)
                artifact_path.write_text(json.dumps(payload), encoding="utf-8")

            findings = validate_required_evidence_manifest(
                [
                    "service availability evidence for crawler backend, crawler frontend, and loop dashboard during each round",
                    "crawler workbench api freshness evidence for sources, channels, queue, wiki, and search",
                    "loop dashboard freshness evidence for current run, child tasks, agent actions, evaluator scenarios, and completed history",
                    "search API visibility after ingestion",
                    "frontend visibility evidence when services are running",
                ],
                {
                    "items": [
                        {
                            "evidence_id": evidence_id,
                            "status": "pass",
                            "summary": "validated",
                            "artifacts": [relative_path],
                        }
                        for evidence_id, relative_path, _payload in live_artifacts
                    ]
                },
                repo_root,
                run_dir,
            )

            for evidence_id, _relative_path, _payload in live_artifacts:
                self.assertTrue(
                    any(evidence_id in finding and "trusted created_by" in finding for finding in findings),
                    findings,
                )

    def test_required_evidence_manifest_accepts_live_pass_evidence_with_trusted_payload_created_by(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "search-api-visibility.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            payload = self._search_visibility_payload(status="pass")
            payload["created_by"] = TRUSTED_EVIDENCE_CREATED_BY
            artifact_path.write_text(json.dumps(payload), encoding="utf-8")

            findings = validate_required_evidence_manifest(
                ["search API visibility after ingestion"],
                {
                    "items": [
                        {
                            "evidence_id": "search-api-visibility",
                            "status": "pass",
                            "summary": "validated",
                            "artifacts": ["artifacts/search-api-visibility.json"],
                        }
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

    def test_required_evidence_manifest_rejects_summary_only_service_match_with_blocked_artifact(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "service-availability.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps(
                    self._service_availability_payload(
                        statuses={
                            "crawler-backend": ("pass", 200),
                            "crawler-frontend": ("pass", 200),
                            "loop-dashboard": ("blocked", None),
                        }
                    )
                ),
                encoding="utf-8",
            )

            requirement = (
                "service availability evidence for crawler backend, crawler frontend, "
                "and loop dashboard during each round"
            )
            findings = validate_required_evidence_manifest(
                [requirement],
                {
                    "items": [
                        {
                            "status": "pass",
                            "summary": requirement,
                            "artifacts": ["artifacts/service-availability.json"],
                        }
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertTrue(
                any("service-availability artifact" in finding for finding in findings),
                findings,
            )
            self.assertIn(
                f"missing required evidence manifest item for: {requirement}",
                findings,
            )

    def test_required_evidence_manifest_blocks_service_availability_placeholder_payload(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "service-availability.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text("{}", encoding="utf-8")

            findings = validate_required_evidence_manifest(
                [
                    "service availability evidence for crawler backend, crawler frontend, and loop dashboard during each round",
                ],
                {
                    "items": [
                        {
                            "evidence_id": "service-availability",
                            "status": "pass",
                            "summary": "validated",
                            "artifacts": ["artifacts/service-availability.json"],
                        }
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertTrue(
                any("service-availability artifact" in finding for finding in findings),
                findings,
            )

    def test_required_evidence_manifest_blocks_non_pass_live_gate_status(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "service-availability.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps(
                    self._service_availability_payload(
                        statuses={
                            "crawler-backend": ("pass", 200),
                            "crawler-frontend": ("pass", 200),
                            "loop-dashboard": ("blocked", None),
                        }
                    )
                ),
                encoding="utf-8",
            )

            findings = validate_required_evidence_manifest(
                [
                    "service availability evidence for crawler backend, crawler frontend, and loop dashboard during each round",
                ],
                {
                    "items": [
                        {
                            "evidence_id": "service-availability",
                            "status": "blocked",
                            "summary": "validated",
                            "artifacts": ["artifacts/service-availability.json"],
                        }
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertTrue(
                any("service-availability has non-pass status blocked" in finding for finding in findings),
                findings,
            )

    def test_required_evidence_manifest_rejects_blocked_summary_only_fallback_match(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "unknown-evidence.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text("{}", encoding="utf-8")

            requirement = "new requirement proof for synthetic placeholder freshness"
            findings = validate_required_evidence_manifest(
                [requirement],
                {
                    "items": [
                        {
                            "status": "blocked",
                            "summary": "new requirement proof for synthetic placeholder freshness",
                            "artifacts": ["artifacts/unknown-evidence.json"],
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

    def test_required_evidence_manifest_blocks_placeholder_freshness_payloads(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)

            crawler_artifact = run_dir / "artifacts" / "crawler-workbench-freshness.json"
            crawler_artifact.parent.mkdir(parents=True, exist_ok=True)
            crawler_artifact.write_text("{}", encoding="utf-8")
            loop_artifact = run_dir / "artifacts" / "loop-dashboard-freshness.json"
            loop_artifact.write_text("{}", encoding="utf-8")

            findings = validate_required_evidence_manifest(
                [
                    "crawler workbench api freshness evidence for sources, channels, queue, wiki, and search",
                    "loop dashboard freshness evidence for current run, child tasks, agent actions, evaluator scenarios, and completed history",
                ],
                {
                    "items": [
                        {
                            "evidence_id": "crawler-workbench-freshness",
                            "status": "pass",
                            "summary": "validated",
                            "artifacts": ["artifacts/crawler-workbench-freshness.json"],
                        },
                        {
                            "evidence_id": "loop-dashboard-freshness",
                            "status": "pass",
                            "summary": "validated",
                            "artifacts": ["artifacts/loop-dashboard-freshness.json"],
                        },
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertTrue(
                any("crawler-workbench-freshness artifact" in finding for finding in findings),
                findings,
            )
            self.assertTrue(
                any("loop-dashboard-freshness artifact" in finding for finding in findings),
                findings,
            )

    def test_required_evidence_manifest_blocks_synthetic_smoke_crawler_freshness_payload(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "crawler-workbench-freshness.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps(
                    self._freshness_payload(
                        status="pass",
                        evidence_id="crawler-workbench-freshness",
                        synthetic_smoke=True,
                    )
                ),
                encoding="utf-8",
            )

            findings = validate_required_evidence_manifest(
                ["crawler workbench api freshness evidence for sources, channels, queue, wiki, and search"],
                {
                    "items": [
                        {
                            "evidence_id": "crawler-workbench-freshness",
                            "status": "pass",
                            "created_by": TRUSTED_EVIDENCE_CREATED_BY,
                            "summary": "validated",
                            "artifacts": ["artifacts/crawler-workbench-freshness.json"],
                        }
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertTrue(
                any("cannot use synthetic_smoke placeholders" in finding for finding in findings),
                findings,
            )

    def test_required_evidence_manifest_blocks_loop_dashboard_freshness_with_generic_details(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "loop-dashboard-freshness.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps(
                    self._freshness_payload(
                        status="pass",
                        evidence_id="loop-dashboard-freshness",
                        details={"checked_views": ["current-run", "child-tasks"]},
                    )
                ),
                encoding="utf-8",
            )

            findings = validate_required_evidence_manifest(
                ["loop dashboard freshness evidence for current run, child tasks, agent actions, evaluator scenarios, and completed history"],
                {
                    "items": [
                        {
                            "evidence_id": "loop-dashboard-freshness",
                            "status": "pass",
                            "created_by": TRUSTED_EVIDENCE_CREATED_BY,
                            "summary": "validated",
                            "artifacts": ["artifacts/loop-dashboard-freshness.json"],
                        }
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertTrue(
                any("must include pass details for" in finding for finding in findings),
                findings,
            )

    def test_required_evidence_manifest_accepts_crawler_freshness_with_required_dimensions(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "crawler-workbench-freshness.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps(self._freshness_payload(status="pass", evidence_id="crawler-workbench-freshness")),
                encoding="utf-8",
            )

            findings = validate_required_evidence_manifest(
                ["crawler workbench api freshness evidence for sources, channels, queue, wiki, and search"],
                {
                    "items": [
                        {
                            "evidence_id": "crawler-workbench-freshness",
                            "status": "pass",
                            "created_by": TRUSTED_EVIDENCE_CREATED_BY,
                            "summary": "validated",
                            "artifacts": ["artifacts/crawler-workbench-freshness.json"],
                        }
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertEqual(findings, [])

    def test_required_evidence_manifest_accepts_loop_dashboard_freshness_with_required_dimensions(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "loop-dashboard-freshness.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps(self._freshness_payload(status="pass", evidence_id="loop-dashboard-freshness")),
                encoding="utf-8",
            )

            findings = validate_required_evidence_manifest(
                ["loop dashboard freshness evidence for current run, child tasks, agent actions, evaluator scenarios, and completed history"],
                {
                    "items": [
                        {
                            "evidence_id": "loop-dashboard-freshness",
                            "status": "pass",
                            "created_by": TRUSTED_EVIDENCE_CREATED_BY,
                            "summary": "validated",
                            "artifacts": ["artifacts/loop-dashboard-freshness.json"],
                        }
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertEqual(findings, [])

    def test_required_evidence_manifest_blocks_empty_search_visibility_payload(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "search-api-visibility.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text("{}", encoding="utf-8")

            findings = validate_required_evidence_manifest(
                ["search API visibility after ingestion"],
                {
                    "items": [
                        {
                            "evidence_id": "search-api-visibility",
                            "status": "pass",
                            "created_by": TRUSTED_EVIDENCE_CREATED_BY,
                            "summary": "validated",
                            "artifacts": ["artifacts/search-api-visibility.json"],
                        }
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertTrue(
                any("search-api-visibility artifact" in finding for finding in findings),
                findings,
            )

    def test_required_evidence_manifest_blocks_empty_frontend_visibility_payload(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "frontend-visibility.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text("{}", encoding="utf-8")

            findings = validate_required_evidence_manifest(
                ["frontend visibility evidence when services are running"],
                {
                    "items": [
                        {
                            "evidence_id": "frontend-visibility",
                            "status": "pass",
                            "created_by": TRUSTED_EVIDENCE_CREATED_BY,
                            "summary": "validated",
                            "artifacts": ["artifacts/frontend-visibility.json"],
                        }
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertTrue(
                any("frontend-visibility artifact" in finding for finding in findings),
                findings,
            )

    def test_required_evidence_manifest_accepts_valid_search_visibility_payload(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "search-api-visibility.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps(self._search_visibility_payload(status="pass")),
                encoding="utf-8",
            )

            findings = validate_required_evidence_manifest(
                ["search API visibility after ingestion"],
                {
                    "items": [
                        {
                            "evidence_id": "search-api-visibility",
                            "status": "pass",
                            "created_by": TRUSTED_EVIDENCE_CREATED_BY,
                            "summary": "validated",
                            "artifacts": ["artifacts/search-api-visibility.json"],
                        }
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertEqual(findings, [])

    def test_required_evidence_manifest_accepts_valid_frontend_visibility_payload(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "frontend-visibility.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps(self._frontend_visibility_payload(status="pass")),
                encoding="utf-8",
            )

            findings = validate_required_evidence_manifest(
                ["frontend visibility evidence when services are running"],
                {
                    "items": [
                        {
                            "evidence_id": "frontend-visibility",
                            "status": "pass",
                            "created_by": TRUSTED_EVIDENCE_CREATED_BY,
                            "summary": "validated",
                            "artifacts": ["artifacts/frontend-visibility.json"],
                        }
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertEqual(findings, [])

    def test_required_evidence_manifest_accepts_service_availability_http_302(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "service-availability.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps(
                    self._service_availability_payload(
                        statuses={
                            "crawler-backend": ("pass", 302),
                            "crawler-frontend": ("pass", 204),
                            "loop-dashboard": ("pass", 200),
                        }
                    )
                ),
                encoding="utf-8",
            )

            findings = validate_required_evidence_manifest(
                [
                    "service availability evidence for crawler backend, crawler frontend, and loop dashboard during each round",
                ],
                {
                    "items": [
                        {
                            "evidence_id": "service-availability",
                            "status": "pass",
                            "created_by": TRUSTED_EVIDENCE_CREATED_BY,
                            "summary": "validated",
                            "artifacts": ["artifacts/service-availability.json"],
                        }
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertEqual(findings, [])

    def test_required_evidence_manifest_blocks_synthetic_smoke_service_availability_payload(self) -> None:
        with TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo"
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = run_dir / "artifacts" / "service-availability.json"
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            artifact_path.write_text(
                json.dumps(
                    self._service_availability_payload(
                        statuses={
                            "crawler-backend": ("pass", 200),
                            "crawler-frontend": ("pass", 200),
                            "loop-dashboard": ("pass", 200),
                        },
                        synthetic_smoke=True,
                    )
                ),
                encoding="utf-8",
            )

            findings = validate_required_evidence_manifest(
                [
                    "service availability evidence for crawler backend, crawler frontend, and loop dashboard during each round",
                ],
                {
                    "items": [
                        {
                            "evidence_id": "service-availability",
                            "status": "pass",
                            "summary": "validated",
                            "artifacts": ["artifacts/service-availability.json"],
                        }
                    ]
                },
                repo_root,
                run_dir,
            )

            self.assertTrue(
                any("cannot use synthetic_smoke placeholders" in finding for finding in findings),
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
        self.assertEqual(result["created_by"], TRUSTED_EVIDENCE_CREATED_BY)
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
