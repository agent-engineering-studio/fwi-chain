"""Check that a text quotes the facts: no number invented, none in the wrong unit.

A model turns the facts of :mod:`fwi_chain.facts` into words. The faults that
matter here are three:

* **invented**: a number that is in no fact;
* **unit**: a number that is a fact, but of another unit. The classic one:
  the 12.4 mm of rain written as 12.4 %, or a wind in km/h given as a
  temperature. The six codes have no unit: "an FWI of 23.4 %" is a fault;
* **rounded**: a number close to a fact, but not the fact rounded to the
  decimals written (``23.5`` for 23.4).

A number may be written with fewer decimals than the fact (``23`` for 23.4)
or, from 100, as a round number (``500`` for 512). Dates, years and clock
times (``10/10``, ``10 October 2026``, ``2026-10-10``, ``12:00``) are not
checked, nor numbers that are in the question. The check knows that a number
is a fact of the right unit, not that it is said of the right thing: "the DC
is 23.4" passes when 23.4 is the FWI. And the more numbers the facts hold, the
more a small invented one can pass by chance: against a whole series of days,
"12 storms" passes if any reading is 12. Check a text against the facts of
the day it is about, not against the whole walk.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

Fault = Literal["invented", "unit", "rounded"]

#: Units as they are written in a text, and as they are named in fact keys.
_UNITS = {
    "\u00b0c": "c",
    "\u00b0 c": "c",
    "degrees celsius": "c",
    "degrees": "c",
    "gradi": "c",
    "km/h": "kmh",
    "kmh": "kmh",
    "kph": "kmh",
    "mm": "mm",
    "millimetres": "mm",
    "millimeters": "mm",
    "millimetri": "mm",
    "days": "days",
    "day": "days",
    "giorni": "days",
    "giorno": "days",
    "%": "pct",
}
_UNIT_RE = "|".join(re.escape(u) for u in sorted(_UNITS, key=len, reverse=True))
_NUMBER = re.compile(
    rf"(?<![\w.])(?P<num>[-+\u2212]?\d+(?:[.,]\d+)*)(?:\s*(?P<unit>{_UNIT_RE})(?![\w/]))?",
    re.IGNORECASE,
)
_MONTHS = (
    "january|february|march|april|may|june|july|august|september|october|november|december|"
    "gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre"
)
_DATES = re.compile(
    r"\d{4}-\d{2}-\d{2}(?:[T ]\d{2}:\d{2}(?::\d{2})?(?:[+-]\d{2}:\d{2}|Z)?)?"
    r"|\b\d{1,2}:\d{2}\b|\b\d{1,2}/\d{1,2}(?:/\d{2,4})?\b"
    rf"|\b\d{{1,2}}\s+(?:{_MONTHS})(?:\s+\d{{4}})?\b|\b(?:19|20)\d{{2}}\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class Misquote:
    """A number of the text that is not a fact as written."""

    text: str
    unit: str | None
    fault: Fault
    #: The nearest fact, as ``path = value unit``, when there is one.
    nearest: str | None = None


def _unit_of(key: str) -> str | None:
    for suffix, unit in (
        ("_c", "c"),
        ("_pct", "pct"),
        ("_kmh", "kmh"),
        ("_mm", "mm"),
        ("_days", "days"),
    ):
        if key.endswith(suffix):
            return unit
    return None


def facts_of(facts: Any, path: str = "") -> Iterator[tuple[str, float, str | None]]:
    """Every number in ``facts``, with its path and the unit its key names."""
    if isinstance(facts, dict):
        for key, value in facts.items():
            yield from facts_of(value, f"{path}.{key}" if path else str(key))
    elif isinstance(facts, list | tuple):
        for i, value in enumerate(facts):
            yield from facts_of(value, f"{path}.{i}")
    elif isinstance(facts, bool) or facts is None:
        return
    elif isinstance(facts, int | float) and math.isfinite(facts):
        # The unit is named by the key, or by a key above it: the counts
        # under "class_days" are days.
        units = (_unit_of(key) for key in reversed(path.split(".")))
        yield path, float(facts), next((u for u in units if u is not None), None)


def parse_number(token: str) -> tuple[float, int]:
    """A number as written -> its value and its decimals. ``1,603`` is 1603; ``2,5`` is 2.5."""
    t = token.replace("\u2212", "-")  # the minus sign
    if re.fullmatch(r"[-+]?\d{1,3}(?:,\d{3})+(?:\.\d+)?", t):
        t = t.replace(",", "")
    elif re.fullmatch(r"[-+]?\d{1,3}(?:(?:\.\d{3}){2,}(?:,\d+)?|\.\d{3},\d+)", t):
        # A dot for thousands only when it cannot be a decimal point:
        # 1.234.567 or 1.603,5. "0.506" and "1.603" are decimals.
        t = t.replace(".", "").replace(",", ".")
    else:
        t = t.replace(",", ".")
    decimals = len(t.split(".", 1)[1]) if "." in t else 0
    return float(t), decimals


def _agrees(written: float, decimals: int, fact: float) -> bool:
    if round(fact, decimals) == written or round(abs(fact), decimals) == abs(written):
        return True
    if decimals == 0 and abs(written) >= 100:
        # A round number: 1,600 for 1,603. Only from 100: below it, "20" for
        # 15.3 would pass.
        zeros = len(str(int(abs(written)))) - len(str(int(abs(written))).rstrip("0"))
        return zeros > 0 and round(abs(fact), -zeros) == abs(written)
    return False


def _close(written: float, decimals: int, fact: float) -> bool:
    return abs(abs(fact) - abs(written)) <= 10.0 ** (-decimals) + 1e-9


def check_text(text: str, facts: Any, *, question: str = "") -> list[Misquote]:
    """The numbers of ``text`` that are not facts of their unit. Empty: faithful."""
    known = list(facts_of(facts))
    asked = {parse_number(m.group("num"))[0] for m in _NUMBER.finditer(_DATES.sub(" ", question))}
    found: list[Misquote] = []
    for m in _NUMBER.finditer(_DATES.sub(" ", text)):
        token = m.group("num")
        written, decimals = parse_number(token)
        unit = _UNITS[m.group("unit").lower()] if m.group("unit") else None
        if written in asked:
            continue
        same_unit = [k for k in known if unit is None or k[2] == unit]
        if any(_agrees(written, decimals, v) for _, v, _ in same_unit):
            continue
        other = [k for k in known if k[2] != unit and _agrees(written, decimals, k[1])]
        if other:
            path, value, u = other[0]
            found.append(
                Misquote(m.group(0), unit, "unit", f"{path} = {value:g} {u or ''}".strip())
            )
            continue
        near = [k for k in known if k[2] == unit and _close(written, decimals, k[1])]
        if near:
            path, value, u = near[0]
            found.append(
                Misquote(m.group(0), unit, "rounded", f"{path} = {value:g} {u or ''}".strip())
            )
            continue
        found.append(Misquote(m.group(0), unit, "invented"))
    return found
