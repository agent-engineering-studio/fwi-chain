# Validation

The FWI equations are a **standard**, not a design choice. The only way to know
they were transcribed correctly is to compare them with a known, published case.
A test suite of properties alone ("FWI goes up with wind") would stay green with
a wrong coefficient. That is why the suite has two layers.

## 1. Against cffdrs, over 48 days

[`cffdrs`](https://cran.r-project.org/package=cffdrs) is the reference R
implementation. It ships a test series of 48 days (13 April to 30 May 1985,
the sample data of Van Wagner & Pickett 1985) and its own output for it. The
[benchmark](benchmark.md) walks this library over the same days, in CI:

| Code | Largest difference from cffdrs over 48 days |
|---|---|
| FFMC | 0.123 |
| DMC | 0.065 |
| DC | 0.005 |
| ISI | 0.252 |
| BUI | 0.063 |
| FWI | 0.254 |

On all 48 days the two give the same EFFIS danger class.

The numbers are close, not equal, and the reason is known. This library
follows the equations as printed in Van Wagner (1987): 147.2 in the FFMC scale
(Eq. 1), 1/43.43 in the DMC (Eq. 12). cffdrs follows the FORTRAN program of
1985, which has 147.27723 and 0.023. With those two constants all six codes
agree with cffdrs to 0.006: since 1.4.0 they are an option,
`FwiParams.constants="cffdrs"` or `CFFDRS_PARAMS`, measured in the benchmark
next to the default. The default stays the report, so no stored chain moves.

The two files of the cffdrs series are not in this repository (cffdrs is
GPL-2): the benchmark downloads them at a fixed commit and checks their
SHA-256. See [the benchmark](benchmark.md).

!!! note "A correction"
    Up to 1.1.0 these pages said the library was "verified against the cffdrs
    reference day to 1e-9". That was not accurate. The inputs of that day are
    the first day of the cffdrs series; the six expected values to 1e-9 are
    this library's own. cffdrs gives FFMC 87.65, ISI 10.78 and FWI 10.04 for
    that day, against 87.69, 10.85 and 10.10 here.

## 1b. The first day, to 1e-9

[`tests/test_chain.py::test_published_reference_day`](https://github.com/agent-engineering-studio/fwi-chain/blob/main/tests/test_chain.py)
pins the six codes of the first day of that series, as this library computes
them:

| Input | Value |
|---|---|
| Start state | FFMC 85, DMC 6, DC 15 (the standard start-up codes) |
| Month | April |
| Temperature | 17.0 °C |
| Relative humidity | 42 % |
| Wind | 25 km/h |
| Rain | 0 mm |

| Output | Pinned value | Tolerance |
|---|---|---|
| FFMC | 87.692980092774 | 1e-9 absolute |
| DMC | 8.5450511359998 | 1e-9 |
| DC | 19.013999999999996 | 1e-9 |
| ISI | 10.853661073312 | 1e-9 |
| BUI | 8.4904265358371 | 1e-9 |
| FWI | 10.096371392382 | 1e-9 |

A pinned value shows a change; it does not show the value is right. What
shows that is the comparison above, and the DC, which can be checked by hand:
see [the worked example](how-fwi-works.md#a-worked-example-by-hand).

```bash
python examples/01_single_day.py
```

## 2. What a single day cannot reach

The cffdrs series has 14 days with rain, so it reaches the rain branches. The
rest of the suite covers each of them on purpose, along with the behaviour the
science requires:

| Test | What it guards |
|---|---|
| `test_light_rain_is_intercepted_by_the_canopy` | rain below 0.5 / 1.5 / 2.8 mm does not wet the fuel |
| `test_heavy_rain_lowers_every_code` | heavy rain wets all three codes, not just FFMC |
| `test_dmc_wetting_covers_the_three_slopes_of_eq_13` | every branch of Eq. 13 (DMC ≤ 33, ≤ 65, > 65) |
| `test_the_saturation_correction_reads_the_pre_rain_moisture` | Eq. 3a applies only to fuel already saturated before the rain |
| `test_codes_stay_inside_their_domains` | no NaN or negative values under extreme sirocco, frost, or a 200 mm cloudburst |
| `test_buildup_index_survives_both_codes_at_zero` | Eq. 27's division by zero on a soaked landscape |
| `test_the_drought_code_remembers_far_longer_than_the_fine_fuel` | the memory asymmetry: after a storm and a dry week FFMC fully recovers, DC recovers less than half |
| `test_fwi_is_monotone_in_both_of_its_inputs` | more spread or more fuel never lowers the index |
| `test_a_day_length_table_of_the_wrong_size_is_refused` | an 11-month table cannot silently shift the year |
| `tests/test_examples.py` | every script in `examples/` runs |

## 3. The quality gate

Every push and pull request runs, on Python 3.12 and 3.13:

```bash
uv run ruff check            # lint
uv run ruff format --check   # formatting
uv run mypy                  # --strict, on src and tests
uv run pytest --cov          # tests, coverage must stay ≥ 90 %
uv run python -m benchmarks.run --check        # the known cases
uv run python -m benchmarks.faithful --check   # the text check
uv build                     # the package builds
```

Locally, `make check` runs the same gate.

## Found a disagreement?

If `fwi-chain` disagrees with another implementation (cffdrs, xclim, a national
service's published values), please
[open an issue](https://github.com/agent-engineering-studio/fwi-chain/issues/new/choose)
with the inputs, the start state, and both outputs. New reference vectors are
among the most valuable contributions to this project.
