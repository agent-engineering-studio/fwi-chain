# Getting started

This guide takes you from `pip install` to a daily job that keeps the chain
running all season. Allow about ten minutes.

## 1. Install

```bash
pip install fwi-chain
# or
uv add fwi-chain
```

Python 3.12 or newer. There are no dependencies to install.

## 2. Compute one day

```python
from fwi_chain import STANDARD_PARAMS, advance

out = advance(
    STANDARD_PARAMS.initial_state,
    month=4,
    temperature_c=17.0,
    relative_humidity_pct=42.0,
    wind_speed_kmh=25.0,
    rain_24h_mm=0.0,
    params=STANDARD_PARAMS,
)
```

`out` is an `FwiOutputs`:

```python
>>> out
FwiOutputs(state=FwiState(ffmc=87.69..., dmc=8.545..., dc=19.014),
           isi=10.85..., bui=8.49..., fwi=10.09...)
```

- `out.state` holds the **three moisture codes**, which is what you carry to tomorrow.
- `out.isi`, `out.bui` and `out.fwi` are **today's indices**, which is what you publish.

All arguments after `state` are **keyword-only**, and every name carries its unit.
That makes it hard to pass wind in m/s by mistake. The call fails loudly if
you forget an argument.

## 3. Run a season

The chain is a fold over days. Each day's output state is the next day's input:

```python
import csv
from datetime import date
from fwi_chain import STANDARD_PARAMS, advance

state = STANDARD_PARAMS.initial_state
with open("noon_weather.csv") as f:  # date,temp_c,rh_pct,wind_kmh,rain_mm
    for row in csv.DictReader(f):
        day = date.fromisoformat(row["date"])
        out = advance(
            state,
            month=day.month,
            temperature_c=float(row["temp_c"]),
            relative_humidity_pct=float(row["rh_pct"]),
            wind_speed_kmh=float(row["wind_kmh"]),
            rain_24h_mm=float(row["rain_mm"]),
            params=STANDARD_PARAMS,
        )
        state = out.state
        print(day, f"FWI {out.fwi:5.1f}")
```

Try the bundled version with synthetic weather:

```bash
git clone https://github.com/agent-engineering-studio/fwi-chain
cd fwi-chain
python examples/02_fire_season.py season.csv   # needs `pip install fwi-chain` or `uv run`
```

## 4. Keep the state between runs

In production you usually run once a day, when the noon observation (or the
forecast) arrives. The process ends, so the state has to live somewhere:

```
┌─────────────┐   load    ┌──────────┐   advance()   ┌──────────┐   save   ┌─────────────┐
│ storage     │ ────────▶ │ FwiState │ ────────────▶ │ FwiState │ ───────▶ │ storage     │
│ (yesterday) │           └──────────┘  + today's    └──────────┘          │ (today)     │
└─────────────┘                          weather                           └─────────────┘
```

`FwiState` is a frozen dataclass of three floats, so it is easy to store anywhere:

```python
import dataclasses, json
from fwi_chain import FwiState

saved = json.dumps(dataclasses.asdict(out.state))  # '{"ffmc": 87.69..., "dmc": ..., "dc": ...}'
state = FwiState(**json.loads(saved))  # tomorrow
```

[Example 03](https://github.com/agent-engineering-studio/fwi-chain/blob/main/examples/03_daily_job_sqlite.py) is a complete daily job backed by
SQLite. Run it a few times and watch it resume from where it left off.

## 5. Adapt the parameters to your region

`STANDARD_PARAMS` uses Van Wagner's day-length tables for **46°N**, which suits
most of Europe, southern Canada and the northern United States. The tables matter
for DMC and DC only. For other regions, build your own `FwiParams`:

```python
from fwi_chain import STANDARD_PARAMS, FwiParams


def shift_six_months(t):  # a common approximation for the southern hemisphere
    return t[6:] + t[:6]


SOUTH = FwiParams(
    ffmc_start=85.0,
    dmc_start=6.0,
    dc_start=15.0,
    day_length_dmc=shift_six_months(STANDARD_PARAMS.day_length_dmc),
    day_length_dc=shift_six_months(STANDARD_PARAMS.day_length_dc),
)
```

Near the equator, or at high latitudes, use tables adjusted for your band. The
`cffdrs` R package documents several. See
[example 05](https://github.com/agent-engineering-studio/fwi-chain/blob/main/examples/05_southern_hemisphere.py).

## Common mistakes

| Mistake | Symptom | Fix |
|---|---|---|
| Wind in **m/s** instead of km/h | FWI far too low on windy days | multiply by 3.6 |
| Daily **max** temperature / **min** humidity instead of noon values | FWI biased high | use noon observations (or a forecast valid at local noon) |
| Rain over the calendar day instead of **noon to noon** | wetting attributed to the wrong day | accumulate rain from yesterday's noon to today's noon |
| **Restarting** the chain from 85/6/15 every run | DC and BUI stay near zero all summer | persist `out.state` and load it tomorrow |
| **Skipping** days with missing data | the codes jump, because one call = one day | fill gaps with an estimate (nearest station, forecast) rather than skipping |
| Relative humidity as a **fraction** (0.42) | FFMC far too high | pass percent (42) |
| Unordered rows | nonsense values | sort by date before running the chain |

## Next steps

- [Cookbook](cookbook.md): pandas, many stations, parallelism, an HTTP service.
- [API reference](api.md): every function and its arguments.
- [How the FWI works](how-fwi-works.md): the science behind the numbers.
