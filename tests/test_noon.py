"""The noon reading from hourly weather.

Two layers. Parity: with nothing refused (any hour of the day, any number of
rain hours) the reading is the one Limen's ``MeteoSnapshot.noon_observation``
gave, on the fixture ``scripts/limen_noon_parity.py`` wrote from Limen's own
code. Then the stated differences: what Limen read without saying, this
function counts, and refuses when asked to.
"""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from fwi_chain import HourlySample, NoonObservation, NoonReading, noon_reading, noon_readings

FIXTURE: dict[str, Any] = json.loads(
    (Path(__file__).parent / "fixtures" / "limen_noon_parity.json").read_text(encoding="utf-8")
)
CASES = {c["name"]: c for c in FIXTURE["cases"]}


def samples_of(case: dict[str, Any]) -> list[HourlySample]:
    return [
        HourlySample(datetime.fromisoformat(t), temp, rh, wind, rain)
        for t, temp, rh, wind, rain in case["samples"]
    ]


def as_limen(case: dict[str, Any], day: str) -> NoonReading:
    """Nothing refused: what Limen did."""
    return noon_reading(
        samples_of(case),
        date.fromisoformat(day),
        noon_hour=case["noon_hour"],
        max_hours_from_noon=None,
        min_rain_hours=0,
    )


# ---------------------------------------------------------------------------
# Parity with Limen
# ---------------------------------------------------------------------------
def test_the_fixture_names_the_limen_commit_it_came_from() -> None:
    assert FIXTURE["limen_commit"]


@pytest.mark.parametrize("name", sorted(CASES))
def test_with_nothing_refused_the_reading_is_limens(name: str) -> None:
    case = CASES[name]
    for day, expected in case["expected"].items():
        got = as_limen(case, day).observation
        if expected is None:
            assert got is None, day
            continue
        assert got is not None, day
        assert [
            got.temperature_c,
            got.relative_humidity_pct,
            got.wind_speed_kmh,
            got.rain_24h_mm,
        ] == pytest.approx(expected, rel=1e-12, abs=1e-12), day


@pytest.mark.parametrize("name", sorted(n for n, c in CASES.items() if not c["gaps"]))
def test_with_no_gap_a_strict_reading_is_limens_too(name: str) -> None:
    """Where every hour is measured, asking for noon itself and 24 hours changes nothing."""
    case = CASES[name]
    for day in list(case["expected"])[1:]:  # the first day has no 24 hours before it
        strict = noon_reading(
            samples_of(case),
            date.fromisoformat(day),
            noon_hour=case["noon_hour"],
            max_hours_from_noon=0,
            min_rain_hours=24,
        )
        assert strict.refused is None
        assert strict.observation == as_limen(case, day).observation
        assert (strict.hours_from_noon, strict.rain_hours_missing) == (0, 0)


@pytest.mark.parametrize("name", sorted(CASES))
def test_noon_readings_is_noon_reading_day_by_day(name: str) -> None:
    case = CASES[name]
    days = [date.fromisoformat(d) for d in case["expected"]]
    for limits in (
        {"max_hours_from_noon": None, "min_rain_hours": 0},
        {
            "max_hours_from_noon": 2,
            "min_rain_hours": 20,
        },
    ):
        together = noon_readings(samples_of(case), days, noon_hour=case["noon_hour"], **limits)
        assert list(together) == days
        for day in days:
            alone = noon_reading(samples_of(case), day, noon_hour=case["noon_hour"], **limits)
            assert together[day] == alone


# ---------------------------------------------------------------------------
# Where Limen guessed: counted here, and refused when asked
# ---------------------------------------------------------------------------
def test_a_reading_far_from_noon_is_counted_and_can_be_refused() -> None:
    """Hours 6 to 20 of 1 September have no wind: Limen read 05:00 as noon."""
    case = CASES["noon hour missing: the nearest hour is read"]
    loose = as_limen(case, "2026-09-01")
    assert loose.observation is not None
    assert loose.time == datetime(2026, 9, 1, 5, tzinfo=UTC)
    assert loose.hours_from_noon == 6

    strict = noon_reading(
        samples_of(case),
        date(2026, 9, 1),
        noon_hour=11,
        max_hours_from_noon=2,
        min_rain_hours=0,
    )
    assert strict.observation is None and strict.refused == "too far from noon"
    assert strict.hours_from_noon == 6  # still said

    one_hour_off = noon_reading(
        samples_of(case),
        date(2026, 8, 31),
        noon_hour=11,
        max_hours_from_noon=2,
        min_rain_hours=0,
    )
    assert one_hour_off.observation is not None and one_hour_off.hours_from_noon == 1


