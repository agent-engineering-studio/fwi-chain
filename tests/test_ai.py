"""Facts, the explanation of a change, the classes and the text check.

The numbers a model may quote come from the chain: these tests hold the facts
to the chain's own outputs, and the check to the faults it is there to find.
"""

from __future__ import annotations

import json
from datetime import date, timedelta
from itertools import pairwise

import pytest

from fwi_chain import (
    EFFIS_FWI_CLASSES,
    STANDARD_PARAMS,
    ChainDay,
    ChainPoint,
    FwiState,
    NoonObservation,
    advance,
    catch_up,
    effis_class,
    explain_change,
    quantiles,
    start_is_stale,
    walk_chain,
)
from fwi_chain.check import Misquote, check_text, facts_of, parse_number
from fwi_chain.facts import RULE, day_facts, distribution_facts, walk_facts

FIRST = date(2026, 7, 1)
DRY = NoonObservation(30.0, 25.0, 20.0, 0.0)
STORM = NoonObservation(24.0, 60.0, 8.0, 12.4)


def span(n: int) -> list[date]:
    return [FIRST + timedelta(days=i) for i in range(n)]


def season() -> list[ChainDay]:
    """Nine dry days, then a storm."""
    days = span(10)
    observations = dict.fromkeys(days[:9], DRY) | {days[9]: STORM}
    return walk_chain(observations, days, start=None, params=STANDARD_PARAMS, max_gap_days=7)


# ---------------------------------------------------------------------------
# start_is_stale / catch_up
# ---------------------------------------------------------------------------
def point(days_before: int) -> ChainPoint:
    return ChainPoint(
        day=FIRST - timedelta(days=days_before),
        state=FwiState(ffmc=90.0, dmc=80.0, dc=500.0),
        chain_days=99,
    )


def test_a_start_is_stale_one_day_past_the_limit() -> None:
    assert not start_is_stale(point(7), FIRST, max_gap_days=7)
    assert start_is_stale(point(8), FIRST, max_gap_days=7)


def test_catch_up_walks_every_day_after_a_start_within_the_limit() -> None:
    days = [FIRST - timedelta(days=i) for i in range(6, -1, -1)]
    got = catch_up(
        dict.fromkeys(days, DRY), FIRST, start=point(7), params=STANDARD_PARAMS, max_gap_days=7
    )
    assert [d.day for d in got] == days
    assert [d.chain_days for d in got] == list(range(100, 107))


@pytest.mark.parametrize("age", [8, 10, 14, 15, 40])
def test_catch_up_discards_a_start_past_the_limit_exactly(age: int) -> None:
    """Between one and two limits old, the trimmed window used to hide the gap."""
    days = [FIRST - timedelta(days=i) for i in range(age, -1, -1)]
    got = catch_up(
        dict.fromkeys(days, DRY), FIRST, start=point(age), params=STANDARD_PARAMS, max_gap_days=7
    )
    assert [(d.day, d.chain_days) for d in got] == [(FIRST, 1)]
    assert got[0].outputs == advance(
        STANDARD_PARAMS.initial_state,
        month=7,
        temperature_c=30.0,
        relative_humidity_pct=25.0,
        wind_speed_kmh=20.0,
        rain_24h_mm=0.0,
        params=STANDARD_PARAMS,
    )


def test_catch_up_from_nothing_walks_the_target_alone() -> None:
    got = catch_up({FIRST: DRY}, FIRST, start=None, params=STANDARD_PARAMS, max_gap_days=7)
    assert [(d.day, d.chain_days) for d in got] == [(FIRST, 1)]


# ---------------------------------------------------------------------------
# effis_class
# ---------------------------------------------------------------------------
def test_the_classes_are_the_ones_effis_publishes() -> None:
    assert EFFIS_FWI_CLASSES == (
        (0.0, "low"),
        (11.2, "moderate"),
        (21.3, "high"),
        (38.0, "very high"),
        (50.0, "extreme"),
        (70.0, "very extreme"),
    )


@pytest.mark.parametrize(
    ("fwi", "name"),
    [
        (0.0, "low"),
        (11.19, "low"),
        (11.2, "moderate"),
        (21.3, "high"),
        (37.99, "high"),
        (38.0, "very high"),
        (50.0, "extreme"),
        (69.9, "extreme"),
        (70.0, "very extreme"),
        (140.0, "very extreme"),
    ],
)
def test_a_boundary_belongs_to_the_class_above(fwi: float, name: str) -> None:
    assert effis_class(fwi) == name


@pytest.mark.parametrize("fwi", [-0.1, float("nan"), float("inf")])
def test_a_number_that_is_not_an_fwi_is_refused(fwi: float) -> None:
    with pytest.raises(ValueError, match="from 0 up"):
        effis_class(fwi)


