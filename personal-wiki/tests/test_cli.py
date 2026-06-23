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


def test_init_domain_cli_creates_domain_skeleton(tmp_path: Path):
    root = tmp_path / "personal-wiki"

    result = subprocess.run(
        [sys.executable, str(CLI), "--root", str(root), "init-domain", "ai-infra"],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert (root / "domains/ai-infra/DOMAIN.md").exists()
    assert (root / "domains/ai-infra/wiki/concepts").is_dir()
    assert "domains/ai-infra/wiki/index.md" in result.stdout


def test_index_cli_writes_domain_index(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    build_valid_fixture(root)

    result = subprocess.run(
        [sys.executable, str(CLI), "--root", str(root), "index", "ai-infra"],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    index_path = root / "domains/ai-infra/wiki/index.md"
    assert str(index_path) in result.stdout
    assert "- [KV Cache](concepts/kv-cache.md) - Cache for transformer key/value states." in (
        index_path.read_text(encoding="utf-8")
    )


def test_backlinks_cli_writes_json_for_domain(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    build_valid_fixture(root)
    write(
        root / "domains/ai-infra/wiki/papers/attention.md",
        "---\ntype: Paper\ntitle: Attention\ndescription: Attention paper.\ndomain: ai-infra\nstatus: draft\nsource_refs: []\n---\n\nSee [KV Cache](../concepts/kv-cache.md).\n",
    )

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--root",
            str(root),
            "backlinks",
            "--domain",
            "ai-infra",
            "--write-json",
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    backlinks_path = root / "domains/ai-infra/wiki/backlinks.json"
    assert str(backlinks_path) in result.stdout
    assert json.loads(backlinks_path.read_text(encoding="utf-8")) == {
        "domains/ai-infra/wiki/concepts/kv-cache": [
            "domains/ai-infra/wiki/papers/attention"
        ]
    }


def test_graph_cli_writes_graph_json_to_requested_output(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    build_valid_fixture(root)
    out = tmp_path / "graph.json"

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--root",
            str(root),
            "graph",
            "--domain",
            "ai-infra",
            "--out",
            str(out),
        ],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0
    assert str(out) in result.stdout
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert {
        "id": "domains/ai-infra/wiki/concepts/kv-cache",
        "path": "domains/ai-infra/wiki/concepts/kv-cache.md",
        "title": "KV Cache",
        "type": "Concept",
        "tags": [],
        "description": "Cache for transformer key/value states.",
    } in payload["nodes"]


def test_snapshot_url_cli_creates_raw_link_source(tmp_path: Path):
    root = tmp_path / "personal-wiki"

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--root",
            str(root),
            "snapshot-url",
            "ai-infra",
            "https://example.com/a",
        ],
        text=True,
        capture_output=True,
    )

    path = root / "domains/ai-infra/raw/links/example-com-a.md"
    assert result.returncode == 0
    assert str(path) in result.stdout
    assert "source_kind: web" in path.read_text(encoding="utf-8")


def test_image_note_cli_creates_reference_note(tmp_path: Path):
    root = tmp_path / "personal-wiki"

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--root",
            str(root),
            "image-note",
            "ai-infra",
            "raw/images/diagram.png",
        ],
        text=True,
        capture_output=True,
    )

    path = root / "domains/ai-infra/wiki/references/diagram-image.md"
    assert result.returncode == 0
    assert str(path) in result.stdout
    text = path.read_text(encoding="utf-8")
    assert "type: Reference" in text
    assert "# Image Meaning" in text


def test_ingest_plan_cli_creates_raw_plan(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    write(root / "domains/ai-infra/raw/inbox/source.md", "# Source\n")

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--root",
            str(root),
            "ingest-plan",
            "ai-infra",
            "raw/inbox/source.md",
        ],
        text=True,
        capture_output=True,
    )

    path = root / "domains/ai-infra/raw/inbox/source.ingest-plan.md"
    assert result.returncode == 0
    assert str(path) in result.stdout
    assert "Candidate page types" in path.read_text(encoding="utf-8")


def test_ingest_plan_cli_reports_absolute_path_outside_domain_without_traceback(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    outside = tmp_path / "outside" / "source.md"
    write(outside, "# Source\n")

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--root",
            str(root),
            "ingest-plan",
            "ai-infra",
            str(outside),
        ],
        text=True,
        capture_output=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert "outside domain" in output
    assert "Traceback" not in output