def test_on_a_tie_the_earlier_hour_is_read() -> None:
    case = CASES["two hours equally near: the earlier one"]
    reading = as_limen(case, "2026-08-31")
    assert reading.time == datetime(2026, 8, 31, 9, tzinfo=UTC)
    assert reading.hours_from_noon == 2


def test_a_day_with_no_reading_says_so() -> None:
    case = CASES["noon hour missing: the nearest hour is read"]
    reading = as_limen(case, "2026-09-02")
    assert reading == NoonReading(day=date(2026, 9, 2), observation=None, refused="no reading")
    assert (reading.rain_hours, reading.rain_hours_missing) == (0, 24)


def test_hours_of_rain_not_measured_are_counted_and_can_be_refused() -> None:
    """Six hours are null before the noon of 31 August; ten are gone before 1 September."""
    case = CASES["hours of rain not measured"]
    for day, missing in (("2026-08-31", 6), ("2026-09-01", 10)):
        loose = as_limen(case, day)
        assert loose.observation is not None  # Limen summed what was there
        assert loose.rain_hours_missing == missing and loose.rain_hours == 24 - missing
        assert loose.rain_measured_mm == loose.observation.rain_24h_mm

        strict = noon_reading(
            samples_of(case),
            date.fromisoformat(day),
            noon_hour=11,
            max_hours_from_noon=None,
            min_rain_hours=20,
        )
        assert strict.observation is None and strict.refused == "too few hours of rain"
        assert strict.rain_hours_missing == missing
        assert strict.rain_measured_mm == loose.rain_measured_mm  # a lower bound, still said


def test_the_first_day_of_a_series_lacks_the_hours_before_it() -> None:
    """Noon at 11 on the first day has 12 hours behind it (00:00 to 11:00), not 24."""
    case = CASES["every hour measured, noon at 11"]
    reading = as_limen(case, "2026-08-30")
    assert reading.observation is not None
    assert (reading.rain_hours, reading.rain_hours_missing) == (12, 12)


def test_a_dry_hour_is_measured_and_a_null_hour_is_not() -> None:
    noon = datetime(2026, 7, 2, 12)
    hours = [noon - timedelta(hours=h) for h in range(24)]
    dry = [HourlySample(t, 30.0, 25.0, 20.0, 0.0) for t in hours]
    unknown = [HourlySample(t, 30.0, 25.0, 20.0, None) for t in hours]
    limits = {"noon_hour": 12, "max_hours_from_noon": 0, "min_rain_hours": 24}
    measured = noon_reading(dry, date(2026, 7, 2), **limits)
    assert measured.observation == NoonObservation(30.0, 25.0, 20.0, 0.0)
    assert measured.rain_hours_missing == 0
    missing = noon_reading(unknown, date(2026, 7, 2), **limits)
    assert missing.observation is None and missing.rain_hours_missing == 24


def test_the_rain_window_ends_at_the_hour_read_and_excludes_the_same_hour_a_day_before() -> None:
    noon = datetime(2026, 7, 2, 12)
    samples = [
        HourlySample(noon - timedelta(hours=24), rain_mm=100.0),  # outside: a day before
        HourlySample(noon - timedelta(hours=23), rain_mm=1.5),
        HourlySample(noon, 30.0, 25.0, 20.0, 2.0),
        HourlySample(noon + timedelta(hours=1), rain_mm=50.0),  # outside: after
    ]
    reading = noon_reading(
        samples, date(2026, 7, 2), noon_hour=12, max_hours_from_noon=0, min_rain_hours=0
    )
    assert reading.observation is not None and reading.observation.rain_24h_mm == 3.5
    assert reading.rain_hours == 2


@pytest.mark.parametrize(
    "limits",
    [
        {"noon_hour": 24, "max_hours_from_noon": None, "min_rain_hours": 0},
        {"noon_hour": 11, "max_hours_from_noon": -1, "min_rain_hours": 0},
        {"noon_hour": 11, "max_hours_from_noon": None, "min_rain_hours": 25},
    ],
)
def test_limits_that_make_no_sense_are_refused(limits: dict[str, Any]) -> None:
    with pytest.raises(ValueError, match="must be"):
        noon_reading([], date(2026, 7, 2), **limits)
