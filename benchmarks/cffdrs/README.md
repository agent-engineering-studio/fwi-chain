# The test series of cffdrs

Two files, copied unchanged from the [`cffdrs`](https://github.com/cffdrs/cffdrs_r)
R package, version 1.10.0 (commit `4d20a303bf`, read on 2026-11-28):

| File here | File there | What it is |
|---|---|---|
| `test_fwi.csv` | `data/test_fwi.csv` | 48 daily noon readings, 13 April to 30 May 1985: the sample data of Van Wagner & Pickett (1985) |
| `fwi_01.csv` | `tests/testthat/data/fwi_01.csv` | what `fwi(test_fwi)` gives for those days, kept by cffdrs as its own expected output |

cffdrs is distributed under GPL-2. These two files are tables of numbers; they
are here as the reference this library is measured against, and nothing of
cffdrs's code is. If you are the author and want them removed, open an issue.

Van Wagner, C.E. and Pickett, T.L. (1985). *Equations and FORTRAN program for
the Canadian Forest Fire Weather Index System.* Canadian Forestry Service,
Forestry Technical Report 33.
