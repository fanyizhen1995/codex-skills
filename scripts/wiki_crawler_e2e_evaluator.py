#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import socket
import subprocess
import sys
import threading
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Sequence


TASK_ID = "wiki-crawler-e2e-eval-01"
SCENARIO_ID = "wiki-crawler-e2e-user-flow"
SOURCE_SUBSCRIPTIONS_SCENARIO_ID = "source-subscriptions-user-flow"
DOMAIN_CHANNELS_SCENARIO_ID = "domain-channels-live-user-flow"
DOMAIN = "ai_infra"
SOURCE_ID = "harness-e2e-local-source"
DOMAIN_CHANNEL_ID = "domain-channel-e2e-api"
DOMAIN_CHANNEL_SOURCE_ID = "domain-channel-e2e-api-source"
DOMAIN_CHANNEL_SECRET = "domain-channel-e2e-synthetic-token-7c0f6a"
DOMAIN_CHANNEL_REPLACEMENT_SECRET = "domain-channel-e2e-replacement-token-91b2d4"


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


class EvaluatorRunError(RuntimeError):
    def __init__(self, message: str, evidence: dict[str, object]) -> None:
        super().__init__(message)
        self.evidence = evidence


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
        if isinstance(exc, EvaluatorRunError):
            evidence = exc.evidence
            evidence["error"] = str(exc)
            evidence["output_dir"] = str(output_dir)
        else:
            evidence = {"error": str(exc), "output_dir": str(output_dir)}
        result = _blocked_result(str(exc), evidence)
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
        domain_channel_api = _run_domain_channel_api_flow(settings)
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
    source_subscription_ui = _run_source_subscription_ui_flow(source_repo, output_dir)

    raw_paths = [
        _relative_evidence_path(output_dir, path)
        for path in sorted((fixture_repo / "personal-wiki" / "domains" / DOMAIN / "raw" / "crawler" / SOURCE_ID).glob("*.md"))
    ]
    wiki_pages = [
        _relative_evidence_path(output_dir, path)
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
    if source_subscription_ui["playwright"]["returncode"] != 0:
        failure_evidence = {
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
            "source_subscription_ui": source_subscription_ui,
        }
        raise EvaluatorRunError(
            "source subscription UI flow failed: "
            f"{source_subscription_ui['playwright']['stderr'] or source_subscription_ui['playwright']['stdout']}",
            failure_evidence,
        )
    domain_channel_ui = _run_domain_channel_ui_flow(source_repo, output_dir)
    if domain_channel_ui["playwright"]["returncode"] != 0:
        failure_evidence = {
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
            "source_subscription_ui": source_subscription_ui,
            "domain_channel_api": domain_channel_api,
            "domain_channel_ui": domain_channel_ui,
        }
        raise EvaluatorRunError(
            "domain channel UI flow failed: "
            f"{domain_channel_ui['playwright']['stderr'] or domain_channel_ui['playwright']['stdout']}",
            failure_evidence,
        )

    secret_plaintext_scan = _scan_for_forbidden_plaintext(
        output_dir,
        [DOMAIN_CHANNEL_SECRET, DOMAIN_CHANNEL_REPLACEMENT_SECRET],
    )
    if not secret_plaintext_scan["passed"]:
        failure_evidence = {
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
            "source_subscription_ui": source_subscription_ui,
            "domain_channel_api": domain_channel_api,
            "domain_channel_ui": domain_channel_ui,
            "secret_plaintext_scan": secret_plaintext_scan,
        }
        raise EvaluatorRunError("synthetic channel secret leaked into retained artifacts", failure_evidence)

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
        "source_subscription_ui": source_subscription_ui,
        "domain_channel_api": domain_channel_api,
        "domain_channel_ui": domain_channel_ui,
        "secret_plaintext_scan": secret_plaintext_scan,
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


class _ProbeHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/probe":
            self.send_response(404)
            self.end_headers()
            return
        self.server.seen_authorization = self.headers.get("Authorization", "")  # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"domain channel probe ok")

    def log_message(self, format: str, *args: object) -> None:
        return


class LocalProbeServer:
    def __enter__(self) -> "LocalProbeServer":
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _ProbeHandler)
        self._server.seen_authorization = ""  # type: ignore[attr-defined]
        self.url = f"http://127.0.0.1:{self._server.server_port}/probe"
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=5)

    @property
    def saw_authorization_header(self) -> bool:
        return bool(getattr(self._server, "seen_authorization", ""))


