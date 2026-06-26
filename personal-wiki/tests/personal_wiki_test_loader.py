import importlib.util
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI_ROOT = ROOT / "tools" / "wiki_cli"


def load_cli_module(name: str):
    path = CLI_ROOT / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"wiki_cli_{name}", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
