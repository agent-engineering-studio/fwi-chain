"""Parity with Limen, where the chain walk and the climatology came from.

``tests/fixtures/limen_parity.json`` holds fixed inputs and what **Limen's
own functions** returned for them (``scripts/limen_parity.py`` produced it,
from the Limen commit recorded in the file). Each test feeds the same inputs
to this library and expects the same answer.

Limen's ``advance_node``, ``ricalcola``, ``correggi``, ``accumula``,
``copertura_valida``, ``quantili``, ``percentile`` and ``tetto_del_nodo`` were
called directly. ``days_to_walk`` and ``writable_days`` have no callable
counterpart there: the fixture holds the result of the two expressions copied
out of ``FwiUpdateExecutor.run``.

Floats are compared to 1e-12 relative, not bit for bit: the fixture was
written on one machine and ``math.exp`` may differ in the last place on
another.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest

from fwi_chain import (
    QUANTILE_LEVELS,
    ChainDay,
    ChainPoint,
    FwiOutputs,
    FwiParams,
    FwiState,
    NoonObservation,
    accumulate_monthly,
    correct_rain,
    coverage_is_valid,
    days_to_walk,
    node_ceiling,
    percentile,
    quantiles,
    rewalk_with_rain,
    walk_chain,
    writable_days,
)

FIXTURE: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "limen_parity.json").read_text(encoding="utf-8")
)
PARAMS = {
    name: FwiParams(
        ffmc_start=p["ffmc_start"],
        dmc_start=p["dmc_start"],
        dc_start=p["dc_start"],
        day_length_dmc=tuple(p["day_length_dmc"]),
        day_length_dc=tuple(p["day_length_dc"]),
    )
    for name, p in FIXTURE["params"].items()
}


def close(value: Any) -> Any:
    return pytest.approx(value, rel=1e-12, abs=1e-12)


def cases(key: str) -> list[Any]:
    return [pytest.param(c, id=c["name"]) for c in FIXTURE[key]]


def observation(w: list[float]) -> NoonObservation:
    return NoonObservation(
        temperature_c=w[0], relative_humidity_pct=w[1], wind_speed_kmh=w[2], rain_24h_mm=w[3]
    )


def observations(by_day: dict[str, list[float]]) -> dict[date, NoonObservation]:
    return {date.fromisoformat(d): observation(w) for d, w in by_day.items()}


def chain_day(row: dict[str, Any]) -> ChainDay:
    return ChainDay(
        day=date.fromisoformat(row["day"]),
        outputs=FwiOutputs(
            state=FwiState(ffmc=row["ffmc"], dmc=row["dmc"], dc=row["dc"]),
            isi=row["isi"],
            bui=row["bui"],
            fwi=row["fwi"],
        ),
        chain_days=row["chain_days"],
        observation=observation(row["observation"]),
    )


def rain(by_day: dict[str, float | None]) -> dict[date, float | None]:
    return {date.fromisoformat(d): v for d, v in by_day.items()}


def assert_same_rows(got: list[ChainDay], expected: list[dict[str, Any]]) -> None:
    assert [g.day.isoformat() for g in got] == [e["day"] for e in expected]
    for g, e in zip(got, expected, strict=True):
        assert g.chain_days == e["chain_days"], e["day"]
        assert [
            g.outputs.state.ffmc,
            g.outputs.state.dmc,
            g.outputs.state.dc,
            g.outputs.isi,
            g.outputs.bui,
            g.outputs.fwi,
        ] == close([e["ffmc"], e["dmc"], e["dc"], e["isi"], e["bui"], e["fwi"]]), e["day"]
        assert [
            g.observation.temperature_c,
            g.observation.relative_humidity_pct,
            g.observation.wind_speed_kmh,
            g.observation.rain_24h_mm,
        ] == e["observation"], e["day"]


def test_the_fixture_names_the_limen_commit_it_came_from() -> None:
    assert FIXTURE["limen_commit"]


# ---------------------------------------------------------------------------
# advance_node
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("case", cases("walk"))
def test_walk_chain_matches_advance_node(case: dict[str, Any]) -> None:
    start = case["start"]
    got = walk_chain(
        observations(case["observations"]),
        [date.fromisoformat(d) for d in case["days"]],
        start=None
        if start is None
        else ChainPoint(
            day=date.fromisoformat(start["day"]),
            state=FwiState(ffmc=start["ffmc"], dmc=start["dmc"], dc=start["dc"]),
            chain_days=start["chain_days"],
        ),
        params=PARAMS[case["params"]],
        max_gap_days=case["max_gap_days"],
    )
    assert_same_rows(got, case["expected"])


@pytest.mark.parametrize("case", FIXTURE["days_to_walk_transcribed"])
def test_days_to_walk_matches_the_sweep(case: dict[str, Any]) -> None:
    last = case["last_day"]
    got = days_to_walk(
        date.fromisoformat(case["target"]),
        last_day=None if last is None else date.fromisoformat(last),
        max_gap_days=case["max_gap_days"],
    )
    assert [d.isoformat() for d in got] == case["expected"]


@pytest.mark.parametrize("case", FIXTURE["writable_transcribed"])
def test_writable_days_matches_the_sweep(case: dict[str, Any]) -> None:
    walk = next(w for w in FIXTURE["walk"] if w["name"] == case["walk"])
    walked = [chain_day(row) for row in walk["expected"]]
    got = writable_days(walked, today=date.fromisoformat(case["today"]))
    assert [d.day.isoformat() for d in got] == case["expected"]


# ---------------------------------------------------------------------------
# ricalcola / correggi
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("case", cases("rewalk"))
def test_rewalk_with_rain_matches_ricalcola(case: dict[str, Any]) -> None:
    got = rewalk_with_rain(
        [chain_day(row) for row in case["rows"]],
        chain_day(case["start"]).point,
        rain(case["rain"]),
        params=PARAMS[case["params"]],
        max_gap_days=case["max_gap_days"],
    )
    assert_same_rows(got, case["expected"])


@pytest.mark.parametrize("case", cases("correct"))
def test_correct_rain_matches_correggi(case: dict[str, Any]) -> None:
    weather = case["weather"]
    got = correct_rain(
        [chain_day(row) for row in case["series"]],
        since=date.fromisoformat(case["since"]),
        rain=rain(case["rain"]),
        params=PARAMS[case["params"]],
        max_gap_days=case["max_gap_days"],
        weather=None if weather is None else observations(weather),
    )
    assert_same_rows(got, case["expected"])


# ---------------------------------------------------------------------------
# climatology
# ---------------------------------------------------------------------------
CLIMATOLOGY: dict[str, Any] = FIXTURE["climatology"]
QUANTILES = {c["name"]: c["expected"] for c in CLIMATOLOGY["quantiles"]}


def test_quantile_levels_match_livelli() -> None:
    assert list(QUANTILE_LEVELS) == CLIMATOLOGY["levels"]


@pytest.mark.parametrize("case", [pytest.param(c, id=c["name"]) for c in CLIMATOLOGY["quantiles"]])
def test_quantiles_match_quantili(case: dict[str, Any]) -> None:
    assert quantiles(case["values"]) == close(case["expected"])


@pytest.mark.parametrize("name", sorted(QUANTILES))
def test_percentile_matches_limen(name: str) -> None:
    probes = [c for c in CLIMATOLOGY["percentiles"] if c["quantiles"] == name]
    assert probes
    for case in probes:
        assert percentile(case["value"], QUANTILES[name]) == close(case["expected"]), case["value"]


@pytest.mark.parametrize("case", CLIMATOLOGY["ceilings"])
def test_node_ceiling_matches_tetto_del_nodo(case: dict[str, Any]) -> None:
    per_month = {int(m): q for m, q in CLIMATOLOGY["ceiling_per_month"].items()}
    got = node_ceiling(
        per_month,
        quantile=case["quantile"],
        months=case["months"],
        minimum=case["minimum"],
        maximum=case["maximum"],
    )
    if case["expected"] is None:
        assert got is None
    else:
        assert got == close(case["expected"])


@pytest.mark.parametrize("case", cases("accumulate"))
def test_accumulate_monthly_matches_accumula(case: dict[str, Any]) -> None:
    params = PARAMS[case["params"]]
    by_day = observations(case["observations"])
    per_month: dict[int, list[float]] = {}
    state, days_walked = params.initial_state, 0
    for step in case["steps"]:
        state, days_walked = accumulate_monthly(
            by_day,
            [date.fromisoformat(d) for d in step["days"]],
            per_month,
            state=state,
            days_walked=days_walked,
            params=params,
            spinup_days=case["spinup_days"],
        )
        assert [state.ffmc, state.dmc, state.dc] == close(step["state"])
        assert days_walked == step["days_walked"]
    assert sorted(per_month) == sorted(int(m) for m in case["per_month"])
    for month, values in case["per_month"].items():
        assert per_month[int(month)] == close(values), month


@pytest.mark.parametrize("case", cases("coverage"))
def test_coverage_is_valid_matches_copertura_valida(case: dict[str, Any]) -> None:
    first, last = (date.fromisoformat(d) for d in case["days"])
    days = [first + timedelta(days=i) for i in range((last - first).days + 1)]
    missing = set(case["missing"])
    observed = [d for i, d in enumerate(days) if i not in missing]
    got = coverage_is_valid(observed, days, max_gap_days=case["max_gap_days"])
    assert got is case["expected"]
