# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.4.0] - 2026-11-28

Additions only: with the default, every number of 1.3.0 is unchanged.

### Added

- `FwiParams.constants`: `"1987"` (the report, the default) or `"cffdrs"`
  (the FORTRAN program of 1985, which the cffdrs R package follows), and
  `CFFDRS_PARAMS`, `STANDARD_PARAMS` with the program's constants. They are
  147.27723 for 147.2 in the FFMC scale (Eq. 1, 10, and the ISI) and
  `280 / exp(0.023 P)` for `exp(5.6348 - P / 43.43)` in the DMC (Eq. 12).
  With them the six codes agree with cffdrs to 0.006 over its 48-day test
  series, against 0.254 FWI points with the default. `fine_fuel_moisture_code`,
  `duff_moisture_code` and `initial_spread_index` take the same `constants`
  keyword. The type is `Constants`.
- The printing is named in the facts (`constants` in `day_facts` with params
  and in `walk_facts`), and the MCP tools `walk` and `explain` take
  `constants`.
- The benchmark measures both printings against cffdrs.

### Changed

- **The two cffdrs files are no longer in the repository.** `test_fwi.csv` and
  `fwi_01.csv` came from cffdrs, which is distributed under GPL-2, while this
  repository is Apache-2.0: rather than keep files of two licences in one
  tree, the benchmark now
  downloads them from cffdrs_r at the commit of version 1.10.0
  (`4d20a303bf`), by a fixed URL, and refuses a file whose SHA-256 is not the
  one recorded in `benchmarks/cffdrs/README.md`. With no network the
  comparison says **skipped**, never passed; CI runs with
  `--require-download`. What stays here is ours: the differences we measured,
  in `benchmarks/results.json`, with the attribution. Notebook 07 and the
  blog figures download the series the same way. The files remain in the git
  history of 1.2.0 and 1.3.0; they were never in a published package.
- **The diary's sample is an Italian summer.** `app/data/esempio_canada_1985.csv`
  held the same 48 readings of the cffdrs series, reformatted, so it went for
  the same reason. In its place is `esempio_gioia_del_colle_2025.csv`: Gioia del
  Colle (BA), 1 May to 30 September 2025, noon readings (11 UTC) taken with
  `noon_readings()` from the Open-Meteo historical weather API (ERA5
  reanalysis, CC BY 4.0, credited on the page and in the file). It is a model,
  not a station. `tools/make_app_sample.py` writes it again; the screenshots
  of the diary are redone on it.

## [1.3.0] - 2026-11-28

Additions only: nothing in 1.2.0 changed.

### Added

- `noon_reading()` and `noon_readings()` (`fwi_chain.noon`): the noon reading
  of a day from hourly weather, with the rain of the 24 hours before the hour
  read. The largest distance from noon and the fewest hours of rain accepted
  are arguments with no default, and the answer (`NoonReading`) always says
  which hour was read and how many hours of rain were not measured. New type
  `HourlySample`, where `None` is "not measured" and never zero.
- Moved from Limen (`MeteoSnapshot.noon_observation` at 9fbdd2d). With nothing
  refused it gives Limen's readings (`tests/test_noon.py`, fixture from
  `scripts/limen_noon_parity.py`). The difference is stated and tested:
  Limen read the nearest hour however far from noon (05:00 as noon, in one
  test case) and summed the rain over the hours that were there, so a missing
  hour counted as dry. Both are now counted, and refused when asked.

## [1.2.0] - 2026-11-28

Additions only: nothing in 1.1.0 changed. The package still has no
dependencies; the MCP server is behind the `mcp` extra.

### Added

- `catch_up()`: the daily update in one call. A stored state more than
  `max_gap_days` before the target day is discarded at exactly that limit.
  Calling `days_to_walk()` and then `walk_chain()` carried a state up to twice
  the limit: both are unchanged, and `catch_up()` is the call that cannot make
  that mistake. `start_is_stale()` is the test alone.
- `effis_class()` and `EFFIS_FWI_CLASSES`: the six fire danger classes EFFIS
  maps an FWI in, with the boundaries it publishes ("very extreme", above 70,
  was added by EFFIS in 2021).
- `explain_change()` (`fwi_chain.explain`): what moved the FWI from one day to
  the next. The chain's memory, and the FWI points moved by temperature,
  humidity, wind and rain, which add up exactly (Shapley split).
