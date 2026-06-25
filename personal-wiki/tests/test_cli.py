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


def assert_no_traceback(output: str) -> None:
    assert "Traceback" not in output


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


def test_validate_cli_without_domain_checks_domain_pages(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    build_invalid_fixture(root)

    result = subprocess.run(
        [sys.executable, str(CLI), "--root", str(root), "validate"],
        text=True,
        capture_output=True,
    )

    assert result.returncode == 1
    assert "missing_required" in result.stdout
    assert "domains/ai-infra/wiki/concepts/bad.md" in result.stdout


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


def test_visualize_cli_writes_static_html_to_requested_output(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    build_valid_fixture(root)
    out = tmp_path / "graph.html"

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--root",
            str(root),
            "visualize",
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
    text = out.read_text(encoding="utf-8")
    assert "Personal Wiki Graph" in text
    assert "KV Cache" in text
    assert "https://" not in text
    assert "http://" not in text


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
    raw_image = root / "domains/ai-infra/raw/images/diagram.png"
    raw_image.parent.mkdir(parents=True, exist_ok=True)
    raw_image.write_bytes(b"fake png")

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


def test_image_note_cli_rejects_missing_raw_image_without_writing_note(tmp_path: Path):
    root = tmp_path / "personal-wiki"

    result = subprocess.run(
        [
            sys.executable,
            str(CLI),
            "--root",
            str(root),
            "image-note",
            "ai-infra",
            "raw/images/missing.png",
        ],
        text=True,
        capture_output=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 1
    assert "Image source does not exist" in output
    assert not (root / "domains/ai-infra/wiki/references/missing-image.md").exists()


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
    assert_no_traceback(output)


def test_cli_rejects_invalid_domains_without_writing_outside_root(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    outside = tmp_path / "outside-domain"
    commands = [
        ["init-domain", str(outside)],
        ["index", str(outside)],
        ["backlinks", "--domain", str(outside), "--write-json"],
        ["graph", "--domain", str(outside), "--out", str(tmp_path / "graph.json")],
        ["visualize", "--domain", str(outside), "--out", str(tmp_path / "graph.html")],
    ]

    for command in commands:
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), *command],
            text=True,
            capture_output=True,
        )
        output = result.stdout + result.stderr
        assert result.returncode == 1, command
        assert_no_traceback(output)
        assert "Invalid domain path" in output

    assert not outside.exists()


def test_cli_returns_two_for_unexpected_internal_errors_without_traceback(tmp_path: Path):
    root = tmp_path / "personal-wiki"
    root.write_text("not a directory", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(CLI), "--root", str(root), "init-domain", "ai-infra"],
        text=True,
        capture_output=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 2
    assert_no_traceback(output)


def test_cli_returns_two_when_root_discovery_fails_without_traceback(tmp_path: Path):
    cwd = tmp_path / "not-a-repo"
    cwd.mkdir()

    result = subprocess.run(
        [sys.executable, str(CLI), "validate"],
        cwd=cwd,
        text=True,
        capture_output=True,
    )

    output = result.stdout + result.stderr
    assert result.returncode == 2
    assert "Internal error:" in output
    assert_no_traceback(output)


def test_cli_end_to_end_domain_workflow(tmp_path: Path):
    root = tmp_path / "personal-wiki"

    def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [sys.executable, str(CLI), "--root", str(root), *args],
            text=True,
            capture_output=True,
        )
        assert result.returncode == 0, result.stdout + result.stderr
        return result

    run_cli("init-domain", "ai-infra")
    build_valid_fixture(root)

    run_cli("validate", "--domain", "ai-infra")
    run_cli("index", "ai-infra")
    run_cli("backlinks", "--domain", "ai-infra", "--write-json")

    graph_json = tmp_path / "graph.json"
    graph_html = tmp_path / "graph.html"
    run_cli("graph", "--domain", "ai-infra", "--out", str(graph_json))
    run_cli("visualize", "--domain", "ai-infra", "--out", str(graph_html))
    run_cli("snapshot-url", "ai-infra", "https://example.com/source")

    raw_image = root / "domains/ai-infra/raw/images/diagram.png"
    raw_image.parent.mkdir(parents=True, exist_ok=True)
    raw_image.write_bytes(b"fake png")
    run_cli("image-note", "ai-infra", "raw/images/diagram.png")
    run_cli("ingest-plan", "ai-infra", "raw/links/example-com-source.md")

    assert (root / "domains/ai-infra/DOMAIN.md").exists()
    assert (root / "domains/ai-infra/raw/notes/source.md").exists()
    assert (root / "domains/ai-infra/wiki/concepts/kv-cache.md").exists()
    assert (root / "domains/ai-infra/wiki/index.md").exists()
    assert (root / "domains/ai-infra/wiki/backlinks.json").exists()
    assert graph_json.exists()
    assert graph_html.exists()
    assert (root / "domains/ai-infra/raw/links/example-com-source.md").exists()
    assert (root / "domains/ai-infra/wiki/references/diagram-image.md").exists()
    assert (root / "domains/ai-infra/raw/links/example-com-source.ingest-plan.md").exists()
