#!/usr/bin/env python3
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).parent
CANDIDATES = SCRIPT_DIR / "gpu_flow_task_candidates.py"
SNAPSHOT = SCRIPT_DIR / "gpu_flow_status_snapshot.py"
CLEANUP = SCRIPT_DIR / "gpu_flow_cleanup_candidates.py"


def write_repo(root: Path) -> None:
    (root / ".codex" / "session-state").mkdir(parents=True)
    (root / ".codex" / "locks").mkdir(parents=True)
    (root / ".worktrees").mkdir()
    (root / ".worktrees" / "gpu-flow-30").mkdir()
    (root / ".worktrees" / "gpu-flow-32").mkdir()
    (root / ".worktrees" / "unknown-old").mkdir()
    (root / "progress.md").write_text(
        "# 项目进度记录\n\n## 2026-06-18 gpu-flow-07-24 用户验收通过\n",
        encoding="utf-8",
    )
    (root / "tasks.json").write_text(
        json.dumps(
            [
                {
                    "id": "gpu-flow-31",
                    "title": "低风险待认领任务",
                    "description": "实现只读诊断，不需要真实集群。",
                    "status": "pending",
                    "priority": "high",
                    "blocked_by": "",
                    "verify": "go test ./pkg/gpuflow/...",
                    "requires_eval": False,
                },
                {
                    "id": "gpu-flow-32",
                    "title": "已有活跃 session 的任务",
                    "description": "需要避免并发冲突。",
                    "status": "pending",
                    "priority": "high",
                    "blocked_by": "",
                    "verify": "go test ./...",
                    "requires_eval": True,
                },
                {
                    "id": "gpu-flow-33",
                    "title": "低优先级任务",
                    "description": "后续再做。",
                    "status": "pending",
                    "priority": "medium",
                    "blocked_by": "gpu-flow-99",
                    "verify": "manual checklist",
                    "requires_eval": False,
                },
                {
                    "id": "gpu-flow-30",
                    "title": "已完成任务",
                    "description": "不应推荐。",
                    "status": "done",
                    "priority": "high",
                    "blocked_by": "",
                    "verify": "go test ./...",
                    "requires_eval": True,
                },
            ],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (root / ".codex" / "session-state" / "gpu-flow-32-codex.json").write_text(
        json.dumps(
            {
                "task": "gpu-flow-32",
                "session": "codex-test",
                "branch": "task/gpu-flow-32",
                "worktree": str(root / ".worktrees" / "gpu-flow-32"),
                "status": "implementing",
                "touched_paths": ["pkg/gpuflow/controllers"],
                "last_update": "2026-06-18T09:30:00+08:00",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / ".codex" / "session-state" / "gpu-flow-30-codex.json").write_text(
        json.dumps(
            {
                "task": "gpu-flow-30",
                "session": "codex-done",
                "branch": "task/gpu-flow-30",
                "worktree": str(root / ".worktrees" / "gpu-flow-30"),
                "status": "accepted",
                "last_update": "2026-06-01T09:30:00+08:00",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / ".codex" / "locks" / "local-k3s-gpu-flow-32.json").write_text(
        json.dumps(
            {
                "resource": "local-k3s",
                "owner_session": "codex-test",
                "task": "gpu-flow-32",
                "operation": "e2e",
                "started_at": "2026-06-18T09:30:00+08:00",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (root / ".codex" / "locks" / "local-k3s-gpu-flow-30.json").write_text(
        json.dumps(
            {
                "resource": "local-k3s",
                "owner_session": "codex-done",
                "task": "gpu-flow-30",
                "operation": "e2e",
                "started_at": "2026-06-01T09:30:00+08:00",
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


class GpuFlowAutomationTest(unittest.TestCase):
    def run_script(self, script: Path, repo: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(script), "--repo", str(repo), *args],
            text=True,
            capture_output=True,
            timeout=10,
        )

    def test_candidates_rank_unblocked_tasks_and_flag_conflicts(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_repo(repo)

            result = self.run_script(CANDIDATES, repo, "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["summary"]["pending"], 3)
        self.assertEqual(data["candidates"][0]["id"], "gpu-flow-31")
        self.assertEqual(data["candidates"][0]["recommendation"], "claim")
        by_id = {task["id"]: task for task in data["candidates"]}
        self.assertEqual(by_id["gpu-flow-32"]["recommendation"], "coordinate")
        self.assertIn("active_session", by_id["gpu-flow-32"]["reasons"])
        self.assertIn("blocked_by", by_id["gpu-flow-33"]["reasons"])

    def test_status_snapshot_reports_counts_and_recent_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_repo(repo)

            result = self.run_script(SNAPSHOT, repo, "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        self.assertEqual(data["tasks"]["pending"], 3)
        self.assertEqual(data["tasks"]["done"], 1)
        self.assertEqual(data["session_state"]["total"], 2)
        self.assertEqual(data["locks"]["total"], 2)
        self.assertIn("gpu-flow-32", data["session_state"]["active_tasks"])
        self.assertNotIn("gpu-flow-30", data["session_state"]["active_tasks"])
        self.assertIn("gpu-flow-07-24", data["progress_head"])

    def test_cleanup_candidates_classify_done_and_active_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            repo = Path(tmpdir)
            write_repo(repo)

            result = self.run_script(CLEANUP, repo, "--json")

        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(result.stdout)
        by_kind = {}
        for item in data["candidates"]:
            by_kind.setdefault(item["kind"], []).append(item)
        safe_tasks = {item["task_id"] for item in by_kind["safe_review"]}
        keep_tasks = {item["task_id"] for item in by_kind["active_keep"]}
        unknown_paths = {Path(item["path"]).name for item in by_kind["unknown_manual"]}
        self.assertIn("gpu-flow-30", safe_tasks)
        self.assertIn("gpu-flow-32", keep_tasks)
        self.assertIn("unknown-old", unknown_paths)


if __name__ == "__main__":
    unittest.main()