def _run_domain_channel_api_flow(settings: object) -> dict[str, object]:
    from fastapi.testclient import TestClient

    from crawler_workbench.main import create_app

    app = create_app(settings)
    app.state.initialize_database(app)
    client = TestClient(app)

    with LocalProbeServer() as probe:
        channel_response = client.post(
            "/api/channels",
            json={
                "id": DOMAIN_CHANNEL_ID,
                "target_domain": DOMAIN,
                "name": "Domain Channel E2E API",
                "base_url": "https://api.domain-channel-e2e.example",
                "probe_url": probe.url,
                "kind": "api",
                "connector": "generic",
                "trust_level": "trusted",
                "enabled": True,
                "auth_required": True,
                "auth_mode": "token",
                "notes": "Synthetic API channel for evaluator coverage",
            },
        )
        channel_response.raise_for_status()

        secret_response = client.post(
            f"/api/channels/{DOMAIN_CHANNEL_ID}/secret",
            json={"secret_kind": "synthetic_token", "secret": DOMAIN_CHANNEL_SECRET},
        )
        secret_response.raise_for_status()

        probe_response = client.post(f"/api/channels/{DOMAIN_CHANNEL_ID}/probe")
        probe_response.raise_for_status()
        probe_payload = probe_response.json()

    source_response = client.post(
        "/api/sources",
        json={
            "id": DOMAIN_CHANNEL_SOURCE_ID,
            "name": "Domain Channel E2E API source",
            "type": "web",
            "fetcher_type": "api_endpoint",
            "target_domain": DOMAIN,
            "url": "https://api.domain-channel-e2e.example/nccl",
            "channel_id": DOMAIN_CHANNEL_ID,
            "trust_level": "trusted",
            "schedule": "manual",
            "auto_ingest": False,
            "auth_required": False,
            "baseline_on_first_run": False,
            "run_policy": "scheduled",
            "topic": "Domain channel evaluator API source",
            "enabled": True,
        },
    )
    source_response.raise_for_status()

    channels_response = client.get("/api/channels", params={"domain": DOMAIN})
    channels_response.raise_for_status()
    sources_response = client.get("/api/sources", params={"domain": DOMAIN, "channel_id": DOMAIN_CHANNEL_ID})
    sources_response.raise_for_status()
    history_response = client.get(f"/api/channels/{DOMAIN_CHANNEL_ID}/probe-runs")
    history_response.raise_for_status()

    secret_payload = secret_response.json()
    channel_payload = next(item for item in channels_response.json() if item["id"] == DOMAIN_CHANNEL_ID)
    source_payload = source_response.json()
    history_payload = history_response.json()
    return {
        "channel_id": DOMAIN_CHANNEL_ID,
        "source_id": DOMAIN_CHANNEL_SOURCE_ID,
        "channel_auth_state": channel_payload["auth_state"],
        "last_probe_status": channel_payload["last_probe_status"],
        "secret_configured": bool(secret_payload["secret_configured"]),
        "probe_status": probe_payload["status"],
        "probe_history_count": len(history_payload),
        "source_channel_id": source_payload["channel_id"],
        "source_fetcher_type": source_payload["fetcher_type"],
        "listed_sources_for_channel": len(sources_response.json()),
        "probe_saw_authorization_header": probe.saw_authorization_header,
    }


