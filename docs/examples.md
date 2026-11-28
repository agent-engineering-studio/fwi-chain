# Notebooks, the page and Docker

## Seven notebooks

All run with no network.

| Notebook | What it shows |
|---|---|
| `01_single_day` | one day of the chain, the six outputs |
| `02_fire_season` | a whole season day by day, the danger classes, a CSV |
| `03_daily_job_sqlite` | a daily job that stores the state and resumes |
| `04_many_stations` | one state per station |
| `05_southern_hemisphere` | day-length tables for another latitude |
| `06_individual_equations` | the equations one by one |
| `07_what_moved_the_index` | 48 days of the cffdrs test series; one day taken apart; a sentence checked against the facts |

They are in [`notebooks/`](https://github.com/agent-engineering-studio/fwi-chain/tree/main/notebooks).
Notebooks 01 to 06 are the scripts of `examples/`, cell by cell.

```bash
uv run --group examples jupyter lab notebooks/
make notebooks     # write them from the examples, run them all, save the results
```

## The page for a public body

`app/` is a small page in Italian, "Il diario del pericolo d'incendio": the
chain of one place, day by day, from the weather the body gives, and what
moved the index on the day chosen. See [Riuso](riuso.md).

```bash
make demo          # http://127.0.0.1:3007 (needs uv and npm)
```

## Docker

Nothing to install but Docker:

```bash
docker compose up                      # the page on :3007, the notebooks on :8885
docker compose --profile mcp up mcp    # the MCP server on :8772/mcp
docker compose run --rm bench          # the benchmark
make down                              # stop and remove everything
```

| Service | Container | Port | Variable |
|---|---|---|---|
| the page | `fwi-chain-ui` | 3007 | `FWI_CHAIN_PORT` |
| the notebooks | `fwi-chain-notebooks` | 8885 | `FWI_CHAIN_NOTEBOOKS_PORT` |
| the MCP server | `fwi-chain-mcp` | 8772 | `FWI_CHAIN_MCP_PORT` |

Every port listens on `127.0.0.1` only. `make help` lists every target.
