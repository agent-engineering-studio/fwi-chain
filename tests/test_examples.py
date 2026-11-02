"""The examples are documentation, so they must keep running.

Each script in ``examples/`` is executed as ``__main__`` in a scratch
directory: a renamed argument or a changed default breaks the build here
instead of breaking a reader's first five minutes.
"""

from __future__ import annotations

import runpy
import sys
from pathlib import Path

import pytest

EXAMPLES = Path(__file__).parent.parent / "examples"
SCRIPTS = sorted(EXAMPLES.glob("[0-9][0-9]_*.py"))


def test_there_are_examples() -> None:
    assert SCRIPTS


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda p: p.name)
def test_example_runs(
    script: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.syspath_prepend(str(EXAMPLES))
    monkeypatch.setattr(sys, "argv", [str(script), str(tmp_path / "out")])
    runpy.run_path(str(script), run_name="__main__")
    assert capsys.readouterr().out.strip()
