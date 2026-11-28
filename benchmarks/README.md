# Benchmark: known cases

A small, fixed set of cases where the answer is known before the code runs.
The equations of the FWI are a standard: the only way to know they were
transcribed right is to compare them with somebody else's numbers.

```bash
uv run python -m benchmarks.run            # the table
uv run python -m benchmarks.run --check    # CI: fails if an outcome or a measure changed
uv run python -m benchmarks.run --write    # accept the new results (results.json)
uv run python -m benchmarks.faithful --check   # the text check finds the faults it should
```

The cffdrs series is downloaded the first time (about 6 KB, checked by
SHA-256; see [`cffdrs/README.md`](cffdrs/README.md)). With no network those
cases print **SKIPPED, not passed**; CI adds `--require-download`, which makes
a skip a failure.

> **A fire weather index is not an alert.** A case here says whether the chain
> computes what it should, nothing about fires.

## The cases

| Case | Where the answer comes from | What is checked |
|---|---|---|
| **48 days of cffdrs** | the test series of the `cffdrs` R package, 13 April to 30 May 1985, and cffdrs's own output for it | each of the six codes within a stated distance of cffdrs, every day; the same EFFIS class, every day |
| **48 days of cffdrs, `constants="cffdrs"`** | the same | each code within 0.007 of cffdrs (measured: 0.006 at most); the same class, every day |
| **The first day, by hand** | Van Wagner (1987) Eq. 22-23, on paper: DC = 15 + (0.36 * 19.8 + 0.9) / 2 = 19.014 | to 1e-9 |
| **The first day, pinned** | this library's own six codes | to 1e-9, so that a change is seen. They prove nothing by themselves |
| **The rain each code ignores** | Van Wagner (1987) Eq. 2, 11, 18: 0.5, 1.5 and 2.8 mm | rain at the limit leaves the code as a dry day; a tenth above lowers it |
| **A stored state too old** | the rule of Limen's backfill | `catch_up()` carries a state exactly at the limit, and discards it one day past |

## What the 48 days say

This library and cffdrs do not give the same numbers, and the benchmark keeps
the difference in view instead of hiding it behind a loose tolerance.

| Code | Largest difference over 48 days: `"1987"` (default) | `"cffdrs"` |
|---|---|---|
| FFMC | 0.123 | 0.005 |
| DMC | 0.065 | 0.006 |
| DC | 0.005 | 0.005 |
| ISI | 0.252 | 0.005 |
| BUI | 0.063 | 0.006 |
| FWI | 0.254 | 0.005 |

The largest FWI difference is on 7 May 1985: 52.56 here, 52.31 in cffdrs, half
a percent. **On all 48 days the two give the same EFFIS class.**

The cause is known. The 1987 report prints the FFMC scale with the constant
147.2 (Eq. 1); the FORTRAN program of Van Wagner & Pickett (1985), which cffdrs
follows, uses 147.27723. The DMC difference is of the same kind: Eq. 12 has
1/43.43 where the program has 0.023 (written `280 / exp(0.023 P)`). With
those two constants changed, all six codes agree with cffdrs to 0.006, the
digits cffdrs prints. The DC, which has no such constant, already agrees to
0.005.

So: this library follows the report as printed, cffdrs the program. Neither
is wrong; they are two printings of one standard, a quarter of an FWI point
apart at most on this series. If you need cffdrs's digits, walk with
`CFFDRS_PARAMS` (or `FwiParams(..., constants="cffdrs")`), from 1.4.0. The
default does not change, so no stored chain moves.

What the benchmark does **not** cover: no observed fire, no comparison with
the FWI that EFFIS or a weather service publishes for a real place (that needs
their weather, and belongs to whoever joins the two), no latitude other than
the standard tables, no winter.

## The faithfulness set

`faithful.json` has four questions about the 48 days, each with an answer
written by hand that quotes the facts right and one with known faults: a
number of another unit, one rounded wrong, one invented. `--check` fails when
`fwi_chain.check.check_text` does not find exactly those faults. It tests the
checker, not a model: no model's answers are in the set yet.

Writing the set found two limits of the check, now in its documentation: a
number that exists as a fact of another unit is reported as a unit fault even
when it was simply made up ("2 days" against an effect of -2.0), and against a
whole series of days a small invented integer can pass by chance.

## Data

`cffdrs/`: see [its README](cffdrs/README.md) for the source, the checksums
and the licence. The files themselves are downloaded, not kept here: cffdrs is
GPL-2.
