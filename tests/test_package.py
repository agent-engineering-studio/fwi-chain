"""What the package promises about itself: no dependency, no sister library, no clock."""

from __future__ import annotations

import ast
import tomllib
from pathlib import Path

import fwi_chain

SRC = Path(fwi_chain.__file__).parent
ROOT = Path(__file__).parent.parent

#: Sister libraries, Limen and limen-core. limen-core pins all of them: if one
#: imported another, it would get a circular dependency and pins in conflict.
FORBIDDEN = {
    "copernicus_ems",
    "dpc_radar",
    "effis_client",
    "egms_client",
    "glofas_ewds",
    "ispra_idrogeo",
    "limen",
    "limen_core",
    "rainfall_thresholds",
}
#: The standard library modules the package may use. Anything else is a
#: dependency (``mcp`` is the one exception, in the one module behind its extra).
ALLOWED = {
    "__future__",
    "argparse",
    "collections",
    "dataclasses",
    "datetime",
    "importlib",
    "itertools",
    "math",
    "re",
    "typing",
    "fwi_chain",
}


def imports() -> list[tuple[str, str]]:
    found = []
    for path in sorted(SRC.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            found += [(path.name, n.split(".")[0]) for n in names]
    return found


def test_version_is_exposed() -> None:
    assert fwi_chain.__version__


def test_the_project_declares_no_dependency() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]
    assert project["dependencies"] == []
    assert sorted(project["optional-dependencies"]) == ["mcp"]


def test_the_package_imports_no_sister_library() -> None:
    assert [f"{file}: {name}" for file, name in imports() if name in FORBIDDEN] == []


def test_the_package_imports_only_the_standard_library() -> None:
    outside = {(file, name) for file, name in imports() if name not in ALLOWED}
    assert outside == {("mcp_server.py", "mcp")}


def test_nothing_reads_a_clock_or_a_file() -> None:
    """No ``today()``, ``now()`` or ``open()``: the day is always an argument."""
    found = []
    for path in sorted(SRC.rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Call):
                name = getattr(node.func, "attr", getattr(node.func, "id", ""))
                if name in {"today", "now", "utcnow", "open", "read_text", "write_text"}:
                    found.append(f"{path.name}:{node.lineno} {name}()")
    assert found == []
