# Contributing to fwi-chain

Thank you for considering a contribution! `fwi-chain` is small on purpose, which
makes it a good place for a first open-source contribution, and a place where
domain expertise in fire science or meteorology goes a long way.

## Ways to help (no code required)

- ⭐ **Star the repo and share it.** The [social media kit](docs/social-kit.md) has ready-made posts and images.
- 🐛 **Report a disagreement** with cffdrs, xclim, or a fire service's published values.
- 📝 **Improve the docs.** If something confused you, it will confuse the next person too.
- 🌍 **Tell us where you use it.** A short issue saying "we run this for region X" helps the project a lot.

## Good first issues

These are well-scoped and don't require deep knowledge of the codebase. Please
open an issue first to say you are taking one, so nobody duplicates the work.

| Idea | Skills | Notes |
|---|---|---|
| More reference vectors from the `cffdrs` test series | Python, a little R | add rows with rain, so every rain branch is checked against published values |
| A table of day-length factors for other latitude bands | fire science | as ready-made `FwiParams` constants, with sources |
| Daily Severity Rating (`dsr = 0.0272 * fwi ** 1.77`) | Python | a one-line function, plus a test and docs |
| Comparison notebook against xclim | Python, xarray | in `docs/`, not a dependency |
| Translations of `docs/how-fwi-works.md` | any language | Italian, Spanish, Portuguese, Greek and French are a good start for Mediterranean users |
| Benchmarks | Python | `pytest-benchmark` or a small script in `docs/` |

## Larger ideas (discuss first)

- **DC overwintering** (Turner & Lawson 1978; Lawson & Armitage 2008): carry the DC
  through a winter instead of restarting at 15.
- **Hourly FFMC** (Van Wagner 1977), for sub-daily danger.
- **Fire Behaviour Prediction (FBP) System** components, probably as a separate package.

The guiding principle: **pure functions, no dependencies, every constant traced to
a published equation.**

## Development setup (5 minutes)

You need [uv](https://docs.astral.sh/uv/).

```bash
git clone https://github.com/agent-engineering-studio/fwi-chain
cd fwi-chain
uv sync          # creates .venv with the dev tools
make check       # lint + typecheck + tests: what CI runs
```

Other targets:

```bash
make format      # ruff format + autofix
make test        # pytest with coverage
make figures     # regenerate docs/images (needs network for matplotlib once)
make build       # build sdist + wheel
```

## Project layout

```
fwi-chain/
├── src/fwi_chain/
│   ├── __init__.py        # public API re-exports, __version__
│   └── chain.py           # the whole library: Van Wagner's equations + advance()
├── tests/
│   ├── test_chain.py      # reference day to 1e-9, rain branches, bounds, memory
│   └── test_examples.py   # every script in examples/ must run
├── examples/              # runnable, dependency-free scripts (01_… to 06_…)
│   └── weather.py         # deterministic synthetic season used by examples and figures
├── docs/
│   ├── *.md               # guides, API reference, FAQ, social kit
│   ├── images/            # figures (generated) and the chain diagram (hand-written SVG)
│   └── scripts/make_figures.py
└── .github/workflows/     # ci.yml (every push/PR), release.yml (tags → PyPI)
```

## Rules of the road

- **`make check` must pass**: ruff, `mypy --strict` and pytest (coverage ≥ 90 %).
  It is the same gate CI runs.
- **Equations are transcribed, not tuned.** Any change to a constant in `chain.py`
  must cite the equation it comes from and come with a reference value that proves it.
- **No runtime dependencies.** Tools used only for docs or development go in the
  `dev` group or run with `uv run --with`.
- **Examples are documentation.** If you change the API, update `examples/` and `docs/`
  in the same PR. `tests/test_examples.py` will remind you.
- **Commits** follow [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, …).
- **Changelog**: add a line under `[Unreleased]` in `CHANGELOG.md` for user-visible changes.

## Pull request checklist

- [ ] `make check` is green
- [ ] tests cover the change (for equations: a reference value)
- [ ] docs and examples updated if the API changed
- [ ] `CHANGELOG.md` updated

## Releasing (maintainers)

Bump `version` in `pyproject.toml`, move `[Unreleased]` to the new version in
`CHANGELOG.md`, then push a tag `vX.Y.Z`. The release workflow checks that the tag
matches the version, runs the tests, publishes to PyPI with trusted publishing,
and creates a GitHub release.

## License

Contributions are accepted under the project's license, Apache-2.0 (section 5 of
the license: inbound = outbound). There is no separate CLA.
