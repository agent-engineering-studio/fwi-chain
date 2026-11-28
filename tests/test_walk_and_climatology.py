"""What the chain walk and the climatology promise, beyond matching Limen.

``test_limen_parity.py`` pins the numbers. These check the properties a
caller relies on, and the edges the parity fixture has no reason to visit.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from fwi_chain import (
    QUANTILE_LEVELS,
    STANDARD_PARAMS,
    ChainDay,
    ChainPoint,
    FwiState,
    NoonObservation,
    accumulate_monthly,
    advance,
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

DRY = NoonObservation(
    temperature_c=30.0, relative_humidity_pct=25.0, wind_speed_kmh=20.0, rain_24h_mm=0.0
)
FIRST = date(2026, 7, 1)


def span(n: int, first: date = FIRST) -> list[date]:
    return [first + timedelta(days=i) for i in range(n)]


def walk(n: int = 10) -> list[ChainDay]:
    days = span(n)
    return walk_chain(
        dict.fromkeys(days, DRY), days, start=None, params=STANDARD_PARAMS, max_gap_days=7
    )


# ---------------------------------------------------------------------------
# walk_chain
# ---------------------------------------------------------------------------
def test_one_walked_day_is_one_advance() -> None:
    (day,) = walk(1)
    assert day.outputs == advance(
        STANDARD_PARAMS.initial_state,
        month=7,
        temperature_c=30.0,
        relative_humidity_pct=25.0,
        wind_speed_kmh=20.0,
        rain_24h_mm=0.0,
        params=STANDARD_PARAMS,
    )
    assert day.chain_days == 1
    assert day.observation is DRY


def test_walking_in_two_runs_is_walking_in_one() -> None:
    whole = walk(10)
    days = span(10)
    obs = dict.fromkeys(days, DRY)
    head = walk_chain(obs, days[:4], start=None, params=STANDARD_PARAMS, max_gap_days=7)
    tail = walk_chain(obs, days[4:], start=head[-1].point, params=STANDARD_PARAMS, max_gap_days=7)
    assert head + tail == whole


def test_no_days_is_no_walk() -> None:
    assert walk_chain({}, [], start=None, params=STANDARD_PARAMS, max_gap_days=7) == []


def test_a_start_too_old_restarts_the_count() -> None:
    old = ChainPoint(
        day=FIRST - timedelta(days=8), state=FwiState(ffmc=90, dmc=80, dc=500), chain_days=99
    )
    days = span(2)
    got = walk_chain(
        dict.fromkeys(days, DRY), days, start=old, params=STANDARD_PARAMS, max_gap_days=7
    )
    assert [d.chain_days for d in got] == [1, 2]
    assert got == walk(2)


# ---------------------------------------------------------------------------
# days_to_walk / writable_days
# ---------------------------------------------------------------------------
def test_days_to_walk_starts_the_day_after_the_stored_one() -> None:
    target = date(2026, 7, 10)
    assert days_to_walk(target, last_day=date(2026, 7, 7), max_gap_days=7) == [
        date(2026, 7, 8),
        date(2026, 7, 9),
        target,
    ]
    assert days_to_walk(target, last_day=None, max_gap_days=7) == [target]
    assert days_to_walk(target, last_day=target, max_gap_days=7) == []


def test_a_forecast_day_is_never_writable() -> None:
    walked = walk(5)
    today = walked[2].day
    assert writable_days(walked, today=today) == walked[:3]
    assert writable_days(walked, today=FIRST - timedelta(days=1)) == []


# ---------------------------------------------------------------------------
# rewalk_with_rain / correct_rain
# ---------------------------------------------------------------------------
def test_rewalking_with_no_rain_changes_nothing() -> None:
    walked = walk(10)
    again = rewalk_with_rain(
        walked[1:], walked[0].point, {}, params=STANDARD_PARAMS, max_gap_days=7
    )
    assert again == walked[1:]


def test_measured_rain_lowers_the_codes_and_the_days_after_follow() -> None:
    walked = walk(10)
    wet = walked[4].day
    again = rewalk_with_rain(
        walked[1:], walked[0].point, {wet: 25.0}, params=STANDARD_PARAMS, max_gap_days=7
    )
    assert again[:3] == walked[1:4]
    assert again[3].observation.rain_24h_mm == 25.0
    assert again[3].observation.temperature_c == DRY.temperature_c
    for new, old in zip(again[3:], walked[4:], strict=True):
        assert new.outputs.state.dc < old.outputs.state.dc
        assert new.outputs.fwi < old.outputs.fwi


def test_a_hole_in_the_measurement_is_not_a_dry_day() -> None:
    days = span(3)
    rainy = NoonObservation(
        temperature_c=20.0, relative_humidity_pct=60.0, wind_speed_kmh=10.0, rain_24h_mm=12.0
    )
    walked = walk_chain(
        dict.fromkeys(days, rainy), days, start=None, params=STANDARD_PARAMS, max_gap_days=7
    )
    again = rewalk_with_rain(
        walked[1:], walked[0].point, {days[1]: None}, params=STANDARD_PARAMS, max_gap_days=7
    )
    assert again == walked[1:]


def test_correcting_twice_gives_the_same_rows() -> None:
    walked = walk(10)
    since = walked[5].day
    rain = {walked[6].day: 18.0}

    def corrected(series: list[ChainDay]) -> list[ChainDay]:
        return correct_rain(series, since=since, rain=rain, params=STANDARD_PARAMS, max_gap_days=7)

    once = corrected(walked)
    assert [d.day for d in once] == [d.day for d in walked[5:]]
    assert corrected(walked[:5] + once) == once


def test_correcting_an_empty_series_is_empty() -> None:
    assert correct_rain([], since=FIRST, rain={}, params=STANDARD_PARAMS, max_gap_days=7) == []


# ---------------------------------------------------------------------------
# climatology
# ---------------------------------------------------------------------------
def test_quantiles_run_from_the_minimum_to_the_maximum() -> None:
    values = [float(v) for v in range(101)]
    q = quantiles(values)
    assert q == pytest.approx(list(QUANTILE_LEVELS))
    assert quantiles(list(reversed(values))) == q


def test_quantiles_need_values() -> None:
    with pytest.raises(ValueError, match="needs values"):
        quantiles([])


def test_percentile_inverts_quantiles() -> None:
    q = quantiles([float(v) for v in range(101)])
    assert percentile(-1.0, q) == 0.0
    assert percentile(37.5, q) == pytest.approx(37.5)
    assert percentile(101.0, q) == 100.0


def test_percentile_takes_the_centre_of_a_flat_stretch() -> None:
    q = quantiles([0.0] * 60 + [float(v) for v in range(1, 41)])
    # Quantiles 0 to 55 are all zero: zero is the middle of them, not the minimum.
    assert percentile(0.0, q) == 27.5
    assert percentile(7.0, [7.0] * 21) == 50.0


def test_percentile_wants_twenty_one_quantiles() -> None:
    with pytest.raises(ValueError, match="expected 21 quantiles, got 3"):
        percentile(1.0, [0.0, 1.0, 2.0])


def test_node_ceiling_is_clamped_and_optional() -> None:
    low, high = [1.0] * 21, [80.0] * 21
    kwargs = {"quantile": 90.0, "minimum": 15.0, "maximum": 50.0}
    assert node_ceiling({7: low}, months=(7,), **kwargs) == 15.0
    assert node_ceiling({7: high}, months=(7,), **kwargs) == 50.0
    assert node_ceiling({7: [20.0] * 21, 8: [30.0] * 21}, months=(7, 8), **kwargs) == 25.0
    assert node_ceiling({7: low}, months=(1, 2), **kwargs) is None
    with pytest.raises(ValueError):
        node_ceiling({7: low}, months=(7,), quantile=92.0, minimum=15.0, maximum=50.0)


def test_spinup_days_move_the_chain_but_stay_out_of_the_distribution() -> None:
    days = span(10)
    per_month: dict[int, list[float]] = {}
    state, walked = accumulate_monthly(
        dict.fromkeys(days, DRY),
        days,
        per_month,
        state=STANDARD_PARAMS.initial_state,
        days_walked=0,
        params=STANDARD_PARAMS,
        spinup_days=6,
    )
    chain = walk(10)
    assert walked == 10
    assert state == chain[-1].outputs.state
    assert per_month == {7: [d.outputs.fwi for d in chain[6:]]}


def test_coverage_counts_the_fraction_and_the_longest_hole() -> None:
    days = span(100)
    assert coverage_is_valid(days, days, max_gap_days=7)
    assert coverage_is_valid(days[:50] + days[53:], days, max_gap_days=7)
    assert not coverage_is_valid(days[:50] + days[53:], days, max_gap_days=2)
    assert not coverage_is_valid(days[:90], days, max_gap_days=30)
    assert coverage_is_valid(days[:90], days, max_gap_days=30, min_fraction=0.9)
