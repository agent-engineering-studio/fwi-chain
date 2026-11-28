"""How faithfully a text quotes the facts: numbers invented, in the wrong unit, rounded.

    uv run python -m benchmarks.faithful            # the table
    uv run python -m benchmarks.faithful --check    # CI: the hand answers score as written

The facts are those of the cffdrs test series, which is downloaded (see
:mod:`benchmarks.cffdrs_data`). With no network the set is **skipped**, not
passed; ``--require-download`` makes that a failure.

**The set** (``faithful.json``): questions, the tool that answers each, and
answers written by hand, one faithful and one with known faults. The facts are
computed by the library when the set runs, so a change in a number shows here.
``--check`` fails when :func:`fwi_chain.check.check_text` does not find exactly
the faults written in ``expect``: it tests the checker, not a model.

**A model's answers** are not here yet. Asking a model costs money and needs
an API key: it is done only after an explicit yes, and its answers are then
added to the set with ``by`` naming the model.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from datetime import date
from pathlib import Path
from typing import Any

from benchmarks import cffdrs_data
from benchmarks.run import cffdrs_series
from fwi_chain import STANDARD_PARAMS
from fwi_chain.check import check_text
from fwi_chain.facts import day_facts, distribution_facts, walk_facts

HERE = Path(__file__).parent


def facts(case: dict[str, Any]) -> dict[str, Any]:
    series = next(
        c
        for c in tomllib.loads((HERE / "cases.toml").read_text(encoding="utf-8"))["case"]
        if c["id"] == "cffdrs-48-days"
    )
    walked, _ = cffdrs_series(series)
    args = case["args"]
    at = {d.day: i for i, d in enumerate(walked)}
    if case["tool"] == "walk":
        return walk_facts(walked, params=STANDARD_PARAMS)
    if case["tool"] == "explain":
        i = at[date.fromisoformat(args["day"])]
        return day_facts(
            walked[i],
            previous=walked[i - 1],
            params=STANDARD_PARAMS,
            spinup_days=args.get("spinup_days"),
        )
    if case["tool"] == "percentile":
        values = [d.outputs.fwi for d in walked if d.day.month == args["month"]]
        return distribution_facts(
            values, value=walked[at[date.fromisoformat(args["day"])]].outputs.fwi
        )
    raise ValueError(f"unknown tool {case['tool']!r}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if a hand answer scores wrong")
    parser.add_argument(
        "--require-download",
        action="store_true",
        help="fail, instead of skipping, when the cffdrs series cannot be downloaded",
    )
    args = parser.parse_args(argv)
    cases = json.loads((HERE / "faithful.json").read_text(encoding="utf-8"))["cases"]
    try:
        cffdrs_data.observations()
    except cffdrs_data.Unavailable as e:
        print(f"SKIPPED, not passed: {len(cases)} questions, the series is not here. {e}")
        return 1 if args.require_download else 0
    wrong = 0
    total = 0
    for case in cases:
        found_facts = facts(case)
        print(f"{case['id']}: {case['question']}")
        for answer in case["answers"]:
            total += 1
            found = check_text(answer["text"], found_facts, question=case["question"])
            got = [[m.text, m.fault] for m in found]
            ok = got == answer["expect"]
            wrong += not ok
            faults = ", ".join(f"{t} ({f})" for t, f in got) or "no fault"
            print(f"  {'✓' if ok else '✗'} {answer['by']:<16} {faults}")
            if not ok:
                print(f"      expected: {answer['expect']}")
    print(f"\n{total - wrong} of {total} answers scored as expected")
    return 1 if args.check and wrong else 0


if __name__ == "__main__":
    sys.exit(main())
