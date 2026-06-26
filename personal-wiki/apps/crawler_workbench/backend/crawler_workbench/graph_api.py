from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

from .settings import Settings


def _load_graph_module(repo_root: Path) -> ModuleType:
    graph_path = _graph_path(repo_root)
    package_name = _package_name(graph_path.parent)
    _ensure_package(package_name, graph_path.parent)
    module_name = f"{package_name}.graph"
    spec = importlib.util.spec_from_file_location(module_name, graph_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load wiki graph module from {graph_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(module_name, None)
        raise
    return module


def domain_graph(settings: Settings, domain: str | None = None) -> dict[str, object]:
    graph_module = _load_graph_module(settings.repo_root)
    return graph_module.build_graph(settings.wiki_root, domain)


def _graph_path(repo_root: Path) -> Path:
    configured = repo_root / "personal-wiki" / "tools" / "wiki_cli" / "graph.py"
    if configured.exists():
        return configured

    bundled = Path(__file__).resolve().parents[4] / "tools" / "wiki_cli" / "graph.py"
    if bundled.exists():
        return bundled
    return configured


def _package_name(path: Path) -> str:
    digest = hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()[:12]
    return f"workbench_wiki_cli_{digest}"


def _ensure_package(name: str, path: Path) -> None:
    package = sys.modules.get(name)
    if package is None:
        package = ModuleType(name)
        package.__package__ = name
        sys.modules[name] = package
    package.__path__ = [str(path)]  # type: ignore[attr-defined]
