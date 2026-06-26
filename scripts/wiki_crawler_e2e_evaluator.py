#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


TASK_ID = "wiki-crawler-e2e-eval-01"
SCENARIO_ID = "wiki-crawler-e2e-user-flow"
DOMAIN = "ai_infra"
SOURCE_ID = "harness-e2e-local-source"


@dataclass(frozen=True)
class CommandEvidence:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str

    def as_dict(self) -> dict[str, object]:
        return {
            "command": self.command,
            "returncode": self.returncode,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


class LocalHarnessFetcher:
    def fetch(self, profile: dict[str, object]) -> list[object]:
        from crawler_workbench.fetchers.base import FetchResult

        return [
            FetchResult(
                canonical_url=str(profile["url"]),
                title="Harness NCCL crawler smoke",
                content=(
                    "# Harness NCCL crawler smoke\n\n"
                    "NCCL collective communication and GPUDirect RDMA are tracked "
                    "by this deterministic local source for evaluator coverage.\n"
                ),
                content_type="text/markdown",
                metadata={"fixture": True, "scenario_id": SCENARIO_ID},
                etag="harness-e2e",
                last_modified="Sat, 27 Jun 2026 00:00:00 GMT",
            )
        ]

    def close(self) -> None:
        return None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)

    source_repo = Path(args.repo_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        evidence = run_e2e(source_repo, output_dir)
        result = _pass_result(evidence)
        _write_outputs(output_dir, result, evidence)
        print(json.dumps({"status": "pass", "output_dir": str(output_dir)}, ensure_ascii=False))
        return 0
    except Exception as exc:
        evidence = {"error": str(exc), "output_dir": str(output_dir)}
        result = _blocked_result(str(exc))
        _write_outputs(output_dir, result, evidence)
        print(json.dumps({"status": "blocked", "error": str(exc), "output_dir": str(output_dir)}, ensure_ascii=False), file=sys.stderr)
        return 1


def run_e2e(source_repo: Path, output_dir: Path) -> dict[str, object]:
    backend_path = source_repo / "personal-wiki" / "apps" / "crawler_workbench" / "backend"
    if not backend_path.exists():
        raise FileNotFoundError(f"missing crawler backend: {backend_path}")
    sys.path.insert(0, str(backend_path))

    from crawler_workbench.db import open_db
    from crawler_workbench.fetch_service import run_source_once
    from crawler_workbench.ingest import approve_task, list_queue, run_approved_task
    from crawler_workbench.main import create_app
    from crawler_workbench.settings import Settings

    state_dir = output_dir.parent / "state"
    fixture_repo = _prepare_fixture_repo(source_repo, output_dir, state_dir)
    _write_sources_yaml(state_dir / "sources.yaml")

    previous_scheduler = os.environ.get("PW_WORKBENCH_DISABLE_SCHEDULER")
    os.environ["PW_WORKBENCH_DISABLE_SCHEDULER"] = "1"
    try:
        settings = Settings(repo_root=fixture_repo, state_dir=state_dir, bind_host="127.0.0.1")
        app = create_app(settings)
        app.state.initialize_database(app)

        with open_db(settings.database_path) as db:
            fetch_result = run_source_once(settings, db, SOURCE_ID, fetcher=LocalHarnessFetcher())
            queue_before = list_queue(db)
            if not queue_before:
                raise RuntimeError("crawler run did not create an ingest task")
            task_id = int(queue_before[0]["id"])
            approve_task(settings, db, task_id)
            ingest_task = run_approved_task(
                settings,
                db,
                task_id,
                auto_commit_enabled=False,
                codex_runner=_fake_codex_runner,
            )
            queue_after = list_queue(db)
    finally:
        if previous_scheduler is None:
            os.environ.pop("PW_WORKBENCH_DISABLE_SCHEDULER", None)
        else:
            os.environ["PW_WORKBENCH_DISABLE_SCHEDULER"] = previous_scheduler

    domain_validate = _run_command(
        [
            "python",
            "personal-wiki/tools/wiki_cli/cli.py",
            "--root",
            "personal-wiki",
            "validate",
            "--domain",
            DOMAIN,
        ],
        cwd=fixture_repo,
    )
    full_validate = _run_command(
        ["python", "personal-wiki/tools/wiki_cli/cli.py", "--root", "personal-wiki", "validate"],
        cwd=fixture_repo,
    )

    raw_paths = [
        str(path.relative_to(fixture_repo).as_posix())
        for path in sorted((fixture_repo / "personal-wiki" / "domains" / DOMAIN / "raw" / "crawler" / SOURCE_ID).glob("*.md"))
    ]
    wiki_pages = [
        str(path.relative_to(fixture_repo).as_posix())
        for path in sorted((fixture_repo / "personal-wiki" / "domains" / DOMAIN / "wiki").rglob("*.md"))
        if path.name != "index.md"
    ]
    required_files = [
        fixture_repo / "personal-wiki" / "domains" / DOMAIN / "wiki" / "index.md",
        fixture_repo / "personal-wiki" / "domains" / DOMAIN / "wiki" / "backlinks.json",
    ]
    missing_required = [str(path.relative_to(fixture_repo)) for path in required_files if not path.exists()]

    if fetch_result["changed_count"] < 1:
        raise RuntimeError(f"expected one changed source item, got {fetch_result}")
    if ingest_task.get("status") != "succeeded":
        raise RuntimeError(f"ingest task did not succeed: {ingest_task}")
    if not raw_paths:
        raise RuntimeError("expected raw crawler evidence file")
    if not wiki_pages:
        raise RuntimeError("expected at least one curated wiki page")
    if missing_required:
        raise RuntimeError(f"missing rebuilt wiki artifacts: {missing_required}")
    if domain_validate.returncode != 0:
        raise RuntimeError(f"domain validate failed: {domain_validate.stderr or domain_validate.stdout}")
    if full_validate.returncode != 0:
        raise RuntimeError(f"full validate failed: {full_validate.stderr or full_validate.stdout}")

    return {
        "task_id": TASK_ID,
        "scenario_id": SCENARIO_ID,
        "fixture_repo": str(fixture_repo),
        "state_dir": str(state_dir),
        "fetch_result": fetch_result,
        "queue_before": queue_before,
        "queue_after": queue_after,
        "ingest_task": ingest_task,
        "raw_paths": raw_paths,
        "wiki_pages": wiki_pages,
        "domain_validate": domain_validate.as_dict(),
        "full_validate": full_validate.as_dict(),
    }


def _prepare_fixture_repo(source_repo: Path, output_dir: Path, state_dir: Path) -> Path:
    fixture_repo = output_dir.parent / "worktree"
    if fixture_repo.exists():
        shutil.rmtree(fixture_repo)
    if state_dir.exists():
        shutil.rmtree(state_dir)
    personal_wiki = fixture_repo / "personal-wiki"
    shutil.copytree(source_repo / "personal-wiki" / "tools", personal_wiki / "tools")
    shutil.copytree(source_repo / "personal-wiki" / "templates", personal_wiki / "templates")
    shutil.copytree(source_repo / "personal-wiki" / "schemas", personal_wiki / "schemas")
    (personal_wiki / "WIKI.md").write_text("# Harness Personal Wiki\n", encoding="utf-8")
    (personal_wiki / "README.md").write_text("# Harness Personal Wiki\n", encoding="utf-8")
    (personal_wiki / "global" / "wiki").mkdir(parents=True)
    (personal_wiki / "domains").mkdir(parents=True)
    _run_command(["python", "personal-wiki/tools/wiki_cli/cli.py", "--root", "personal-wiki", "init-domain", DOMAIN], cwd=fixture_repo, check=True)
    _write_clean_domain_files(personal_wiki / "domains" / DOMAIN)
    _run_command(["git", "init"], cwd=fixture_repo, check=True)
    _run_command(["git", "config", "user.email", "harness@example.invalid"], cwd=fixture_repo, check=True)
    _run_command(["git", "config", "user.name", "Harness Evaluator"], cwd=fixture_repo, check=True)
    _run_command(["git", "add", "personal-wiki"], cwd=fixture_repo, check=True)
    _run_command(["git", "commit", "-m", "fixture baseline"], cwd=fixture_repo, check=True)
    return fixture_repo


def _write_clean_domain_files(domain_root: Path) -> None:
    (domain_root / "DOMAIN.md").write_text(
        "# ai_infra\n\n"
        "## Boundary\n\n"
        "Harness evaluator fixture for AI infrastructure crawler validation.\n",
        encoding="utf-8",
    )
    (domain_root / "ingest.md").write_text("# Ingest Log\n\n", encoding="utf-8")
    index_path = domain_root / "wiki" / "index.md"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        "---\n"
        "type: Index\n"
        "title: ai_infra Index\n"
        "description: Generated index for ai_infra.\n"
        "domain: ai_infra\n"
        "---\n"
        "# ai_infra Index\n",
        encoding="utf-8",
    )


