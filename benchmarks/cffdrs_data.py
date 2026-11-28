"""The test series of cffdrs: downloaded when needed, checked, never committed.

cffdrs is distributed under GPL-2, so its files stay out of this repository.
They are read from the cffdrs_r repository at the commit of version 1.10.0,
by a fixed URL, and accepted only if their SHA-256 is the one recorded here.
A copy is kept in ``benchmarks/cffdrs/.cache/`` (ignored by git) so that a
second run needs no network.

With no network :func:`fetch` raises :class:`Unavailable`: the caller says the
comparison was skipped, it does not pass it. A file that downloads but has
another checksum raises ``RuntimeError``: that is a different file, not a
missing one.
"""

from __future__ import annotations

import csv
import hashlib
import io
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

from fwi_chain import NoonObservation

#: cffdrs_r at version 1.10.0.
COMMIT = "4d20a303bf94febccce62f068cc8ffad0fec57c1"
BASE = f"https://raw.githubusercontent.com/cffdrs/cffdrs_r/{COMMIT}/"

#: The file name here -> its path in cffdrs_r, and the SHA-256 of its bytes there.
FILES = {
    "test_fwi.csv": (
        "data/test_fwi.csv",
        "9fac2165cbc4ffdadd9509943efebddba29afcb6936a4e60ab4d86fafd2a6c2a",
    ),
    "fwi_01.csv": (
        "tests/testthat/data/fwi_01.csv",
        "ad9b9a964eb0409c0e8eeb4f88ce5384cb1b49e098765d5c1f539bc32d96ef43",
    ),
}

CACHE = Path(__file__).parent / "cffdrs" / ".cache"
CODES = ("ffmc", "dmc", "dc", "isi", "bui", "fwi")


class Unavailable(Exception):  # noqa: N818 (a state, not an error of ours)
    """The file could not be downloaded: no network, or the server did not answer."""


def url_of(name: str) -> str:
    return BASE + FILES[name][0]


def fetch(name: str) -> str:
    """The text of one file, from the cache or downloaded, checked by its SHA-256."""
    _, sha256 = FILES[name]
    cached = CACHE / name
    if cached.exists():
        raw = cached.read_bytes()
        if hashlib.sha256(raw).hexdigest() == sha256:
            return raw.decode("utf-8")
    try:
        with urllib.request.urlopen(url_of(name), timeout=30) as response:
            raw = bytes(response.read())
    except (urllib.error.URLError, TimeoutError, OSError) as e:
        raise Unavailable(f"{name} not downloaded from {url_of(name)}: {e}") from e
    got = hashlib.sha256(raw).hexdigest()
    if got != sha256:
        raise RuntimeError(f"{url_of(name)} has SHA-256 {got}, expected {sha256}")
    CACHE.mkdir(parents=True, exist_ok=True)
    cached.write_bytes(raw)
    return raw.decode("utf-8")


def observations() -> dict[date, NoonObservation]:
    """The 48 noon readings, 13 April to 30 May 1985."""
    rows = csv.DictReader(io.StringIO(fetch("test_fwi.csv")), delimiter=";")
    return {
        date(int(r["yr"]), int(r["mon"]), int(r["day"])): NoonObservation(
            float(r["temp"]), float(r["rh"]), float(r["ws"]), float(r["prec"])
        )
        for r in rows
    }


def expected() -> list[dict[str, float]]:
    """What cffdrs gives for the same days, as it keeps them for its own tests."""
    rows = csv.DictReader(io.StringIO(fetch("fwi_01.csv")))
    return [{c: float(r[c.upper()]) for c in CODES} for r in rows]
