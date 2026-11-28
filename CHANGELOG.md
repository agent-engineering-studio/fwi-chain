# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