def _write_sources_yaml(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "sources:\n"
        f"- id: {SOURCE_ID}\n"
        "  name: Harness E2E Local Source\n"
        "  type: web\n"
        f"  target_domain: {DOMAIN}\n"
        "  url: https://example.invalid/harness/wiki-crawler-e2e\n"
        "  trust_level: trusted\n"
        "  schedule: manual\n"
        "  auto_ingest: false\n"
        "  auth_required: false\n"
        "  baseline_on_first_run: false\n"
        "  topic: NCCL crawler evaluator fixture\n",
        encoding="utf-8",
    )


def _fake_codex_runner(settings: object, prompt: str) -> subprocess.CompletedProcess[str]:
    repo_root = Path(getattr(settings, "repo_root"))
    raw_pages = sorted((repo_root / "personal-wiki" / "domains" / DOMAIN / "raw" / "crawler" / SOURCE_ID).glob("*.md"))
    if not raw_pages:
        return subprocess.CompletedProcess(["fake-codex"], 1, "", "missing raw page")
    raw_path = raw_pages[-1]
    page_path = repo_root / "personal-wiki" / "domains" / DOMAIN / "wiki" / "references" / "harness-nccl-crawler-smoke.md"
    source_ref = os.path.relpath(raw_path, start=page_path.parent)
    page_path.parent.mkdir(parents=True, exist_ok=True)
    page_path.write_text(
        "---\n"
        "type: Reference\n"
        "title: Harness NCCL crawler smoke\n"
        "description: Deterministic E2E page generated by the wiki crawler evaluator.\n"
        "domain: ai_infra\n"
        "status: draft\n"
        "tags: [harness, crawler, nccl]\n"
        "source_refs:\n"
        f"  - {Path(source_ref).as_posix()}\n"
        "updated: 2026-06-27\n"
        "aliases: []\n"
        "related: []\n"
        "---\n\n"
        "# Summary\n\n"
        "The crawler captured a deterministic NCCL source and preserved it as raw evidence.\n\n"
        "# Evidence\n\n"
        f"- Raw source: [{raw_path.name}]({Path(source_ref).as_posix()})\n",
        encoding="utf-8",
    )
    return subprocess.CompletedProcess(["fake-codex"], 0, f"wrote {page_path}\n", "")


