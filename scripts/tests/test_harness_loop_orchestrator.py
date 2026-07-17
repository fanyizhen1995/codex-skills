import io
import hashlib
import os
import shutil
import tempfile
import unittest
import json
import subprocess
from contextlib import redirect_stdout
from pathlib import Path
from typing import Mapping
from unittest.mock import patch

import pytest

import scripts.harness_loop_orchestrator as harness_loop_orchestrator
from scripts.harness_loop_contracts import (
    read_json_file,
    run_dir_for,
    validate_evaluator_result_payload,
    validate_generator_result_payload,
    validate_loop_state_payload,
    validate_planner_output_payload,
    validate_run_payload,
    write_json_file,
)
from scripts.harness_ai_infra_evidence import trusted_live_evidence_artifact_path
from scripts.tests.legacy_audit_fixtures import fake_audit_report
from scripts.harness_loop_autonomous import (
    NoActionDecision,
    check_autonomous_scope,
    create_default_loop_state,
    policy_patterns_for_run,
    write_loop_state,
)
from scripts.harness_loop_governance import classify_candidate
from scripts.harness_loop_orchestrator import (
    confirm_preflight,
    create_preflight_run,
    load_run,
    main,
    save_run,
    status_for_run,
)
from scripts.loop_supervisor.models import ActionRequest, ActionResultClass, ActionType


def run_auditor(*_args: object, **_kwargs: object) -> None:
    pytest.skip("legacy Auditor runtime was removed by Supervisor cutover")


def run_autonomous(*_args: object, **_kwargs: object) -> None:
    pytest.skip("legacy autonomous multi-round runtime was removed by Supervisor cutover")


def run_demand_multi(*_args: object, **_kwargs: object) -> None:
    pytest.skip("legacy demand multi-round runtime was removed by Supervisor cutover")


def test_public_orchestrator_parser_rejects_removed_runtime_commands() -> None:
    parser = harness_loop_orchestrator._build_parser()
    removed_commands = (
        ["run", "--run-id", "run-1", "--planner-driver", "fake", "--generator-driver", "fake", "--evaluator-driver", "fake"],
        ["run-demand-multi", "--run-id", "run-1", "--planner-driver", "fake", "--generator-driver", "fake", "--evaluator-driver", "fake"],
        ["run-autonomous", "--run-id", "run-1", "--planner-driver", "fake", "--generator-driver", "fake", "--evaluator-driver", "fake"],
        ["run-auditor", "--run-id", "run-1", "--driver", "fake"],
        ["plan", "--run-id", "run-1", "--driver", "fake"],
        ["generate", "--run-id", "run-1", "--driver", "fake"],
        ["evaluate", "--run-id", "run-1", "--driver", "fake"],
        ["artifact-hygiene", "--run-id", "run-1"],
        ["cleanup", "--run-id", "run-1"],
    )
    for command in removed_commands:
        with pytest.raises(SystemExit):
            parser.parse_args(command)

    public_bypasses = (
        "run_loop",
        "run_demand_multi",
        "run_autonomous",
        "run_auditor",
        "run_planner",
        "run_generator",
        "run_evaluator",
        "run_artifact_hygiene_step",
        "run_cleanup",
        "run_bounded_planner",
        "run_bounded_generator",
        "run_bounded_evaluator",
        "run_bounded_artifact_hygiene",
        "run_bounded_commit",
        "run_bounded_push",
        "run_bounded_cleanup",
    )
    assert all(not hasattr(harness_loop_orchestrator, name) for name in public_bypasses)


def test_skill_invocation_prompt_names_canonical_hash_field_and_format() -> None:
    prompt = harness_loop_orchestrator._skill_invocation_prompt("run-1", "planner")

    assert 'artifact_sha256 with value "sha256:<64 lowercase hex>"' in prompt
    assert "include invocation_id, skill_path, artifact_path, and artifact_sha256" in prompt
    assert "Only report repository-owned skill files" in prompt
    assert "repo-relative POSIX path" in prompt
    assert "Do not report skills under ~/.codex" in prompt


def test_policy_patterns_allow_exact_auto_remediation_harness_paths_from_reviewer_directive() -> None:
    run = {
        "domain": "ai_infra",
        "allowed_paths": [
            "personal-wiki/domains/**/wiki/**",
            "personal-wiki/domains/**/raw/**",
        ],
        "denylist_paths": [".env", "**/.env"],
        "manual_confirm_paths": ["tasks.json", "progress.md", "docs/**", "scripts/**"],
        "reviewer_directives": [{"decision": "auto_remediate"}],
    }
    changed_paths = [
        "scripts/harness_loop_autonomous.py",
        "scripts/harness_loop_orchestrator.py",
        "scripts/loop_supervisor/recovery.py",
        "scripts/tests/test_harness_loop_orchestrator.py",
        "scripts/tests/test_harness_loop_supervisor_recovery.py",
        "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
    ]

    allowed, denied, manual = policy_patterns_for_run(run, domain="ai_infra")
    scope = check_autonomous_scope(changed_paths, allowed, denied, manual)

    assert scope.allowed, scope.findings
    assert sorted(scope.allowed_paths) == sorted(changed_paths)


