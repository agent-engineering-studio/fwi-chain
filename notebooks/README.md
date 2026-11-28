# Example notebooks

Seven notebooks. All run with no network: what they read is in the repository.

| Notebook | What it shows |
|---|---|
| [`01_single_day`](01_single_day.ipynb) | one day of the chain, the six outputs |
| [`02_fire_season`](02_fire_season.ipynb) | a whole season day by day, the danger classes, a CSV |
| [`03_daily_job_sqlite`](03_daily_job_sqlite.ipynb) | a daily job that stores the state and resumes |
| [`04_many_stations`](04_many_stations.ipynb) | one state per station |
| [`05_southern_hemisphere`](05_southern_hemisphere.ipynb) | day-length tables for another latitude |
| [`06_individual_equations`](06_individual_equations.ipynb) | the equations one by one, for what-if questions |
| [`07_what_moved_the_index`](07_what_moved_the_index.ipynb) | 48 days of the cffdrs test series; one day taken apart (memory, wind, humidity, temperature, rain); a sentence checked against the facts |

Notebooks 01 to 06 are the scripts of [`examples/`](../examples/), cell by
cell: `tools/make_notebooks.py` writes them, so the two cannot drift. 02, 03
and 04 use a synthetic season (`examples/weather.py`): it is not observed
weather.

> **A fire weather index is not an alert.** The official fire danger for
> Europe is published by [EFFIS](https://forest-fire.emergency.copernicus.eu/).

## Run them

With [uv](https://docs.astral.sh/uv/):

```bash
uv run --group examples jupyter lab notebooks/
make notebooks     # write them from the examples, run them all, save the results
```

With Docker alone, from the root of the repository:

```bash
docker compose up notebooks     # http://localhost:8885
```
