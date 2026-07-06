import subprocess
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

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
                "source": "planner",
                "status": "complete",
                "updated_at": state["last_scan_at"],
                "evidence": ["no candidates"],
            }
        ]

        self.assertTrue(decide_no_action(state).no_action)

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

        decision = decide_no_action(state)

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
                "source": "planner",
                "status": "complete",
                "updated_at": state["last_scan_at"],
                "evidence": ["no candidates"],
            }
        ]

        decision = decide_no_action(state, now=now)

        self.assertFalse(decision.no_action)
        self.assertIn("last_scan_at is stale", decision.reasons)

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
