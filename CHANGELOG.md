# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

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
