"""Run the known cases and print how the chain scores.

    uv run python -m benchmarks.run            # the table
    uv run python -m benchmarks.run --check    # CI: fail if an outcome or a measure changed
    uv run python -m benchmarks.run --write    # save them in results.json
    uv run python -m benchmarks.run --check --require-download   # CI

``--check`` fails when an outcome, or a measured difference, is not the one
in ``results.json``: a change to the code or to a case is seen, and saved on
purpose.

The comparison with cffdrs downloads its test series (see
:mod:`benchmarks.cffdrs_data`). With no network those cases are reported as
**skipped**, never as passed; ``--require-download`` turns a skip into a
failure, and CI runs with it.
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal

from benchmarks import cffdrs_data
from fwi_chain import (
    CFFDRS_PARAMS,
    STANDARD_PARAMS,
    ChainDay,
    ChainPoint,
    FwiParams,
    FwiState,
    NoonObservation,
    advance,
    catch_up,
    effis_class,
    walk_chain,
)

HERE = Path(__file__).parent
RESULTS = HERE / "results.json"
CODES = ("ffmc", "dmc", "dc", "isi", "bui", "fwi")

Outcome = Literal["pass", "fail", "skipped"]

PARAMS: dict[str, FwiParams] = {"1987": STANDARD_PARAMS, "cffdrs": CFFDRS_PARAMS}


@dataclass(frozen=True, slots=True)
class Result:
    case: str
    check: str
    outcome: Outcome
    got: str


def codes_of(day: ChainDay) -> dict[str, float]:
    o = day.outputs
    return {
        "ffmc": o.state.ffmc,
        "dmc": o.state.dmc,
        "dc": o.state.dc,
        "isi": o.isi,
        "bui": o.bui,
        "fwi": o.fwi,
    }


def cffdrs_series(case: dict[str, Any]) -> tuple[list[ChainDay], list[dict[str, float]]]:
    """The chain over the inputs, and what cffdrs gives for the same days.

    Raises :class:`benchmarks.cffdrs_data.Unavailable` when the series cannot
    be downloaded.
    """
    observations = cffdrs_data.observations()
    walked = walk_chain(
        observations,
        sorted(observations),
        start=None,
        params=PARAMS[case.get("constants", "1987")],
        max_gap_days=7,
    )
    return walked, cffdrs_data.expected()


def against_cffdrs(case: dict[str, Any]) -> list[Result]:
    try:
        walked, expected = cffdrs_series(case)
    except cffdrs_data.Unavailable as e:
        return [Result(case["id"], "the series of cffdrs 1.10.0", "skipped", str(e))]
    out = []
    for code in CODES:
        worst = max(abs(codes_of(d)[code] - e[code]) for d, e in zip(walked, expected, strict=True))
        limit = case["tolerance"][code]
        out.append(
            Result(
                case["id"],
                f"{code.upper()} within {limit:g} of cffdrs",
                "pass" if worst <= limit else "fail",
                f"largest difference {worst:.3f} over {len(walked)} days",
            )
        )
    same = sum(
        effis_class(d.outputs.fwi) == effis_class(e["fwi"])
        for d, e in zip(walked, expected, strict=True)
    )
    out.append(
        Result(
            case["id"],
            "same EFFIS class as cffdrs, every day",
            "pass" if same == len(walked) else "fail",
            f"{same} of {len(walked)} days",
        )
    )
    return out


def one_day(case: dict[str, Any], rain_mm: float | None = None) -> dict[str, float]:
    reading = dict(case.get("reading") or {})
    if rain_mm is not None:
        reading["rain_24h_mm"] = rain_mm
    out = advance(FwiState(**case["state"]), month=case["month"], params=STANDARD_PARAMS, **reading)
    return {
        "ffmc": out.state.ffmc,
        "dmc": out.state.dmc,
        "dc": out.state.dc,
        "isi": out.isi,
        "bui": out.bui,
        "fwi": out.fwi,
    }


def day(case: dict[str, Any]) -> list[Result]:
    got = one_day(case)
    return [
        Result(
            case["id"],
            f"{code.upper()} = {want:.6g}",
            "pass" if abs(got[code] - want) <= case["tolerance"] else "fail",
            f"{got[code]:.6f}",
        )
        for code, want in case["expect"].items()
    ]


#: A dry summer day on fuel that has been drying: every code can go down.
_RAIN_CASE = {
    "state": {"ffmc": 90.0, "dmc": 40.0, "dc": 300.0},
    "month": 7,
    "reading": {"temperature_c": 25.0, "relative_humidity_pct": 40.0, "wind_speed_kmh": 15.0},
}


def rain_threshold(case: dict[str, Any]) -> list[Result]:
    code = case["code"]
    dry = one_day(_RAIN_CASE, 0.0)[code]
    at = one_day(_RAIN_CASE, case["at_mm"])[code]
    above = one_day(_RAIN_CASE, case["above_mm"])[code]
    return [
        Result(
            case["id"],
            f"{case['at_mm']} mm leaves {code.upper()} as a dry day",
            "pass" if at == dry else "fail",
            f"{at:.3f} against {dry:.3f}",
        ),
        Result(
            case["id"],
            f"{case['above_mm']} mm lowers {code.upper()}",
            "pass" if above < dry else "fail",
            f"{above:.3f} against {dry:.3f}",
        ),
    ]


def stale_start(case: dict[str, Any]) -> list[Result]:
    target = date(2026, 7, 20)
    start = ChainPoint(
        day=target - timedelta(days=case["age_days"]),
        state=FwiState(ffmc=90.0, dmc=80.0, dc=500.0),
        chain_days=99,
    )
    days = [target - timedelta(days=i) for i in range(case["age_days"])]
    reading = NoonObservation(30.0, 25.0, 20.0, 0.0)
    walked = catch_up(
        dict.fromkeys(days, reading),
        target,
        start=start,
        params=STANDARD_PARAMS,
        max_gap_days=case["max_gap_days"],
    )
    discarded = walked[-1].chain_days < 99
    return [
        Result(
            case["id"],
            f"{case['age_days']} days old, limit {case['max_gap_days']}: "
            + ("discarded" if case["discarded"] else "carried on"),
            "pass" if discarded == case["discarded"] else "fail",
            f"chain_days {walked[-1].chain_days}, DC {walked[-1].outputs.state.dc:.1f}",
        )
    ]


KINDS = {
    "against-cffdrs": against_cffdrs,
    "day": day,
    "rain-threshold": rain_threshold,
    "stale-start": stale_start,
}


def run() -> list[Result]:
    cases = tomllib.loads((HERE / "cases.toml").read_text(encoding="utf-8"))["case"]
    return [result for case in cases for result in KINDS[case["kind"]](case)]


def report(results: list[Result]) -> str:
    passed = sum(r.outcome == "pass" for r in results)
    skipped = sum(r.outcome == "skipped" for r in results)
    head = f"fwi-chain: {passed} of {len(results)} checks"
    lines = [head + (f", {skipped} SKIPPED (not passed)" if skipped else "")]
    for r in results:
        mark = {"pass": "✓", "fail": "✗", "skipped": "-"}[r.outcome]
        lines.append(f"  {mark} {r.case:<34} {r.check:<46} {r.got}")
    return "\n".join(lines)


def saved(results: list[Result]) -> dict[str, dict[str, str]]:
    return {
        f"{r.case} · {r.check}": {"outcome": r.outcome, "got": r.got}
        for r in results
        if r.outcome != "skipped"
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--check", action="store_true", help="fail if results differ")
    parser.add_argument("--write", action="store_true", help="save results to results.json")
    parser.add_argument(
        "--require-download",
        action="store_true",
        help="fail, instead of skipping, when the cffdrs series cannot be downloaded",
    )
    args = parser.parse_args(argv)
    results = run()
    print(report(results))
    skipped = {r.case for r in results if r.outcome == "skipped"}
    if skipped:
        print(
            "\nSKIPPED, not passed: the cffdrs series could not be downloaded "
            f"({', '.join(sorted(skipped))}). Run again with the network."
        )
        if args.require_download or args.write:
            return 1
    now = saved(results)
    if args.write:
        RESULTS.write_text(json.dumps(now, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.check:
        before = {
            k: v
            for k, v in json.loads(RESULTS.read_text(encoding="utf-8")).items()
            if k.split(" · ", 1)[0] not in skipped
        }
        if before != now:
            changed = sorted(
                f"{k}: {before.get(k)} -> {v}" for k, v in now.items() if before.get(k) != v
            ) or ["a check was removed"]
            print("\nresults changed (run with --write to accept):", *changed, sep="\n  ")
            return 1
        if any(r.outcome == "fail" for r in results):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