def _run_command(command: list[str], cwd: Path, check: bool = False) -> CommandEvidence:
    result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, check=False)
    evidence = CommandEvidence(command=command, returncode=result.returncode, stdout=result.stdout, stderr=result.stderr)
    if check and result.returncode != 0:
        raise RuntimeError(f"command failed: {' '.join(command)}\n{result.stdout}{result.stderr}")
    return evidence


def _pass_result(evidence: dict[str, object]) -> dict[str, object]:
    evidence_paths = [
        "evidence.json",
        "summary.md",
        *[str(path) for path in evidence.get("raw_paths", [])],
        *[str(path) for path in evidence.get("wiki_pages", [])],
    ]
    return {
        "status": "pass",
        "gate": "task",
        "task_id": TASK_ID,
        "final_bundle_id": "",
        "attempt": 1,
        "summary": "wiki crawler E2E scenario passed",
        "findings": [],
        "scenario_results": [
            {
                "scenario_id": SCENARIO_ID,
                "status": "pass",
                "evidence": evidence_paths,
                "notes": "fetch, approval, ingest, index, backlinks, and validation completed in an isolated fixture repo",
            }
        ],
        "rerun_commands": [
            "python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/wiki-crawler-e2e-eval-01"
        ],
        "environment_checks": [
            {"name": "fixture_repo", "status": "pass", "detail": str(evidence.get("fixture_repo", ""))},
            {"name": "domain_validate", "status": "pass", "detail": "returncode=0"},
            {"name": "full_validate", "status": "pass", "detail": "returncode=0"},
        ],
        "verdict_reason": "All required wiki crawler E2E outcomes were observed.",
        "next_action": "proceed_to_user_acceptance",
    }


def _blocked_result(reason: str) -> dict[str, object]:
    return {
        "status": "blocked",
        "gate": "task",
        "task_id": TASK_ID,
        "final_bundle_id": "",
        "attempt": 1,
        "summary": reason,
        "findings": [
            {
                "id": "WIKI-CRAWLER-E2E-BLOCKED",
                "severity": "major",
                "category": "environment_or_workflow_blocked",
                "evidence": ["evidence.json"],
                "recommended_action": "Review the helper output and rerun after fixing the blocker.",
            }
        ],
        "scenario_results": [
            {
                "scenario_id": SCENARIO_ID,
                "status": "blocked",
                "evidence": ["evidence.json"],
                "notes": reason,
            }
        ],
        "rerun_commands": [
            "python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/wiki-crawler-e2e-eval-01"
        ],
        "environment_checks": [],
        "verdict_reason": reason,
        "next_action": "repair_and_reevaluate",
    }


def _write_outputs(output_dir: Path, result: dict[str, object], evidence: dict[str, object]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "result.json").write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output_dir / "evidence.json").write_text(json.dumps(evidence, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    scenario = result["scenario_results"][0]  # type: ignore[index]
    (output_dir / "summary.md").write_text(
        "# Wiki Crawler E2E Evaluator Summary\n\n"
        f"- status: {result['status']}\n"
        f"- task_id: {TASK_ID}\n"
        f"- scenario_id: {SCENARIO_ID}\n"
        f"- scenario_status: {scenario['status']}\n"
        f"- verdict: {result['verdict_reason']}\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    raise SystemExit(main())
