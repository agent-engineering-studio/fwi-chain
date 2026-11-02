# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

## [1.0.0] - 2026-11-02

### Added

- The Van Wagner (1987) FWI chain: FFMC, DMC, DC, ISI, BUI, FWI, and
  `advance()` for one day of the chain with an explicit `FwiState`.
- `STANDARD_PARAMS`: the standard start-up codes and the 46°N day-length
  tables.
- Extracted from Limen (`src/limen/core/scoring/wildfire/fwi.py` at
  49425f2), where the history of the equations lives; relicensed under
  Apache-2.0 by its sole author.
