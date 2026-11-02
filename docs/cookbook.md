# Cookbook

Short, copy-pasteable recipes for common tasks. `fwi-chain` itself has no
dependencies. Where a recipe uses pandas or FastAPI, that is your choice, not
a requirement.

- [Persist the state between runs](#persist-the-state-between-runs)
- [Run the chain over a pandas DataFrame](#run-the-chain-over-a-pandas-dataframe)
- [Many stations or grid cells](#many-stations-or-grid-cells)
- [Use all CPU cores](#use-all-cpu-cores)
- [Convert units](#convert-units)
- [Danger classes](#danger-classes)
- [Daily Severity Rating (DSR)](#daily-severity-rating-dsr)
- [Missing days](#missing-days)
- [Run on a forecast](#run-on-a-forecast)
- [Serve it over HTTP](#serve-it-over-http)
- [What-if analysis](#what-if-analysis)

---

## Persist the state between runs

The state is three floats. Store it however you like.

**JSON file**

```python
import dataclasses, json
from pathlib import Path
from fwi_chain import STANDARD_PARAMS, FwiState

path = Path("state.json")
state = FwiState(**json.loads(path.read_text())) if path.exists() else STANDARD_PARAMS.initial_state
# ... out = advance(state, ...) ...
path.write_text(json.dumps(dataclasses.asdict(out.state)))
```

**SQL table** (one row per station per day; keeping history makes reruns easy)

```sql
CREATE TABLE fwi_state (
    station TEXT NOT NULL,
    day     DATE NOT NULL,
    ffmc REAL, dmc REAL, dc REAL,
    isi  REAL, bui REAL, fwi REAL,
    PRIMARY KEY (station, day)
);
```

The full daily job is [`examples/03_daily_job_sqlite.py`](../examples/03_daily_job_sqlite.py).

**Redis / key-value cache**

```python
r.hset(f"fwi:{station}", mapping=dataclasses.asdict(out.state))
state = FwiState(**{k.decode(): float(v) for k, v in r.hgetall(f"fwi:{station}").items()})
```

---

## Run the chain over a pandas DataFrame

The chain is sequential in time, so iterate rows in date order and collect the results.

```python
import pandas as pd
from fwi_chain import STANDARD_PARAMS, advance

df = pd.read_csv("noon.csv", parse_dates=["date"]).sort_values("date")

state = STANDARD_PARAMS.initial_state
records = []
for row in df.itertuples(index=False):
    out = advance(
        state,
        month=row.date.month,
        temperature_c=row.temp_c,
        relative_humidity_pct=row.rh_pct,
        wind_speed_kmh=row.wind_kmh,
        rain_24h_mm=row.rain_mm,
        params=STANDARD_PARAMS,
    )
    state = out.state
    records.append(
        {
            "ffmc": out.state.ffmc,
            "dmc": out.state.dmc,
            "dc": out.state.dc,
            "isi": out.isi,
            "bui": out.bui,
            "fwi": out.fwi,
        }
    )

df = df.join(pd.DataFrame(records, index=df.index))
```

With a `station` column, run the same loop per group:

```python
def run_chain(group: pd.DataFrame) -> pd.DataFrame:
    ...  # the loop above, on `group`
    return group.join(pd.DataFrame(records, index=group.index))


df = pd.concat(run_chain(g) for _, g in df.sort_values("date").groupby("station"))
```

> For large gridded datasets (NetCDF, Zarr), a vectorised implementation such as
> [xclim](https://github.com/Ouranosinc/xclim) will be faster than a Python loop.
> `fwi-chain` is designed for row-at-a-time pipelines: databases, streams, services.

---

## Many stations or grid cells

Locations are independent, so keep a mapping from location to state:

```python
states: dict[str, FwiState] = load_states()  # from your storage

for station_id, obs in todays_observations.items():
    prev = states.get(station_id, STANDARD_PARAMS.initial_state)
    out = advance(
        prev,
        month=today.month,
        params=STANDARD_PARAMS,
        temperature_c=obs.t,
        relative_humidity_pct=obs.rh,
        wind_speed_kmh=obs.wind,
        rain_24h_mm=obs.rain,
    )
    states[station_id] = out.state
    publish(station_id, today, out.fwi)

save_states(states)
```

See [`examples/04_many_stations.py`](../examples/04_many_stations.py).

---

## Use all CPU cores

Each location's season is independent. Spread locations, not days, across processes:

```python
from concurrent.futures import ProcessPoolExecutor
from fwi_chain import STANDARD_PARAMS, advance


def run_season(readings):  # one location, all days in order
    state, fwi = STANDARD_PARAMS.initial_state, []
    for r in readings:
        out = advance(
            state,
            month=r.day.month,
            params=STANDARD_PARAMS,
            temperature_c=r.temperature_c,
            relative_humidity_pct=r.relative_humidity_pct,
            wind_speed_kmh=r.wind_speed_kmh,
            rain_24h_mm=r.rain_24h_mm,
        )
        state = out.state
        fwi.append(out.fwi)
    return fwi


if __name__ == "__main__":
    with ProcessPoolExecutor() as pool:
        results = list(pool.map(run_season, readings_per_location, chunksize=64))
```

One `advance` call is a few microseconds of pure arithmetic, so a single core
handles a full season for thousands of locations in seconds.

---

## Convert units

| You have | `fwi-chain` wants | Conversion |
|---|---|---|
| wind in m/s | km/h | `kmh = ms * 3.6` |
| wind in knots | km/h | `kmh = kn * 1.852` |
| temperature in K | °C | `c = k - 273.15` |
| temperature in °F | °C | `c = (f - 32) / 1.8` |
| RH as a fraction | % | `pct = frac * 100` |
| rain in inches | mm | `mm = inch * 25.4` |
| precipitation in m (e.g. ERA5 `tp`) | mm | `mm = m * 1000` |
| dew point + temperature | RH % | Magnus formula: `100 * exp(17.625*td/(243.04+td)) / exp(17.625*t/(243.04+t))` |

---

## Danger classes

Classes are regional. Here are the EFFIS thresholds for Europe:

```python
DANGER_CLASSES = [
    (50.0, "extreme"),
    (38.0, "very high"),
    (21.3, "high"),
    (11.2, "moderate"),
    (5.2, "low"),
    (0.0, "very low"),
]


def danger_class(fwi: float) -> str:
    return next(label for lower, label in DANGER_CLASSES if fwi >= lower)
```

---

## Daily Severity Rating (DSR)

DSR is a transformation of FWI that scales with the effort needed to control a
fire. It is commonly averaged over a season (the Seasonal Severity Rating):

```python
def daily_severity_rating(fwi: float) -> float:
    return 0.0272 * fwi**1.77
```

---

## Missing days

One call to `advance` is **one day**. If a day's observation is missing,
skipping it compresses two days of drying into one step, and calling `advance`
twice with the same weather double-counts. Prefer, in order:

1. a nearby station, or a weather-model analysis for that day;
2. a forecast that was valid for that day;
3. a conservative estimate (for example yesterday's temperature and humidity, no rain);

and flag the output as estimated. Do not reset the state.

---

## Run on a forecast

To forecast danger for the next *N* days, start from today's **observed** state
and advance it through the forecast. Do **not** save the forecast states as the
real chain:

```python
state = load_observed_state(station)       # the real chain, up to today
for day in forecast_days:                  # tomorrow, the day after, ...
    out = advance(state, month=day.date.month, params=STANDARD_PARAMS, ...)
    state = out.state                      # local only: never persisted
    print(day.date, out.fwi)
```

Tomorrow, when the observation arrives, advance the **observed** state again.

---

## Serve it over HTTP

A tiny stateless endpoint with FastAPI. The client sends yesterday's state and
today's weather and gets back today's outputs:

```python
from dataclasses import asdict
from fastapi import FastAPI
from pydantic import BaseModel
from fwi_chain import STANDARD_PARAMS, FwiState, advance

app = FastAPI()


class Request(BaseModel):
    ffmc: float = 85.0
    dmc: float = 6.0
    dc: float = 15.0
    month: int
    temperature_c: float
    relative_humidity_pct: float
    wind_speed_kmh: float
    rain_24h_mm: float


@app.post("/fwi")
def fwi(req: Request) -> dict:
    out = advance(
        FwiState(req.ffmc, req.dmc, req.dc),
        month=req.month,
        temperature_c=req.temperature_c,
        relative_humidity_pct=req.relative_humidity_pct,
        wind_speed_kmh=req.wind_speed_kmh,
        rain_24h_mm=req.rain_24h_mm,
        params=STANDARD_PARAMS,
    )
    return {**asdict(out.state), "isi": out.isi, "bui": out.bui, "fwi": out.fwi}
```

```bash
curl -s localhost:8000/fwi -H 'content-type: application/json' \
  -d '{"month":4,"temperature_c":17,"relative_humidity_pct":42,"wind_speed_kmh":25,"rain_24h_mm":0}'
# {"ffmc":87.69...,"dmc":8.545...,"dc":19.014,"isi":10.85...,"bui":8.49...,"fwi":10.09...}
```

---

## What-if analysis

The six equations are exported individually, so you can explore sensitivity
without running a season:

```python
from fwi_chain import initial_spread_index, fire_weather_index

for wind in range(0, 70, 10):
    isi = initial_spread_index(92.0, wind_speed_kmh=wind)
    print(wind, round(fire_weather_index(isi, 80.0), 1))
```

See [`examples/06_individual_equations.py`](../examples/06_individual_equations.py).
