# The test series of cffdrs

The benchmark compares this library with the [`cffdrs`](https://github.com/cffdrs/cffdrs_r)
R package on cffdrs's own test series. The two files of that series are **not
in this repository**: cffdrs is distributed under GPL-2. Until fwi-chain 1.3.0
they were committed here; from 1.4.0 the benchmark downloads them when it runs.

| File | Path in cffdrs_r | SHA-256 of the bytes there |
|---|---|---|
| `test_fwi.csv`: 48 daily noon readings, 13 April to 30 May 1985 | `data/test_fwi.csv` | `9fac2165cbc4ffdadd9509943efebddba29afcb6936a4e60ab4d86fafd2a6c2a` |
| `fwi_01.csv`: what `fwi(test_fwi)` gives for those days, cffdrs's own expected output | `tests/testthat/data/fwi_01.csv` | `ad9b9a964eb0409c0e8eeb4f88ce5384cb1b49e098765d5c1f539bc32d96ef43` |

They are read at a fixed commit, the one of cffdrs 1.10.0:
`https://raw.githubusercontent.com/cffdrs/cffdrs_r/4d20a303bf94febccce62f068cc8ffad0fec57c1/<path>`.
A file whose SHA-256 is not the one above is refused. A copy is kept in
`.cache/` here, ignored by git. With no network the comparison is reported as
**skipped**, not passed; CI runs with `--require-download`, where a skip is a
failure. The code is in [`../cffdrs_data.py`](../cffdrs_data.py).

## What stays here: our numbers, and the differences we measured

Over the 48 days, the largest difference between this library and cffdrs, per
code (fwi-chain 1.4.0, measured 2026-11-28):

| Code | `constants="1987"` (the default) | `constants="cffdrs"` |
|---|---|---|
| FFMC | 0.123 | 0.005 |
| DMC | 0.065 | 0.006 |
| DC | 0.005 | 0.005 |
| ISI | 0.252 | 0.005 |
| BUI | 0.063 | 0.006 |
| FWI | 0.254 | 0.005 |
| Same EFFIS class | 48 of 48 days | 48 of 48 days |

cffdrs keeps its output to two decimals (three for the DMC), so 0.005 is its
rounding. The results of every run are in [`../results.json`](../results.json).

## Attribution

The readings are the sample data of Van Wagner, C.E. and Pickett, T.L. (1985).
*Equations and FORTRAN program for the Canadian Forest Fire Weather Index
System.* Canadian Forestry Service, Forestry Technical Report 33. The expected
output is computed by the `cffdrs` R package, version 1.10.0 (GPL-2), and
kept by its authors with the package. Nothing of cffdrs's code is in this repository.
