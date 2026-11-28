<p align="center">
  <img src="https://raw.githubusercontent.com/agent-engineering-studio/fwi-chain/main/docs/images/social-preview.png" alt="fwi-chain: the Canadian Fire Weather Index in pure Python" width="100%">
</p>

<p align="center">
  <a href="https://github.com/agent-engineering-studio/fwi-chain/actions/workflows/ci.yml"><img src="https://github.com/agent-engineering-studio/fwi-chain/actions/workflows/ci.yml/badge.svg" alt="ci"></a>
  <a href="https://pypi.org/project/fwi-chain/"><img src="https://img.shields.io/pypi/v/fwi-chain" alt="PyPI"></a>
  <img src="https://img.shields.io/badge/python-3.12%20%7C%203.13-blue" alt="Python 3.12 | 3.13">
  <img src="https://img.shields.io/badge/dependencies-0-brightgreen" alt="zero dependencies">
  <img src="https://img.shields.io/badge/typing-mypy%20--strict-blue" alt="mypy --strict">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-Apache--2.0-green" alt="Apache-2.0"></a>
</p>

# fwi-chain

**The Canadian Forest Fire Weather Index (FWI) System as small, pure, typed Python functions.**
It has no dependencies and is measured in CI against the 48-day test series of `cffdrs`.

Give it the weather at noon and it tells you how easily a wildfire would start, how
fast it would spread, and how hard it would be to fight. That is the same index
that national fire services and the European Forest Fire Information System (EFFIS)
publish every day.

```bash
pip install fwi-chain
```

---

## Contents

