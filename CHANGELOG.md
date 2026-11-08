# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

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
