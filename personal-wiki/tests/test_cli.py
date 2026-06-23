import json
import subprocess
import sys
from pathlib import Path


CLI = Path(__file__).resolve().parents[1] / "tools" / "wiki_cli" / "cli.py"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def build_valid_fixture(root: Path) -> None:
    write(
        root / "domains/ai-infra/raw/notes/source.md",
        "---\ntype: RawSource\ntitle: Source\nsource_kind: note\ncaptured: 2026-06-23\nstatus: pending\n---\n\n# Raw Content\n",
    )
    write(
        root / "domains/ai-infra/wiki/concepts/kv-cache.md",
        "---\ntype: Concept\ntitle: KV Cache\ndescription: Cache for transformer key/value states.\ndomain: ai-infra\nstatus: draft\nsource_refs:\n  - ../../raw/notes/source.md\n---\n\n# Summary\nBody.\n\n# Citations\n- ../../raw/notes/source.md\n",
    )


def build_invalid_fixture(root: Path) -> None:
    write(
        root / "domains/ai-infra/wiki/concepts/bad.md",
        "---\ntype: Concept\ntitle: Bad\ndomain: ai-infra\n---\n\n# Summary\nMissing description.\n",
    )


def test_validate_cli_exits_zero_for_valid_fixture(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    build_valid_fixture(root)
    result = subprocess.run(
        [sys.executable, str(CLI), "--root", str(root), "validate", "--domain", "ai-infra"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0
    assert "No validation issues" in result.stdout


def test_validate_cli_exits_one_for_invalid_fixture(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    build_invalid_fixture(root)
    result = subprocess.run(
        [sys.executable, str(CLI), "--root", str(root), "validate", "--domain", "ai-infra"],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert "missing_required" in result.stdout
    assert "wiki/concepts/bad.md" in result.stdout
    assert "description" in result.stdout


def test_validate_cli_discovers_root_from_outer_repo_cwd(tmp_path: Path):
    outer = tmp_path / "repo"
    root = outer / "personal-wiki"
    build_invalid_fixture(root)
    write(root / "WIKI.md", "# Personal Wiki\n")

    result = subprocess.run(
        [sys.executable, str(CLI), "validate", "--domain", "ai-infra"],
        cwd=outer,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "missing_required" in result.stdout


def test_validate_cli_outputs_json_list_for_invalid_fixture(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    build_invalid_fixture(root)
    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--root",
            str(root),
            "validate",
            "--domain",
            "ai-infra",
            "--json",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload == [
        {
            "code": "missing_required",
            "path": str(root / "domains/ai-infra/wiki/concepts/bad.md"),
            "message": "Missing required frontmatter field: description",
        }
    ]
