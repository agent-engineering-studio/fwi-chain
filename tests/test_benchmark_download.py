"""The cffdrs series is downloaded and checked; without it the comparison is skipped, not passed.

No network here: the download is replaced, so these tests run offline.
"""

from __future__ import annotations

import hashlib
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from benchmarks import cffdrs_data, run


class _Response:
    def __init__(self, raw: bytes) -> None:
        self.raw = raw

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_: object) -> None:
        return None

    def read(self) -> bytes:
        return self.raw


@pytest.fixture
def empty_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setattr(cffdrs_data, "CACHE", tmp_path / "cache")
    return tmp_path


@pytest.fixture
def offline(empty_cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*_: Any, **__: Any) -> None:
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(urllib.request, "urlopen", refuse)


def test_no_network_is_unavailable(offline: None) -> None:
    with pytest.raises(cffdrs_data.Unavailable, match="no network"):
        cffdrs_data.fetch("test_fwi.csv")


def test_without_the_series_the_cases_are_skipped_not_passed(
    offline: None, capsys: pytest.CaptureFixture[str]
) -> None:
    results = run.run()
    skipped = [r for r in results if r.outcome == "skipped"]
    assert {r.case for r in skipped} == {"cffdrs-48-days", "cffdrs-48-days-cffdrs-constants"}
    assert run.main(["--check"]) == 0
    assert "SKIPPED, not passed" in capsys.readouterr().out
    assert run.main(["--check", "--require-download"]) == 1


def test_another_file_is_refused(empty_cache: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_, **__: _Response(b"not it"))
    with pytest.raises(RuntimeError, match="SHA-256"):
        cffdrs_data.fetch("test_fwi.csv")
    assert not (empty_cache / "cache" / "test_fwi.csv").exists()


def test_the_right_file_is_kept_for_the_next_run(
    empty_cache: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = b"long;lat;yr;mon;day;temp;rh;ws;prec\r\n"
    name = "test_fwi.csv"
    monkeypatch.setitem(
        cffdrs_data.FILES, name, (cffdrs_data.FILES[name][0], hashlib.sha256(raw).hexdigest())
    )
    monkeypatch.setattr(urllib.request, "urlopen", lambda *_, **__: _Response(raw))
    assert cffdrs_data.fetch(name) == raw.decode()
    monkeypatch.setattr(urllib.request, "urlopen", None)
    assert cffdrs_data.fetch(name) == raw.decode()
