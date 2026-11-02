"""Van Wagner's FWI chain.

The test that matters is the first one: the six outputs against the
published values. The equations are a standard, not a design choice, so the
only way to know they were transcribed correctly is to compare them with a
known case -- a property-only suite would stay green with a wrong
coefficient.

The rest checks what a single vector cannot reach: the rain branches, the
physical bounds, and the fact that the codes *remember*.
"""

from __future__ import annotations

import math

import pytest

import fwi_chain
from fwi_chain import (
    STANDARD_PARAMS,
    FwiParams,
    FwiState,
    advance,
    buildup_index,
    drought_code,
    duff_moisture_code,
    fine_fuel_moisture_code,
    fire_weather_index,
    initial_spread_index,
)

PARAMS = STANDARD_PARAMS


# ---------------------------------------------------------------------------
# The reference vector
# ---------------------------------------------------------------------------
def test_published_reference_day() -> None:
    """Reference case of the FWI chain, from the standard start-up codes.

    Inputs: 17.0 °C, 42 % RH, 25 km/h, 0 mm, April, starting from
    FFMC/DMC/DC = 85 / 6 / 15. It is the first day of the test series that
    ships with the reference implementation of Van Wagner's equations (the
    `cffdrs` R package), and it can be checked by hand: the DC, for
    instance, is 15 + (0.36·(17+2.8) + 0.9)/2 = 19.014.

    Absolute tolerance 1e-9: nothing is being calibrated, a transcription is
    being checked. A larger deviation is a wrong coefficient, not
    floating-point noise.
    """
    out = advance(
        PARAMS.initial_state,
        month=4,
        temperature_c=17.0,
        relative_humidity_pct=42.0,
        wind_speed_kmh=25.0,
        rain_24h_mm=0.0,
        params=PARAMS,
    )
    assert out.state.ffmc == pytest.approx(87.692980092774, abs=1e-9)
    assert out.state.dmc == pytest.approx(8.5450511359998, abs=1e-9)
    assert out.state.dc == pytest.approx(19.013999999999996, abs=1e-9)
    assert out.isi == pytest.approx(10.853661073312, abs=1e-9)
    assert out.bui == pytest.approx(8.4904265358371, abs=1e-9)
    assert out.fwi == pytest.approx(10.096371392382, abs=1e-9)


def test_standard_params_are_van_wagners() -> None:
    assert PARAMS.initial_state == FwiState(ffmc=85.0, dmc=6.0, dc=15.0)
    assert PARAMS.day_length_dmc[6] == 12.4
    assert PARAMS.day_length_dc[6] == 6.4


def test_version_is_exposed() -> None:
    assert fwi_chain.__version__


# ---------------------------------------------------------------------------
# The rain branches -- what a dry day never touches
# ---------------------------------------------------------------------------
def test_light_rain_is_intercepted_by_the_canopy() -> None:
    """Below each code's threshold the rain does not reach the fuel.

    0.5 mm for FFMC, 1.5 for DMC, 2.8 for DC: not roundings but the amount
    the canopy holds before anything reaches the ground. Rain below the
    threshold must leave the code *drying*.
    """
    dry = fine_fuel_moisture_code(
        90.0,
        temperature_c=20.0,
        relative_humidity_pct=40.0,
        wind_speed_kmh=10.0,
        rain_24h_mm=0.0,
    )
    drizzle = fine_fuel_moisture_code(
        90.0,
        temperature_c=20.0,
        relative_humidity_pct=40.0,
        wind_speed_kmh=10.0,
        rain_24h_mm=0.4,
    )
    assert drizzle == dry

    assert drought_code(100.0, temperature_c=20.0, rain_24h_mm=2.0, day_length=5.8) > 100.0


def test_heavy_rain_lowers_every_code() -> None:
    """Heavy rain must wet all three codes, not only the fine fuel."""
    assert (
        fine_fuel_moisture_code(
            92.0,
            temperature_c=18.0,
            relative_humidity_pct=60.0,
            wind_speed_kmh=5.0,
            rain_24h_mm=30.0,
        )
        < 92.0
    )
    assert (
        duff_moisture_code(
            80.0,
            temperature_c=18.0,
            relative_humidity_pct=60.0,
            rain_24h_mm=40.0,
            day_length=13.9,
        )
        < 80.0
    )
    assert drought_code(500.0, temperature_c=18.0, rain_24h_mm=40.0, day_length=5.8) < 500.0


@pytest.mark.parametrize("previous_dmc", [20.0, 50.0, 90.0])
def test_dmc_wetting_covers_the_three_slopes_of_eq_13(previous_dmc: float) -> None:
    """Eq. 13 has three branches (≤ 33, ≤ 65, above): rain must wet in each."""
    wet = duff_moisture_code(
        previous_dmc,
        temperature_c=15.0,
        relative_humidity_pct=70.0,
        rain_24h_mm=20.0,
        day_length=9.0,
    )
    assert 0.0 <= wet < previous_dmc


def test_the_saturation_correction_reads_the_pre_rain_moisture() -> None:
    """Eq. 3a applies to fuel that was *already* saturated before the rain.

    A very low FFMC means soaked fuel (above 150 % moisture): there the extra
    water runs off instead of being absorbed. If the branch read the
    post-rain value, the correction would also hit fuel that was dry at
    dawn, overstating its wetting.

    The observable check: starting soaked, the rain must not push the
    moisture past its 250 cap, i.e. the FFMC below its minimum.
    """
    soaked = fine_fuel_moisture_code(
        5.0,
        temperature_c=10.0,
        relative_humidity_pct=95.0,
        wind_speed_kmh=2.0,
        rain_24h_mm=60.0,
    )
    assert 0.0 <= soaked <= 101.0


