# API reference

Everything is importable from the top-level package:

```python
from fwi_chain import (
    advance,
    FwiState,
    FwiOutputs,
    FwiParams,
    STANDARD_PARAMS,
    fine_fuel_moisture_code,
    duff_moisture_code,
    drought_code,
    initial_spread_index,
    buildup_index,
    fire_weather_index,
    # many days (1.1)
    walk_chain,
    days_to_walk,
    writable_days,
    rewalk_with_rain,
    correct_rain,
    NoonObservation,
    ChainPoint,
    ChainDay,
    catch_up,
    start_is_stale,
    # climatology (1.1)
    quantiles,
    percentile,
    node_ceiling,
    accumulate_monthly,
    coverage_is_valid,
    QUANTILE_LEVELS,
    # classes and what moved the index (1.2)
    effis_class,
    EFFIS_FWI_CLASSES,
    explain_change,
    Explanation,
    Driver,
)
```

The facts, the text check and the MCP server are in their own modules
(`fwi_chain.facts`, `fwi_chain.check`, `fwi_chain.mcp_server`): see
[Facts, explanation and MCP](ai.md).

All functions are **pure**: no I/O, no global state, no clock. They are safe to call
from any thread or process. Weather arguments are **keyword-only** and carry their
unit in the name.

---

## The chain

### `advance(state, *, month, temperature_c, relative_humidity_pct, wind_speed_kmh, rain_24h_mm, params) -> FwiOutputs`

Runs **one day** of the chain: yesterday's codes plus today's noon reading.

| Argument | Type | Meaning |
|---|---|---|
| `state` | `FwiState` | yesterday's FFMC, DMC and DC (or `params.initial_state` on day one) |
| `month` | `int` | 1–12. Selects the day-length factors. Raises `ValueError` outside that range |
| `temperature_c` | `float` | noon air temperature, °C |
| `relative_humidity_pct` | `float` | noon relative humidity, %. Values outside 0–100 are clamped |
| `wind_speed_kmh` | `float` | noon 10 m wind speed, km/h. Negative values are treated as 0 |
| `rain_24h_mm` | `float` | rain accumulated over the previous 24 h, mm |
| `params` | `FwiParams` | start-up codes and day-length tables. Usually `STANDARD_PARAMS` |

Returns an `FwiOutputs`.

```python
out = advance(
    state,
    month=7,
    temperature_c=31,
    relative_humidity_pct=22,
    wind_speed_kmh=18,
    rain_24h_mm=0,
    params=STANDARD_PARAMS,
)
state = out.state
```

---

## Data types

All three are `@dataclass(frozen=True, slots=True)`: immutable, hashable, cheap,
and serialisable with `dataclasses.asdict`.

### `FwiState`

The three recursive codes carried from one day to the next.

| Field | Range | Meaning |
|---|---|---|
| `ffmc` | 0–101 | Fine Fuel Moisture Code |
| `dmc` | ≥ 0 | Duff Moisture Code |
| `dc` | ≥ 0 | Drought Code |

### `FwiOutputs`

A day's full result.

| Field | Type | Meaning |
|---|---|---|
| `state` | `FwiState` | today's codes, which become tomorrow's input |
| `isi` | `float` | Initial Spread Index |
| `bui` | `float` | Buildup Index |
| `fwi` | `float` | Fire Weather Index |

### `FwiParams`

What a deployment may choose, as opposed to the constants Van Wagner fixed.

| Field | Type | Meaning |
|---|---|---|
| `ffmc_start` | `float` | FFMC at the start of the season |
| `dmc_start` | `float` | DMC at the start of the season |
| `dc_start` | `float` | DC at the start of the season |
| `day_length_dmc` | `tuple[float, ...]` | 12 monthly DMC day-length factors, **January first** |
| `day_length_dc` | `tuple[float, ...]` | 12 monthly DC day-length adjustments, **January first** |

- `initial_state` (property) returns `FwiState(ffmc_start, dmc_start, dc_start)`.
- The constructor raises `ValueError` if a table does not have exactly 12 entries.
  An 11-entry table would otherwise shift the whole year silently.

### `STANDARD_PARAMS`

Van Wagner's published defaults: start-up codes 85 / 6 / 15 and the day-length
tables for 46°N (Tables 2 and 3 of the 1987 report).

| Month | J | F | M | A | M | J | J | A | S | O | N | D |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `day_length_dmc` | 6.5 | 7.5 | 9.0 | 12.8 | 13.9 | 13.9 | 12.4 | 10.9 | 9.4 | 8.0 | 7.0 | 6.0 |
| `day_length_dc` | −1.6 | −1.6 | −1.6 | 0.9 | 3.8 | 5.8 | 6.4 | 5.0 | 2.4 | 0.4 | −1.6 | −1.6 |