def write_fake_evaluator_scenario(repo_root: Path, task_id: str) -> Path:
    scenario_dir = repo_root / "docs" / "harness" / "evaluator-scenarios"
    scenario_dir.mkdir(parents=True, exist_ok=True)
    scenario_path = scenario_dir / f"{task_id}.json"
    scenario_path.write_text(
        json.dumps(
            {
                "task_id": task_id,
                "must_simulate": True,
                "user_scenarios": [
                    {
                        "scenario_id": "EUS-01",
                        "user_goal": "Exercise the synthetic evaluator loop.",
                        "prerequisites": ["Temporary repository exists."],
                        "entrypoint": "python3 -c \"print('scenario-ok')\"",
                        "steps": ["Run the fake evaluator task loop."],
                        "expected_outcomes": ["Fake evaluator records a pass result."],
                        "failure_signals": ["Fake evaluator result is missing."],
                        "cleanup": ["TemporaryDirectory cleanup removes generated files."],
                        "automation_hint": "manual",
                    }
                ],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return scenario_path


def call_cli(argv: list[str]) -> int:
    with patch.dict(os.environ, {"HARNESS_LEGACY_MULTI_ROUND_TEST_COMPAT": "1"}):
        with redirect_stdout(io.StringIO()):
            return main(argv)


def remove_fake_evaluator_attempts(eval_dir: Path) -> None:
    for attempt_dir in eval_dir.glob("fake-attempt-*"):
        if attempt_dir.is_dir():
            shutil.rmtree(attempt_dir, ignore_errors=True)
    try:
        eval_dir.rmdir()
    except OSError:
        pass


def remove_empty_directory(path: Path) -> None:
    try:
        path.rmdir()
    except OSError:
        pass


def init_git_repo(repo_root: Path) -> None:
    subprocess.run(["git", "init"], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(
        ["git", "config", "user.email", "codex@example.invalid"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    subprocess.run(
        ["git", "config", "user.name", "Codex"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    (repo_root / "README.md").write_text("temporary repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(
        ["git", "commit", "-m", "test: initial"],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def commit_seeded_autonomous_state(repo_root: Path, domain: str) -> None:
    if not (repo_root / ".git").exists():
        return
    loop_runs_root = repo_root / ".codex" / "loop-runs"
    if not loop_runs_root.exists():
        return
    loop_state = f"personal-wiki/domains/{domain}/loop-state.json"
    coverage_map = f"personal-wiki/domains/{domain}/coverage-map.json"
    subprocess.run(
        ["git", "add", "--", loop_state, coverage_map],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    status = subprocess.run(
        ["git", "diff", "--cached", "--quiet", "--", loop_state, coverage_map],
        cwd=repo_root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if status.returncode == 0:
        return
    subprocess.run(
        ["git", "commit", "-m", f"test: seed {domain} autonomous state", "--", loop_state, coverage_map],
        cwd=repo_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def seed_no_action_loop_state(repo_root: Path, domain: str) -> dict[str, object]:
    state = create_default_loop_state(domain, "Expand wiki")
    state["candidate_backlog"] = []
    state["coverage_gaps"] = []
    state["known_sources"] = [
        {
            "id": "src-1",
            "title": "Source",
            "source": "manual",
            "status": "scanned",
            "updated_at": state["last_scan_at"],
            "evidence": ["checked"],
        }
    ]
    state["no_action_evidence"] = [
        {
            "id": "scan-1",
            "title": "Scan",
            "source": "coverage-map",
            "status": "complete",
            "updated_at": state["last_scan_at"],
            "evidence": ["coverage-map scan confirmed no candidates"],
        }
    ]
    write_loop_state(repo_root, domain, state)
    write_json_file(
        repo_root / "personal-wiki" / "domains" / domain / "coverage-map.json",
        {
            "domain": domain,
            "domain_goal": state["domain_goal"],
            "layers": {
                layer: {
                    "status": "covered",
                    "covered_pages": [f"wiki/{layer}.md"],
                    "raw_evidence": [f"raw/{layer}.json"],
                    "candidate_gaps": [],
                    "blocked_reason": "",
                    "last_scanned_at": state["last_scan_at"],
                    "notes": "",
                }
                for layer in (
                    "training-distributed",
                    "inference-runtime",
                    "orchestration-scheduling",
                    "data-rag-vector",
                    "eval-observability-reliability",
                    "security-governance-cost",
                    "hardware-accelerator",
                    "network-storage-cluster",
                )
            },
        },
    )
    commit_seeded_autonomous_state(repo_root, domain)
    return state


def seed_candidate_loop_state(repo_root: Path, domain: str) -> dict[str, object]:
    state = create_default_loop_state(domain, "Expand wiki")
    state["known_sources"] = [
        {
            "id": "src-1",
            "title": "Source",
            "source": "manual",
            "status": "scanned",
            "updated_at": state["last_scan_at"],
            "evidence": ["checked"],
        }
    ]
    state["candidate_backlog"] = [
        {
            "id": "candidate-1",
            "title": "Capture synthetic source",
            "source": "planner",
            "status": "pending",
            "updated_at": state["last_scan_at"],
            "evidence": ["seeded candidate"],
        }
    ]
    write_loop_state(repo_root, domain, state)
    write_json_file(
        repo_root / "personal-wiki" / "domains" / domain / "coverage-map.json",
        {
            "domain": domain,
            "domain_goal": state["domain_goal"],
            "layers": {
                layer: {
                    "status": "covered",
                    "covered_pages": [f"wiki/{layer}.md"],
                    "raw_evidence": [f"raw/{layer}.json"],
                    "candidate_gaps": [],
                    "blocked_reason": "",
                    "last_scanned_at": state["last_scan_at"],
                    "notes": "",
                }
                for layer in (
                    "training-distributed",
                    "inference-runtime",
                    "orchestration-scheduling",
                    "data-rag-vector",
                    "eval-observability-reliability",
                    "security-governance-cost",
                    "hardware-accelerator",
                    "network-storage-cluster",
                )
            },
        },
    )
    commit_seeded_autonomous_state(repo_root, domain)
    return state


def seed_open_must_fix_audit(repo_root: Path, run_id: str) -> None:
    run_dir = run_dir_for(repo_root, run_id)
    signal_path = run_dir / "deterministic-signals.json"
    write_json_file(
        signal_path,
        {
            "schema_version": 1,
            "run_id": run_id,
            "computed_at": "2026-07-08T00:00:00Z",
            "created_by": "harness_loop_orchestrator",
            "summary": {"same_evaluator_finding_count": 2},
        },
    )
    report = fake_audit_report(
        run_id=run_id,
        audit_id="audit-001",
        signals=read_json_file(signal_path),
        signal_artifact_path=signal_path.relative_to(repo_root).as_posix(),
        signal_artifact_sha256=hashlib.sha256(signal_path.read_bytes()).hexdigest(),
    )
    write_json_file(run_dir / "audit-reports" / "audit-001.json", report)


class HarnessLoopOrchestratorTests(unittest.TestCase):
    def test_audit_cadence_carries_completed_parent_across_continuation(self) -> None:
        run = {
            "policy": "autonomous_knowledge",
            "run_kind": "single",
            "_autonomous_completed_task_ids": ["continuation-task-1"],
            "audit_cadence": {"unit": "parent_task", "mode": "fixed_interval", "interval": 2},
            "_audit_cadence_state": {
                "last_audited_progress_count": 0,
                "carried_completed_since_last_audit": 1,
            },
        }

        self.assertEqual(harness_loop_orchestrator._audit_steps_since_last_audit(run), 2)
        self.assertTrue(harness_loop_orchestrator._audit_cadence_due(run, force=False))

    def test_publish_freshness_target_is_idempotent_and_binds_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_id = "freshness-run"
            run_dir = run_dir_for(repo_root, run_id)
            evidence_dir = run_dir / "trusted-live-evidence"
            evidence_dir.mkdir(parents=True)
            for name in ("crawler-workbench-freshness", "frontend-visibility", "search-api-visibility"):
                write_json_file(
                    evidence_dir / f"{name}.json",
                    {
                        "status": "pass",
                        "run_id": run_id,
                        "task_id": "freshness-run-task-1",
                        "captured_at": "2026-07-10T00:00:00Z",
                        "summary": f"{name} passed",
                    },
                )
            run = {
                "run_id": run_id,
                "task_id": "freshness-run-task-1",
                "domain": "ai_infra",
                "trusted_live_evidence_state": {
                    name: {
                        "artifact_path": f"trusted-live-evidence/{name}.json",
                        "sha256": hashlib.sha256((evidence_dir / f"{name}.json").read_bytes()).hexdigest(),
                        "created_by": "harness_loop_orchestrator",
                    }
                    for name in ("crawler-workbench-freshness", "frontend-visibility", "search-api-visibility")
                },
            }
            generator = {
                "changed_paths": [
                    "personal-wiki/domains/ai_infra/wiki/references/example.md",
                    "personal-wiki/domains/ai_infra/raw/crawler/example.md",
                ]
            }

            first = harness_loop_orchestrator._publish_supervisor_freshness_target(
                repo_root, run, generator, "a" * 40
            )
            second = harness_loop_orchestrator._publish_supervisor_freshness_target(
                repo_root, run, generator, "a" * 40
            )

            targets = (repo_root / ".codex" / "supervisor" / "freshness-targets.jsonl").read_text(
                encoding="utf-8"
            ).splitlines()
            self.assertEqual(first["target_commit"], "a" * 40)
            self.assertEqual(first["status"], "pass")
            self.assertEqual(first["wiki_paths"], ["personal-wiki/domains/ai_infra/wiki/references/example.md"])
            self.assertEqual(second["target_id"], first["target_id"])
            self.assertEqual(len(targets), 1)

    def test_push_autonomous_commit_pushes_origin_main_and_records_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            repo_root = root / "repo"
            remote = root / "origin.git"
            repo_root.mkdir()
            init_git_repo(repo_root)
            subprocess.run(["git", "branch", "-M", "main"], cwd=repo_root, check=True, capture_output=True)
            subprocess.run(["git", "init", "--bare", str(remote)], check=True, capture_output=True)
            subprocess.run(["git", "remote", "add", "origin", str(remote)], cwd=repo_root, check=True)
            run_id = "push-run"
            run_dir_for(repo_root, run_id).mkdir(parents=True)
            note = repo_root / "note.md"
            note.write_text("push me\n", encoding="utf-8")
            subprocess.run(["git", "add", "note.md"], cwd=repo_root, check=True)
            subprocess.run(["git", "commit", "-m", "test: push"], cwd=repo_root, check=True, capture_output=True)
            commit_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, text=True, capture_output=True
            ).stdout.strip()

            result = harness_loop_orchestrator._push_autonomous_commit(
                repo_root,
                {"run_id": run_id, "task_id": "push-task", "branch": "main"},
                commit_sha,
            )

            self.assertEqual(result["status"], "pass")
            self.assertEqual(result["remote"], "origin")
            self.assertEqual(result["branch"], "main")
            self.assertEqual(result["commit"], commit_sha)
            self.assertEqual(result["run_id"], run_id)
            self.assertEqual(result["task_id"], "push-task")
            persisted = read_json_file(run_dir_for(repo_root, run_id) / "push-result.json")
            self.assertEqual(persisted["status"], "pass")
            self.assertEqual(persisted["run_id"], run_id)
            self.assertEqual(persisted["task_id"], "push-task")
            remote_head = subprocess.run(
                ["git", "--git-dir", str(remote), "rev-parse", "refs/heads/main"],
                check=True,
                text=True,
                capture_output=True,
            ).stdout.strip()
            self.assertEqual(remote_head, commit_sha)

    def test_push_autonomous_main_commit_without_origin_is_retryable_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            subprocess.run(["git", "branch", "-M", "main"], cwd=repo_root, check=True, capture_output=True)
            run_id = "push-without-origin"
            run_dir_for(repo_root, run_id).mkdir(parents=True)
            commit_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, text=True, capture_output=True
            ).stdout.strip()

            result = harness_loop_orchestrator._push_autonomous_commit(
                repo_root, {"run_id": run_id, "branch": "main"}, commit_sha
            )

            self.assertEqual(result["status"], "fail")
            self.assertIn("origin remote is not configured", result["error"])

    def test_publish_freshness_target_rejects_untrusted_pass_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_id = "untrusted-freshness-run"
            evidence_dir = run_dir_for(repo_root, run_id) / "trusted-live-evidence"
            evidence_dir.mkdir(parents=True)
            for name in ("crawler-workbench-freshness", "search-api-visibility", "frontend-visibility"):
                write_json_file(evidence_dir / f"{name}.json", {"status": "pass"})

            target = harness_loop_orchestrator._publish_supervisor_freshness_target(
                repo_root,
                {"run_id": run_id, "task_id": "task-1", "domain": "ai_infra"},
                {"changed_paths": ["personal-wiki/domains/ai_infra/wiki/references/example.md"]},
                "b" * 40,
            )

            self.assertEqual(target["status"], "fail")
            self.assertEqual({item["status"] for item in target["evidence"]}, {"untrusted"})

    def test_completed_continuation_task_advances_semantic_parent_counter(self) -> None:
        run = {
            "task_id": "continuation-task-1",
            "parent_task_counter": 17,
            "semantic_parent_task_next": 18,
            "_autonomous_completed_task_ids": [],
        }

        harness_loop_orchestrator._record_completed_autonomous_task(run)

        self.assertEqual(run["parent_task_counter"], 18)
        self.assertEqual(run["semantic_parent_task_next"], 19)
        self.assertEqual(harness_loop_orchestrator._semantic_parent_task_number(run), 19)

    REQUIRED_EVIDENCE_STABLE_IDS = {
        "confirmed ai_infra autonomous expansion preflight": "confirmed-preflight",
        "policy_file and expanded limits recorded in run.json": "policy-run-limits",
        "gap proof with duplicate checks before each task": "gap-proof",
        "validated ai_infra coverage-map evidence for all required layers": "coverage-map",
        "domain loop-state.json with coverage evidence": "loop-state",
        "raw evidence or existing raw reuse evidence": "raw-evidence",
        "curated wiki source_refs": "curated-wiki-source-refs",
        "wiki validate --domain ai_infra result": "wiki-validate",
        "search/api visibility evidence for new knowledge": "search-api-visibility",
        "frontend visibility evidence when services are running": "frontend-visibility",
        "crawler workbench api freshness evidence for sources, channels, queue, wiki, and search": "crawler-workbench-freshness",
        "domain channels evidence for new or changed crawler source subscriptions": "domain-channels",
        "loop dashboard freshness evidence for current run, child tasks, agent actions, evaluator scenarios, and completed history": "loop-dashboard-freshness",
        "service availability evidence for crawler backend, crawler frontend, and loop dashboard during each round": "service-availability",
        "link probe or blocked/auth evidence for new external sources": "link-probe",
        "secret scan evidence for changed paths": "secret-scan",
        "code test evidence when crawler/harness/frontend/backend changes": "code-tests",
        "autonomous-scope-result.json": "autonomous-scope-result",
        "supply-chain-result.json for dependency changes": "supply-chain-result",
        "commit-result.json": "commit-result",
        "fresh no-action evidence before stopped_no_action": "no-action-evidence",
    }

    def _seed_policy_fixture(self, repo_root: Path, relative_path: str) -> str:
        source_root = Path(__file__).resolve().parents[2]
        payload = read_json_file(source_root / relative_path)
        write_json_file(repo_root / relative_path, payload)
        return relative_path

    def _valid_gap_proof_payload(self, task_id: str) -> dict[str, object]:
        return {
            "task_id": task_id,
            "layer": "inference-runtime",
            "candidate": {
                "title": "Synthetic gap proof candidate",
                "source_type": "docs",
                "identity_key": "url:https://example.invalid/docs/gap-proof",
            },
            "local_checks": {
                "raw_manifest_scan": "No matching raw manifest entries found.",
                "wiki_search": "No matching wiki content found.",
                "domain_index_scan": "No matching domain index content found.",
            },
            "gap_reason": "Synthetic autonomous coverage gap for orchestrator testing.",
            "planned_outputs": ["personal-wiki/domains/ai_infra/raw/synthetic-gap-proof.md"],
        }

    def _valid_service_availability_payload(self) -> dict[str, object]:
        return {
            "overall_status": "pass",
            "created_by": "harness_loop_orchestrator",
            "services": [
                {
                    "service": "crawler-backend",
                    "url": "http://127.0.0.1:8765/api/health",
                    "status": "pass",
                    "http_status": 200,
                    "error": "",
                },
                {
                    "service": "crawler-frontend",
                    "url": "http://127.0.0.1:5173/",
                    "status": "pass",
                    "http_status": 200,
                    "error": "",
                },
                {
                    "service": "loop-dashboard",
                    "url": "http://127.0.0.1:8766/api/health",
                    "status": "pass",
                    "http_status": 200,
                    "error": "",
                },
            ],
        }

    def _valid_freshness_payload(self, evidence_id: str) -> dict[str, object]:
        details: dict[str, object]
        if evidence_id == "crawler-workbench-freshness":
            details = {
                "sources": {"status": "pass"},
                "channels": {"status": "pass"},
                "queue": {"status": "pass"},
                "wiki": self._valid_search_visibility_payload(),
                "search": self._valid_search_visibility_payload(),
            }
        else:
            details = {
                "current_run": {
                    "status": "pass",
                    "http_status": 200,
                    "json": {
                        "run_id": "expanded-run",
                        "project_root": "/tmp/current-project",
                        "source_path": ".worktrees/ai-infra-meta-loop-runtime/.codex/loop-runs/expanded-run",
                    },
                },
                "child_tasks": {
                    "status": "pass",
                    "http_status": 200,
                    "json": {
                        "run_id": "expanded-run",
                        "project_root": "/tmp/current-project",
                        "source_path": ".worktrees/ai-infra-meta-loop-runtime/.codex/loop-runs/expanded-run",
                        "children": [],
                        "child_run_ids": [],
                        "current_child_run_id": "",
                    },
                },
                "agent_actions": {"status": "pass", "http_status": 200, "json": {"run_id": "expanded-run", "events": []}},
                "evaluator_scenarios": {"status": "pass", "http_status": 200, "json": {"run_id": "expanded-run", "logs": []}},
                "completed_history": {"status": "pass", "http_status": 200, "json": [{"run_id": "expanded-run"}]},
                "project": {"status": "pass", "http_status": 200, "json": {"project_root": "/tmp/current-project"}},
            }
        payload = {
            "status": "pass",
            "created_by": "harness_loop_orchestrator",
            "summary": f"{evidence_id} captured",
            "details": details,
        }
        if evidence_id in {"crawler-workbench-freshness", "loop-dashboard-freshness"}:
            payload["run_id"] = "expanded-run"
            payload["task_id"] = "expanded-run-task-1"
            payload["domain"] = "ai_infra"
            payload["worktree"] = "/tmp/current-project"
        return payload

    def _valid_search_visibility_payload(self) -> dict[str, object]:
        expected_target = {
            "target_id": "wiki:personal-wiki/domains/ai_infra/runtime/expanded-runtime-smoke.md",
            "kind": "wiki_page",
            "path": "personal-wiki/domains/ai_infra/runtime/expanded-runtime-smoke.md",
            "title": "Expanded Runtime Smoke",
            "query": "Expanded Runtime Smoke",
            "content_terms": ["tensorlake", "schedulerproof", "rdmawatch"],
            "content_fingerprint": "tensorlake schedulerproof rdmawatch",
        }
        return {
            "status": "pass",
            "created_by": "harness_loop_orchestrator",
            "run_id": "expanded-run",
            "task_id": "expanded-run-task-1",
            "domain": "ai_infra",
            "query": "Expanded Runtime Smoke",
            "visible_results": 1,
            "visible_items": [expected_target["path"]],
            "expected_targets": [expected_target],
            "matched_targets": [
                {
                    "target_id": expected_target["target_id"],
                    "path": expected_target["path"],
                    "title": expected_target["title"],
                    "query": expected_target["query"],
                    "matched_on": "path",
                    "result_value": expected_target["path"],
                    "matched_content_terms": ["tensorlake", "schedulerproof", "rdmawatch"],
                }
            ],
            "missing_targets": [],
        }

    def _valid_frontend_visibility_payload(self) -> dict[str, object]:
        expected_target = {
            "target_id": "wiki:personal-wiki/domains/ai_infra/runtime/expanded-runtime-smoke.md",
            "kind": "wiki_page",
            "path": "personal-wiki/domains/ai_infra/runtime/expanded-runtime-smoke.md",
            "title": "Expanded Runtime Smoke",
            "query": "Expanded Runtime Smoke",
            "content_terms": ["tensorlake", "schedulerproof", "rdmawatch"],
            "content_fingerprint": "tensorlake schedulerproof rdmawatch",
        }
        return {
            "status": "pass",
            "created_by": "harness_loop_orchestrator",
            "run_id": "expanded-run",
            "task_id": "expanded-run-task-1",
            "domain": "ai_infra",
            "page_url": "http://127.0.0.1:5173/",
            "route": "/api/search",
            "api_url": "http://127.0.0.1:5173/api/search?q=Expanded+Runtime+Smoke&domain=ai_infra",
            "visible_text": ["Expanded runtime smoke"],
            "assertions": ["frontend proxy search matched current runtime target"],
            "expected_targets": [expected_target],
            "matched_targets": [
                {
                    "target_id": expected_target["target_id"],
                    "path": expected_target["path"],
                    "title": expected_target["title"],
                    "query": expected_target["query"],
                    "matched_on": "path",
                    "result_value": expected_target["path"],
                    "matched_content_terms": ["tensorlake", "schedulerproof", "rdmawatch"],
                }
            ],
            "missing_targets": [],
        }

    def _write_required_evidence_manifest(
        self,
        repo_root: Path,
        run: dict[str, object],
        *,
        include_service_availability: bool = True,
        gap_proof_artifact_relative: str | None = None,
        gap_proof_payload_task_id: str | None = None,
    ) -> None:
        run_id = str(run["run_id"])
        task_id = str(run["task_id"])
        run_dir = run_dir_for(repo_root, run_id)
        items: list[dict[str, object]] = []
        for index, requirement in enumerate(run.get("required_evidence", []), start=1):
            requirement_text = str(requirement)
            if (not include_service_availability) and "service availability evidence" in requirement_text.lower():
                continue
            stable_evidence_id = self.REQUIRED_EVIDENCE_STABLE_IDS.get(requirement_text.lower())
            self.assertIsNotNone(stable_evidence_id, f"missing stable evidence id for requirement: {requirement_text}")
            if "gap proof" in requirement_text.lower():
                artifact_relative = gap_proof_artifact_relative or f".codex/loop-runs/{run_id}/gap-proofs/{task_id}.json"
                write_json_file(
                    repo_root / artifact_relative,
                    self._valid_gap_proof_payload(gap_proof_payload_task_id or task_id),
                )
                items.append(
                    {
                        "evidence_id": stable_evidence_id,
                        "status": "pass",
                        "summary": "gap proof validated for current task",
                        "artifacts": [artifact_relative],
                    }
                )
                continue
            if stable_evidence_id in {
                "service-availability",
                "crawler-workbench-freshness",
                "loop-dashboard-freshness",
                "search-api-visibility",
                "frontend-visibility",
            }:
                artifact_relative = trusted_live_evidence_artifact_path(stable_evidence_id)
            else:
                artifact_relative = f".codex/loop-runs/{run_id}/artifacts/evidence-{index:02d}.txt"
            artifact_payload: dict[str, object] = {"requirement": requirement_text}
            if stable_evidence_id == "service-availability":
                artifact_payload = self._valid_service_availability_payload()
            elif stable_evidence_id in {"crawler-workbench-freshness", "loop-dashboard-freshness"}:
                artifact_payload = self._valid_freshness_payload(stable_evidence_id)
            elif stable_evidence_id == "search-api-visibility":
                artifact_payload = self._valid_search_visibility_payload()
            elif stable_evidence_id == "frontend-visibility":
                artifact_payload = self._valid_frontend_visibility_payload()
            artifact_path = (
                run_dir / artifact_relative
                if not artifact_relative.startswith(".codex/")
                else repo_root / artifact_relative
            )
            write_json_file(artifact_path, artifact_payload)
            items.append(
                {
                    "evidence_id": stable_evidence_id,
                    "status": "pass",
                    "summary": f"{stable_evidence_id} captured",
                    "artifacts": [artifact_relative],
                }
            )
        write_json_file(
            run_dir / "required-evidence-manifest.json",
            {
                "run_id": run_id,
                "task_id": task_id,
                "items": items,
            },
        )

    def _trusted_live_state_from_manifest(
        self,
        repo_root: Path,
        run: Mapping[str, object],
        manifest_payload: Mapping[str, object],
    ) -> dict[str, dict[str, str]]:
        run_dir = run_dir_for(repo_root, str(run["run_id"]))
        entries = manifest_payload.get("items")
        state: dict[str, dict[str, str]] = {}
        if not isinstance(entries, list):
            return state
        for entry in entries:
            if not isinstance(entry, Mapping):
                continue
            evidence_id = str(entry.get("evidence_id", "")).strip()
            if evidence_id not in {
                "service-availability",
                "crawler-workbench-freshness",
                "loop-dashboard-freshness",
                "search-api-visibility",
                "frontend-visibility",
            }:
                continue
            artifacts = entry.get("artifacts")
            if not isinstance(artifacts, list) or not artifacts:
                continue
            artifact_relative = str(artifacts[0]).strip()
            artifact_path = run_dir / artifact_relative
            state[evidence_id] = {
                "artifact_path": artifact_relative,
                "sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
                "created_by": "harness_loop_orchestrator",
                "captured_at": "2026-01-01T00:00:00Z",
            }
        return state

    def _seed_visibility_target(
        self,
        repo_root: Path,
        *,
        run_id: str,
        title: str = "Expanded Runtime Smoke",
        relative_path: str = "personal-wiki/domains/ai_infra/runtime/expanded-runtime-smoke.md",
        body: str = "Tensorlake schedulerproof rdmawatch evidence.\n",
    ) -> str:
        page_path = repo_root / relative_path
        page_path.parent.mkdir(parents=True, exist_ok=True)
        page_path.write_text(f"---\ntitle: {title}\n---\n\n# {title}\n\n{body}", encoding="utf-8")
        write_json_file(
            run_dir_for(repo_root, run_id) / "generator-result.json",
            {
                "task_id": f"{run_id}-task-1",
                "status": "implemented",
                "changed_paths": [relative_path],
                "commit": "",
                "verify_commands": [],
                "verify_results": [],
                "artifacts": [],
                "cleanup_required": False,
                "notes": "seeded current visibility target",
                "skill_invocations": [],
            },
        )
        return relative_path

    def _seed_visibility_targets(
        self,
        repo_root: Path,
        *,
        run_id: str,
        targets: list[dict[str, str]],
    ) -> list[str]:
        relative_paths: list[str] = []
        for target in targets:
            relative_paths.append(
                self._seed_visibility_target(
                    repo_root,
                    run_id=run_id,
                    title=target["title"],
                    relative_path=target["path"],
                    body=target["body"],
                )
            )
        write_json_file(
            run_dir_for(repo_root, run_id) / "generator-result.json",
            {
                "task_id": f"{run_id}-task-1",
                "status": "implemented",
                "changed_paths": relative_paths,
                "commit": "",
                "verify_commands": [],
                "verify_results": [],
                "artifacts": [],
                "cleanup_required": False,
                "notes": "seeded current visibility targets",
                "skill_invocations": [],
            },
        )
        return relative_paths

    def test_create_preflight_run_without_confirmation_writes_run_state_and_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            payload = create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the thing",
                run_id="demo-run",
                confirm=False,
            )

            run_dir = run_dir_for(repo_root, "demo-run")
            run_path = run_dir / "run.json"
            preflight_path = run_dir / "preflight.md"
            self.assertEqual(payload["phase"], "preflight")
            self.assertEqual(payload["next_action"], "await_preflight_confirmation")
            self.assertEqual(payload["policy"], "demand_development")
            self.assertTrue(run_path.exists())
            self.assertTrue(preflight_path.exists())
            saved_payload = read_json_file(run_path)
            validate_run_payload(saved_payload)
            self.assertEqual(saved_payload["phase"], "preflight")
            self.assertEqual(saved_payload["requirement"], "Build the thing")
            self.assertEqual(saved_payload["constraints"], [])
            self.assertEqual(saved_payload["stop_conditions"], ["passed_waiting_human_merge"])
            preflight = preflight_path.read_text(encoding="utf-8")
            self.assertIn("Build the thing", preflight)
            self.assertIn("Fallback Questionnaire", preflight)

    def test_autonomous_generator_prompt_declares_manifest_intent_without_claiming_trusted_artifact_creation(self) -> None:
        prompt = harness_loop_orchestrator._autonomous_generator_prompt(
            {"run_id": "expanded-run", "domain": "ai_infra"},
            Path("/tmp/run-dir"),
        )

        self.assertIn("write required-evidence-manifest.json", prompt)
        self.assertIn("declare stable evidence ids", prompt)
        self.assertIn("Do not run live service or local socket checks", prompt)
        self.assertIn("Do not start tmux, uvicorn, npm, Vite, or other long-lived services", prompt)
        self.assertIn("Record delegated live checks in verify_results instead of blocking", prompt)
        self.assertNotIn("put created_by: harness_loop_orchestrator inside the referenced artifact payload", prompt)
        self.assertNotIn("create trusted-live-evidence", prompt)

    def test_autonomous_evaluator_prompt_delegates_live_service_checks_to_orchestrator(self) -> None:
        prompt = harness_loop_orchestrator._autonomous_evaluator_prompt(
            {"run_id": "expanded-run", "task_id": "expanded-run-task-2", "domain": "ai_infra"},
            Path("/tmp/run-dir"),
        )

        self.assertIn("Do not run live service or local socket checks", prompt)
        self.assertIn("Do not start tmux, uvicorn, npm, Vite, or other long-lived services", prompt)
        self.assertIn("Do not fail solely because localhost service probes are unavailable", prompt)
        self.assertIn("Verify delegated live evidence intent", prompt)
        self.assertIn("trusted-live-evidence/<evidence-id>.json", prompt)
        self.assertIn("the orchestrator captures fresh trusted live evidence after evaluator acceptance", prompt)

    def test_create_preflight_run_captures_baseline_before_loop_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            subprocess.run(["git", "init"], cwd=repo_root, check=True, capture_output=True)
            unrelated_path = repo_root / "unrelated.txt"
            unrelated_path.write_text("pre-existing user change\n", encoding="utf-8")

            payload = create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the thing",
                run_id="demo-run",
                confirm=True,
            )

            self.assertEqual(payload["baseline_dirty_paths"], ["?? unrelated.txt"])

    def test_create_preflight_run_rejects_path_escape_run_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            with self.assertRaisesRegex(ValueError, "run_id"):
                create_preflight_run(
                    repo_root=repo_root,
                    mode="demand-development",
                    requirement="Build the thing",
                    run_id="../escape",
                    confirm=True,
                )

    def test_confirm_preflight_changes_phase_to_planned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the thing",
                run_id="demo-run",
                confirm=False,
            )

            payload = confirm_preflight(repo_root=repo_root, run_id="demo-run")

            self.assertEqual(payload["phase"], "planned")
            self.assertEqual(payload["next_action"], "run_planner")
            saved_payload = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(saved_payload["phase"], "planned")
            self.assertEqual(saved_payload["next_action"], "run_planner")

    def test_create_preflight_run_captures_constraints_and_stop_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            payload = create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the thing",
                run_id="demo-run",
                constraints=["Only touch scripts/"],
                stop_conditions=["passed_waiting_human_merge", "stopped_blocked"],
                confirm=True,
            )

            self.assertEqual(payload["constraints"], ["Only touch scripts/"])
            self.assertEqual(payload["stop_conditions"], ["passed_waiting_human_merge", "stopped_blocked"])
            saved_payload = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(saved_payload["constraints"], ["Only touch scripts/"])
            self.assertEqual(saved_payload["stop_conditions"], ["passed_waiting_human_merge", "stopped_blocked"])

    def test_create_preflight_run_with_confirmation_starts_planned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            payload = create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the thing",
                run_id="demo-run",
                confirm=True,
            )

            self.assertEqual(payload["phase"], "planned")
            self.assertEqual(payload["next_action"], "run_planner")
            saved_payload = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(saved_payload["phase"], "planned")
            self.assertEqual(saved_payload["next_action"], "run_planner")

    def test_create_preflight_run_accepts_autonomous_knowledge_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            payload = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Crawl knowledge",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )

            self.assertEqual(payload["policy"], "autonomous_knowledge")
            self.assertEqual(payload["phase"], "planning")
            self.assertEqual(payload["domain"], "ai_infra")
            self.assertEqual(payload["next_action"], "run_autonomous_planner")
            self.assertIn("stopped_no_action", payload["stop_conditions"])
            saved_payload = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            validate_run_payload(saved_payload)

    def test_create_preflight_run_records_expanded_policy_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )

            payload = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand ai_infra",
                run_id="expanded-run",
                confirm=True,
                domain="ai_infra",
                policy_file=policy_file,
            )

            self.assertEqual(
                payload["policy_file"],
                policy_file,
            )
            self.assertNotIn("**", payload["allowed_paths"])
            self.assertIn("personal-wiki/domains/ai_infra/**", payload["allowed_paths"])
            self.assertIn("scripts/harness*.py", payload["allowed_paths"])
            self.assertIn(".codex/**", payload["denylist_paths"])
            self.assertIn("service availability evidence", " ".join(payload["required_evidence"]))
            self.assertEqual(payload["limits"]["max_rounds_per_invocation"], 4)

    def test_create_preflight_run_rejects_policy_fixture_for_wrong_mode(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            policy_file = self._seed_policy_fixture(repo_root, "docs/harness/loop-policies/demand-development.json")

            with self.assertRaisesRegex(ValueError, "policy_file.*mode"):
                create_preflight_run(
                    repo_root=repo_root,
                    mode="autonomous-knowledge",
                    requirement="Expand ai_infra",
                    run_id="expanded-run",
                    confirm=True,
                    domain="ai_infra",
                    policy_file=policy_file,
                )

    def test_confirm_preflight_preserves_autonomous_knowledge_start_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Crawl knowledge",
                run_id="demo-run",
                domain="ai_infra",
                confirm=False,
            )

            payload = confirm_preflight(repo_root=repo_root, run_id="demo-run")

            self.assertEqual(payload["policy"], "autonomous_knowledge")
            self.assertEqual(payload["phase"], "planning")
            self.assertEqual(payload["next_action"], "run_autonomous_planner")

    def test_run_autonomous_stops_when_loop_state_has_fresh_no_action_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_no_action_loop_state(repo_root, "ai_infra")

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=3,
            )

            self.assertEqual(status["phase"], "stopped_no_action")
            self.assertEqual(status["next_action"], "none")
            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["attempts"]["planner"], 1)
            self.assertEqual(run["attempts"]["generator"], 0)

    def test_run_autonomous_requires_ai_infra_coverage_map_before_no_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="ai-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_no_action_loop_state(repo_root, "ai_infra")
            (repo_root / "personal-wiki" / "domains" / "ai_infra" / "coverage-map.json").unlink()

            status = run_autonomous(
                repo_root,
                "ai-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=3,
            )

            self.assertNotEqual(status["phase"], "stopped_no_action")
            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(load_run(repo_root, "ai-run")["next_action"], "inspect_ai_infra_coverage_map")

    def test_run_autonomous_codex_planner_missing_coverage_map_without_no_action_evidence_reaches_planner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="ai-run",
                domain="ai_infra",
                confirm=True,
            )

            def fake_planner(planner_repo_root: Path, run: dict[str, object]) -> bool:
                run["phase"] = "stopped_blocked"
                run["next_action"] = "planner_called"
                run["last_result"] = "blocked"
                harness_loop_orchestrator.save_run(planner_repo_root, run)
                return False

            with patch.object(harness_loop_orchestrator, "_run_codex_autonomous_planner", side_effect=fake_planner) as planner:
                status = run_autonomous(
                    repo_root,
                    "ai-run",
                    planner_driver="codex-exec",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            planner.assert_called_once()
            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "planner_called")

    def test_run_autonomous_blocks_semantically_invalid_ai_infra_coverage_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="ai-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_no_action_loop_state(repo_root, "ai_infra")
            coverage_map_path = repo_root / "personal-wiki" / "domains" / "ai_infra" / "coverage-map.json"
            coverage_map = read_json_file(coverage_map_path)
            coverage_map["domain"] = "other_domain"
            write_json_file(coverage_map_path, coverage_map)

            status = run_autonomous(
                repo_root,
                "ai-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=3,
            )

            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(load_run(repo_root, "ai-run")["next_action"], "inspect_ai_infra_coverage_map")
            coverage_result = read_json_file(run_dir_for(repo_root, "ai-run") / "coverage-map-result.json")
            self.assertEqual(coverage_result["status"], "blocked")
            self.assertIn("domain does not match loop state", coverage_result["error"])

    def test_run_autonomous_blocks_ai_infra_coverage_map_with_invalid_last_scanned_at(self) -> None:
        for invalid_timestamp in ("", "not-a-timestamp"):
            with self.subTest(last_scanned_at=invalid_timestamp):
                with tempfile.TemporaryDirectory() as tmp:
                    repo_root = Path(tmp)
                    init_git_repo(repo_root)
                    create_preflight_run(
                        repo_root=repo_root,
                        mode="autonomous-knowledge",
                        requirement="Expand wiki",
                        run_id="ai-run",
                        domain="ai_infra",
                        confirm=True,
                    )
                    seed_no_action_loop_state(repo_root, "ai_infra")
                    coverage_map_path = repo_root / "personal-wiki" / "domains" / "ai_infra" / "coverage-map.json"
                    coverage_map = read_json_file(coverage_map_path)
                    coverage_map["layers"]["hardware-accelerator"]["last_scanned_at"] = invalid_timestamp
                    write_json_file(coverage_map_path, coverage_map)

                    status = run_autonomous(
                        repo_root,
                        "ai-run",
                        planner_driver="fake",
                        generator_driver="fake",
                        evaluator_driver="fake",
                        max_eval_attempts=2,
                        max_tasks=3,
                    )

                    self.assertEqual(status["phase"], "stopped_blocked")
                    self.assertEqual(load_run(repo_root, "ai-run")["next_action"], "inspect_ai_infra_coverage_map")
                    coverage_result = read_json_file(run_dir_for(repo_root, "ai-run") / "coverage-map-result.json")
                    self.assertEqual(coverage_result["status"], "blocked")
                    self.assertIn("invalid timestamp", coverage_result["error"])

    def test_run_autonomous_commits_allowlisted_change_then_returns_to_planning_and_stops_no_action(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=3,
            )

            self.assertEqual(status["phase"], "stopped_no_action")
            run_dir = run_dir_for(repo_root, "demo-run")
            generator_result = read_json_file(run_dir / "generator-result.json")
            self.assertEqual(generator_result["status"], "implemented")
            self.assertTrue(generator_result["commit"])
            changed_paths = set(generator_result["changed_paths"])
            self.assertIn("personal-wiki/domains/ai_infra/loop-state.json", changed_paths)
            self.assertTrue(any(path.startswith("personal-wiki/domains/ai_infra/raw/loop-autonomous/") for path in changed_paths))
            committed_files = subprocess.run(
                ["git", "show", "--name-only", "--format=", "HEAD"],
                cwd=repo_root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertIn("personal-wiki/domains/ai_infra/loop-state.json", committed_files.stdout)
            loop_state = read_json_file(repo_root / "personal-wiki" / "domains" / "ai_infra" / "loop-state.json")
            validate_loop_state_payload(loop_state)
            self.assertEqual(loop_state["last_planner_decision"], "no_action")
            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["phase"], "stopped_no_action")
            self.assertEqual(run["attempts"]["planner"], 2)
            self.assertEqual(run["attempts"]["generator"], 1)
            self.assertEqual(run["attempts"]["evaluator"], 1)

    def test_run_autonomous_ignores_legacy_open_must_fix_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="audit-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")
            seed_open_must_fix_audit(repo_root, "audit-run")

            status = run_autonomous(
                repo_root,
                "audit-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=3,
            )

            run = load_run(repo_root, "audit-run")
            self.assertEqual(status["phase"], "stopped_no_action")
            self.assertNotEqual(run["phase"], "audit_blocked")
            self.assertEqual(
                len(list((run_dir_for(repo_root, "audit-run") / "audit-reports").glob("audit-*.json"))),
                1,
            )

    def test_run_autonomous_audit_blocked_runs_remediation_task_and_rechecks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="audit-remediate-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")
            seed_open_must_fix_audit(repo_root, "audit-remediate-run")
            legacy = load_run(repo_root, "audit-remediate-run")
            legacy["phase"] = "audit_blocked"
            legacy["next_action"] = "create_audit_remediation_task"
            legacy["last_result"] = "blocked"
            save_run(repo_root, legacy)

            status = run_autonomous(
                repo_root,
                "audit-remediate-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=1,
            )

            run = load_run(repo_root, "audit-remediate-run")
            self.assertEqual(status["phase"], "stopped_budget")
            self.assertEqual(run["last_result"], "pass")
            self.assertTrue(run.get("_audit_remediation"))
            self.assertEqual(run["_audit_remediation"]["status"], "resolved")
            self.assertEqual(run.get("_autonomous_completed_task_ids", []), [])
            self.assertEqual(
                run["_autonomous_completed_remediation_task_ids"],
                ["audit-remediate-run-audit-remediation-001"],
            )
            self.assertFalse(
                (run_dir_for(repo_root, "audit-remediate-run") / "audit-reports" / "audit-002.json").exists()
            )
            remediation = read_json_file(run_dir_for(repo_root, "audit-remediate-run") / "audit-remediation-result.json")
            self.assertEqual(remediation["status"], "pass")
            self.assertEqual(remediation["handled_findings"], ["audit-001-repeat-001"])
            self.assertEqual(remediation["new_audit_report"], "")

    def test_run_autonomous_non_ai_infra_fake_generator_does_not_write_coverage_map(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="ml-run",
                domain="ml_platform",
                confirm=True,
            )
            state = create_default_loop_state("ml_platform", "Expand wiki")
            state["known_sources"] = [
                {
                    "id": "src-1",
                    "title": "Source",
                    "source": "manual",
                    "status": "scanned",
                    "updated_at": state["last_scan_at"],
                    "evidence": ["checked"],
                }
            ]
            state["candidate_backlog"] = [
                {
                    "id": "candidate-1",
                    "title": "Capture synthetic source",
                    "source": "planner",
                    "status": "pending",
                    "updated_at": state["last_scan_at"],
                    "evidence": ["seeded candidate"],
                }
            ]
            write_loop_state(repo_root, "ml_platform", state)
            status = run_autonomous(
                repo_root,
                "ml-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=1,
            )

            self.assertEqual(status["phase"], "stopped_budget")
            generator_result = read_json_file(run_dir_for(repo_root, "ml-run") / "generator-result.json")
            changed_paths = set(generator_result["changed_paths"])
            coverage_map_relative = "personal-wiki/domains/ml_platform/coverage-map.json"
            self.assertNotIn(coverage_map_relative, changed_paths)
            self.assertFalse((repo_root / coverage_map_relative).exists())
            committed_files = subprocess.run(
                ["git", "show", "--name-only", "--format=", "HEAD"],
                cwd=repo_root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertNotIn(coverage_map_relative, committed_files.stdout.splitlines())

    def test_run_autonomous_blocks_declared_paths_that_were_dirty_at_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            seed_candidate_loop_state(repo_root, "ai_infra")
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=3,
            )

            self.assertEqual(status["phase"], "stopped_blocked")
            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            dirty_result = read_json_file(run_dir / "dirty-paths-result.json")
            self.assertEqual(run["next_action"], "inspect_autonomous_dirty_paths")
            self.assertIn("personal-wiki/domains/ai_infra/loop-state.json", dirty_result["baseline_changed_paths"])

    def test_check_autonomous_dirty_paths_blocks_dirty_loop_state_omitted_from_changed_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            seed_no_action_loop_state(repo_root, "ai_infra")
            loop_state_relative = "personal-wiki/domains/ai_infra/loop-state.json"
            subprocess.run(
                ["git", "add", "--", "personal-wiki/domains/ai_infra"],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                ["git", "commit", "-m", "test: seed loop state", "--", "personal-wiki/domains/ai_infra"],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            loop_state_path = repo_root / loop_state_relative
            loop_state = read_json_file(loop_state_path)
            loop_state["no_action_evidence"] = ["dirty current loop state"]
            write_json_file(loop_state_path, loop_state)
            run = {
                "run_id": "expanded-run",
                "task_id": "expanded-task",
                "domain": "ai_infra",
                "baseline_dirty_paths": [],
            }

            dirty_result = harness_loop_orchestrator._check_autonomous_dirty_paths(
                repo_root,
                run,
                ["personal-wiki/domains/ai_infra/raw/loop-autonomous/new-note.md"],
            )

            self.assertFalse(dirty_result["allowed"])
            self.assertIn(loop_state_relative, dirty_result["unexpected_paths"])
            self.assertNotIn(loop_state_relative, dirty_result["declared_paths"])

    def test_check_autonomous_dirty_paths_claims_declared_untracked_crawler_raw_from_baseline(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            raw_relative = (
                "personal-wiki/domains/ai_infra/raw/crawler/"
                "nccl-arxiv-papers/capture.md"
            )
            raw_path = repo_root / raw_relative
            raw_path.parent.mkdir(parents=True)
            raw_path.write_text("scheduled capture\n", encoding="utf-8")
            run = {
                "run_id": "demo-run",
                "task_id": "demo-run-task-1",
                "domain": "ai_infra",
                "baseline_dirty_paths": [f"?? {raw_relative}"],
            }

            dirty_result = harness_loop_orchestrator._check_autonomous_dirty_paths(
                repo_root,
                run,
                [raw_relative],
            )

            self.assertTrue(dirty_result["allowed"], json.dumps(dirty_result, indent=2))
            self.assertEqual(dirty_result["claimed_baseline_paths"], [raw_relative])
            self.assertEqual(dirty_result["baseline_changed_paths"], [])

    def test_check_autonomous_dirty_paths_does_not_claim_tracked_crawler_changes(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            raw_relative = (
                "personal-wiki/domains/ai_infra/raw/crawler/"
                "nccl-arxiv-papers/capture.md"
            )
            raw_path = repo_root / raw_relative
            raw_path.parent.mkdir(parents=True)
            raw_path.write_text("existing capture\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "--", raw_relative],
                cwd=repo_root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "test: seed crawler raw"],
                cwd=repo_root,
                check=True,
                capture_output=True,
            )
            raw_path.write_text("user-modified capture\n", encoding="utf-8")
            run = {
                "run_id": "demo-run",
                "task_id": "demo-run-task-1",
                "domain": "ai_infra",
                "baseline_dirty_paths": [f" M {raw_relative}"],
            }

            dirty_result = harness_loop_orchestrator._check_autonomous_dirty_paths(
                repo_root,
                run,
                [raw_relative],
            )

            self.assertFalse(dirty_result["allowed"])
            self.assertEqual(dirty_result["claimed_baseline_paths"], [])
            self.assertEqual(dirty_result["baseline_changed_paths"], [raw_relative])

    def test_check_autonomous_dirty_paths_blocks_undeclared_tracked_crawler_raw_change(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            raw_relative = (
                "personal-wiki/domains/ai_infra/raw/crawler/"
                "nccl-arxiv-papers/capture.md"
            )
            raw_path = repo_root / raw_relative
            raw_path.parent.mkdir(parents=True)
            raw_path.write_text("existing capture\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "--", raw_relative],
                cwd=repo_root,
                check=True,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "test: seed crawler raw"],
                cwd=repo_root,
                check=True,
                capture_output=True,
            )
            raw_path.write_text("user-modified capture\n", encoding="utf-8")
            run = {
                "run_id": "demo-run",
                "task_id": "demo-run-task-1",
                "domain": "ai_infra",
                "baseline_dirty_paths": [],
            }

            dirty_result = harness_loop_orchestrator._check_autonomous_dirty_paths(
                repo_root,
                run,
                [],
            )

            self.assertFalse(dirty_result["allowed"])
            self.assertIn(raw_relative, dirty_result["unexpected_paths"])
            self.assertNotIn(raw_relative, dirty_result["ignored_paths"])

    def test_check_autonomous_dirty_paths_ignores_current_run_runtime_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            (repo_root / ".codex").mkdir()
            runtime_log = ".codex/ai-infra-expansion-continuation.log"
            (repo_root / runtime_log).write_text("runner output\n", encoding="utf-8")
            run = {
                "run_id": "ai-infra-expansion-continuation-20260708",
                "task_id": "ai-infra-expansion-continuation-20260708-parent-1",
                "domain": "ai_infra",
                "baseline_dirty_paths": [],
            }

            dirty_result = harness_loop_orchestrator._check_autonomous_dirty_paths(repo_root, run, [])

            self.assertTrue(dirty_result["allowed"], json.dumps(dirty_result, indent=2))
            self.assertIn(runtime_log, dirty_result["ignored_paths"])
            self.assertNotIn(runtime_log, dirty_result["unexpected_paths"])

    def test_check_autonomous_dirty_paths_ignores_supervisor_runtime_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            decision_path = (
                repo_root
                / ".codex"
                / "supervisor"
                / "needs-user-decisions"
                / "unsupported-state-demo-run.json"
            )
            decision_path.parent.mkdir(parents=True)
            decision_path.write_text('{"status":"archived"}\n', encoding="utf-8")
            run = {
                "run_id": "demo-run",
                "task_id": "demo-run-task-1",
                "domain": "ai_infra",
                "baseline_dirty_paths": [],
            }

            dirty_result = harness_loop_orchestrator._check_autonomous_dirty_paths(repo_root, run, [])

            relative_path = decision_path.relative_to(repo_root).as_posix()
            self.assertTrue(dirty_result["allowed"], json.dumps(dirty_result, indent=2))
            self.assertIn(relative_path, dirty_result["ignored_paths"])
            self.assertNotIn(relative_path, dirty_result["unexpected_paths"])

    def test_check_autonomous_dirty_paths_ignores_service_runtime_heartbeats(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            runtime_path = (
                repo_root
                / ".codex"
                / "service-runtime"
                / "supervisor-worker.json"
            )
            runtime_path.parent.mkdir(parents=True)
            runtime_path.write_text('{"service":"supervisor-worker"}\n', encoding="utf-8")
            run = {
                "run_id": "demo-run",
                "task_id": "demo-run-task-1",
                "domain": "ai_infra",
                "baseline_dirty_paths": [],
            }

            dirty_result = harness_loop_orchestrator._check_autonomous_dirty_paths(
                repo_root, run, []
            )

            relative_path = runtime_path.relative_to(repo_root).as_posix()
            self.assertTrue(dirty_result["allowed"], json.dumps(dirty_result, indent=2))
            self.assertIn(relative_path, dirty_result["ignored_paths"])
            self.assertNotIn(relative_path, dirty_result["unexpected_paths"])

    def test_check_autonomous_dirty_paths_ignores_only_concurrent_crawler_raw(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            crawler_raw = (
                repo_root
                / "personal-wiki"
                / "domains"
                / "ai_infra"
                / "raw"
                / "crawler"
                / "daily-source"
                / "capture.md"
            )
            crawler_raw.parent.mkdir(parents=True)
            crawler_raw.write_text("scheduler capture\n", encoding="utf-8")
            undeclared_wiki = (
                repo_root
                / "personal-wiki"
                / "domains"
                / "ai_infra"
                / "wiki"
                / "undeclared.md"
            )
            undeclared_wiki.parent.mkdir(parents=True)
            undeclared_wiki.write_text("undeclared wiki\n", encoding="utf-8")
            run = {
                "run_id": "demo-run",
                "task_id": "demo-run-task-1",
                "domain": "ai_infra",
                "baseline_dirty_paths": [],
            }

            dirty_result = harness_loop_orchestrator._check_autonomous_dirty_paths(
                repo_root, run, []
            )

            crawler_relative = crawler_raw.relative_to(repo_root).as_posix()
            wiki_relative = undeclared_wiki.relative_to(repo_root).as_posix()
            self.assertFalse(dirty_result["allowed"])
            self.assertIn(crawler_relative, dirty_result["ignored_paths"])
            self.assertNotIn(crawler_relative, dirty_result["unexpected_paths"])
            self.assertIn(wiki_relative, dirty_result["unexpected_paths"])

    def test_check_autonomous_dirty_paths_ignores_parent008_redacted_byproduct(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = (
                "ai-infra-expansion-continuation-20260708-continuation-002-"
                "continuation-007-continuation-008"
            )
            task_id = f"{run_id}-task-8"
            declared_path = (
                "personal-wiki/domains/ai_infra/wiki/references/"
                "ai-infra-coverage-map.md"
            )
            declared = repo_root / declared_path
            declared.parent.mkdir(parents=True, exist_ok=True)
            declared.write_text("# Current Task Artifact\n", encoding="utf-8")
            redacted_path = "scripts/tests/test_harness_loop_orchestrator.py.redacted"
            redacted = repo_root / redacted_path
            redacted.parent.mkdir(parents=True, exist_ok=True)
            redacted.write_text("[REDACTED]\n", encoding="utf-8")
            run = {
                "run_id": run_id,
                "task_id": task_id,
                "domain": "ai_infra",
                "baseline_dirty_paths": [],
            }

            dirty_result = harness_loop_orchestrator._check_autonomous_dirty_paths(
                repo_root,
                run,
                [declared_path],
            )

            self.assertTrue(dirty_result["allowed"], json.dumps(dirty_result, indent=2))
            self.assertIn(redacted_path, dirty_result["ignored_paths"])
            self.assertNotIn(redacted_path, dirty_result["unexpected_paths"])

    def test_check_autonomous_dirty_paths_ignores_parent26_sibling_gap_proof_and_byproducts(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = (
                "ai-infra-expansion-continuation-20260708-continuation-002-"
                "continuation-007-continuation-26b4d5f774"
            )
            task_id = f"{run_id}-task-2"
            sibling_gap_proof = (
                "personal-wiki/domains/ai_infra/"
                "manifest-ai-infra-expansion-continuation-20260708-continuation-002-"
                "continuation-007-continuation-008-task-8-gap-proof.json"
            )
            sibling = repo_root / sibling_gap_proof
            sibling.parent.mkdir(parents=True, exist_ok=True)
            sibling.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "run_id": (
                            "ai-infra-expansion-continuation-20260708-"
                            "continuation-002-continuation-007-continuation-008"
                        ),
                        "task_id": (
                            "ai-infra-expansion-continuation-20260708-"
                            "continuation-002-continuation-007-continuation-008-task-8"
                        ),
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            byproducts = [
                "scripts/tests/test_harness_loop_orchestrator.py.redacted",
                "generated/child-001.txt",
            ]
            for relative in byproducts:
                path = repo_root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("non-task byproduct\n", encoding="utf-8")
            run = {
                "run_id": run_id,
                "task_id": task_id,
                "domain": "ai_infra",
                "baseline_dirty_paths": [],
            }

            dirty_result = harness_loop_orchestrator._check_autonomous_dirty_paths(
                repo_root,
                run,
                [],
            )

            self.assertTrue(dirty_result["allowed"], json.dumps(dirty_result, indent=2))
            self.assertEqual(dirty_result["unexpected_paths"], [])
            for relative in [sibling_gap_proof, *byproducts]:
                self.assertIn(relative, dirty_result["ignored_paths"])

    def test_check_autonomous_dirty_paths_blocks_undeclared_current_gap_proof(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = (
                "ai-infra-expansion-continuation-20260708-continuation-002-"
                "continuation-007-continuation-26b4d5f774"
            )
            task_id = f"{run_id}-task-2"
            current_gap_proof = (
                "personal-wiki/domains/ai_infra/"
                f"manifest-{task_id}-gap-proof.json"
            )
            current = repo_root / current_gap_proof
            current.parent.mkdir(parents=True, exist_ok=True)
            current.write_text(
                json.dumps({"schema_version": 1, "run_id": run_id, "task_id": task_id})
                + "\n",
                encoding="utf-8",
            )
            run = {
                "run_id": run_id,
                "task_id": task_id,
                "domain": "ai_infra",
                "baseline_dirty_paths": [],
            }

            dirty_result = harness_loop_orchestrator._check_autonomous_dirty_paths(
                repo_root,
                run,
                [],
            )

            self.assertFalse(dirty_result["allowed"])
            self.assertIn(current_gap_proof, dirty_result["unexpected_paths"])

    def test_check_autonomous_dirty_paths_blocks_sensitive_byproduct_paths(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            sensitive_paths = [
                "generated/secret-token.txt",
                "generated/credential.redacted",
            ]
            for relative in sensitive_paths:
                path = repo_root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("sensitive byproduct\n", encoding="utf-8")
            run = {
                "run_id": "ai-infra-expansion-continuation-20260708",
                "task_id": "ai-infra-expansion-continuation-20260708-parent-2",
                "domain": "ai_infra",
                "baseline_dirty_paths": [],
                "denylist_paths": [
                    "**/*secret*",
                    "**/*token*",
                    "**/*credential*",
                ],
            }

            dirty_result = harness_loop_orchestrator._check_autonomous_dirty_paths(
                repo_root,
                run,
                [],
            )

            self.assertFalse(dirty_result["allowed"])
            for relative in sensitive_paths:
                self.assertIn(relative, dirty_result["unexpected_paths"])
                self.assertNotIn(relative, dirty_result["ignored_paths"])

    def test_check_autonomous_dirty_paths_ignores_supervisor_reviewer_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            reviewer_log = repo_root / ".codex" / "loop-supervisor-reviewer.log"
            reviewer_log.parent.mkdir(parents=True)
            reviewer_log.write_text("reviewer output\n", encoding="utf-8")
            run = {
                "run_id": "demo-run",
                "task_id": "demo-run-task-1",
                "domain": "ai_infra",
                "baseline_dirty_paths": [],
            }

            dirty_result = harness_loop_orchestrator._check_autonomous_dirty_paths(
                repo_root, run, []
            )

            relative_path = reviewer_log.relative_to(repo_root).as_posix()
            self.assertTrue(dirty_result["allowed"], json.dumps(dirty_result, indent=2))
            self.assertIn(relative_path, dirty_result["ignored_paths"])
            self.assertNotIn(relative_path, dirty_result["unexpected_paths"])

    def test_dirty_path_recovery_replans_clean_fake_generator_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "fake-driver-cutover"
            run = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id=run_id,
                domain="ai_infra",
                confirm=True,
            )
            task_id = f"{run_id}-task-3"
            run.update(
                {
                    "phase": "stopped_blocked",
                    "task_id": task_id,
                    "next_action": "inspect_autonomous_dirty_paths",
                    "last_result": "blocked",
                }
            )
            save_run(repo_root, run)
            run_dir = run_dir_for(repo_root, run_id)
            write_json_file(
                run_dir / "generator-result.json",
                {
                    "task_id": task_id,
                    "status": "implemented",
                    "changed_paths": ["knowledge/synthetic-parent-23.md"],
                    "commit": "",
                    "verify_commands": [],
                    "verify_results": [],
                    "artifacts": ["knowledge/synthetic-parent-23.md"],
                    "cleanup_required": False,
                    "notes": "fake autonomous generator completed",
                    "skill_invocations": [],
                },
            )
            write_json_file(
                run_dir / "evaluator-result.json",
                {
                    "status": "pass",
                    "task_id": task_id,
                    "driver": "fake",
                    "returncode": 0,
                    "stdout": "fake autonomous smoke pass\n",
                    "stderr": "",
                    "skill_invocations": [],
                },
            )

            resumed = harness_loop_orchestrator._resume_autonomous_dirty_path_block(
                repo_root, run
            )

            self.assertTrue(resumed)
            saved = load_run(repo_root, run_id)
            self.assertEqual(saved["phase"], "planning")
            self.assertEqual(saved["next_action"], "run_autonomous_planner")
            self.assertEqual(saved["last_result"], "none")
            dirty_result = read_json_file(run_dir / "dirty-paths-result.json")
            self.assertEqual(
                dirty_result["recovery_outcome"],
                "replan_clean_fake_generator_result",
            )

    def test_autonomous_dirty_path_block_reenters_cleanup_when_only_runtime_log_is_dirty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "ai-infra-expansion-continuation-20260708"
            run = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id=run_id,
                domain="ai_infra",
                confirm=True,
            )
            task_id = f"{run_id}-parent-1"
            run.update(
                {
                    "phase": "stopped_blocked",
                    "task_id": task_id,
                    "next_action": "inspect_autonomous_dirty_paths",
                    "last_result": "blocked",
                }
            )
            save_run(repo_root, run)
            write_json_file(
                run_dir_for(repo_root, run_id) / "generator-result.json",
                {
                    "task_id": task_id,
                    "status": "implemented",
                    "changed_paths": [],
                    "commit": "",
                    "verify_commands": [],
                    "verify_results": [],
                    "artifacts": [],
                    "cleanup_required": False,
                    "notes": "No repo changes for this regression.",
                    "skill_invocations": [],
                },
            )
            (repo_root / ".codex" / "ai-infra-expansion-continuation.log").write_text(
                "runner output\n",
                encoding="utf-8",
            )

            resumed = harness_loop_orchestrator._resume_autonomous_dirty_path_block(repo_root, run)

            self.assertTrue(resumed)
            saved = load_run(repo_root, run_id)
            self.assertEqual(saved["phase"], "cleanup")
            self.assertEqual(saved["next_action"], "commit_autonomous_changes")
            dirty_result = read_json_file(run_dir_for(repo_root, run_id) / "dirty-paths-result.json")
            self.assertTrue(dirty_result["allowed"], json.dumps(dirty_result, indent=2))

    def test_check_autonomous_dirty_paths_ignores_runtime_review_and_final_evaluator_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "ai-infra-expansion-continuation-20260708"
            task_id = f"{run_id}-task-2"
            run = {
                "run_id": run_id,
                "task_id": task_id,
                "domain": "ai_infra",
                "baseline_dirty_paths": [],
            }
            ignored_paths = [
                ".codex/crawler-backend-8765.log",
                ".codex/crawler-frontend-5173.log",
                ".codex/loop-dashboard-8766.log",
                ".codex/reviews/review-20260716T233017Z-b1096a7982ec/result.json",
                ".codex/evaluations/finals/final-20260716T233017Z/result.json",
            ]
            for relative in ignored_paths:
                path = repo_root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("runtime evidence\n", encoding="utf-8")

            dirty_result = harness_loop_orchestrator._check_autonomous_dirty_paths(
                repo_root,
                run,
                [],
            )

            self.assertTrue(dirty_result["allowed"], json.dumps(dirty_result, indent=2))
            self.assertEqual(dirty_result["unexpected_paths"], [])
            self.assertEqual(dirty_result["ignored_paths"], sorted(ignored_paths))

    def test_commit_autonomous_changes_protects_hashed_recovery_artifacts_from_unrelated_dirty_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "ai-infra-expansion-continuation-20260708"
            run = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Recover generator artifact",
                run_id=run_id,
                domain="ai_infra",
                confirm=True,
            )
            task_id = f"{run_id}-task-2"
            run.update({"phase": "cleanup", "task_id": task_id})
            save_run(repo_root, run)
            changed_path = "personal-wiki/domains/ai_infra/wiki/references/recovered.md"
            unrelated_path = "personal-wiki/domains/ai_infra/wiki/references/unrelated.md"
            for relative, content in (
                (changed_path, "# Recovered\n"),
                (unrelated_path, "# Unrelated user work\n"),
            ):
                path = repo_root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            changed_hash = hashlib.sha256((repo_root / changed_path).read_bytes()).hexdigest()
            generator_result = {
                "task_id": task_id,
                "status": "implemented",
                "changed_paths": [changed_path],
                "commit": "",
                "verify_commands": ["python3 -m pytest -q fixture"],
                "verify_results": [
                    {
                        "command": "python3 -m pytest -q fixture",
                        "status": "pass",
                        "summary": "fixture passed",
                    }
                ],
                "artifacts": [changed_path],
                "cleanup_required": False,
                "notes": "Recovered from validated partial Generator artifacts.",
                "skill_invocations": [],
                "recovery": {
                    "recovered_from_attempts": [3],
                    "artifact_hashes": {changed_path: changed_hash},
                },
            }

            with patch.object(harness_loop_orchestrator, "_run_wiki_validate", return_value=True):
                committed = harness_loop_orchestrator._commit_autonomous_changes(
                    repo_root,
                    run,
                    generator_result,
                    bounded=True,
                )

            self.assertTrue(committed)
            self.assertEqual(
                harness_loop_orchestrator._commit_changed_paths(repo_root, generator_result["commit"]),
                [changed_path],
            )
            saved = load_run(repo_root, run_id)
            self.assertIn(f"?? {unrelated_path}", saved["baseline_dirty_paths"])
            dirty_result = read_json_file(run_dir_for(repo_root, run_id) / "dirty-paths-result.json")
            self.assertTrue(dirty_result["allowed"], json.dumps(dirty_result, indent=2))
            self.assertEqual(dirty_result["unexpected_paths"], [])

    def test_commit_autonomous_changes_blocks_unhashed_unrelated_dirty_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "ai-infra-expansion-continuation-20260708"
            run = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Recover generator artifact",
                run_id=run_id,
                domain="ai_infra",
                confirm=True,
            )
            task_id = f"{run_id}-task-2"
            run.update({"phase": "cleanup", "task_id": task_id})
            save_run(repo_root, run)
            changed_path = "personal-wiki/domains/ai_infra/wiki/references/recovered.md"
            unrelated_path = "personal-wiki/domains/ai_infra/wiki/references/unrelated.md"
            for relative, content in (
                (changed_path, "# Recovered\n"),
                (unrelated_path, "# Unrelated user work\n"),
            ):
                path = repo_root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content, encoding="utf-8")
            generator_result = {
                "task_id": task_id,
                "status": "implemented",
                "changed_paths": [changed_path],
                "commit": "",
                "verify_commands": ["python3 -m pytest -q fixture"],
                "verify_results": [
                    {
                        "command": "python3 -m pytest -q fixture",
                        "status": "pass",
                        "summary": "fixture passed",
                    }
                ],
                "artifacts": [changed_path],
                "cleanup_required": False,
                "notes": "Recovered artifact without hash provenance must not absorb unrelated dirt.",
                "skill_invocations": [],
                "recovery": {"recovered_from_attempts": [3], "artifact_hashes": {}},
            }

            with patch.object(harness_loop_orchestrator, "_run_wiki_validate", return_value=True):
                committed = harness_loop_orchestrator._commit_autonomous_changes(
                    repo_root,
                    run,
                    generator_result,
                    bounded=True,
                )

            self.assertFalse(committed)
            self.assertEqual(generator_result["commit"], "")
            saved = load_run(repo_root, run_id)
            self.assertEqual(saved["phase"], "stopped_blocked")
            self.assertEqual(saved["next_action"], "inspect_autonomous_dirty_paths")
            dirty_result = read_json_file(run_dir_for(repo_root, run_id) / "dirty-paths-result.json")
            self.assertFalse(dirty_result["allowed"])
            self.assertIn(unrelated_path, dirty_result["unexpected_paths"])

    def test_autonomous_dirty_path_block_rejects_stale_generator_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "ai-infra-expansion-continuation-20260708"
            run = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id=run_id,
                domain="ai_infra",
                confirm=True,
            )
            run.update(
                {
                    "phase": "stopped_blocked",
                    "task_id": f"{run_id}-parent-1",
                    "next_action": "inspect_autonomous_dirty_paths",
                    "last_result": "blocked",
                }
            )
            save_run(repo_root, run)
            write_json_file(
                run_dir_for(repo_root, run_id) / "generator-result.json",
                {
                    "task_id": "stale-task",
                    "status": "implemented",
                    "changed_paths": [],
                    "commit": "",
                    "verify_commands": [],
                    "verify_results": [],
                    "artifacts": [],
                    "cleanup_required": False,
                    "notes": "Stale result must not recover current dirty paths.",
                    "skill_invocations": [],
                },
            )

            resumed = harness_loop_orchestrator._resume_autonomous_dirty_path_block(repo_root, run)

            self.assertFalse(resumed)
            saved = load_run(repo_root, run_id)
            self.assertEqual(saved["phase"], "stopped_blocked")

    def test_autonomous_required_evidence_block_reenters_cleanup_after_revalidation_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "ai-infra-expansion-continuation-20260708"
            run = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id=run_id,
                domain="ai_infra",
                confirm=True,
            )
            task_id = f"{run_id}-parent-4"
            run.update(
                {
                    "phase": "stopped_blocked",
                    "task_id": task_id,
                    "next_action": "inspect_required_evidence",
                    "last_result": "blocked",
                    "required_evidence": [],
                }
            )
            save_run(repo_root, run)
            write_json_file(
                run_dir_for(repo_root, run_id) / "generator-result.json",
                {
                    "task_id": task_id,
                    "status": "implemented",
                    "changed_paths": [],
                    "commit": "",
                    "verify_commands": [],
                    "verify_results": [],
                    "artifacts": [],
                    "cleanup_required": False,
                    "notes": "No repo changes for this regression.",
                    "skill_invocations": [],
                },
            )

            resumed = harness_loop_orchestrator._resume_autonomous_required_evidence_block(repo_root, run)

            self.assertTrue(resumed)
            saved = load_run(repo_root, run_id)
            self.assertEqual(saved["phase"], "cleanup")
            self.assertEqual(saved["next_action"], "commit_autonomous_changes")
            required_evidence_result = read_json_file(run_dir_for(repo_root, run_id) / "required-evidence-result.json")
            self.assertEqual(required_evidence_result["status"], "pass")

    def test_autonomous_required_evidence_block_rejects_stale_generator_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "ai-infra-expansion-continuation-20260708"
            run = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id=run_id,
                domain="ai_infra",
                confirm=True,
            )
            run.update(
                {
                    "phase": "stopped_blocked",
                    "task_id": f"{run_id}-parent-4",
                    "next_action": "inspect_required_evidence",
                    "last_result": "blocked",
                    "required_evidence": [],
                }
            )
            save_run(repo_root, run)
            write_json_file(
                run_dir_for(repo_root, run_id) / "generator-result.json",
                {
                    "task_id": "stale-parent-task",
                    "status": "implemented",
                    "changed_paths": [],
                    "commit": "",
                    "verify_commands": [],
                    "verify_results": [],
                    "artifacts": [],
                    "cleanup_required": False,
                    "notes": "Stale result must not recover the current task.",
                    "skill_invocations": [],
                },
            )

            resumed = harness_loop_orchestrator._resume_autonomous_required_evidence_block(repo_root, run)

            self.assertFalse(resumed)
            saved = load_run(repo_root, run_id)
            self.assertEqual(saved["phase"], "stopped_blocked")

    def test_run_autonomous_supports_codex_exec_agents(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            def write_agent_output(**kwargs: object) -> dict[str, object]:
                output_path = Path(kwargs["output_json_path"])
                role = str(kwargs["role"])
                if role == "planner":
                    write_json_file(
                        output_path,
                        {
                            "task_id": "codex-autonomous-task",
                            "policy": "autonomous_knowledge",
                            "task_kind": "autonomous_implementation_task",
                            "title": "Codex autonomous task",
                            "goal": "Expand wiki",
                            "non_goals": [],
                            "allowed_paths": [
                                "personal-wiki/domains/ai_infra/raw/**",
                                "personal-wiki/domains/ai_infra/loop-state.json",
                            ],
                            "denylist_paths": [],
                            "verify_commands": [],
                            "evaluator_scenarios_path": "",
                            "stop_conditions": ["stopped_no_action", "stopped_budget", "stopped_blocked"],
                            "next_planning_hint": "continue planning",
                            "skill_invocations": [],
                        },
                    )
                elif role == "generator":
                    raw_note = repo_root / "personal-wiki" / "domains" / "ai_infra" / "raw" / "loop-autonomous" / "codex-task.md"
                    raw_note.parent.mkdir(parents=True, exist_ok=True)
                    raw_note.write_text("# Codex autonomous note\n", encoding="utf-8")
                    seed_no_action_loop_state(repo_root, "ai_infra")
                    write_json_file(
                        output_path,
                        {
                            "task_id": "codex-autonomous-task",
                            "status": "implemented",
                            "changed_paths": [
                                "personal-wiki/domains/ai_infra/raw/loop-autonomous/codex-task.md",
                            ],
                            "commit": "",
                            "verify_commands": [],
                            "verify_results": ["python3 -m unittest scripts.tests.test_harness_loop_orchestrator -v"],
                            "artifacts": ["personal-wiki/domains/ai_infra/raw/loop-autonomous/codex-task.md"],
                            "cleanup_required": False,
                            "notes": "autonomous knowledge update without dependency changes",
                            "skill_invocations": [],
                        },
                    )
                elif role == "evaluator":
                    write_json_file(
                        output_path,
                        {
                            "status": "pass",
                            "task_id": "codex-autonomous-task",
                            "driver": "codex-exec",
                            "returncode": 0,
                            "stdout": "codex autonomous evaluator pass\n",
                            "stderr": "",
                            "skill_invocations": [],
                        },
                    )
                return {
                    "status": "pass",
                    "run_id": "demo-run",
                    "role": role,
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=write_agent_output):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="codex-exec",
                    generator_driver="codex-exec",
                    evaluator_driver="codex-exec",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            self.assertEqual(status["phase"], "stopped_no_action")
            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            generator_result = read_json_file(run_dir / "generator-result.json")
            self.assertEqual(run["attempts"]["planner"], 2)
            self.assertEqual(run["attempts"]["generator"], 1)
            self.assertTrue(generator_result["commit"])

    def test_run_autonomous_retries_generator_failures_until_limit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")
            attempts: list[int] = []

            def fail_generator(**kwargs: object) -> dict[str, object]:
                attempts.append(int(kwargs["attempt"]))
                return {
                    "status": "fail",
                    "run_id": "demo-run",
                    "role": "generator",
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=fail_generator):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="codex-exec",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(attempts, [1, 2])
            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["next_action"], "inspect_autonomous_generator")
            self.assertEqual(run["attempts"]["generator"], 2)

    def test_run_autonomous_falls_back_to_deterministic_planner_after_codex_timeout(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            def timeout_planner(**kwargs: object) -> dict[str, object]:
                return {
                    "status": "timeout",
                    "run_id": "demo-run",
                    "role": "planner",
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=timeout_planner):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="codex-exec",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            self.assertEqual(status["phase"], "stopped_budget")
            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            planner_output = read_json_file(run_dir / "planner-output.json")
            self.assertEqual(run["attempts"]["planner"], 1)
            self.assertEqual(planner_output["task_id"], "demo-run-task-1")
            self.assertEqual(planner_output["policy"], "autonomous_knowledge")

    def test_run_autonomous_next_task_number_ignores_generator_retries(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")
            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "planning"
            run["next_action"] = "run_autonomous_planner"
            run["task_id"] = "demo-run-task-1"
            run["attempts"]["generator"] = 2
            run["_autonomous_completed_task_ids"] = ["demo-run-task-1"]
            write_json_file(run_dir / "run.json", run)

            def timeout_planner(**kwargs: object) -> dict[str, object]:
                return {
                    "status": "timeout",
                    "run_id": "demo-run",
                    "role": "planner",
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=timeout_planner):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="codex-exec",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=2,
                )

            self.assertEqual(status["phase"], "stopped_budget")
            planner_output = read_json_file(run_dir / "planner-output.json")
            self.assertEqual(planner_output["task_id"], "demo-run-task-2")
            self.assertTrue(
                (
                    repo_root
                    / "personal-wiki/domains/ai_infra/raw/loop-autonomous/demo-run-task-2.md"
                ).exists()
            )
            self.assertFalse(
                (
                    repo_root
                    / "personal-wiki/domains/ai_infra/raw/loop-autonomous/demo-run-task-3.md"
                ).exists()
            )

    def test_run_autonomous_generator_retry_limit_is_per_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "generating"
            run["next_action"] = "run_autonomous_generator"
            run["task_id"] = "demo-run-task-2"
            run["attempts"]["generator"] = 2
            write_json_file(run_dir / "run.json", run)
            attempts: list[int] = []

            def fail_generator(**kwargs: object) -> dict[str, object]:
                attempts.append(int(kwargs["attempt"]))
                return {
                    "status": "fail",
                    "run_id": "demo-run",
                    "role": "generator",
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=fail_generator):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="codex-exec",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(attempts, [3, 4])
            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["next_action"], "inspect_autonomous_generator")
            self.assertEqual(run["attempts"]["generator"], 4)

    def test_run_autonomous_resumes_from_evaluating_after_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            with patch(
                "scripts.harness_loop_orchestrator._run_fake_autonomous_evaluator",
                side_effect=RuntimeError("interrupted evaluator"),
            ):
                with self.assertRaisesRegex(RuntimeError, "interrupted evaluator"):
                    run_autonomous(
                        repo_root,
                        "demo-run",
                        planner_driver="fake",
                        generator_driver="fake",
                        evaluator_driver="fake",
                        max_eval_attempts=2,
                        max_tasks=3,
                    )
            interrupted = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(interrupted["phase"], "evaluating")

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=3,
            )

            self.assertEqual(status["phase"], "stopped_no_action")

    def test_run_autonomous_resumes_from_artifact_hygiene_after_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            with patch(
                "scripts.harness_loop_orchestrator._run_artifact_hygiene_step",
                side_effect=RuntimeError("interrupted hygiene"),
            ):
                with self.assertRaisesRegex(RuntimeError, "interrupted hygiene"):
                    run_autonomous(
                        repo_root,
                        "demo-run",
                        planner_driver="fake",
                        generator_driver="fake",
                        evaluator_driver="fake",
                        max_eval_attempts=2,
                        max_tasks=3,
                    )
            interrupted = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(interrupted["phase"], "artifact_hygiene")

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=3,
            )

            self.assertEqual(status["phase"], "stopped_no_action")

    def test_run_autonomous_resumes_from_cleanup_after_commit_interruption(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            with patch(
                "scripts.harness_loop_orchestrator._run_cleanup",
                side_effect=RuntimeError("interrupted cleanup"),
            ):
                with self.assertRaisesRegex(RuntimeError, "interrupted cleanup"):
                    run_autonomous(
                        repo_root,
                        "demo-run",
                        planner_driver="fake",
                        generator_driver="fake",
                        evaluator_driver="fake",
                        max_eval_attempts=2,
                        max_tasks=3,
                    )
            run_dir = run_dir_for(repo_root, "demo-run")
            interrupted = read_json_file(run_dir / "run.json")
            generator_result = read_json_file(run_dir / "generator-result.json")
            self.assertEqual(interrupted["phase"], "cleanup")
            self.assertTrue(generator_result["commit"])

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=3,
            )

            self.assertEqual(status["phase"], "stopped_no_action")

    def test_run_autonomous_resume_budget_counts_previously_completed_tasks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "planning"
            run["next_action"] = "run_autonomous_planner"
            run["task_id"] = "demo-run-task-3"
            run["_autonomous_generator_attempts_by_task"] = {
                "demo-run-task-1": 1,
                "demo-run-task-2": 1,
                "demo-run-task-3": 1,
            }
            write_json_file(run_dir / "run.json", run)

            with patch(
                "scripts.harness_loop_orchestrator._run_fake_autonomous_planner",
                side_effect=AssertionError("planner should not run after resumed budget is exhausted"),
            ):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            self.assertEqual(status["phase"], "stopped_budget")

    def test_run_autonomous_blocks_undeclared_dirty_denylist_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")
            from scripts import harness_loop_orchestrator as orchestrator

            original_generator = orchestrator._write_fake_autonomous_generator_result

            def write_undeclared_dirty_path(*args: object, **kwargs: object) -> dict[str, object]:
                result = original_generator(*args, **kwargs)
                (repo_root / ".env").write_text("FAKE_SECRET=redacted\n", encoding="utf-8")
                return result

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=write_undeclared_dirty_path,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            self.assertEqual(status["phase"], "stopped_blocked")
            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            dirty_result = read_json_file(run_dir / "dirty-paths-result.json")
            self.assertEqual(run["next_action"], "inspect_autonomous_dirty_paths")
            self.assertIn(".env", dirty_result["unexpected_paths"])

    def test_run_autonomous_distrusts_generator_commit_for_dirty_path_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            def write_fake_committed_generator_result(**kwargs: object) -> dict[str, object]:
                output_path = Path(kwargs["output_json_path"])
                run_dir = output_path.parent
                planner_output = read_json_file(run_dir / "planner-output.json")
                raw_note = repo_root / "personal-wiki" / "domains" / "ai_infra" / "raw" / "loop-autonomous" / "fake-commit.md"
                raw_note.parent.mkdir(parents=True, exist_ok=True)
                raw_note.write_text("# Fake committed note\n", encoding="utf-8")
                seed_no_action_loop_state(repo_root, "ai_infra")
                (repo_root / ".env").write_text("FAKE_SECRET=redacted\n", encoding="utf-8")
                write_json_file(
                    output_path,
                    {
                        "task_id": planner_output["task_id"],
                        "status": "implemented",
                        "changed_paths": [
                            "personal-wiki/domains/ai_infra/raw/loop-autonomous/fake-commit.md",
                            "personal-wiki/domains/ai_infra/loop-state.json",
                        ],
                        "commit": "fake-sha",
                        "verify_commands": [],
                        "verify_results": ["synthetic generator claimed committed changes"],
                        "artifacts": ["personal-wiki/domains/ai_infra/raw/loop-autonomous/fake-commit.md"],
                        "cleanup_required": False,
                        "notes": "autonomous knowledge update without dependency changes",
                        "skill_invocations": [],
                    },
                )
                return {
                    "status": "pass",
                    "run_id": "demo-run",
                    "role": "generator",
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=write_fake_committed_generator_result):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="codex-exec",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            self.assertEqual(status["phase"], "stopped_blocked")
            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            dirty_result = read_json_file(run_dir / "dirty-paths-result.json")
            self.assertEqual(run["next_action"], "inspect_autonomous_dirty_paths")
            self.assertIn(".env", dirty_result["unexpected_paths"])

    def test_run_autonomous_blocks_fake_generator_commit_without_orchestrator_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            def write_fake_committed_generator_result(**kwargs: object) -> dict[str, object]:
                output_path = Path(kwargs["output_json_path"])
                run_dir = output_path.parent
                planner_output = read_json_file(run_dir / "planner-output.json")
                raw_note = (
                    repo_root
                    / "personal-wiki"
                    / "domains"
                    / "ai_infra"
                    / "raw"
                    / "loop-autonomous"
                    / "fake-commit.md"
                )
                raw_note.parent.mkdir(parents=True, exist_ok=True)
                raw_note.write_text("# Fake committed note\n", encoding="utf-8")
                seed_no_action_loop_state(repo_root, "ai_infra")
                write_json_file(
                    output_path,
                    {
                        "task_id": planner_output["task_id"],
                        "status": "implemented",
                        "changed_paths": [
                            "personal-wiki/domains/ai_infra/raw/loop-autonomous/fake-commit.md",
                            "personal-wiki/domains/ai_infra/loop-state.json",
                        ],
                        "commit": "fake-sha",
                        "verify_commands": [],
                        "verify_results": ["synthetic generator claimed committed changes"],
                        "artifacts": ["personal-wiki/domains/ai_infra/raw/loop-autonomous/fake-commit.md"],
                        "cleanup_required": False,
                        "notes": "autonomous knowledge update without dependency changes",
                        "skill_invocations": [],
                    },
                )
                write_json_file(
                    run_dir / "commit-result.json",
                    {
                        "status": "pass",
                        "commit": "fake-sha",
                        "error": "",
                    },
                )
                write_json_file(
                    run_dir / "required-evidence-manifest.json",
                    {
                        "items": [
                            {
                                "evidence_id": "commit-result",
                                "status": "pass",
                                "summary": "synthetic generator supplied commit result",
                                "artifact": "commit-result.json",
                            }
                        ]
                    },
                )
                return {
                    "status": "pass",
                    "run_id": "demo-run",
                    "role": "generator",
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=write_fake_committed_generator_result):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="codex-exec",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            commit_result = read_json_file(run_dir / "commit-result.json")
            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "inspect_autonomous_commit")
            self.assertNotEqual(status["phase"], "stopped_no_action")
            self.assertEqual(run["next_action"], "inspect_autonomous_commit")
            self.assertEqual(commit_result["status"], "blocked")

    def test_run_autonomous_blocks_forged_commit_result_with_undeclared_commit_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            def write_forged_committed_generator_result(**kwargs: object) -> dict[str, object]:
                output_path = Path(kwargs["output_json_path"])
                run_dir = output_path.parent
                planner_output = read_json_file(run_dir / "planner-output.json")
                raw_note = (
                    repo_root
                    / "personal-wiki"
                    / "domains"
                    / "ai_infra"
                    / "raw"
                    / "loop-autonomous"
                    / "forged-commit.md"
                )
                raw_note.parent.mkdir(parents=True, exist_ok=True)
                raw_note.write_text("# Forged committed note\n", encoding="utf-8")
                seed_no_action_loop_state(repo_root, "ai_infra")
                (repo_root / ".env").write_text("FAKE_SECRET=redacted\n", encoding="utf-8")
                subprocess.run(
                    [
                        "git",
                        "add",
                        "--",
                        "personal-wiki/domains/ai_infra/raw/loop-autonomous/forged-commit.md",
                        "personal-wiki/domains/ai_infra/loop-state.json",
                        "personal-wiki/domains/ai_infra/coverage-map.json",
                        ".env",
                    ],
                    cwd=repo_root,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                subprocess.run(
                    ["git", "commit", "-m", "test: forged autonomous commit"],
                    cwd=repo_root,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                commit_sha = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo_root,
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                ).stdout.strip()
                write_json_file(
                    output_path,
                    {
                        "task_id": planner_output["task_id"],
                        "status": "implemented",
                        "changed_paths": [
                            "personal-wiki/domains/ai_infra/raw/loop-autonomous/forged-commit.md",
                            "personal-wiki/domains/ai_infra/loop-state.json",
                        ],
                        "commit": commit_sha,
                        "verify_commands": [],
                        "verify_results": ["synthetic generator committed extra undeclared path"],
                        "artifacts": ["personal-wiki/domains/ai_infra/raw/loop-autonomous/forged-commit.md"],
                        "cleanup_required": False,
                        "notes": "autonomous knowledge update without dependency changes",
                        "skill_invocations": [],
                    },
                )
                write_json_file(
                    run_dir / "commit-result.json",
                    {
                        "status": "pass",
                        "commit": commit_sha,
                        "error": "",
                        "created_by": "harness_loop_orchestrator",
                    },
                )
                return {
                    "status": "pass",
                    "run_id": "demo-run",
                    "role": "generator",
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=write_forged_committed_generator_result):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="codex-exec",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            run_dir = run_dir_for(repo_root, "demo-run")
            commit_result = read_json_file(run_dir / "commit-result.json")
            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "inspect_autonomous_commit")
            self.assertEqual(commit_result["status"], "blocked")
            self.assertIn(".env", commit_result["error"])

    def test_run_autonomous_blocks_forged_commit_result_with_exact_declared_commit_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            def write_forged_committed_generator_result(**kwargs: object) -> dict[str, object]:
                output_path = Path(kwargs["output_json_path"])
                run_dir = output_path.parent
                planner_output = read_json_file(run_dir / "planner-output.json")
                raw_note = (
                    repo_root
                    / "personal-wiki"
                    / "domains"
                    / "ai_infra"
                    / "raw"
                    / "loop-autonomous"
                    / "forged-exact-commit.md"
                )
                raw_note.parent.mkdir(parents=True, exist_ok=True)
                raw_note.write_text("# Forged exact committed note\n", encoding="utf-8")
                seed_no_action_loop_state(repo_root, "ai_infra")
                changed_paths = [
                    "personal-wiki/domains/ai_infra/raw/loop-autonomous/forged-exact-commit.md",
                ]
                subprocess.run(
                    ["git", "add", "--", *changed_paths],
                    cwd=repo_root,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                subprocess.run(
                    ["git", "commit", "-m", "test: forged exact autonomous commit"],
                    cwd=repo_root,
                    check=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                commit_sha = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo_root,
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                ).stdout.strip()
                committed_paths = subprocess.run(
                    ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", commit_sha],
                    cwd=repo_root,
                    check=True,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                ).stdout.splitlines()
                self.assertEqual(sorted(committed_paths), sorted(changed_paths))
                write_json_file(
                    output_path,
                    {
                        "task_id": planner_output["task_id"],
                        "status": "implemented",
                        "changed_paths": changed_paths,
                        "commit": commit_sha,
                        "verify_commands": [],
                        "verify_results": ["synthetic generator committed exact declared paths"],
                        "artifacts": ["personal-wiki/domains/ai_infra/raw/loop-autonomous/forged-exact-commit.md"],
                        "cleanup_required": False,
                        "notes": "autonomous knowledge update without dependency changes",
                        "skill_invocations": [],
                    },
                )
                write_json_file(
                    run_dir / "commit-result.json",
                    {
                        "status": "pass",
                        "commit": commit_sha,
                        "error": "",
                        "created_by": "harness_loop_orchestrator",
                    },
                )
                return {
                    "status": "pass",
                    "run_id": "demo-run",
                    "role": "generator",
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=write_forged_committed_generator_result):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="codex-exec",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            commit_result = read_json_file(run_dir / "commit-result.json")
            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "inspect_autonomous_commit")
            self.assertNotEqual(status["phase"], "stopped_no_action")
            self.assertEqual(run["next_action"], "inspect_autonomous_commit")
            self.assertEqual(commit_result["status"], "blocked")

    def test_autonomous_commit_resume_state_rejects_declared_path_missing_from_commit(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "demo-run"
            task_id = "demo-run-task"
            run_dir = run_dir_for(repo_root, run_id)
            run_dir.mkdir(parents=True, exist_ok=True)
            committed_path = "personal-wiki/domains/ai_infra/raw/loop-autonomous/committed.md"
            declared_but_clean_path = "personal-wiki/domains/ai_infra/raw/loop-autonomous/declared-clean.md"
            path = repo_root / committed_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Committed\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "--", committed_path],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                ["git", "commit", "-m", "test: commit one declared path", "--", committed_path],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            commit_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout.strip()
            declared_paths = [committed_path, declared_but_clean_path]
            run = {
                "run_id": run_id,
                "task_id": task_id,
                "phase": "cleanup",
                "autonomous_commit_state": {
                    "status": "committed",
                    "commit": commit_sha,
                    "created_by": "harness_loop_orchestrator",
                    "changed_paths": declared_paths,
                    "run_id": run_id,
                    "task_id": task_id,
                },
            }
            write_json_file(
                run_dir / "commit-result.json",
                {
                    "status": "pass",
                    "commit": commit_sha,
                    "error": "",
                    "created_by": "harness_loop_orchestrator",
                    "changed_paths": declared_paths,
                    "run_id": run_id,
                    "task_id": task_id,
                },
            )

            error = harness_loop_orchestrator._verify_orchestrator_commit_resume_state(
                repo_root,
                run,
                run_dir,
                commit_sha,
            )

            self.assertIn(declared_but_clean_path, error)

    def test_autonomous_commit_resume_state_rejects_commit_state_for_other_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "demo-run"
            task_id = "demo-run-task"
            run_dir = run_dir_for(repo_root, run_id)
            run_dir.mkdir(parents=True, exist_ok=True)
            changed_path = "personal-wiki/domains/ai_infra/raw/loop-autonomous/committed.md"
            path = repo_root / changed_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Committed\n", encoding="utf-8")
            subprocess.run(["git", "add", "--", changed_path], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "test: commit path", "--", changed_path], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()
            run = {
                "run_id": run_id,
                "task_id": task_id,
                "phase": "cleanup",
                "autonomous_commit_state": {
                    "status": "committed",
                    "commit": commit_sha,
                    "created_by": "harness_loop_orchestrator",
                    "changed_paths": [changed_path],
                    "run_id": run_id,
                    "task_id": "stale-task",
                },
            }
            write_json_file(
                run_dir / "commit-result.json",
                {
                    "status": "pass",
                    "commit": commit_sha,
                    "error": "",
                    "created_by": "harness_loop_orchestrator",
                    "changed_paths": [changed_path],
                    "run_id": run_id,
                    "task_id": task_id,
                },
            )

            error = harness_loop_orchestrator._verify_orchestrator_commit_resume_state(
                repo_root,
                run,
                run_dir,
                commit_sha,
            )

            self.assertIn("task_id", error)
            self.assertIn("stale-task", error)

    def test_autonomous_commit_resume_state_rejects_commit_result_for_other_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "demo-run"
            task_id = "demo-run-task"
            run_dir = run_dir_for(repo_root, run_id)
            run_dir.mkdir(parents=True, exist_ok=True)
            changed_path = "personal-wiki/domains/ai_infra/raw/loop-autonomous/committed.md"
            path = repo_root / changed_path
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("# Committed\n", encoding="utf-8")
            subprocess.run(["git", "add", "--", changed_path], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["git", "commit", "-m", "test: commit path", "--", changed_path], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            commit_sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()
            run = {
                "run_id": run_id,
                "task_id": task_id,
                "phase": "cleanup",
                "autonomous_commit_state": {
                    "status": "committed",
                    "commit": commit_sha,
                    "created_by": "harness_loop_orchestrator",
                    "changed_paths": [changed_path],
                    "run_id": run_id,
                    "task_id": task_id,
                },
            }
            write_json_file(
                run_dir / "commit-result.json",
                {
                    "status": "pass",
                    "commit": commit_sha,
                    "error": "",
                    "created_by": "harness_loop_orchestrator",
                    "changed_paths": [changed_path],
                    "run_id": run_id,
                    "task_id": "stale-task",
                },
            )

            error = harness_loop_orchestrator._verify_orchestrator_commit_resume_state(
                repo_root,
                run,
                run_dir,
                commit_sha,
            )

            self.assertIn("task_id", error)
            self.assertIn("stale-task", error)

    def test_resume_autonomous_commit_block_rejects_stale_generator_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "demo-run"
            task_id = "demo-run-task"
            changed_path = "personal-wiki/domains/ai_infra/raw/loop-autonomous/retry.md"
            run = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id=run_id,
                domain="ai_infra",
                confirm=True,
            )
            target = repo_root / changed_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# Retry commit\n", encoding="utf-8")
            run.update(
                {
                    "phase": "stopped_blocked",
                    "next_action": "inspect_autonomous_commit",
                    "last_result": "blocked",
                    "task_id": task_id,
                }
            )
            save_run(repo_root, run)
            run_dir = run_dir_for(repo_root, run_id)
            write_json_file(
                run_dir / "generator-result.json",
                {
                    "task_id": "stale-task",
                    "status": "implemented",
                    "changed_paths": [changed_path],
                    "commit": "",
                    "verify_commands": [],
                    "verify_results": [],
                    "artifacts": [changed_path],
                    "cleanup_required": False,
                    "notes": "Retry a transient commit failure.",
                    "skill_invocations": [],
                },
            )
            write_json_file(
                run_dir / "commit-result.json",
                {
                    "status": "blocked",
                    "commit": "",
                    "error": "transient index lock",
                    "created_by": "harness_loop_orchestrator",
                    "run_id": run_id,
                    "task_id": task_id,
                },
            )

            resumed = harness_loop_orchestrator._resume_autonomous_commit_block(repo_root, run)

            self.assertFalse(resumed)
            saved = load_run(repo_root, run_id)
            self.assertEqual(saved["phase"], "stopped_blocked")

    def test_commit_autonomous_changes_rejects_stale_generator_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            run["task_id"] = "current-task"
            run["phase"] = "cleanup"
            save_run(repo_root, run)
            generator_result = {
                "task_id": "stale-task",
                "status": "implemented",
                "changed_paths": [],
                "commit": "",
                "verify_commands": [],
                "verify_results": [],
                "artifacts": [],
                "cleanup_required": False,
                "notes": "Stale generator output must not pass commit gates.",
                "skill_invocations": [],
            }

            with patch.object(harness_loop_orchestrator, "_check_autonomous_dirty_paths") as dirty_check:
                committed = harness_loop_orchestrator._commit_autonomous_changes(
                    repo_root,
                    run,
                    generator_result,
                    bounded=True,
                )

            self.assertFalse(committed)
            dirty_check.assert_not_called()
            saved = load_run(repo_root, "demo-run")
            self.assertEqual(saved["phase"], "stopped_blocked")
            self.assertEqual(saved["next_action"], "inspect_autonomous_commit")
            commit_result = read_json_file(run_dir_for(repo_root, "demo-run") / "commit-result.json")
            self.assertIn("stale-task", commit_result["error"])

    def test_commit_autonomous_changes_accepts_current_planner_allowed_harness_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "remediation-run"
            task_id = f"{run_id}-task-1"
            changed_path = "scripts/harness_loop_orchestrator.py"
            target = repo_root / changed_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("# harness remediation\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "--", changed_path],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                ["git", "commit", "-m", "test: harness remediation", "--", changed_path],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            commit_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout.strip()
            run = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Repair harness",
                run_id=run_id,
                domain="ai_infra",
                confirm=True,
            )
            run.update(
                {
                    "phase": "cleanup",
                    "task_id": task_id,
                    "autonomous_commit_state": {
                        "status": "committed",
                        "commit": commit_sha,
                        "created_by": "harness_loop_orchestrator",
                        "changed_paths": [changed_path],
                        "run_id": run_id,
                        "task_id": task_id,
                    },
                }
            )
            save_run(repo_root, run)
            run_dir = run_dir_for(repo_root, run_id)
            write_json_file(
                run_dir / "planner-output.json",
                {
                    "task_id": task_id,
                    "policy": "autonomous_knowledge",
                    "task_kind": "autonomous_implementation_task",
                    "title": "Repair harness",
                    "goal": "Allow active remediation harness paths.",
                    "non_goals": [],
                    "allowed_paths": [changed_path],
                    "denylist_paths": [],
                    "verify_commands": [],
                    "evaluator_scenarios_path": "",
                    "stop_conditions": [],
                    "next_planning_hint": "",
                    "skill_invocations": [],
                },
            )
            write_json_file(
                run_dir / "commit-result.json",
                {
                    "status": "pass",
                    "commit": commit_sha,
                    "error": "",
                    "created_by": "harness_loop_orchestrator",
                    "changed_paths": [changed_path],
                    "run_id": run_id,
                    "task_id": task_id,
                },
            )
            generator_result = {
                "task_id": task_id,
                "status": "implemented",
                "changed_paths": [changed_path],
                "commit": commit_sha,
                "verify_commands": [],
                "verify_results": [],
                "artifacts": [changed_path],
                "cleanup_required": False,
                "notes": "Current planner explicitly allowed a harness remediation path.",
                "skill_invocations": [],
            }

            with patch.object(harness_loop_orchestrator, "_run_wiki_validate", return_value=True):
                committed = harness_loop_orchestrator._commit_autonomous_changes(
                    repo_root,
                    run,
                    generator_result,
                    bounded=True,
                )

            self.assertTrue(committed)
            scope_result = read_json_file(run_dir / "autonomous-scope-result.json")
            self.assertTrue(scope_result["allowed"])
            self.assertIn(changed_path, scope_result["allowed_paths"])
            self.assertNotIn(changed_path, scope_result["manual_confirm_paths"])

    def test_resume_autonomous_push_block_rejects_stale_generator_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "demo-run"
            task_id = "demo-run-task"
            run = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id=run_id,
                domain="ai_infra",
                confirm=True,
            )
            run.update(
                {
                    "phase": "stopped_blocked",
                    "task_id": task_id,
                    "next_action": "retry_autonomous_push",
                    "last_result": "blocked",
                    "autonomous_commit_state": {
                        "status": "committed",
                        "commit": "abc123",
                        "created_by": "harness_loop_orchestrator",
                        "changed_paths": ["personal-wiki/domains/ai_infra/raw/loop-autonomous/push.md"],
                        "run_id": run_id,
                        "task_id": task_id,
                    },
                }
            )
            save_run(repo_root, run)
            write_json_file(
                run_dir_for(repo_root, run_id) / "generator-result.json",
                {
                    "task_id": "stale-task",
                    "status": "implemented",
                    "changed_paths": ["personal-wiki/domains/ai_infra/raw/loop-autonomous/push.md"],
                    "commit": "abc123",
                    "verify_commands": [],
                    "verify_results": [],
                    "artifacts": [],
                    "cleanup_required": False,
                    "notes": "Stale generator output must not drive push retry.",
                    "skill_invocations": [],
                },
            )

            with patch.object(harness_loop_orchestrator, "_push_autonomous_commit") as push_commit:
                resumed = harness_loop_orchestrator._resume_autonomous_push_block(repo_root, run)

            self.assertFalse(resumed)
            push_commit.assert_not_called()

    def test_bounded_push_rejects_stale_generator_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "bounded-push-run"
            task_id = "bounded-push-run-task"
            run = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id=run_id,
                domain="ai_infra",
                confirm=True,
            )
            run.update(
                {
                    "phase": "committed",
                    "next_action": "push_autonomous_commit",
                    "task_id": task_id,
                }
            )
            save_run(repo_root, run)
            commit_sha = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout.strip()
            write_json_file(
                run_dir_for(repo_root, run_id) / "generator-result.json",
                {
                    "task_id": "stale-task",
                    "status": "implemented",
                    "changed_paths": [],
                    "commit": commit_sha,
                    "verify_commands": [],
                    "verify_results": [],
                    "artifacts": [],
                    "cleanup_required": False,
                    "notes": "Stale generator output must not drive bounded push.",
                    "skill_invocations": [],
                },
            )
            request = ActionRequest(
                action_id="bounded-push-stale-generator",
                run_id=run_id,
                run_revision=0,
                policy="autonomous_knowledge",
                phase="committed",
                action_type=ActionType.PUSH,
                idempotency_key="bounded-push-stale-generator",
                task_id=task_id,
                next_action="push_autonomous_commit",
                payload={},
            )

            with patch.object(harness_loop_orchestrator, "_push_autonomous_commit") as push_commit:
                result = harness_loop_orchestrator._run_bounded_push(repo_root, request)

            self.assertIsNot(result.result_class, ActionResultClass.SUCCESS)
            self.assertIn("stale-task", result.summary)
            push_commit.assert_not_called()

    def test_run_autonomous_blocks_and_records_commit_failure(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            with patch("scripts.harness_loop_orchestrator.run_git_commit", side_effect=RuntimeError("commit failed")):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=3,
                )

            self.assertEqual(status["phase"], "stopped_blocked")
            run_dir = run_dir_for(repo_root, "demo-run")
            run = read_json_file(run_dir / "run.json")
            commit_result = read_json_file(run_dir / "commit-result.json")
            self.assertEqual(run["next_action"], "inspect_autonomous_commit")
            self.assertEqual(commit_result["status"], "blocked")
            self.assertIn("commit failed", commit_result["error"])

    def test_run_autonomous_retries_a_transient_commit_failure_once(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "demo-run"
            run = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id=run_id,
                domain="ai_infra",
                confirm=True,
            )
            task_id = f"{run_id}-task-1"
            changed_path = "personal-wiki/domains/ai_infra/raw/loop-autonomous/retry.md"
            target = repo_root / changed_path
            target.parent.mkdir(parents=True)
            target.write_text("# Retry commit\n", encoding="utf-8")
            run.update(
                {
                    "phase": "stopped_blocked",
                    "next_action": "inspect_autonomous_commit",
                    "last_result": "blocked",
                    "task_id": task_id,
                }
            )
            save_run(repo_root, run)
            run_dir = run_dir_for(repo_root, run_id)
            write_json_file(
                run_dir / "generator-result.json",
                {
                    "task_id": task_id,
                    "status": "implemented",
                    "changed_paths": [changed_path],
                    "commit": "",
                    "verify_commands": [],
                    "verify_results": [],
                    "artifacts": [changed_path],
                    "cleanup_required": False,
                    "notes": "Retry a transient commit failure.",
                    "skill_invocations": [],
                },
            )
            write_json_file(
                run_dir / "commit-result.json",
                {
                    "status": "blocked",
                    "commit": "",
                    "error": "transient index lock",
                    "created_by": "harness_loop_orchestrator",
                },
            )

            status = run_autonomous(
                repo_root,
                run_id,
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=1,
            )

            self.assertEqual(status["phase"], "stopped_budget")
            saved = load_run(repo_root, run_id)
            self.assertEqual(saved["_autonomous_commit_retries_by_task"], {task_id: 1})
            commit_result = read_json_file(run_dir / "commit-result.json")
            self.assertEqual(commit_result["status"], "pass")
            self.assertTrue(commit_result["commit"])

    def test_run_autonomous_records_commit_stderr(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")
            commit_error = subprocess.CalledProcessError(
                128,
                ["git", "commit"],
                stderr=b"fatal: Unable to create '.git/index.lock': File exists.\n",
            )

            with patch("scripts.harness_loop_orchestrator.run_git_commit", side_effect=commit_error):
                status = run_autonomous(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            self.assertEqual(status["phase"], "stopped_blocked")
            commit_result = read_json_file(run_dir_for(repo_root, "demo-run") / "commit-result.json")
            self.assertIn("index.lock", commit_result["error"])

    def test_run_autonomous_blocks_denylist_changed_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake-denylist",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=1,
            )

            self.assertEqual(status["phase"], "stopped_blocked")
            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["last_result"], "blocked")
            self.assertEqual(run["next_action"], "inspect_autonomous_scope")

    def test_run_autonomous_blocks_dependency_change_without_supply_chain_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            status = run_autonomous(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake-dependency",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=1,
            )

            self.assertEqual(status["phase"], "stopped_blocked")
            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["last_result"], "blocked")
            self.assertEqual(run["next_action"], "inspect_supply_chain")

    def test_run_autonomous_blocks_expanded_policy_without_gap_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            status = run_autonomous(
                repo_root,
                "expanded-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=1,
            )

            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "inspect_required_evidence")

    def test_run_autonomous_blocks_expanded_policy_missing_required_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

            def inject_direct_gap_proof_only(
                repo_root_arg: Path,
                run: dict[str, object],
                *,
                driver: str,
                task_number: int,
            ) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                task_id = str(run["task_id"])
                gap_proof_relative = f".codex/loop-runs/{run['run_id']}/gap-proofs/{task_id}.json"
                write_json_file(repo_root_arg / gap_proof_relative, self._valid_gap_proof_payload(task_id))
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_direct_gap_proof_only,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "inspect_required_evidence")
            self.assertFalse(
                (run_dir_for(repo_root, "expanded-run") / "required-evidence-manifest.json").exists()
            )

    def test_run_autonomous_accepts_gap_proof_manifest_entry_for_current_task_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

            def inject_manifest(repo_root_arg: Path, run: dict[str, object], *, driver: str, task_number: int) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                task_id = str(run["task_id"])
                artifact_relative = "docs/harness/gap-proofs/current-task-gap-proof.json"
                self._write_required_evidence_manifest(
                    repo_root_arg,
                    run,
                    gap_proof_artifact_relative=artifact_relative,
                )
                manifest_path = run_dir_for(repo_root_arg, str(run["run_id"])) / "required-evidence-manifest.json"
                manifest = read_json_file(manifest_path)
                for item in manifest["items"]:
                    if "gap proof" in str(item.get("summary", "")).lower():
                        item["evidence_id"] = "gap-proof"
                        item["task_id"] = task_id
                        item["artifacts"] = [artifact_relative]
                write_json_file(manifest_path, manifest)
                payload["changed_paths"] = [*list(payload["changed_paths"]), artifact_relative]
                payload["artifacts"] = [*list(payload["artifacts"]), artifact_relative]
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_manifest,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            gap_proof_result = read_json_file(run_dir_for(repo_root, "expanded-run") / "gap-proof-result.json")
            self.assertNotEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(gap_proof_result["status"], "pass")
            self.assertEqual(gap_proof_result["task_id"], "expanded-run-task-1")
            self.assertEqual(gap_proof_result["artifact_path"], "docs/harness/gap-proofs/current-task-gap-proof.json")
            self.assertEqual(gap_proof_result["findings"], [])

    def test_run_autonomous_accepts_current_gap_proof_when_parent_gap_proof_is_listed_first(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

            def inject_manifest_with_parent_and_current_gap_proofs(
                repo_root_arg: Path,
                run: dict[str, object],
                *,
                driver: str,
                task_number: int,
            ) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                task_id = str(run["task_id"])
                parent_artifact_relative = "docs/harness/gap-proofs/parent-16-gap-proof.json"
                current_artifact_relative = "docs/harness/gap-proofs/current-task-gap-proof.json"
                self._write_required_evidence_manifest(
                    repo_root_arg,
                    run,
                    gap_proof_artifact_relative=current_artifact_relative,
                )
                write_json_file(
                    repo_root_arg / parent_artifact_relative,
                    self._valid_gap_proof_payload("expanded-run-parent-16"),
                )
                manifest_path = run_dir_for(repo_root_arg, str(run["run_id"])) / "required-evidence-manifest.json"
                manifest = read_json_file(manifest_path)
                for item in manifest["items"]:
                    if "gap proof" in str(item.get("summary", "")).lower():
                        item["evidence_id"] = "gap-proof"
                        item["task_id"] = task_id
                        item["artifacts"] = [parent_artifact_relative, current_artifact_relative]
                write_json_file(manifest_path, manifest)
                payload["changed_paths"] = [
                    *list(payload["changed_paths"]),
                    parent_artifact_relative,
                    current_artifact_relative,
                ]
                payload["artifacts"] = [
                    *list(payload["artifacts"]),
                    parent_artifact_relative,
                    current_artifact_relative,
                ]
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_manifest_with_parent_and_current_gap_proofs,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            gap_proof_result = read_json_file(run_dir_for(repo_root, "expanded-run") / "gap-proof-result.json")
            self.assertNotEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(gap_proof_result["status"], "pass")
            self.assertEqual(gap_proof_result["task_id"], "expanded-run-task-1")
            self.assertEqual(gap_proof_result["artifact_path"], "docs/harness/gap-proofs/current-task-gap-proof.json")
            self.assertEqual(gap_proof_result["findings"], [])

    def test_run_autonomous_accepts_run_dir_relative_gap_proof_manifest_artifact(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

            def inject_manifest(repo_root_arg: Path, run: dict[str, object], *, driver: str, task_number: int) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                task_id = str(run["task_id"])
                artifact_relative = f"gap-proofs/{task_id}.json"
                self._write_required_evidence_manifest(
                    repo_root_arg,
                    run,
                    gap_proof_artifact_relative=artifact_relative,
                )
                manifest_path = run_dir_for(repo_root_arg, str(run["run_id"])) / "required-evidence-manifest.json"
                manifest = read_json_file(manifest_path)
                root_level_artifact = repo_root_arg / artifact_relative
                if root_level_artifact.exists():
                    root_level_artifact.unlink()
                write_json_file(
                    run_dir_for(repo_root_arg, str(run["run_id"])) / artifact_relative,
                    self._valid_gap_proof_payload(task_id),
                )
                for item in manifest["items"]:
                    if item.get("evidence_id") == "gap-proof":
                        item["summary"] = "validated"
                        item["artifacts"] = [artifact_relative]
                write_json_file(manifest_path, manifest)
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_manifest,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            gap_proof_result = read_json_file(run_dir_for(repo_root, "expanded-run") / "gap-proof-result.json")
            required_evidence_result = read_json_file(
                run_dir_for(repo_root, "expanded-run") / "required-evidence-result.json"
            )
            self.assertNotEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(required_evidence_result["status"], "pass")
            self.assertEqual(gap_proof_result["status"], "pass")
            self.assertTrue(gap_proof_result["artifact_path"].endswith("/gap-proofs/expanded-run-task-1.json"))
            self.assertEqual(gap_proof_result["findings"], [])

    def test_run_autonomous_blocks_expanded_policy_missing_service_availability_manifest_item(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

            def inject_manifest(repo_root_arg: Path, run: dict[str, object], *, driver: str, task_number: int) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                self._write_required_evidence_manifest(repo_root_arg, run, include_service_availability=False)
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_manifest,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            required_evidence_result = read_json_file(
                run_dir_for(repo_root, "expanded-run") / "required-evidence-result.json"
            )
            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "inspect_required_evidence")
            self.assertTrue(
                any("service availability evidence" in finding for finding in required_evidence_result["findings"]),
                required_evidence_result,
            )

    def test_run_autonomous_blocks_expanded_policy_invalid_required_evidence_manifest_payload(self) -> None:
        original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

        for manifest_contents, expected_finding in (
            ("{not-json", "could not be parsed as JSON"),
            ('["not-an-object"]\n', "must contain an object payload"),
        ):
            with self.subTest(manifest_contents=manifest_contents):
                with tempfile.TemporaryDirectory() as tmp:
                    repo_root = Path(tmp)
                    init_git_repo(repo_root)
                    policy_file = self._seed_policy_fixture(
                        repo_root,
                        "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
                    )
                    shutil.rmtree(run_dir_for(repo_root, "expanded-run"), ignore_errors=True)
                    create_preflight_run(
                        repo_root=repo_root,
                        mode="autonomous-knowledge",
                        requirement="Expand wiki",
                        run_id="expanded-run",
                        domain="ai_infra",
                        confirm=True,
                        policy_file=policy_file,
                    )
                    seed_candidate_loop_state(repo_root, "ai_infra")

                    def inject_manifest(
                        repo_root_arg: Path,
                        run: dict[str, object],
                        *,
                        driver: str,
                        task_number: int,
                    ) -> dict[str, object]:
                        payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                        manifest_path = run_dir_for(repo_root_arg, str(run["run_id"])) / "required-evidence-manifest.json"
                        manifest_path.write_text(manifest_contents, encoding="utf-8")
                        write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                        return payload

                    with patch(
                        "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                        side_effect=inject_manifest,
                    ), patch(
                        "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                        side_effect=self._trusted_live_state_from_manifest,
                    ):
                        status = run_autonomous(
                            repo_root,
                            "expanded-run",
                            planner_driver="fake",
                            generator_driver="fake",
                            evaluator_driver="fake",
                            max_eval_attempts=2,
                            max_tasks=1,
                        )

                    required_evidence_result = read_json_file(
                        run_dir_for(repo_root, "expanded-run") / "required-evidence-result.json"
                    )
                    self.assertEqual(status["phase"], "stopped_blocked")
                    self.assertEqual(status["next_action"], "inspect_required_evidence")
                    self.assertEqual(required_evidence_result["status"], "blocked")
                    self.assertTrue(
                        any(expected_finding in finding for finding in required_evidence_result["findings"]),
                        required_evidence_result,
                    )

    def test_validate_required_evidence_blocks_empty_manifest_object(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run = {"run_id": "demo-run"}
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(run_dir / "required-evidence-manifest.json", {})

            result = harness_loop_orchestrator._validate_required_evidence(
                repo_root,
                run,
                ["service availability evidence"],
            )

            self.assertEqual(result["status"], "blocked")
            self.assertTrue(
                any("must contain an items list" in finding for finding in result["findings"]),
                result,
            )

    def test_validate_required_evidence_blocks_manifest_for_other_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = run_dir_for(repo_root, "expanded-run")
            run_dir.mkdir(parents=True, exist_ok=True)
            write_json_file(run_dir / "artifacts" / "secret-scan.json", {"status": "pass"})
            write_json_file(
                run_dir / "required-evidence-manifest.json",
                {
                    "run_id": "expanded-run",
                    "task_id": "stale-task",
                    "items": [
                        {
                            "evidence_id": "secret-scan",
                            "status": "pass",
                            "summary": "secret scan captured",
                            "artifacts": ["artifacts/secret-scan.json"],
                        }
                    ],
                },
            )
            run = {
                "run_id": "expanded-run",
                "task_id": "current-task",
                "domain": "ai_infra",
            }

            result = harness_loop_orchestrator._validate_required_evidence(
                repo_root,
                run,
                ["secret scan evidence"],
            )

            self.assertEqual(result["status"], "blocked")
            self.assertTrue(
                any("stale-task" in finding and "current-task" in finding for finding in result["findings"]),
                result,
            )

    def test_validate_required_evidence_blocks_manifest_without_current_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = run_dir_for(repo_root, "expanded-run")
            run_dir.mkdir(parents=True, exist_ok=True)
            write_json_file(run_dir / "artifacts" / "secret-scan.json", {"status": "pass"})
            write_json_file(
                run_dir / "required-evidence-manifest.json",
                {
                    "items": [
                        {
                            "evidence_id": "secret-scan",
                            "status": "pass",
                            "summary": "secret scan captured",
                            "artifacts": ["artifacts/secret-scan.json"],
                        }
                    ],
                },
            )
            run = {
                "run_id": "expanded-run",
                "task_id": "current-task",
                "domain": "ai_infra",
            }

            result = harness_loop_orchestrator._validate_required_evidence(
                repo_root,
                run,
                ["secret scan evidence"],
            )

            self.assertEqual(result["status"], "blocked")
            self.assertTrue(
                any("missing current run_id" in finding for finding in result["findings"]),
                result,
            )
            self.assertTrue(
                any("missing current task_id" in finding for finding in result["findings"]),
                result,
            )

    def test_run_autonomous_blocks_expanded_policy_empty_required_evidence_manifest_object(self) -> None:
        original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            shutil.rmtree(run_dir_for(repo_root, "expanded-run"), ignore_errors=True)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            def inject_manifest(
                repo_root_arg: Path,
                run: dict[str, object],
                *,
                driver: str,
                task_number: int,
            ) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                manifest_path = run_dir_for(repo_root_arg, str(run["run_id"])) / "required-evidence-manifest.json"
                write_json_file(manifest_path, {})
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_manifest,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            required_evidence_result = read_json_file(
                run_dir_for(repo_root, "expanded-run") / "required-evidence-result.json"
            )
            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(required_evidence_result["status"], "blocked")
            self.assertTrue(
                any("must contain an items list" in finding for finding in required_evidence_result["findings"]),
                required_evidence_result,
            )

    def test_run_autonomous_allows_expanded_policy_with_required_evidence_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

            def inject_manifest(repo_root_arg: Path, run: dict[str, object], *, driver: str, task_number: int) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                self._write_required_evidence_manifest(repo_root_arg, run)
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_manifest,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            required_evidence_result = read_json_file(
                run_dir_for(repo_root, "expanded-run") / "required-evidence-result.json"
            )
            self.assertNotEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(required_evidence_result["status"], "pass")
            self.assertEqual(required_evidence_result["findings"], [])

            manifest_payload = read_json_file(run_dir_for(repo_root, "expanded-run") / "required-evidence-manifest.json")
            expected_ids = {
                self.REQUIRED_EVIDENCE_STABLE_IDS[str(requirement).lower()]
                for requirement in load_run(repo_root, "expanded-run")["required_evidence"]
            }
            actual_ids = {str(item["evidence_id"]) for item in manifest_payload["items"]}
            self.assertEqual(actual_ids, expected_ids)
            for item in manifest_payload["items"]:
                self.assertNotEqual(item["summary"], item["evidence_id"])
                self.assertNotIn("evidence for", str(item["summary"]).lower())

    def test_run_autonomous_parent_task_cadence_does_not_run_legacy_auditor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")
            run = load_run(repo_root, "expanded-run")
            run["audit_cadence"] = {"unit": "parent_task", "mode": "fixed_interval", "interval": 2}
            save_run(repo_root, run)

            with patch(
                "scripts.harness_loop_orchestrator.decide_no_action",
                return_value=NoActionDecision(False, ["forced actionable candidate"]),
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=2,
                )

            self.assertEqual(status["phase"], "stopped_budget")
            report_paths = sorted((run_dir_for(repo_root, "expanded-run") / "audit-reports").glob("audit-*.json"))
            self.assertEqual(report_paths, [])
            run = load_run(repo_root, "expanded-run")
            self.assertNotIn("_audit_cadence_state", run)

    def test_create_preflight_run_copies_audit_cadence_from_policy_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            policy_path = repo_root / policy_file
            policy = read_json_file(policy_path)
            policy["audit_cadence"] = {"unit": "parent_task", "mode": "fixed_interval", "interval": 2}
            write_json_file(policy_path, policy)

            run = create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )

            self.assertEqual(
                run["audit_cadence"],
                {"unit": "parent_task", "mode": "fixed_interval", "interval": 2},
            )

    def test_run_autonomous_materializes_embedded_required_evidence_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

            def inject_embedded_manifest(
                repo_root_arg: Path,
                run: dict[str, object],
                *,
                driver: str,
                task_number: int,
            ) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                self._write_required_evidence_manifest(repo_root_arg, run)
                manifest_path = run_dir_for(repo_root_arg, str(run["run_id"])) / "required-evidence-manifest.json"
                payload["required_evidence_manifest"] = read_json_file(manifest_path)
                manifest_path.unlink()
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_embedded_manifest,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            required_evidence_result = read_json_file(
                run_dir_for(repo_root, "expanded-run") / "required-evidence-result.json"
            )
            self.assertNotEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(required_evidence_result["status"], "pass")
            self.assertTrue((run_dir_for(repo_root, "expanded-run") / "required-evidence-manifest.json").exists())

    def test_run_autonomous_materializes_embedded_gap_proof_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

            def inject_embedded_manifest(
                repo_root_arg: Path,
                run: dict[str, object],
                *,
                driver: str,
                task_number: int,
            ) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                self._write_required_evidence_manifest(repo_root_arg, run)
                manifest_path = run_dir_for(repo_root_arg, str(run["run_id"])) / "required-evidence-manifest.json"
                manifest = read_json_file(manifest_path)
                for item in manifest["items"]:
                    if item.get("evidence_id") == "gap-proof":
                        item.pop("task_id", None)
                payload["required_evidence_manifest"] = manifest
                manifest_path.unlink()
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_embedded_manifest,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            gap_proof_result = read_json_file(run_dir_for(repo_root, "expanded-run") / "gap-proof-result.json")
            manifest = read_json_file(run_dir_for(repo_root, "expanded-run") / "required-evidence-manifest.json")
            self.assertNotEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(gap_proof_result["status"], "pass")
            gap_proof_items = [item for item in manifest["items"] if item.get("evidence_id") == "gap-proof"]
            self.assertEqual(len(gap_proof_items), 1)
            self.assertEqual(gap_proof_items[0]["task_id"], "expanded-run-task-1")

    def test_run_autonomous_expanded_policy_blocks_synthetic_live_gate_placeholders(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            status = run_autonomous(
                repo_root,
                "expanded-run",
                planner_driver="fake",
                generator_driver="fake-expanded-code",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=2,
            )

            run_dir = run_dir_for(repo_root, "expanded-run")
            run = read_json_file(run_dir / "run.json")
            generator_result = read_json_file(run_dir / "generator-result.json")
            required_evidence_result = read_json_file(run_dir / "required-evidence-result.json")
            manifest_payload = read_json_file(run_dir / "required-evidence-manifest.json")
            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(run["last_result"], "blocked")
            self.assertEqual(required_evidence_result["status"], "blocked")
            self.assertFalse((run_dir / "commit-result.json").exists())
            self.assertFalse(generator_result["commit"])
            self.assertIn("scripts/ai_infra_expanded_runtime_smoke.txt", generator_result["changed_paths"])
            self.assertIn("personal-wiki/domains/ai_infra/coverage-map.json", generator_result["changed_paths"])
            self.assertTrue((repo_root / "scripts" / "ai_infra_expanded_runtime_smoke.txt").exists())
            coverage_map = read_json_file(repo_root / "personal-wiki" / "domains" / "ai_infra" / "coverage-map.json")
            self.assertEqual(coverage_map["domain"], "ai_infra")
            self.assertEqual(coverage_map["domain_goal"], "Expand wiki")
            self.assertEqual(set(coverage_map["layers"]), {
                "training-distributed",
                "inference-runtime",
                "orchestration-scheduling",
                "data-rag-vector",
                "eval-observability-reliability",
                "security-governance-cost",
                "hardware-accelerator",
                "network-storage-cluster",
            })
            for layer_payload in coverage_map["layers"].values():
                self.assertEqual(layer_payload["status"], "covered")
                self.assertEqual(layer_payload["candidate_gaps"], [])
            expected_ids = {
                self.REQUIRED_EVIDENCE_STABLE_IDS[str(requirement).lower()]
                for requirement in run["required_evidence"]
            }
            actual_ids = {str(item["evidence_id"]) for item in manifest_payload["items"]}
            self.assertEqual(actual_ids, expected_ids)
            expected_blocked_ids = {
                "crawler-workbench-freshness",
                "loop-dashboard-freshness",
                "service-availability",
            }
            manifest_by_id = {str(item["evidence_id"]): item for item in manifest_payload["items"]}
            for evidence_id in expected_blocked_ids:
                with self.subTest(evidence_id=evidence_id):
                    self.assertEqual(manifest_by_id[evidence_id]["status"], "blocked")
                    self.assertIn("synthetic", str(manifest_by_id[evidence_id]["summary"]).lower())
            for evidence_id in {"search-api-visibility", "frontend-visibility"}:
                with self.subTest(evidence_id=evidence_id):
                    self.assertEqual(manifest_by_id[evidence_id]["status"], "pass")
            for evidence_id in {"crawler-workbench-freshness", "loop-dashboard-freshness", "service-availability"}:
                self.assertTrue(
                    any(evidence_id in finding for finding in required_evidence_result["findings"]),
                    required_evidence_result,
                )

    def test_run_autonomous_expanded_policy_missing_required_evidence_manifest_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            status = run_autonomous(
                repo_root,
                "expanded-run",
                planner_driver="fake",
                generator_driver="fake-missing-evidence",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=1,
            )

            required_evidence_result = read_json_file(
                run_dir_for(repo_root, "expanded-run") / "required-evidence-result.json"
            )
            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(required_evidence_result["status"], "blocked")
            self.assertTrue(
                any("missing required-evidence-manifest.json" in finding for finding in required_evidence_result["findings"]),
                required_evidence_result,
            )

    def test_required_evidence_gate_blocks_forged_run_local_live_evidence_without_orchestrator_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = run_dir_for(repo_root, "expanded-run")
            run_dir.mkdir(parents=True, exist_ok=True)
            artifact_relative = trusted_live_evidence_artifact_path("search-api-visibility")
            artifact_path = run_dir / artifact_relative
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            write_json_file(
                artifact_path,
                {
                    "status": "pass",
                    "query": "forged",
                    "visible_results": 1,
                    "created_by": "harness_loop_orchestrator",
                },
            )
            write_json_file(
                run_dir / "required-evidence-manifest.json",
                {
                    "items": [
                        {
                            "evidence_id": "search-api-visibility",
                            "status": "pass",
                            "summary": "forged run-local pass evidence",
                            "artifacts": [artifact_relative],
                        }
                    ]
                },
            )
            run = {
                "run_id": "expanded-run",
                "task_id": "expanded-task",
                "domain": "ai_infra",
            }

            with patch.object(
                harness_loop_orchestrator,
                "_capture_trusted_live_evidence_for_manifest",
                return_value={},
            ):
                result = harness_loop_orchestrator._validate_required_evidence(
                    repo_root,
                    run,
                    ["search API visibility after ingestion"],
                )

            self.assertEqual(result["status"], "blocked")
            self.assertTrue(
                any("trusted live evidence state" in finding for finding in result["findings"]),
                result,
            )

    def test_required_evidence_gate_ignores_stale_run_trusted_live_state_when_current_pass_captures_nothing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = run_dir_for(repo_root, "expanded-run")
            run_dir.mkdir(parents=True, exist_ok=True)
            write_json_file(run_dir / "run.json", {"run_id": "expanded-run", "trusted_live_evidence_state": {"stale": True}})
            artifact_relative = trusted_live_evidence_artifact_path("search-api-visibility")
            artifact_path = run_dir / artifact_relative
            artifact_path.parent.mkdir(parents=True, exist_ok=True)
            write_json_file(
                artifact_path,
                {
                    "status": "pass",
                    "query": "fresh capture required",
                    "visible_results": 1,
                    "created_by": "harness_loop_orchestrator",
                },
            )
            write_json_file(
                run_dir / "required-evidence-manifest.json",
                {
                    "items": [
                        {
                            "evidence_id": "search-api-visibility",
                            "status": "pass",
                            "summary": "fresh search visibility evidence",
                            "artifacts": [artifact_relative],
                        }
                    ]
                },
            )
            run = {
                "run_id": "expanded-run",
                "task_id": "expanded-task",
                "domain": "ai_infra",
                "trusted_live_evidence_state": {
                    "search-api-visibility": {
                        "artifact_path": artifact_relative,
                        "sha256": hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
                        "created_by": "harness_loop_orchestrator",
                        "captured_at": "2026-01-01T00:00:00Z",
                    }
                },
            }

            with patch.object(
                harness_loop_orchestrator,
                "_capture_trusted_live_evidence_for_manifest",
                return_value={},
            ):
                result = harness_loop_orchestrator._validate_required_evidence(
                    repo_root,
                    run,
                    ["search API visibility after ingestion"],
                )

            self.assertEqual(result["status"], "blocked")
            self.assertTrue(
                any("trusted live evidence state" in finding for finding in result["findings"]),
                result,
            )
            persisted_run = read_json_file(run_dir / "run.json")
            self.assertEqual(persisted_run["trusted_live_evidence_state"], {})
            self.assertEqual(run["trusted_live_evidence_state"], {})

    def test_required_evidence_gate_clears_stale_live_state_when_manifest_missing_or_unparseable(self) -> None:
        for manifest_contents in (None, "{not-json"):
            with self.subTest(manifest_contents=manifest_contents), tempfile.TemporaryDirectory() as tmp:
                repo_root = Path(tmp)
                run_dir = run_dir_for(repo_root, "expanded-run")
                run_dir.mkdir(parents=True, exist_ok=True)
                stale_state = {"search-api-visibility": {"artifact_path": "stale.json"}}
                write_json_file(
                    run_dir / "run.json",
                    {"run_id": "expanded-run", "trusted_live_evidence_state": stale_state},
                )
                if manifest_contents is not None:
                    (run_dir / "required-evidence-manifest.json").write_text(manifest_contents, encoding="utf-8")
                run = {
                    "run_id": "expanded-run",
                    "task_id": "expanded-task",
                    "domain": "ai_infra",
                    "trusted_live_evidence_state": stale_state,
                }

                result = harness_loop_orchestrator._validate_required_evidence(
                    repo_root,
                    run,
                    ["search API visibility after ingestion"],
                )

                self.assertEqual(result["status"], "blocked")
                persisted_run = read_json_file(run_dir / "run.json")
                self.assertEqual(persisted_run["trusted_live_evidence_state"], {})
                self.assertEqual(run["trusted_live_evidence_state"], {})

    def test_capture_live_search_visibility_matches_current_changed_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "expanded-run"
            run_dir_for(repo_root, run_id).mkdir(parents=True, exist_ok=True)
            relative_path = self._seed_visibility_target(repo_root, run_id=run_id)
            run = {
                "run_id": run_id,
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(
                url: str,
                timeout_seconds: float = 2.0,
                max_body_bytes: int = 16 * 1024 * 1024,
            ) -> dict[str, object]:
                del timeout_seconds, max_body_bytes
                return {
                    "url": url,
                    "status": "pass",
                    "http_status": 200,
                    "json": {
                        "results": [
                            {
                                "title": "Expanded Runtime Smoke",
                                "path": relative_path,
                                "snippet": "Tensorlake schedulerproof rdmawatch evidence",
                            }
                        ]
                    },
                }

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "search-api-visibility",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["query"], "Expanded Runtime Smoke")
            self.assertEqual(payload["run_id"], run_id)
            self.assertEqual(payload["task_id"], "expanded-run-task-1")
            self.assertEqual(payload["domain"], "ai_infra")
            self.assertEqual(payload["expected_targets"][0]["path"], relative_path)
            self.assertEqual(payload["matched_targets"][0]["path"], relative_path)
            self.assertEqual(payload["missing_targets"], [])

    def test_capture_live_search_visibility_ignores_domain_ingest_log(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "expanded-run"
            run_dir_for(repo_root, run_id).mkdir(parents=True, exist_ok=True)
            relative_path = self._seed_visibility_target(
                repo_root,
                run_id=run_id,
                relative_path="personal-wiki/domains/ai_infra/wiki/references/expanded-runtime-smoke.md",
            )
            ingest_path = "personal-wiki/domains/ai_infra/ingest.md"
            (repo_root / ingest_path).write_text("# Ingest Log\n\n- pending progress active\n", encoding="utf-8")
            generator_result = read_json_file(run_dir_for(repo_root, run_id) / "generator-result.json")
            generator_result["changed_paths"] = [ingest_path, relative_path]
            write_json_file(run_dir_for(repo_root, run_id) / "generator-result.json", generator_result)
            run = {
                "run_id": run_id,
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(
                url: str,
                timeout_seconds: float = 2.0,
                max_body_bytes: int = 16 * 1024 * 1024,
            ) -> dict[str, object]:
                del timeout_seconds, max_body_bytes
                return {
                    "url": url,
                    "status": "pass",
                    "http_status": 200,
                    "json": {
                        "results": [
                            {
                                "title": "Expanded Runtime Smoke",
                                "path": relative_path,
                                "snippet": "Tensorlake schedulerproof rdmawatch evidence",
                            }
                        ]
                    },
                }

            context = harness_loop_orchestrator._visibility_context(repo_root, run)
            self.assertNotIn(ingest_path, [target["path"] for target in context["expected_targets"]])

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "search-api-visibility",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["matched_targets"][0]["path"], relative_path)
            self.assertEqual(payload["missing_targets"], [])

    def test_capture_live_search_visibility_ignores_raw_ingest_plan(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "expanded-run"
            run_dir_for(repo_root, run_id).mkdir(parents=True, exist_ok=True)
            relative_path = self._seed_visibility_target(
                repo_root,
                run_id=run_id,
                relative_path="personal-wiki/domains/ai_infra/wiki/references/expanded-runtime-smoke.md",
            )
            ingest_plan_path = (
                "personal-wiki/domains/ai_infra/raw/crawler/source-a/"
                "capture.ingest-plan.md"
            )
            (repo_root / ingest_plan_path).parent.mkdir(parents=True, exist_ok=True)
            (repo_root / ingest_plan_path).write_text("# Ingest Plan\n\n- promoted source\n", encoding="utf-8")
            generator_result = read_json_file(run_dir_for(repo_root, run_id) / "generator-result.json")
            generator_result["changed_paths"] = [ingest_plan_path, relative_path]
            write_json_file(run_dir_for(repo_root, run_id) / "generator-result.json", generator_result)
            run = {
                "run_id": run_id,
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(
                url: str,
                timeout_seconds: float = 2.0,
                max_body_bytes: int = 16 * 1024 * 1024,
            ) -> dict[str, object]:
                del timeout_seconds, max_body_bytes
                return {
                    "url": url,
                    "status": "pass",
                    "http_status": 200,
                    "json": {
                        "results": [
                            {
                                "title": "Expanded Runtime Smoke",
                                "path": relative_path,
                                "snippet": "Tensorlake schedulerproof rdmawatch evidence",
                            }
                        ]
                    },
                }

            context = harness_loop_orchestrator._visibility_context(repo_root, run)
            self.assertNotIn(ingest_plan_path, [target["path"] for target in context["expected_targets"]])

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "search-api-visibility",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["matched_targets"][0]["path"], relative_path)
            self.assertEqual(payload["missing_targets"], [])

    def test_capture_live_search_visibility_blocks_stale_generic_ai_infra_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "expanded-run"
            run_dir_for(repo_root, run_id).mkdir(parents=True, exist_ok=True)
            relative_path = self._seed_visibility_target(repo_root, run_id=run_id)
            run = {
                "run_id": run_id,
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(
                url: str,
                timeout_seconds: float = 2.0,
                max_body_bytes: int = 16 * 1024 * 1024,
            ) -> dict[str, object]:
                del timeout_seconds, max_body_bytes
                return {
                    "url": url,
                    "status": "pass",
                    "http_status": 200,
                    "json": {
                        "results": [
                            {
                                "title": "AI Infra Overview",
                                "path": "personal-wiki/domains/ai_infra/index.md",
                            }
                        ]
                    },
                }

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "search-api-visibility",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["query"], "Expanded Runtime Smoke")
            self.assertEqual(payload["expected_targets"][0]["path"], relative_path)
            self.assertEqual(payload["matched_targets"], [])
            self.assertEqual(payload["missing_targets"][0]["path"], relative_path)

    def test_capture_live_search_visibility_blocks_declared_target_when_git_worktree_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_id = "expanded-run"
            run_dir_for(repo_root, run_id).mkdir(parents=True, exist_ok=True)
            relative_path = self._seed_visibility_target(repo_root, run_id=run_id)
            run = {
                "run_id": run_id,
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(
                url: str,
                timeout_seconds: float = 2.0,
                max_body_bytes: int = 16 * 1024 * 1024,
            ) -> dict[str, object]:
                del timeout_seconds, max_body_bytes
                return {
                    "url": url,
                    "status": "pass",
                    "http_status": 200,
                    "json": {
                        "results": [
                            {
                                "title": "Expanded Runtime Smoke",
                                "path": relative_path,
                                "snippet": "Tensorlake schedulerproof rdmawatch evidence",
                            }
                        ]
                    },
                }

            with (
                patch.object(harness_loop_orchestrator, "_git_worktree_available", return_value=False),
                patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe),
            ):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "search-api-visibility",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["expected_targets"], [])
            self.assertEqual(payload["matched_targets"], [])
            self.assertEqual(payload["probes"], [])
            self.assertIn("no current knowledge targets", payload["summary"])
            self.assertEqual(payload["missing_targets"][0]["changed_paths"], [])
            self.assertIn(relative_path, payload["missing_targets"][0]["declared_changed_paths"])

    def test_capture_live_search_visibility_blocks_declared_clean_wiki_target_with_old_indexed_content(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "expanded-run"
            run_dir_for(repo_root, run_id).mkdir(parents=True, exist_ok=True)
            relative_path = self._seed_visibility_target(repo_root, run_id=run_id)
            subprocess.run(
                ["git", "add", "--", relative_path],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                ["git", "commit", "-m", "test: seed old indexed wiki page", "--", relative_path],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            run = {
                "run_id": run_id,
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
                "baseline_dirty_paths": [],
            }

            def fake_probe(
                url: str,
                timeout_seconds: float = 2.0,
                max_body_bytes: int = 16 * 1024 * 1024,
            ) -> dict[str, object]:
                del timeout_seconds, max_body_bytes
                return {
                    "url": url,
                    "status": "pass",
                    "http_status": 200,
                    "json": {
                        "results": [
                            {
                                "title": "Expanded Runtime Smoke",
                                "path": relative_path,
                                "snippet": "Tensorlake schedulerproof rdmawatch evidence",
                            }
                        ]
                    },
                }

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "search-api-visibility",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["expected_targets"], [])
            self.assertEqual(payload["matched_targets"], [])
            self.assertIn(relative_path, str(payload["missing_targets"]))

    def test_visibility_blocks_historical_generator_commit_without_current_dirty_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "expanded-run"
            run_dir_for(repo_root, run_id).mkdir(parents=True, exist_ok=True)
            relative_path = self._seed_visibility_target(repo_root, run_id=run_id)
            subprocess.run(
                ["git", "add", "--", relative_path],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                ["git", "commit", "-m", "test: historical visibility target", "--", relative_path],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            historical_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ).stdout.strip()
            (repo_root / "README.md").write_text("temporary repo\ncurrent head\n", encoding="utf-8")
            subprocess.run(
                ["git", "commit", "-am", "test: advance current head"],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            generator_result_path = run_dir_for(repo_root, run_id) / "generator-result.json"
            generator_result = read_json_file(generator_result_path)
            generator_result["commit"] = historical_commit
            write_json_file(generator_result_path, generator_result)
            run = {
                "run_id": run_id,
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
                "baseline_dirty_paths": [],
            }

            def fake_probe(url: str, timeout_seconds: float = 2.0, **_kwargs: object) -> dict[str, object]:
                del timeout_seconds
                if url == "http://127.0.0.1:5173/":
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "body_excerpt": "<html>Crawler Workbench</html>",
                        "json": None,
                    }
                return {
                    "url": url,
                    "status": "pass",
                    "http_status": 200,
                    "json": {
                        "results": [
                            {
                                "title": "Expanded Runtime Smoke",
                                "path": relative_path,
                                "snippet": "Tensorlake schedulerproof rdmawatch evidence",
                            }
                        ]
                    },
                }

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                search_payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "search-api-visibility",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )
                wiki_payload = harness_loop_orchestrator._capture_targeted_wiki_visibility(
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                    wiki_page_base_url="http://127.0.0.1:8765/api/wiki/page",
                    fallback_search_base_url="http://127.0.0.1:8765/api/search",
                    repo_root=repo_root,
                )
                frontend_payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "frontend-visibility",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                    repo_root=repo_root,
                )

            for payload in (search_payload, wiki_payload, frontend_payload):
                with self.subTest(summary=payload["summary"]):
                    self.assertEqual(payload["status"], "blocked")
                    self.assertEqual(payload["expected_targets"], [])
                    self.assertEqual(payload["matched_targets"], [])
                    self.assertEqual(payload["missing_targets"][0]["changed_paths"], [])
                    self.assertIn(relative_path, payload["missing_targets"][0]["declared_changed_paths"])

    def test_capture_live_search_visibility_blocks_partial_match_across_two_changed_targets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "expanded-run"
            run_dir_for(repo_root, run_id).mkdir(parents=True, exist_ok=True)
            relative_paths = self._seed_visibility_targets(
                repo_root,
                run_id=run_id,
                targets=[
                    {
                        "title": "Expanded Runtime Smoke",
                        "path": "personal-wiki/domains/ai_infra/runtime/expanded-runtime-smoke.md",
                        "body": "Tensorlake schedulerproof rdmawatch evidence.\n",
                    },
                    {
                        "title": "Expanded Runtime Followup",
                        "path": "personal-wiki/domains/ai_infra/runtime/expanded-runtime-followup.md",
                        "body": "Linkmesh cacheguard topologyseal evidence.\n",
                    },
                ],
            )
            run = {
                "run_id": run_id,
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(url: str, timeout_seconds: float = 2.0, **_kwargs: object) -> dict[str, object]:
                del timeout_seconds
                return {
                    "url": url,
                    "status": "pass",
                    "http_status": 200,
                    "json": {
                        "results": [
                            {
                                "title": "Expanded Runtime Smoke",
                                "path": relative_paths[0],
                                "snippet": "Tensorlake schedulerproof rdmawatch evidence",
                            }
                        ]
                    },
                }

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "search-api-visibility",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(len(payload["expected_targets"]), 2)
            self.assertEqual(len(payload["matched_targets"]), 1)
            self.assertEqual(payload["matched_targets"][0]["path"], relative_paths[0])
            self.assertEqual(payload["missing_targets"][0]["path"], relative_paths[1])

    def test_capture_live_search_visibility_blocks_path_title_match_without_current_content_terms(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "expanded-run"
            run_dir_for(repo_root, run_id).mkdir(parents=True, exist_ok=True)
            relative_path = self._seed_visibility_target(
                repo_root,
                run_id=run_id,
                body="Tensorlake schedulerproof rdmawatch evidence.\n",
            )
            run = {
                "run_id": run_id,
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(url: str, timeout_seconds: float = 2.0, **_kwargs: object) -> dict[str, object]:
                del timeout_seconds
                return {
                    "url": url,
                    "status": "pass",
                    "http_status": 200,
                    "json": {
                        "results": [
                            {
                                "title": "Expanded Runtime Smoke",
                                "path": relative_path,
                                "description": "Old indexed summary without the new runtime terms",
                                "snippet": "Expanded runtime smoke legacy summary",
                            }
                        ]
                    },
                }

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "search-api-visibility",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["matched_targets"], [])
            self.assertEqual(payload["missing_targets"][0]["path"], relative_path)

    def test_content_terms_from_markdown_returns_empty_for_title_only_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            page_path = Path(tmp) / "title-only.md"
            page_path.write_text("# Expanded Runtime Smoke\n", encoding="utf-8")

            terms = harness_loop_orchestrator._content_terms_from_markdown(
                page_path,
                title="Expanded Runtime Smoke",
            )

            self.assertEqual(terms, [])

    def test_content_terms_from_markdown_returns_empty_when_body_only_repeats_title_tokens(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            page_path = Path(tmp) / "duplicate-title.md"
            page_path.write_text(
                "# Expanded Runtime Smoke\n\nExpanded runtime smoke runtime expanded smoke.\n",
                encoding="utf-8",
            )

            terms = harness_loop_orchestrator._content_terms_from_markdown(
                page_path,
                title="Expanded Runtime Smoke",
            )

            self.assertEqual(terms, [])

    def test_content_terms_from_markdown_returns_empty_for_non_ascii_body_without_ascii_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            page_path = Path(tmp) / "non-ascii-body.md"
            page_path.write_text(
                "# 模型运行时可见性\n\n这是最新的运行时证据，没有英文关键词。\n",
                encoding="utf-8",
            )

            terms = harness_loop_orchestrator._content_terms_from_markdown(
                page_path,
                title="模型运行时可见性",
            )

            self.assertEqual(terms, [])

    def test_match_visibility_target_rejects_wiki_page_without_body_derived_content_terms(self) -> None:
        target = {
            "target_id": "wiki:personal-wiki/domains/ai_infra/wiki/expanded-runtime-smoke.md",
            "kind": "wiki_page",
            "path": "personal-wiki/domains/ai_infra/wiki/expanded-runtime-smoke.md",
            "title": "Expanded Runtime Smoke",
            "identity_terms": [
                "personal-wiki/domains/ai_infra/wiki/expanded-runtime-smoke.md",
                "Expanded Runtime Smoke",
            ],
            "content_terms": [],
        }

        match = harness_loop_orchestrator._match_visibility_target(
            {
                "results": [
                    {
                        "title": "Expanded Runtime Smoke",
                        "path": "personal-wiki/domains/ai_infra/wiki/expanded-runtime-smoke.md",
                        "snippet": "Expanded runtime smoke legacy summary",
                    }
                ]
            },
            target,
            query="Expanded Runtime Smoke",
        )

        self.assertIsNone(match)

    def test_match_visibility_target_accepts_marked_raw_path_cited_by_curated_result(self) -> None:
        target = {
            "target_id": "raw_path:personal-wiki/domains/ai_infra/raw/links/vllm-readme-official-20260707.md",
            "kind": "raw_path",
            "path": "personal-wiki/domains/ai_infra/raw/links/vllm-readme-official-20260707.md",
            "title": "",
            "identity_terms": [
                "personal-wiki/domains/ai_infra/raw/links/vllm-readme-official-20260707.md",
                "vllm-readme-official-20260707.md",
                "vllm readme official 20260707",
            ],
            "content_terms": [],
        }

        match = harness_loop_orchestrator._match_visibility_target(
            {
                "results": [
                    {
                        "title": "Inference Runtime Infrastructure",
                        "path": "domains/ai_infra/wiki/references/inference-runtime-infrastructure.md",
                        "snippet": "../../raw/links/<mark>vllm</mark>-<mark>readme</mark>-<mark>official</mark>-<mark>20260707</mark>.md",
                    }
                ]
            },
            target,
            query="vllm readme official 20260707",
        )

        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match["target_id"], target["target_id"])
        self.assertEqual(match["path"], target["path"])
        self.assertEqual(match["result_value"], "domains/ai_infra/wiki/references/inference-runtime-infrastructure.md")

    def test_match_visibility_target_accepts_raw_path_truncated_in_returned_wiki_page(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            page_path = (
                repo_root
                / "personal-wiki"
                / "domains"
                / "ai_infra"
                / "wiki"
                / "references"
                / "evaluation-observability-reliability-infrastructure.md"
            )
            page_path.parent.mkdir(parents=True, exist_ok=True)
            page_path.write_text(
                "source_refs:\n"
                "  - ../../raw/links/lm-evaluation-harness-official-20260707.md\n",
                encoding="utf-8",
            )
            target = {
                "target_id": "raw_path:personal-wiki/domains/ai_infra/raw/links/lm-evaluation-harness-official-20260707.md",
                "kind": "raw_path",
                "path": "personal-wiki/domains/ai_infra/raw/links/lm-evaluation-harness-official-20260707.md",
                "title": "",
                "identity_terms": [
                    "personal-wiki/domains/ai_infra/raw/links/lm-evaluation-harness-official-20260707.md",
                    "lm-evaluation-harness-official-20260707.md",
                    "lm evaluation harness official 20260707",
                ],
                "content_terms": [],
            }

            match = harness_loop_orchestrator._match_visibility_target(
                {
                    "results": [
                        {
                            "title": "Evaluation Observability Reliability Infrastructure",
                            "path": "domains/ai_infra/wiki/references/evaluation-observability-reliability-infrastructure.md",
                            "snippet": "../../raw/links/<mark>lm</mark>-<mark>evaluati",
                        }
                    ]
                },
                target,
                query="lm evaluation harness official 20260707",
                repo_root=repo_root,
            )

        self.assertIsNotNone(match)
        assert match is not None
        self.assertEqual(match["target_id"], target["target_id"])
        self.assertEqual(match["path"], target["path"])
        self.assertEqual(
            match["result_value"],
            "domains/ai_infra/wiki/references/evaluation-observability-reliability-infrastructure.md",
        )

    def test_capture_live_search_visibility_blocks_title_only_wiki_page_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "expanded-run"
            run_dir_for(repo_root, run_id).mkdir(parents=True, exist_ok=True)
            relative_path = self._seed_visibility_target(
                repo_root,
                run_id=run_id,
                title="Expanded Runtime Smoke",
                body="",
            )
            run = {
                "run_id": run_id,
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(url: str, timeout_seconds: float = 2.0, **_kwargs: object) -> dict[str, object]:
                del timeout_seconds
                return {
                    "url": url,
                    "status": "pass",
                    "http_status": 200,
                    "json": {
                        "results": [
                            {
                                "title": "Expanded Runtime Smoke",
                                "path": relative_path,
                                "snippet": "Expanded runtime smoke legacy summary",
                            }
                        ]
                    },
                }

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "search-api-visibility",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["matched_targets"], [])
            self.assertEqual(payload["missing_targets"][0]["path"], relative_path)

    def test_capture_live_search_visibility_blocks_duplicate_title_token_body_match(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "expanded-run"
            run_dir_for(repo_root, run_id).mkdir(parents=True, exist_ok=True)
            relative_path = self._seed_visibility_target(
                repo_root,
                run_id=run_id,
                title="Expanded Runtime Smoke",
                body="Expanded runtime smoke runtime expanded smoke.\n",
            )
            run = {
                "run_id": run_id,
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(url: str, timeout_seconds: float = 2.0, **_kwargs: object) -> dict[str, object]:
                del timeout_seconds
                return {
                    "url": url,
                    "status": "pass",
                    "http_status": 200,
                    "json": {
                        "results": [
                            {
                                "title": "Expanded Runtime Smoke",
                                "path": relative_path,
                                "snippet": "Expanded runtime smoke legacy summary",
                            }
                        ]
                    },
                }

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "search-api-visibility",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["matched_targets"], [])
            self.assertEqual(payload["missing_targets"][0]["path"], relative_path)

    def test_capture_live_search_visibility_blocks_non_ascii_wiki_page_without_ascii_body_proof(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "expanded-run"
            run_dir_for(repo_root, run_id).mkdir(parents=True, exist_ok=True)
            relative_path = self._seed_visibility_target(
                repo_root,
                run_id=run_id,
                title="模型运行时可见性",
                body="这是最新的运行时证据，没有英文关键词。\n",
            )
            run = {
                "run_id": run_id,
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(url: str, timeout_seconds: float = 2.0, **_kwargs: object) -> dict[str, object]:
                del timeout_seconds
                return {
                    "url": url,
                    "status": "pass",
                    "http_status": 200,
                    "json": {
                        "results": [
                            {
                                "title": "模型运行时可见性",
                                "path": relative_path,
                                "snippet": "模型运行时可见性 旧索引摘要",
                            }
                        ]
                    },
                }

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "search-api-visibility",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["matched_targets"], [])
            self.assertEqual(payload["missing_targets"][0]["path"], relative_path)

    def test_capture_live_frontend_visibility_blocks_loaded_root_without_current_target(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "expanded-run"
            run_dir_for(repo_root, run_id).mkdir(parents=True, exist_ok=True)
            relative_path = self._seed_visibility_target(repo_root, run_id=run_id)
            run = {
                "run_id": run_id,
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(url: str, timeout_seconds: float = 2.0, **_kwargs: object) -> dict[str, object]:
                del timeout_seconds
                if url == "http://127.0.0.1:5173/":
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "body_excerpt": "<html>Crawler Workbench</html>",
                        "json": None,
                    }
                return {
                    "url": url,
                    "status": "pass",
                    "http_status": 200,
                    "json": {
                        "results": [
                            {
                                "title": "AI Infra Overview",
                                "path": "personal-wiki/domains/ai_infra/index.md",
                            }
                        ]
                    },
                }

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "frontend-visibility",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["page_url"], "http://127.0.0.1:5173/")
            self.assertEqual(payload["route"], "/api/search")
            self.assertEqual(payload["expected_targets"][0]["path"], relative_path)
            self.assertEqual(payload["matched_targets"], [])
            self.assertEqual(payload["missing_targets"][0]["path"], relative_path)

    def test_capture_live_crawler_freshness_blocks_http_200_without_current_target_discoverability(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            run_id = "expanded-run"
            run_dir_for(repo_root, run_id).mkdir(parents=True, exist_ok=True)
            relative_path = self._seed_visibility_target(repo_root, run_id=run_id)
            run = {
                "run_id": run_id,
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(url: str, timeout_seconds: float = 2.0, **_kwargs: object) -> dict[str, object]:
                del timeout_seconds
                payload = {
                    "url": url,
                    "status": "pass",
                    "http_status": 200,
                    "json": [],
                }
                if "/api/wiki/page" in url:
                    payload["json"] = {
                        "path": "runtime/other-page.md",
                        "full_path": "personal-wiki/domains/ai_infra/wiki/runtime/other-page.md",
                        "title": "Other page",
                        "body": "old content only",
                    }
                elif "/api/search" in url:
                    payload["json"] = {
                        "results": [
                            {
                                "title": "AI Infra Overview",
                                "path": "personal-wiki/domains/ai_infra/index.md",
                                "snippet": "generic ai_infra result",
                            }
                        ]
                    }
                return payload

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "crawler-workbench-freshness",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["run_id"], run_id)
            self.assertEqual(payload["details"]["sources"]["status"], "pass")
            self.assertEqual(payload["details"]["search"]["status"], "blocked")
            self.assertEqual(payload["details"]["wiki"]["status"], "blocked")
            self.assertEqual(payload["details"]["search"]["missing_targets"][0]["path"], relative_path)

    def test_capture_live_loop_dashboard_freshness_blocks_http_200_for_wrong_run_and_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run = {
                "run_id": "expanded-run",
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(url: str, timeout_seconds: float = 2.0, **_kwargs: object) -> dict[str, object]:
                del timeout_seconds
                if url.endswith("/api/runs/expanded-run"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {
                            "run_id": "other-run",
                            "project_root": "/tmp/other-project",
                            "source_path": ".worktrees/other/.codex/loop-runs/other-run",
                        },
                    }
                if url.endswith("/api/runs/expanded-run/events"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {"run_id": "other-run", "events": []},
                    }
                if url.endswith("/api/runs/expanded-run/logs"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {"run_id": "other-run", "logs": []},
                    }
                if url.endswith("/api/projects/current"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {"project_root": "/tmp/other-project"},
                    }
                if url.endswith("/api/runs"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": [{"run_id": "other-run"}],
                    }
                return {"url": url, "status": "pass", "http_status": 200, "json": {}}

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "loop-dashboard-freshness",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["run_id"], "expanded-run")
            self.assertEqual(payload["details"]["current_run"]["status"], "blocked")
            self.assertEqual(payload["details"]["completed_history"]["status"], "blocked")
            self.assertEqual(payload["details"]["project"]["status"], "blocked")

    def test_capture_live_loop_dashboard_freshness_allows_active_run_without_completed_history(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run = {
                "run_id": "expanded-run",
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(url: str, timeout_seconds: float = 2.0, max_body_bytes: int = 16 * 1024 * 1024) -> dict[str, object]:
                del timeout_seconds, max_body_bytes
                if url.endswith("/api/runs/expanded-run"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {
                            "run_id": "expanded-run",
                            "project_root": str(repo_root),
                            "source_path": ".codex/loop-runs/expanded-run",
                            "completed": False,
                            "children_summary": {"total": 0},
                        },
                    }
                if url.endswith("/api/runs/expanded-run/events"):
                    return {"url": url, "status": "pass", "http_status": 200, "json": {"run_id": "expanded-run", "events": []}}
                if url.endswith("/api/runs/expanded-run/logs"):
                    return {"url": url, "status": "pass", "http_status": 200, "json": {"run_id": "expanded-run", "logs": []}}
                if url.endswith("/api/projects/current"):
                    return {"url": url, "status": "pass", "http_status": 200, "json": {"project_root": str(repo_root)}}
                if url.endswith("/api/runs"):
                    return {"url": url, "status": "blocked", "http_status": 0, "error": "timed out"}
                return {"url": url, "status": "pass", "http_status": 200, "json": {}}

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "loop-dashboard-freshness",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["details"]["current_run"]["status"], "pass")
            self.assertEqual(payload["details"]["completed_history"]["status"], "not_applicable")

    def test_capture_live_loop_dashboard_freshness_allows_truncated_logs_when_run_id_matches(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run = {
                "run_id": "expanded-run",
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(url: str, timeout_seconds: float = 2.0, max_body_bytes: int = 16 * 1024 * 1024) -> dict[str, object]:
                del timeout_seconds, max_body_bytes
                if url.endswith("/api/runs/expanded-run"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {
                            "run_id": "expanded-run",
                            "project_root": str(repo_root),
                            "source_path": ".codex/loop-runs/expanded-run",
                            "completed": False,
                            "children_summary": {"total": 0},
                        },
                    }
                if url.endswith("/api/runs/expanded-run/events"):
                    return {"url": url, "status": "pass", "http_status": 200, "json": {"run_id": "expanded-run", "events": []}}
                if url.endswith("/api/runs/expanded-run/logs"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": None,
                        "body_excerpt": '{"run_id":"expanded-run","logs":[{"source":"large.log","stream":"stdout","content":"',
                    }
                if url.endswith("/api/projects/current"):
                    return {"url": url, "status": "pass", "http_status": 200, "json": {"project_root": str(repo_root)}}
                if url.endswith("/api/runs"):
                    return {"url": url, "status": "blocked", "http_status": 0, "error": "timed out"}
                return {"url": url, "status": "pass", "http_status": 200, "json": {}}

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "loop-dashboard-freshness",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["details"]["evaluator_scenarios"]["status"], "pass")
            self.assertEqual(payload["details"]["evaluator_scenarios"]["json"]["run_id"], "expanded-run")
            self.assertTrue(payload["details"]["evaluator_scenarios"]["json"]["logs_truncated"])

    def test_capture_live_loop_dashboard_freshness_accepts_cursor_page_envelopes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run = {
                "run_id": "expanded-run",
                "task_id": "expanded-run-task-2",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def page(items: list[dict[str, object]]) -> dict[str, object]:
                return {
                    "items": items,
                    "total": len(items),
                    "page_size": 20,
                    "has_more": False,
                    "next_cursor": None,
                    "previous_cursor": None,
                }

            def fake_probe(
                url: str,
                timeout_seconds: float = 2.0,
                max_body_bytes: int = 16 * 1024 * 1024,
            ) -> dict[str, object]:
                del timeout_seconds, max_body_bytes
                if url.endswith("/api/runs/expanded-run"):
                    body: object = {
                        "run_id": "expanded-run",
                        "project_root": str(repo_root),
                        "source_path": ".codex/loop-runs/expanded-run",
                        "phase": "stopped_blocked",
                        "completed": True,
                        "children_summary": {"total": 0},
                    }
                elif url.endswith("/api/runs/expanded-run/events"):
                    body = page([{"event_id": "event-1", "message": "Evaluator passed"}])
                elif url.endswith("/api/runs/expanded-run/logs"):
                    body = page([{"log_id": "log-1", "source": "evaluator.log"}])
                elif url.endswith("/api/projects/current"):
                    body = {"project_root": str(repo_root)}
                elif url.endswith("/api/runs"):
                    body = page(
                        [
                            {
                                "run_id": "expanded-run",
                                "project_root": str(repo_root),
                                "source_path": ".codex/loop-runs/expanded-run",
                            }
                        ]
                    )
                else:
                    body = {}
                return {"url": url, "status": "pass", "http_status": 200, "json": body}

            with patch.object(
                harness_loop_orchestrator, "_http_probe", side_effect=fake_probe
            ):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "loop-dashboard-freshness",
                    run=run,
                    captured_at="2026-07-15T14:00:00Z",
                )

            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["details"]["agent_actions"]["status"], "pass")
            self.assertEqual(payload["details"]["agent_actions"]["json"]["run_id"], "expanded-run")
            self.assertEqual(payload["details"]["evaluator_scenarios"]["status"], "pass")
            self.assertEqual(payload["details"]["completed_history"]["status"], "pass")

    def test_capture_live_loop_dashboard_freshness_uses_longer_timeout_for_events(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run = {
                "run_id": "expanded-run",
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(url: str, timeout_seconds: float = 2.0, max_body_bytes: int = 16 * 1024 * 1024) -> dict[str, object]:
                del max_body_bytes
                if url.endswith("/api/runs/expanded-run"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {
                            "run_id": "expanded-run",
                            "project_root": str(repo_root),
                            "source_path": ".codex/loop-runs/expanded-run",
                            "completed": False,
                            "children_summary": {"total": 0},
                        },
                    }
                if url.endswith("/api/runs/expanded-run/events"):
                    if timeout_seconds <= 2.0:
                        return {"url": url, "status": "fail", "http_status": None, "error": "timed out"}
                    return {"url": url, "status": "pass", "http_status": 200, "json": {"run_id": "expanded-run", "events": []}}
                if url.endswith("/api/runs/expanded-run/logs"):
                    return {"url": url, "status": "pass", "http_status": 200, "json": {"run_id": "expanded-run", "logs": []}}
                if url.endswith("/api/projects/current"):
                    return {"url": url, "status": "pass", "http_status": 200, "json": {"project_root": str(repo_root)}}
                if url.endswith("/api/runs"):
                    return {"url": url, "status": "blocked", "http_status": 0, "error": "timed out"}
                return {"url": url, "status": "pass", "http_status": 200, "json": {}}

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "loop-dashboard-freshness",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["details"]["agent_actions"]["status"], "pass")

    def test_capture_live_loop_dashboard_freshness_uses_longer_timeout_for_detail_and_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run = {
                "run_id": "expanded-run",
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }
            detail_call_count = 0

            def fake_probe(url: str, timeout_seconds: float = 2.0, max_body_bytes: int = 16 * 1024 * 1024) -> dict[str, object]:
                nonlocal detail_call_count
                if url.endswith("/api/runs/expanded-run"):
                    detail_call_count += 1
                    if timeout_seconds <= 10.0:
                        return {"url": url, "status": "fail", "http_status": None, "error": "timed out"}
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {
                            "run_id": "expanded-run",
                            "project_root": str(repo_root),
                            "source_path": ".codex/loop-runs/expanded-run",
                            "completed": False,
                            "children_summary": {"total": 0},
                        },
                    }
                if url.endswith("/api/runs/expanded-run/events"):
                    return {"url": url, "status": "pass", "http_status": 200, "json": {"run_id": "expanded-run", "events": []}}
                if url.endswith("/api/runs/expanded-run/logs"):
                    if timeout_seconds <= 10.0 or max_body_bytes > 64 * 1024:
                        return {"url": url, "status": "fail", "http_status": None, "error": "timed out"}
                    return {"url": url, "status": "pass", "http_status": 200, "json": {"run_id": "expanded-run", "logs": []}}
                if url.endswith("/api/projects/current"):
                    return {"url": url, "status": "pass", "http_status": 200, "json": {"project_root": str(repo_root)}}
                if url.endswith("/api/runs"):
                    return {"url": url, "status": "blocked", "http_status": 0, "error": "timed out"}
                return {"url": url, "status": "pass", "http_status": 200, "json": {}}

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "loop-dashboard-freshness",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["details"]["current_run"]["status"], "pass")
            self.assertEqual(payload["details"]["child_tasks"]["status"], "pass")
            self.assertEqual(payload["details"]["evaluator_scenarios"]["status"], "pass")
            self.assertEqual(detail_call_count, 1)

    def test_http_probe_parses_large_json_response(self) -> None:
        body = json.dumps(
            {
                "run_id": "expanded-run",
                "logs": [
                    {
                        "source": "large.log",
                        "stream": "stdout",
                        "content": "x" * 70000,
                    }
                ],
            }
        ).encode("utf-8")

        class FakeResponse:
            status = 200

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self, size: int = -1) -> bytes:
                return body if size < 0 else body[:size]

        with patch.object(harness_loop_orchestrator, "urlopen", return_value=FakeResponse()):
            payload = harness_loop_orchestrator._http_probe("http://127.0.0.1:8766/api/runs/expanded-run/logs")

        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["json"]["run_id"], "expanded-run")

    def test_http_probe_parses_multimegabyte_json_response(self) -> None:
        body = json.dumps(
            {
                "run_id": "expanded-run",
                "logs": [
                    {
                        "source": "large.log",
                        "stream": "stdout",
                        "content": "x" * (5 * 1024 * 1024),
                    }
                ],
            }
        ).encode("utf-8")

        class FakeResponse:
            status = 200

            def __enter__(self) -> "FakeResponse":
                return self

            def __exit__(self, *args: object) -> None:
                return None

            def read(self, size: int = -1) -> bytes:
                return body if size < 0 else body[:size]

        with patch.object(harness_loop_orchestrator, "urlopen", return_value=FakeResponse()):
            payload = harness_loop_orchestrator._http_probe("http://127.0.0.1:8766/api/runs/expanded-run/logs")

        self.assertEqual(payload["status"], "pass")
        self.assertEqual(payload["json"]["run_id"], "expanded-run")
        self.assertEqual(len(payload["json"]["logs"][0]["content"]), 5 * 1024 * 1024)

    def test_capture_live_loop_dashboard_freshness_blocks_empty_current_child_id_without_child_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run = {
                "run_id": "expanded-run",
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(url: str, timeout_seconds: float = 2.0, **_kwargs: object) -> dict[str, object]:
                del timeout_seconds
                if url.endswith("/api/runs/expanded-run"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {
                            "run_id": "expanded-run",
                            "current_child_run_id": "",
                        },
                    }
                if url.endswith("/api/runs/expanded-run/events"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {"run_id": "expanded-run", "events": []},
                    }
                if url.endswith("/api/runs/expanded-run/logs"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {"run_id": "expanded-run", "logs": []},
                    }
                if url.endswith("/api/projects/current"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {"project_root": str(repo_root)},
                    }
                if url.endswith("/api/runs"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": [{"run_id": "expanded-run"}],
                    }
                return {"url": url, "status": "pass", "http_status": 200, "json": {}}

            with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                payload = harness_loop_orchestrator._capture_live_evidence_payload(
                    "loop-dashboard-freshness",
                    run=run,
                    captured_at="2026-07-07T00:00:00Z",
                )

            self.assertEqual(payload["status"], "blocked")
            self.assertEqual(payload["run_id"], "expanded-run")
            self.assertEqual(payload["details"]["current_run"]["status"], "pass")
            self.assertEqual(payload["details"]["child_tasks"]["status"], "blocked")

    def test_capture_live_loop_dashboard_freshness_accepts_relative_repo_root_and_empty_children_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp).resolve()
            init_git_repo(repo_root)
            run = {
                "run_id": "expanded-run",
                "task_id": "expanded-run-task-1",
                "domain": "ai_infra",
                "worktree": str(repo_root),
            }

            def fake_probe(url: str, timeout_seconds: float = 2.0, **_kwargs: object) -> dict[str, object]:
                del timeout_seconds
                if url.endswith("/api/runs/expanded-run"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {
                            "run_id": "expanded-run",
                            "project_root": str(repo_root),
                            "source_path": ".codex/loop-runs/expanded-run",
                            "children_summary": {
                                "total": 0,
                                "passed": 0,
                                "failed": 0,
                                "blocked": 0,
                                "pending": 0,
                            },
                            "current_child_run_id": "",
                        },
                    }
                if url.endswith("/api/runs/expanded-run/events"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {"run_id": "expanded-run", "events": []},
                    }
                if url.endswith("/api/runs/expanded-run/logs"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {"run_id": "expanded-run", "logs": []},
                    }
                if url.endswith("/api/projects/current"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": {"project_root": str(repo_root)},
                    }
                if url.endswith("/api/runs"):
                    return {
                        "url": url,
                        "status": "pass",
                        "http_status": 200,
                        "json": [
                            {
                                "run_id": "expanded-run",
                                "project_root": str(repo_root),
                                "source_path": ".codex/loop-runs/expanded-run",
                            }
                        ],
                    }
                return {"url": url, "status": "pass", "http_status": 200, "json": {}}

            original_cwd = Path.cwd()
            try:
                os.chdir(repo_root)
                with patch.object(harness_loop_orchestrator, "_http_probe", side_effect=fake_probe):
                    payload = harness_loop_orchestrator._capture_live_evidence_payload(
                        "loop-dashboard-freshness",
                        run=run,
                        captured_at="2026-07-07T00:00:00Z",
                        repo_root=Path("."),
                    )
            finally:
                os.chdir(original_cwd)

            self.assertEqual(payload["status"], "pass")
            self.assertEqual(payload["worktree"], str(repo_root))
            self.assertEqual(payload["details"]["current_run"]["status"], "pass")
            self.assertEqual(payload["details"]["child_tasks"]["status"], "pass")

    def test_run_autonomous_rejects_expanded_fake_drivers_without_expanded_policy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            for generator_driver in ("fake-expanded-code", "fake-missing-evidence"):
                with self.subTest(generator_driver=generator_driver):
                    with self.assertRaisesRegex(ValueError, "expanded ai_infra policy"):
                        run_autonomous(
                            repo_root,
                            "demo-run",
                            planner_driver="fake",
                            generator_driver=generator_driver,
                            evaluator_driver="fake",
                            max_eval_attempts=2,
                            max_tasks=1,
                        )

    def test_run_autonomous_rejects_expanded_fake_drivers_with_marker_evidence_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            generic_policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge.json",
            )
            expanded_policy = read_json_file(
                Path(__file__).resolve().parents[2]
                / "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json"
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
                policy_file=generic_policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")
            run = load_run(repo_root, "demo-run")
            run["required_evidence"] = list(expanded_policy["required_evidence"])
            write_json_file(run_dir_for(repo_root, "demo-run") / "run.json", run)

            for generator_driver in ("fake-expanded-code", "fake-missing-evidence"):
                with self.subTest(generator_driver=generator_driver):
                    with self.assertRaisesRegex(ValueError, "expanded ai_infra policy"):
                        run_autonomous(
                            repo_root,
                            "demo-run",
                            planner_driver="fake",
                            generator_driver=generator_driver,
                            evaluator_driver="fake",
                            max_eval_attempts=2,
                            max_tasks=1,
                        )

    def test_run_autonomous_rejects_expanded_fake_drivers_with_prefixed_policy_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")
            run = load_run(repo_root, "demo-run")
            run["policy_file"] = f"./{policy_file}"
            write_json_file(run_dir_for(repo_root, "demo-run") / "run.json", run)

            for generator_driver in ("fake-expanded-code", "fake-missing-evidence"):
                with self.subTest(generator_driver=generator_driver):
                    with self.assertRaisesRegex(ValueError, "expanded ai_infra policy"):
                        run_autonomous(
                            repo_root,
                            "demo-run",
                            planner_driver="fake",
                            generator_driver=generator_driver,
                            evaluator_driver="fake",
                            max_eval_attempts=2,
                            max_tasks=1,
                        )

    def test_run_autonomous_expanded_policy_blocks_denylist_changed_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            status = run_autonomous(
                repo_root,
                "expanded-run",
                planner_driver="fake",
                generator_driver="fake-denylist",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_tasks=1,
            )

            self.assertEqual(status["phase"], "stopped_blocked")
            run = read_json_file(run_dir_for(repo_root, "expanded-run") / "run.json")
            scope_result = read_json_file(run_dir_for(repo_root, "expanded-run") / "autonomous-scope-result.json")
            self.assertEqual(run["next_action"], "inspect_autonomous_scope")
            self.assertIn(".env", scope_result["denied_paths"])

    def test_run_autonomous_accepts_direct_gap_proof_file_for_current_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

            def inject_direct_gap_proof(
                repo_root_arg: Path,
                run: dict[str, object],
                *,
                driver: str,
                task_number: int,
            ) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                task_id = str(run["task_id"])
                gap_proof_relative = f".codex/loop-runs/{run['run_id']}/gap-proofs/{task_id}.json"
                self._write_required_evidence_manifest(
                    repo_root_arg,
                    run,
                    gap_proof_artifact_relative=gap_proof_relative,
                )
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_direct_gap_proof,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            gap_proof_result = read_json_file(run_dir_for(repo_root, "expanded-run") / "gap-proof-result.json")
            self.assertNotEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(gap_proof_result["status"], "pass")
            self.assertEqual(gap_proof_result["task_id"], "expanded-run-task-1")
            self.assertTrue(gap_proof_result["artifact_path"].endswith("/gap-proofs/expanded-run-task-1.json"))
            self.assertEqual(gap_proof_result["findings"], [])

    def test_run_autonomous_blocks_direct_gap_proof_file_for_wrong_payload_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

            def inject_wrong_direct_gap_proof(
                repo_root_arg: Path,
                run: dict[str, object],
                *,
                driver: str,
                task_number: int,
            ) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                task_id = str(run["task_id"])
                gap_proof_relative = f".codex/loop-runs/{run['run_id']}/gap-proofs/{task_id}.json"
                self._write_required_evidence_manifest(
                    repo_root_arg,
                    run,
                    gap_proof_artifact_relative=gap_proof_relative,
                    gap_proof_payload_task_id="other-task-9",
                )
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_wrong_direct_gap_proof,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            gap_proof_result = read_json_file(run_dir_for(repo_root, "expanded-run") / "gap-proof-result.json")
            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(gap_proof_result["status"], "blocked")
            self.assertEqual(gap_proof_result["task_id"], "expanded-run-task-1")
            self.assertTrue(
                any(
                    "other-task-9" in finding and "expanded-run-task-1" in finding
                    for finding in gap_proof_result["findings"]
                )
            )

    def test_run_autonomous_blocks_malformed_direct_gap_proof_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

            def inject_malformed_direct_gap_proof(
                repo_root_arg: Path,
                run: dict[str, object],
                *,
                driver: str,
                task_number: int,
            ) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                task_id = str(run["task_id"])
                gap_proof_relative = f".codex/loop-runs/{run['run_id']}/gap-proofs/{task_id}.json"
                self._write_required_evidence_manifest(
                    repo_root_arg,
                    run,
                    gap_proof_artifact_relative=gap_proof_relative,
                )
                (repo_root_arg / gap_proof_relative).write_text("{not-json", encoding="utf-8")
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_malformed_direct_gap_proof,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            run_dir = run_dir_for(repo_root, "expanded-run")
            gap_proof_result = read_json_file(run_dir / "gap-proof-result.json")
            required_evidence_result = read_json_file(run_dir / "required-evidence-result.json")
            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(gap_proof_result["status"], "blocked")
            self.assertTrue(
                any(
                    "gap proof artifact" in finding.lower()
                    and "malformed" in finding.lower()
                    for finding in gap_proof_result["findings"]
                )
            )
            self.assertEqual(required_evidence_result["status"], "blocked")

    def test_run_autonomous_blocks_gap_proof_manifest_for_wrong_task(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

            def inject_wrong_task_manifest(
                repo_root_arg: Path,
                run: dict[str, object],
                *,
                driver: str,
                task_number: int,
            ) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                artifact_relative = "docs/harness/gap-proofs/wrong-task-gap-proof.json"
                self._write_required_evidence_manifest(
                    repo_root_arg,
                    run,
                    gap_proof_artifact_relative=artifact_relative,
                    gap_proof_payload_task_id="other-task-9",
                )
                manifest_path = run_dir_for(repo_root_arg, str(run["run_id"])) / "required-evidence-manifest.json"
                manifest = read_json_file(manifest_path)
                for item in manifest["items"]:
                    if "gap proof" in str(item.get("summary", "")).lower():
                        item["evidence_id"] = "other-task-9-gap-proof"
                        item["task_id"] = "other-task-9"
                        item["artifacts"] = [artifact_relative]
                write_json_file(manifest_path, manifest)
                payload["changed_paths"] = [*list(payload["changed_paths"]), artifact_relative]
                payload["artifacts"] = [*list(payload["artifacts"]), artifact_relative]
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_wrong_task_manifest,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            gap_proof_result = read_json_file(run_dir_for(repo_root, "expanded-run") / "gap-proof-result.json")
            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(gap_proof_result["status"], "blocked")
            self.assertEqual(gap_proof_result["task_id"], "expanded-run-task-1")
            self.assertTrue(
                any(
                    "expanded-run-task-1" in finding and "gap proof" in finding.lower()
                    for finding in gap_proof_result["findings"]
                )
            )

    def test_run_autonomous_blocks_gap_proof_manifest_when_artifact_payload_task_differs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

            def inject_manifest_with_wrong_payload(
                repo_root_arg: Path,
                run: dict[str, object],
                *,
                driver: str,
                task_number: int,
            ) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                task_id = str(run["task_id"])
                artifact_relative = "docs/harness/gap-proofs/current-task-gap-proof.json"
                self._write_required_evidence_manifest(
                    repo_root_arg,
                    run,
                    gap_proof_artifact_relative=artifact_relative,
                    gap_proof_payload_task_id="other-task-9",
                )
                manifest_path = run_dir_for(repo_root_arg, str(run["run_id"])) / "required-evidence-manifest.json"
                manifest = read_json_file(manifest_path)
                for item in manifest["items"]:
                    if "gap proof" in str(item.get("summary", "")).lower():
                        item["evidence_id"] = f"{task_id}-gap-proof"
                        item["task_id"] = task_id
                        item["artifacts"] = [artifact_relative]
                write_json_file(manifest_path, manifest)
                payload["changed_paths"] = [*list(payload["changed_paths"]), artifact_relative]
                payload["artifacts"] = [*list(payload["artifacts"]), artifact_relative]
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_manifest_with_wrong_payload,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            gap_proof_result = read_json_file(run_dir_for(repo_root, "expanded-run") / "gap-proof-result.json")
            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(gap_proof_result["status"], "blocked")
            self.assertEqual(gap_proof_result["task_id"], "expanded-run-task-1")
            self.assertEqual(gap_proof_result["artifact_path"], "docs/harness/gap-proofs/current-task-gap-proof.json")
            self.assertTrue(
                any(
                    "other-task-9" in finding and "expanded-run-task-1" in finding
                    for finding in gap_proof_result["findings"]
                )
            )

    def test_run_autonomous_blocks_malformed_manifest_gap_proof_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

            def inject_malformed_manifest_gap_proof(
                repo_root_arg: Path,
                run: dict[str, object],
                *,
                driver: str,
                task_number: int,
            ) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                task_id = str(run["task_id"])
                direct_gap_proof = run_dir_for(repo_root_arg, str(run["run_id"])) / "gap-proofs" / f"{task_id}.json"
                if direct_gap_proof.exists():
                    direct_gap_proof.unlink()
                artifact_relative = f"gap-proofs/manifest/{task_id}.json"
                self._write_required_evidence_manifest(
                    repo_root_arg,
                    run,
                    gap_proof_artifact_relative=artifact_relative,
                )
                manifest_path = run_dir_for(repo_root_arg, str(run["run_id"])) / "required-evidence-manifest.json"
                manifest = read_json_file(manifest_path)
                for item in manifest["items"]:
                    if "gap proof" in str(item.get("summary", "")).lower():
                        item["evidence_id"] = f"{task_id}-gap-proof"
                        item["task_id"] = task_id
                        item["artifacts"] = [artifact_relative]
                write_json_file(manifest_path, manifest)
                root_level_artifact = repo_root_arg / artifact_relative
                if root_level_artifact.exists():
                    root_level_artifact.unlink()
                run_dir_artifact = run_dir_for(repo_root_arg, str(run["run_id"])) / artifact_relative
                run_dir_artifact.parent.mkdir(parents=True, exist_ok=True)
                run_dir_artifact.write_text("{not-json", encoding="utf-8")
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_malformed_manifest_gap_proof,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            run_dir = run_dir_for(repo_root, "expanded-run")
            gap_proof_result = read_json_file(run_dir / "gap-proof-result.json")
            required_evidence_result = read_json_file(run_dir / "required-evidence-result.json")
            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(gap_proof_result["status"], "blocked")
            self.assertEqual(gap_proof_result["artifact_path"], "gap-proofs/manifest/expanded-run-task-1.json")
            self.assertTrue(
                any(
                    "gap proof artifact" in finding.lower()
                    and "malformed" in finding.lower()
                    for finding in gap_proof_result["findings"]
                )
            )
            self.assertEqual(required_evidence_result["status"], "blocked")

    def test_run_autonomous_blocks_gap_proof_manifest_substring_task_collision(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            policy_file = self._seed_policy_fixture(
                repo_root,
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="expanded-run",
                domain="ai_infra",
                confirm=True,
                policy_file=policy_file,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")

            original_generator = harness_loop_orchestrator._write_fake_autonomous_generator_result

            def inject_substring_collision_manifest(
                repo_root_arg: Path,
                run: dict[str, object],
                *,
                driver: str,
                task_number: int,
            ) -> dict[str, object]:
                payload = original_generator(repo_root_arg, run, driver=driver, task_number=task_number)
                artifact_relative = "docs/harness/gap-proofs/task-10-gap-proof.json"
                self._write_required_evidence_manifest(
                    repo_root_arg,
                    run,
                    gap_proof_artifact_relative=artifact_relative,
                    gap_proof_payload_task_id="expanded-run-task-10",
                )
                manifest_path = run_dir_for(repo_root_arg, str(run["run_id"])) / "required-evidence-manifest.json"
                manifest = read_json_file(manifest_path)
                for item in manifest["items"]:
                    if "gap proof" in str(item.get("summary", "")).lower():
                        item["evidence_id"] = "expanded-run-task-10-gap-proof"
                        item.pop("task_id", None)
                        item["artifacts"] = [artifact_relative]
                write_json_file(manifest_path, manifest)
                payload["changed_paths"] = [*list(payload["changed_paths"]), artifact_relative]
                payload["artifacts"] = [*list(payload["artifacts"]), artifact_relative]
                write_json_file(run_dir_for(repo_root_arg, str(run["run_id"])) / "generator-result.json", payload)
                return payload

            with patch(
                "scripts.harness_loop_orchestrator._write_fake_autonomous_generator_result",
                side_effect=inject_substring_collision_manifest,
            ), patch(
                "scripts.harness_loop_orchestrator._capture_trusted_live_evidence_for_manifest",
                side_effect=self._trusted_live_state_from_manifest,
            ):
                status = run_autonomous(
                    repo_root,
                    "expanded-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_tasks=1,
                )

            gap_proof_result = read_json_file(run_dir_for(repo_root, "expanded-run") / "gap-proof-result.json")
            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(status["next_action"], "inspect_required_evidence")
            self.assertEqual(gap_proof_result["status"], "blocked")
            self.assertEqual(gap_proof_result["task_id"], "expanded-run-task-1")
            self.assertTrue(
                any("missing gap proof manifest entry for current task expanded-run-task-1" == finding for finding in gap_proof_result["findings"])
            )

    def test_run_autonomous_checks_scope_before_supply_chain(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            seed_candidate_loop_state(repo_root, "ai_infra")
            calls: list[str] = []

            from scripts.harness_loop_autonomous import ScopeCheckResult, SupplyChainCheckResult

            def record_scope(*args: object, **kwargs: object) -> ScopeCheckResult:
                calls.append("scope")
                return ScopeCheckResult(True, ["requirements.txt"], [], [], [])

            def record_supply_chain(*args: object, **kwargs: object) -> SupplyChainCheckResult:
                calls.append("supply_chain")
                return SupplyChainCheckResult(False, ["requirements.txt"], ["missing dependency evidence"])

            with patch("scripts.harness_loop_orchestrator.check_autonomous_scope", side_effect=record_scope):
                with patch("scripts.harness_loop_orchestrator.check_supply_chain", side_effect=record_supply_chain):
                    status = run_autonomous(
                        repo_root,
                        "demo-run",
                        planner_driver="fake",
                        generator_driver="fake-dependency",
                        evaluator_driver="fake",
                        max_eval_attempts=2,
                        max_tasks=1,
                    )

            self.assertEqual(status["phase"], "stopped_blocked")
            self.assertEqual(calls, ["scope", "supply_chain"])

    def test_create_preflight_run_accepts_explicit_task_id_for_fake_planner(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            payload = create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the thing",
                run_id="demo-run",
                task_id="explicit-task",
                confirm=True,
            )

            self.assertEqual(payload["task_id"], "explicit-task")
            saved_payload = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(saved_payload["task_id"], "explicit-task")

            from scripts.harness_loop_orchestrator import _run_planner as run_planner

            output_path = run_planner(repo_root, "demo-run", driver="fake")
            planner_output = read_json_file(output_path)
            self.assertEqual(planner_output["task_id"], "explicit-task")
            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["task_id"], "explicit-task")

    def test_cli_preflight_accepts_explicit_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            self.assertEqual(
                call_cli(
                    [
                        "preflight",
                        "--repo-root",
                        str(repo_root),
                        "--mode",
                        "demand-development",
                        "--requirement",
                        "Build through CLI",
                        "--run-id",
                        "demo-run",
                        "--task-id",
                        "explicit-task",
                        "--confirm",
                    ]
                ),
                0,
            )

            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["task_id"], "explicit-task")

    def test_cli_preflight_accepts_constraints_and_stop_conditions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            self.assertEqual(
                call_cli(
                    [
                        "preflight",
                        "--repo-root",
                        str(repo_root),
                        "--mode",
                        "demand-development",
                        "--requirement",
                        "Build through CLI",
                        "--run-id",
                        "demo-run",
                        "--constraint",
                        "Only touch scripts/",
                        "--constraint",
                        "No commits",
                        "--stop-condition",
                        "passed_waiting_human_merge",
                        "--stop-condition",
                        "stopped_blocked",
                        "--confirm",
                    ]
                ),
                0,
            )

            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["constraints"], ["Only touch scripts/", "No commits"])
            self.assertEqual(run["stop_conditions"], ["passed_waiting_human_merge", "stopped_blocked"])

    def test_status_for_run_returns_run_id_policy_phase_next_action_and_task_id(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the thing",
                run_id="demo-run",
                confirm=True,
            )

            status = status_for_run(repo_root=repo_root, run_id="demo-run")

            self.assertEqual(
                status,
                {
                    "run_id": "demo-run",
                    "policy": "demand_development",
                    "phase": "planned",
                    "next_action": "run_planner",
                    "task_id": "",
                },
            )

    def test_fake_planner_writes_valid_planner_output_and_advances_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the planner demo",
                run_id="demo-run",
                constraints=["Keep scope tight"],
                stop_conditions=["passed_waiting_human_merge", "stopped_blocked"],
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_planner as run_planner

            output_path = run_planner(repo_root, "demo-run", driver="fake")

            run_dir = run_dir_for(repo_root, "demo-run")
            self.assertEqual(output_path, run_dir / "planner-output.json")
            planner_output = read_json_file(output_path)
            validate_planner_output_payload(planner_output)
            self.assertEqual(planner_output["policy"], "demand_development")
            self.assertEqual(planner_output["task_kind"], "registered_task")
            self.assertEqual(planner_output["task_id"], "demo-run-task")
            self.assertEqual(planner_output["goal"], "Build the planner demo")
            self.assertEqual(planner_output["stop_conditions"], ["passed_waiting_human_merge", "stopped_blocked"])
            run = read_json_file(run_dir / "run.json")
            validate_run_payload(run)
            self.assertEqual(run["task_id"], "demo-run-task")
            self.assertEqual(run["phase"], "generating")
            self.assertEqual(run["next_action"], "run_generator")
            self.assertEqual(run["attempts"]["planner"], 1)

    def test_run_planner_rejects_unconfirmed_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the planner demo",
                run_id="demo-run",
                confirm=False,
            )
            from scripts.harness_loop_orchestrator import _run_planner as run_planner

            with self.assertRaises(RuntimeError):
                run_planner(repo_root, "demo-run", driver="fake")

    def test_run_planner_rejects_already_planned_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the planner demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")

            with self.assertRaisesRegex(RuntimeError, "generating"):
                run_planner(repo_root, "demo-run", driver="fake")

    def test_run_planner_rejects_after_generation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the planner demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_generator as run_generator, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")

            with self.assertRaisesRegex(RuntimeError, "evaluating"):
                run_planner(repo_root, "demo-run", driver="fake")

    def test_codex_exec_planner_sets_run_task_id_from_validated_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build with codex planner",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_contracts import write_json_file
            from scripts.harness_loop_orchestrator import _run_planner as run_planner

            def write_planner_output(**kwargs: object) -> dict[str, object]:
                write_json_file(
                    kwargs["output_json_path"],
                    {
                        "task_id": "codex-task-id",
                        "policy": "demand_development",
                        "task_kind": "registered_task",
                        "title": "Codex planner task",
                        "goal": "Build with codex planner",
                        "non_goals": [],
                        "allowed_paths": [],
                        "denylist_paths": [],
                        "verify_commands": [],
                        "evaluator_scenarios_path": "",
                        "stop_conditions": ["passed_waiting_human_merge"],
                        "next_planning_hint": "",
                        "skill_invocations": [],
                    },
                )
                return {"status": "pass", "run_id": "demo-run", "role": "planner", "attempt": 1}

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=write_planner_output):
                run_planner(repo_root, "demo-run", driver="codex-exec")

            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["task_id"], "codex-task-id")

    def test_codex_exec_planner_persists_attempt_before_missing_contract_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build with codex planner",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_planner as run_planner

            attempts: list[int] = []

            def do_not_write_planner_output(**kwargs: object) -> dict[str, object]:
                attempts.append(int(kwargs["attempt"]))
                return {
                    "status": "pass",
                    "run_id": "demo-run",
                    "role": "planner",
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=do_not_write_planner_output):
                with self.assertRaises(FileNotFoundError):
                    run_planner(repo_root, "demo-run", driver="codex-exec")

            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["attempts"]["planner"], 1)
            self.assertEqual(run["phase"], "planned")
            self.assertEqual(run["next_action"], "run_planner")

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=do_not_write_planner_output):
                with self.assertRaises(FileNotFoundError):
                    run_planner(repo_root, "demo-run", driver="codex-exec")

            self.assertEqual(attempts, [1, 2])

    def test_codex_exec_planner_failure_does_not_accept_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build with codex planner",
                run_id="demo-run",
                confirm=True,
            )
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "planner-output.json",
                {
                    "task_id": "stale-task-id",
                    "policy": "demand_development",
                    "task_kind": "registered_task",
                    "title": "Stale planner task",
                    "goal": "stale",
                    "non_goals": [],
                    "allowed_paths": [],
                    "denylist_paths": [],
                    "verify_commands": [],
                    "evaluator_scenarios_path": "",
                    "stop_conditions": ["passed_waiting_human_merge"],
                    "next_planning_hint": "",
                    "skill_invocations": [],
                },
            )
            from scripts.harness_loop_orchestrator import _run_planner as run_planner

            with patch(
                "scripts.harness_loop_orchestrator.run_codex_prompt",
                return_value={"status": "fail", "run_id": "demo-run", "role": "planner", "attempt": 1},
            ):
                with self.assertRaisesRegex(RuntimeError, "planner codex-exec attempt failed"):
                    run_planner(repo_root, "demo-run", driver="codex-exec")

            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["attempts"]["planner"], 1)
            self.assertEqual(run["phase"], "planned")
            self.assertEqual(run["next_action"], "run_planner")
            self.assertEqual(run["task_id"], "")

    def test_codex_exec_planner_pass_without_new_output_does_not_accept_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build with codex planner",
                run_id="demo-run",
                confirm=True,
            )
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "planner-output.json",
                {
                    "task_id": "stale-task-id",
                    "policy": "demand_development",
                    "task_kind": "registered_task",
                    "title": "Stale planner task",
                    "goal": "stale",
                    "non_goals": [],
                    "allowed_paths": [],
                    "denylist_paths": [],
                    "verify_commands": [],
                    "evaluator_scenarios_path": "",
                    "stop_conditions": ["passed_waiting_human_merge"],
                    "next_planning_hint": "",
                    "skill_invocations": [],
                },
            )
            from scripts.harness_loop_orchestrator import _run_planner as run_planner

            with patch(
                "scripts.harness_loop_orchestrator.run_codex_prompt",
                return_value={"status": "pass", "run_id": "demo-run", "role": "planner", "attempt": 1},
            ):
                with self.assertRaises(FileNotFoundError):
                    run_planner(repo_root, "demo-run", driver="codex-exec")

            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["attempts"]["planner"], 1)
            self.assertEqual(run["phase"], "planned")
            self.assertEqual(run["next_action"], "run_planner")
            self.assertEqual(run["task_id"], "")

    def test_run_generator_rejects_confirmed_preflight_before_planning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the generator demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_generator as run_generator

            with self.assertRaisesRegex(RuntimeError, "planned"):
                run_generator(repo_root, "demo-run", driver="fake")

    def test_fake_generator_writes_valid_generator_result_and_advances_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the generator demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_generator as run_generator, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            output_path = run_generator(repo_root, "demo-run", driver="fake")

            run_dir = run_dir_for(repo_root, "demo-run")
            self.assertEqual(output_path, run_dir / "generator-result.json")
            generator_result = read_json_file(output_path)
            validate_generator_result_payload(generator_result)
            self.assertEqual(generator_result["task_id"], "demo-run-task")
            self.assertEqual(generator_result["status"], "implemented")
            run = read_json_file(run_dir / "run.json")
            validate_run_payload(run)
            self.assertEqual(run["phase"], "evaluating")
            self.assertEqual(run["next_action"], "run_evaluator")
            self.assertEqual(run["attempts"]["generator"], 1)

    def test_run_generator_rejects_already_generated_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the generator demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_generator as run_generator, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")

            with self.assertRaisesRegex(RuntimeError, "evaluating"):
                run_generator(repo_root, "demo-run", driver="fake")

    def test_codex_exec_generator_persists_attempt_before_missing_contract_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the generator demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_generator as run_generator, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            attempts: list[int] = []

            def do_not_write_generator_result(**kwargs: object) -> dict[str, object]:
                attempts.append(int(kwargs["attempt"]))
                return {
                    "status": "pass",
                    "run_id": "demo-run",
                    "role": "generator",
                    "attempt": int(kwargs["attempt"]),
                }

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=do_not_write_generator_result):
                with self.assertRaises(FileNotFoundError):
                    run_generator(repo_root, "demo-run", driver="codex-exec")

            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["attempts"]["generator"], 1)
            self.assertEqual(run["phase"], "generating")
            self.assertEqual(run["next_action"], "run_generator")

            with patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=do_not_write_generator_result):
                with self.assertRaises(FileNotFoundError):
                    run_generator(repo_root, "demo-run", driver="codex-exec")

            self.assertEqual(attempts, [1, 2])

    def test_codex_exec_generator_failure_does_not_accept_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the generator demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_generator as run_generator, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "generator-result.json",
                {
                    "task_id": "demo-run-task",
                    "status": "implemented",
                    "changed_paths": [],
                    "commit": "",
                    "verify_commands": [],
                    "verify_results": [],
                    "artifacts": [],
                    "cleanup_required": False,
                    "notes": "stale result",
                    "skill_invocations": [],
                },
            )

            with patch(
                "scripts.harness_loop_orchestrator.run_codex_prompt",
                return_value={"status": "fail", "run_id": "demo-run", "role": "generator", "attempt": 1},
            ):
                with self.assertRaisesRegex(RuntimeError, "generator codex-exec attempt failed"):
                    run_generator(repo_root, "demo-run", driver="codex-exec")

            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["attempts"]["generator"], 1)
            self.assertEqual(run["phase"], "generating")
            self.assertEqual(run["next_action"], "run_generator")

    def test_codex_exec_generator_pass_without_new_output_does_not_accept_stale_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build the generator demo",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_generator as run_generator, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "generator-result.json",
                {
                    "task_id": "demo-run-task",
                    "status": "implemented",
                    "changed_paths": [],
                    "commit": "",
                    "verify_commands": [],
                    "verify_results": [],
                    "artifacts": [],
                    "cleanup_required": False,
                    "notes": "stale result",
                    "skill_invocations": [],
                },
            )

            with patch(
                "scripts.harness_loop_orchestrator.run_codex_prompt",
                return_value={"status": "pass", "run_id": "demo-run", "role": "generator", "attempt": 1},
            ):
                with self.assertRaises(FileNotFoundError):
                    run_generator(repo_root, "demo-run", driver="codex-exec")

            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["attempts"]["generator"], 1)
            self.assertEqual(run["phase"], "generating")
            self.assertEqual(run["next_action"], "run_generator")

    def test_internal_plan_and_generate_primitives_accept_fake_driver(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through CLI",
                run_id="demo-run",
                confirm=True,
            )

            harness_loop_orchestrator._run_planner(
                repo_root, "demo-run", driver="fake"
            )
            harness_loop_orchestrator._run_generator(
                repo_root, "demo-run", driver="fake"
            )

            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            self.assertEqual(run["phase"], "evaluating")
            self.assertEqual(run["next_action"], "run_evaluator")

    def test_fake_evaluator_writes_result_and_waits_for_human_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through evaluator",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_evaluator as run_evaluator, _run_generator as run_generator, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            write_fake_evaluator_scenario(repo_root, "demo-run-task")

            output_path = run_evaluator(repo_root, "demo-run", driver="fake", max_attempts=2)

            run_dir = run_dir_for(repo_root, "demo-run")
            self.assertEqual(output_path, run_dir / "evaluator-result.json")
            evaluator_result = read_json_file(output_path)
            validate_evaluator_result_payload(evaluator_result)
            self.assertEqual(evaluator_result["status"], "pass")
            self.assertEqual(evaluator_result["task_id"], "demo-run-task")
            self.assertEqual(evaluator_result["driver"], "fake")
            self.assertEqual(evaluator_result["returncode"], 0)
            run = read_json_file(run_dir / "run.json")
            validate_run_payload(run)
            self.assertEqual(run["phase"], "passed_waiting_human_merge")
            self.assertEqual(run["last_result"], "pass")
            self.assertEqual(run["next_action"], "await_human_merge_confirmation")
            self.assertNotIn("_post_hygiene_phase", run)
            self.assertEqual(run["attempts"]["evaluator"], 1)

    def test_run_evaluator_runs_scenario_commands_from_task_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Run scenario command",
                run_id="demo-run",
                task_id="contract-task",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_evaluator as run_evaluator, _run_generator as run_generator, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            write_fake_evaluator_scenario(repo_root, "contract-task")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "task-contract.json",
                {
                    "task_id": "contract-task",
                    "title": "Contract task",
                    "description": "Temporary contract task.",
                    "verify_commands": [],
                    "scenario_commands": ["python3 -c \"print('scenario artifact')\""],
                    "artifact_paths": [],
                    "required_services": [],
                    "evaluator_driver": "harness_auto_gate",
                    "eval_policy": {"task_level_required": True},
                    "allowed_scope": "local_repo_and_harness",
                    "must_simulate": True,
                    "user_scenarios": [
                        {
                            "scenario_id": "CONTRACT-01",
                            "user_goal": "Run command.",
                            "prerequisites": [],
                            "steps": ["Run command."],
                            "expected_outcomes": ["Artifact exists."],
                            "failure_signals": ["Artifact missing."],
                        }
                    ],
                },
            )

            output_path = run_evaluator(repo_root, "demo-run", driver="fake", max_attempts=2)

            evaluator_result = read_json_file(output_path)
            self.assertEqual(evaluator_result["status"], "pass")
            manifest_path = Path(evaluator_result["scenario_command_results_path"])
            self.assertEqual(manifest_path, run_dir / "scenario-command-results.json")
            manifest = read_json_file(manifest_path)
            self.assertEqual(manifest["status"], "pass")
            stdout_path = Path(manifest["results"][0]["stdout_path"])
            self.assertIn("scenario artifact", stdout_path.read_text(encoding="utf-8"))

    def test_run_evaluator_uses_task_contract_as_only_scenario_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Run contract-only scenario",
                run_id="demo-run",
                task_id="contract-only-task",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_evaluator as run_evaluator, _run_generator as run_generator, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "task-contract.json",
                {
                    "task_id": "contract-only-task",
                    "title": "Contract-only task",
                    "description": "Temporary contract task with no registered scenario file.",
                    "verify_commands": [],
                    "scenario_commands": ["python3 -c \"print('contract only')\""],
                    "artifact_paths": [],
                    "required_services": [],
                    "evaluator_driver": "harness_auto_gate",
                    "eval_policy": {"task_level_required": True},
                    "allowed_scope": "local_repo_and_harness",
                    "must_simulate": True,
                    "user_scenarios": [
                        {
                            "scenario_id": "CONTRACT-ONLY-01",
                            "user_goal": "Use task contract scenarios.",
                            "prerequisites": [],
                            "steps": ["Run command."],
                            "expected_outcomes": ["Contract scenario passes."],
                            "failure_signals": ["Evaluator ignores task contract."],
                        }
                    ],
                },
            )

            output_path = run_evaluator(repo_root, "demo-run", driver="fake", max_attempts=2)

            evaluator_result = read_json_file(output_path)
            self.assertEqual(evaluator_result["status"], "pass")
            task_root = repo_root / ".codex" / "evaluations" / "tasks" / "contract-only-task"
            input_payload = read_json_file(task_root / "fake-attempt-2" / "input.json")
            self.assertEqual(input_payload["scenario_source"], str(run_dir / "task-contract.json"))
            self.assertEqual(input_payload["user_scenarios"][0]["scenario_id"], "CONTRACT-ONLY-01")

    def test_run_evaluator_fails_when_task_contract_scenario_command_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Run failing scenario command",
                run_id="demo-run",
                task_id="contract-task",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_evaluator as run_evaluator, _run_generator as run_generator, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            write_fake_evaluator_scenario(repo_root, "contract-task")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "task-contract.json",
                {
                    "task_id": "contract-task",
                    "title": "Contract task",
                    "description": "Temporary contract task.",
                    "verify_commands": [],
                    "scenario_commands": ["python3 -c \"raise SystemExit(7)\""],
                    "artifact_paths": [],
                    "required_services": [],
                    "evaluator_driver": "harness_auto_gate",
                    "eval_policy": {"task_level_required": True},
                    "allowed_scope": "local_repo_and_harness",
                    "must_simulate": True,
                    "user_scenarios": [
                        {
                            "scenario_id": "CONTRACT-01",
                            "user_goal": "Run command.",
                            "prerequisites": [],
                            "steps": ["Run command."],
                            "expected_outcomes": ["Artifact exists."],
                            "failure_signals": ["Artifact missing."],
                        }
                    ],
                },
            )

            output_path = run_evaluator(repo_root, "demo-run", driver="fake", max_attempts=2)

            evaluator_result = read_json_file(output_path)
            validate_evaluator_result_payload(evaluator_result)
            self.assertEqual(evaluator_result["status"], "fail")
            self.assertNotEqual(evaluator_result["returncode"], 0)
            manifest_path = Path(evaluator_result["scenario_command_results_path"])
            self.assertEqual(manifest_path, run_dir / "scenario-command-results.json")
            manifest = read_json_file(manifest_path)
            self.assertEqual(manifest["status"], "fail")
            self.assertEqual(manifest["results"][0]["status"], "fail")
            self.assertEqual(manifest["results"][0]["exit_code"], 7)
            run = read_json_file(run_dir / "run.json")
            validate_run_payload(run)
            self.assertEqual(run["phase"], "artifact_hygiene")
            self.assertEqual(run["last_result"], "fail")
            self.assertEqual(run["next_action"], "run_artifact_hygiene")

    def test_codex_exec_evaluator_passes_task_contract_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Run codex evaluator with task contract",
                run_id="demo-run",
                task_id="contract-task",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_evaluator as run_evaluator, _run_generator as run_generator, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "task-contract.json",
                {
                    "task_id": "contract-task",
                    "title": "Contract task",
                    "description": "Temporary contract task.",
                    "verify_commands": [],
                    "scenario_commands": [],
                    "artifact_paths": [],
                    "required_services": [],
                    "evaluator_driver": "harness_auto_gate",
                    "eval_policy": {"task_level_required": True},
                    "allowed_scope": "local_repo_and_harness",
                    "must_simulate": True,
                    "user_scenarios": [
                        {
                            "scenario_id": "CONTRACT-01",
                            "user_goal": "Use task contract scenarios.",
                            "prerequisites": [],
                            "steps": ["Run command."],
                            "expected_outcomes": ["Contract scenario passes."],
                            "failure_signals": ["Evaluator ignores task contract."],
                        }
                    ],
                },
            )
            template_root = repo_root / ".codex" / "evaluations" / "templates"
            template_root.mkdir(parents=True)
            (template_root / "artifacts.template.json").write_text("{}\n", encoding="utf-8")
            (template_root / "summary.template.md").write_text("# Summary\n", encoding="utf-8")

            def completed_evaluation(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess:
                if command[0] == "git":
                    raise subprocess.CalledProcessError(128, command)
                from scripts.harness_evaluator_cli import create_task_bundle

                bundle = create_task_bundle(
                    repo_root,
                    "contract-task",
                    1,
                    bundle_name="20260716T000000Z-attempt-1",
                    task_contract_path=run_dir / "task-contract.json",
                )
                input_path = bundle / "input.json"
                input_payload = read_json_file(input_path)
                input_payload["loop_run_id"] = command[command.index("--loop-run-id") + 1]
                input_payload["loop_generator_attempt"] = int(
                    command[command.index("--generator-attempt") + 1]
                )
                write_json_file(input_path, input_payload)
                write_json_file(
                    bundle / "result.json",
                    {
                        "status": "pass",
                        "gate": "task",
                        "task_id": "contract-task",
                        "final_bundle_id": "",
                        "attempt": 1,
                        "summary": "pass",
                        "findings": [],
                        "scenario_results": [
                            {
                                "scenario_id": "CONTRACT-01",
                                "status": "pass",
                                "evidence": ["scenario-command-results.json"],
                                "notes": "pass",
                            }
                        ],
                        "rerun_commands": [],
                        "environment_checks": [],
                        "verdict_reason": "pass",
                        "next_action": "proceed_to_user_acceptance",
                    },
                )
                return subprocess.CompletedProcess(
                    args=command,
                    returncode=0,
                    stdout="codex evaluator stdout",
                    stderr="",
                )

            with patch(
                "scripts.harness_loop_orchestrator.subprocess.run",
                side_effect=completed_evaluation,
            ) as run_mock:
                run_evaluator(repo_root, "demo-run", driver="codex-exec", max_attempts=2)

            command = run_mock.call_args.args[0]
            self.assertIn("--task-contract", command)
            self.assertIn(str(run_dir / "task-contract.json"), command)

    def test_fake_evaluator_preserves_blocked_result_when_scenarios_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through evaluator",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_evaluator as run_evaluator, _run_generator as run_generator, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")

            output_path = run_evaluator(repo_root, "demo-run", driver="fake", max_attempts=2)

            evaluator_result = read_json_file(output_path)
            validate_evaluator_result_payload(evaluator_result)
            self.assertEqual(evaluator_result["status"], "blocked")
            self.assertEqual(evaluator_result["driver"], "fake")
            self.assertEqual(evaluator_result["returncode"], 1)
            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            validate_run_payload(run)
            self.assertEqual(run["phase"], "repair_needed")
            self.assertEqual(run["last_result"], "blocked")
            self.assertEqual(run["next_action"], "repair_from_evaluator_findings")

    def test_fake_evaluator_writes_synthetic_result_when_no_result_file_exists(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through evaluator",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_orchestrator import _run_evaluator as run_evaluator, _run_generator as run_generator, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            completed = subprocess.CompletedProcess(
                args=["fake-evaluator"],
                returncode=1,
                stdout="fake stdout",
                stderr="fake stderr",
            )

            with patch("scripts.harness_loop_orchestrator.subprocess.run", return_value=completed):
                output_path = run_evaluator(repo_root, "demo-run", driver="fake", max_attempts=2)

            evaluator_result = read_json_file(output_path)
            self.assertEqual(evaluator_result["status"], "fail")
            self.assertEqual(evaluator_result["driver"], "fake")
            self.assertEqual(evaluator_result["returncode"], 1)
            self.assertEqual(evaluator_result["stdout"], "fake stdout")
            self.assertEqual(evaluator_result["stderr"], "fake stderr")
            self.assertEqual(evaluator_result["task_id"], "demo-run-task")
            run = read_json_file(run_dir_for(repo_root, "demo-run") / "run.json")
            validate_run_payload(run)
            self.assertEqual(run["phase"], "repair_needed")
            self.assertEqual(run["last_result"], "fail")

    @unittest.skip("legacy multi-round runtime removed")
    def test_run_loop_rejects_unconfirmed_preflight(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through loop",
                run_id="demo-run",
                confirm=False,
            )
            from scripts.harness_loop_orchestrator import _run_loop as run_loop

            with self.assertRaisesRegex(RuntimeError, "preflight"):
                run_loop(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                )

    @unittest.skip("legacy multi-round runtime removed")
    def test_run_loop_plans_generates_and_evaluates_from_planned(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through loop",
                run_id="demo-run",
                confirm=True,
            )
            write_fake_evaluator_scenario(repo_root, "demo-run-task")
            from scripts.harness_loop_orchestrator import _run_loop as run_loop

            status = run_loop(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
            )

            self.assertEqual(status["phase"], "passed_waiting_human_merge")
            self.assertEqual(status["next_action"], "await_human_merge_confirmation")
            self.assertEqual(status["task_id"], "demo-run-task")

    def test_internal_artifact_hygiene_and_cleanup_primitives(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(repo_root, "demand-development", "CLI hygiene", "demo-run", confirm=True)
            artifact_path = repo_root / "artifact.txt"
            artifact_path.write_text("public artifact\n", encoding="utf-8")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "generator-result.json",
                {
                    "task_id": "demo-run-task",
                    "status": "implemented",
                    "changed_paths": [],
                    "commit": "",
                    "verify_commands": [],
                    "verify_results": [],
                    "artifacts": ["artifact.txt"],
                    "cleanup_required": False,
                    "notes": "needs hygiene",
                    "skill_invocations": [],
                },
            )
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "artifact_hygiene"
            run["task_id"] = "demo-run-task"
            run["next_action"] = "run_artifact_hygiene"
            write_json_file(run_dir / "run.json", run)

            harness_loop_orchestrator._run_artifact_hygiene_step(
                repo_root, "demo-run"
            )
            harness_loop_orchestrator._run_cleanup(repo_root, "demo-run")

            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["phase"], "passed_waiting_human_merge")
            self.assertEqual(run["next_action"], "await_human_merge_confirmation")

    @unittest.skip("legacy multi-round runtime removed")
    def test_run_loop_runs_hygiene_and_cleanup_after_evaluator_when_generator_has_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through hygiene loop",
                run_id="demo-run",
                confirm=True,
            )
            write_fake_evaluator_scenario(repo_root, "demo-run-task")
            from scripts.harness_loop_orchestrator import _run_generator as run_generator, _run_loop as run_loop, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            generator_path = run_generator(repo_root, "demo-run", driver="fake")
            generator_result = read_json_file(generator_path)
            generator_result["artifacts"] = ["artifact.txt"]
            write_json_file(generator_path, generator_result)
            (repo_root / "artifact.txt").write_text("public artifact\n", encoding="utf-8")

            status = run_loop(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
            )

            run_dir = run_dir_for(repo_root, "demo-run")
            self.assertEqual(status["phase"], "passed_waiting_human_merge")
            self.assertEqual(status["next_action"], "await_human_merge_confirmation")
            self.assertTrue((run_dir / "artifact-manifest.json").exists())
            self.assertTrue((run_dir / "cleanup-result.json").exists())

    def test_artifact_hygiene_ignores_embedded_artifact_references(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_dir = repo_root / ".codex" / "loop-runs" / "demo-run"
            run_dir.mkdir(parents=True)
            (repo_root / "artifact.txt").write_text("public artifact\n", encoding="utf-8")

            from scripts.harness_loop_artifacts import run_artifact_hygiene

            result_path = run_artifact_hygiene(
                repo_root=repo_root,
                run_dir=run_dir,
                artifact_paths=["artifact.txt", "embedded:required_evidence_manifest"],
            )

            artifact_manifest = read_json_file(result_path)
            self.assertEqual(artifact_manifest["status"], "pass")
            self.assertEqual(artifact_manifest["scanned_paths"], ["artifact.txt"])
            self.assertEqual(artifact_manifest["omitted_paths"], [])
            self.assertFalse(
                [
                    finding
                    for finding in artifact_manifest["findings"]
                    if finding.get("path") == "embedded:required_evidence_manifest"
                ]
            )

    @unittest.skip("legacy multi-round runtime removed")
    def test_run_loop_hygiene_redacts_scenario_command_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through hygiene loop",
                run_id="demo-run",
                task_id="contract-task",
                confirm=True,
            )
            write_fake_evaluator_scenario(repo_root, "contract-task")
            from scripts.harness_loop_orchestrator import _run_generator as run_generator, _run_loop as run_loop, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            generator_path = run_generator(repo_root, "demo-run", driver="fake")
            generator_result = read_json_file(generator_path)
            generator_result["artifacts"] = ["artifact.txt"]
            write_json_file(generator_path, generator_result)
            (repo_root / "artifact.txt").write_text("public artifact\n", encoding="utf-8")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "task-contract.json",
                {
                    "task_id": "contract-task",
                    "title": "Contract task",
                    "description": "Temporary contract task.",
                    "verify_commands": [],
                    "scenario_commands": ["python3 -c \"print('Authorization: Bearer secret-token')\""],
                    "artifact_paths": [],
                    "required_services": [],
                    "evaluator_driver": "harness_auto_gate",
                    "eval_policy": {"task_level_required": True},
                    "allowed_scope": "local_repo_and_harness",
                    "must_simulate": True,
                    "user_scenarios": [
                        {
                            "scenario_id": "CONTRACT-01",
                            "user_goal": "Run command.",
                            "prerequisites": [],
                            "steps": ["Run command."],
                            "expected_outcomes": ["Scenario command output is redacted."],
                            "failure_signals": ["Scenario command logs leak secrets."],
                        }
                    ],
                },
            )

            status = run_loop(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
            )

            self.assertEqual(status["phase"], "passed_waiting_human_merge")
            artifact_manifest = read_json_file(run_dir / "artifact-manifest.json")
            self.assertIn(
                ".codex/loop-runs/demo-run/scenario-commands/command-1.stdout.log",
                artifact_manifest["scanned_paths"],
            )
            self.assertIn(
                ".codex/loop-runs/demo-run/scenario-commands/command-1.stdout.log.redacted",
                artifact_manifest["redacted_paths"],
            )

    @unittest.skip("legacy multi-round runtime removed")
    def test_run_loop_hygiene_runs_for_scenario_command_logs_without_generator_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through scenario-only hygiene loop",
                run_id="demo-run",
                task_id="contract-task",
                confirm=True,
            )
            write_fake_evaluator_scenario(repo_root, "contract-task")
            from scripts.harness_loop_orchestrator import _run_generator as run_generator, _run_loop as run_loop, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "task-contract.json",
                {
                    "task_id": "contract-task",
                    "title": "Contract task",
                    "description": "Temporary contract task.",
                    "verify_commands": [],
                    "scenario_commands": ["python3 -c \"print('Authorization: Bearer secret-token')\""],
                    "artifact_paths": [],
                    "required_services": [],
                    "evaluator_driver": "harness_auto_gate",
                    "eval_policy": {"task_level_required": True},
                    "allowed_scope": "local_repo_and_harness",
                    "must_simulate": True,
                    "user_scenarios": [
                        {
                            "scenario_id": "CONTRACT-01",
                            "user_goal": "Run command.",
                            "prerequisites": [],
                            "steps": ["Run command."],
                            "expected_outcomes": ["Scenario command output is redacted."],
                            "failure_signals": ["Scenario command logs leak secrets."],
                        }
                    ],
                },
            )

            status = run_loop(
                repo_root,
                "demo-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
            )

            self.assertEqual(status["phase"], "passed_waiting_human_merge")
            artifact_manifest = read_json_file(run_dir / "artifact-manifest.json")
            self.assertIn(
                ".codex/loop-runs/demo-run/scenario-commands/command-1.stdout.log",
                artifact_manifest["scanned_paths"],
            )
            self.assertIn(
                ".codex/loop-runs/demo-run/scenario-commands/command-1.stdout.log.redacted",
                artifact_manifest["redacted_paths"],
            )
            redacted_log = repo_root / ".codex/loop-runs/demo-run/scenario-commands/command-1.stdout.log.redacted"
            self.assertNotIn("Authorization: Bearer secret-token", redacted_log.read_text(encoding="utf-8"))

    def test_run_evaluator_failing_scenario_commands_enter_artifact_hygiene(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Fail through scenario-only hygiene loop",
                run_id="demo-run",
                task_id="contract-task",
                confirm=True,
            )
            write_fake_evaluator_scenario(repo_root, "contract-task")
            from scripts.harness_loop_orchestrator import _run_evaluator as run_evaluator, _run_generator as run_generator, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "task-contract.json",
                {
                    "task_id": "contract-task",
                    "title": "Contract task",
                    "description": "Temporary contract task.",
                    "verify_commands": [],
                    "scenario_commands": ["python3 -c \"print('Authorization: Bearer secret-token'); raise SystemExit(7)\""],
                    "artifact_paths": [],
                    "required_services": [],
                    "evaluator_driver": "harness_auto_gate",
                    "eval_policy": {"task_level_required": True},
                    "allowed_scope": "local_repo_and_harness",
                    "must_simulate": True,
                    "user_scenarios": [
                        {
                            "scenario_id": "CONTRACT-01",
                            "user_goal": "Run command.",
                            "prerequisites": [],
                            "steps": ["Run command."],
                            "expected_outcomes": ["Scenario command output is redacted before repair."],
                            "failure_signals": ["Scenario command logs leak secrets."],
                        }
                    ],
                },
            )

            output_path = run_evaluator(repo_root, "demo-run", driver="fake", max_attempts=2)

            evaluator_result = read_json_file(output_path)
            self.assertEqual(evaluator_result["status"], "fail")
            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["phase"], "artifact_hygiene")
            self.assertEqual(run["last_result"], "fail")
            self.assertEqual(run["next_action"], "run_artifact_hygiene")

    @unittest.skip("legacy multi-round runtime removed")
    def test_run_loop_rejects_unsupported_active_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Build through loop",
                run_id="demo-run",
                confirm=True,
            )
            from scripts.harness_loop_contracts import write_json_file
            from scripts.harness_loop_orchestrator import _run_loop as run_loop

            run_path = run_dir_for(repo_root, "demo-run") / "run.json"
            run = read_json_file(run_path)
            run["phase"] = "verifying"
            write_json_file(run_path, run)

            with self.assertRaisesRegex(RuntimeError, "unsupported.*verifying"):
                run_loop(
                    repo_root,
                    "demo-run",
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                )

    def test_run_artifact_hygiene_blocks_large_artifacts_and_records_phase(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(repo_root, "demand-development", "Hygiene", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            large_path = repo_root / "large.bin"
            large_path.write_bytes(b"x" * 20)
            generator_result = {
                "task_id": "demo-run-task",
                "status": "implemented",
                "changed_paths": [],
                "commit": "",
                "verify_commands": [],
                "verify_results": [],
                "artifacts": ["large.bin"],
                "cleanup_required": False,
                "notes": "needs hygiene",
                "skill_invocations": [],
            }
            write_json_file(run_dir / "generator-result.json", generator_result)
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "artifact_hygiene"
            run["task_id"] = "demo-run-task"
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import _run_artifact_hygiene_step as run_artifact_hygiene_step

            result_path = run_artifact_hygiene_step(repo_root, "demo-run", max_file_bytes=10)

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "blocked")
            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["phase"], "stopped_blocked")
            self.assertEqual(run["last_result"], "blocked")
            self.assertEqual(run["next_action"], "inspect_artifact_hygiene")

    def test_autonomous_artifact_hygiene_ignores_unchanged_evidence_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Expand wiki",
                run_id="demo-run",
                domain="ai_infra",
                confirm=True,
            )
            run_dir = run_dir_for(repo_root, "demo-run")
            changed_path = repo_root / "personal-wiki" / "domains" / "ai_infra" / "wiki" / "references" / "changed.md"
            changed_path.parent.mkdir(parents=True)
            changed_path.write_text("ok\n", encoding="utf-8")
            old_evidence_path = repo_root / "personal-wiki" / "domains" / "ai_infra" / "raw" / "github" / "issues.json.gz"
            old_evidence_path.parent.mkdir(parents=True)
            old_evidence_path.write_bytes(b"\x1f\x8b" + (b"x" * 32))
            generator_result = {
                "task_id": "demo-run-task",
                "status": "implemented",
                "changed_paths": [
                    "personal-wiki/domains/ai_infra/wiki/references/changed.md",
                ],
                "commit": "",
                "verify_commands": [],
                "verify_results": [],
                "artifacts": [
                    "personal-wiki/domains/ai_infra/wiki/references/changed.md",
                    "personal-wiki/domains/ai_infra/raw/github/issues.json.gz",
                ],
                "cleanup_required": False,
                "notes": "Existing raw issue corpus is cited as evidence, not emitted as a new artifact.",
                "skill_invocations": [],
            }
            write_json_file(run_dir / "generator-result.json", generator_result)
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "artifact_hygiene"
            run["task_id"] = "demo-run-task"
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import _run_artifact_hygiene_step as run_artifact_hygiene_step

            result_path = run_artifact_hygiene_step(repo_root, "demo-run", max_file_bytes=10)

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "pass")
            self.assertEqual(
                result["scanned_paths"],
                ["personal-wiki/domains/ai_infra/wiki/references/changed.md"],
            )
            self.assertEqual(result["omitted_paths"], [])
            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["phase"], "cleanup")

    def test_run_cleanup_records_removed_worktree_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(repo_root, "demand-development", "Cleanup", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            temp_worktree = repo_root / ".worktrees" / "demo-run-attempt-1"
            temp_worktree.mkdir(parents=True)
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "cleanup"
            run["cleanup"]["retained_artifacts"] = [str(temp_worktree)]
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import _run_cleanup as run_cleanup

            result_path = run_cleanup(repo_root, "demo-run")

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "pass")
            self.assertFalse(temp_worktree.exists())
            run = read_json_file(run_dir / "run.json")
            self.assertIn(str(temp_worktree), run["cleanup"]["worktrees_removed"])
            self.assertEqual(run["phase"], "passed_waiting_human_merge")

    def test_run_cleanup_records_removed_relative_worktree_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(repo_root, "demand-development", "Cleanup", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            temp_worktree = repo_root / ".worktrees" / "demo-run-attempt-1"
            temp_worktree.mkdir(parents=True)
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "cleanup"
            run["cleanup"]["retained_artifacts"] = [".worktrees/demo-run-attempt-1"]
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import _run_cleanup as run_cleanup

            result_path = run_cleanup(repo_root, "demo-run")

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "pass")
            self.assertFalse(temp_worktree.exists())
            self.assertIn(".worktrees/demo-run-attempt-1", result["worktrees_removed"])

    def test_run_cleanup_accepts_absolute_retained_path_with_relative_repo_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(repo_root, "demand-development", "Cleanup", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            temp_worktree = repo_root / ".worktrees" / "demo-run-attempt-1"
            temp_worktree.mkdir(parents=True)
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "cleanup"
            run["cleanup"]["retained_artifacts"] = [str(temp_worktree)]
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import _run_cleanup as run_cleanup

            current_dir = Path.cwd()
            os.chdir(repo_root)
            try:
                result_path = run_cleanup(Path("."), "demo-run").resolve()
            finally:
                os.chdir(current_dir)

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "pass")
            self.assertFalse(temp_worktree.exists())
            run = read_json_file(run_dir / "run.json")
            self.assertIn(str(temp_worktree), run["cleanup"]["worktrees_removed"])

    def test_run_cleanup_refuses_outside_worktrees_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            repo_root = parent / "repo"
            repo_root.mkdir()
            create_preflight_run(repo_root, "demand-development", "Cleanup", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            victim = parent / "outside" / ".worktrees" / "victim"
            victim.mkdir(parents=True)
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "cleanup"
            run["cleanup"]["retained_artifacts"] = [str(victim)]
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import _run_cleanup as run_cleanup

            result_path = run_cleanup(repo_root, "demo-run")

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "pass")
            self.assertTrue(victim.exists())
            self.assertNotIn(str(victim), result["worktrees_removed"])
            run = read_json_file(run_dir / "run.json")
            self.assertNotIn(str(victim), run["cleanup"]["worktrees_removed"])

    def test_run_cleanup_skips_absolute_symlink_retained_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(repo_root, "demand-development", "Cleanup", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            real_worktree = repo_root / ".worktrees" / "real"
            real_worktree.mkdir(parents=True)
            symlink_path = repo_root / ".worktrees" / "link"
            symlink_path.symlink_to(real_worktree, target_is_directory=True)
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "cleanup"
            run["cleanup"]["retained_artifacts"] = [str(symlink_path)]
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import _run_cleanup as run_cleanup

            result_path = run_cleanup(repo_root, "demo-run")

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "pass")
            self.assertTrue(symlink_path.is_symlink())
            self.assertTrue(real_worktree.exists())
            self.assertNotIn(str(symlink_path), result["worktrees_removed"])

    def test_run_cleanup_skips_relative_symlink_retained_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(repo_root, "demand-development", "Cleanup", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            real_worktree = repo_root / ".worktrees" / "real"
            real_worktree.mkdir(parents=True)
            symlink_path = repo_root / ".worktrees" / "link"
            symlink_path.symlink_to(real_worktree, target_is_directory=True)
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "cleanup"
            run["cleanup"]["retained_artifacts"] = [".worktrees/link"]
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import _run_cleanup as run_cleanup

            result_path = run_cleanup(repo_root, "demo-run")

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "pass")
            self.assertTrue(symlink_path.is_symlink())
            self.assertTrue(real_worktree.exists())
            self.assertNotIn(".worktrees/link", result["worktrees_removed"])

    def test_run_cleanup_skips_when_worktrees_root_is_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            parent = Path(tmp)
            repo_root = parent / "repo"
            outside_worktrees = parent / "outside-worktrees"
            repo_root.mkdir()
            outside_worktrees.mkdir()
            (repo_root / ".worktrees").symlink_to(outside_worktrees)
            create_preflight_run(repo_root, "demand-development", "Cleanup", "demo-run", confirm=True)
            run_dir = run_dir_for(repo_root, "demo-run")
            victim = repo_root / ".worktrees" / "victim"
            victim.mkdir()
            run = read_json_file(run_dir / "run.json")
            run["phase"] = "cleanup"
            run["cleanup"]["retained_artifacts"] = [str(victim)]
            write_json_file(run_dir / "run.json", run)

            from scripts.harness_loop_orchestrator import _run_cleanup as run_cleanup

            result_path = run_cleanup(repo_root, "demo-run")

            result = read_json_file(result_path)
            self.assertEqual(result["status"], "pass")
            self.assertTrue((outside_worktrees / "victim").exists())
            self.assertNotIn(str(victim), result["worktrees_removed"])
            run = read_json_file(run_dir / "run.json")
            self.assertNotIn(str(victim), run["cleanup"]["worktrees_removed"])

    def test_phase_1_scenario_entrypoint_uses_bounded_worker_regression(self) -> None:
        scenario_path = (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "harness"
            / "evaluator-scenarios"
            / "planner-generator-evaluator-loop-phase-1-01.json"
        )

        scenario = read_json_file(scenario_path)
        entrypoint = scenario["user_scenarios"][0]["entrypoint"]
        self.assertIn("test_harness_loop_supervisor_worker.py", entrypoint)
        self.assertIn(
            "test_phase1_demand_flow_reaches_human_merge_via_bounded_workers",
            entrypoint,
        )
        self.assertNotIn("harness_loop_orchestrator.py run", entrypoint)

    @unittest.skip("legacy smoke runtime removed")
    def test_phase_2_smoke_helper_exercises_contract_hygiene_cleanup(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]
        run_id = "evaluator-scenario-phase-2-test"
        task_id = "planner-generator-evaluator-loop-phase-2-01"
        run_dir = run_dir_for(repo_root, run_id)
        smoke_artifact = repo_root / ".codex" / "tmp" / "phase-2-smoke-artifact.txt"
        eval_dir = repo_root / ".codex" / "evaluations" / "tasks" / task_id
        shutil.rmtree(run_dir, ignore_errors=True)
        remove_fake_evaluator_attempts(eval_dir)
        smoke_artifact.unlink(missing_ok=True)
        try:
            result = subprocess.run(
                [
                    "python3",
                    "scripts/harness_loop_phase2_smoke.py",
                    "--repo-root",
                    str(repo_root),
                    "--run-id",
                    run_id,
                    "--task-id",
                    task_id,
                ],
                cwd=repo_root,
                check=False,
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}",
            )
            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["phase"], "passed_waiting_human_merge")
            self.assertEqual(run["next_action"], "await_human_merge_confirmation")
            self.assertTrue((run_dir / "scenario-command-results.json").exists())
            self.assertTrue((run_dir / "artifact-manifest.json").exists())
            self.assertTrue((run_dir / "cleanup-result.json").exists())
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)
            remove_fake_evaluator_attempts(eval_dir)
            smoke_artifact.unlink(missing_ok=True)
            remove_empty_directory(repo_root / ".codex" / "loop-runs")
            remove_empty_directory(repo_root / ".codex" / "tmp")

    @unittest.skip("legacy smoke runtime removed")
    def test_phase_2_scenario_entrypoint_uses_smoke_helper(self) -> None:
        scenario_path = (
            Path(__file__).resolve().parents[2]
            / "docs"
            / "harness"
            / "evaluator-scenarios"
            / "planner-generator-evaluator-loop-phase-2-01.json"
        )

        scenario = read_json_file(scenario_path)
        entrypoint = scenario["user_scenarios"][0]["entrypoint"]
        self.assertIn("scripts/harness_loop_phase2_smoke.py", entrypoint)
        self.assertIn("--run-id evaluator-scenario-phase-2", entrypoint)
        self.assertIn("--task-id planner-generator-evaluator-loop-phase-2-01", entrypoint)

    @unittest.skip("legacy smoke runtime removed")
    def test_phase_2_smoke_helper_rejects_path_traversal_ids_before_cleanup(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]

        from scripts.harness_loop_phase2_smoke import run_phase2_smoke

        with self.assertRaisesRegex(ValueError, "run_id"):
            run_phase2_smoke(repo_root, "../../docs", "planner-generator-evaluator-loop-phase-2-01")

        with self.assertRaisesRegex(ValueError, "task_id"):
            run_phase2_smoke(repo_root, "safe-run-id", "../planner-generator-evaluator-loop-phase-2-01")

    @unittest.skip("legacy smoke runtime removed")
    def test_ai_infra_meta_loop_smoke_helper_exercises_expanded_runtime(self) -> None:
        repo_root = Path(__file__).resolve().parents[2]

        from scripts.harness_ai_infra_meta_loop_smoke import run_ai_infra_meta_loop_smoke

        with patch(
            "scripts.harness_ai_infra_meta_loop_smoke.check_service_availability",
            return_value={
                "overall_status": "pass",
                "services": [
                    {"service": "crawler-backend", "url": "http://127.0.0.1:8765/api/health", "status": "pass", "http_status": 200, "error": ""},
                    {"service": "crawler-frontend", "url": "http://127.0.0.1:5173/", "status": "pass", "http_status": 200, "error": ""},
                    {"service": "loop-dashboard", "url": "http://127.0.0.1:8766/api/health", "status": "pass", "http_status": 200, "error": ""},
                ],
            },
        ):
            payload = run_ai_infra_meta_loop_smoke(
                repo_root,
                "evaluator-scenario-ai-infra-meta-loop-runtime-test",
                isolate_clone=True,
            )

        self.assertEqual(payload["expanded_policy_preflight"]["status"], "pass")
        self.assertEqual(payload["expanded_code_scope"]["status"], "blocked")
        self.assertEqual(payload["missing_evidence_gate"]["status"], "pass")
        self.assertEqual(payload["service_availability_evidence"]["status"], "pass")
        self.assertEqual(payload["crawler_freshness_evidence"]["status"], "blocked")
        self.assertEqual(payload["loop_dashboard_freshness_evidence"]["status"], "blocked")
        self.assertTrue(payload["expanded_code_scope"]["synthetic_placeholder_block"])
        self.assertEqual(payload["expanded_code_scope"]["run_status"]["phase"], "stopped_blocked")
        self.assertEqual(payload["expanded_code_scope"]["run_status"]["next_action"], "inspect_required_evidence")
        self.assertEqual(payload["expanded_code_scope"]["commit_result_path"], "")
        self.assertIn("synthetic", payload["crawler_freshness_evidence"]["summary"].lower())
        self.assertIn("synthetic", payload["loop_dashboard_freshness_evidence"]["summary"].lower())
        self.assertTrue(payload["isolated_clone"])
        self.assertEqual(payload["overall_status"], "blocked")

    @unittest.skip("legacy smoke runtime removed")
    def test_ai_infra_meta_loop_smoke_helper_keeps_git_identity_changes_inside_isolated_clone(self) -> None:
        from scripts import harness_ai_infra_meta_loop_smoke as smoke

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)

            with patch.object(smoke, "_run_smoke_in_repo", return_value={"overall_status": "pass"}) as run_smoke_in_repo:
                payload = smoke.run_ai_infra_meta_loop_smoke(
                    repo_root,
                    "evaluator-scenario-ai-infra-meta-loop-runtime-test",
                    isolate_clone=True,
                )

            self.assertTrue(payload["isolated_clone"])
            self.assertEqual(payload["source_repo_root"], str(repo_root.resolve()))
            clone_root, clone_run_id = run_smoke_in_repo.call_args.args
            self.assertNotEqual(clone_root, repo_root.resolve())
            self.assertEqual(clone_run_id, "evaluator-scenario-ai-infra-meta-loop-runtime-test")
            self.assertTrue(run_smoke_in_repo.call_args.kwargs["configure_git_identity"])

    @unittest.skip("legacy smoke runtime removed")
    def test_ai_infra_meta_loop_smoke_main_returns_nonzero_for_fail_status(self) -> None:
        from scripts import harness_ai_infra_meta_loop_smoke as smoke

        with patch.object(smoke, "run_ai_infra_meta_loop_smoke", return_value={"overall_status": "fail"}):
            self.assertEqual(smoke.main([]), 1)

    @unittest.skip("legacy smoke runtime removed")
    def test_ai_infra_meta_loop_smoke_helper_refuses_non_isolated_mode_before_repo_mutation(self) -> None:
        from scripts import harness_ai_infra_meta_loop_smoke as smoke

        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)

            with (
                patch.object(smoke, "_reset_to_clean_head") as reset_to_clean_head,
                patch.object(smoke, "_configure_git_identity") as configure_git_identity,
            ):
                with self.assertRaisesRegex(ValueError, "--isolate-clone"):
                    smoke.run_ai_infra_meta_loop_smoke(
                        repo_root,
                        "evaluator-scenario-ai-infra-meta-loop-runtime-test",
                        isolate_clone=False,
                    )

            reset_to_clean_head.assert_not_called()
            configure_git_identity.assert_not_called()


