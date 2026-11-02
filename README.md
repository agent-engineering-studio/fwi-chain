# fwi-chain

The Canadian Forest Fire Weather Index chain (Van Wagner 1987) as pure,
typed Python functions with no dependencies — verified against the published
reference day to 1e-9.

[![ci](https://github.com/agent-engineering-studio/fwi-chain/actions/workflows/ci.yml/badge.svg)](https://github.com/agent-engineering-studio/fwi-chain/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/fwi-chain)](https://pypi.org/project/fwi-chain/)

Four noon readings a day (temperature, relative humidity, 10 m wind, rain
over the previous 24 h) give six numbers:

| Code | What it tracks | Memory |
|------|----------------|--------|
| FFMC | fine fuel moisture | ~2/3 day |
| DMC  | duff moisture | ~12 days |
| DC   | deep drought | ~52 days |
| ISI  | rate of spread (FFMC × wind) | — |
| BUI  | available fuel (DMC + DC) | — |
| FWI  | fire intensity, the index EFFIS publishes for Europe | — |

The three moisture codes are recursive: today's value depends on
yesterday's. A chain started from the standard values needs weeks of
spin-up, so the library gives you the state as a value (`FwiState`) and
leaves persisting it to you — a table, a file, a cache.

## Install

```bash
pip install fwi-chain
```

## Use

```python
from fwi_chain import STANDARD_PARAMS, advance

state = STANDARD_PARAMS.initial_state  # FFMC/DMC/DC = 85 / 6 / 15
out = advance(
    state,
    month=4,
    temperature_c=17.0,
    relative_humidity_pct=42.0,
    wind_speed_kmh=25.0,
    rain_24h_mm=0.0,
    params=STANDARD_PARAMS,
)
print(round(out.fwi, 2))  # 10.1
state = out.state  # store it: tomorrow starts from here
```

The individual equations (`fine_fuel_moisture_code`, `duff_moisture_code`,
`drought_code`, `initial_spread_index`, `buildup_index`,
`fire_weather_index`) are exported too.

`STANDARD_PARAMS` carries Van Wagner's day-length tables for 46°N. Far from
that latitude, or south of the equator, build your own `FwiParams`:

```python
from fwi_chain import FwiParams

params = FwiParams(
    ffmc_start=85.0,
    dmc_start=6.0,
    dc_start=15.0,
    day_length_dmc=(...),  # 12 monthly factors, January first
    day_length_dc=(...),
)
```

## Why another FWI implementation

- **Zero dependencies, scalar, pure.** No NumPy, no xarray, no I/O, no clock.
  It fits a database job, a stream processor or a small service. For gridded
  climate data, [xclim](https://github.com/Ouranosinc/xclim)'s vectorised FWI
  is the better tool.
- **The state is explicit.** One call is one day; persisting and resuming the
  chain is the caller's choice, not hidden in an array dimension.
- **Verified, not just tested.** The suite checks the six outputs of the
  reference day of the `cffdrs` test series to an absolute 1e-9, plus every
  rain branch, physical bounds under extreme weather, and the memory
  asymmetry between FFMC and DC.

Extracted from [Limen](https://github.com/agent-engineering-studio/limen),
where it runs the wildfire danger chain for every ~9 km weather node in Italy.

## Reference

Van Wagner, C.E. (1987). *Development and structure of the Canadian Forest
Fire Weather Index System*. Canadian Forestry Service, Forestry Technical
Report 35. Equation numbers in the source comments are that report's.

## Development

```bash
uv sync
make check
```

## License

[Apache-2.0](./LICENSE).