- [What is the Fire Weather Index?](#what-is-the-fire-weather-index)
- [Quick start](#quick-start)
- [See it in action](#see-it-in-action)
- [Why fwi-chain](#why-fwi-chain)
- [Examples](#examples)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [Reference and citation](#reference-and-citation)

---

## What is the Fire Weather Index?

The FWI System was developed by the Canadian Forest Service (Van Wagner, 1987) and is
now the most widely used fire danger rating system in the world. It takes **four
weather readings at local noon**:

| Input | Unit |
|---|---|
| Air temperature | °C |
| Relative humidity | % |
| Wind speed at 10 m | km/h |
| Rain over the previous 24 hours | mm |

From these it computes **six numbers**:

<p align="center">
  <img src="https://raw.githubusercontent.com/agent-engineering-studio/fwi-chain/main/docs/images/fwi-chain-diagram.svg" alt="Diagram of the FWI chain: noon weather feeds FFMC, DMC and DC; FFMC plus wind gives ISI; DMC plus DC gives BUI; ISI and BUI give FWI" width="100%">
</p>

| Code | Name | What it tracks | Memory |
|------|------|----------------|--------|
| **FFMC** | Fine Fuel Moisture Code | dryness of litter, needles and grass: *will a spark catch?* | ~16 hours |
| **DMC**  | Duff Moisture Code | dryness of the loose organic layer below | ~12 days |
| **DC**   | Drought Code | deep, seasonal drought in compact organic soil | ~52 days |
| **ISI**  | Initial Spread Index | FFMC × wind: *how fast would it run?* | — |
| **BUI**  | Buildup Index | DMC + DC: *how much fuel is there to burn?* | — |
| **FWI**  | Fire Weather Index | ISI + BUI: *how intense would the fire be?* | — |

The key idea is that **the three moisture codes have memory**. Today's value depends
on yesterday's, so the FWI is a *chain* that runs day after day through the
fire season. `fwi-chain` makes that memory an explicit value (`FwiState`) that
you store wherever you like.

> New to fire weather? Read **[How the FWI works, in plain words](https://agentengineering.it/fwi-chain/how-fwi-works/)**.

## Quick start

```python
from fwi_chain import STANDARD_PARAMS, advance

state = STANDARD_PARAMS.initial_state  # FFMC/DMC/DC = 85 / 6 / 15, the spring start-up

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

A whole season is just a loop:

```python
state = STANDARD_PARAMS.initial_state
for day in noon_observations:  # your weather, one row per day, in order
    out = advance(
        state,
        month=day.month,
        temperature_c=day.temp,
        relative_humidity_pct=day.rh,
        wind_speed_kmh=day.wind,
        rain_24h_mm=day.rain,
        params=STANDARD_PARAMS,
    )
    state = out.state  # the chain: today's output, tomorrow's input
    print(day.date, round(out.fwi, 1))
```

Each of the six equations is also exported on its own (`fine_fuel_moisture_code`,
`duff_moisture_code`, `drought_code`, `initial_spread_index`, `buildup_index`,
`fire_weather_index`), so you can ask what-if questions directly. See the
[API reference](https://agentengineering.it/fwi-chain/api/).

## See it in action

Every chart below is computed by `fwi-chain` itself from a synthetic, reproducible
Mediterranean season. Regenerate them with `make figures`.

**A fire season, day by day.** Spring rain keeps the index low. Through the summer,
drought builds up, and one windy September day pushes the FWI past 100.

![FWI through a synthetic fire season with the rain below it](https://raw.githubusercontent.com/agent-engineering-studio/fwi-chain/main/docs/images/fire-season.svg)

**Three memories.** The same weather drives all three moisture codes, but they forget
at very different speeds. FFMC jumps back within a day of rain. The Drought Code
climbs slowly all summer and keeps its memory for weeks.

![The three moisture codes over the season](https://raw.githubusercontent.com/agent-engineering-studio/fwi-chain/main/docs/images/moisture-codes.svg)

**Why the state matters.** Restart the chain on 1 July from the spring default codes
and it underestimates the danger for weeks, because it has "forgotten" a dry
spring. That is why `fwi-chain` hands you the state instead of hiding it.

![A cold restart on 1 July compared with a chain that carried its state from April](https://raw.githubusercontent.com/agent-engineering-studio/fwi-chain/main/docs/images/restart.svg)

## Why fwi-chain

- **Zero dependencies, scalar, pure.** No NumPy, no xarray, no I/O, no clock. It fits
  in a database job, a stream processor, or a serverless function. For gridded climate data, [xclim](https://github.com/Ouranosinc/xclim)'s
  vectorised FWI is the better tool.
- **The state is explicit.** One call is one day. You choose how to persist and resume
  the chain (a table, a file, a cache), instead of having it hidden in an array dimension.
- **Measured, not just tested.** A benchmark in CI walks the 48-day test series of
  `cffdrs` and compares the six codes with cffdrs's own output: at most 0.25 FWI points
  apart, the same EFFIS class on all 48 days. The difference has a known cause (two
  constants printed differently in 1985 and 1987); `CFFDRS_PARAMS` takes the 1985 ones
  and matches cffdrs to 0.006. The suite also covers every rain
  branch, physical bounds under extreme weather, and the memory of the codes.
  See [Validation](https://agentengineering.it/fwi-chain/validation/).
- **Readable.** About 300 lines, with every line tied to an equation number in
  Van Wagner's report. It works as a reference implementation as well as a library.
- **Typed.** Ships `py.typed` and passes `mypy --strict`. Frozen dataclasses, keyword-only
  arguments, and units in every parameter name (`wind_speed_kmh`, `rain_24h_mm`).

`fwi-chain` was extracted from [Limen](https://github.com/agent-engineering-studio/limen),
where it runs the wildfire danger chain for every ~9 km weather node in Italy.

## Many days, facts and an MCP server

Since 1.1 the library also walks a chain over many days from a state you stored
(`catch_up`, `walk_chain`), redoes it when better rain arrives (`correct_rain`) and
places a value in the climatology of its place and month (`quantiles`, `percentile`).

Since 1.3 it also reads the noon observation out of hourly weather (`noon_readings`),
refusing a reading taken far from noon or with hours of rain missing.

Since 1.2 it says **what moved the index**. On 7 May 1985, in the test series of
`cffdrs`, the FWI went from 21.7 to 52.6:

```text
the chain's memory    +1.2
wind                 +18.0   12 -> 27 km/h
humidity             +11.1   33 -> 17 %
temperature           +0.6   27 -> 28 °C
rain                  +0.0
```

The same answers come as plain data (`fwi_chain.facts`), with a check that a text
quotes them right (`fwi_chain.check.check_text`) and an MCP server for AI agents
(`pip install "fwi-chain[mcp]"`, then `fwi-chain-mcp`). The rule of all three: the
numbers come from the chain; a model may explain them, never invent them. See
[Facts, explanation and MCP](https://agentengineering.it/fwi-chain/ai/).

> **A fire weather index is not an alert**, and not a forecast of fires. The official
> fire danger for Europe is published by [EFFIS](https://forest-fire.emergency.copernicus.eu/).

The danger classes (`effis_class`: low, moderate from 11.2, high from 21.3, very high
from 38, extreme from 50, very extreme above 70) are the ones EFFIS publishes in its
[technical background](https://forest-fire.emergency.copernicus.eu/about-effis/technical-background/fire-danger-forecast),
read on 2026-11-28. If EFFIS changes them, the library follows in a new release.

## Try it with Docker

```bash
docker compose up                      # a page for a public body on :3007, notebooks on :8885
docker compose --profile mcp up mcp    # the MCP server on :8772/mcp
make help                              # every target
```

The page (`app/`, in Italian) shows the chain of one place day by day from the weather
you give it, and what moved the index. It fetches no weather, no fires, no forecast.

## Examples

Runnable, dependency-free scripts live in [`examples/`](examples/). CI runs every one
of them, so they always match the code.

| Script | What it shows |
|---|---|
| [`01_single_day.py`](examples/01_single_day.py) | One day of the chain, all six outputs explained |
| [`02_fire_season.py`](examples/02_fire_season.py) | A full season, danger classes, CSV export |
| [`03_daily_job_sqlite.py`](examples/03_daily_job_sqlite.py) | A daily job that persists the state in SQLite and resumes |
| [`04_many_stations.py`](examples/04_many_stations.py) | One state per station or grid cell, as in production |
| [`05_southern_hemisphere.py`](examples/05_southern_hemisphere.py) | Custom `FwiParams` for other latitudes |
| [`06_individual_equations.py`](examples/06_individual_equations.py) | What-if analysis with the individual equations |

```console
$ python examples/02_fire_season.py
214 days, 2026-04-01 to 2026-10-31
Peak FWI 103.76 on 2026-09-13 (wind 47.4 km/h)
Days per danger class:
  low            60  ##############################
  moderate       33  ################
  high           64  ################################
  very high      34  #################
  extreme        19  #########
  very extreme    4  ##
```

## Documentation

| Guide | For whom |
|---|---|
| [How the FWI works](https://agentengineering.it/fwi-chain/how-fwi-works/) | Everyone: the science in plain words, with pictures |
| [Getting started](https://agentengineering.it/fwi-chain/getting-started/) | Developers: from `pip install` to a daily job, plus common mistakes |
| [Cookbook](https://agentengineering.it/fwi-chain/cookbook/) | Recipes: pandas, CSV, SQLite, many stations, parallelism, units, HTTP service |
| [API reference](https://agentengineering.it/fwi-chain/api/) | Every public function and class |
| [Facts, explanation and MCP](https://agentengineering.it/fwi-chain/ai/) | What moved the index, the answers as data, the text check, the MCP server |
| [Validation](https://agentengineering.it/fwi-chain/validation/) and [Benchmark](https://agentengineering.it/fwi-chain/benchmark/) | What the numbers are measured against, and what they are not |
| [Riuso](https://agentengineering.it/fwi-chain/riuso/) | In Italian, for a public body |
| [FAQ](https://agentengineering.it/fwi-chain/faq/) | Short answers to common questions |

## Contributing

**Contributions are very welcome**, whether you are a fire scientist, a meteorologist,
a Python developer, or someone who writes clear docs. Some ideas:

- 🔬 Add reference cases to the benchmark: another implementation, a fire service's published values
- 🌍 Contribute day-length tables for other latitude bands
- 📈 Implement the Daily Severity Rating, hourly FFMC, or DC overwintering
- 📝 Improve the docs, translate them, or write a tutorial for your region
- 🐛 Report anything that disagrees with a reference implementation

Start with **[CONTRIBUTING.md](CONTRIBUTING.md)**. It covers a five-minute dev setup,
the project layout, and a list of good first issues.

## Reference and citation

Van Wagner, C.E. (1987). *Development and structure of the Canadian Forest Fire Weather
Index System*. Canadian Forestry Service, Forestry Technical Report 35. The equation
numbers in the source comments are that report's.

If `fwi-chain` helps your work, a link back or a ⭐ on GitHub helps other people find it.

## License

[Apache-2.0](./LICENSE).
