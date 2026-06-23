from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import graph as graph_module  # type: ignore
    import html as html_module  # type: ignore
    import ingest  # type: ignore
    import indexer  # type: ignore
    import paths  # type: ignore
    import validate as validate_module  # type: ignore
else:
    from . import graph as graph_module
    from . import html as html_module
    from . import ingest
    from . import indexer
    from . import paths
    from . import validate as validate_module


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wiki-cli")
    parser.add_argument("--root", type=Path)

    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("--domain")
    validate_parser.add_argument("--json", action="store_true")
    init_domain_parser = subparsers.add_parser("init-domain")
    init_domain_parser.add_argument("name")
    index_parser = subparsers.add_parser("index")
    index_parser.add_argument("domain")
    backlinks_parser = subparsers.add_parser("backlinks")
    backlinks_parser.add_argument("--domain")
    backlinks_parser.add_argument("--write-json", action="store_true")
    graph_parser = subparsers.add_parser("graph")
    graph_parser.add_argument("--domain")
    graph_parser.add_argument("--out", type=Path, default=Path("graph.json"))
    visualize_parser = subparsers.add_parser("visualize")
    visualize_parser.add_argument("--domain")
    visualize_parser.add_argument("--out", type=Path, default=Path("graph.html"))
    snapshot_parser = subparsers.add_parser("snapshot-url")
    snapshot_parser.add_argument("domain")
    snapshot_parser.add_argument("url")
    snapshot_parser.add_argument("--fetch", action="store_true")
    image_parser = subparsers.add_parser("image-note")
    image_parser.add_argument("domain")
    image_parser.add_argument("image_path")
    ingest_parser = subparsers.add_parser("ingest-plan")
    ingest_parser.add_argument("domain")
    ingest_parser.add_argument("raw_path")

    args = parser.parse_args(argv)
    root = args.root if args.root is not None else paths.repo_root_from(Path.cwd())

    try:
        if args.command == "validate":
            return _run_validate(root, args.domain, args.json)
        if args.command == "init-domain":
            return _run_init_domain(root, args.name)
        if args.command == "index":
            return _run_index(root, args.domain)
        if args.command == "backlinks":
            return _run_backlinks(root, args.domain, args.write_json)
        if args.command == "graph":
            return _run_graph(root, args.domain, args.out)
        if args.command == "visualize":
            return _run_visualize(root, args.domain, args.out)
        if args.command == "snapshot-url":
            return _run_snapshot_url(root, args.domain, args.url, args.fetch)
        if args.command == "image-note":
            return _run_image_note(root, args.domain, args.image_path)
        if args.command == "ingest-plan":
            return _run_ingest_plan(root, args.domain, args.raw_path)
    except ValueError as error:
        print(str(error), file=sys.stderr)
        return 1
    except Exception as error:
        print(f"Internal error: {error}", file=sys.stderr)
        return 2

    parser.error(f"Unknown command: {args.command}")
    return 1


def _run_validate(root: Path, domain: str | None, output_json: bool) -> int:
    issues = validate_module.validate(root, domain=domain)
    if output_json:
        print(
            json.dumps(
                [
                    {
                        "code": issue.code,
                        "path": str(issue.path),
                        "message": issue.message,
                    }
                    for issue in issues
                ],
                indent=2,
            )
        )
    elif issues:
        for issue in issues:
            print(f"{issue.code} {issue.path} {issue.message}")
    else:
        print("No validation issues")
    return 1 if issues else 0


def _run_init_domain(root: Path, name: str) -> int:
    for path in indexer.init_domain(root, name):
        print(path.relative_to(root).as_posix())
    return 0


def _run_index(root: Path, domain: str) -> int:
    path = indexer.build_index(root, domain)
    print(path)
    return 0


def _run_backlinks(root: Path, domain: str | None, write_json: bool) -> int:
    backlinks = graph_module.collect_backlinks(root, domain)
    if write_json:
        out = _wiki_root(root, domain) / "backlinks.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(backlinks, indent=2) + "\n", encoding="utf-8")
        print(out)
    else:
        print(json.dumps(backlinks, indent=2))
    return 0


def _run_graph(root: Path, domain: str | None, out: Path) -> int:
    path = graph_module.write_graph(root, domain, out)
    print(path)
    return 0


def _run_visualize(root: Path, domain: str | None, out: Path) -> int:
    path = html_module.generate_html(root, domain, out)
    print(path)
    return 0


def _run_snapshot_url(root: Path, domain: str, url: str, fetch: bool) -> int:
    path = ingest.snapshot_url(root, domain, url, fetch=fetch)
    print(path)
    return 0


def _run_image_note(root: Path, domain: str, image_path: str) -> int:
    path = ingest.image_note(root, domain, image_path)
    print(path)
    return 0


def _run_ingest_plan(root: Path, domain: str, raw_path: str) -> int:
    path = ingest.ingest_plan(root, domain, raw_path)
    print(path)
    return 0


def _wiki_root(root: Path, domain: str | None) -> Path:
    if domain is not None:
        return paths.domain_wiki(root, domain)
    return root / "global" / "wiki"


if __name__ == "__main__":
    raise SystemExit(main())