---

## The individual equations

Use these for sensitivity analysis, teaching, or a custom chain. The equation
numbers refer to Van Wagner (1987).

### `fine_fuel_moisture_code(previous, *, temperature_c, relative_humidity_pct, wind_speed_kmh, rain_24h_mm) -> float`

Eqs. 1–10. Returns today's FFMC on the 0–101 scale. Rain at or below 0.5 mm is
intercepted by the canopy and ignored.

### `duff_moisture_code(previous, *, temperature_c, relative_humidity_pct, rain_24h_mm, day_length) -> float`

Eqs. 11–17. `day_length` is the month's factor, e.g. `params.day_length_dmc[month - 1]`.
Rain at or below 1.5 mm is ignored. Below −1.1 °C there is no drying.

### `drought_code(previous, *, temperature_c, rain_24h_mm, day_length) -> float`

Eqs. 18–23. `day_length` is e.g. `params.day_length_dc[month - 1]`. Rain at or below
2.8 mm is ignored. Below −2.8 °C there is no drying.

### `initial_spread_index(ffmc, *, wind_speed_kmh) -> float`

Eqs. 24–26. Expected rate of spread. This is where wind enters the chain.

### `buildup_index(dmc, dc) -> float`

Eqs. 27–28. Total fuel available. Returns `0.0` when both codes are zero (a
saturated landscape), where Eq. 27 would otherwise divide by zero.

### `fire_weather_index(isi, bui) -> float`

Eqs. 29–31. The published index: the intensity of a spreading fire.

```python
from fwi_chain import initial_spread_index, buildup_index, fire_weather_index

isi = initial_spread_index(92.0, wind_speed_kmh=30.0)  # 25.8
bui = buildup_index(dmc=40.0, dc=400.0)  # 64.0
fwi = fire_weather_index(isi, bui)  # 47.2
```

---

## Guarantees

- **No NaN, no negatives.** Under any finite weather, from frost to a 45 °C,
  120 km/h sirocco to a 200 mm cloudburst, all six outputs are finite and ≥ 0,
  and FFMC ≤ 101. This is tested.