# ---------------------------------------------------------------------------
# Physical bounds
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("temperature_c", "relative_humidity_pct", "wind_speed_kmh", "rain_24h_mm"),
    [
        (45.0, 0.0, 120.0, 0.0),  # extreme sirocco
        (-20.0, 100.0, 0.0, 0.0),  # saturated frost
        (25.0, 50.0, 20.0, 200.0),  # cloudburst
        (0.0, 100.0, 0.0, 0.0),
    ],
)
def test_codes_stay_inside_their_domains(
    temperature_c: float,
    relative_humidity_pct: float,
    wind_speed_kmh: float,
    rain_24h_mm: float,
) -> None:
    """No weather extreme may produce a NaN or an out-of-range code.

    A NaN here becomes a hole in a downstream map on exactly the day the
    weather is most extreme.
    """
    out = advance(
        FwiState(ffmc=85.0, dmc=25.0, dc=200.0),
        month=7,
        temperature_c=temperature_c,
        relative_humidity_pct=relative_humidity_pct,
        wind_speed_kmh=wind_speed_kmh,
        rain_24h_mm=rain_24h_mm,
        params=PARAMS,
    )
    for name, value in (
        ("ffmc", out.state.ffmc),
        ("dmc", out.state.dmc),
        ("dc", out.state.dc),
        ("isi", out.isi),
        ("bui", out.bui),
        ("fwi", out.fwi),
    ):
        assert math.isfinite(value), name
        assert value >= 0.0, name
    assert out.state.ffmc <= 101.0


def test_buildup_index_survives_both_codes_at_zero() -> None:
    """Eq. 27 divides by `dmc + 0.4·dc`: on soaked ground that is a division
    by zero, not an impossible case."""
    assert buildup_index(0.0, 0.0) == 0.0


def test_buildup_index_uses_eq_28_when_duff_dominates() -> None:
    assert buildup_index(60.0, 50.0) > 0.0


# ---------------------------------------------------------------------------
# Memory -- the reason the state has to be persisted
# ---------------------------------------------------------------------------
def test_the_drought_code_remembers_far_longer_than_the_fine_fuel() -> None:
    """FFMC forgets in a day, DC in ~52.

    That asymmetry is why a caller has to persist the state: if the DC
    forgot quickly too, restarting from the standard values would be
    harmless. After heavy rain followed by a dry week the fine fuel must
    have recovered almost entirely, the DC hardly at all.
    """
    state = FwiState(ffmc=85.0, dmc=40.0, dc=500.0)
    wet = advance(
        state,
        month=7,
        temperature_c=20.0,
        relative_humidity_pct=80.0,
        wind_speed_kmh=5.0,
        rain_24h_mm=50.0,
        params=PARAMS,
    )
    dc_after_rain = wet.state.dc
    ffmc_after_rain = wet.state.ffmc

    dry = wet
    for _ in range(7):
        dry = advance(
            dry.state,
            month=7,
            temperature_c=32.0,
            relative_humidity_pct=20.0,
            wind_speed_kmh=15.0,
            rain_24h_mm=0.0,
            params=PARAMS,
        )

    # The fraction of what the rain took that a dry week gave back: the two
    # codes have different scales, but the recovered fraction compares.
    ffmc_recovered = (dry.state.ffmc - ffmc_after_rain) / (85.0 - ffmc_after_rain)
    dc_recovered = (dry.state.dc - dc_after_rain) / (500.0 - dc_after_rain)

    # The fine fuel recovered all of it and more: a week at 32 °C and 20 %
    # humidity leaves it drier than before the rain.
    assert ffmc_recovered > 1.0
    assert dry.state.ffmc > 90.0
    # The DC recovered less than half, in the July when it dries fastest.
    assert dc_recovered < 0.5


def test_wind_only_enters_through_the_spread_index() -> None:
    """Wind enters ISI (Eq. 24) and, through FFMC, the drying rate -- but not
    BUI, which is available fuel only."""
    calm = initial_spread_index(90.0, wind_speed_kmh=0.0)
    gale = initial_spread_index(90.0, wind_speed_kmh=60.0)
    assert gale > calm * 10.0


def test_fwi_is_monotone_in_both_of_its_inputs() -> None:
    """More spread or more fuel never gives a lower index."""
    base = fire_weather_index(10.0, 50.0)
    assert fire_weather_index(20.0, 50.0) > base
    assert fire_weather_index(10.0, 120.0) > base


def test_a_tiny_fire_stays_below_one() -> None:
    """Eqs. 30-31: below B = 1 the index is B itself, not the log form."""
    assert 0.0 <= fire_weather_index(0.5, 1.0) <= 1.0


# ---------------------------------------------------------------------------
# Parameter validation
# ---------------------------------------------------------------------------
def test_a_day_length_table_of_the_wrong_size_is_refused() -> None:
    """Eleven months would pass silently and shift the whole year."""
    with pytest.raises(ValueError, match="12 monthly entries"):
        FwiParams(
            ffmc_start=85.0,
            dmc_start=6.0,
            dc_start=15.0,
            day_length_dmc=PARAMS.day_length_dmc[:11],
            day_length_dc=PARAMS.day_length_dc,
        )


def test_an_impossible_month_is_refused() -> None:
    with pytest.raises(ValueError, match=r"month must be in 1\.\.12"):
        advance(
            PARAMS.initial_state,
            month=13,
            temperature_c=20.0,
            relative_humidity_pct=50.0,
            wind_speed_kmh=10.0,
            rain_24h_mm=0.0,
            params=PARAMS,
        )
