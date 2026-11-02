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
)
```

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