- `fwi_chain.facts`: `day_facts()`, `walk_facts()` and `distribution_facts()`
  give the chain's answers as plain data, with units in the key names and the
  rule that a fire weather index is not an alert.
- `fwi_chain.check.check_text()`: the numbers of a text that are not facts as
  written (invented, in the wrong unit, rounded wrong).
- An MCP server, `fwi-chain-mcp` (`pip install "fwi-chain[mcp]"`), on standard
  input and output or streamable HTTP (port 8772): tools `walk`, `explain`,
  `percentile` and `check`. It computes only from what a call gives it.
- A benchmark of known cases, run in CI (`make bench`): the 48 days of the
  `cffdrs` test series against cffdrs's own output, the rain each code
  ignores, a stored state too old; and a faithfulness set for `check_text`.
- A page in Italian for a public body, `app/` ("Il diario del pericolo
  d'incendio"): the chain of one place day by day from the weather the body
  gives, and what moved the index. It fetches nothing.
- Seven notebooks in `notebooks/`, the first six written from `examples/`.
- Docker (`Dockerfile`, `compose.yaml`: the page on 3007, the notebooks on
  8885, the MCP server on 8772), a `Makefile` with `make help`,
  `publiccode.yml`, `llms.txt`, `llms-full.txt` and an agent skill on the site.

### Fixed

- Documentation: the library was described as "verified against the cffdrs
  reference day to 1e-9". It was not: the values pinned to 1e-9 are this
  library's own. Measured against cffdrs's own output over its 48-day series,
  the two differ by at most 0.25 FWI points (0.12 FFMC, 0.07 DMC) and give the
  same EFFIS class every day. cffdrs follows the constants of the 1985 FORTRAN
  program (147.27723, 0.023), this library the 1987 report as printed (147.2,
  1/43.43). No number computed by the library changed.
- Documentation and example 02 used an older six-class EFFIS scale ("very
  low" below 5.2). They now use the scale EFFIS publishes today.

## [1.1.0] - 2026-11-28

Additions only: nothing in 1.0.0 changed.

### Added

- Walking the chain over many days (`fwi_chain.walk`): `walk_chain()` resumes
  from a stored point across days with no observation and restarts from the
  standard codes after a gap too long; `days_to_walk()` gives the days a chain
  has to catch up; `writable_days()` keeps a forecast day from being stored.
  New types `NoonObservation`, `ChainPoint` and `ChainDay`.
- Re-walking the chain when better rain arrives: `rewalk_with_rain()` and
  `correct_rain()` redo stored days with measured rain, in millimetres, keeping
  the temperature, humidity and wind already used.
- A climatology (`fwi_chain.climatology`): `quantiles()` summarises a list of
  values in the 21 `QUANTILE_LEVELS`, `percentile()` places a value among them,
  `node_ceiling()` derives a place's "full" FWI from its monthly quantiles,
  `accumulate_monthly()` files years of chain under their months and
  `coverage_is_valid()` says whether a stretch of days is complete enough.
- All of it moved from Limen (`advance_node`, `ricalcola`, `correggi`,
  `accumula`, `copertura_valida`, `quantili`, `percentile`, `tetto_del_nodo` at
  3b0e1ee) and checked against Limen's own output on fixed inputs
  (`tests/test_limen_parity.py`, fixture from `scripts/limen_parity.py`).
  Still pure, scalar and without dependencies: days are `datetime.date` values
  the caller passes in, and nothing reads a clock.
- Documentation: a plain-language guide to the FWI System, getting started, a
  cookbook, an API reference, validation notes, an FAQ and a social media kit.
- A documentation site on GitHub Pages, built with [Zensical](https://zensical.org)
  (`zensical.toml`, `make docs`).
- Six runnable, dependency-free examples in `examples/`, executed by the test
  suite so they cannot drift from the code.
- Figures computed by the library (`make figures`) and a diagram of the chain.
- Issue and pull request templates; an expanded contributing guide.

## [1.0.0] - 2026-11-02

### Added

- The Van Wagner (1987) FWI chain: FFMC, DMC, DC, ISI, BUI, FWI, and
  `advance()` for one day of the chain with an explicit `FwiState`.
- `STANDARD_PARAMS`: the standard start-up codes and the 46°N day-length
  tables.
- Extracted from Limen (`src/limen/core/scoring/wildfire/fwi.py` at
  49425f2), where the history of the equations lives; relicensed under
  Apache-2.0 by its sole author.