def _run_source_subscription_ui_flow(source_repo: Path, output_dir: Path) -> dict[str, object]:
    frontend_dir = source_repo / "personal-wiki" / "apps" / "crawler_workbench" / "frontend"
    if not frontend_dir.exists():
        raise FileNotFoundError(f"missing crawler frontend: {frontend_dir}")
    install_evidence = _ensure_frontend_dependencies(frontend_dir)

    ui_output_dir = output_dir / "source-subscriptions-ui"
    report_dir = ui_output_dir / "playwright-report"
    json_report = ui_output_dir / "source-subscriptions-live.json"
    ui_output_dir.mkdir(parents=True, exist_ok=True)

    env = _source_subscription_ui_env(
        output_dir,
        base_env=os.environ,
        report_dir=report_dir,
        json_report=json_report,
    )

    result = subprocess.run(
        ["npm", "run", "test:ui:live"],
        cwd=frontend_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    return {
        "playwright": CommandEvidence(
            command=["npm", "run", "test:ui:live"],
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
        ).as_dict(),
        "dependency_install": install_evidence,
        "report_dir": _relative_evidence_path(output_dir, report_dir),
        "json_report": _relative_evidence_path(output_dir, json_report),
    }


def _run_domain_channel_ui_flow(source_repo: Path, output_dir: Path) -> dict[str, object]:
    frontend_dir = source_repo / "personal-wiki" / "apps" / "crawler_workbench" / "frontend"
    if not frontend_dir.exists():
        raise FileNotFoundError(f"missing crawler frontend: {frontend_dir}")
    install_evidence = _ensure_frontend_dependencies(frontend_dir)

    ui_output_dir = output_dir / "domain-channels-ui"
    report_dir = ui_output_dir / "playwright-report"
    json_report = ui_output_dir / "domain-channels-live.json"
    ui_output_dir.mkdir(parents=True, exist_ok=True)

    env = _domain_channel_ui_env(
        output_dir,
        base_env=os.environ,
        report_dir=report_dir,
        json_report=json_report,
    )

    result = subprocess.run(
        ["npm", "run", "test:ui:live"],
        cwd=frontend_dir,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    redactions = _redact_forbidden_plaintext_in_tree(ui_output_dir, [DOMAIN_CHANNEL_REPLACEMENT_SECRET])
    return {
        "playwright": CommandEvidence(
            command=["npm", "run", "test:ui:live"],
            returncode=result.returncode,
            stdout=_redact_known_plaintext(result.stdout),
            stderr=_redact_known_plaintext(result.stderr),
        ).as_dict(),
        "dependency_install": install_evidence,
        "redacted_artifacts": redactions,
        "backend_url": env["PW_WORKBENCH_E2E_BACKEND_URL"],
        "frontend_port": env["PW_WORKBENCH_E2E_FRONTEND_PORT"],
        "report_dir": _relative_evidence_path(output_dir, report_dir),
        "json_report": _relative_evidence_path(output_dir, json_report),
    }


def _ensure_frontend_dependencies(frontend_dir: Path) -> dict[str, object]:
    playwright_bin = frontend_dir / "node_modules" / ".bin" / "playwright"
    if playwright_bin.exists():
        return {"command": [], "returncode": 0, "stdout": "node_modules present", "stderr": ""}
    ci_result = subprocess.run(
        ["npm", "ci"],
        cwd=frontend_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if ci_result.returncode == 0:
        return CommandEvidence(
            command=["npm", "ci"],
            returncode=ci_result.returncode,
            stdout=ci_result.stdout[-4000:],
            stderr=ci_result.stderr[-4000:],
        ).as_dict()

    fallback_result = subprocess.run(
        ["npm", "install", "--package-lock=false"],
        cwd=frontend_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if fallback_result.returncode != 0:
        raise EvaluatorRunError(
            "frontend dependency install failed",
            {
                "dependency_install": {
                    "primary": CommandEvidence(
                        command=["npm", "ci"],
                        returncode=ci_result.returncode,
                        stdout=ci_result.stdout,
                        stderr=ci_result.stderr,
                    ).as_dict(),
                    "fallback": CommandEvidence(
                        command=["npm", "install", "--package-lock=false"],
                        returncode=fallback_result.returncode,
                        stdout=fallback_result.stdout,
                        stderr=fallback_result.stderr,
                    ).as_dict(),
                }
            },
        )
    return {
        "command": ["npm", "install", "--package-lock=false"],
        "returncode": fallback_result.returncode,
        "stdout": fallback_result.stdout[-4000:],
        "stderr": fallback_result.stderr[-4000:],
        "fallback_reason": ci_result.stderr[-1000:],
    }


def _source_subscription_ui_env(
    output_dir: Path,
    base_env: dict[str, str] | os._Environ[str],
    report_dir: Path | None = None,
    json_report: Path | None = None,
) -> dict[str, str]:
    return _live_ui_env(
        output_dir,
        base_env=base_env,
        report_dir=report_dir,
        json_report=json_report,
    )


def _domain_channel_ui_env(
    output_dir: Path,
    base_env: dict[str, str] | os._Environ[str],
    report_dir: Path | None = None,
    json_report: Path | None = None,
) -> dict[str, str]:
    env = _live_ui_env(
        output_dir,
        base_env=base_env,
        report_dir=report_dir or (output_dir / "domain-channels-ui" / "playwright-report"),
        json_report=json_report or (output_dir / "domain-channels-ui" / "domain-channels-live.json"),
    )
    env["PW_WORKBENCH_E2E_DOMAIN_CHANNELS"] = "1"
    env["PW_WORKBENCH_E2E_DOMAIN_CHANNEL_SECRET"] = DOMAIN_CHANNEL_REPLACEMENT_SECRET
    return env


def _live_ui_env(
    output_dir: Path,
    base_env: dict[str, str] | os._Environ[str],
    report_dir: Path | None = None,
    json_report: Path | None = None,
) -> dict[str, str]:
    env = dict(base_env)
    if "PW_WORKBENCH_E2E_BACKEND_PORT" not in env:
        env["PW_WORKBENCH_E2E_BACKEND_PORT"] = str(_find_free_port())
    if "PW_WORKBENCH_E2E_FRONTEND_PORT" not in env:
        env["PW_WORKBENCH_E2E_FRONTEND_PORT"] = str(_find_free_port(excluding={int(env["PW_WORKBENCH_E2E_BACKEND_PORT"])}))
    env["PW_WORKBENCH_E2E_BACKEND_URL"] = f"http://127.0.0.1:{env['PW_WORKBENCH_E2E_BACKEND_PORT']}"
    env["PW_WORKBENCH_E2E_REPORT_DIR"] = str(report_dir or (output_dir / "source-subscriptions-ui" / "playwright-report"))
    env["PW_WORKBENCH_E2E_JSON_REPORT"] = str(json_report or (output_dir / "source-subscriptions-ui" / "source-subscriptions-live.json"))
    return env


def _find_free_port(excluding: set[int] | None = None) -> int:
    excluded = excluding or set()
    for _ in range(20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            port = int(sock.getsockname()[1])
        if port not in excluded:
            return port
    raise RuntimeError("could not allocate an unused local port")


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


def _ui_evidence_paths(evidence: dict[str, object]) -> list[str]:
    ui_evidence_paths: list[str] = []
    for evidence_key in ("source_subscription_ui", "domain_channel_ui"):
        ui_payload = evidence.get(evidence_key, {})
        if isinstance(ui_payload, dict):
            for key in ("json_report", "report_dir"):
                value = ui_payload.get(key)
                if isinstance(value, str) and value:
                    ui_evidence_paths.append(value)
    return ui_evidence_paths


def _specific_ui_evidence_paths(evidence: dict[str, object], evidence_key: str) -> list[str]:
    ui_payload = evidence.get(evidence_key, {})
    paths: list[str] = []
    if isinstance(ui_payload, dict):
        for key in ("json_report", "report_dir"):
            value = ui_payload.get(key)
            if isinstance(value, str) and value:
                paths.append(value)
    return paths


def _redact_known_plaintext(value: str) -> str:
    redacted = value
    for secret in (DOMAIN_CHANNEL_SECRET, DOMAIN_CHANNEL_REPLACEMENT_SECRET):
        redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


def _redact_forbidden_plaintext_in_tree(root: Path, forbidden_values: Sequence[str]) -> list[str]:
    redacted_paths: list[str] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if b"\0" in raw[:4096]:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        redacted = text
        for value in forbidden_values:
            if value:
                redacted = redacted.replace(value, "[REDACTED]")
        if redacted == text:
            continue
        path.write_text(redacted, encoding="utf-8")
        redacted_paths.append(path.relative_to(root).as_posix())
    return redacted_paths


def _scan_for_forbidden_plaintext(output_dir: Path, forbidden_values: Sequence[str]) -> dict[str, object]:
    leaks: list[dict[str, object]] = []
    for path in sorted(output_dir.rglob("*")):
        if not path.is_file():
            continue
        if path.name.endswith(".sqlite3") or path.name == "secrets.key":
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        if b"\0" in raw[:4096]:
            continue
        text = raw.decode("utf-8", errors="ignore")
        for value in forbidden_values:
            if value and value in text:
                leaks.append(
                    {
                        "path": _relative_evidence_path(output_dir, path),
                        "value_sha256_prefix": hashlib.sha256(value.encode("utf-8")).hexdigest()[:12],
                    }
                )
    return {"passed": not leaks, "leaks": leaks, "scanned_root": str(output_dir)}


def _pass_result(evidence: dict[str, object]) -> dict[str, object]:
    source_subscription_paths = _specific_ui_evidence_paths(evidence, "source_subscription_ui")
    domain_channel_paths = _specific_ui_evidence_paths(evidence, "domain_channel_ui")
    evidence_paths = [
        "evidence.json",
        "summary.md",
        *[str(path) for path in evidence.get("raw_paths", [])],
        *[str(path) for path in evidence.get("wiki_pages", [])],
        *source_subscription_paths,
        *domain_channel_paths,
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
            },
            {
                "scenario_id": SOURCE_SUBSCRIPTIONS_SCENARIO_ID,
                "status": "pass",
                "evidence": source_subscription_paths,
                "notes": "Playwright clicked the source subscription UI and verified the same-site accelerator candidate trust flow against a real backend",
            },
            {
                "scenario_id": DOMAIN_CHANNELS_SCENARIO_ID,
                "status": "pass",
                "evidence": ["evidence.json", *domain_channel_paths],
                "notes": "API and Playwright flows created a domain channel, replaced a synthetic secret, ran a probe, attached a child source, and verified retained artifacts do not contain secret plaintext",
            }
        ],
        "rerun_commands": [
            "python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/crawler-domain-channels-live-e2e-01"
        ],
        "environment_checks": [
            {"name": "fixture_repo", "status": "pass", "detail": str(evidence.get("fixture_repo", ""))},
            {"name": "domain_validate", "status": "pass", "detail": "returncode=0"},
            {"name": "full_validate", "status": "pass", "detail": "returncode=0"},
            {"name": "source_subscription_ui", "status": "pass", "detail": "playwright returncode=0"},
            {"name": "domain_channel_api", "status": "pass", "detail": "channel/source/probe workflow passed"},
            {"name": "domain_channel_ui", "status": "pass", "detail": "playwright returncode=0"},
            {"name": "secret_plaintext_scan", "status": "pass", "detail": "no retained secret plaintext found"},
        ],
        "verdict_reason": "All required wiki crawler and domain channel E2E outcomes were observed.",
        "next_action": "proceed_to_user_acceptance",
    }


def _blocked_result(reason: str, evidence: dict[str, object] | None = None) -> dict[str, object]:
    evidence = evidence or {}
    source_subscription_paths = _specific_ui_evidence_paths(evidence, "source_subscription_ui")
    domain_channel_paths = _specific_ui_evidence_paths(evidence, "domain_channel_ui")
    evidence_paths = ["evidence.json", *source_subscription_paths, *domain_channel_paths]
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
                "evidence": evidence_paths,
                "notes": reason,
            },
            {
                "scenario_id": SOURCE_SUBSCRIPTIONS_SCENARIO_ID,
                "status": "blocked",
                "evidence": ["evidence.json", *source_subscription_paths],
                "notes": reason,
            },
            {
                "scenario_id": DOMAIN_CHANNELS_SCENARIO_ID,
                "status": "blocked",
                "evidence": ["evidence.json", *domain_channel_paths],
                "notes": reason,
            }
        ],
        "rerun_commands": [
            "python3 scripts/wiki_crawler_e2e_evaluator.py --repo-root . --output-dir .codex/wiki-crawler-e2e/crawler-domain-channels-live-e2e-01"
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
        f"- source_subscriptions_scenario: {result['scenario_results'][1]['status']}\n"
        f"- domain_channels_scenario: {result['scenario_results'][2]['status']}\n"
        f"- verdict: {result['verdict_reason']}\n",
        encoding="utf-8",
    )


def _relative_evidence_path(output_dir: Path, path: Path) -> str:
    try:
        return str(path.relative_to(output_dir).as_posix())
    except ValueError:
        return str(path)


if __name__ == "__main__":
    raise SystemExit(main())