# ---------------------------------------------------------------------------
# explain_change
# ---------------------------------------------------------------------------
def test_the_explanation_adds_up() -> None:
    walked = season()
    for previous, today in pairwise(walked):
        e = explain_change(previous, today, params=STANDARD_PARAMS)
        assert e.fwi_today == today.outputs.fwi and e.fwi_yesterday == previous.outputs.fwi
        assert e.change == pytest.approx(e.carry_over + e.weather, abs=1e-9)
        assert e.weather == pytest.approx(sum(d.effect for d in e.drivers), abs=1e-9)
        assert sorted(d.input for d in e.drivers) == ["humidity", "rain", "temperature", "wind"]


def test_with_the_same_weather_only_the_memory_moves_the_index() -> None:
    walked = season()
    e = explain_change(walked[3], walked[4], params=STANDARD_PARAMS)
    assert e.weather == 0.0 and all(d.effect == 0.0 for d in e.drivers)
    assert e.carry_over == e.change > 0.0  # still drying


def test_the_storm_is_what_lowered_the_index() -> None:
    walked = season()
    e = explain_change(walked[8], walked[9], params=STANDARD_PARAMS)
    assert e.change < -20.0
    assert e.drivers[0].input == "rain" and e.drivers[0].effect < 0.0
    assert (e.drivers[0].yesterday, e.drivers[0].today) == (0.0, 12.4)
    assert all(d.effect < 0.0 for d in e.drivers)  # cooler, damper, calmer, wetter
    assert abs(e.drivers[0].effect) >= abs(e.drivers[1].effect)


def test_the_explanation_does_not_depend_on_the_order_of_the_readings() -> None:
    """One reading changed alone gets the whole of the weather's share."""
    days = span(2)
    windy = NoonObservation(30.0, 25.0, 45.0, 0.0)
    walked = walk_chain(
        {days[0]: DRY, days[1]: windy}, days, start=None, params=STANDARD_PARAMS, max_gap_days=7
    )
    e = explain_change(walked[0], walked[1], params=STANDARD_PARAMS)
    by = {d.input: d.effect for d in e.drivers}
    assert by["wind"] == pytest.approx(e.weather) and by["wind"] > 0.0
    assert by["rain"] == by["humidity"] == by["temperature"] == 0.0


# ---------------------------------------------------------------------------
# facts
# ---------------------------------------------------------------------------
def test_day_facts_are_the_chain_rounded_to_one_decimal() -> None:
    walked = season()
    f = day_facts(walked[9], previous=walked[8], params=STANDARD_PARAMS, spinup_days=30)
    o = walked[9].outputs
    assert f["day"] == "2026-07-10"
    assert f["codes"] == {
        "ffmc": round(o.state.ffmc, 1),
        "dmc": round(o.state.dmc, 1),
        "dc": round(o.state.dc, 1),
        "isi": round(o.isi, 1),
        "bui": round(o.bui, 1),
        "fwi": round(o.fwi, 1),
    }
    assert f["observation"] == {
        "temperature_c": 24.0,
        "relative_humidity_pct": 60.0,
        "wind_speed_kmh": 8.0,
        "rain_24h_mm": 12.4,
    }
    assert f["effis_class"] == effis_class(o.fwi) == "low"
    assert f["chain_days"] == 10 and f["settled"] is False and f["spinup_days"] == 30
    assert f["rule"] == RULE and "not an alert" in RULE
    change = f["change"]
    assert change["previous_day"] == "2026-07-09"
    assert change["fwi_previous"] == round(walked[8].outputs.fwi, 1)
    assert change["drivers"][0] == {
        "input": "rain",
        "previous_mm": 0.0,
        "today_mm": 12.4,
        "effect": change["drivers"][0]["effect"],
    }
    assert {tuple(d)[1] for d in change["drivers"]} == {
        "previous_mm",
        "previous_kmh",
        "previous_pct",
        "previous_c",
    }
    json.dumps(f)  # JSON-ready


def test_day_facts_alone_have_no_change_and_no_climatology() -> None:
    f = day_facts(season()[0])
    assert "change" not in f and "climatology" not in f and "settled" not in f


def test_what_moved_the_index_needs_the_params() -> None:
    walked = season()
    with pytest.raises(ValueError, match="needs the params"):
        day_facts(walked[1], previous=walked[0])


def test_day_facts_place_the_fwi_in_its_month() -> None:
    walked = season()
    q = quantiles([float(v) for v in range(101)])
    f = day_facts(walked[8], month_quantiles=q)
    fwi = walked[8].outputs.fwi
    assert f["climatology"] == {
        "percentile": round(fwi, 1),
        "median_fwi": 50.0,
        "p90_fwi": 90.0,
        "quantile_levels": [50, 90],
        "month": 7,
    }


