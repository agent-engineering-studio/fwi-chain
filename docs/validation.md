# Validation

The FWI equations are a **standard**, not a design choice. The only way to know
they were transcribed correctly is to compare them with a known, published case.
A test suite of properties alone ("FWI goes up with wind") would stay green with
a wrong coefficient. That is why the suite has two layers.

## 1. The reference day, to 1e-9

[`tests/test_chain.py::test_published_reference_day`](https://github.com/agent-engineering-studio/fwi-chain/blob/main/tests/test_chain.py) runs
the first day of the test series that ships with
[`cffdrs`](https://cran.r-project.org/package=cffdrs), the reference R
implementation of Van Wagner's equations:

| Input | Value |
|---|---|
| Start state | FFMC 85, DMC 6, DC 15 (the standard start-up codes) |
| Month | April |
| Temperature | 17.0 °C |
| Relative humidity | 42 % |
| Wind | 25 km/h |
| Rain | 0 mm |

| Output | Expected | Tolerance |
|---|---|---|
| FFMC | 87.692980092774 | 1e-9 absolute |
| DMC | 8.5450511359998 | 1e-9 |
| DC | 19.013999999999996 | 1e-9 |
| ISI | 10.853661073312 | 1e-9 |
| BUI | 8.4904265358371 | 1e-9 |
| FWI | 10.096371392382 | 1e-9 |

The tolerance is tight on purpose. Nothing is being calibrated: a transcription
is being checked. A deviation larger than 1e-9 means a wrong coefficient, not
floating-point noise.

Check it yourself in one line:

```bash
python examples/01_single_day.py
```

The DC can even be checked by hand. See
[the worked example](how-fwi-works.md#a-worked-example-by-hand).

## 2. What a single day cannot reach

The reference day is dry, so it never exercises the rain branches. The rest of
the suite covers them, along with the behaviour the science requires:

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
uv build                     # the package builds
```

Locally, `make check` runs the same gate.

## Found a disagreement?

If `fwi-chain` disagrees with another implementation (cffdrs, xclim, a national
service's published values), please
[open an issue](https://github.com/agent-engineering-studio/fwi-chain/issues/new/choose)
with the inputs, the start state, and both outputs. New reference vectors are
among the most valuable contributions to this project.