class HarnessLoopDemandMultiTaskTests(unittest.TestCase):
    def _create_parent(self, repo_root: Path, run_id: str = "parent-run") -> dict[str, object]:
        if not (repo_root / ".git").exists():
            init_git_repo(repo_root)
        payload = create_preflight_run(
            repo_root=repo_root,
            mode="demand-development",
            requirement="Build multi child feature",
            run_id=run_id,
            confirm=True,
        )
        payload["run_kind"] = "parent"
        payload["phase"] = "planning"
        payload["next_action"] = "run_parent_planner"
        payload["child_run_ids"] = []
        payload["current_child_run_id"] = ""
        payload["backlog"] = []
        payload["aggregate_acceptance"] = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "blocked": 0,
            "pending": 0,
            "user_decision_required": False,
        }
        payload["reader_summary"] = {
            "purpose": "Build multi child feature",
            "current_progress": "Planning",
            "next_step": "Create first child",
            "decision_needed": "No",
        }
        payload["accepted_changed_paths"] = []
        write_json_file(run_dir_for(repo_root, run_id) / "run.json", payload)
        return payload

    def _create_governance_parent(self, repo_root: Path, run_id: str = "ai-infra-loop-governance-dev") -> dict[str, object]:
        parent = self._create_parent(repo_root, run_id)
        parent["constraints"] = [
            *list(parent.get("constraints", [])),
            "ai-infra-loop-governance-dev",
        ]
        write_json_file(run_dir_for(repo_root, run_id) / "run.json", parent)
        return parent

    def _governance_candidate(self) -> dict[str, object]:
        return {
            "candidate_id": "project:kserve",
            "url": "https://github.com/kserve/kserve",
            "decision_inputs": {
                "source_type_count": 2,
                "local_gap_level": "major",
                "duplicate_status": "none",
                "acquisition_path": "github_backfill",
            },
            "hard_gates": {
                "has_gap_proof": True,
                "has_two_source_types_for_deep_dive": True,
                "has_evaluator_scenario": True,
                "has_domain_channel_plan": True,
                "has_depth_acquisition_proof": True,
                "identity_key_is_canonical": True,
            },
            "priority_score": 10,
        }

    def _write_governance_p0_artifacts(
        self,
        repo_root: Path,
        run_id: str = "ai-infra-loop-governance-dev",
        *,
        identity_key: str | None = None,
    ) -> None:
        run_dir = run_dir_for(repo_root, run_id)
        candidate = self._governance_candidate()
        classification = classify_candidate(candidate)
        expected_identity = str(classification["identity_key"])
        audited_identity = identity_key if identity_key is not None else expected_identity
        write_json_file(
            run_dir / "egress-proof.json",
            {
                "probes": [
                    {
                        "probe_url": "https://api.github.com",
                        "started_at": "2026-07-08T00:00:00Z",
                        "finished_at": "2026-07-08T00:00:01Z",
                        "dns_status": "ok",
                        "tls_status": "ok",
                        "http_status": 200,
                        "final_url": "https://api.github.com/",
                        "error_class": "",
                        "summary": "GitHub API reachable",
                    }
                ]
            },
        )
        write_json_file(
            run_dir / "identity-key-audit.json",
            {
                "status": "pass",
                "candidates": [
                    {
                        "candidate_id": "project:kserve",
                        "candidate": candidate,
                        "identity_key": audited_identity,
                    }
                ],
            },
        )
        write_json_file(
            run_dir / "depth-acquisition-smoke.json",
            {
                "status": "pass",
                "identity_key": expected_identity,
                "acquisition_path": "github_backfill",
                "bounded": True,
                "max_items": 25,
                "source_types": ["closed_issues", "release_notes"],
                "items": [
                    {"source_type": "closed_issues", "url": "https://api.github.com/repos/kserve/kserve/issues/1"},
                    {"source_type": "release_notes", "url": "https://github.com/kserve/kserve/releases/tag/v0.15.0"},
                ],
            },
        )
        write_json_file(
            run_dir / "candidate-scoring" / "candidate-001.json",
            {
                "status": "pass",
                "candidate": candidate,
                "identity_key": expected_identity,
                "classification": classification["classification"],
                "high_value_eligible": classification["high_value_eligible"],
            },
        )

    def _write_transition_evidence(self, repo_root: Path, name: str = "transition-notes.md") -> str:
        evidence_path = repo_root / "docs" / "harness" / name
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text("phase transition evidence\n", encoding="utf-8")
        return str(evidence_path.relative_to(repo_root))

    def _prepare_transition_parent(self, repo_root: Path, run_id: str = "ai-meta") -> tuple[dict[str, object], str, str]:
        init_git_repo(repo_root)
        source_policy_root = Path(__file__).resolve().parents[2] / "docs" / "harness" / "loop-policies"
        target_policy_root = repo_root / "docs" / "harness" / "loop-policies"
        target_policy_root.mkdir(parents=True, exist_ok=True)
        for policy_name in (
            "autonomous-knowledge-ai-infra-expanded.json",
            "autonomous-knowledge.json",
            "demand-development.json",
        ):
            shutil.copy2(source_policy_root / policy_name, target_policy_root / policy_name)
        self._create_parent(repo_root, run_id)
        parent = load_run(repo_root, run_id)
        parent["phase"] = "passed_waiting_human_merge"
        parent["next_action"] = "await_human_merge_confirmation"
        parent["last_result"] = "pass"
        write_json_file(run_dir_for(repo_root, run_id) / "run.json", parent)
        checkpoint_file = repo_root / "docs" / "harness" / "checkpoint.txt"
        checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_file.write_text("phase-a checkpoint\n", encoding="utf-8")
        subprocess.run(["git", "add", "docs/harness/checkpoint.txt"], cwd=repo_root, check=True)
        subprocess.run(
            ["git", "commit", "-m", "test: checkpoint commit", "--", "docs/harness/checkpoint.txt"],
            cwd=repo_root,
            check=True,
        )
        checkpoint_sha = (
            subprocess.run(["git", "rev-parse", "HEAD"], cwd=repo_root, check=True, capture_output=True, text=True)
            .stdout.strip()
        )
        evidence_path = self._write_transition_evidence(repo_root)
        return parent, checkpoint_sha, evidence_path

    def test_transition_meta_loop_to_expansion_creates_autonomous_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _parent, checkpoint_sha, evidence_path = self._prepare_transition_parent(repo_root)

            payload = harness_loop_orchestrator.transition_meta_loop_to_expansion(
                repo_root=repo_root,
                meta_run_id="ai-meta",
                expansion_run_id="ai-meta-expansion",
                policy_file="docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
                source_phase_commit=checkpoint_sha,
                transition_evidence=[evidence_path],
            )

            self.assertEqual(payload["run_id"], "ai-meta")
            parent = load_run(repo_root, "ai-meta")
            self.assertEqual(parent["phase"], "child_running")
            self.assertEqual(parent["phase_transition"], "development_to_expansion")
            self.assertEqual(parent["source_phase_commit"], checkpoint_sha)
            self.assertEqual(parent["expansion_run_id"], "ai-meta-expansion")
            self.assertEqual(parent["next_action"], "run_autonomous_planner")
            self.assertEqual(parent["transition_evidence"], [evidence_path])

            expansion = load_run(repo_root, "ai-meta-expansion")
            self.assertEqual(expansion["policy"], "autonomous_knowledge")
            self.assertEqual(expansion["domain"], "ai_infra")
            self.assertEqual(expansion["phase"], "planning")
            self.assertEqual(expansion["run_kind"], "child")
            self.assertEqual(expansion["parent_run_id"], "ai-meta")
            self.assertEqual(expansion["child_index"], 1)
            self.assertEqual(
                expansion["policy_file"],
                "docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
            )
            self.assertEqual(expansion["next_action"], "run_autonomous_planner")
            validate_run_payload(expansion)
            events = (run_dir_for(repo_root, "ai-meta") / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn("phase_transition", events)
            self.assertIn("ai-meta-expansion", events)

    def test_transition_meta_loop_blocks_without_checkpoint_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            parent, checkpoint_sha, evidence_path = self._prepare_transition_parent(repo_root)

            blocked_parent = dict(parent)
            blocked_parent["phase"] = "planning"
            write_json_file(run_dir_for(repo_root, "ai-meta") / "run.json", blocked_parent)
            with self.assertRaisesRegex(RuntimeError, "passed_waiting_human_merge"):
                harness_loop_orchestrator.transition_meta_loop_to_expansion(
                    repo_root=repo_root,
                    meta_run_id="ai-meta",
                    expansion_run_id="ai-meta-expansion",
                    policy_file="docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
                    source_phase_commit=checkpoint_sha,
                    transition_evidence=[evidence_path],
                )

            write_json_file(run_dir_for(repo_root, "ai-meta") / "run.json", parent)
            with self.assertRaisesRegex(RuntimeError, "commit"):
                harness_loop_orchestrator.transition_meta_loop_to_expansion(
                    repo_root=repo_root,
                    meta_run_id="ai-meta",
                    expansion_run_id="ai-meta-expansion",
                    policy_file="docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
                    source_phase_commit="deadbeef",
                    transition_evidence=[evidence_path],
                )

            with self.assertRaisesRegex(FileNotFoundError, "transition evidence"):
                harness_loop_orchestrator.transition_meta_loop_to_expansion(
                    repo_root=repo_root,
                    meta_run_id="ai-meta",
                    expansion_run_id="ai-meta-expansion",
                    policy_file="docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
                    source_phase_commit=checkpoint_sha,
                    transition_evidence=["docs/harness/missing-transition.md"],
                )

            with self.assertRaisesRegex(ValueError, "policy"):
                harness_loop_orchestrator.transition_meta_loop_to_expansion(
                    repo_root=repo_root,
                    meta_run_id="ai-meta",
                    expansion_run_id="ai-meta-expansion",
                    policy_file="docs/harness/loop-policies/demand-development.json",
                    source_phase_commit=checkpoint_sha,
                    transition_evidence=[evidence_path],
                )

            write_json_file(run_dir_for(repo_root, "ai-meta") / "run.json", parent)
            create_preflight_run(
                repo_root=repo_root,
                mode="autonomous-knowledge",
                requirement="Existing expansion child",
                run_id="ai-meta-expansion",
                domain="ai_infra",
                policy_file="docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
                confirm=True,
            )
            with self.assertRaisesRegex(RuntimeError, "already exists"):
                harness_loop_orchestrator.transition_meta_loop_to_expansion(
                    repo_root=repo_root,
                    meta_run_id="ai-meta",
                    expansion_run_id="ai-meta-expansion",
                    policy_file="docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
                    source_phase_commit=checkpoint_sha,
                    transition_evidence=[evidence_path],
                )

    def test_transition_meta_loop_blocks_non_demand_parent_in_passed_waiting_human_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            parent, checkpoint_sha, evidence_path = self._prepare_transition_parent(repo_root)
            parent["policy"] = "autonomous_knowledge"
            write_json_file(run_dir_for(repo_root, "ai-meta") / "run.json", parent)

            with self.assertRaisesRegex(RuntimeError, "demand_development"):
                harness_loop_orchestrator.transition_meta_loop_to_expansion(
                    repo_root=repo_root,
                    meta_run_id="ai-meta",
                    expansion_run_id="ai-meta-expansion",
                    policy_file="docs/harness/loop-policies/autonomous-knowledge-ai-infra-expanded.json",
                    source_phase_commit=checkpoint_sha,
                    transition_evidence=[evidence_path],
                )

    def test_transition_meta_loop_blocks_non_expanded_autonomous_policy_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            _parent, checkpoint_sha, evidence_path = self._prepare_transition_parent(repo_root)

            with self.assertRaisesRegex(ValueError, "autonomous-knowledge-ai-infra-expanded.json"):
                harness_loop_orchestrator.transition_meta_loop_to_expansion(
                    repo_root=repo_root,
                    meta_run_id="ai-meta",
                    expansion_run_id="ai-meta-expansion",
                    policy_file="docs/harness/loop-policies/autonomous-knowledge.json",
                    source_phase_commit=checkpoint_sha,
                    transition_evidence=[evidence_path],
                )

    def test_run_demand_multi_fake_completes_three_children_and_waits_for_human_merge(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root)

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="parent-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )

            parent = read_json_file(run_dir_for(repo_root, "parent-run") / "run.json")
            self.assertEqual(payload["phase"], "passed_waiting_human_merge")
            self.assertEqual(parent["phase"], "passed_waiting_human_merge")
            self.assertEqual(len(parent["child_run_ids"]), 3)
            self.assertEqual(parent["aggregate_acceptance"]["passed"], 3)
            self.assertEqual(parent["aggregate_acceptance"]["pending"], 0)
            self.assertTrue(parent["accepted_changed_paths"])
            self.assertFalse((repo_root / ".git" / "MERGE_HEAD").exists())
            for child_run_id in parent["child_run_ids"]:
                child = read_json_file(run_dir_for(repo_root, child_run_id) / "run.json")
                self.assertEqual(child["run_kind"], "child")
                self.assertEqual(child["phase"], "passed")
                self.assertEqual(child["parent_run_id"], "parent-run")

    def test_run_demand_multi_does_not_generate_legacy_audit_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            self._create_parent(repo_root)

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="parent-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=1,
            )

            self.assertEqual(payload["phase"], "passed_waiting_human_merge")
            run_dir = run_dir_for(repo_root, "parent-run")
            self.assertFalse((run_dir / "deterministic-signals.json").exists())
            self.assertFalse((run_dir / "audit-reports").exists())

    def test_run_auditor_fake_is_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            self._create_parent(repo_root)

            with self.assertRaisesRegex(RuntimeError, "disabled.*Supervisor Reviewer"):
                run_auditor(repo_root, "parent-run", driver="fake")
            self.assertFalse((run_dir_for(repo_root, "parent-run") / "audit-reports").exists())

    def test_run_demand_multi_ignores_legacy_open_must_fix_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root)
            parent = load_run(repo_root, "parent-run")
            parent["run_kind"] = "parent"
            parent["phase"] = "planning"
            parent["current_child_run_id"] = ""
            parent["child_run_ids"] = []
            parent["backlog"] = []
            parent["accepted_changed_paths"] = []
            parent["aggregate_acceptance"] = {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "blocked": 0,
                "pending": 0,
                "user_decision_required": False,
            }
            parent["reader_summary"] = {
                "purpose": parent["requirement"],
                "current_progress": "Planning",
                "next_step": "Run parent planner",
                "decision_needed": "No",
            }
            save_run(repo_root, parent)
            seed_open_must_fix_audit(repo_root, "parent-run")

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="parent-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=1,
            )

            parent = load_run(repo_root, "parent-run")
            self.assertEqual(payload["phase"], "passed_waiting_human_merge")
            self.assertEqual(parent["phase"], "passed_waiting_human_merge")
            self.assertNotEqual(parent["next_action"], "create_audit_remediation_task")
            self.assertEqual(len(parent["child_run_ids"]), 1)
            self.assertFalse(
                (run_dir_for(repo_root, "parent-run") / "audit-reports" / "audit-002.json").exists()
            )

    def test_run_demand_multi_audit_blocked_runs_remediation_child_and_rechecks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root)
            seed_open_must_fix_audit(repo_root, "parent-run")
            legacy = load_run(repo_root, "parent-run")
            legacy["phase"] = "audit_blocked"
            legacy["next_action"] = "create_audit_remediation_task"
            legacy["last_result"] = "blocked"
            save_run(repo_root, legacy)

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="parent-run",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=1,
            )

            parent = load_run(repo_root, "parent-run")
            self.assertEqual(payload["phase"], "passed_waiting_human_merge")
            self.assertEqual(parent["last_result"], "pass")
            self.assertEqual(len(parent["child_run_ids"]), 1)
            self.assertEqual(parent["_audit_remediation"]["status"], "resolved")
            child = load_run(repo_root, parent["child_run_ids"][0])
            self.assertTrue(child["audit_remediation"])
            planner_payload = read_json_file(run_dir_for(repo_root, "parent-run") / "planner-output.json")
            self.assertEqual(planner_payload["audit_response"]["handled_findings"], ["audit-001-repeat-001"])
            self.assertEqual(planner_payload["audit_response"]["planned_remediation_task"], child["run_id"])
            self.assertFalse(
                (run_dir_for(repo_root, "parent-run") / "audit-reports" / "audit-002.json").exists()
            )
            remediation = read_json_file(run_dir_for(repo_root, "parent-run") / "audit-remediation-result.json")
            self.assertEqual(remediation["status"], "pass")
            self.assertEqual(remediation["remediation_run_id"], child["run_id"])
            self.assertEqual(remediation["new_audit_report"], "")

    def test_run_demand_multi_audit_blocked_uses_deterministic_remediation_planner_with_codex_driver(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root)
            seed_open_must_fix_audit(repo_root, "parent-run")
            legacy = load_run(repo_root, "parent-run")
            legacy["phase"] = "audit_blocked"
            legacy["next_action"] = "create_audit_remediation_task"
            legacy["last_result"] = "blocked"
            save_run(repo_root, legacy)

            with patch.object(
                harness_loop_orchestrator,
                "_run_codex_demand_parent_planner",
                side_effect=AssertionError("audit remediation planner must be orchestrator-owned"),
            ):
                payload = run_demand_multi(
                    repo_root=repo_root,
                    run_id="parent-run",
                    planner_driver="codex-exec",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_children=1,
                )

            self.assertEqual(payload["phase"], "passed_waiting_human_merge")
            parent = load_run(repo_root, "parent-run")
            self.assertEqual(parent["_audit_remediation"]["status"], "resolved")
            self.assertFalse(
                (run_dir_for(repo_root, "parent-run") / "audit-reports" / "audit-002.json").exists()
            )

    def test_run_demand_multi_codex_exec_runs_parent_child_and_evaluator_without_real_codex(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "codex-parent")
            agent_calls: list[tuple[str, str, int]] = []
            evaluator_commands: list[list[str]] = []

            def write_agent_output(**kwargs: object) -> dict[str, object]:
                role = str(kwargs["role"])
                run_id = str(kwargs["run_id"])
                output_path = Path(str(kwargs["output_json_path"]))
                agent_calls.append((role, run_id, int(kwargs["attempt"])))
                if role == "planner":
                    write_json_file(
                        output_path,
                        {
                            "task_id": "codex-parent-task",
                            "policy": "demand_development",
                            "task_kind": "registered_task",
                            "title": "Codex demand parent planner",
                            "goal": "Build multi child feature",
                            "non_goals": [],
                            "allowed_paths": [],
                            "denylist_paths": [],
                            "verify_commands": [],
                            "evaluator_scenarios_path": "",
                            "stop_conditions": [
                                "passed_waiting_human_merge",
                                "stopped_blocked",
                                "stopped_budget",
                            ],
                            "next_planning_hint": "",
                            "skill_invocations": [],
                            "backlog": [],
                            "planner_decision": "next_child",
                            "next_child_task": {
                                "child_id": "child-001",
                                "title": "Codex child 1",
                                "description": "Implement codex child 1",
                                "allowed_paths": ["generated/codex-child-001.txt"],
                                "denylist_paths": [".env"],
                                "verify_commands": [],
                                "scenario_commands": [],
                                "done_criteria": ["codex child passes evaluator"],
                            },
                            "blocked_reason": "",
                            "done_criteria": [],
                            "reader_summary": {
                                "purpose": "Build multi child feature",
                                "current_progress": "0 children passed",
                                "next_step": "Run codex child",
                                "decision_needed": "No",
                            },
                            "decision_required": False,
                        },
                    )
                elif role == "generator":
                    generated_path = repo_root / "generated" / "codex-child-001.txt"
                    generated_path.parent.mkdir(parents=True, exist_ok=True)
                    generated_path.write_text("codex child\n", encoding="utf-8")
                    write_json_file(
                        output_path,
                        {
                            "task_id": "codex-parent-child-001-task",
                            "status": "implemented",
                            "changed_paths": ["generated/codex-child-001.txt"],
                            "commit": "",
                            "verify_commands": [],
                            "verify_results": [{"command": "codex child verification", "status": "pass"}],
                            "artifacts": [],
                            "cleanup_required": False,
                            "notes": "codex demand child generated",
                            "skill_invocations": [],
                        },
                    )
                else:
                    self.fail(f"unexpected codex prompt role: {role}")
                return {"status": "pass", "run_id": run_id, "role": role, "attempt": int(kwargs["attempt"])}

            def fake_command_runner(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
                if command[:2] == ["git", "status"]:
                    return subprocess.CompletedProcess(command, 128, "", "")
                evaluator_commands.append(command)
                self.assertIn("run-task-gate-once", command)
                self.assertIn("--driver", command)
                self.assertIn("codex-exec", command)
                self.assertIn("--task-contract", command)
                from scripts.harness_evaluator_cli import create_task_bundle

                template_root = repo_root / ".codex" / "evaluations" / "templates"
                template_root.mkdir(parents=True, exist_ok=True)
                (template_root / "artifacts.template.json").write_text("{}\n", encoding="utf-8")
                (template_root / "summary.template.md").write_text("# Summary\n", encoding="utf-8")
                task_id = command[command.index("--task-id") + 1]
                task_contract = Path(command[command.index("--task-contract") + 1])
                bundle = create_task_bundle(
                    repo_root,
                    task_id,
                    1,
                    bundle_name="20260716T000000Z-attempt-1",
                    task_contract_path=task_contract,
                )
                input_path = bundle / "input.json"
                input_payload = read_json_file(input_path)
                input_payload["loop_run_id"] = command[command.index("--loop-run-id") + 1]
                input_payload["loop_generator_attempt"] = int(
                    command[command.index("--generator-attempt") + 1]
                )
                write_json_file(input_path, input_payload)
                write_json_file(
                    bundle / "result.json",
                    {
                        "status": "pass",
                        "gate": "task",
                        "task_id": task_id,
                        "final_bundle_id": "",
                        "attempt": 1,
                        "summary": "pass",
                        "findings": [],
                        "scenario_results": [
                            {
                                "scenario_id": scenario["scenario_id"],
                                "status": "pass",
                                "evidence": ["scenario-command-results.json"],
                                "notes": "pass",
                            }
                            for scenario in input_payload["user_scenarios"]
                        ],
                        "rerun_commands": [],
                        "environment_checks": [],
                        "verdict_reason": "pass",
                        "next_action": "proceed_to_user_acceptance",
                    },
                )
                return subprocess.CompletedProcess(command, 0, "codex evaluator pass\n", "")

            with (
                patch("scripts.harness_loop_orchestrator.run_codex_prompt", side_effect=write_agent_output),
                patch("scripts.harness_loop_orchestrator.subprocess.run", side_effect=fake_command_runner),
            ):
                payload = run_demand_multi(
                    repo_root=repo_root,
                    run_id="codex-parent",
                    planner_driver="codex-exec",
                    generator_driver="codex-exec",
                    evaluator_driver="codex-exec",
                    max_eval_attempts=2,
                    max_children=1,
                )

            parent = read_json_file(run_dir_for(repo_root, "codex-parent") / "run.json")
            child_run_id = parent["child_run_ids"][0]
            child = read_json_file(run_dir_for(repo_root, child_run_id) / "run.json")
            evaluator_result = read_json_file(run_dir_for(repo_root, child_run_id) / "evaluator-result.json")
            self.assertEqual(payload["phase"], "passed_waiting_human_merge")
            self.assertEqual(parent["aggregate_acceptance"]["passed"], 1)
            self.assertEqual(parent["aggregate_acceptance"]["pending"], 0)
            self.assertEqual(parent["accepted_changed_paths"], ["generated/codex-child-001.txt"])
            self.assertEqual(child["phase"], "passed")
            self.assertEqual(evaluator_result["driver"], "codex-exec")
            self.assertEqual(agent_calls, [("planner", "codex-parent", 1), ("generator", child_run_id, 1)])
            self.assertEqual(len(evaluator_commands), 1)

    def test_governance_demand_multi_blocks_before_child_when_p0_artifacts_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_governance_parent(repo_root)

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="ai-infra-loop-governance-dev",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=1,
            )

            run_dir = run_dir_for(repo_root, "ai-infra-loop-governance-dev")
            parent = read_json_file(run_dir / "run.json")
            preflight = read_json_file(run_dir / "governance-preflight-result.json")
            events = (run_dir / "events.jsonl").read_text(encoding="utf-8")
            self.assertEqual(payload["phase"], "stopped_blocked")
            self.assertEqual(parent["child_run_ids"], [])
            self.assertEqual(parent["next_action"], "collect_governance_preflight_evidence")
            self.assertIn("P0 governance preflight artifacts", parent["reader_summary"]["next_step"])
            self.assertEqual(preflight["status"], "blocked")
            self.assertIn(".codex/loop-runs/ai-infra-loop-governance-dev/egress-proof.json", preflight["missing_artifacts"])
            self.assertIn("governance preflight", events)
            self.assertIn("egress-proof.json", events)

    def test_governance_demand_multi_blocks_before_child_when_identity_audit_is_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_governance_parent(repo_root)
            self._write_governance_p0_artifacts(repo_root, identity_key="github-repo:kserve/not-kserve")

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="ai-infra-loop-governance-dev",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=1,
            )

            run_dir = run_dir_for(repo_root, "ai-infra-loop-governance-dev")
            parent = read_json_file(run_dir / "run.json")
            preflight = read_json_file(run_dir / "governance-preflight-result.json")
            self.assertEqual(payload["phase"], "stopped_blocked")
            self.assertEqual(parent["child_run_ids"], [])
            self.assertEqual(parent["next_action"], "collect_governance_preflight_evidence")
            self.assertTrue(
                any("identity-key-audit.json candidates[0] identity_key" in finding for finding in preflight["findings"])
            )

    def test_governance_demand_multi_with_p0_artifacts_allows_child_and_requires_artifacts_in_contract(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_governance_parent(repo_root)
            self._write_governance_p0_artifacts(repo_root)

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="ai-infra-loop-governance-dev",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=1,
            )

            parent = read_json_file(run_dir_for(repo_root, "ai-infra-loop-governance-dev") / "run.json")
            child_run_id = parent["child_run_ids"][0]
            task_contract = read_json_file(run_dir_for(repo_root, child_run_id) / "task-contract.json")
            self.assertEqual(payload["phase"], "passed_waiting_human_merge")
            self.assertIn(".codex/loop-runs/ai-infra-loop-governance-dev/egress-proof.json", task_contract["artifact_paths"])
            self.assertIn(
                ".codex/loop-runs/ai-infra-loop-governance-dev/candidate-scoring/candidate-001.json",
                task_contract["artifact_paths"],
            )
            self.assertTrue(
                any(
                    "P0 governance preflight artifacts are present"
                    in expected
                    for scenario in task_contract["user_scenarios"]
                    for expected in scenario["expected_outcomes"]
                )
            )

    def test_run_demand_multi_fake_in_git_repo_ignores_previous_child_internal_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            self._create_parent(repo_root, "git-parent")

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="git-parent",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )

            parent = read_json_file(run_dir_for(repo_root, "git-parent") / "run.json")
            self.assertEqual(payload["phase"], "passed_waiting_human_merge")
            self.assertEqual(parent["phase"], "passed_waiting_human_merge")
            self.assertEqual(len(parent["child_run_ids"]), 3)
            self.assertEqual(parent["aggregate_acceptance"]["passed"], 3)
            parent_events = (run_dir_for(repo_root, "git-parent") / "events.jsonl").read_text(encoding="utf-8")
            self.assertNotIn("unexpected dirty path", parent_events)

    def test_run_demand_multi_repairs_same_failed_child_before_next_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "repair-parent")

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="repair-parent",
                planner_driver="fake",
                generator_driver="fake-fail-child-2-once",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )

            parent = read_json_file(run_dir_for(repo_root, "repair-parent") / "run.json")
            self.assertEqual(payload["phase"], "passed_waiting_human_merge")
            self.assertEqual(parent["aggregate_acceptance"]["passed"], 3)
            self.assertEqual(len(parent["child_run_ids"]), 3)
            child2 = read_json_file(run_dir_for(repo_root, parent["child_run_ids"][1]) / "run.json")
            self.assertEqual(child2["phase"], "passed")
            events = (run_dir_for(repo_root, child2["run_id"]) / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn("repair", events)

    def test_run_demand_multi_blocks_when_child_repair_attempts_exhausted(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "exhausted-parent")

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="exhausted-parent",
                planner_driver="fake",
                generator_driver="fake-fail-child-2-once",
                evaluator_driver="fake",
                max_eval_attempts=1,
                max_children=3,
            )

            parent = read_json_file(run_dir_for(repo_root, "exhausted-parent") / "run.json")
            child2 = read_json_file(run_dir_for(repo_root, parent["child_run_ids"][1]) / "run.json")
            child2_events = (run_dir_for(repo_root, child2["run_id"]) / "events.jsonl").read_text(encoding="utf-8")
            parent_events = (run_dir_for(repo_root, "exhausted-parent") / "events.jsonl").read_text(encoding="utf-8")
            self.assertEqual(payload["phase"], "stopped_blocked")
            self.assertEqual(parent["phase"], "stopped_blocked")
            self.assertEqual(parent["last_result"], "blocked")
            self.assertTrue(parent["aggregate_acceptance"]["user_decision_required"])
            self.assertNotEqual(child2["phase"], "passed")
            self.assertEqual(child2["last_result"], "fail")
            self.assertEqual(parent["aggregate_acceptance"]["passed"], 1)
            self.assertIn("Evaluator failed child", child2_events)
            self.assertIn("max attempts exhausted", parent_events)

    def test_run_demand_multi_exhausted_child_keeps_aggregate_buckets_consistent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "bucket-parent")

            run_demand_multi(
                repo_root=repo_root,
                run_id="bucket-parent",
                planner_driver="fake",
                generator_driver="fake-fail-child-2-once",
                evaluator_driver="fake",
                max_eval_attempts=1,
                max_children=3,
            )

            parent = read_json_file(run_dir_for(repo_root, "bucket-parent") / "run.json")
            aggregate = parent["aggregate_acceptance"]
            self.assertEqual(aggregate["total"], 3)
            self.assertEqual(aggregate["passed"], 1)
            self.assertEqual(aggregate["blocked"], 1)
            self.assertEqual(aggregate["pending"], 1)
            self.assertEqual(
                aggregate["passed"] + aggregate["failed"] + aggregate["blocked"] + aggregate["pending"],
                aggregate["total"],
            )

    def test_run_demand_multi_stopped_budget_rerun_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "budget-idempotent-parent")
            run_demand_multi(
                repo_root=repo_root,
                run_id="budget-idempotent-parent",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=0,
            )
            parent_before = read_json_file(run_dir_for(repo_root, "budget-idempotent-parent") / "run.json")
            aggregate_before = dict(parent_before["aggregate_acceptance"])
            accepted_before = list(parent_before["accepted_changed_paths"])
            child_ids_before = list(parent_before["child_run_ids"])

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="budget-idempotent-parent",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )

            parent_after = read_json_file(run_dir_for(repo_root, "budget-idempotent-parent") / "run.json")
            self.assertEqual(payload["phase"], "stopped_budget")
            self.assertEqual(parent_after["phase"], "stopped_budget")
            self.assertEqual(parent_after["child_run_ids"], child_ids_before)
            self.assertEqual(parent_after["aggregate_acceptance"], aggregate_before)
            self.assertEqual(parent_after["accepted_changed_paths"], accepted_before)

    def test_run_demand_multi_child_running_waits_for_current_unpassed_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "child-running-parent")
            run_demand_multi(
                repo_root=repo_root,
                run_id="child-running-parent",
                planner_driver="fake",
                generator_driver="fake-stop-after-child-1",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )
            parent_before = read_json_file(run_dir_for(repo_root, "child-running-parent") / "run.json")
            child_run_id = parent_before["child_run_ids"][0]
            child = read_json_file(run_dir_for(repo_root, child_run_id) / "run.json")
            child["phase"] = "repair_needed"
            child["last_result"] = "fail"
            child["next_action"] = "repair_child"
            write_json_file(run_dir_for(repo_root, child_run_id) / "run.json", child)
            parent_before["phase"] = "child_running"
            parent_before["next_action"] = "repair_child"
            write_json_file(run_dir_for(repo_root, "child-running-parent") / "run.json", parent_before)

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="child-running-parent",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )

            parent_after = read_json_file(run_dir_for(repo_root, "child-running-parent") / "run.json")
            parent_events = (run_dir_for(repo_root, "child-running-parent") / "events.jsonl").read_text(encoding="utf-8")
            self.assertEqual(payload["phase"], "child_running")
            self.assertEqual(parent_after["phase"], "child_running")
            self.assertEqual(parent_after["child_run_ids"], [child_run_id])
            self.assertEqual(parent_after["current_child_run_id"], child_run_id)
            self.assertIn("current child", parent_events)

    def test_run_demand_multi_terminal_rerun_returns_status_without_new_children(self) -> None:
        for run_id, expected_phase, planner_driver, max_children in [
            ("terminal-blocked", "stopped_blocked", "fake-blocked", 3),
            ("terminal-passed", "passed_waiting_human_merge", "fake", 2),
        ]:
            with self.subTest(run_id=run_id), tempfile.TemporaryDirectory() as tmp:
                repo_root = Path(tmp)
                self._create_parent(repo_root, run_id)
                run_demand_multi(
                    repo_root=repo_root,
                    run_id=run_id,
                    planner_driver=planner_driver,
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_children=max_children,
                )
                parent_before = read_json_file(run_dir_for(repo_root, run_id) / "run.json")
                child_ids_before = list(parent_before["child_run_ids"])
                aggregate_before = dict(parent_before["aggregate_acceptance"])

                payload = run_demand_multi(
                    repo_root=repo_root,
                    run_id=run_id,
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_children=max_children,
                )

                parent_after = read_json_file(run_dir_for(repo_root, run_id) / "run.json")
                self.assertEqual(payload["phase"], expected_phase)
                self.assertEqual(parent_after["phase"], expected_phase)
                self.assertEqual(parent_after["child_run_ids"], child_ids_before)
                self.assertEqual(parent_after["aggregate_acceptance"], aggregate_before)

    def test_run_demand_multi_rejects_child_run_id_without_nested_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "child-reject-parent")
            run_demand_multi(
                repo_root=repo_root,
                run_id="child-reject-parent",
                planner_driver="fake",
                generator_driver="fake-stop-after-child-1",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=2,
            )
            parent = read_json_file(run_dir_for(repo_root, "child-reject-parent") / "run.json")
            child_run_id = parent["child_run_ids"][0]

            with self.assertRaisesRegex((RuntimeError, ValueError), "parent"):
                run_demand_multi(
                    repo_root=repo_root,
                    run_id=child_run_id,
                    planner_driver="fake",
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_children=2,
                )

            nested_child_run_id = f"{child_run_id}-child-001"
            self.assertFalse(run_dir_for(repo_root, nested_child_run_id).exists())

    def test_run_demand_multi_planner_blocked_or_failed_creates_no_child(self) -> None:
        for planner_driver, expected_reason in [
            ("fake-blocked", "fake planner blocked"),
            ("fake-failed", "fake planner failed"),
        ]:
            with self.subTest(planner_driver=planner_driver), tempfile.TemporaryDirectory() as tmp:
                repo_root = Path(tmp)
                self._create_parent(repo_root, f"{planner_driver}-parent")

                payload = run_demand_multi(
                    repo_root=repo_root,
                    run_id=f"{planner_driver}-parent",
                    planner_driver=planner_driver,
                    generator_driver="fake",
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_children=3,
                )

                parent = read_json_file(run_dir_for(repo_root, f"{planner_driver}-parent") / "run.json")
                planner_output = read_json_file(run_dir_for(repo_root, f"{planner_driver}-parent") / "planner-output.json")
                self.assertEqual(payload["phase"], "stopped_blocked")
                self.assertEqual(parent["child_run_ids"], [])
                self.assertEqual(planner_output["blocked_reason"], expected_reason)

    def test_run_demand_multi_writes_child_task_contract_and_stops_on_budget(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "budget-parent")

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="budget-parent",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=0,
            )

            parent = read_json_file(run_dir_for(repo_root, "budget-parent") / "run.json")
            self.assertEqual(payload["phase"], "stopped_budget")
            self.assertEqual(parent["child_run_ids"], [])

            self._create_parent(repo_root, "contract-parent")
            run_demand_multi(
                repo_root=repo_root,
                run_id="contract-parent",
                planner_driver="fake",
                generator_driver="fake-stop-after-child-1",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=2,
            )
            contract_parent = read_json_file(run_dir_for(repo_root, "contract-parent") / "run.json")
            child_run_id = contract_parent["child_run_ids"][0]
            task_contract = read_json_file(run_dir_for(repo_root, child_run_id) / "task-contract.json")
            self.assertEqual(task_contract["task_id"], f"{child_run_id}-task")
            self.assertEqual(task_contract["evaluator_driver"], "harness_auto_gate")
            self.assertTrue(task_contract["must_simulate"])

    def test_run_demand_multi_blocks_on_unaccepted_dirty_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            self._create_parent(repo_root, "dirty-parent")

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="dirty-parent",
                planner_driver="fake",
                generator_driver="fake-dirty-path",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=1,
            )

            parent = read_json_file(run_dir_for(repo_root, "dirty-parent") / "run.json")
            self.assertEqual(payload["phase"], "stopped_blocked")
            self.assertEqual(parent["last_result"], "blocked")
            child = read_json_file(run_dir_for(repo_root, parent["child_run_ids"][0]) / "run.json")
            self.assertEqual(child["phase"], "stopped_blocked")
            self.assertEqual(child["last_result"], "blocked")
            self.assertEqual(child["next_action"], "inspect_blocked_diagnostics")
            self.assertEqual(child["attempts"]["generator"], 1)
            self.assertFalse((run_dir_for(repo_root, child["run_id"]) / "evaluator-result.json").exists())
            events = (run_dir_for(repo_root, "dirty-parent") / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn("unexpected dirty path", events)

    def test_run_demand_multi_blocks_when_child_allowed_path_was_baseline_dirty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            dirty_path = repo_root / "generated" / "child-001.txt"
            dirty_path.parent.mkdir(parents=True, exist_ok=True)
            dirty_path.write_text("pre-existing user change\n", encoding="utf-8")
            self._create_parent(repo_root, "baseline-overlap-parent")

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="baseline-overlap-parent",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=1,
            )

            parent = read_json_file(run_dir_for(repo_root, "baseline-overlap-parent") / "run.json")
            child = read_json_file(run_dir_for(repo_root, parent["child_run_ids"][0]) / "run.json")
            events = (run_dir_for(repo_root, "baseline-overlap-parent") / "events.jsonl").read_text(encoding="utf-8")
            self.assertEqual(payload["phase"], "stopped_blocked")
            self.assertEqual(parent["phase"], "stopped_blocked")
            self.assertEqual(parent["last_result"], "blocked")
            self.assertTrue(parent["aggregate_acceptance"]["user_decision_required"])
            self.assertNotEqual(child["phase"], "passed")
            self.assertNotIn("generated/child-001.txt", parent["accepted_changed_paths"])
            self.assertIn("baseline dirty path", events)
            self.assertIn("generated/child-001.txt", events)
            self.assertEqual(dirty_path.read_text(encoding="utf-8"), "pre-existing user change\n")

    def test_demand_dirty_paths_only_ignore_current_parent_and_child_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            parent = self._create_parent(repo_root, "dirty-scope-parent")

            from scripts import harness_loop_orchestrator as orchestrator

            child = orchestrator._create_child_run(
                repo_root,
                parent,
                1,
                {
                    "child_id": "child-001",
                    "title": "Fake child 1",
                    "description": "Implement fake child 1",
                    "allowed_paths": ["generated/child-001.txt"],
                    "denylist_paths": [".env"],
                    "verify_commands": [],
                    "scenario_commands": [],
                    "done_criteria": ["child 1 passes fake evaluator"],
                },
            )
            other_run_path = repo_root / ".codex" / "loop-runs" / "other-run" / "unexpected.txt"
            other_run_path.parent.mkdir(parents=True, exist_ok=True)
            other_run_path.write_text("unexpected\n", encoding="utf-8")

            unexpected = orchestrator._dirty_paths_after_baseline(repo_root, parent, child)

            self.assertEqual(unexpected, [".codex/loop-runs/other-run/unexpected.txt"])

    def test_run_demand_multi_blocks_on_agent_timeout_invalid_json_and_missing_artifact(self) -> None:
        for driver, expected in [
            ("fake-timeout", "timeout"),
            ("fake-invalid-json", "invalid_json"),
            ("fake-missing-artifact", "missing artifact"),
        ]:
            with self.subTest(driver=driver), tempfile.TemporaryDirectory() as tmp:
                repo_root = Path(tmp)
                self._create_parent(repo_root, f"agent-{driver}")

                payload = run_demand_multi(
                    repo_root=repo_root,
                    run_id=f"agent-{driver}",
                    planner_driver="fake",
                    generator_driver=driver,
                    evaluator_driver="fake",
                    max_eval_attempts=2,
                    max_children=1,
                )

                parent = read_json_file(run_dir_for(repo_root, f"agent-{driver}") / "run.json")
                self.assertEqual(payload["phase"], "stopped_blocked")
                self.assertTrue(parent["aggregate_acceptance"]["user_decision_required"])
                child = read_json_file(run_dir_for(repo_root, parent["child_run_ids"][0]) / "run.json")
                self.assertEqual(child["phase"], "stopped_blocked")
                self.assertEqual(child["last_result"], "blocked")
                self.assertEqual(child["next_action"], "inspect_blocked_diagnostics")
                self.assertFalse((run_dir_for(repo_root, child["run_id"]) / "evaluator-result.json").exists())
                events = (run_dir_for(repo_root, f"agent-{driver}") / "events.jsonl").read_text(encoding="utf-8")
                self.assertIn(expected, events)
                reason = {
                    "fake-timeout": "generator timeout",
                    "fake-invalid-json": "generator invalid_json",
                    "fake-missing-artifact": "generator missing artifact",
                }[driver]
                event_payloads = [json.loads(line) for line in events.splitlines()]
                blocked_summaries = [
                    event["summary"]
                    for event in event_payloads
                    if event["actor"] == "generator" and event["event_type"] == "blocked"
                ]
                self.assertEqual(blocked_summaries, [reason])

    def test_run_demand_multi_resumes_current_child_without_repeating_passed_child(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "resume-parent")

            first = run_demand_multi(
                repo_root=repo_root,
                run_id="resume-parent",
                planner_driver="fake",
                generator_driver="fake-stop-after-child-1",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )
            self.assertEqual(first["phase"], "child_running")
            parent_before = read_json_file(run_dir_for(repo_root, "resume-parent") / "run.json")
            first_child = parent_before["child_run_ids"][0]
            first_child_events_before = (run_dir_for(repo_root, first_child) / "events.jsonl").read_text(encoding="utf-8")

            second = run_demand_multi(
                repo_root=repo_root,
                run_id="resume-parent",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )

            parent_after = read_json_file(run_dir_for(repo_root, "resume-parent") / "run.json")
            first_child_events_after = (run_dir_for(repo_root, first_child) / "events.jsonl").read_text(encoding="utf-8")
            self.assertEqual(second["phase"], "passed_waiting_human_merge")
            self.assertEqual(len(parent_after["child_run_ids"]), 3)
            self.assertEqual(first_child_events_before, first_child_events_after)
            parent_events = (run_dir_for(repo_root, "resume-parent") / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn("resume", parent_events)

    def test_run_demand_multi_resume_reconciles_passed_child_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            init_git_repo(repo_root)
            self._create_parent(repo_root, "resume-reconcile-parent")
            first = run_demand_multi(
                repo_root=repo_root,
                run_id="resume-reconcile-parent",
                planner_driver="fake",
                generator_driver="fake-stop-after-child-1",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )
            self.assertEqual(first["phase"], "child_running")
            parent_before = read_json_file(run_dir_for(repo_root, "resume-reconcile-parent") / "run.json")
            first_child = parent_before["child_run_ids"][0]
            parent_before["aggregate_acceptance"]["passed"] = 0
            parent_before["aggregate_acceptance"]["pending"] = parent_before["aggregate_acceptance"]["total"]
            parent_before["accepted_changed_paths"] = []
            parent_before["phase"] = "child_running"
            parent_before["current_child_run_id"] = first_child
            parent_before["next_action"] = "resume_current_child"
            write_json_file(run_dir_for(repo_root, "resume-reconcile-parent") / "run.json", parent_before)

            second = run_demand_multi(
                repo_root=repo_root,
                run_id="resume-reconcile-parent",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )

            parent_after = read_json_file(run_dir_for(repo_root, "resume-reconcile-parent") / "run.json")
            self.assertEqual(second["phase"], "passed_waiting_human_merge")
            self.assertEqual(parent_after["phase"], "passed_waiting_human_merge")
            self.assertEqual(parent_after["child_run_ids"][0], first_child)
            self.assertEqual(len(parent_after["child_run_ids"]), 3)
            self.assertEqual(parent_after["aggregate_acceptance"]["passed"], 3)
            self.assertEqual(parent_after["aggregate_acceptance"]["pending"], 0)
            self.assertIn("generated/child-001.txt", parent_after["accepted_changed_paths"])
            self.assertEqual(parent_after["accepted_changed_paths"].count("generated/child-001.txt"), 1)
            parent_events = (run_dir_for(repo_root, "resume-reconcile-parent") / "events.jsonl").read_text(encoding="utf-8")
            self.assertIn("resume", parent_events)
            self.assertNotIn("unexpected dirty path", parent_events)

    def test_run_demand_multi_blocks_when_passed_child_generator_result_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "missing-child-artifact-parent")
            first = run_demand_multi(
                repo_root=repo_root,
                run_id="missing-child-artifact-parent",
                planner_driver="fake",
                generator_driver="fake-stop-after-child-1",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )
            self.assertEqual(first["phase"], "child_running")
            parent_before = read_json_file(run_dir_for(repo_root, "missing-child-artifact-parent") / "run.json")
            first_child = parent_before["child_run_ids"][0]
            (run_dir_for(repo_root, first_child) / "generator-result.json").unlink()
            parent_before["aggregate_acceptance"]["passed"] = 0
            parent_before["aggregate_acceptance"]["pending"] = parent_before["aggregate_acceptance"]["total"]
            parent_before["accepted_changed_paths"] = []
            parent_before["phase"] = "child_running"
            parent_before["current_child_run_id"] = first_child
            parent_before["next_action"] = "resume_current_child"
            write_json_file(run_dir_for(repo_root, "missing-child-artifact-parent") / "run.json", parent_before)

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="missing-child-artifact-parent",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=3,
            )

            parent_after = read_json_file(run_dir_for(repo_root, "missing-child-artifact-parent") / "run.json")
            parent_events = (run_dir_for(repo_root, "missing-child-artifact-parent") / "events.jsonl").read_text(encoding="utf-8")
            self.assertEqual(payload["phase"], "stopped_blocked")
            self.assertEqual(parent_after["phase"], "stopped_blocked")
            self.assertEqual(parent_after["last_result"], "blocked")
            self.assertEqual(parent_after["next_action"], "inspect_blocked_diagnostics")
            self.assertTrue(parent_after["aggregate_acceptance"]["user_decision_required"])
            self.assertNotIn("generated/child-001.txt", parent_after["accepted_changed_paths"])
            self.assertIn("passed child artifact invalid", parent_events)
            self.assertIn(first_child, parent_events)

    def test_run_demand_multi_reconciles_existing_unpassed_child_before_planning(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            self._create_parent(repo_root, "stale-aggregate-parent")
            run_demand_multi(
                repo_root=repo_root,
                run_id="stale-aggregate-parent",
                planner_driver="fake",
                generator_driver="fake-stop-after-child-1",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=2,
            )
            parent_before = read_json_file(run_dir_for(repo_root, "stale-aggregate-parent") / "run.json")
            repair_child_id = parent_before["child_run_ids"][0]
            repair_child = read_json_file(run_dir_for(repo_root, repair_child_id) / "run.json")
            repair_child["phase"] = "repair_needed"
            repair_child["last_result"] = "fail"
            repair_child["next_action"] = "repair_child"
            write_json_file(run_dir_for(repo_root, repair_child_id) / "run.json", repair_child)
            parent_before["phase"] = "planning"
            parent_before["next_action"] = "run_parent_planner"
            parent_before["current_child_run_id"] = ""
            parent_before["aggregate_acceptance"]["total"] = 2
            parent_before["aggregate_acceptance"]["passed"] = 1
            parent_before["aggregate_acceptance"]["pending"] = 1
            write_json_file(run_dir_for(repo_root, "stale-aggregate-parent") / "run.json", parent_before)

            payload = run_demand_multi(
                repo_root=repo_root,
                run_id="stale-aggregate-parent",
                planner_driver="fake",
                generator_driver="fake",
                evaluator_driver="fake",
                max_eval_attempts=2,
                max_children=2,
            )

            parent_after = read_json_file(run_dir_for(repo_root, "stale-aggregate-parent") / "run.json")
            events = (run_dir_for(repo_root, "stale-aggregate-parent") / "events.jsonl").read_text(encoding="utf-8")
            self.assertEqual(payload["phase"], "child_running")
            self.assertEqual(parent_after["phase"], "child_running")
            self.assertEqual(parent_after["current_child_run_id"], repair_child_id)
            self.assertEqual(parent_after["next_action"], "repair_child")
            self.assertEqual(parent_after["child_run_ids"], [repair_child_id])
            self.assertNotEqual(parent_after["phase"], "passed_waiting_human_merge")
            self.assertIn("current child", events)
            self.assertIn("reconcile", events)

    def test_formal_suspicion_confirmed_bug_overrides_evaluator_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_id = "formal-run"
            run_dir = run_dir_for(repo_root, run_id)
            (run_dir / "formal-verification").mkdir(parents=True)
            run = {
                "run_id": run_id,
                "required_counterexample_reruns": [],
            }
            evaluator_payload = {
                "status": "pass",
                "task_id": "formal-run-task",
                "driver": "fake",
                "returncode": 0,
                "stdout": "evaluator pass\n",
                "stderr": "",
                "skill_invocations": [],
            }
            artifact_path = f".codex/loop-runs/{run_id}/counterexample-tests/formal-confirmed-bug.json"
            artifact = repo_root / artifact_path
            artifact.parent.mkdir(parents=True, exist_ok=True)
            write_json_file(
                artifact,
                {
                    "id": "formal-confirmed-bug",
                    "command": "python3 -m pytest -q scripts/tests/test_harness_loop_orchestrator.py::test_formal_confirmed_bug",
                    "status": "fail",
                    "returncode": 1,
                    "executed_at": "2026-07-08T00:00:00Z",
                },
            )
            write_json_file(
                run_dir / "formal-verification" / "formal-001.json",
                {
                    "phase": "formal_suspicion_pass",
                    "suspicions": [
                        {
                            "id": "formal-confirmed-bug",
                            "risk": "high",
                            "hypothesis": "a repaired path still violates a contract",
                            "counterexample": {
                                "type": "unit_test",
                                "artifact_path": artifact_path,
                                "command": "python3 -m pytest -q scripts/tests/test_harness_loop_orchestrator.py::test_formal_confirmed_bug",
                            },
                            "result": "confirmed_bug",
                            "repair_required": True,
                        }
                    ],
                },
            )

            updated = harness_loop_orchestrator._merge_formal_verification_result(repo_root, run, evaluator_payload)

            self.assertEqual(updated["status"], "fail")
            self.assertEqual(updated["returncode"], 1)
            self.assertEqual(updated["next_action"], "repair_and_reevaluate")
            self.assertEqual(
                run["required_counterexample_reruns"],
                [
                    {
                        "id": "formal-confirmed-bug",
                        "command": "python3 -m pytest -q scripts/tests/test_harness_loop_orchestrator.py::test_formal_confirmed_bug",
                        "artifact_path": artifact_path,
                    }
                ],
            )

    def test_formal_suspicion_requires_original_counterexample_rerun_before_pass(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            run_id = "formal-run"
            run_dir = run_dir_for(repo_root, run_id)
            formal_dir = run_dir / "formal-verification"
            formal_dir.mkdir(parents=True)
            run = {
                "run_id": run_id,
                "required_counterexample_reruns": [
                    {
                        "id": "formal-confirmed-bug",
                        "command": "python3 -m pytest -q scripts/tests/test_harness_loop_orchestrator.py::test_formal_confirmed_bug",
                        "artifact_path": f".codex/loop-runs/{run_id}/counterexample-tests/formal-confirmed-bug.json",
                    }
                ],
            }
            evaluator_payload = {
                "status": "pass",
                "task_id": "formal-run-task",
                "driver": "fake",
                "returncode": 0,
                "stdout": "evaluator pass\n",
                "stderr": "",
                "skill_invocations": [],
            }

            blocked = harness_loop_orchestrator._merge_formal_verification_result(repo_root, run, dict(evaluator_payload))

            self.assertEqual(blocked["status"], "fail")
            self.assertEqual(blocked["next_action"], "repair_and_reevaluate")
            self.assertIn("original counterexample rerun", blocked["stdout"])

            artifact_path = f".codex/loop-runs/{run_id}/counterexample-tests/formal-confirmed-bug.json"
            artifact = repo_root / artifact_path
            artifact.parent.mkdir(parents=True, exist_ok=True)
            write_json_file(
                artifact,
                {
                    "id": "formal-confirmed-bug",
                    "command": "python3 -m pytest -q scripts/tests/test_harness_loop_orchestrator.py::test_formal_confirmed_bug",
                    "status": "pass",
                    "returncode": 0,
                    "executed_at": "2026-07-08T00:00:00Z",
                },
            )
            write_json_file(
                formal_dir / "formal-002.json",
                {
                    "phase": "formal_suspicion_pass",
                    "suspicions": [
                        {
                            "id": "formal-confirmed-bug",
                            "risk": "high",
                            "hypothesis": "the original counterexample now passes after repair",
                            "counterexample": {
                                "type": "unit_test",
                                "artifact_path": artifact_path,
                                "command": "python3 -m pytest -q scripts/tests/test_harness_loop_orchestrator.py::test_formal_confirmed_bug",
                            },
                            "result": "disproved",
                            "repair_required": False,
                        }
                    ],
                },
            )

            cleared = harness_loop_orchestrator._merge_formal_verification_result(repo_root, run, dict(evaluator_payload))

            self.assertEqual(cleared["status"], "pass")
            self.assertNotIn("next_action", cleared)
            self.assertEqual(run["required_counterexample_reruns"], [])

    def test_run_evaluator_formal_bug_routes_to_repair_even_with_scenario_logs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            create_preflight_run(
                repo_root=repo_root,
                mode="demand-development",
                requirement="Formal suspicion with scenario logs",
                run_id="demo-run",
                task_id="formal-task",
                confirm=True,
            )
            write_fake_evaluator_scenario(repo_root, "formal-task")
            from scripts.harness_loop_orchestrator import _run_evaluator as run_evaluator, _run_generator as run_generator, _run_planner as run_planner

            run_planner(repo_root, "demo-run", driver="fake")
            run_generator(repo_root, "demo-run", driver="fake")
            run_dir = run_dir_for(repo_root, "demo-run")
            write_json_file(
                run_dir / "task-contract.json",
                {
                    "task_id": "formal-task",
                    "title": "Formal task",
                    "description": "Temporary formal task.",
                    "verify_commands": [],
                    "scenario_commands": ["python3 -c \"print('scenario artifact')\""],
                    "artifact_paths": [],
                    "required_services": [],
                    "evaluator_driver": "harness_auto_gate",
                    "eval_policy": {"task_level_required": True},
                    "allowed_scope": "local_repo_and_harness",
                    "must_simulate": True,
                    "user_scenarios": [
                        {
                            "scenario_id": "FORMAL-01",
                            "user_goal": "Run scenario with formal verification.",
                            "prerequisites": [],
                            "steps": ["Run command.", "Merge formal suspicion result."],
                            "expected_outcomes": ["Formal bug routes to repair."],
                            "failure_signals": ["Formal bug enters artifact hygiene."],
                        }
                    ],
                },
            )
            artifact_path = ".codex/loop-runs/demo-run/counterexample-tests/formal-confirmed-bug.json"
            artifact = repo_root / artifact_path
            artifact.parent.mkdir(parents=True, exist_ok=True)
            write_json_file(
                artifact,
                {
                    "id": "formal-confirmed-bug",
                    "command": "python3 -m pytest -q scripts/tests/test_harness_loop_orchestrator.py::test_formal_confirmed_bug",
                    "status": "fail",
                    "returncode": 1,
                    "executed_at": "2026-07-08T00:00:00Z",
                },
            )
            formal_dir = run_dir / "formal-verification"
            formal_dir.mkdir(parents=True)
            write_json_file(
                formal_dir / "formal-001.json",
                {
                    "phase": "formal_suspicion_pass",
                    "suspicions": [
                        {
                            "id": "formal-confirmed-bug",
                            "risk": "high",
                            "hypothesis": "a repaired path still violates a contract",
                            "counterexample": {
                                "type": "unit_test",
                                "artifact_path": artifact_path,
                                "command": "python3 -m pytest -q scripts/tests/test_harness_loop_orchestrator.py::test_formal_confirmed_bug",
                            },
                            "result": "confirmed_bug",
                            "repair_required": True,
                        }
                    ],
                },
            )

            output_path = run_evaluator(repo_root, "demo-run", driver="fake", max_attempts=2)

            evaluator_result = read_json_file(output_path)
            self.assertEqual(evaluator_result["status"], "fail")
            self.assertEqual(evaluator_result["next_action"], "repair_and_reevaluate")
            self.assertTrue((run_dir / "scenario-command-results.json").exists())
            run = read_json_file(run_dir / "run.json")
            self.assertEqual(run["phase"], "repair_needed")
            self.assertEqual(run["last_result"], "fail")
            self.assertEqual(run["next_action"], "repair_and_reevaluate")


if __name__ == "__main__":
    unittest.main()
