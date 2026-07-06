import json
import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

import scripts.harness_loop_autonomous as harness_loop_autonomous
from scripts.harness_loop_autonomous import (
    autonomous_allowed_paths,
    autonomous_denylist_paths,
    check_autonomous_scope,
    check_supply_chain,
    create_default_loop_state,
    decide_no_action,
    load_or_create_loop_state,
    policy_patterns_for_run,
    run_git_commit,
    write_loop_state,
)
from scripts.harness_loop_contracts import validate_loop_state_payload


class HarnessLoopAutonomousTests(unittest.TestCase):
    def _full_ai_infra_coverage_map(self, *, last_scanned_at: str | None = None) -> dict:
        scanned_at = last_scanned_at or "2026-07-02T00:00:00Z"
        return {
            "domain": "ai_infra",
            "domain_goal": "Expand wiki",
            "layers": {
                layer: {
                    "status": "covered",
                    "covered_pages": [f"wiki/{layer}.md"],
                    "raw_evidence": [f"raw/{layer}.json"],
                    "candidate_gaps": [],
                    "blocked_reason": "",
                    "last_scanned_at": scanned_at,
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
        }

    def test_create_default_loop_state_records_confirmed_no_action_standards(self) -> None:
        state = create_default_loop_state("ai_infra", "Expand wiki", scan_ttl_days=30)

        validate_loop_state_payload(state)
        self.assertEqual(state["domain"], "ai_infra")
        self.assertEqual(state["domain_goal"], "Expand wiki")
        self.assertEqual(state["last_planner_decision"], "planned")
        self.assertEqual(state["candidate_backlog"], [])
        self.assertEqual(state["coverage_gaps"], [])
        self.assertEqual(state["no_action_evidence"], [])

    def test_decide_no_action_requires_empty_backlog_and_fresh_scan(self) -> None:
        state = create_default_loop_state("ai_infra", "Expand wiki", scan_ttl_days=30)
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

        self.assertTrue(
            decide_no_action(
                state,
                coverage_map=self._full_ai_infra_coverage_map(last_scanned_at=state["last_scan_at"]),
            ).no_action
        )

    def test_decide_no_action_rejects_missing_evidence(self) -> None:
        state = create_default_loop_state("ai_infra", "Expand wiki", scan_ttl_days=30)
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

        decision = decide_no_action(
            state,
            coverage_map=self._full_ai_infra_coverage_map(last_scanned_at=state["last_scan_at"]),
        )

        self.assertFalse(decision.no_action)
        self.assertIn("no_action_evidence is empty", decision.reasons)

    def test_decide_no_action_rejects_scan_older_than_ttl_even_before_next_full_day(self) -> None:
        now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
        scan_at = now - timedelta(days=30, hours=1)
        state = create_default_loop_state("ai_infra", "Expand wiki", scan_ttl_days=30)
        state["last_scan_at"] = scan_at.isoformat().replace("+00:00", "Z")
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

        decision = decide_no_action(
            state,
            now=now,
            coverage_map=self._full_ai_infra_coverage_map(last_scanned_at=state["last_scan_at"]),
        )

        self.assertFalse(decision.no_action)
        self.assertIn("last_scan_at is stale", decision.reasons)

    def test_decide_no_action_requires_ai_infra_coverage_map(self) -> None:
        now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
        state = create_default_loop_state("ai_infra", "Expand wiki", scan_ttl_days=30)
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
                "title": "Coverage scan",
                "source": "coverage-map",
                "status": "complete",
                "updated_at": state["last_scan_at"],
                "evidence": ["coverage-map scan confirmed"],
            }
        ]

        missing_map = harness_loop_autonomous.decide_no_action(state, now=now, coverage_map=None)
        self.assertFalse(missing_map.no_action)
        self.assertIn("coverage_map is required for ai_infra no-action", missing_map.reasons)

        missing_layer_map = self._full_ai_infra_coverage_map(last_scanned_at=state["last_scan_at"])
        missing_layer_map["layers"].pop("hardware-accelerator")
        missing_layer = harness_loop_autonomous.decide_no_action(state, now=now, coverage_map=missing_layer_map)
        self.assertFalse(missing_layer.no_action)
        self.assertIn("coverage_map missing required layers", missing_layer.reasons)

        gap_map = self._full_ai_infra_coverage_map(last_scanned_at=state["last_scan_at"])
        gap_map["layers"]["hardware-accelerator"]["candidate_gaps"] = ["missing vendor coverage"]
        gap_decision = harness_loop_autonomous.decide_no_action(state, now=now, coverage_map=gap_map)
        self.assertFalse(gap_decision.no_action)
        self.assertIn("coverage_map has actionable candidate_gaps", gap_decision.reasons)

        stale_timestamp = (now - timedelta(days=31)).isoformat().replace("+00:00", "Z")
        stale_map = self._full_ai_infra_coverage_map(last_scanned_at=stale_timestamp)
        stale_decision = harness_loop_autonomous.decide_no_action(state, now=now, coverage_map=stale_map)
        self.assertFalse(stale_decision.no_action)
        self.assertIn("coverage_map has stale layers", stale_decision.reasons)

        non_reference_state = dict(state)
        non_reference_state["no_action_evidence"] = [
            {
                "id": "scan-2",
                "title": "Planner scan",
                "source": "planner",
                "status": "complete",
                "updated_at": state["last_scan_at"],
                "evidence": ["no candidates"],
            }
        ]
        evidence_decision = harness_loop_autonomous.decide_no_action(
            non_reference_state,
            now=now,
            coverage_map=self._full_ai_infra_coverage_map(last_scanned_at=state["last_scan_at"]),
        )
        self.assertFalse(evidence_decision.no_action)
        self.assertIn("no_action_evidence must reference coverage-map", evidence_decision.reasons)

    def test_scope_check_rejects_denylist_even_when_allowlist_matches(self) -> None:
        result = check_autonomous_scope(
            ["personal-wiki/domains/ai_infra/wiki/page.md", ".env"],
            autonomous_allowed_paths(),
            autonomous_denylist_paths(),
        )

        self.assertFalse(result.allowed)
        self.assertIn(".env", result.denied_paths)

    def test_scope_check_flags_manual_confirm_paths(self) -> None:
        result = check_autonomous_scope(
            ["tasks.json"],
            ["**"],
            autonomous_denylist_paths(),
            manual_confirm_patterns=["tasks.json"],
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.manual_confirm_paths, ["tasks.json"])

    def test_policy_patterns_allow_repo_wide_repairs_but_keep_denylist(self) -> None:
        allowed, denied, manual = policy_patterns_for_run(
            {
                "allowed_paths": ["**"],
                "denylist_paths": [".codex/**", "generated/**"],
                "manual_confirm_paths": [],
            },
            domain="ai_infra",
        )

        result = check_autonomous_scope(["scripts/harness_loop_orchestrator.py"], allowed, denied, manual)

        self.assertTrue(result.allowed)
        self.assertFalse(check_autonomous_scope([".codex/secret.log"], allowed, denied, manual).allowed)

    def test_expanded_policy_denies_superpowers_paths_even_with_repo_wide_allowlist(self) -> None:
        policy_path = Path(__file__).resolve().parents[2] / "docs" / "harness" / "loop-policies" / "autonomous-knowledge-ai-infra-expanded.json"
        with policy_path.open("r", encoding="utf-8") as handle:
            policy = json.load(handle)

        result = check_autonomous_scope(
            [
                ".superpowers/sdd/review.diff",
                "nested/.superpowers/sdd/review.diff",
            ],
            policy["allowed_paths"],
            policy["denylist_paths"],
            policy.get("manual_confirm_paths", []),
        )

        self.assertFalse(result.allowed)
        self.assertEqual(
            result.denied_paths,
            [
                ".superpowers/sdd/review.diff",
                "nested/.superpowers/sdd/review.diff",
            ],
        )

    def test_expanded_policy_denies_root_level_artifact_paths(self) -> None:
        policy_path = Path(__file__).resolve().parents[2] / "docs" / "harness" / "loop-policies" / "autonomous-knowledge-ai-infra-expanded.json"
        with policy_path.open("r", encoding="utf-8") as handle:
            policy = json.load(handle)

        changed_paths = [
            "foo.log",
            "foo.pid",
            "dist/app.js",
            "build/app.js",
            "node_modules/pkg/index.js",
            ".pytest_cache/v/cache",
            "__pycache__/x.pyc",
            ".superpowers/sdd/review.diff",
        ]
        result = check_autonomous_scope(
            changed_paths,
            policy["allowed_paths"],
            policy["denylist_paths"],
            policy.get("manual_confirm_paths", []),
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.denied_paths, changed_paths)

    def test_expanded_policy_denies_nested_runtime_artifact_dirs(self) -> None:
        policy_path = Path(__file__).resolve().parents[2] / "docs" / "harness" / "loop-policies" / "autonomous-knowledge-ai-infra-expanded.json"
        with policy_path.open("r", encoding="utf-8") as handle:
            policy = json.load(handle)

        changed_paths = [
            "x/.codex/y",
            "x/.worktrees/y",
            "x/generated/y",
        ]
        result = check_autonomous_scope(
            changed_paths,
            policy["allowed_paths"],
            policy["denylist_paths"],
            policy.get("manual_confirm_paths", []),
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.denied_paths, changed_paths)

    def test_expanded_policy_denies_artifact_and_cache_dirs_under_allowed_paths(self) -> None:
        policy_path = Path(__file__).resolve().parents[2] / "docs" / "harness" / "loop-policies" / "autonomous-knowledge-ai-infra-expanded.json"
        with policy_path.open("r", encoding="utf-8") as handle:
            policy = json.load(handle)

        changed_paths = [
            "docs/harness/artifacts/x.json",
            "docs/harness/cache/x.json",
            "personal-wiki/domains/ai_infra/artifacts/x.json",
            "personal-wiki/domains/ai_infra/cache/x.json",
        ]
        result = check_autonomous_scope(
            changed_paths,
            policy["allowed_paths"],
            policy["denylist_paths"],
            policy.get("manual_confirm_paths", []),
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.denied_paths, changed_paths)

    def test_expanded_policy_restricts_unrelated_paths_and_allows_required_ranges(self) -> None:
        policy_path = Path(__file__).resolve().parents[2] / "docs" / "harness" / "loop-policies" / "autonomous-knowledge-ai-infra-expanded.json"
        with policy_path.open("r", encoding="utf-8") as handle:
            policy = json.load(handle)

        unrelated_result = check_autonomous_scope(
            ["random.txt", "tools/unrelated.py"],
            policy["allowed_paths"],
            policy["denylist_paths"],
            policy.get("manual_confirm_paths", []),
        )
        allowed_result = check_autonomous_scope(
            [
                "personal-wiki/domains/ai_infra/wiki/runtime.md",
                "personal-wiki/apps/crawler_workbench/backend/crawler_workbench/main.py",
                "personal-wiki/apps/crawler_workbench/frontend/src/App.tsx",
                "scripts/harness_loop_orchestrator.py",
                "docs/harness/planner-generator-evaluator-loop.md",
                "scripts/tests/test_harness_ai_infra_evidence.py",
                "tasks.json",
                "progress.md",
            ],
            policy["allowed_paths"],
            policy["denylist_paths"],
            policy.get("manual_confirm_paths", []),
        )

        self.assertFalse(unrelated_result.allowed)
        self.assertEqual(unrelated_result.denied_paths, ["random.txt", "tools/unrelated.py"])
        self.assertTrue(allowed_result.allowed, allowed_result.findings)

    def test_expanded_policy_denies_root_level_secret_token_and_credential_paths(self) -> None:
        policy_path = Path(__file__).resolve().parents[2] / "docs" / "harness" / "loop-policies" / "autonomous-knowledge-ai-infra-expanded.json"
        with policy_path.open("r", encoding="utf-8") as handle:
            policy = json.load(handle)

        changed_paths = [
            "secrets/key.txt",
            "secret.txt",
            "token.txt",
            "credential.txt",
        ]
        result = check_autonomous_scope(
            changed_paths,
            policy["allowed_paths"],
            policy["denylist_paths"],
            policy.get("manual_confirm_paths", []),
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.denied_paths, changed_paths)

    def test_expanded_policy_denies_secret_like_paths_case_insensitively(self) -> None:
        policy_path = Path(__file__).resolve().parents[2] / "docs" / "harness" / "loop-policies" / "autonomous-knowledge-ai-infra-expanded.json"
        with policy_path.open("r", encoding="utf-8") as handle:
            policy = json.load(handle)

        changed_paths = [
            ".ENV",
            "API_TOKEN.txt",
            "SecretConfig.md",
            "CREDENTIALS.md",
        ]
        result = check_autonomous_scope(
            changed_paths,
            policy["allowed_paths"],
            policy["denylist_paths"],
            policy.get("manual_confirm_paths", []),
        )

        self.assertFalse(result.allowed)
        self.assertEqual(result.denied_paths, changed_paths)

    def test_policy_patterns_fall_back_to_conservative_defaults_for_legacy_empty_lists(self) -> None:
        allowed, denied, manual = policy_patterns_for_run(
            {
                "allowed_paths": [],
                "denylist_paths": [],
                "manual_confirm_paths": [],
            },
            domain="ai_infra",
        )

        wiki_result = check_autonomous_scope(
            ["personal-wiki/domains/ai_infra/raw/source.md"],
            allowed,
            denied,
            manual,
        )
        scripts_result = check_autonomous_scope(
            ["scripts/harness_loop_orchestrator.py"],
            allowed,
            denied,
            manual,
        )
        env_result = check_autonomous_scope(
            [".env"],
            allowed,
            denied,
            manual,
        )

        self.assertTrue(wiki_result.allowed)
        self.assertFalse(scripts_result.allowed)
        self.assertEqual(scripts_result.manual_confirm_paths, ["scripts/harness_loop_orchestrator.py"])
        self.assertFalse(env_result.allowed)
        self.assertEqual(env_result.denied_paths, [".env"])

    def test_policy_patterns_honor_manual_only_overrides(self) -> None:
        allowed, denied, manual = policy_patterns_for_run(
            {
                "manual_confirm_paths": ["tasks.json"],
            },
            domain="ai_infra",
        )

        tasks_result = check_autonomous_scope(["tasks.json"], allowed, denied, manual)
        scripts_result = check_autonomous_scope(["scripts/harness_loop_orchestrator.py"], allowed, denied, manual)

        self.assertFalse(tasks_result.allowed)
        self.assertEqual(tasks_result.manual_confirm_paths, ["tasks.json"])
        self.assertFalse(scripts_result.allowed)
        self.assertEqual(scripts_result.denied_paths, ["scripts/harness_loop_orchestrator.py"])
        self.assertEqual(manual, ["tasks.json"])

        empty_allowed, empty_denied, empty_manual = policy_patterns_for_run(
            {
                "manual_confirm_paths": [],
            },
            domain="ai_infra",
        )

        empty_tasks_result = check_autonomous_scope(["tasks.json"], empty_allowed, empty_denied, empty_manual)

        self.assertFalse(empty_tasks_result.allowed)
        self.assertEqual(empty_tasks_result.denied_paths, ["tasks.json"])
        self.assertEqual(empty_manual, [])

    def test_supply_chain_check_requires_explanation_for_dependency_paths(self) -> None:
        result = check_supply_chain(["requirements.txt"], explanation="", verification=["pytest"])

        self.assertFalse(result.allowed)
        self.assertIn("missing dependency necessity", result.findings[0])

    def test_supply_chain_check_requires_verification_for_dependency_paths(self) -> None:
        result = check_supply_chain(
            ["pyproject.toml"],
            explanation="Needed for TOML parsing",
            verification=[],
        )

        self.assertFalse(result.allowed)
        self.assertIn("missing dependency verification", result.findings[0])

    def test_supply_chain_check_rejects_blank_verification_entries_for_dependency_paths(self) -> None:
        result = check_supply_chain(
            ["pyproject.toml"],
            explanation="Needed for TOML parsing",
            verification=["  "],
        )

        self.assertFalse(result.allowed)
        self.assertIn("missing dependency verification", result.findings[0])

    def test_supply_chain_check_accepts_dependency_paths_with_explanation_and_verification(self) -> None:
        result = check_supply_chain(
            ["pyproject.toml"],
            explanation="Needed for TOML parsing",
            verification=["python3 -m unittest scripts.tests.test_harness_loop_autonomous -v"],
        )

        self.assertTrue(result.allowed)
        self.assertEqual(result.findings, [])

    def test_load_or_create_and_write_loop_state_round_trips_domain_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
            state = load_or_create_loop_state(repo_root, "ai_infra", "Expand wiki")
            state["candidate_backlog"].append(
                {
                    "id": "candidate-1",
                    "title": "Candidate",
                    "source": "planner",
                    "status": "pending",
                    "updated_at": state["last_scan_at"],
                    "evidence": ["planner proposed source"],
                }
            )

            path = write_loop_state(repo_root, "ai_infra", state)
            loaded = load_or_create_loop_state(repo_root, "ai_infra", "Ignored")

            self.assertEqual(path, repo_root / "personal-wiki" / "domains" / "ai_infra" / "loop-state.json")
            self.assertEqual(loaded["candidate_backlog"][0]["id"], "candidate-1")

    def test_load_or_create_loop_state_rejects_unsafe_domain_path_segments(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)

            with self.assertRaisesRegex(ValueError, "domain"):
                load_or_create_loop_state(repo_root, "../outside", "Expand wiki")

    def test_run_git_commit_commits_only_requested_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
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
            tracked = repo_root / "tracked.md"
            other = repo_root / "other.md"
            tracked.write_text("tracked\n", encoding="utf-8")
            other.write_text("other\n", encoding="utf-8")

            commit_sha = run_git_commit(repo_root, ["tracked.md"], "test: commit tracked")

            self.assertRegex(commit_sha, r"^[0-9a-f]{40}$")
            staged_status = subprocess.run(
                ["git", "status", "--short"],
                cwd=repo_root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertIn("?? other.md", staged_status.stdout)
            self.assertNotIn("tracked.md", staged_status.stdout)

    def test_run_git_commit_does_not_commit_pre_staged_unrelated_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
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
            tracked = repo_root / "tracked.md"
            staged_other = repo_root / "staged-other.md"
            tracked.write_text("tracked\n", encoding="utf-8")
            staged_other.write_text("staged other\n", encoding="utf-8")
            subprocess.run(
                ["git", "add", "--", "staged-other.md"],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            run_git_commit(repo_root, ["tracked.md"], "test: commit tracked")

            committed_files = subprocess.run(
                ["git", "show", "--name-only", "--format=", "HEAD"],
                cwd=repo_root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(committed_files.stdout.splitlines(), ["tracked.md"])
            status = subprocess.run(
                ["git", "status", "--short"],
                cwd=repo_root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertIn("A  staged-other.md", status.stdout)

    def test_run_git_commit_with_explicit_file_pathspec_does_not_commit_unrequested_dirty_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
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
            raw_dir = repo_root / "personal-wiki" / "domains" / "ai_infra" / "raw"
            raw_dir.mkdir(parents=True)
            requested = raw_dir / "requested.md"
            preexisting = raw_dir / "preexisting.md"
            requested.write_text("requested\n", encoding="utf-8")
            preexisting.write_text("preexisting\n", encoding="utf-8")

            commit_sha = run_git_commit(
                repo_root,
                ["personal-wiki/domains/ai_infra/raw/requested.md"],
                "test: commit requested raw evidence",
            )

            self.assertRegex(commit_sha, r"^[0-9a-f]{40}$")
            committed_files = subprocess.run(
                ["git", "show", "--name-only", "--format=", "HEAD"],
                cwd=repo_root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(
                committed_files.stdout.splitlines(),
                ["personal-wiki/domains/ai_infra/raw/requested.md"],
            )
            status = subprocess.run(
                ["git", "status", "--short"],
                cwd=repo_root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertIn("?? personal-wiki/domains/ai_infra/raw/preexisting.md", status.stdout)

    def test_run_git_commit_rejects_git_pathspec_magic(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
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
            (repo_root / "one.md").write_text("one\n", encoding="utf-8")
            (repo_root / "two.md").write_text("two\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "unsafe commit pathspec"):
                run_git_commit(repo_root, [":(glob)**/*.md"], "test: reject pathspec magic")

    def test_run_git_commit_rejects_git_wildcard_pathspecs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
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
            (repo_root / "one.md").write_text("one\n", encoding="utf-8")
            (repo_root / "two.md").write_text("two\n", encoding="utf-8")

            for pathspec in ("*.md", "**/*.md", "?.md", "[ot]ne.md"):
                with self.subTest(pathspec=pathspec):
                    with self.assertRaisesRegex(ValueError, "unsafe commit pathspec"):
                        run_git_commit(repo_root, [pathspec], "test: reject wildcard pathspec")

    def test_run_git_commit_with_directory_pathspec_commits_single_dirty_file_containing_space(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
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
            raw_dir = repo_root / "personal-wiki" / "domains" / "ai_infra" / "raw"
            raw_dir.mkdir(parents=True)
            requested = raw_dir / "requested evidence.md"
            requested.write_text("requested\n", encoding="utf-8")

            commit_sha = run_git_commit(
                repo_root,
                ["personal-wiki/domains/ai_infra/raw"],
                "test: commit requested raw evidence",
            )

            self.assertRegex(commit_sha, r"^[0-9a-f]{40}$")
            committed_files = subprocess.run(
                ["git", "show", "--name-only", "--format=", "HEAD"],
                cwd=repo_root,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            self.assertEqual(
                committed_files.stdout.splitlines(),
                ["personal-wiki/domains/ai_infra/raw/requested evidence.md"],
            )

    def test_run_git_commit_rejects_directory_pathspec_that_matches_rename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
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
            raw_dir = repo_root / "personal-wiki" / "domains" / "ai_infra" / "raw"
            raw_dir.mkdir(parents=True)
            original = raw_dir / "old.md"
            renamed = raw_dir / "renamed evidence.md"
            original.write_text("original\n", encoding="utf-8")
            subprocess.run(["git", "add", "--", "."], cwd=repo_root, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(
                ["git", "commit", "-m", "test: seed"],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            subprocess.run(
                ["git", "mv", "--", str(original.relative_to(repo_root)), str(renamed.relative_to(repo_root))],
                cwd=repo_root,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            with self.assertRaisesRegex(ValueError, "rename"):
                run_git_commit(
                    repo_root,
                    ["personal-wiki/domains/ai_infra/raw"],
                    "test: reject directory rename expansion",
                )

    def test_run_git_commit_rejects_directory_pathspec_that_matches_multiple_dirty_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            repo_root = Path(tmp)
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
            raw_dir = repo_root / "personal-wiki" / "domains" / "ai_infra" / "raw"
            raw_dir.mkdir(parents=True)
            (raw_dir / "requested.md").write_text("requested\n", encoding="utf-8")
            (raw_dir / "preexisting.md").write_text("preexisting\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "directory pathspec"):
                run_git_commit(
                    repo_root,
                    ["personal-wiki/domains/ai_infra/raw"],
                    "test: unsafe directory pathspec",
                )


if __name__ == "__main__":
    unittest.main()