def test_walk_facts_sum_up_the_stretch() -> None:
    walked = season()
    q = {7: quantiles([float(v) for v in range(101)])}
    f = walk_facts(walked, params=STANDARD_PARAMS, quantiles_by_month=q, spinup_days=5)
    peak = max(walked, key=lambda d: d.outputs.fwi)
    assert (f["first_day"], f["last_day"], f["walked_days"]) == ("2026-07-01", "2026-07-10", 10)
    assert f["rain_total_mm"] == 12.4
    assert f["peak"] == {
        "day": peak.day.isoformat(),
        "fwi": round(peak.outputs.fwi, 1),
        "effis_class": effis_class(peak.outputs.fwi),
    }
    assert sum(f["class_days"].values()) == 10
    assert [row["day"] for row in f["series"]] == [d.day.isoformat() for d in walked]
    assert f["series"][-1]["rain_24h_mm"] == 12.4
    assert f["last"]["change"]["drivers"][0]["input"] == "rain"
    assert f["last"]["settled"] is True and "climatology" in f["last"]
    json.dumps(f)


def test_a_single_walked_day_has_no_change() -> None:
    f = walk_facts(season()[:1], params=STANDARD_PARAMS)
    assert "change" not in f["last"] and "climatology" not in f["last"]


def test_no_walked_day_is_not_no_danger() -> None:
    with pytest.raises(ValueError, match="no day was walked"):
        walk_facts([], params=STANDARD_PARAMS)


def test_distribution_facts() -> None:
    values = [float(v) for v in range(101)]
    f = distribution_facts(values, value=92.5)
    assert f["values"] == 101 and len(f["quantiles"]) == 21
    assert (f["median_fwi"], f["p90_fwi"], f["max_fwi"]) == (50.0, 90.0, 100.0)
    assert (f["fwi"], f["percentile"], f["effis_class"]) == (92.5, 92.5, "very extreme")
    assert "percentile" not in distribution_facts(values)
    with pytest.raises(ValueError):
        distribution_facts([])


# ---------------------------------------------------------------------------
# check_text
# ---------------------------------------------------------------------------
def storm_facts() -> dict[str, object]:
    walked = season()
    return day_facts(walked[9], previous=walked[8], params=STANDARD_PARAMS)


def test_a_faithful_text_has_no_misquote() -> None:
    f = storm_facts()
    codes = f["codes"]
    assert isinstance(codes, dict)
    text = (
        f"On 10 July 2026 the FWI fell to {codes['fwi']}, class low, after 12.4 mm of rain "
        f"in 24 hours with 24 °C, 60 % humidity and wind at 8 km/h. "
        f"The drought code is {codes['dc']:.0f}."
    )
    assert check_text(text, f, question="What happened in the last 24 hours?") == []


def test_the_three_faults() -> None:
    f = storm_facts()
    found = check_text("It rained 12.4 % and 12.5 mm, with gusts of 77 km/h.", f)
    assert [(m.text, m.fault) for m in found] == [
        ("12.4 %", "unit"),
        ("12.5 mm", "rounded"),
        ("77 km/h", "invented"),
    ]
    assert found[0] == Misquote("12.4 %", "pct", "unit", found[0].nearest)
    assert found[0].nearest is not None and "12.4 mm" in found[0].nearest


def test_a_code_has_no_unit() -> None:
    f = storm_facts()
    codes = f["codes"]
    assert isinstance(codes, dict)
    (m,) = check_text(f"The FWI is {codes['dc']} mm.", f)
    assert m.fault == "unit"


def test_numbers_in_the_question_dates_and_italian_are_let_through() -> None:
    f = storm_facts()
    text = "Il 10/07/2026 alle 12:00 sono caduti 12,4 mm; la domanda chiedeva di 3 scenari."
    assert check_text(text, f, question="Confronta 3 scenari") == []


def test_facts_of_walks_the_whole_structure() -> None:
    found = {path: (value, unit) for path, value, unit in facts_of(storm_facts())}
    assert found["observation.rain_24h_mm"] == (12.4, "mm")
    assert found["observation.temperature_c"] == (24.0, "c")
    assert found["chain_days"] == (10.0, "days")
    assert found["change.drivers.0.today_mm"] == (12.4, "mm")
    assert found["codes.fwi"][1] is None
    assert "effis_class" not in found  # a word, not a number


def test_numbers_as_people_write_them() -> None:
    assert parse_number("1,603") == (1603.0, 0)
    assert parse_number("2,5") == (2.5, 1)
    assert parse_number("1.603,5") == (1603.5, 1)
    assert parse_number("−3.2") == (-3.2, 1)
    assert check_text("about 500", {"dc": 512.0}) == []
    assert [m.fault for m in check_text("about 600", {"dc": 512.0})] == ["invented"]