- **Deterministic.** The same inputs always give bit-identical outputs.
- **Stable API.** The package follows [Semantic Versioning](https://semver.org/).

### `__version__`

`fwi_chain.__version__` is the installed package version, read from package metadata.

---

## Many days

*New in 1.1.* `advance()` is one day. These walk a chain over many, from a point
you stored, and leave the storing to you. Days are `datetime.date` values you pass
in: nothing reads a clock, so "today" is always an argument.

### Types

| Type | Fields | Meaning |
|---|---|---|
| `NoonObservation` | `temperature_c`, `relative_humidity_pct`, `wind_speed_kmh`, `rain_24h_mm` | the four noon readings of one day |
| `ChainPoint` | `day`, `state`, `chain_days` | a chain as of one day: where a walk resumes from |
| `ChainDay` | `day`, `outputs`, `chain_days`, `observation` | one walked day. `.point` gives it back as a `ChainPoint` |

`chain_days` counts the days the chain has been advanced since it last started
from the standard codes. It tells a settled drought code from one still reporting
its seed.

### `walk_chain(observations, days, *, start, params, max_gap_days) -> list[ChainDay]`

Walks one chain over `days`. `observations` maps a day to its `NoonObservation`;
`start` is the last stored `ChainPoint` before `days[0]`, or `None`.

- A day with no observation is **skipped, not zeroed**.
- A `start` more than `max_gap_days` before `days[0]` is discarded: the walk
  restarts from `params.initial_state` and `chain_days` from zero.
- Days missing inside the window are not counted against `max_gap_days`.

```python
from datetime import date
from fwi_chain import STANDARD_PARAMS, NoonObservation, walk_chain

days = [date(2026, 7, 1), date(2026, 7, 2), date(2026, 7, 3)]
observations = {
    days[0]: NoonObservation(31, 22, 18, 0),
    days[2]: NoonObservation(28, 35, 10, 4.2),  # 2 July is missing: skipped
}
walked = walk_chain(observations, days, start=None, params=STANDARD_PARAMS, max_gap_days=7)
resume_from = walked[-1].point  # store this; pass it as `start` next time
```

### `days_to_walk(target, *, last_day, max_gap_days) -> list[date]`

The days to walk to bring a chain up to `target`: from the day after `last_day`,
never further back than `max_gap_days` before `target`. `[target]` when `last_day`
is `None`.

### `catch_up(observations, target, *, start, params, max_gap_days) -> list[ChainDay]`

*New in 1.2.* The daily update in one call: brings a chain up to `target`. A
`start` more than `max_gap_days` before `target` is discarded, at exactly that
limit, and `target` alone is walked from the standard codes; otherwise every
day after `start` is walked.

Use this instead of calling `days_to_walk` and then `walk_chain` yourself:
that pair trims the window first and measures the gap from the trimmed window,
so a state up to twice the limit old is carried on.

### `start_is_stale(start, day, *, max_gap_days) -> bool`

*New in 1.2.* Whether `start` is more than `max_gap_days` before `day`.

### `writable_days(walked, *, today) -> list[ChainDay]`

The walked days on or before `today`. A forecast day is worth computing and must
never be stored: it would become tomorrow's predecessor.

### `rewalk_with_rain(rows, start, rain, *, params, max_gap_days) -> list[ChainDay]`

Redoes `rows` from `start` with measured rain. `rain` maps a day to millimetres
over the 24 h before its noon reading; a day missing from it, or mapped to `None`,
keeps the row's own rain, because a hole in the measurement is not a dry day.
Temperature, humidity and wind are the rows' own. Stops at the first row more than
`max_gap_days` after the one before it.

### `correct_rain(series, *, since, rain, params, max_gap_days, weather=None) -> list[ChainDay]`

The same, on a stored chain: restarts from the last row before `since` (or from
the chain's first row, if it was born later) and returns every row after it,
redone. With `weather`, a row whose day is in it takes that observation before the
rain is applied. Idempotent.

---

## Climatology

*New in 1.1.* Where an FWI falls in the distribution of its place and its month.

### `QUANTILE_LEVELS`

`(0.0, 5.0, …, 100.0)`: the 21 levels every function here uses.

### `quantiles(values) -> list[float]`

The 21 quantiles of `values`, linearly interpolated between ranks. Raises
`ValueError` on an empty sequence.

### `percentile(value, q) -> float`

The percentile (0–100) of `value` among the 21 quantiles `q`. 0 or 100 outside the
distribution. On a flat stretch, such as a winter month with many days at FWI 0,
it returns the centre of the stretch.

```python
from fwi_chain import percentile, quantiles

q = quantiles(august_fwi_values)  # years of 1–31 August, for one place
percentile(41.0, q)  # e.g. 92.5: a rare day here
```

### `node_ceiling(per_month, *, quantile, months, minimum, maximum) -> float | None`

A place's "full" FWI: the mean over `months` of the monthly quantile at level
`quantile`, kept between `minimum` and `maximum`. `per_month` maps a month (1–12)
to its 21 quantiles. `None` when none of `months` has them.

### `accumulate_monthly(observations, days, per_month, *, state, days_walked, params, spinup_days) -> tuple[FwiState, int]`

Advances the chain over `days` and **appends** each day's FWI to
`per_month[month]`, a dict you own. Returns the new state and day count, to pass
back in for the next stretch. The first `spinup_days` walked days move the chain
but stay out of the distribution.

### `coverage_is_valid(observed, days, *, max_gap_days, min_fraction=0.95) -> bool`

Whether a stretch of days has enough observations to enter a climatology: at least
`min_fraction` of them, and no run of missing days longer than `max_gap_days`.

---

## Danger classes

*New in 1.2.*

### `effis_class(fwi) -> str`

The fire danger class EFFIS maps an FWI in: `"low"`, `"moderate"`, `"high"`,
`"very high"`, `"extreme"`, `"very extreme"`. A boundary belongs to the class
above it. Raises `ValueError` for a negative or non-finite FWI.

### `EFFIS_FWI_CLASSES`

`((0.0, "low"), (11.2, "moderate"), (21.3, "high"), (38.0, "very high"),
(50.0, "extreme"), (70.0, "very extreme"))`: each class with the FWI it starts
at, as EFFIS publishes them.

---

## What moved the index

*New in 1.2.*

### `explain_change(previous, today, *, params) -> Explanation`

Takes apart the difference between the FWI of two consecutive walked days.

| Field of `Explanation` | Meaning |
|---|---|
| `fwi_yesterday`, `fwi_today`, `change` | the two values and their difference |
| `carry_over` | what the chain's memory alone did: today with yesterday's weather again |
| `weather` | what the change in the weather did; `change == carry_over + weather` |
| `drivers` | four `Driver(input, yesterday, today, effect)`, largest effect first; the effects add up to `weather` |

See [Facts, explanation and MCP](ai.md) for how the split is made.
